"""SimulationLogger for capturing complete simulation state.

The logger hooks into the simulation loop to capture all decisions
and state changes, enabling replay and analysis.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .events import (
    AgentSnapshot,
    CommitmentBrokenEvent,
    CommitmentFormedEvent,
    MovementEvent,
    RunSummary,
    SearchDecision,
    SimulationConfig,
    TargetEvaluation,
    TickRecord,
    TradeEvent,
)

if TYPE_CHECKING:
    from .formats import LogFormat


@dataclass
class RunData:
    """Complete data from a simulation run."""

    config: SimulationConfig
    ticks: list[TickRecord]
    summary: RunSummary | None = None

    def welfare_at(self, tick: int) -> float:
        """Get total welfare at a specific tick."""
        if tick < 0 or tick >= len(self.ticks):
            raise IndexError(f"Tick {tick} out of range [0, {len(self.ticks)})")
        return self.ticks[tick].total_welfare

    def trades_at(self, tick: int) -> int:
        """Get cumulative trades at a specific tick."""
        if tick < 0 or tick >= len(self.ticks):
            raise IndexError(f"Tick {tick} out of range [0, {len(self.ticks)})")
        return self.ticks[tick].cumulative_trades

    def agent_trajectory(self, agent_id: str) -> list[AgentSnapshot]:
        """Get an agent's state across all ticks."""
        trajectory = []
        for tick_record in self.ticks:
            for snapshot in tick_record.agent_snapshots:
                if snapshot.agent_id == agent_id:
                    trajectory.append(snapshot)
                    break
        return trajectory

    @property
    def agent_ids(self) -> list[str]:
        """Get list of all agent IDs in the simulation."""
        if not self.ticks:
            return []
        return [s.agent_id for s in self.ticks[0].agent_snapshots]


class SimulationLogger:
    """Captures complete simulation state for replay and analysis.

    Can operate in two modes:
    - In-memory: Collect all ticks, retrieve via finalize()
    - Streaming: Write each tick to disk as it occurs

    Usage:
        logger = SimulationLogger(config)
        # ... simulation runs, calling logger.log_tick() each step ...
        run_data = logger.finalize()
    """

    def __init__(
        self,
        config: SimulationConfig,
        output_path: Path | None = None,
        log_format: "LogFormat | None" = None,
    ):
        """Initialize the logger.

        Args:
            config: Simulation configuration to record
            output_path: If provided, write ticks to this directory as they occur
            log_format: Format for writing logs (default: JSONLinesFormat)
        """
        self.config = config
        self.output_path = output_path
        self.log_format = log_format
        self.ticks: list[TickRecord] = []
        self._initial_welfare: float | None = None

        if output_path is not None:
            self._setup_output()

    def _setup_output(self) -> None:
        """Set up output directory and write config."""
        if self.output_path is None:
            return

        self.output_path.mkdir(parents=True, exist_ok=True)

        # Import here to avoid circular dependency
        if self.log_format is None:
            from .formats import JSONLinesFormat

            self.log_format = JSONLinesFormat()

        self.log_format.write_config(self.config, self.output_path)

    def log_tick(self, tick_record: TickRecord) -> None:
        """Record a complete tick.

        Args:
            tick_record: Complete record of the tick's events
        """
        # Track initial welfare for summary
        if self._initial_welfare is None:
            self._initial_welfare = tick_record.total_welfare

        self.ticks.append(tick_record)

        # Write to disk if streaming
        if self.output_path is not None and self.log_format is not None:
            self.log_format.write_tick(tick_record, self.output_path)

    def finalize(self) -> RunData:
        """Complete logging and return full run data.

        Returns:
            RunData containing config, all ticks, and summary statistics
        """
        summary = None
        if self.ticks:
            final_tick = self.ticks[-1]
            initial_welfare = self._initial_welfare or 0.0
            summary = RunSummary(
                total_ticks=len(self.ticks),
                final_welfare=final_tick.total_welfare,
                total_trades=final_tick.cumulative_trades,
                welfare_gain=final_tick.total_welfare - initial_welfare,
            )

            # Write summary to disk if streaming
            if self.output_path is not None and self.log_format is not None:
                self.log_format.write_summary(summary, self.output_path)

        return RunData(config=self.config, ticks=self.ticks, summary=summary)


