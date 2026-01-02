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
from microecon.visualization.replay import ReplayController


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
# Trade animation tracking
# ============================================================================

@dataclass
class TradeAnimation:
    """Track a trade animation in progress."""
    agent1_id: str
    agent2_id: str
    start_time: float
    duration: float = 0.5


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
    WINDOW_HEIGHT = 800
    METRICS_PANEL_WIDTH = 200
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

        if self.mode == "live" and self.sim is not None:
            for agent in self.sim.agents:
                pos = self.sim.grid.get_position(agent)
                if pos is not None:
                    proxy = AgentProxy.from_agent(agent, pos)
                    self._agent_proxies.append(proxy)
                    self._agents_by_id[proxy.id] = proxy
        elif self.mode == "replay" and self.replay is not None:
            state = self.replay.get_state()
            if state is not None:
                # Get perception radius from config if available
                perception_radius = self.replay.run.config.perception_radius
                for snapshot in state.agent_snapshots:
                    proxy = AgentProxy.from_snapshot(snapshot, perception_radius)
                    self._agent_proxies.append(proxy)
                    self._agents_by_id[proxy.id] = proxy

    def get_agents(self) -> list[AgentProxy]:
        """Get all agents as AgentProxy objects."""
        return self._agent_proxies

    def get_agent_by_id(self, agent_id: str) -> Optional[AgentProxy]:
        """Get agent by ID."""
        return self._agents_by_id.get(agent_id)

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
        elif self.mode == "replay" and self.replay is not None:
            self.replay.step()
            self._update_timeline_slider()
            self.record_positions()

    def step_back(self) -> None:
        """Step backward one tick (replay mode only)."""
        if self.mode == "replay" and self.replay is not None:
            self.replay.step_back()
            self._update_timeline_slider()

    def on_speed_change(self, sender: int, app_data: float) -> None:
        """Handle speed slider change."""
        self.ticks_per_second = app_data

    def on_timeline_change(self, sender: int, app_data: int) -> None:
        """Handle timeline slider change (replay mode)."""
        if self.mode == "replay" and self.replay is not None:
            self.replay.seek(app_data)

    def _update_timeline_slider(self) -> None:
        """Update timeline slider to match current tick."""
        if self.mode == "replay" and self.timeline_slider and self.replay is not None:
            dpg.set_value(self.timeline_slider, self.replay.current_tick)

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
        elif self.mode == "replay" and self.replay is not None:
            self.replay.reset()
            self._update_timeline_slider()

        self.trade_animations.clear()
        self.position_history.clear()
        self.selected_agent = None

    def record_trades(self, trades: list[TradeEvent]) -> None:
        """Record trades for animation."""
        current_time = time.time()
        for trade in trades:
            self.trade_animations.append(TradeAnimation(
                agent1_id=trade.agent1_id,
                agent2_id=trade.agent2_id,
                start_time=current_time,
            ))

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
                elif self.mode == "replay" and self.replay is not None:
                    if not self.replay.at_end:
                        self.replay.step()
                        self._update_timeline_slider()
                        self.record_positions()
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
        """Handle click on canvas for agent selection."""
        # Only process on mouse click
        if not dpg.is_mouse_button_clicked(dpg.mvMouseButton_Left):
            return

        if not dpg.is_item_hovered("grid_drawlist"):
            return

        mouse_pos = dpg.get_mouse_pos(local=False)
        dl_pos = dpg.get_item_pos("grid_drawlist")
        local_x = mouse_pos[0] - dl_pos[0]
        local_y = mouse_pos[1] - dl_pos[1]

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
        self.render_trade_animations()
        self.render_agents()
        self.render_metrics()
        self.render_hover_info()

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
        """Draw movement trails for all agents."""
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
        """Draw perception radius circle for selected agent."""
        if self.selected_agent is None:
            return

        # In replay mode, need to verify agent still exists (selection may be stale)
        current_agent = self.get_agent_by_id(self.selected_agent.id)
        if current_agent is None:
            self.selected_agent = None
            return

        cx, cy = self.grid_to_canvas(current_agent.position)
        # Convert perception_radius (grid units) to canvas pixels
        radius_px = current_agent.perception_radius * self.cell_size

        # Draw semi-transparent circle
        dpg.draw_circle(
            (cx, cy),
            radius_px,
            color=(100, 150, 255, 60),  # Light blue stroke
            fill=(100, 150, 255, 30),   # Very subtle fill
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
        """Update hover information panel."""
        if self.hovered_agent is not None:
            agent = self.hovered_agent
            dpg.set_value(self.hover_id_text, f"ID: {agent.id[:8]}...")
            dpg.set_value(self.hover_alpha_text, f"Alpha: {agent.alpha:.3f}")
            dpg.set_value(
                self.hover_endow_text,
                f"Endowment: ({agent.endowment_x:.1f}, {agent.endowment_y:.1f})"
            )
            dpg.set_value(self.hover_utility_text, f"Utility: {agent.utility:.2f}")
        else:
            dpg.set_value(self.hover_id_text, "ID: -")
            dpg.set_value(self.hover_alpha_text, "Alpha: -")
            dpg.set_value(self.hover_endow_text, "Endowment: -")
            dpg.set_value(self.hover_utility_text, "Utility: -")

    def run(self) -> None:
        """Main application loop."""
        self.setup()

        while dpg.is_dearpygui_running():
            self.update()
            self.update_hover()
            self.update_selection()
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


# Allow running as: python -m microecon.visualization.app
if __name__ == "__main__":
    run_visualization()
