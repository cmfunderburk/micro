"""Edgeworth box visualization for trade analysis (VIZ-012 to VIZ-014).

The Edgeworth box shows the allocation space for a 2-agent, 2-good economy.
Key features:
- Box dimensions = total endowments (X, Y)
- Each point represents an allocation (agent A gets (x, y), agent B gets (X-x, Y-y))
- Indifference curves show constant utility levels
- Contract curve shows Pareto-efficient allocations

Reference: Kreps I Ch 15, MWG Ch 15
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math

import dearpygui.dearpygui as dpg


@dataclass
class TradeData:
    """Data for visualizing a trade in the Edgeworth box."""
    # Agent A (origin at bottom-left)
    agent_a_id: str
    alpha_a: float
    endowment_a: tuple[float, float]  # (x, y) before trade
    allocation_a: tuple[float, float]  # (x, y) after trade
    utility_a_before: float
    utility_a_after: float

    # Agent B (origin at top-right)
    agent_b_id: str
    alpha_b: float
    endowment_b: tuple[float, float]
    allocation_b: tuple[float, float]
    utility_b_before: float
    utility_b_after: float

    @property
    def total_x(self) -> float:
        """Total endowment of good x."""
        return self.endowment_a[0] + self.endowment_b[0]

    @property
    def total_y(self) -> float:
        """Total endowment of good y."""
        return self.endowment_a[1] + self.endowment_b[1]


def compute_indifference_curve(
    alpha: float,
    utility: float,
    x_min: float,
    x_max: float,
    n_points: int = 50,
) -> list[tuple[float, float]]:
    """
    Compute points on a Cobb-Douglas indifference curve.

    For u(x, y) = x^α * y^(1-α), the indifference curve at utility u is:
        y = (u / x^α)^(1/(1-α))

    Args:
        alpha: Preference parameter (0 < alpha < 1)
        utility: Target utility level
        x_min: Minimum x value
        x_max: Maximum x value
        n_points: Number of points to compute

    Returns:
        List of (x, y) points on the indifference curve
    """
    if utility <= 0 or alpha <= 0 or alpha >= 1:
        return []

    points = []
    exponent = 1.0 / (1.0 - alpha)

    for i in range(n_points):
        x = x_min + (x_max - x_min) * (i / (n_points - 1)) if n_points > 1 else x_min
        if x <= 0:
            continue
        try:
            y = (utility / (x ** alpha)) ** exponent
            if y >= 0 and math.isfinite(y):
                points.append((x, y))
        except (ValueError, OverflowError):
            continue

    return points


def compute_contract_curve(
    alpha_a: float,
    alpha_b: float,
    total_x: float,
    total_y: float,
    n_points: int = 50,
) -> list[tuple[float, float]]:
    """
    Compute points on the contract curve.

    The contract curve is the locus of Pareto-efficient allocations where MRS_A = MRS_B.

    For Cobb-Douglas preferences:
        (α_A / (1-α_A)) * (y_A / x_A) = (α_B / (1-α_B)) * ((Y - y_A) / (X - x_A))

    Solving for y_A in terms of x_A:
        y_A = (α_A * (1-α_B) * Y * x_A) / (α_B * (1-α_A) * X + (α_A * (1-α_B) - α_B * (1-α_A)) * x_A)

    Args:
        alpha_a: Agent A's preference parameter
        alpha_b: Agent B's preference parameter
        total_x: Total endowment of good x
        total_y: Total endowment of good y
        n_points: Number of points to compute

    Returns:
        List of (x_A, y_A) points on the contract curve
    """
    if alpha_a <= 0 or alpha_a >= 1 or alpha_b <= 0 or alpha_b >= 1:
        return []

    points = []
    X, Y = total_x, total_y

    # Coefficients for the contract curve equation
    a1 = alpha_a * (1 - alpha_b)
    a2 = alpha_b * (1 - alpha_a)

    for i in range(n_points):
        # x_A from 0 to X (excluding endpoints to avoid division by zero)
        x_a = 0.01 * X + (0.98 * X) * (i / (n_points - 1)) if n_points > 1 else 0.5 * X

        # Compute denominator
        denom = a2 * X + (a1 - a2) * x_a

        if abs(denom) < 1e-10:
            continue

        y_a = (a1 * Y * x_a) / denom

        # Check bounds
        if 0 < y_a < Y:
            points.append((x_a, y_a))

    return points


class EdgeworthBoxPopup:
    """
    Popup window showing Edgeworth box for a trade.

    Displays:
    - Box with endowment point and allocation point
    - Indifference curves through both points for both agents
    - Contract curve
    - Trade vector (arrow from endowment to allocation)
    """

    BOX_SIZE = 400  # Pixels
    MARGIN = 50

    def __init__(self):
        self.window_id: int = 0
        self.drawlist_id: int = 0
        self.current_trade: Optional[TradeData] = None
        self._is_open = False

    def show(self, trade: TradeData) -> None:
        """Show the Edgeworth box popup for the given trade."""
        self.current_trade = trade
        # Always recreate window to ensure proper display
        if self._is_open:
            self.hide()
        self._create_window()
        self._render()

    def hide(self) -> None:
        """Hide the popup."""
        if self._is_open and self.window_id and dpg.does_item_exist(self.window_id):
            dpg.delete_item(self.window_id)
        self._is_open = False
        self.current_trade = None
        self.window_id = 0
        self.drawlist_id = 0

    def _create_window(self) -> None:
        """Create the popup window."""
        # Clean up any existing popup with same tag
        if dpg.does_item_exist("edgeworth_popup"):
            dpg.delete_item("edgeworth_popup")

        width = self.BOX_SIZE + 2 * self.MARGIN + 100
        height = self.BOX_SIZE + 2 * self.MARGIN + 80

        with dpg.window(
            label="Edgeworth Box",
            width=width,
            height=height,
            no_collapse=True,
            on_close=self.hide,
            tag="edgeworth_popup",
            pos=(100, 100),  # Position it visibly on screen
        ) as self.window_id:
            # Info text
            if self.current_trade:
                dpg.add_text(
                    f"Trade: {self.current_trade.agent_a_id[:8]} <-> {self.current_trade.agent_b_id[:8]}"
                )
            else:
                dpg.add_text("Trade: -")

            # Drawlist for the box
            self.drawlist_id = dpg.add_drawlist(
                width=self.BOX_SIZE + 2 * self.MARGIN,
                height=self.BOX_SIZE + 2 * self.MARGIN,
            )

            # Legend
            with dpg.group(horizontal=True):
                dpg.add_text("Endowment", color=(255, 200, 100))
                dpg.add_text("  ")
                dpg.add_text("Allocation", color=(100, 255, 100))
                dpg.add_text("  ")
                dpg.add_text("Contract curve", color=(255, 100, 255))

        self._is_open = True

    def _render(self) -> None:
        """Render the Edgeworth box."""
        if not self._is_open or self.current_trade is None:
            return

        if not dpg.does_item_exist(self.drawlist_id):
            return

        # Clear previous drawings
        dpg.delete_item(self.drawlist_id, children_only=True)

        trade = self.current_trade
        X, Y = trade.total_x, trade.total_y

        # Coordinate transformation: (x, y) in goods space -> (px, py) in pixels
        def to_px(x: float, y: float) -> tuple[float, float]:
            """Convert goods coordinates to pixel coordinates."""
            px = self.MARGIN + (x / X) * self.BOX_SIZE
            # Flip y axis (y increases upward in goods space, downward in pixels)
            py = self.MARGIN + self.BOX_SIZE - (y / Y) * self.BOX_SIZE
            return (px, py)

        # Draw box border
        dpg.draw_rectangle(
            to_px(0, Y), to_px(X, 0),
            color=(200, 200, 200, 255),
            thickness=2,
            parent=self.drawlist_id,
        )

        # Draw axis labels
        dpg.draw_text(
            (self.MARGIN - 30, self.MARGIN + self.BOX_SIZE + 10),
            "A", size=16, color=(100, 150, 255),
            parent=self.drawlist_id,
        )
        dpg.draw_text(
            (self.MARGIN + self.BOX_SIZE + 10, self.MARGIN - 20),
            "B", size=16, color=(255, 150, 100),
            parent=self.drawlist_id,
        )

        # Draw contract curve
        contract_points = compute_contract_curve(
            trade.alpha_a, trade.alpha_b, X, Y, n_points=40
        )
        for i in range(len(contract_points) - 1):
            p1 = to_px(*contract_points[i])
            p2 = to_px(*contract_points[i + 1])
            dpg.draw_line(p1, p2, color=(255, 100, 255, 150), thickness=2, parent=self.drawlist_id)

        # Draw indifference curves for agent A (utility before and after)
        ic_a_before = compute_indifference_curve(
            trade.alpha_a, trade.utility_a_before, 0.01 * X, 0.99 * X, 40
        )
        ic_a_after = compute_indifference_curve(
            trade.alpha_a, trade.utility_a_after, 0.01 * X, 0.99 * X, 40
        )

        # Draw A's indifference curves (clipped to box)
        for i in range(len(ic_a_before) - 1):
            x1, y1 = ic_a_before[i]
            x2, y2 = ic_a_before[i + 1]
            if y1 <= Y and y2 <= Y:
                dpg.draw_line(
                    to_px(x1, y1), to_px(x2, y2),
                    color=(100, 150, 255, 100), thickness=1,
                    parent=self.drawlist_id,
                )

        for i in range(len(ic_a_after) - 1):
            x1, y1 = ic_a_after[i]
            x2, y2 = ic_a_after[i + 1]
            if y1 <= Y and y2 <= Y:
                dpg.draw_line(
                    to_px(x1, y1), to_px(x2, y2),
                    color=(100, 150, 255, 200), thickness=1.5,
                    parent=self.drawlist_id,
                )

        # Draw indifference curves for agent B (in B's coordinates, then transform)
        # B's origin is at (X, Y), so B's allocation (x_b, y_b) appears at (X - x_b, Y - y_b) in A's frame
        ic_b_before = compute_indifference_curve(
            trade.alpha_b, trade.utility_b_before, 0.01 * X, 0.99 * X, 40
        )
        ic_b_after = compute_indifference_curve(
            trade.alpha_b, trade.utility_b_after, 0.01 * X, 0.99 * X, 40
        )

        # Draw B's curves (transform to A's frame)
        for i in range(len(ic_b_before) - 1):
            x1_b, y1_b = ic_b_before[i]
            x2_b, y2_b = ic_b_before[i + 1]
            x1_a, y1_a = X - x1_b, Y - y1_b
            x2_a, y2_a = X - x2_b, Y - y2_b
            if 0 <= y1_a <= Y and 0 <= y2_a <= Y:
                dpg.draw_line(
                    to_px(x1_a, y1_a), to_px(x2_a, y2_a),
                    color=(255, 150, 100, 100), thickness=1,
                    parent=self.drawlist_id,
                )

        for i in range(len(ic_b_after) - 1):
            x1_b, y1_b = ic_b_after[i]
            x2_b, y2_b = ic_b_after[i + 1]
            x1_a, y1_a = X - x1_b, Y - y1_b
            x2_a, y2_a = X - x2_b, Y - y2_b
            if 0 <= y1_a <= Y and 0 <= y2_a <= Y:
                dpg.draw_line(
                    to_px(x1_a, y1_a), to_px(x2_a, y2_a),
                    color=(255, 150, 100, 200), thickness=1.5,
                    parent=self.drawlist_id,
                )

        # Draw endowment point
        endow_px = to_px(*trade.endowment_a)
        dpg.draw_circle(
            endow_px, 8,
            color=(255, 200, 100, 255),
            fill=(255, 200, 100, 200),
            parent=self.drawlist_id,
        )

        # Draw allocation point
        alloc_px = to_px(*trade.allocation_a)
        dpg.draw_circle(
            alloc_px, 8,
            color=(100, 255, 100, 255),
            fill=(100, 255, 100, 200),
            parent=self.drawlist_id,
        )

        # Draw trade vector (arrow from endowment to allocation)
        dpg.draw_arrow(
            alloc_px, endow_px,
            color=(255, 255, 255, 200),
            thickness=2,
            size=10,
            parent=self.drawlist_id,
        )