# Helper functions for creating event objects from simulation state


def create_agent_snapshot(
    agent_id: str,
    position: tuple[int, int],
    endowment: tuple[float, float],
    alpha: float,
    utility: float,
) -> AgentSnapshot:
    """Create an AgentSnapshot from simulation state."""
    return AgentSnapshot(
        agent_id=agent_id,
        position=position,
        endowment=endowment,
        alpha=alpha,
        utility=utility,
    )


def create_target_evaluation(
    target_id: str,
    target_position: tuple[int, int],
    distance: float,
    ticks_to_reach: int,
    expected_surplus: float,
    discounted_value: float,
    observed_alpha: float,
) -> TargetEvaluation:
    """Create a TargetEvaluation from search computation."""
    return TargetEvaluation(
        target_id=target_id,
        target_position=target_position,
        distance=distance,
        ticks_to_reach=ticks_to_reach,
        expected_surplus=expected_surplus,
        discounted_value=discounted_value,
        observed_alpha=observed_alpha,
    )


def create_search_decision(
    agent_id: str,
    position: tuple[int, int],
    visible_agents: int,
    evaluations: list[TargetEvaluation],
    chosen_target_id: str | None,
    chosen_value: float,
) -> SearchDecision:
    """Create a SearchDecision from search computation."""
    return SearchDecision(
        agent_id=agent_id,
        position=position,
        visible_agents=visible_agents,
        evaluations=tuple(evaluations),
        chosen_target_id=chosen_target_id,
        chosen_value=chosen_value,
    )


def create_movement_event(
    agent_id: str,
    from_pos: tuple[int, int],
    to_pos: tuple[int, int],
    target_id: str | None,
    reason: str,
) -> MovementEvent:
    """Create a MovementEvent from movement execution."""
    return MovementEvent(
        agent_id=agent_id,
        from_pos=from_pos,
        to_pos=to_pos,
        target_id=target_id,
        reason=reason,
    )


def create_trade_event(
    agent1_id: str,
    agent2_id: str,
    proposer_id: str,
    pre_endowments: tuple[tuple[float, float], tuple[float, float]],
    post_allocations: tuple[tuple[float, float], tuple[float, float]],
    utilities: tuple[float, float],
    gains: tuple[float, float],
    trade_occurred: bool,
) -> TradeEvent:
    """Create a TradeEvent from trade execution."""
    return TradeEvent(
        agent1_id=agent1_id,
        agent2_id=agent2_id,
        proposer_id=proposer_id,
        pre_endowments=pre_endowments,
        post_allocations=post_allocations,
        utilities=utilities,
        gains=gains,
        trade_occurred=trade_occurred,
    )


def create_commitment_formed_event(
    agent_a: str,
    agent_b: str,
) -> CommitmentFormedEvent:
    """Create a CommitmentFormedEvent from matching phase."""
    return CommitmentFormedEvent(
        agent_a=agent_a,
        agent_b=agent_b,
    )


def create_commitment_broken_event(
    agent_a: str,
    agent_b: str,
    reason: str,
) -> CommitmentBrokenEvent:
    """Create a CommitmentBrokenEvent from commitment maintenance or trade."""
    return CommitmentBrokenEvent(
        agent_a=agent_a,
        agent_b=agent_b,
        reason=reason,
    )


def create_tick_record(
    tick: int,
    agent_snapshots: list[AgentSnapshot],
    search_decisions: list[SearchDecision],
    movements: list[MovementEvent],
    trades: list[TradeEvent],
    total_welfare: float,
    cumulative_trades: int,
    commitments_formed: list[CommitmentFormedEvent] | None = None,
    commitments_broken: list[CommitmentBrokenEvent] | None = None,
) -> TickRecord:
    """Create a TickRecord from tick execution."""
    return TickRecord(
        tick=tick,
        agent_snapshots=tuple(agent_snapshots),
        search_decisions=tuple(search_decisions),
        movements=tuple(movements),
        trades=tuple(trades),
        total_welfare=total_welfare,
        cumulative_trades=cumulative_trades,
        commitments_formed=tuple(commitments_formed or []),
        commitments_broken=tuple(commitments_broken or []),
    )
