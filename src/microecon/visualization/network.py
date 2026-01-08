"""
Trade Network Panel visualization.

A dockable window that displays trade relationships as a network graph,
showing who traded with whom using force-directed or circular layouts.

NET-001 to NET-011 implementation from PRD-TRADE-NETWORK-PANEL.json.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, TYPE_CHECKING
import math

import dearpygui.dearpygui as dpg

if TYPE_CHECKING:
    from microecon.visualization.app import VisualizationApp


@dataclass
class NodeData:
    """Data for a node in the trade network graph."""
    agent_id: str
    alpha: float
    x: float = 0.0  # Canvas x position
    y: float = 0.0  # Canvas y position
    # Force-directed layout velocity
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class EdgeData:
    """Data for an edge in the trade network graph."""
    agent1_id: str
    agent2_id: str
    trade_count: int
    last_trade_tick: int = 0  # For recency coloring


class TradeNetworkPanel:
    """
    Trade Network Panel - a dockable window showing trade relationships.

    Features:
    - Circular and force-directed layouts (NET-003, NET-004, NET-005)
    - Node color encoding by alpha (NET-006)
    - Edge thickness by frequency, color by recency (NET-007, NET-008)
    - Click-to-select interaction (NET-009)
    - Live and replay mode support (NET-010)
    - Network metrics display (NET-011)
    """

    # Window defaults
    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 550
    DRAW_SIZE = 450  # Drawing area size
    NODE_RADIUS = 12

    # Layout parameters
    FORCE_ITERATIONS = 50
    REPULSION_STRENGTH = 5000.0
    ATTRACTION_STRENGTH = 0.01
    DAMPING = 0.85

    def __init__(self, app: "VisualizationApp"):
        """
        Initialize the Trade Network Panel.

        Args:
            app: The main VisualizationApp instance for data access and coordination
        """
        self.app = app
        self._window_id: int = 0
        self._drawlist_id: int = 0
        self._is_visible: bool = False

        # Layout state
        self._layout_type: str = "circular"  # "circular" or "force"
        self._nodes: dict[str, NodeData] = {}
        self._edges: list[EdgeData] = []

        # UI element references
        self._layout_combo_id: int = 0
        self._metrics_text_ids: dict[str, int] = {}

        # Selection callback (to sync with main app)
        self._on_select_callback: Optional[Callable[[str], None]] = None

        # Track current tick for recency calculation
        self._current_tick: int = 0

    def setup(self) -> None:
        """Create the Trade Network window and its contents (NET-001, NET-002)."""
        # Create the dockable window
        self._window_id = dpg.add_window(
            label="Trade Network",
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
            pos=(100, 100),
            show=False,  # Hidden by default
            on_close=self._on_window_close,
            tag="trade_network_window",
        )

        with dpg.group(parent=self._window_id):
            # Controls row
            with dpg.group(horizontal=True):
                dpg.add_text("Layout:")
                self._layout_combo_id = dpg.add_combo(
                    items=["Circular", "Force-Directed"],
                    default_value="Circular",
                    width=150,
                    callback=self._on_layout_change,
                )
                dpg.add_button(
                    label="Refresh",
                    callback=self._refresh_layout,
                    width=70,
                )

            dpg.add_separator()

            # Drawing area
            self._drawlist_id = dpg.add_drawlist(
                width=self.DRAW_SIZE,
                height=self.DRAW_SIZE,
                tag="trade_network_drawlist",
            )

            # Register mouse click handler for node selection
            with dpg.handler_registry(tag="trade_network_mouse_handler"):
                dpg.add_mouse_click_handler(callback=self._on_mouse_click)

            dpg.add_separator()

            # Metrics section (NET-011)
            dpg.add_text("Network Metrics:", color=(200, 200, 200))
            self._metrics_text_ids["nodes"] = dpg.add_text("Nodes: 0")
            self._metrics_text_ids["edges"] = dpg.add_text("Edges: 0")
            self._metrics_text_ids["density"] = dpg.add_text("Density: 0.0")
            self._metrics_text_ids["avg_degree"] = dpg.add_text("Avg Degree: 0.0")
            self._metrics_text_ids["clustering"] = dpg.add_text("Clustering: 0.0")

    def show(self) -> None:
        """Show the Trade Network window (NET-002)."""
        if self._window_id:
            dpg.show_item(self._window_id)
            dpg.focus_item(self._window_id)
            self._is_visible = True
            self.update()  # Refresh data when showing

    def hide(self) -> None:
        """Hide the Trade Network window."""
        if self._window_id:
            dpg.hide_item(self._window_id)
            self._is_visible = False

    def toggle(self) -> None:
        """Toggle window visibility (NET-002)."""
        if self._is_visible:
            self.hide()
        else:
            self.show()

    @property
    def is_visible(self) -> bool:
        """Whether the window is currently visible."""
        return self._is_visible

    def _on_window_close(self) -> None:
        """Handle window close button click."""
        self._is_visible = False

    def _on_layout_change(self, sender: int, app_data: str) -> None:
        """Handle layout combo box change (NET-005)."""
        self._layout_type = "circular" if app_data == "Circular" else "force"
        self._compute_layout()
        self._render()

    def _refresh_layout(self) -> None:
        """Refresh the layout and render."""
        self.update()

    def set_on_select_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for when a node is selected."""
        self._on_select_callback = callback

    # ========================================================================
    # Data Management
    # ========================================================================

    def update(self, current_tick: int = 0) -> None:
        """
        Update the network data from the app and re-render.

        Called when simulation state changes or window is shown.

        Args:
            current_tick: Current simulation tick (for recency calculation)
        """
        if not self._is_visible:
            return

        self._current_tick = current_tick if current_tick > 0 else self.app.get_current_tick()
        self._build_network_data()
        self._compute_layout()
        self._render()
        self._update_metrics()

    def _build_network_data(self) -> None:
        """Build nodes and edges from current trade data (NET-010)."""
        # Get agents from app
        agents = self.app.get_agents()

        # Build nodes
        self._nodes = {}
        for agent in agents:
            self._nodes[agent.id] = NodeData(
                agent_id=agent.id,
                alpha=agent.alpha,
            )

        # Build edges from trade network
        # In live mode, use app._trade_network
        # In replay mode, we also use app._trade_network (populated during replay)
        self._edges = []
        trade_network = getattr(self.app, '_trade_network', {})

        # Track edges we've already added (to handle bidirectional)
        seen_pairs: set[tuple[str, str]] = set()

        for (a1, a2), count in trade_network.items():
            # Normalize pair ordering
            pair = (min(a1, a2), max(a1, a2))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # Only add edge if both agents exist
            if pair[0] in self._nodes and pair[1] in self._nodes:
                self._edges.append(EdgeData(
                    agent1_id=pair[0],
                    agent2_id=pair[1],
                    trade_count=count,
                    last_trade_tick=self._current_tick,  # Approximate; could track per-edge
                ))

    # ========================================================================
    # Layout Algorithms
    # ========================================================================

    def _compute_layout(self) -> None:
        """Compute node positions based on selected layout (NET-003, NET-004)."""
        if self._layout_type == "circular":
            self._circular_layout()
        else:
            self._force_directed_layout()

    def _circular_layout(self) -> None:
        """
        Position nodes on a circle (NET-003).

        All agent nodes positioned on a circle, evenly spaced around circumference.
        """
        n = len(self._nodes)
        if n == 0:
            return

        center_x = self.DRAW_SIZE / 2
        center_y = self.DRAW_SIZE / 2
        radius = self.DRAW_SIZE / 2 - self.NODE_RADIUS - 20  # Margin

        for i, node in enumerate(self._nodes.values()):
            angle = 2 * math.pi * i / n
            node.x = center_x + radius * math.cos(angle)
            node.y = center_y + radius * math.sin(angle)

    def _force_directed_layout(self) -> None:
        """
        Position nodes using force-directed algorithm (NET-004).

        Connected nodes attract (spring force), all nodes repel (inverse square).
        Iterates until stable or max iterations reached.
        """
        n = len(self._nodes)
        if n == 0:
            return

        # Initialize positions randomly in center area
        center = self.DRAW_SIZE / 2
        spread = self.DRAW_SIZE / 4

        import random
        rng = random.Random(42)  # Deterministic for consistency

        for node in self._nodes.values():
            node.x = center + (rng.random() - 0.5) * spread * 2
            node.y = center + (rng.random() - 0.5) * spread * 2
            node.vx = 0.0
            node.vy = 0.0

        # Build adjacency set for faster lookup
        adjacency: dict[str, set[str]] = {aid: set() for aid in self._nodes}
        for edge in self._edges:
            adjacency[edge.agent1_id].add(edge.agent2_id)
            adjacency[edge.agent2_id].add(edge.agent1_id)

        # Iterate force simulation
        node_list = list(self._nodes.values())

        for _ in range(self.FORCE_ITERATIONS):
            # Repulsion between all pairs
            for i, node_a in enumerate(node_list):
                for node_b in node_list[i+1:]:
                    dx = node_a.x - node_b.x
                    dy = node_a.y - node_b.y
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < 1:
                        dist_sq = 1

                    # Repulsive force (inverse square)
                    force = self.REPULSION_STRENGTH / dist_sq
                    dist = math.sqrt(dist_sq)
                    fx = force * dx / dist
                    fy = force * dy / dist

                    node_a.vx += fx
                    node_a.vy += fy
                    node_b.vx -= fx
                    node_b.vy -= fy

            # Attraction along edges
            for edge in self._edges:
                node_a = self._nodes[edge.agent1_id]
                node_b = self._nodes[edge.agent2_id]

                dx = node_b.x - node_a.x
                dy = node_b.y - node_a.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 1:
                    dist = 1

                # Attractive force (spring)
                force = self.ATTRACTION_STRENGTH * dist
                fx = force * dx / dist
                fy = force * dy / dist

                node_a.vx += fx
                node_a.vy += fy
                node_b.vx -= fx
                node_b.vy -= fy

            # Apply velocity with damping and boundary constraints
            margin = self.NODE_RADIUS + 10
            for node in node_list:
                node.vx *= self.DAMPING
                node.vy *= self.DAMPING

                node.x += node.vx
                node.y += node.vy

                # Keep within bounds
                node.x = max(margin, min(self.DRAW_SIZE - margin, node.x))
                node.y = max(margin, min(self.DRAW_SIZE - margin, node.y))

    # ========================================================================
    # Rendering
    # ========================================================================

    def _render(self) -> None:
        """Render the network graph to the drawlist."""
        if not self._drawlist_id:
            return

        # Clear previous drawing
        dpg.delete_item(self._drawlist_id, children_only=True)

        # Draw background
        dpg.draw_rectangle(
            (0, 0),
            (self.DRAW_SIZE, self.DRAW_SIZE),
            fill=(30, 30, 30, 255),
            parent=self._drawlist_id,
        )

        # Draw edges first (so nodes appear on top)
        self._render_edges()

        # Draw nodes
        self._render_nodes()

    def _render_edges(self) -> None:
        """Render edges with thickness and color encoding (NET-007, NET-008)."""
        if not self._edges:
            return

        # Find max trade count for normalization
        max_trades = max(e.trade_count for e in self._edges) if self._edges else 1

        for edge in self._edges:
            node_a = self._nodes.get(edge.agent1_id)
            node_b = self._nodes.get(edge.agent2_id)
            if not node_a or not node_b:
                continue

            # Thickness: min(1 + trade_count * 0.5, 5) (NET-007)
            thickness = min(1 + edge.trade_count * 0.5, 5)

            # Color based on recency (NET-008)
            # More recent = brighter, older = faded
            ticks_since_trade = max(0, self._current_tick - edge.last_trade_tick)
            # Fade over 50 ticks
            fade = max(0.3, 1.0 - ticks_since_trade / 50.0)

            # Base color: light gray, faded by recency
            base_brightness = int(200 * fade)
            color = (base_brightness, base_brightness, int(base_brightness * 0.8), 255)

            dpg.draw_line(
                (node_a.x, node_a.y),
                (node_b.x, node_b.y),
                color=color,
                thickness=thickness,
                parent=self._drawlist_id,
            )

    def _render_nodes(self) -> None:
        """Render nodes with alpha-based coloring (NET-006)."""
        from microecon.visualization.app import alpha_to_color

        for node in self._nodes.values():
            # Get color from alpha (NET-006)
            fill_color = alpha_to_color(node.alpha)

            # Draw node circle
            dpg.draw_circle(
                (node.x, node.y),
                self.NODE_RADIUS,
                fill=fill_color,
                color=(255, 255, 255, 200),  # White border
                thickness=2,
                parent=self._drawlist_id,
            )

            # Highlight selected node
            selected = self.app.selected_agent
            if selected and selected.id == node.agent_id:
                dpg.draw_circle(
                    (node.x, node.y),
                    self.NODE_RADIUS + 4,
                    color=(255, 255, 0, 255),  # Yellow selection ring
                    thickness=3,
                    parent=self._drawlist_id,
                )

    def _update_metrics(self) -> None:
        """Update the network metrics display (NET-011)."""
        n_nodes = len(self._nodes)
        n_edges = len(self._edges)

        # Density: edges / max possible edges
        max_edges = n_nodes * (n_nodes - 1) // 2 if n_nodes > 1 else 1
        density = n_edges / max_edges if max_edges > 0 else 0.0

        # Average degree
        if n_nodes > 0:
            total_degree = sum(2 for _ in self._edges)  # Each edge contributes 2 to total degree
            avg_degree = total_degree / n_nodes
        else:
            avg_degree = 0.0

        # Clustering coefficient (simplified calculation)
        clustering = self._compute_clustering_coefficient()

        # Update UI
        dpg.set_value(self._metrics_text_ids["nodes"], f"Nodes: {n_nodes}")
        dpg.set_value(self._metrics_text_ids["edges"], f"Edges: {n_edges}")
        dpg.set_value(self._metrics_text_ids["density"], f"Density: {density:.3f}")
        dpg.set_value(self._metrics_text_ids["avg_degree"], f"Avg Degree: {avg_degree:.2f}")
        dpg.set_value(self._metrics_text_ids["clustering"], f"Clustering: {clustering:.3f}")

    def _compute_clustering_coefficient(self) -> float:
        """Compute the clustering coefficient of the network."""
        if len(self._nodes) < 3:
            return 0.0

        # Build adjacency sets
        neighbors: dict[str, set[str]] = {aid: set() for aid in self._nodes}
        for edge in self._edges:
            neighbors[edge.agent1_id].add(edge.agent2_id)
            neighbors[edge.agent2_id].add(edge.agent1_id)

        # Compute local clustering for each node
        local_clustering = []
        for agent_id, nbrs in neighbors.items():
            if len(nbrs) < 2:
                continue

            # Count triangles
            nbr_list = list(nbrs)
            connected_pairs = 0
            possible_pairs = len(nbr_list) * (len(nbr_list) - 1) // 2

            for i, n1 in enumerate(nbr_list):
                for n2 in nbr_list[i+1:]:
                    if n2 in neighbors.get(n1, set()):
                        connected_pairs += 1

            if possible_pairs > 0:
                local_clustering.append(connected_pairs / possible_pairs)

        return sum(local_clustering) / len(local_clustering) if local_clustering else 0.0

    # ========================================================================
    # Interaction
    # ========================================================================

    def _on_mouse_click(self, sender: int, app_data: int) -> None:
        """Handle mouse click for node selection (NET-009)."""
        if not self._is_visible:
            return

        # Only handle left click
        if app_data != 0:  # 0 = left button
            return

        # Get mouse position relative to drawlist
        mouse_pos = dpg.get_mouse_pos(local=False)

        # Check if click is within the Trade Network window
        if not dpg.is_item_hovered("trade_network_window"):
            return

        # Get drawlist position
        drawlist_pos = dpg.get_item_pos(self._drawlist_id)
        if not drawlist_pos:
            return

        # Calculate local position
        local_x = mouse_pos[0] - drawlist_pos[0]
        local_y = mouse_pos[1] - drawlist_pos[1]

        # Check if within drawlist bounds
        if not (0 <= local_x <= self.DRAW_SIZE and 0 <= local_y <= self.DRAW_SIZE):
            return

        # Find clicked node
        clicked_node = self._find_node_at(local_x, local_y)
        if clicked_node:
            # Notify callback (to sync with main app selection)
            if self._on_select_callback:
                self._on_select_callback(clicked_node.agent_id)

            # Re-render to show selection
            self._render()

    def _find_node_at(self, x: float, y: float) -> Optional[NodeData]:
        """Find the node at the given canvas coordinates."""
        for node in self._nodes.values():
            dx = x - node.x
            dy = y - node.y
            if dx * dx + dy * dy <= self.NODE_RADIUS * self.NODE_RADIUS:
                return node
        return None

    def on_selection_changed(self) -> None:
        """Called when selection changes in the main app (NET-009)."""
        if self._is_visible:
            self._render()  # Re-render to update selection highlight
