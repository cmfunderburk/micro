"""
Time-series visualization using DearPyGui's ImPlot integration.

Provides real-time charts for:
- Welfare over time (total utility trajectory)
- Trade count over time (cumulative or per-tick)

Supports synchronized playback with timeline scrubbing and
overlay capability for protocol comparison.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import dearpygui.dearpygui as dpg


@dataclass
class TimeSeriesData:
    """
    Container for time-series data to be plotted.

    Stores tick values and corresponding metric values.
    """
    ticks: list[int] = field(default_factory=list)
    values: list[float] = field(default_factory=list)

    def append(self, tick: int, value: float) -> None:
        """Add a data point."""
        self.ticks.append(tick)
        self.values.append(value)

    def clear(self) -> None:
        """Clear all data."""
        self.ticks.clear()
        self.values.clear()

    def get_up_to_tick(self, max_tick: int) -> tuple[list[int], list[float]]:
        """Get data up to and including max_tick."""
        indices = [i for i, t in enumerate(self.ticks) if t <= max_tick]
        return (
            [self.ticks[i] for i in indices],
            [self.values[i] for i in indices],
        )


class TimeSeriesPanel:
    """
    Panel containing time-series charts for simulation metrics.

    Creates two charts:
    - Welfare over time
    - Trade count over time (cumulative)

    Can be used in live mode (data appended as simulation runs)
    or replay mode (data preloaded, view synced to current tick).
    """

    CHART_HEIGHT = 120

    def __init__(self, parent: int | str):
        """
        Initialize time-series panel within a parent container.

        Args:
            parent: DearPyGui parent container tag/id
        """
        self.parent = parent

        # Data storage
        self.welfare_data = TimeSeriesData()
        self.trades_data = TimeSeriesData()

        # UI element references
        self.welfare_plot: int = 0
        self.welfare_x_axis: int = 0
        self.welfare_y_axis: int = 0
        self.welfare_series: int = 0

        self.trades_plot: int = 0
        self.trades_x_axis: int = 0
        self.trades_y_axis: int = 0
        self.trades_series: int = 0

        # Vertical line for current tick (in replay mode)
        self.welfare_vline: int = 0
        self.trades_vline: int = 0

        # Configuration
        self.current_tick: int = 0
        self.replay_mode: bool = False

    def setup(self, width: int = 200) -> None:
        """
        Create the chart UI elements.

        Args:
            width: Width of the charts
        """
        with dpg.group(parent=self.parent):
            dpg.add_text("Time Series", color=(200, 200, 200))
            dpg.add_separator()

            # Welfare plot
            self.welfare_plot = dpg.add_plot(
                label="Welfare",
                height=self.CHART_HEIGHT,
                width=-1,
                no_menus=True,
                no_box_select=True,
            )

            self.welfare_x_axis = dpg.add_plot_axis(
                dpg.mvXAxis,
                label="Tick",
                parent=self.welfare_plot,
                no_tick_labels=True,
            )

            self.welfare_y_axis = dpg.add_plot_axis(
                dpg.mvYAxis,
                label="",
                parent=self.welfare_plot,
            )

            self.welfare_series = dpg.add_line_series(
                [],
                [],
                label="Welfare",
                parent=self.welfare_y_axis,
            )

            # Vertical line for current tick in replay
            self.welfare_vline = dpg.add_vline_series(
                [0],
                parent=self.welfare_x_axis,
            )
            dpg.configure_item(self.welfare_vline, show=False)

            dpg.add_separator()

            # Trades plot
            self.trades_plot = dpg.add_plot(
                label="Trades",
                height=self.CHART_HEIGHT,
                width=-1,
                no_menus=True,
                no_box_select=True,
            )

            self.trades_x_axis = dpg.add_plot_axis(
                dpg.mvXAxis,
                label="Tick",
                parent=self.trades_plot,
            )

            self.trades_y_axis = dpg.add_plot_axis(
                dpg.mvYAxis,
                label="",
                parent=self.trades_plot,
            )

            self.trades_series = dpg.add_line_series(
                [],
                [],
                label="Trades",
                parent=self.trades_y_axis,
            )

            # Vertical line for current tick in replay
            self.trades_vline = dpg.add_vline_series(
                [0],
                parent=self.trades_x_axis,
            )
            dpg.configure_item(self.trades_vline, show=False)

    def set_replay_mode(self, enabled: bool) -> None:
        """Enable or disable replay mode (shows playhead on charts)."""
        self.replay_mode = enabled
        dpg.configure_item(self.welfare_vline, show=enabled)
        dpg.configure_item(self.trades_vline, show=enabled)

    def record_tick(self, tick: int, welfare: float, cumulative_trades: int) -> None:
        """
        Record data for a single tick (live mode).

        Args:
            tick: Current tick number
            welfare: Total welfare at this tick
            cumulative_trades: Cumulative trade count at this tick
        """
        self.welfare_data.append(tick, welfare)
        self.trades_data.append(tick, float(cumulative_trades))
        self.current_tick = tick
        self._update_series()

    def load_full_data(
        self,
        ticks: list[int],
        welfare: list[float],
        trades: list[int],
    ) -> None:
        """
        Load complete time-series data (replay mode).

        Args:
            ticks: List of tick numbers
            welfare: Welfare values at each tick
            trades: Cumulative trade counts at each tick
        """
        self.welfare_data.clear()
        self.trades_data.clear()

        for t, w, tr in zip(ticks, welfare, trades):
            self.welfare_data.append(t, w)
            self.trades_data.append(t, float(tr))

        self._update_series()

    def seek_to_tick(self, tick: int) -> None:
        """
        Update view to show up to specified tick (replay mode).

        In replay mode, this updates the playhead position.
        The full data is shown, with a vertical line at current tick.
        """
        self.current_tick = tick
        if self.replay_mode:
            dpg.set_value(self.welfare_vline, [[tick]])
            dpg.set_value(self.trades_vline, [[tick]])

    def reset(self) -> None:
        """Clear all data and reset charts."""
        self.welfare_data.clear()
        self.trades_data.clear()
        self.current_tick = 0
        self._update_series()

    def _update_series(self) -> None:
        """Update chart series with current data."""
        # Welfare
        if self.welfare_data.ticks:
            dpg.set_value(
                self.welfare_series,
                [self.welfare_data.ticks, self.welfare_data.values],
            )
            dpg.fit_axis_data(self.welfare_x_axis)
            dpg.fit_axis_data(self.welfare_y_axis)

        # Trades
        if self.trades_data.ticks:
            dpg.set_value(
                self.trades_series,
                [self.trades_data.ticks, self.trades_data.values],
            )
            dpg.fit_axis_data(self.trades_x_axis)
            dpg.fit_axis_data(self.trades_y_axis)


class DualTimeSeriesPanel:
    """
    Panel for comparing time-series from two runs (protocol comparison).

    Shows welfare and trades over time for both runs on the same charts
    with different colors. Includes playhead for synchronized playback.
    """

    CHART_HEIGHT = 120

    def __init__(self, parent: int | str, label_a: str = "A", label_b: str = "B"):
        """
        Initialize dual time-series panel.

        Args:
            parent: DearPyGui parent container
            label_a: Label for first run
            label_b: Label for second run
        """
        self.parent = parent
        self.label_a = label_a
        self.label_b = label_b

        # Data storage for both runs
        self.welfare_data_a = TimeSeriesData()
        self.welfare_data_b = TimeSeriesData()
        self.trades_data_a = TimeSeriesData()
        self.trades_data_b = TimeSeriesData()

        # UI elements
        self.welfare_plot: int = 0
        self.welfare_x_axis: int = 0
        self.welfare_y_axis: int = 0
        self.welfare_series_a: int = 0
        self.welfare_series_b: int = 0
        self.welfare_vline: int = 0

        self.trades_plot: int = 0
        self.trades_x_axis: int = 0
        self.trades_y_axis: int = 0
        self.trades_series_a: int = 0
        self.trades_series_b: int = 0
        self.trades_vline: int = 0

        self.current_tick: int = 0

    def setup(self, width: int = 200) -> None:
        """Create the chart UI elements."""
        # Colors for the two runs
        color_a = (100, 200, 100, 255)  # Green for A
        color_b = (200, 150, 100, 255)  # Orange for B

        with dpg.group(parent=self.parent):
            dpg.add_text("Time Series", color=(200, 200, 200))
            dpg.add_separator()

            # Legend
            with dpg.group(horizontal=True):
                dpg.add_text("●", color=color_a)
                dpg.add_text(f" {self.label_a}  ", color=(180, 180, 180))
                dpg.add_text("●", color=color_b)
                dpg.add_text(f" {self.label_b}", color=(180, 180, 180))

            dpg.add_separator()

            # Welfare plot
            self.welfare_plot = dpg.add_plot(
                label="Welfare",
                height=self.CHART_HEIGHT,
                width=-1,
                no_menus=True,
                no_box_select=True,
            )

            self.welfare_x_axis = dpg.add_plot_axis(
                dpg.mvXAxis,
                label="Tick",
                parent=self.welfare_plot,
                no_tick_labels=True,
            )

            self.welfare_y_axis = dpg.add_plot_axis(
                dpg.mvYAxis,
                label="",
                parent=self.welfare_plot,
            )

            self.welfare_series_a = dpg.add_line_series(
                [],
                [],
                label=self.label_a,
                parent=self.welfare_y_axis,
            )
            dpg.bind_item_theme(
                self.welfare_series_a,
                self._create_line_theme(color_a),
            )

            self.welfare_series_b = dpg.add_line_series(
                [],
                [],
                label=self.label_b,
                parent=self.welfare_y_axis,
            )
            dpg.bind_item_theme(
                self.welfare_series_b,
                self._create_line_theme(color_b),
            )

            # Playhead
            self.welfare_vline = dpg.add_vline_series(
                [0],
                parent=self.welfare_x_axis,
            )

            dpg.add_separator()

            # Trades plot
            self.trades_plot = dpg.add_plot(
                label="Trades",
                height=self.CHART_HEIGHT,
                width=-1,
                no_menus=True,
                no_box_select=True,
            )

            self.trades_x_axis = dpg.add_plot_axis(
                dpg.mvXAxis,
                label="Tick",
                parent=self.trades_plot,
            )

            self.trades_y_axis = dpg.add_plot_axis(
                dpg.mvYAxis,
                label="",
                parent=self.trades_plot,
            )

            self.trades_series_a = dpg.add_line_series(
                [],
                [],
                label=self.label_a,
                parent=self.trades_y_axis,
            )
            dpg.bind_item_theme(
                self.trades_series_a,
                self._create_line_theme(color_a),
            )

            self.trades_series_b = dpg.add_line_series(
                [],
                [],
                label=self.label_b,
                parent=self.trades_y_axis,
            )
            dpg.bind_item_theme(
                self.trades_series_b,
                self._create_line_theme(color_b),
            )

            # Playhead
            self.trades_vline = dpg.add_vline_series(
                [0],
                parent=self.trades_x_axis,
            )

    @staticmethod
    def _create_line_theme(color: tuple[int, int, int, int]) -> int:
        """Create a theme for a line series with specific color."""
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(
                    dpg.mvPlotCol_Line,
                    color,
                    category=dpg.mvThemeCat_Plots,
                )
        return theme

    def load_data(
        self,
        ticks: list[int],
        welfare_a: list[float],
        welfare_b: list[float],
        trades_a: list[int],
        trades_b: list[int],
    ) -> None:
        """
        Load complete time-series data for both runs.

        Args:
            ticks: List of tick numbers (same for both runs)
            welfare_a: Welfare values for run A
            welfare_b: Welfare values for run B
            trades_a: Cumulative trade counts for run A
            trades_b: Cumulative trade counts for run B
        """
        self.welfare_data_a.clear()
        self.welfare_data_b.clear()
        self.trades_data_a.clear()
        self.trades_data_b.clear()

        for t, wa, wb, ta, tb in zip(ticks, welfare_a, welfare_b, trades_a, trades_b):
            self.welfare_data_a.append(t, wa)
            self.welfare_data_b.append(t, wb)
            self.trades_data_a.append(t, float(ta))
            self.trades_data_b.append(t, float(tb))

        self._update_series()

    def seek_to_tick(self, tick: int) -> None:
        """Update playhead position."""
        self.current_tick = tick
        dpg.set_value(self.welfare_vline, [[tick]])
        dpg.set_value(self.trades_vline, [[tick]])

    def _update_series(self) -> None:
        """Update chart series with current data."""
        # Welfare A
        if self.welfare_data_a.ticks:
            dpg.set_value(
                self.welfare_series_a,
                [self.welfare_data_a.ticks, self.welfare_data_a.values],
            )

        # Welfare B
        if self.welfare_data_b.ticks:
            dpg.set_value(
                self.welfare_series_b,
                [self.welfare_data_b.ticks, self.welfare_data_b.values],
            )

        # Fit welfare axes
        if self.welfare_data_a.ticks or self.welfare_data_b.ticks:
            dpg.fit_axis_data(self.welfare_x_axis)
            dpg.fit_axis_data(self.welfare_y_axis)

        # Trades A
        if self.trades_data_a.ticks:
            dpg.set_value(
                self.trades_series_a,
                [self.trades_data_a.ticks, self.trades_data_a.values],
            )

        # Trades B
        if self.trades_data_b.ticks:
            dpg.set_value(
                self.trades_series_b,
                [self.trades_data_b.ticks, self.trades_data_b.values],
            )

        # Fit trades axes
        if self.trades_data_a.ticks or self.trades_data_b.ticks:
            dpg.fit_axis_data(self.trades_x_axis)
            dpg.fit_axis_data(self.trades_y_axis)
