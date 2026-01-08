"""Replay controllers for simulation playback.

Provides ReplayController for single-run replay and DualReplayController
for synchronized side-by-side comparison of two runs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from microecon.logging import RunData, TickRecord, load_run


class ReplayController:
    """Controller for replaying a logged simulation run.

    Provides playback controls (play/pause/step/seek) over logged data,
    enabling scrubbing through simulation history.

    Usage:
        controller = ReplayController.from_file("path/to/run")
        controller.step()  # Advance one tick
        state = controller.get_state()  # Get current tick record
        controller.seek(50)  # Jump to tick 50
    """

    def __init__(self, run_data: RunData):
        """Initialize replay controller.

        Args:
            run_data: Logged run data to replay
        """
        self.run = run_data
        self.current_tick = 0

    @classmethod
    def from_file(cls, path: Path | str) -> "ReplayController":
        """Load a run from disk and create a controller.

        Args:
            path: Path to the run directory

        Returns:
            ReplayController for the loaded run
        """
        if isinstance(path, str):
            path = Path(path)
        run_data = load_run(path)
        return cls(run_data)

    @property
    def total_ticks(self) -> int:
        """Total number of ticks in the run."""
        return len(self.run.ticks)

    @property
    def at_start(self) -> bool:
        """True if at the first tick."""
        return self.current_tick == 0

    @property
    def at_end(self) -> bool:
        """True if at the last tick."""
        return self.current_tick >= self.total_ticks - 1

    def get_state(self) -> TickRecord | None:
        """Get the current tick record.

        Returns:
            Current TickRecord, or None if no ticks available
        """
        if not self.run.ticks or self.current_tick >= len(self.run.ticks):
            return None
        return self.run.ticks[self.current_tick]

    def step(self) -> TickRecord | None:
        """Advance to the next tick.

        Returns:
            The new current tick, or None if at end
        """
        if self.current_tick < self.total_ticks - 1:
            self.current_tick += 1
        return self.get_state()

    def step_back(self) -> TickRecord | None:
        """Go back to the previous tick.

        Returns:
            The new current tick, or None if at start
        """
        if self.current_tick > 0:
            self.current_tick -= 1
        return self.get_state()

    def seek(self, tick: int) -> TickRecord | None:
        """Jump to a specific tick.

        Args:
            tick: Target tick number (clamped to valid range)

        Returns:
            The tick record at the new position
        """
        self.current_tick = max(0, min(tick, self.total_ticks - 1))
        return self.get_state()

    def reset(self) -> TickRecord | None:
        """Reset to the first tick.

        Returns:
            The first tick record
        """
        self.current_tick = 0
        return self.get_state()

    def go_to_end(self) -> TickRecord | None:
        """Jump to the last tick.

        Returns:
            The last tick record
        """
        if self.total_ticks > 0:
            self.current_tick = self.total_ticks - 1
        return self.get_state()


class DualReplayController:
    """Controller for synchronized replay of two runs.

    Enables side-by-side comparison of different protocol runs
    (e.g., Nash vs Rubinstein) with synchronized playback.

    Usage:
        controller = DualReplayController(run_a, run_b)
        controller.step()  # Advance both runs
        state_a, state_b = controller.get_states()
    """

    def __init__(
        self,
        run_a: RunData,
        run_b: RunData,
        synced: bool = True,
    ):
        """Initialize dual replay controller.

        Args:
            run_a: First run data
            run_b: Second run data
            synced: If True, both runs advance together
        """
        self.replay_a = ReplayController(run_a)
        self.replay_b = ReplayController(run_b)
        self.synced = synced

    @classmethod
    def from_files(
        cls, path_a: Path | str, path_b: Path | str, synced: bool = True
    ) -> "DualReplayController":
        """Load two runs from disk and create a controller.

        Args:
            path_a: Path to first run directory
            path_b: Path to second run directory
            synced: If True, both runs advance together

        Returns:
            DualReplayController for the loaded runs
        """
        if isinstance(path_a, str):
            path_a = Path(path_a)
        if isinstance(path_b, str):
            path_b = Path(path_b)
        run_a = load_run(path_a)
        run_b = load_run(path_b)
        return cls(run_a, run_b, synced)

    @property
    def current_tick(self) -> int:
        """Current tick (uses run A's position)."""
        return self.replay_a.current_tick

    @property
    def total_ticks(self) -> int:
        """Total ticks (minimum of both runs)."""
        return min(self.replay_a.total_ticks, self.replay_b.total_ticks)

    @property
    def at_start(self) -> bool:
        """True if at the first tick."""
        return self.replay_a.at_start and self.replay_b.at_start

    @property
    def at_end(self) -> bool:
        """True if at the last tick (for the shorter run)."""
        return self.current_tick >= self.total_ticks - 1

    def get_states(self) -> tuple[TickRecord | None, TickRecord | None]:
        """Get current tick records for both runs.

        Returns:
            Tuple of (state_a, state_b)
        """
        return self.replay_a.get_state(), self.replay_b.get_state()

    def step(self) -> tuple[TickRecord | None, TickRecord | None]:
        """Advance to the next tick.

        If synced, both runs advance. Otherwise, only run A advances.

        Returns:
            Tuple of new states (state_a, state_b)
        """
        self.replay_a.step()
        if self.synced:
            self.replay_b.step()
        return self.get_states()

    def step_back(self) -> tuple[TickRecord | None, TickRecord | None]:
        """Go back to the previous tick.

        Returns:
            Tuple of new states (state_a, state_b)
        """
        self.replay_a.step_back()
        if self.synced:
            self.replay_b.step_back()
        return self.get_states()

    def seek(self, tick: int) -> tuple[TickRecord | None, TickRecord | None]:
        """Jump to a specific tick.

        Args:
            tick: Target tick number

        Returns:
            Tuple of states at the new position
        """
        self.replay_a.seek(tick)
        if self.synced:
            self.replay_b.seek(tick)
        return self.get_states()

    def reset(self) -> tuple[TickRecord | None, TickRecord | None]:
        """Reset to the first tick.

        Returns:
            Tuple of first tick records
        """
        self.replay_a.reset()
        if self.synced:
            self.replay_b.reset()
        return self.get_states()

    def go_to_end(self) -> tuple[TickRecord | None, TickRecord | None]:
        """Jump to the last tick.

        Returns:
            Tuple of last tick records
        """
        # Go to the end of the shorter run
        target = self.total_ticks - 1
        return self.seek(target)

    def welfare_difference(self) -> float:
        """Get welfare difference at current tick (B - A).

        Returns:
            Welfare of run B minus welfare of run A
        """
        state_a, state_b = self.get_states()
        welfare_a = state_a.total_welfare if state_a else 0.0
        welfare_b = state_b.total_welfare if state_b else 0.0
        return welfare_b - welfare_a

    def trade_difference(self) -> int:
        """Get trade count difference at current tick (B - A).

        Returns:
            Cumulative trades of run B minus run A
        """
        state_a, state_b = self.get_states()
        trades_a = state_a.cumulative_trades if state_a else 0
        trades_b = state_b.cumulative_trades if state_b else 0
        return trades_b - trades_a
