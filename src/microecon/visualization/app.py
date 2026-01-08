"""
DearPyGui-based visualization for microecon simulation.

This module provides a live visualization of the search-and-exchange simulation,
showing agents moving on a grid, trading, and updating metrics in real-time.

Supports two modes:
- Live mode: Run a new simulation with real-time updates
- Replay mode: Play back a logged simulation run with timeline scrubbing
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal
import time

import dearpygui.dearpygui as dpg

from microecon.simulation import Simulation, create_simple_economy, TradeEvent
from microecon.grid import Position
from microecon.agent import Agent
from microecon.logging import AgentSnapshot, TickRecord, RunData
from microecon.logging.events import BeliefSnapshot, TypeBeliefSnapshot, PriceBeliefSnapshot
from microecon.visualization.replay import ReplayController
from microecon.visualization.timeseries import TimeSeriesPanel, DualTimeSeriesPanel
from microecon.visualization.export import (
    export_png, export_svg, SVGExportConfig,
    export_tick_json, export_agents_csv, export_trades_csv,
    GIFRecorder, GIFExportConfig, DataExportConfig,
)
from microecon.visualization.edgeworth import EdgeworthBoxPopup, TradeData


# ============================================================================
# Color utilities
# ============================================================================

def alpha_to_color(alpha: float) -> tuple[int, int, int, int]:
    """
    Map agent's alpha parameter to a color.

    Low alpha (prefers good y) -> blue (70, 130, 180)
    High alpha (prefers good x) -> orange (255, 140, 0)

    Returns RGBA tuple (0-255 for each component).
    """
    # Interpolate between steel blue and orange
    r = int(70 + alpha * (255 - 70))
    g = int(130 + alpha * (140 - 130))
    b = int(180 + alpha * (0 - 180))
    return (r, g, b, 255)


def lerp_color(c1: tuple[int, ...], c2: tuple[int, ...], t: float) -> tuple[int, ...]:
    """Linear interpolation between two colors."""
    return tuple(int(a + t * (b - a)) for a, b in zip(c1, c2))


# ============================================================================
# Agent data proxy (unified interface for live/replay modes)
# ============================================================================

@dataclass
class AgentProxy:
    """
    Unified interface for agent data in both live and replay modes.

    In live mode, wraps an Agent object.
    In replay mode, wraps an AgentSnapshot from logged data.
    """
    id: str
    position: Position
    alpha: float
    endowment_x: float
    endowment_y: float
    utility: float
    perception_radius: float = 7.0  # Default; only used for selection overlay

    @classmethod
    def from_agent(cls, agent: Agent, pos: Position) -> "AgentProxy":
        """Create from live Agent."""
        return cls(
            id=agent.id,
            position=pos,
            alpha=agent.preferences.alpha,
            endowment_x=agent.endowment.x,
            endowment_y=agent.endowment.y,
            utility=agent.utility(),
            perception_radius=agent.perception_radius,
        )

    @classmethod
    def from_snapshot(cls, snapshot: AgentSnapshot, perception_radius: float = 7.0) -> "AgentProxy":
        """Create from logged AgentSnapshot."""
        return cls(
            id=snapshot.agent_id,
            position=Position(snapshot.position[0], snapshot.position[1]),
            alpha=snapshot.alpha,
            endowment_x=snapshot.endowment[0],
            endowment_y=snapshot.endowment[1],
            utility=snapshot.utility,
            perception_radius=perception_radius,
        )


# ============================================================================
# Belief data proxy (VIZ-004 to VIZ-007)
# ============================================================================

@dataclass
class BeliefProxy:
    """
    Proxy for agent belief data in visualization.

    Provides access to an agent's beliefs about other agents (type beliefs)
    and about market prices (price belief).
    """
    agent_id: str
    type_beliefs: tuple[TypeBeliefSnapshot, ...]  # Beliefs about other agents
    price_belief: Optional[PriceBeliefSnapshot]   # Belief about prices
    n_trades_in_memory: int

    @property
    def n_type_beliefs(self) -> int:
        """Number of type beliefs held."""
        return len(self.type_beliefs)

    @property
    def has_beliefs(self) -> bool:
        """Whether agent has any beliefs."""
        return self.n_type_beliefs > 0 or (self.price_belief is not None and self.price_belief.n_observations > 0)

    def get_belief_about(self, target_id: str) -> Optional[TypeBeliefSnapshot]:
        """Get belief about a specific agent, if any."""
        for tb in self.type_beliefs:
            if tb.target_agent_id == target_id:
                return tb
        return None

    @classmethod
    def from_snapshot(cls, snapshot: BeliefSnapshot) -> "BeliefProxy":
        """Create from logged BeliefSnapshot."""
        return cls(
            agent_id=snapshot.agent_id,
            type_beliefs=snapshot.type_beliefs,
            price_belief=snapshot.price_belief,
            n_trades_in_memory=snapshot.n_trades_in_memory,
        )

    @classmethod
    def from_agent(cls, agent: Agent) -> "BeliefProxy":
        """Create from live Agent with belief system."""
        if not agent.has_beliefs:
            return cls(
                agent_id=agent.id,
                type_beliefs=(),
                price_belief=None,
                n_trades_in_memory=0,
            )

        # Convert type beliefs to snapshots
        type_belief_snapshots = tuple(
            TypeBeliefSnapshot(
                target_agent_id=tb.agent_id,
                believed_alpha=tb.believed_alpha,
                confidence=tb.confidence,
                n_interactions=tb.n_interactions,
            )
            for tb in agent.type_beliefs.values()
        )

        # Convert price belief to snapshot
        price_snapshot = PriceBeliefSnapshot(
            mean=agent.price_belief.mean,
            variance=agent.price_belief.variance,
            n_observations=agent.price_belief.n_observations,
        ) if agent.price_belief else None

        return cls(
            agent_id=agent.id,
            type_beliefs=type_belief_snapshots,
            price_belief=price_snapshot,
            n_trades_in_memory=agent.memory.n_trades() if agent.memory else 0,
        )


# ============================================================================
# Trade animation tracking
# ============================================================================

@dataclass
class TradeAnimation:
    """Track a trade animation in progress."""
    agent1_id: str
    agent2_id: str
    start_time: float
    duration: float = 2.0  # Increased from 0.5 for easier clicking (VIZ-012)
    # Pre/post allocation data for Edgeworth box (VIZ-012)
    pre_endow_1: Optional[tuple[float, float]] = None
    pre_endow_2: Optional[tuple[float, float]] = None
    post_alloc_1: Optional[tuple[float, float]] = None
    post_alloc_2: Optional[tuple[float, float]] = None
    alpha_1: Optional[float] = None
    alpha_2: Optional[float] = None


# ============================================================================
# Main visualization app
# ============================================================================

class VisualizationApp:
    """
    Main visualization application.

    Handles the DearPyGui window, rendering, and simulation control.
    """

    # Layout constants
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 850
    METRICS_PANEL_WIDTH = 240
    CONTROLS_HEIGHT = 60
    GRID_MARGIN = 20

    # Colors
    GRID_LINE_COLOR = (200, 200, 200, 100)
    TRADE_LINE_COLOR = (255, 200, 0, 255)
    BACKGROUND_COLOR = (30, 30, 30, 255)

    def __init__(
        self,
        n_agents: int = 10,
        grid_size: int = 15,
        seed: int | None = None,
        mode: Literal["live", "replay"] = "live",
        run_data: RunData | None = None,
    ):
        """
        Initialize visualization app.

        Args:
            n_agents: Number of agents (live mode only)
            grid_size: Grid size (live mode only)
            seed: Random seed (live mode only)
            mode: "live" for new simulation, "replay" for logged run
            run_data: Logged run data (required for replay mode)
        """
        self.mode = mode

        if mode == "live":
            self.n_agents = n_agents
            self.grid_size = grid_size
            self.seed = seed
            self.sim: Optional[Simulation] = create_simple_economy(
                n_agents, grid_size, seed=seed
            )
            self.replay: Optional[ReplayController] = None
        else:
            if run_data is None:
                raise ValueError("run_data required for replay mode")
            self.n_agents = run_data.config.n_agents
            self.grid_size = run_data.config.grid_size
            self.seed = run_data.config.seed
            self.sim = None
            self.replay = ReplayController(run_data)

        # Playback state
        self.playing = False
        self.ticks_per_second = 2.0
        self.last_tick_time = 0.0

        # Animation state
        self.trade_animations: list[TradeAnimation] = []

        # UI element references
        self.drawlist: int = 0
        self.tick_text: int = 0
        self.trades_text: int = 0
        self.welfare_text: int = 0
        self.gains_text: int = 0
        self.play_button: int = 0
        self.speed_slider: int = 0

        # Replay-specific UI elements
        self.timeline_slider: int = 0
        self.step_back_button: int = 0
        self.mode_text: int = 0

        # Rendering state
        self.canvas_size = 0.0
        self.cell_size = 0.0
        self.canvas_origin = (0.0, 0.0)

        # Hover tracking (uses AgentProxy for unified interface)
        self.hovered_agent: Optional[AgentProxy] = None

        # Selection tracking (click to select, shows perception radius)
        self.selected_agent: Optional[AgentProxy] = None

        # Movement trail tracking
        self.position_history: dict[str, list[Position]] = {}  # agent_id -> recent positions
        self.TRAIL_LENGTH = 5

        # Cache for AgentProxy lookup (rebuilt each frame)
        self._agent_proxies: list[AgentProxy] = []
        self._agents_by_id: dict[str, AgentProxy] = {}

        # Overlay toggle state (VIZ-001, VIZ-002, VIZ-003, VIZ-006)
        self.overlay_toggles: dict[str, bool] = {
            "trails": True,              # Default ON for backward compatibility
            "perception_selected": True,  # Show perception for selected agent
            "perception_all": False,      # Show perception for all agents
            "belief_connections": False,  # Show belief connections between agents (VIZ-006)
        }
        # UI element references for toggles
        self.overlay_toggle_ids: dict[str, int] = {}

        # Belief proxy cache (VIZ-004 to VIZ-007)
        self._belief_proxies: dict[str, BeliefProxy] = {}  # agent_id -> BeliefProxy

        # Time-series panel (initialized in setup)
        self.timeseries_panel: Optional[TimeSeriesPanel] = None

        # Export state (VIZ-008 to VIZ-011)
        self._gif_recorder: Optional[GIFRecorder] = None
        self._gif_recording = False
        self.export_status_text: int = 0  # UI element reference

        # Edgeworth box popup (VIZ-012 to VIZ-014)
        self._edgeworth_popup: Optional[EdgeworthBoxPopup] = None
        self._trade_history: list[TradeData] = []  # Persistent trade history for panel

    def grid_to_canvas(self, pos: Position) -> tuple[float, float]:
        """Convert grid position to canvas coordinates."""
        x = self.canvas_origin[0] + (pos.col + 0.5) * self.cell_size
        y = self.canvas_origin[1] + (pos.row + 0.5) * self.cell_size
        return (x, y)

    def canvas_to_grid(self, x: float, y: float) -> Optional[Position]:
        """Convert canvas coordinates to grid position, or None if outside grid."""
        col = int((x - self.canvas_origin[0]) / self.cell_size)
        row = int((y - self.canvas_origin[1]) / self.cell_size)
        if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
            return Position(row, col)
        return None

    # ========================================================================
    # Unified data access (works in both live and replay modes)
    # ========================================================================

    def _build_agent_proxies(self) -> None:
        """Rebuild agent proxy cache from current state."""
        self._agent_proxies = []
        self._agents_by_id = {}
        self._belief_proxies = {}

        if self.mode == "live" and self.sim is not None:
            for agent in self.sim.agents:
                pos = self.sim.grid.get_position(agent)
                if pos is not None:
                    proxy = AgentProxy.from_agent(agent, pos)
                    self._agent_proxies.append(proxy)
                    self._agents_by_id[proxy.id] = proxy
                    # Build belief proxy (VIZ-004 to VIZ-007)
                    if agent.has_beliefs:
                        self._belief_proxies[agent.id] = BeliefProxy.from_agent(agent)
        elif self.mode == "replay" and self.replay is not None:
            state = self.replay.get_state()
            if state is not None:
                # Get perception radius from config if available
                perception_radius = self.replay.run.config.perception_radius
                for snapshot in state.agent_snapshots:
                    proxy = AgentProxy.from_snapshot(snapshot, perception_radius)
                    self._agent_proxies.append(proxy)
                    self._agents_by_id[proxy.id] = proxy
                # Build belief proxies from tick record (VIZ-007)
                for belief_snapshot in state.belief_snapshots:
                    self._belief_proxies[belief_snapshot.agent_id] = BeliefProxy.from_snapshot(belief_snapshot)

    def get_agents(self) -> list[AgentProxy]:
        """Get all agents as AgentProxy objects."""
        return self._agent_proxies

    def get_agent_by_id(self, agent_id: str) -> Optional[AgentProxy]:
        """Get agent by ID."""
        return self._agents_by_id.get(agent_id)

    def get_belief_by_id(self, agent_id: str) -> Optional[BeliefProxy]:
        """Get belief proxy by agent ID (VIZ-004)."""
        return self._belief_proxies.get(agent_id)

    def get_current_tick(self) -> int:
        """Get current tick number."""
        if self.mode == "live" and self.sim is not None:
            return self.sim.tick
        elif self.mode == "replay" and self.replay is not None:
            return self.replay.current_tick + 1  # 1-indexed for display
        return 0

    def get_total_ticks(self) -> int:
        """Get total ticks (for replay mode timeline)."""
        if self.mode == "replay" and self.replay is not None:
            return self.replay.total_ticks
        return 0

    def get_total_trades(self) -> int:
        """Get cumulative trade count."""
        if self.mode == "live" and self.sim is not None:
            return len(self.sim.trades)
        elif self.mode == "replay" and self.replay is not None:
            state = self.replay.get_state()
            return state.cumulative_trades if state else 0
        return 0

    def get_total_welfare(self) -> float:
        """Get total welfare."""
        if self.mode == "live" and self.sim is not None:
            return self.sim.total_welfare()
        elif self.mode == "replay" and self.replay is not None:
            state = self.replay.get_state()
            return state.total_welfare if state else 0.0
        return 0.0

    def get_welfare_gains(self) -> float:
        """Get welfare gains from initial state."""
        if self.mode == "live" and self.sim is not None:
            return self.sim.welfare_gains()
        elif self.mode == "replay" and self.replay is not None:
            # Calculate from initial welfare
            if self.replay.run.ticks:
                initial = self.replay.run.ticks[0].total_welfare
                state = self.replay.get_state()
                current = state.total_welfare if state else initial
                return current - initial
        return 0.0

    def find_agent_at_canvas(self, x: float, y: float) -> Optional[AgentProxy]:
        """Find agent near canvas coordinates, for hover detection."""
        agent_radius = self.cell_size * 0.35
        for agent in self.get_agents():
            ax, ay = self.grid_to_canvas(agent.position)
            dist = ((x - ax) ** 2 + (y - ay) ** 2) ** 0.5
            if dist <= agent_radius:
                return agent
        return None

    def setup(self) -> None:
        """Set up the DearPyGui context and windows."""
        dpg.create_context()
        dpg.create_viewport(
            title="Microecon Simulation",
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
        )

        # Create main window
        with dpg.window(label="Main", tag="main_window", no_title_bar=True):
            with dpg.group(horizontal=True):
                # Left side: grid canvas
                with dpg.child_window(
                    width=-self.METRICS_PANEL_WIDTH - 10,
                    height=-self.CONTROLS_HEIGHT - 10,
                    no_scrollbar=True,
                    tag="grid_container",
                ):
                    self.drawlist = dpg.add_drawlist(
                        width=800,
                        height=700,
                        tag="grid_drawlist",
                    )

                # Right side: metrics panel
                with dpg.child_window(
                    width=self.METRICS_PANEL_WIDTH,
                    height=-self.CONTROLS_HEIGHT - 10,
                    tag="metrics_panel",
                ):
                    dpg.add_text("Metrics", color=(200, 200, 200))
                    dpg.add_separator()
                    self.tick_text = dpg.add_text("Tick: 0")
                    self.trades_text = dpg.add_text("Trades: 0")
                    self.welfare_text = dpg.add_text("Welfare: 0.0")
                    self.gains_text = dpg.add_text("Gains: 0.0")

                    dpg.add_separator()
                    dpg.add_text("Hovered Agent:", color=(200, 200, 200))
                    dpg.add_separator()
                    self.hover_id_text = dpg.add_text("ID: -")
                    self.hover_alpha_text = dpg.add_text("Alpha: -")
                    self.hover_endow_text = dpg.add_text("Endowment: -")
                    self.hover_utility_text = dpg.add_text("Utility: -")
                    # Belief summary in hover (VIZ-004)
                    self.hover_beliefs_text = dpg.add_text("Beliefs: -")

                    # Belief panel for selected agent (VIZ-005)
                    dpg.add_separator()
                    with dpg.collapsing_header(label="Selected Agent Beliefs", default_open=False, tag="belief_panel_header"):
                        self.belief_panel_agent_text = dpg.add_text("Agent: -")
                        self.belief_panel_price_text = dpg.add_text("Price belief: -")
                        self.belief_panel_memory_text = dpg.add_text("Trades in memory: -")
                        dpg.add_separator()
                        dpg.add_text("Type Beliefs:", color=(180, 180, 180))
                        # Dynamic list of type beliefs (up to 5 shown)
                        self.belief_panel_type_texts = []
                        for i in range(5):
                            txt = dpg.add_text(f"  -")
                            self.belief_panel_type_texts.append(txt)

                    # Overlay toggles section (VIZ-001)
                    dpg.add_separator()
                    with dpg.collapsing_header(label="Overlays", default_open=True):
                        self.overlay_toggle_ids["trails"] = dpg.add_checkbox(
                            label="Movement Trails",
                            default_value=self.overlay_toggles["trails"],
                            callback=self._on_overlay_toggle,
                            user_data="trails",
                        )
                        self.overlay_toggle_ids["perception_selected"] = dpg.add_checkbox(
                            label="Perception (Selected)",
                            default_value=self.overlay_toggles["perception_selected"],
                            callback=self._on_overlay_toggle,
                            user_data="perception_selected",
                        )
                        self.overlay_toggle_ids["perception_all"] = dpg.add_checkbox(
                            label="Perception (All Agents)",
                            default_value=self.overlay_toggles["perception_all"],
                            callback=self._on_overlay_toggle,
                            user_data="perception_all",
                        )
                        self.overlay_toggle_ids["belief_connections"] = dpg.add_checkbox(
                            label="Belief Connections",
                            default_value=self.overlay_toggles["belief_connections"],
                            callback=self._on_overlay_toggle,
                            user_data="belief_connections",
                        )

                    # Trade history panel (VIZ-012 improvement)
                    dpg.add_separator()
                    with dpg.collapsing_header(label="Recent Trades", default_open=True, tag="trade_history_header"):
                        dpg.add_text("Click a trade to view Edgeworth box:", color=(180, 180, 180))
                        # Trade list will be populated dynamically
                        self.trade_list_group = dpg.add_group(tag="trade_list_group")

                    # Export section (VIZ-008 to VIZ-011)
                    dpg.add_separator()
                    with dpg.collapsing_header(label="Export", default_open=False):
                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label="PNG",
                                callback=self._export_png,
                                width=50,
                            )
                            dpg.add_button(
                                label="SVG",
                                callback=self._export_svg,
                                width=50,
                            )
                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label="JSON",
                                callback=self._export_json,
                                width=50,
                            )
                            dpg.add_button(
                                label="CSV",
                                callback=self._export_csv,
                                width=50,
                            )
                        # GIF recording (replay mode)
                        if self.mode == "replay":
                            dpg.add_separator()
                            with dpg.group(horizontal=True):
                                dpg.add_button(
                                    label="Record GIF",
                                    callback=self._start_gif_recording,
                                    width=80,
                                    tag="gif_record_btn",
                                )
                                dpg.add_button(
                                    label="Stop & Save",
                                    callback=self._stop_gif_recording,
                                    width=80,
                                    tag="gif_stop_btn",
                                    enabled=False,
                                )
                        self.export_status_text = dpg.add_text("", color=(150, 200, 150))

                    # Time-series charts
                    dpg.add_separator()
                    self.timeseries_panel = TimeSeriesPanel("metrics_panel")
                    self.timeseries_panel.setup()

                    # In replay mode, preload time-series data
                    if self.mode == "replay" and self.replay is not None:
                        self._load_replay_timeseries()
                        self.timeseries_panel.set_replay_mode(True)

            # Bottom: controls
            with dpg.child_window(
                height=self.CONTROLS_HEIGHT,
                no_scrollbar=True,
                tag="controls_panel",
            ):
                with dpg.group(horizontal=True):
                    # Mode indicator
                    mode_label = "REPLAY" if self.mode == "replay" else "LIVE"
                    mode_color = (100, 200, 100) if self.mode == "live" else (200, 150, 100)
                    self.mode_text = dpg.add_text(f"[{mode_label}]", color=mode_color)
                    dpg.add_text("  ")

                    self.play_button = dpg.add_button(
                        label="Play",
                        callback=self.toggle_play,
                        width=80,
                    )

                    # Step back (replay mode only)
                    if self.mode == "replay":
                        self.step_back_button = dpg.add_button(
                            label="<",
                            callback=self.step_back,
                            width=40,
                        )

                    dpg.add_button(
                        label="Step" if self.mode == "live" else ">",
                        callback=self.step_once,
                        width=80 if self.mode == "live" else 40,
                    )

                    dpg.add_text("  Speed:")
                    self.speed_slider = dpg.add_slider_float(
                        default_value=2.0,
                        min_value=0.5,
                        max_value=10.0,
                        width=150,
                        callback=self.on_speed_change,
                    )
                    dpg.add_text("t/s")

                    # Timeline slider (replay mode only)
                    if self.mode == "replay" and self.replay is not None:
                        dpg.add_text("  Tick:")
                        self.timeline_slider = dpg.add_slider_int(
                            default_value=0,
                            min_value=0,
                            max_value=self.replay.total_ticks - 1,
                            width=200,
                            callback=self.on_timeline_change,
                        )
                        dpg.add_text(f"/{self.replay.total_ticks}")

                    dpg.add_text("  ")
                    dpg.add_button(
                        label="Reset",
                        callback=self.reset_simulation,
                        width=80,
                    )

        dpg.set_primary_window("main_window", True)
        dpg.setup_dearpygui()
        dpg.show_viewport()

    def toggle_play(self) -> None:
        """Toggle play/pause state."""
        self.playing = not self.playing
        dpg.set_item_label(self.play_button, "Pause" if self.playing else "Play")
        if self.playing:
            self.last_tick_time = time.time()

    def step_once(self) -> None:
        """Execute a single step forward."""
        if self.mode == "live" and self.sim is not None:
            trades = self.sim.step()
            self.record_trades(trades)
            self.record_positions()
            self._update_timeseries()
        elif self.mode == "replay" and self.replay is not None:
            self.replay.step()
            self._update_timeline_slider()
            self.record_positions()
            self._update_timeseries()

    def step_back(self) -> None:
        """Step backward one tick (replay mode only)."""
        if self.mode == "replay" and self.replay is not None:
            self.replay.step_back()
            self._update_timeline_slider()
            self._update_timeseries()
            # Clear trails and animations - they would show future state otherwise
            self.position_history.clear()
            self.trade_animations.clear()

    def on_speed_change(self, sender: int, app_data: float) -> None:
        """Handle speed slider change."""
        self.ticks_per_second = app_data

    def _on_overlay_toggle(self, sender: int, app_data: bool, user_data: str) -> None:
        """Handle overlay toggle checkbox change (VIZ-001)."""
        self.overlay_toggles[user_data] = app_data

    def on_timeline_change(self, sender: int, app_data: int) -> None:
        """Handle timeline slider change (replay mode)."""
        if self.mode == "replay" and self.replay is not None:
            self.replay.seek(app_data)
            self._update_timeseries()
            # Clear trails - scrubbing invalidates position history
            self.position_history.clear()
            self.trade_animations.clear()

    def _update_timeline_slider(self) -> None:
        """Update timeline slider to match current tick."""
        if self.mode == "replay" and self.timeline_slider and self.replay is not None:
            dpg.set_value(self.timeline_slider, self.replay.current_tick)

    def _load_replay_timeseries(self) -> None:
        """Load time-series data from replay run."""
        if self.replay is None or self.timeseries_panel is None:
            return

        ticks = []
        welfare = []
        trades = []

        for i, tick_record in enumerate(self.replay.run.ticks):
            ticks.append(i + 1)  # 1-indexed for display
            welfare.append(tick_record.total_welfare)
            trades.append(tick_record.cumulative_trades)

        self.timeseries_panel.load_full_data(ticks, welfare, trades)

    def _update_timeseries(self) -> None:
        """Update time-series panel with current data."""
        if self.timeseries_panel is None:
            return

        if self.mode == "live" and self.sim is not None:
            self.timeseries_panel.record_tick(
                self.sim.tick,
                self.sim.total_welfare(),
                len(self.sim.trades),
            )
        elif self.mode == "replay" and self.replay is not None:
            self.timeseries_panel.seek_to_tick(self.replay.current_tick + 1)

    def reset_simulation(self) -> None:
        """Reset to initial state."""
        self.playing = False
        dpg.set_item_label(self.play_button, "Play")

        if self.mode == "live":
            self.sim = create_simple_economy(
                self.n_agents,
                self.grid_size,
                seed=self.seed,
            )
            if self.timeseries_panel is not None:
                self.timeseries_panel.reset()
        elif self.mode == "replay" and self.replay is not None:
            self.replay.reset()
            self._update_timeline_slider()
            if self.timeseries_panel is not None:
                self.timeseries_panel.seek_to_tick(1)

        self.trade_animations.clear()
        self.position_history.clear()
        self._trade_history.clear()
        self.selected_agent = None

    def record_trades(self, trades: list[TradeEvent]) -> None:
        """Record trades for animation with allocation data for Edgeworth box."""
        current_time = time.time()
        for trade in trades:
            # Get agent data for Edgeworth box
            agent1 = next((a for a in self.sim.agents if a.id == trade.agent1_id), None) if self.sim else None
            agent2 = next((a for a in self.sim.agents if a.id == trade.agent2_id), None) if self.sim else None

            # Extract pre-trade and post-trade allocations from outcome
            # Note: After trade, agent.endowment == outcome.allocation
            # Pre-trade endowments can be computed from total and allocation
            pre_1 = post_1 = pre_2 = post_2 = None
            alpha1 = alpha2 = None

            if hasattr(trade, 'outcome') and trade.outcome is not None:
                outcome = trade.outcome
                post_1 = (outcome.allocation_1.x, outcome.allocation_1.y)
                post_2 = (outcome.allocation_2.x, outcome.allocation_2.y)
                # Pre-trade: total = post_1 + post_2, so we can estimate
                # For now, use gains to estimate utility change
                # Actually, store post allocations and use them for visualization

            if agent1:
                alpha1 = agent1.preferences.alpha
                if post_1 is None:
                    post_1 = (agent1.endowment.x, agent1.endowment.y)
            if agent2:
                alpha2 = agent2.preferences.alpha
                if post_2 is None:
                    post_2 = (agent2.endowment.x, agent2.endowment.y)

            # Estimate pre-trade endowments (before this trade)
            # Since we don't have actual pre-trade data, use current as approximation
            pre_1 = post_1
            pre_2 = post_2

            self.trade_animations.append(TradeAnimation(
                agent1_id=trade.agent1_id,
                agent2_id=trade.agent2_id,
                start_time=current_time,
                pre_endow_1=pre_1,
                pre_endow_2=pre_2,
                post_alloc_1=post_1,
                post_alloc_2=post_2,
                alpha_1=alpha1,
                alpha_2=alpha2,
            ))

            # Store TradeData for persistent history (VIZ-012)
            if alpha1 is not None and alpha2 is not None and post_1 and post_2:
                # Calculate utilities using Cobb-Douglas formula directly
                def cobb_douglas_u(x: float, y: float, alpha: float) -> float:
                    if x <= 0 or y <= 0:
                        return 0.0
                    return (x ** alpha) * (y ** (1 - alpha))

                util1 = cobb_douglas_u(post_1[0], post_1[1], alpha1)
                util2 = cobb_douglas_u(post_2[0], post_2[1], alpha2)

                trade_data = TradeData(
                    agent_a_id=trade.agent1_id,
                    alpha_a=alpha1,
                    endowment_a=pre_1 or post_1,
                    allocation_a=post_1,
                    utility_a_before=util1,  # Approximation
                    utility_a_after=util1,
                    agent_b_id=trade.agent2_id,
                    alpha_b=alpha2,
                    endowment_b=pre_2 or post_2,
                    allocation_b=post_2,
                    utility_b_before=util2,  # Approximation
                    utility_b_after=util2,
                )
                self._trade_history.append(trade_data)
                # Keep only last 20 trades
                if len(self._trade_history) > 20:
                    self._trade_history = self._trade_history[-20:]

    def record_positions(self) -> None:
        """Record current positions for trail rendering."""
        for agent in self.get_agents():
            if agent.id not in self.position_history:
                self.position_history[agent.id] = []
            history = self.position_history[agent.id]
            # Only record if position changed (avoid duplicates when stationary)
            if not history or history[-1] != agent.position:
                history.append(agent.position)
            # Trim to TRAIL_LENGTH
            if len(history) > self.TRAIL_LENGTH:
                self.position_history[agent.id] = history[-self.TRAIL_LENGTH:]

    def update(self) -> None:
        """Update simulation state if playing."""
        if self.playing:
            current_time = time.time()
            tick_interval = 1.0 / self.ticks_per_second

            if current_time - self.last_tick_time >= tick_interval:
                if self.mode == "live" and self.sim is not None:
                    trades = self.sim.step()
                    self.record_trades(trades)
                    self.record_positions()
                    self._update_timeseries()
                elif self.mode == "replay" and self.replay is not None:
                    if not self.replay.at_end:
                        self.replay.step()
                        self._update_timeline_slider()
                        self.record_positions()
                        self._update_timeseries()
                    else:
                        # Stop at end of replay
                        self.playing = False
                        dpg.set_item_label(self.play_button, "Play")

                self.last_tick_time = current_time

        # Clean up expired animations
        current_time = time.time()
        self.trade_animations = [
            anim for anim in self.trade_animations
            if current_time - anim.start_time < anim.duration
        ]

    def update_hover(self) -> None:
        """Update hover state based on mouse position."""
        if not dpg.is_item_hovered("grid_drawlist"):
            self.hovered_agent = None
            return

        mouse_pos = dpg.get_mouse_pos(local=False)
        # Get drawlist position
        dl_pos = dpg.get_item_pos("grid_drawlist")
        local_x = mouse_pos[0] - dl_pos[0]
        local_y = mouse_pos[1] - dl_pos[1]

        self.hovered_agent = self.find_agent_at_canvas(local_x, local_y)

    def update_selection(self) -> None:
        """Handle click on canvas for agent selection (VIZ-012)."""
        # Only process on mouse click
        if not dpg.is_mouse_button_clicked(dpg.mvMouseButton_Left):
            return

        if not dpg.is_item_hovered("grid_drawlist"):
            return

        mouse_pos = dpg.get_mouse_pos(local=False)
        dl_pos = dpg.get_item_pos("grid_drawlist")
        local_x = mouse_pos[0] - dl_pos[0]
        local_y = mouse_pos[1] - dl_pos[1]

        # First check for trade animation clicks (VIZ-012)
        clicked_trade = self._find_trade_at_canvas(local_x, local_y)
        if clicked_trade is not None:
            self._show_edgeworth_box(clicked_trade)
            return

        clicked_agent = self.find_agent_at_canvas(local_x, local_y)

        if clicked_agent is None:
            # Clicked empty space - deselect
            self.selected_agent = None
        elif clicked_agent == self.selected_agent:
            # Clicked same agent - toggle off
            self.selected_agent = None
        else:
            # Clicked new agent - select it
            self.selected_agent = clicked_agent

    def _find_trade_at_canvas(self, x: float, y: float) -> Optional[TradeData]:
        """Find trade animation near canvas coordinates (VIZ-012)."""
        current_time = time.time()

        for anim in self.trade_animations:
            if current_time - anim.start_time > anim.duration:
                continue

            # Check if click is near the trade line
            agent1 = self.get_agent_by_id(anim.agent1_id)
            agent2 = self.get_agent_by_id(anim.agent2_id)
            if agent1 is None or agent2 is None:
                continue

            p1 = self.grid_to_canvas(agent1.position)
            p2 = self.grid_to_canvas(agent2.position)

            # Check if point is close to line segment
            if self._point_near_line(x, y, p1[0], p1[1], p2[0], p2[1], threshold=15):
                # Build TradeData from animation data if available (VIZ-012 fix)
                return self._build_trade_data_from_anim(anim, agent1, agent2)

        return None

    def _build_trade_data_from_anim(
        self, anim: TradeAnimation, agent1: AgentProxy, agent2: AgentProxy
    ) -> TradeData:
        """Build TradeData from animation with stored allocation data."""
        # Use stored allocation data if available
        endow_1 = anim.pre_endow_1 or (agent1.endowment_x, agent1.endowment_y)
        endow_2 = anim.pre_endow_2 or (agent2.endowment_x, agent2.endowment_y)
        alloc_1 = anim.post_alloc_1 or endow_1
        alloc_2 = anim.post_alloc_2 or endow_2
        alpha1 = anim.alpha_1 or agent1.alpha
        alpha2 = anim.alpha_2 or agent2.alpha

        # Compute utilities
        def cobb_douglas_u(x: float, y: float, alpha: float) -> float:
            if x <= 0 or y <= 0:
                return 0.0
            return (x ** alpha) * (y ** (1 - alpha))

        return TradeData(
            agent_a_id=anim.agent1_id,
            alpha_a=alpha1,
            endowment_a=endow_1,
            allocation_a=alloc_1,
            utility_a_before=cobb_douglas_u(endow_1[0], endow_1[1], alpha1),
            utility_a_after=cobb_douglas_u(alloc_1[0], alloc_1[1], alpha1),
            agent_b_id=anim.agent2_id,
            alpha_b=alpha2,
            endowment_b=endow_2,
            allocation_b=alloc_2,
            utility_b_before=cobb_douglas_u(endow_2[0], endow_2[1], alpha2),
            utility_b_after=cobb_douglas_u(alloc_2[0], alloc_2[1], alpha2),
        )

    def _point_near_line(
        self, px: float, py: float,
        x1: float, y1: float, x2: float, y2: float,
        threshold: float = 10,
    ) -> bool:
        """Check if point (px, py) is within threshold of line segment (x1, y1)-(x2, y2)."""
        # Vector from p1 to p2
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq < 1e-6:
            # Line is a point
            return (px - x1) ** 2 + (py - y1) ** 2 <= threshold ** 2

        # Project point onto line, clamp to segment
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))

        # Closest point on segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Distance from point to closest point on segment
        dist_sq = (px - closest_x) ** 2 + (py - closest_y) ** 2
        return dist_sq <= threshold ** 2

    def _build_trade_data(self, agent1_id: str, agent2_id: str) -> Optional[TradeData]:
        """Build TradeData for displaying in Edgeworth box."""
        agent1 = self.get_agent_by_id(agent1_id)
        agent2 = self.get_agent_by_id(agent2_id)
        if agent1 is None or agent2 is None:
            return None

        # For live mode, we have current state but not pre-trade state
        # For replay mode, we can get trade details from the tick record
        tick_record = self._get_current_tick_record()
        if tick_record is not None:
            # Find the trade in the tick record
            for trade in tick_record.trades:
                if (trade.agent1_id == agent1_id and trade.agent2_id == agent2_id) or \
                   (trade.agent1_id == agent2_id and trade.agent2_id == agent1_id):
                    # Found the trade - use its data
                    if trade.agent1_id == agent1_id:
                        return TradeData(
                            agent_a_id=trade.agent1_id,
                            alpha_a=agent1.alpha,
                            endowment_a=trade.pre_endowments[0],
                            allocation_a=trade.post_allocations[0],
                            utility_a_before=trade.pre_endowments[0][0] ** agent1.alpha * trade.pre_endowments[0][1] ** (1 - agent1.alpha),
                            utility_a_after=trade.utilities[0],
                            agent_b_id=trade.agent2_id,
                            alpha_b=agent2.alpha,
                            endowment_b=trade.pre_endowments[1],
                            allocation_b=trade.post_allocations[1],
                            utility_b_before=trade.pre_endowments[1][0] ** agent2.alpha * trade.pre_endowments[1][1] ** (1 - agent2.alpha),
                            utility_b_after=trade.utilities[1],
                        )
                    else:
                        return TradeData(
                            agent_a_id=trade.agent2_id,
                            alpha_a=agent2.alpha,
                            endowment_a=trade.pre_endowments[1],
                            allocation_a=trade.post_allocations[1],
                            utility_a_before=trade.pre_endowments[1][0] ** agent2.alpha * trade.pre_endowments[1][1] ** (1 - agent2.alpha),
                            utility_a_after=trade.utilities[1],
                            agent_b_id=trade.agent1_id,
                            alpha_b=agent1.alpha,
                            endowment_b=trade.pre_endowments[0],
                            allocation_b=trade.post_allocations[0],
                            utility_b_before=trade.pre_endowments[0][0] ** agent1.alpha * trade.pre_endowments[0][1] ** (1 - agent1.alpha),
                            utility_b_after=trade.utilities[0],
                        )

        # Fallback for live mode: use current state as allocation
        return TradeData(
            agent_a_id=agent1_id,
            alpha_a=agent1.alpha,
            endowment_a=(agent1.endowment_x, agent1.endowment_y),
            allocation_a=(agent1.endowment_x, agent1.endowment_y),
            utility_a_before=agent1.utility,
            utility_a_after=agent1.utility,
            agent_b_id=agent2_id,
            alpha_b=agent2.alpha,
            endowment_b=(agent2.endowment_x, agent2.endowment_y),
            allocation_b=(agent2.endowment_x, agent2.endowment_y),
            utility_b_before=agent2.utility,
            utility_b_after=agent2.utility,
        )

    def _show_edgeworth_box(self, trade: TradeData) -> None:
        """Show Edgeworth box popup for a trade (VIZ-013)."""
        if self._edgeworth_popup is None:
            self._edgeworth_popup = EdgeworthBoxPopup()
        self._edgeworth_popup.show(trade)

    def _update_trade_history(self) -> None:
        """Update the trade history panel with recent trades (VIZ-012)."""
        if not dpg.does_item_exist("trade_list_group"):
            return

        # Clear existing trade buttons
        dpg.delete_item("trade_list_group", children_only=True)

        # Use persistent trade history (not animations which expire)
        # Show most recent first, limit to 10
        recent_trades = list(reversed(self._trade_history[-10:]))

        if not recent_trades:
            dpg.add_text("(no recent trades)", parent="trade_list_group", color=(150, 150, 150))
            return

        for i, trade_data in enumerate(recent_trades):
            # Create a clickable trade item
            label = f"{trade_data.agent_a_id[:6]}.. <-> {trade_data.agent_b_id[:6]}.."
            dpg.add_button(
                label=label,
                callback=self._on_trade_history_click,
                user_data=i,
                parent="trade_list_group",
                width=-1,
            )

    def _on_trade_history_click(self, sender: int, app_data: None, user_data: int) -> None:
        """Handle click on trade history item (VIZ-012)."""
        # Get trade directly from history (most recent first)
        recent_trades = list(reversed(self._trade_history[-10:]))
        if user_data >= len(recent_trades):
            return

        trade_data = recent_trades[user_data]
        self._show_edgeworth_box(trade_data)

    def render(self) -> None:
        """Render the current simulation state."""
        # Rebuild agent proxy cache for this frame
        self._build_agent_proxies()

        # Get dimensions from viewport (more reliable with tiling WMs)
        vp_width = dpg.get_viewport_client_width()
        vp_height = dpg.get_viewport_client_height()

        # Calculate grid container size (viewport minus metrics panel and controls)
        width = vp_width - self.METRICS_PANEL_WIDTH - 30
        height = vp_height - self.CONTROLS_HEIGHT - 30

        # Ensure minimum dimensions
        width = max(200, width)
        height = max(200, height)

        # Update drawlist size
        dpg.configure_item(self.drawlist, width=width, height=height)

        # Calculate canvas layout (square, centered)
        self.canvas_size = min(width, height) - 2 * self.GRID_MARGIN
        self.cell_size = self.canvas_size / self.grid_size
        self.canvas_origin = (
            (width - self.canvas_size) / 2,
            (height - self.canvas_size) / 2,
        )

        # Clear and redraw
        dpg.delete_item(self.drawlist, children_only=True)

        self.render_grid()
        self.render_trails()              # Trails behind agents
        self.render_perception_overlay()  # Radius behind agents
        self.render_belief_connections()  # Belief lines behind agents (VIZ-006)
        self.render_trade_animations()
        self.render_agents()
        self.render_metrics()
        self.render_hover_info()
        self.render_belief_panel()        # Belief panel for selected agent (VIZ-005)
        self._update_trade_history()      # Trade history panel (VIZ-012)

    def render_grid(self) -> None:
        """Render the grid lines."""
        ox, oy = self.canvas_origin

        # Draw vertical lines
        for i in range(self.grid_size + 1):
            x = ox + i * self.cell_size
            dpg.draw_line(
                (x, oy),
                (x, oy + self.canvas_size),
                color=self.GRID_LINE_COLOR,
                parent=self.drawlist,
            )

        # Draw horizontal lines
        for i in range(self.grid_size + 1):
            y = oy + i * self.cell_size
            dpg.draw_line(
                (ox, y),
                (ox + self.canvas_size, y),
                color=self.GRID_LINE_COLOR,
                parent=self.drawlist,
            )

    def render_trails(self) -> None:
        """Draw movement trails for all agents (VIZ-002)."""
        if not self.overlay_toggles.get("trails", True):
            return  # Toggle is OFF
        for agent in self.get_agents():
            history = self.position_history.get(agent.id, [])
            if len(history) < 2:
                continue

            # Build point list: history + current (oldest to newest)
            points = history + [agent.position]

            # Draw line segments with fading opacity
            for i in range(len(points) - 1):
                # Fade: oldest segments more transparent
                opacity = int(40 + (i / len(points)) * 80)  # 40 to 120
                p1 = self.grid_to_canvas(points[i])
                p2 = self.grid_to_canvas(points[i + 1])

                # Use agent's color but with reduced opacity
                base_color = alpha_to_color(agent.alpha)
                trail_color = (base_color[0], base_color[1], base_color[2], opacity)

                dpg.draw_line(p1, p2, color=trail_color, thickness=2, parent=self.drawlist)

    def render_perception_overlay(self) -> None:
        """Draw perception radius circles (VIZ-003).

        Supports two modes controlled by toggles:
        - perception_selected: Show radius for selected agent only
        - perception_all: Show radius for all agents
        """
        show_selected = self.overlay_toggles.get("perception_selected", True)
        show_all = self.overlay_toggles.get("perception_all", False)

        if not show_selected and not show_all:
            return  # Both toggles OFF

        agents_to_show = []

        if show_all:
            # Show perception for all agents
            agents_to_show = self.get_agents()
        elif show_selected and self.selected_agent is not None:
            # Only show for selected agent
            current_agent = self.get_agent_by_id(self.selected_agent.id)
            if current_agent is None:
                self.selected_agent = None
                return
            agents_to_show = [current_agent]

        for agent in agents_to_show:
            cx, cy = self.grid_to_canvas(agent.position)
            # Convert perception_radius (grid units) to canvas pixels
            radius_px = agent.perception_radius * self.cell_size

            # Use different opacity when showing all agents (less prominent)
            if show_all and len(agents_to_show) > 1:
                stroke_color = (100, 150, 255, 40)
                fill_color = (100, 150, 255, 15)
            else:
                stroke_color = (100, 150, 255, 60)
                fill_color = (100, 150, 255, 30)

            dpg.draw_circle(
                (cx, cy),
                radius_px,
                color=stroke_color,
                fill=fill_color,
                parent=self.drawlist,
            )

    def render_agents(self) -> None:
        """Render all agents on the grid."""
        # Group agents by position for overlap handling
        agents_by_pos: dict[Position, list[AgentProxy]] = {}
        for agent in self.get_agents():
            if agent.position not in agents_by_pos:
                agents_by_pos[agent.position] = []
            agents_by_pos[agent.position].append(agent)

        agent_radius = self.cell_size * 0.35

        # Check for selected/hovered by ID (since AgentProxy instances change each frame)
        selected_id = self.selected_agent.id if self.selected_agent else None
        hovered_id = self.hovered_agent.id if self.hovered_agent else None

        for pos, agents in agents_by_pos.items():
            cx, cy = self.grid_to_canvas(pos)

            if len(agents) == 1:
                # Single agent: draw at center
                agent = agents[0]
                color = alpha_to_color(agent.alpha)

                # Selection ring (thicker, more prominent)
                if agent.id == selected_id:
                    dpg.draw_circle(
                        (cx, cy),
                        agent_radius + 5,
                        color=(255, 255, 255, 255),
                        thickness=3,
                        parent=self.drawlist,
                    )
                # Hover highlight (thinner)
                elif agent.id == hovered_id:
                    dpg.draw_circle(
                        (cx, cy),
                        agent_radius + 3,
                        color=(255, 255, 255, 200),
                        parent=self.drawlist,
                    )

                dpg.draw_circle(
                    (cx, cy),
                    agent_radius,
                    color=color,
                    fill=color,
                    parent=self.drawlist,
                )
            else:
                # Multiple agents: offset in a circle
                import math
                n = len(agents)
                offset = agent_radius * 0.6
                for i, agent in enumerate(agents):
                    angle = 2 * math.pi * i / n
                    ax = cx + offset * math.cos(angle)
                    ay = cy + offset * math.sin(angle)
                    color = alpha_to_color(agent.alpha)
                    small_radius = agent_radius * 0.7

                    # Selection ring (thicker, more prominent)
                    if agent.id == selected_id:
                        dpg.draw_circle(
                            (ax, ay),
                            small_radius + 4,
                            color=(255, 255, 255, 255),
                            thickness=2,
                            parent=self.drawlist,
                        )
                    # Hover highlight (thinner)
                    elif agent.id == hovered_id:
                        dpg.draw_circle(
                            (ax, ay),
                            small_radius + 3,
                            color=(255, 255, 255, 200),
                            parent=self.drawlist,
                        )

                    dpg.draw_circle(
                        (ax, ay),
                        small_radius,
                        color=color,
                        fill=color,
                        parent=self.drawlist,
                    )

    def render_trade_animations(self) -> None:
        """Render active trade animations."""
        current_time = time.time()

        for anim in self.trade_animations:
            # Find agent positions
            agent1 = self.get_agent_by_id(anim.agent1_id)
            agent2 = self.get_agent_by_id(anim.agent2_id)
            if agent1 is None or agent2 is None:
                continue

            # Calculate fade based on animation progress
            progress = (current_time - anim.start_time) / anim.duration
            opacity = int(255 * (1 - progress))

            # Draw line between agents
            c1 = self.grid_to_canvas(agent1.position)
            c2 = self.grid_to_canvas(agent2.position)

            dpg.draw_line(
                c1, c2,
                color=(255, 200, 0, opacity),
                thickness=3,
                parent=self.drawlist,
            )

            # Draw highlight circles
            radius = self.cell_size * 0.45
            dpg.draw_circle(
                c1,
                radius,
                color=(255, 200, 0, opacity),
                thickness=2,
                parent=self.drawlist,
            )
            dpg.draw_circle(
                c2,
                radius,
                color=(255, 200, 0, opacity),
                thickness=2,
                parent=self.drawlist,
            )

    def render_metrics(self) -> None:
        """Update the metrics panel."""
        dpg.set_value(self.tick_text, f"Tick: {self.get_current_tick()}")
        dpg.set_value(self.trades_text, f"Trades: {self.get_total_trades()}")
        dpg.set_value(self.welfare_text, f"Welfare: {self.get_total_welfare():.1f}")
        dpg.set_value(self.gains_text, f"Gains: {self.get_welfare_gains():.1f}")

    def render_hover_info(self) -> None:
        """Update hover information panel (VIZ-004)."""
        if self.hovered_agent is not None:
            agent = self.hovered_agent
            dpg.set_value(self.hover_id_text, f"ID: {agent.id[:8]}...")
            dpg.set_value(self.hover_alpha_text, f"Alpha: {agent.alpha:.3f}")
            dpg.set_value(
                self.hover_endow_text,
                f"Endowment: ({agent.endowment_x:.1f}, {agent.endowment_y:.1f})"
            )
            dpg.set_value(self.hover_utility_text, f"Utility: {agent.utility:.2f}")
            # Belief summary (VIZ-004)
            belief = self.get_belief_by_id(agent.id)
            if belief and belief.has_beliefs:
                price_info = ""
                if belief.price_belief and belief.price_belief.n_observations > 0:
                    price_info = f", p={belief.price_belief.mean:.2f}"
                dpg.set_value(
                    self.hover_beliefs_text,
                    f"Beliefs: {belief.n_type_beliefs} types, {belief.n_trades_in_memory} mem{price_info}"
                )
            else:
                dpg.set_value(self.hover_beliefs_text, "Beliefs: none")
        else:
            dpg.set_value(self.hover_id_text, "ID: -")
            dpg.set_value(self.hover_alpha_text, "Alpha: -")
            dpg.set_value(self.hover_endow_text, "Endowment: -")
            dpg.set_value(self.hover_utility_text, "Utility: -")
            dpg.set_value(self.hover_beliefs_text, "Beliefs: -")

    def render_belief_panel(self) -> None:
        """Update belief panel for selected agent (VIZ-005)."""
        if self.selected_agent is None:
            dpg.set_value(self.belief_panel_agent_text, "Agent: (none selected)")
            dpg.set_value(self.belief_panel_price_text, "Price belief: -")
            dpg.set_value(self.belief_panel_memory_text, "Trades in memory: -")
            for txt in self.belief_panel_type_texts:
                dpg.set_value(txt, "  -")
            return

        belief = self.get_belief_by_id(self.selected_agent.id)
        dpg.set_value(self.belief_panel_agent_text, f"Agent: {self.selected_agent.id[:8]}...")

        if belief is None or not belief.has_beliefs:
            dpg.set_value(self.belief_panel_price_text, "Price belief: (no beliefs)")
            dpg.set_value(self.belief_panel_memory_text, "Trades in memory: 0")
            for txt in self.belief_panel_type_texts:
                dpg.set_value(txt, "  -")
            return

        # Price belief
        if belief.price_belief and belief.price_belief.n_observations > 0:
            dpg.set_value(
                self.belief_panel_price_text,
                f"Price belief: μ={belief.price_belief.mean:.2f}, σ²={belief.price_belief.variance:.3f}"
            )
        else:
            dpg.set_value(self.belief_panel_price_text, "Price belief: none")

        dpg.set_value(self.belief_panel_memory_text, f"Trades in memory: {belief.n_trades_in_memory}")

        # Type beliefs (show up to 5)
        type_beliefs_sorted = sorted(
            belief.type_beliefs,
            key=lambda tb: tb.confidence,
            reverse=True
        )[:5]

        for i, txt in enumerate(self.belief_panel_type_texts):
            if i < len(type_beliefs_sorted):
                tb = type_beliefs_sorted[i]
                dpg.set_value(
                    txt,
                    f"  {tb.target_agent_id[:6]}: α={tb.believed_alpha:.2f} (c={tb.confidence:.2f})"
                )
            else:
                dpg.set_value(txt, "  -")

    def render_belief_connections(self) -> None:
        """Draw belief connection lines between agents (VIZ-006).

        Lines connect agents who have beliefs about each other.
        Line opacity encodes confidence level.
        """
        if not self.overlay_toggles.get("belief_connections", False):
            return

        # Draw lines for all type beliefs
        for agent_id, belief in self._belief_proxies.items():
            observer = self.get_agent_by_id(agent_id)
            if observer is None:
                continue

            for type_belief in belief.type_beliefs:
                target = self.get_agent_by_id(type_belief.target_agent_id)
                if target is None:
                    continue

                # Draw line with opacity based on confidence
                opacity = int(40 + type_belief.confidence * 160)  # 40-200
                color = (150, 200, 255, opacity)

                p1 = self.grid_to_canvas(observer.position)
                p2 = self.grid_to_canvas(target.position)

                # Line thickness based on confidence
                thickness = 1 + type_belief.confidence * 2  # 1-3

                dpg.draw_line(
                    p1, p2,
                    color=color,
                    thickness=thickness,
                    parent=self.drawlist,
                )

    # ========================================================================
    # Export methods (VIZ-008 to VIZ-011)
    # ========================================================================

    def _export_png(self) -> None:
        """Export current frame as PNG (VIZ-008)."""
        from pathlib import Path
        import time as time_module
        timestamp = time_module.strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"export/screenshot_{timestamp}.png")
        if export_png(output_path):
            dpg.set_value(self.export_status_text, f"Saved: {output_path}")
        else:
            dpg.set_value(self.export_status_text, "PNG export failed")

    def _export_svg(self) -> None:
        """Export current state as SVG (VIZ-009)."""
        from pathlib import Path
        import time as time_module
        timestamp = time_module.strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"export/visualization_{timestamp}.svg")
        config = SVGExportConfig(include_trails=self.overlay_toggles.get("trails", True))
        if export_svg(self, output_path, config):
            dpg.set_value(self.export_status_text, f"Saved: {output_path}")
        else:
            dpg.set_value(self.export_status_text, "SVG export failed")

    def _export_json(self) -> None:
        """Export current tick as JSON (VIZ-011)."""
        from pathlib import Path
        import time as time_module
        tick_record = self._get_current_tick_record()
        if tick_record is None:
            dpg.set_value(self.export_status_text, "No tick data to export")
            return
        timestamp = time_module.strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"export/tick_{tick_record.tick}_{timestamp}.json")
        if export_tick_json(tick_record, output_path):
            dpg.set_value(self.export_status_text, f"Saved: {output_path}")
        else:
            dpg.set_value(self.export_status_text, "JSON export failed")

    def _export_csv(self) -> None:
        """Export current tick agents as CSV (VIZ-011)."""
        from pathlib import Path
        import time as time_module
        tick_record = self._get_current_tick_record()
        if tick_record is None:
            dpg.set_value(self.export_status_text, "No tick data to export")
            return
        timestamp = time_module.strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"export/agents_{tick_record.tick}_{timestamp}.csv")
        if export_agents_csv(tick_record, output_path):
            dpg.set_value(self.export_status_text, f"Saved: {output_path}")
        else:
            dpg.set_value(self.export_status_text, "CSV export failed")

    def _get_current_tick_record(self) -> Optional[TickRecord]:
        """Get current tick record for export."""
        if self.mode == "replay" and self.replay is not None:
            return self.replay.get_state()
        # Live mode doesn't have full tick records, return None
        return None

    def _start_gif_recording(self) -> None:
        """Start GIF recording (VIZ-010)."""
        self._gif_recorder = GIFRecorder()
        self._gif_recording = True
        dpg.configure_item("gif_record_btn", enabled=False)
        dpg.configure_item("gif_stop_btn", enabled=True)
        dpg.set_value(self.export_status_text, "Recording GIF...")

    def _stop_gif_recording(self) -> None:
        """Stop GIF recording and save (VIZ-010)."""
        if self._gif_recorder is None:
            return
        from pathlib import Path
        import time as time_module
        timestamp = time_module.strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"export/animation_{timestamp}.gif")
        config = GIFExportConfig(frame_duration_ms=200)
        if self._gif_recorder.export(output_path, config):
            dpg.set_value(self.export_status_text, f"Saved: {output_path} ({len(self._gif_recorder.frames)} frames)")
        else:
            dpg.set_value(self.export_status_text, "GIF export failed")
        self._gif_recording = False
        self._gif_recorder = None
        dpg.configure_item("gif_record_btn", enabled=True)
        dpg.configure_item("gif_stop_btn", enabled=False)

    def run(self) -> None:
        """Main application loop."""
        self.setup()

        while dpg.is_dearpygui_running():
            self.update()
            self.update_hover()
            self.update_selection()
            self.render()
            dpg.render_dearpygui_frame()

            # Capture frame for GIF if recording (VIZ-010)
            if self._gif_recording and self._gif_recorder is not None:
                self._gif_recorder.capture_frame()

        dpg.destroy_context()


# ============================================================================
# Dual viewport visualization for side-by-side comparison
# ============================================================================

class DualVisualizationApp:
    """
    Dual viewport visualization for comparing two simulation runs.

    Shows two grids side-by-side with synchronized playback and
    comparison metrics. Useful for comparing Nash vs Rubinstein
    bargaining protocols with the same initial conditions.
    """

    # Layout constants
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 850
    METRICS_PANEL_WIDTH = 240
    CONTROLS_HEIGHT = 120  # Increased to fit timeline markers
    GRID_MARGIN = 15
    TIMELINE_HEIGHT = 30

    # Colors
    GRID_LINE_COLOR = (200, 200, 200, 100)
    BACKGROUND_COLOR = (30, 30, 30, 255)
    TRADE_LINE_COLOR = (255, 200, 0, 255)

    def __init__(
        self,
        run_a: RunData,
        run_b: RunData,
        label_a: str = "Run A",
        label_b: str = "Run B",
    ):
        """
        Initialize dual visualization.

        Args:
            run_a: First run data (left viewport)
            run_b: Second run data (right viewport)
            label_a: Label for first run (e.g., "Nash")
            label_b: Label for second run (e.g., "Rubinstein")
        """
        from microecon.visualization.replay import DualReplayController

        self.label_a = label_a
        self.label_b = label_b

        # Validate grid sizes match
        if run_a.config.grid_size != run_b.config.grid_size:
            raise ValueError(
                f"Grid sizes must match for dual comparison. "
                f"{label_a} has grid_size={run_a.config.grid_size}, "
                f"{label_b} has grid_size={run_b.config.grid_size}."
            )
        self.grid_size = run_a.config.grid_size

        # Create dual replay controller
        self.controller = DualReplayController(run_a, run_b, synced=True)

        # Playback state
        self.playing = False
        self.ticks_per_second = 2.0
        self.last_tick_time = 0.0

        # UI element references
        self.drawlist_a: int = 0
        self.drawlist_b: int = 0
        self.tick_text: int = 0
        self.play_button: int = 0
        self.timeline_slider: int = 0

        # Metrics text elements
        self.welfare_a_text: int = 0
        self.welfare_b_text: int = 0
        self.trades_a_text: int = 0
        self.trades_b_text: int = 0
        self.welfare_diff_text: int = 0
        self.trades_diff_text: int = 0

        # Rendering state (per viewport)
        self.canvas_size = 0.0
        self.cell_size = 0.0

        # Agent caches
        self._agents_a: list[AgentProxy] = []
        self._agents_b: list[AgentProxy] = []
        self._agents_a_by_id: dict[str, AgentProxy] = {}
        self._agents_b_by_id: dict[str, AgentProxy] = {}

        # Trade animations (one list per viewport)
        self.trade_animations_a: list[TradeAnimation] = []
        self.trade_animations_b: list[TradeAnimation] = []

        # Movement trails (one dict per viewport)
        self.position_history_a: dict[str, list[Position]] = {}
        self.position_history_b: dict[str, list[Position]] = {}
        self.TRAIL_LENGTH = 5

        # Track last tick to detect when we've stepped
        self._last_tick = -1

        # Precompute event ticks for timeline markers
        self.events_a = self._precompute_events(run_a)
        self.events_b = self._precompute_events(run_b)

        # Overlay toggle state (VIZ-001, VIZ-002, VIZ-003)
        self.overlay_toggles: dict[str, bool] = {
            "trails": True,  # Default ON for backward compatibility
        }
        # UI element references for toggles
        self.overlay_toggle_ids: dict[str, int] = {}

        # Timeline drawlist reference
        self.timeline_drawlist: int = 0
        self.timeline_width = 400  # Will be updated in render

        # Time-series panel for comparison (initialized in setup)
        self.timeseries_panel: Optional[DualTimeSeriesPanel] = None

        # Store run data for time-series loading
        self._run_a = run_a
        self._run_b = run_b

    @staticmethod
    def _precompute_events(run_data: RunData) -> dict[str, list[int]]:
        """Precompute which ticks have trades and commitment events.

        Returns dict with 'trades', 'commitments_formed', 'commitments_broken'
        keys, each containing list of tick indices.
        """
        events: dict[str, list[int]] = {
            'trades': [],
            'commitments_formed': [],
            'commitments_broken': [],
        }

        for i, tick in enumerate(run_data.ticks):
            if tick.trades:
                # Only count ticks with actual trades (trade_occurred=True)
                if any(t.trade_occurred for t in tick.trades):
                    events['trades'].append(i)
            if tick.commitments_formed:
                events['commitments_formed'].append(i)
            if tick.commitments_broken:
                events['commitments_broken'].append(i)

        return events

    def _build_agent_proxies(self) -> None:
        """Rebuild agent proxy caches for both runs."""
        self._agents_a = []
        self._agents_b = []
        self._agents_a_by_id = {}
        self._agents_b_by_id = {}

        state_a, state_b = self.controller.get_states()

        if state_a is not None:
            perception_radius = self.controller.replay_a.run.config.perception_radius
            for snapshot in state_a.agent_snapshots:
                proxy = AgentProxy.from_snapshot(snapshot, perception_radius)
                self._agents_a.append(proxy)
                self._agents_a_by_id[proxy.id] = proxy

        if state_b is not None:
            perception_radius = self.controller.replay_b.run.config.perception_radius
            for snapshot in state_b.agent_snapshots:
                proxy = AgentProxy.from_snapshot(snapshot, perception_radius)
                self._agents_b.append(proxy)
                self._agents_b_by_id[proxy.id] = proxy

    def setup(self) -> None:
        """Set up the DearPyGui context and windows."""
        dpg.create_context()
        dpg.create_viewport(
            title=f"Comparison: {self.label_a} vs {self.label_b}",
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
        )

        # Create main window
        with dpg.window(label="Main", tag="main_window", no_title_bar=True):
            # Top row: two grids side by side with metrics
            with dpg.group(horizontal=True):
                # Left viewport
                with dpg.child_window(
                    width=-self.METRICS_PANEL_WIDTH - 10,
                    height=-self.CONTROLS_HEIGHT - 10,
                    no_scrollbar=True,
                    tag="grids_container",
                ):
                    with dpg.group(horizontal=True):
                        # Grid A
                        with dpg.group():
                            dpg.add_text(self.label_a, color=(100, 200, 100))
                            self.drawlist_a = dpg.add_drawlist(
                                width=400,
                                height=500,
                                tag="grid_drawlist_a",
                            )

                        dpg.add_spacer(width=20)

                        # Grid B
                        with dpg.group():
                            dpg.add_text(self.label_b, color=(200, 150, 100))
                            self.drawlist_b = dpg.add_drawlist(
                                width=400,
                                height=500,
                                tag="grid_drawlist_b",
                            )

                # Right side: comparison metrics
                with dpg.child_window(
                    width=self.METRICS_PANEL_WIDTH,
                    height=-self.CONTROLS_HEIGHT - 10,
                    tag="metrics_panel",
                ):
                    dpg.add_text("Comparison", color=(200, 200, 200))
                    dpg.add_separator()

                    self.tick_text = dpg.add_text("Tick: 0 / 0")
                    dpg.add_separator()

                    # Run A metrics
                    dpg.add_text(f"{self.label_a}:", color=(100, 200, 100))
                    self.welfare_a_text = dpg.add_text("  Welfare: 0.0")
                    self.trades_a_text = dpg.add_text("  Trades: 0")

                    dpg.add_separator()

                    # Run B metrics
                    dpg.add_text(f"{self.label_b}:", color=(200, 150, 100))
                    self.welfare_b_text = dpg.add_text("  Welfare: 0.0")
                    self.trades_b_text = dpg.add_text("  Trades: 0")

                    dpg.add_separator()

                    # Difference metrics
                    dpg.add_text("Difference:", color=(200, 200, 200))
                    self.welfare_diff_text = dpg.add_text("  Welfare: +0.0")
                    self.trades_diff_text = dpg.add_text("  Trades: +0")

                    # Overlay toggles section (VIZ-001)
                    dpg.add_separator()
                    with dpg.collapsing_header(label="Overlays", default_open=True):
                        self.overlay_toggle_ids["trails"] = dpg.add_checkbox(
                            label="Movement Trails",
                            default_value=self.overlay_toggles["trails"],
                            callback=self._on_overlay_toggle,
                            user_data="trails",
                        )

                    # Time-series charts for comparison
                    dpg.add_separator()
                    self.timeseries_panel = DualTimeSeriesPanel(
                        "metrics_panel",
                        label_a=self.label_a,
                        label_b=self.label_b,
                    )
                    self.timeseries_panel.setup()
                    self._load_timeseries_data()

            # Bottom: controls
            with dpg.child_window(
                height=self.CONTROLS_HEIGHT,
                no_scrollbar=True,
                tag="controls_panel",
            ):
                # Timeline with event markers
                with dpg.group(horizontal=True):
                    dpg.add_text("Timeline: ", color=(150, 150, 150))
                    self.timeline_drawlist = dpg.add_drawlist(
                        width=600,
                        height=self.TIMELINE_HEIGHT,
                        tag="timeline_drawlist",
                    )
                    dpg.add_text("  ")
                    # Legend
                    dpg.add_text("T", color=(255, 200, 0))
                    dpg.add_text("=Trade ", color=(150, 150, 150))
                    dpg.add_text("C", color=(100, 200, 100))
                    dpg.add_text("=Commit ", color=(150, 150, 150))

                dpg.add_spacer(height=5)

                with dpg.group(horizontal=True):
                    dpg.add_text("[COMPARISON]", color=(150, 150, 255))
                    dpg.add_text("  ")

                    self.play_button = dpg.add_button(
                        label="Play",
                        callback=self.toggle_play,
                        width=80,
                    )

                    dpg.add_button(
                        label="<",
                        callback=self.step_back,
                        width=40,
                    )

                    dpg.add_button(
                        label=">",
                        callback=self.step_forward,
                        width=40,
                    )

                    dpg.add_text("  Speed:")
                    dpg.add_slider_float(
                        default_value=2.0,
                        min_value=0.5,
                        max_value=10.0,
                        width=120,
                        callback=self.on_speed_change,
                    )
                    dpg.add_text("t/s")

                    dpg.add_text("  Tick:")
                    self.timeline_slider = dpg.add_slider_int(
                        default_value=0,
                        min_value=0,
                        max_value=self.controller.total_ticks - 1,
                        width=200,
                        callback=self.on_timeline_change,
                    )
                    dpg.add_text(f"/{self.controller.total_ticks}")

                    dpg.add_text("  ")
                    dpg.add_button(
                        label="Reset",
                        callback=self.reset,
                        width=80,
                    )

        dpg.set_primary_window("main_window", True)
        dpg.setup_dearpygui()
        dpg.show_viewport()

    def toggle_play(self) -> None:
        """Toggle play/pause."""
        self.playing = not self.playing
        dpg.set_item_label(self.play_button, "Pause" if self.playing else "Play")
        if self.playing:
            self.last_tick_time = time.time()

    def step_forward(self) -> None:
        """Step forward one tick."""
        self.controller.step()
        self._update_timeline_slider()
        self._update_timeseries()
        self._on_tick_changed()

    def step_back(self) -> None:
        """Step backward one tick."""
        self.controller.step_back()
        self._update_timeline_slider()
        self._update_timeseries()
        # Clear trails and animations when going backwards
        self.position_history_a.clear()
        self.position_history_b.clear()
        self.trade_animations_a.clear()
        self.trade_animations_b.clear()

    def on_speed_change(self, sender: int, app_data: float) -> None:
        """Handle speed slider change."""
        self.ticks_per_second = app_data

    def _on_overlay_toggle(self, sender: int, app_data: bool, user_data: str) -> None:
        """Handle overlay toggle checkbox change (VIZ-001)."""
        self.overlay_toggles[user_data] = app_data

    def on_timeline_change(self, sender: int, app_data: int) -> None:
        """Handle timeline slider change."""
        self.controller.seek(app_data)
        self._update_timeseries()
        # Clear trails and animations when scrubbing
        self.position_history_a.clear()
        self.position_history_b.clear()
        self.trade_animations_a.clear()
        self.trade_animations_b.clear()

    def _update_timeline_slider(self) -> None:
        """Update timeline slider to match current tick."""
        if self.timeline_slider:
            dpg.set_value(self.timeline_slider, self.controller.current_tick)

    def _load_timeseries_data(self) -> None:
        """Load time-series data for both runs."""
        if self.timeseries_panel is None:
            return

        # Extract data from both runs
        ticks = []
        welfare_a = []
        welfare_b = []
        trades_a = []
        trades_b = []

        # Use the shorter run length
        min_len = min(len(self._run_a.ticks), len(self._run_b.ticks))

        for i in range(min_len):
            ticks.append(i + 1)  # 1-indexed for display
            welfare_a.append(self._run_a.ticks[i].total_welfare)
            welfare_b.append(self._run_b.ticks[i].total_welfare)
            trades_a.append(self._run_a.ticks[i].cumulative_trades)
            trades_b.append(self._run_b.ticks[i].cumulative_trades)

        self.timeseries_panel.load_data(ticks, welfare_a, welfare_b, trades_a, trades_b)

    def _update_timeseries(self) -> None:
        """Update time-series playhead position."""
        if self.timeseries_panel is not None:
            self.timeseries_panel.seek_to_tick(self.controller.current_tick + 1)

    def reset(self) -> None:
        """Reset to first tick."""
        self.playing = False
        dpg.set_item_label(self.play_button, "Play")
        self.controller.reset()
        self._update_timeline_slider()
        self._update_timeseries()
        # Clear trails and animations
        self.position_history_a.clear()
        self.position_history_b.clear()
        self.trade_animations_a.clear()
        self.trade_animations_b.clear()
        self._last_tick = -1

    def _on_tick_changed(self) -> None:
        """Handle tick advancement - detect trades and record positions."""
        current_tick = self.controller.current_tick
        if current_tick == self._last_tick:
            return
        self._last_tick = current_tick

        state_a, state_b = self.controller.get_states()
        current_time = time.time()

        # Record trades for animations
        if state_a is not None:
            for trade in state_a.trades:
                if trade.trade_occurred:
                    self.trade_animations_a.append(TradeAnimation(
                        agent1_id=trade.agent1_id,
                        agent2_id=trade.agent2_id,
                        start_time=current_time,
                    ))

        if state_b is not None:
            for trade in state_b.trades:
                if trade.trade_occurred:
                    self.trade_animations_b.append(TradeAnimation(
                        agent1_id=trade.agent1_id,
                        agent2_id=trade.agent2_id,
                        start_time=current_time,
                    ))

        # Record positions for trails (need to rebuild proxies first)
        self._build_agent_proxies()

        for agent in self._agents_a:
            if agent.id not in self.position_history_a:
                self.position_history_a[agent.id] = []
            history = self.position_history_a[agent.id]
            if not history or history[-1] != agent.position:
                history.append(agent.position)
            if len(history) > self.TRAIL_LENGTH:
                self.position_history_a[agent.id] = history[-self.TRAIL_LENGTH:]

        for agent in self._agents_b:
            if agent.id not in self.position_history_b:
                self.position_history_b[agent.id] = []
            history = self.position_history_b[agent.id]
            if not history or history[-1] != agent.position:
                history.append(agent.position)
            if len(history) > self.TRAIL_LENGTH:
                self.position_history_b[agent.id] = history[-self.TRAIL_LENGTH:]

    def update(self) -> None:
        """Update playback state."""
        if self.playing:
            current_time = time.time()
            tick_interval = 1.0 / self.ticks_per_second

            if current_time - self.last_tick_time >= tick_interval:
                if not self.controller.at_end:
                    self.controller.step()
                    self._update_timeline_slider()
                    self._on_tick_changed()
                else:
                    self.playing = False
                    dpg.set_item_label(self.play_button, "Play")

                self.last_tick_time = current_time

        # Clean up expired animations
        current_time = time.time()
        self.trade_animations_a = [
            anim for anim in self.trade_animations_a
            if current_time - anim.start_time < anim.duration
        ]
        self.trade_animations_b = [
            anim for anim in self.trade_animations_b
            if current_time - anim.start_time < anim.duration
        ]

    def grid_to_canvas(self, pos: Position, origin: tuple[float, float]) -> tuple[float, float]:
        """Convert grid position to canvas coordinates."""
        x = origin[0] + (pos.col + 0.5) * self.cell_size
        y = origin[1] + (pos.row + 0.5) * self.cell_size
        return (x, y)

    def render(self) -> None:
        """Render both viewports."""
        self._build_agent_proxies()

        # Get viewport dimensions
        vp_width = dpg.get_viewport_client_width()
        vp_height = dpg.get_viewport_client_height()

        # Calculate grid sizes (two grids side by side)
        available_width = vp_width - self.METRICS_PANEL_WIDTH - 60
        grid_width = (available_width - 20) // 2  # 20px gap between grids
        grid_height = vp_height - self.CONTROLS_HEIGHT - 60

        # Ensure minimum and square
        grid_size = min(grid_width, grid_height, 500)
        grid_size = max(200, grid_size)

        # Update drawlist sizes
        dpg.configure_item(self.drawlist_a, width=grid_size, height=grid_size)
        dpg.configure_item(self.drawlist_b, width=grid_size, height=grid_size)

        # Calculate cell size
        self.canvas_size = grid_size - 2 * self.GRID_MARGIN
        self.cell_size = self.canvas_size / self.grid_size

        # Render both grids
        origin = (self.GRID_MARGIN, self.GRID_MARGIN)
        self._render_grid(
            self.drawlist_a, origin, self._agents_a,
            self.position_history_a, self.trade_animations_a,
            self._agents_a_by_id
        )
        self._render_grid(
            self.drawlist_b, origin, self._agents_b,
            self.position_history_b, self.trade_animations_b,
            self._agents_b_by_id
        )

        # Render metrics
        self._render_metrics()

        # Render timeline with event markers
        self._render_timeline()

    def _render_grid(
        self,
        drawlist: int,
        origin: tuple[float, float],
        agents: list[AgentProxy],
        position_history: dict[str, list[Position]],
        trade_animations: list[TradeAnimation],
        agents_by_id: dict[str, AgentProxy],
    ) -> None:
        """Render a single grid viewport with trails and trade animations."""
        dpg.delete_item(drawlist, children_only=True)

        ox, oy = origin

        # Draw grid lines
        for i in range(self.grid_size + 1):
            x = ox + i * self.cell_size
            dpg.draw_line(
                (x, oy),
                (x, oy + self.canvas_size),
                color=self.GRID_LINE_COLOR,
                parent=drawlist,
            )

        for i in range(self.grid_size + 1):
            y = oy + i * self.cell_size
            dpg.draw_line(
                (ox, y),
                (ox + self.canvas_size, y),
                color=self.GRID_LINE_COLOR,
                parent=drawlist,
            )

        # Draw movement trails (behind agents) - VIZ-002
        if self.overlay_toggles.get("trails", True):
            for agent in agents:
                history = position_history.get(agent.id, [])
                if len(history) < 2:
                    continue

                # Build point list: history + current (oldest to newest)
                points = history + [agent.position]

                # Draw line segments with fading opacity
                for i in range(len(points) - 1):
                    opacity = int(40 + (i / len(points)) * 80)  # 40 to 120
                    p1 = self.grid_to_canvas(points[i], origin)
                    p2 = self.grid_to_canvas(points[i + 1], origin)

                    base_color = alpha_to_color(agent.alpha)
                    trail_color = (base_color[0], base_color[1], base_color[2], opacity)

                    dpg.draw_line(p1, p2, color=trail_color, thickness=2, parent=drawlist)

        # Draw trade animations
        current_time = time.time()
        for anim in trade_animations:
            agent1 = agents_by_id.get(anim.agent1_id)
            agent2 = agents_by_id.get(anim.agent2_id)
            if agent1 is None or agent2 is None:
                continue

            progress = (current_time - anim.start_time) / anim.duration
            opacity = int(255 * (1 - progress))

            c1 = self.grid_to_canvas(agent1.position, origin)
            c2 = self.grid_to_canvas(agent2.position, origin)

            dpg.draw_line(
                c1, c2,
                color=(255, 200, 0, opacity),
                thickness=3,
                parent=drawlist,
            )

            # Draw highlight circles
            radius = self.cell_size * 0.45
            dpg.draw_circle(
                c1, radius,
                color=(255, 200, 0, opacity),
                thickness=2,
                parent=drawlist,
            )
            dpg.draw_circle(
                c2, radius,
                color=(255, 200, 0, opacity),
                thickness=2,
                parent=drawlist,
            )

        # Draw agents
        agent_radius = self.cell_size * 0.35

        # Group by position for overlap handling
        agents_by_pos: dict[Position, list[AgentProxy]] = {}
        for agent in agents:
            if agent.position not in agents_by_pos:
                agents_by_pos[agent.position] = []
            agents_by_pos[agent.position].append(agent)

        for pos, pos_agents in agents_by_pos.items():
            cx, cy = self.grid_to_canvas(pos, origin)

            if len(pos_agents) == 1:
                agent = pos_agents[0]
                color = alpha_to_color(agent.alpha)
                dpg.draw_circle(
                    (cx, cy),
                    agent_radius,
                    color=color,
                    fill=color,
                    parent=drawlist,
                )
            else:
                import math
                n = len(pos_agents)
                offset = agent_radius * 0.6
                for i, agent in enumerate(pos_agents):
                    angle = 2 * math.pi * i / n
                    ax = cx + offset * math.cos(angle)
                    ay = cy + offset * math.sin(angle)
                    color = alpha_to_color(agent.alpha)
                    small_radius = agent_radius * 0.7
                    dpg.draw_circle(
                        (ax, ay),
                        small_radius,
                        color=color,
                        fill=color,
                        parent=drawlist,
                    )

    def _render_metrics(self) -> None:
        """Update the metrics panel."""
        state_a, state_b = self.controller.get_states()

        # Tick counter
        dpg.set_value(
            self.tick_text,
            f"Tick: {self.controller.current_tick + 1} / {self.controller.total_ticks}"
        )

        # Individual metrics
        welfare_a = state_a.total_welfare if state_a else 0.0
        welfare_b = state_b.total_welfare if state_b else 0.0
        trades_a = state_a.cumulative_trades if state_a else 0
        trades_b = state_b.cumulative_trades if state_b else 0

        dpg.set_value(self.welfare_a_text, f"  Welfare: {welfare_a:.1f}")
        dpg.set_value(self.trades_a_text, f"  Trades: {trades_a}")
        dpg.set_value(self.welfare_b_text, f"  Welfare: {welfare_b:.1f}")
        dpg.set_value(self.trades_b_text, f"  Trades: {trades_b}")

        # Differences (B - A)
        welfare_diff = welfare_b - welfare_a
        trades_diff = trades_b - trades_a

        welfare_sign = "+" if welfare_diff >= 0 else ""
        trades_sign = "+" if trades_diff >= 0 else ""

        dpg.set_value(self.welfare_diff_text, f"  Welfare: {welfare_sign}{welfare_diff:.1f}")
        dpg.set_value(self.trades_diff_text, f"  Trades: {trades_sign}{trades_diff}")

    def _render_timeline(self) -> None:
        """Render timeline with event markers for both runs."""
        if not self.timeline_drawlist:
            return

        dpg.delete_item(self.timeline_drawlist, children_only=True)

        # Get drawlist dimensions
        width = dpg.get_item_width(self.timeline_drawlist)
        height = self.TIMELINE_HEIGHT

        # Track dimensions (with padding)
        padding = 10
        track_width = width - 2 * padding
        track_y_a = 8   # Run A track (top)
        track_y_b = 22  # Run B track (bottom)
        track_height = 6

        total_ticks = self.controller.total_ticks
        if total_ticks <= 1:
            return

        # Helper to convert tick to x position
        def tick_to_x(tick: int) -> float:
            return padding + (tick / (total_ticks - 1)) * track_width

        # Draw track backgrounds
        track_bg_color = (60, 60, 60, 255)
        dpg.draw_rectangle(
            (padding, track_y_a - track_height // 2),
            (padding + track_width, track_y_a + track_height // 2),
            color=track_bg_color,
            fill=track_bg_color,
            parent=self.timeline_drawlist,
        )
        dpg.draw_rectangle(
            (padding, track_y_b - track_height // 2),
            (padding + track_width, track_y_b + track_height // 2),
            color=track_bg_color,
            fill=track_bg_color,
            parent=self.timeline_drawlist,
        )

        # Draw run labels
        dpg.draw_text(
            (2, track_y_a - 4),
            "A",
            color=(100, 200, 100, 200),
            size=10,
            parent=self.timeline_drawlist,
        )
        dpg.draw_text(
            (2, track_y_b - 4),
            "B",
            color=(200, 150, 100, 200),
            size=10,
            parent=self.timeline_drawlist,
        )

        # Colors for events
        trade_color = (255, 200, 0, 255)       # Yellow for trades
        commit_color = (100, 200, 100, 255)   # Green for commitments

        # Draw event markers for Run A
        for tick in self.events_a['trades']:
            x = tick_to_x(tick)
            dpg.draw_circle(
                (x, track_y_a),
                3,
                color=trade_color,
                fill=trade_color,
                parent=self.timeline_drawlist,
            )

        for tick in self.events_a['commitments_formed']:
            x = tick_to_x(tick)
            # Draw small diamond for commitment
            dpg.draw_polygon(
                [(x, track_y_a - 3), (x + 2, track_y_a), (x, track_y_a + 3), (x - 2, track_y_a)],
                color=commit_color,
                fill=commit_color,
                parent=self.timeline_drawlist,
            )

        # Draw event markers for Run B
        for tick in self.events_b['trades']:
            x = tick_to_x(tick)
            dpg.draw_circle(
                (x, track_y_b),
                3,
                color=trade_color,
                fill=trade_color,
                parent=self.timeline_drawlist,
            )

        for tick in self.events_b['commitments_formed']:
            x = tick_to_x(tick)
            dpg.draw_polygon(
                [(x, track_y_b - 3), (x + 2, track_y_b), (x, track_y_b + 3), (x - 2, track_y_b)],
                color=commit_color,
                fill=commit_color,
                parent=self.timeline_drawlist,
            )

        # Draw playhead (current position)
        current_x = tick_to_x(self.controller.current_tick)
        playhead_color = (255, 255, 255, 255)
        # Vertical line spanning both tracks
        dpg.draw_line(
            (current_x, 2),
            (current_x, height - 2),
            color=playhead_color,
            thickness=2,
            parent=self.timeline_drawlist,
        )

    def run(self) -> None:
        """Main application loop."""
        self.setup()

        while dpg.is_dearpygui_running():
            self.update()
            self.render()
            dpg.render_dearpygui_frame()

        dpg.destroy_context()


def run_visualization(
    n_agents: int = 10,
    grid_size: int = 15,
    seed: int | None = None,
) -> None:
    """
    Launch the visualization window in live mode.

    Args:
        n_agents: Number of agents in the simulation
        grid_size: Size of the grid (NxN)
        seed: Random seed for reproducibility
    """
    app = VisualizationApp(n_agents=n_agents, grid_size=grid_size, seed=seed, mode="live")
    app.run()


def run_replay(run_data: RunData) -> None:
    """
    Launch the visualization window in replay mode.

    Args:
        run_data: Logged run data to replay
    """
    app = VisualizationApp(mode="replay", run_data=run_data)
    app.run()


def run_replay_from_path(path: Path | str) -> None:
    """
    Launch the visualization window in replay mode from a log directory.

    Args:
        path: Path to the run directory containing config.json and ticks.jsonl
    """
    from microecon.logging import load_run

    if isinstance(path, str):
        path = Path(path)
    run_data = load_run(path)
    run_replay(run_data)


def run_comparison(
    run_a: RunData,
    run_b: RunData,
    label_a: str = "Run A",
    label_b: str = "Run B",
) -> None:
    """
    Launch dual viewport comparison of two runs.

    Args:
        run_a: First run data (left viewport)
        run_b: Second run data (right viewport)
        label_a: Label for first run
        label_b: Label for second run
    """
    app = DualVisualizationApp(run_a, run_b, label_a, label_b)
    app.run()


def run_comparison_from_paths(
    path_a: Path | str,
    path_b: Path | str,
    label_a: str = "Run A",
    label_b: str = "Run B",
) -> None:
    """
    Launch dual viewport comparison from log directories.

    Args:
        path_a: Path to first run directory
        path_b: Path to second run directory
        label_a: Label for first run
        label_b: Label for second run
    """
    from microecon.logging import load_run

    if isinstance(path_a, str):
        path_a = Path(path_a)
    if isinstance(path_b, str):
        path_b = Path(path_b)

    run_a = load_run(path_a)
    run_b = load_run(path_b)
    run_comparison(run_a, run_b, label_a, label_b)


def run_protocol_comparison(
    n_agents: int = 10,
    grid_size: int = 15,
    ticks: int = 100,
    seed: int = 42,
) -> None:
    """
    Run Nash vs Rubinstein comparison with same initial conditions.

    Convenience function that runs both protocols and launches
    the dual viewport comparison.

    Args:
        n_agents: Number of agents
        grid_size: Size of the grid
        ticks: Number of simulation ticks
        seed: Random seed (same for both runs)
    """
    from microecon.batch import run_comparison as batch_comparison
    from microecon.analysis import pair_runs_by_seed

    # Run both protocols
    results = batch_comparison(
        n_agents=n_agents,
        grid_size=grid_size,
        ticks=ticks,
        seeds=[seed],
    )

    # Get run data
    runs = [r.run_data for r in results if r.run_data is not None]

    # Pair by seed
    pairs = pair_runs_by_seed(runs, "nash", "rubinstein")

    if pairs:
        nash_run, rubinstein_run = pairs[0]
        run_comparison(nash_run, rubinstein_run, "Nash", "Rubinstein")
    else:
        raise ValueError("Could not pair runs by protocol")


def run_matching_protocol_comparison(
    n_agents: int = 10,
    grid_size: int = 15,
    ticks: int = 100,
    seed: int = 42,
) -> None:
    """
    Run Opportunistic vs StableRoommates comparison with same initial conditions.

    Convenience function that runs both matching protocols and launches
    the dual viewport comparison. Uses Nash bargaining for both.

    Args:
        n_agents: Number of agents
        grid_size: Size of the grid
        ticks: Number of simulation ticks
        seed: Random seed (same for both runs)
    """
    from microecon.batch import run_matching_comparison as batch_matching_comparison

    # Run both matching protocols
    results = batch_matching_comparison(
        n_agents=n_agents,
        grid_size=grid_size,
        ticks=ticks,
        seeds=[seed],
    )

    # Get run data (results alternate: opportunistic, stable_roommates)
    runs = [r.run_data for r in results if r.run_data is not None]

    if len(runs) >= 2:
        # First run is opportunistic, second is stable_roommates
        run_comparison(runs[0], runs[1], "Opportunistic", "StableRoommates")
    else:
        raise ValueError("Could not get both matching protocol runs")


# Allow running as: python -m microecon.visualization.app
if __name__ == "__main__":
    run_visualization()
