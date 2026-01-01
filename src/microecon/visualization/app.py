"""
DearPyGui-based visualization for microecon simulation.

This module provides a live visualization of the search-and-exchange simulation,
showing agents moving on a grid, trading, and updating metrics in real-time.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import time

import dearpygui.dearpygui as dpg

from microecon.simulation import Simulation, create_simple_economy, TradeEvent
from microecon.grid import Position
from microecon.agent import Agent


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
    ):
        self.n_agents = n_agents
        self.grid_size = grid_size
        self.seed = seed

        # Simulation state
        self.sim: Simulation = create_simple_economy(n_agents, grid_size, seed=seed)

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

        # Rendering state
        self.canvas_size = 0.0
        self.cell_size = 0.0
        self.canvas_origin = (0.0, 0.0)

        # Hover tracking
        self.hovered_agent: Optional[Agent] = None

        # Selection tracking (click to select, shows perception radius)
        self.selected_agent: Optional[Agent] = None

        # Movement trail tracking
        self.position_history: dict[str, list[Position]] = {}  # agent_id -> recent positions
        self.TRAIL_LENGTH = 5

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

    def find_agent_at_canvas(self, x: float, y: float) -> Optional[Agent]:
        """Find agent near canvas coordinates, for hover detection."""
        agent_radius = self.cell_size * 0.35
        for agent in self.sim.agents:
            pos = self.sim.grid.get_position(agent)
            if pos is None:
                continue
            ax, ay = self.grid_to_canvas(pos)
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
                    self.play_button = dpg.add_button(
                        label="Play",
                        callback=self.toggle_play,
                        width=80,
                    )
                    dpg.add_button(
                        label="Step",
                        callback=self.step_once,
                        width=80,
                    )
                    dpg.add_text("  Speed:")
                    self.speed_slider = dpg.add_slider_float(
                        default_value=2.0,
                        min_value=0.5,
                        max_value=10.0,
                        width=200,
                        callback=self.on_speed_change,
                    )
                    dpg.add_text("ticks/sec  ")
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
        """Execute a single simulation step."""
        trades = self.sim.step()
        self.record_trades(trades)
        self.record_positions()

    def on_speed_change(self, sender: int, app_data: float) -> None:
        """Handle speed slider change."""
        self.ticks_per_second = app_data

    def reset_simulation(self) -> None:
        """Reset the simulation to initial state."""
        self.playing = False
        dpg.set_item_label(self.play_button, "Play")
        self.sim = create_simple_economy(
            self.n_agents,
            self.grid_size,
            seed=self.seed,
        )
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
        for agent in self.sim.agents:
            pos = self.sim.grid.get_position(agent)
            if pos is None:
                continue
            if agent.id not in self.position_history:
                self.position_history[agent.id] = []
            history = self.position_history[agent.id]
            # Only record if position changed (avoid duplicates when stationary)
            if not history or history[-1] != pos:
                history.append(pos)
            # Trim to TRAIL_LENGTH
            if len(history) > self.TRAIL_LENGTH:
                self.position_history[agent.id] = history[-self.TRAIL_LENGTH:]

    def update(self) -> None:
        """Update simulation state if playing."""
        if self.playing:
            current_time = time.time()
            tick_interval = 1.0 / self.ticks_per_second
            if current_time - self.last_tick_time >= tick_interval:
                trades = self.sim.step()
                self.record_trades(trades)
                self.record_positions()
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
        for agent in self.sim.agents:
            history = self.position_history.get(agent.id, [])
            if len(history) < 2:
                continue

            # Get current position as trail head
            current_pos = self.sim.grid.get_position(agent)
            if current_pos is None:
                continue

            # Build point list: history + current (oldest to newest)
            points = history + [current_pos]

            # Draw line segments with fading opacity
            for i in range(len(points) - 1):
                # Fade: oldest segments more transparent
                alpha = int(40 + (i / len(points)) * 80)  # 40 to 120
                p1 = self.grid_to_canvas(points[i])
                p2 = self.grid_to_canvas(points[i + 1])

                # Use agent's color but with reduced opacity
                base_color = alpha_to_color(agent.preferences.alpha)
                trail_color = (base_color[0], base_color[1], base_color[2], alpha)

                dpg.draw_line(p1, p2, color=trail_color, thickness=2, parent=self.drawlist)

    def render_perception_overlay(self) -> None:
        """Draw perception radius circle for selected agent."""
        if self.selected_agent is None:
            return

        pos = self.sim.grid.get_position(self.selected_agent)
        if pos is None:
            return

        cx, cy = self.grid_to_canvas(pos)
        # Convert perception_radius (grid units) to canvas pixels
        radius_px = self.selected_agent.perception_radius * self.cell_size

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
        agents_by_pos: dict[Position, list[Agent]] = {}
        for agent in self.sim.agents:
            pos = self.sim.grid.get_position(agent)
            if pos is not None:
                if pos not in agents_by_pos:
                    agents_by_pos[pos] = []
                agents_by_pos[pos].append(agent)

        agent_radius = self.cell_size * 0.35

        for pos, agents in agents_by_pos.items():
            cx, cy = self.grid_to_canvas(pos)

            if len(agents) == 1:
                # Single agent: draw at center
                agent = agents[0]
                color = alpha_to_color(agent.preferences.alpha)

                # Selection ring (thicker, more prominent)
                if agent == self.selected_agent:
                    dpg.draw_circle(
                        (cx, cy),
                        agent_radius + 5,
                        color=(255, 255, 255, 255),
                        thickness=3,
                        parent=self.drawlist,
                    )
                # Hover highlight (thinner)
                elif agent == self.hovered_agent:
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
                    color = alpha_to_color(agent.preferences.alpha)
                    small_radius = agent_radius * 0.7

                    # Selection ring (thicker, more prominent)
                    if agent == self.selected_agent:
                        dpg.draw_circle(
                            (ax, ay),
                            small_radius + 4,
                            color=(255, 255, 255, 255),
                            thickness=2,
                            parent=self.drawlist,
                        )
                    # Hover highlight (thinner)
                    elif agent == self.hovered_agent:
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
            agent1 = self.sim._agents_by_id.get(anim.agent1_id)
            agent2 = self.sim._agents_by_id.get(anim.agent2_id)
            if agent1 is None or agent2 is None:
                continue

            pos1 = self.sim.grid.get_position(agent1)
            pos2 = self.sim.grid.get_position(agent2)
            if pos1 is None or pos2 is None:
                continue

            # Calculate fade based on animation progress
            progress = (current_time - anim.start_time) / anim.duration
            alpha = int(255 * (1 - progress))

            # Draw line between agents
            c1 = self.grid_to_canvas(pos1)
            c2 = self.grid_to_canvas(pos2)

            dpg.draw_line(
                c1, c2,
                color=(255, 200, 0, alpha),
                thickness=3,
                parent=self.drawlist,
            )

            # Draw highlight circles
            radius = self.cell_size * 0.45
            dpg.draw_circle(
                c1,
                radius,
                color=(255, 200, 0, alpha),
                thickness=2,
                parent=self.drawlist,
            )
            dpg.draw_circle(
                c2,
                radius,
                color=(255, 200, 0, alpha),
                thickness=2,
                parent=self.drawlist,
            )

    def render_metrics(self) -> None:
        """Update the metrics panel."""
        state = self.sim.get_state()
        dpg.set_value(self.tick_text, f"Tick: {state.tick}")
        dpg.set_value(self.trades_text, f"Trades: {state.total_trades}")
        dpg.set_value(self.welfare_text, f"Welfare: {self.sim.total_welfare():.1f}")
        dpg.set_value(self.gains_text, f"Gains: {self.sim.welfare_gains():.1f}")

    def render_hover_info(self) -> None:
        """Update hover information panel."""
        if self.hovered_agent is not None:
            agent = self.hovered_agent
            dpg.set_value(self.hover_id_text, f"ID: {agent.id}")
            dpg.set_value(self.hover_alpha_text, f"Alpha: {agent.preferences.alpha:.3f}")
            dpg.set_value(
                self.hover_endow_text,
                f"Endowment: ({agent.endowment.x:.1f}, {agent.endowment.y:.1f})"
            )
            dpg.set_value(self.hover_utility_text, f"Utility: {agent.utility():.2f}")
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
    Launch the visualization window.

    Args:
        n_agents: Number of agents in the simulation
        grid_size: Size of the grid (NxN)
        seed: Random seed for reproducibility
    """
    app = VisualizationApp(n_agents=n_agents, grid_size=grid_size, seed=seed)
    app.run()


# Allow running as: python -m microecon.visualization.app
if __name__ == "__main__":
    run_visualization()
