"""Time series analysis functions.

Extract and analyze temporal patterns from simulation runs.
"""

from typing import Callable

from microecon.logging import RunData, TickRecord


def welfare_over_time(run: RunData) -> list[float]:
    """Extract total welfare at each tick.

    Args:
        run: RunData object

    Returns:
        List of welfare values indexed by tick
    """
    return [tick.total_welfare for tick in run.ticks]


def trades_over_time(run: RunData) -> list[int]:
    """Extract cumulative trade count at each tick.

    Args:
        run: RunData object

    Returns:
        List of cumulative trade counts indexed by tick
    """
    return [tick.cumulative_trades for tick in run.ticks]


def trades_per_tick(run: RunData) -> list[int]:
    """Extract number of trades occurring at each tick.

    Args:
        run: RunData object

    Returns:
        List of trade counts per tick
    """
    return [len(tick.trades) for tick in run.ticks]


def agent_utility_over_time(run: RunData, agent_id: str) -> list[float]:
    """Extract a single agent's utility trajectory.

    Args:
        run: RunData object
        agent_id: ID of the agent to track

    Returns:
        List of utility values indexed by tick
    """
    utilities = []
    for tick in run.ticks:
        for snapshot in tick.agent_snapshots:
            if snapshot.agent_id == agent_id:
                utilities.append(snapshot.utility)
                break
        else:
            # Agent not found in this tick (shouldn't happen normally)
            utilities.append(float("nan"))
    return utilities


def agent_position_over_time(
    run: RunData, agent_id: str
) -> list[tuple[int, int]]:
    """Extract a single agent's position trajectory.

    Args:
        run: RunData object
        agent_id: ID of the agent to track

    Returns:
        List of (row, col) positions indexed by tick
    """
    positions = []
    for tick in run.ticks:
        for snapshot in tick.agent_snapshots:
            if snapshot.agent_id == agent_id:
                positions.append(snapshot.position)
                break
        else:
            positions.append((-1, -1))  # Agent not found
    return positions


def agent_endowment_over_time(
    run: RunData, agent_id: str
) -> list[tuple[float, float]]:
    """Extract a single agent's endowment trajectory.

    Args:
        run: RunData object
        agent_id: ID of the agent to track

    Returns:
        List of (x, y) endowments indexed by tick
    """
    endowments = []
    for tick in run.ticks:
        for snapshot in tick.agent_snapshots:
            if snapshot.agent_id == agent_id:
                endowments.append(snapshot.endowment)
                break
        else:
            endowments.append((float("nan"), float("nan")))
    return endowments


def welfare_gains_over_time(run: RunData) -> list[float]:
    """Extract cumulative welfare gains over time.

    Welfare gain = current welfare - initial welfare

    Args:
        run: RunData object

    Returns:
        List of welfare gains indexed by tick
    """
    if not run.ticks:
        return []
    initial_welfare = run.ticks[0].total_welfare
    return [tick.total_welfare - initial_welfare for tick in run.ticks]


def metric_over_time(
    run: RunData, extractor: Callable[[TickRecord], float]
) -> list[float]:
    """Extract a custom metric over time.

    Args:
        run: RunData object
        extractor: Function that takes a TickRecord and returns a metric value

    Returns:
        List of metric values indexed by tick
    """
    return [extractor(tick) for tick in run.ticks]


def average_utility_over_time(run: RunData) -> list[float]:
    """Extract average agent utility at each tick.

    Args:
        run: RunData object

    Returns:
        List of average utilities indexed by tick
    """
    averages = []
    for tick in run.ticks:
        if tick.agent_snapshots:
            avg = sum(s.utility for s in tick.agent_snapshots) / len(
                tick.agent_snapshots
            )
            averages.append(avg)
        else:
            averages.append(0.0)
    return averages


def utility_variance_over_time(run: RunData) -> list[float]:
    """Extract variance of agent utilities at each tick.

    Useful for measuring inequality dynamics.

    Args:
        run: RunData object

    Returns:
        List of utility variances indexed by tick
    """
    variances = []
    for tick in run.ticks:
        if len(tick.agent_snapshots) < 2:
            variances.append(0.0)
            continue

        utilities = [s.utility for s in tick.agent_snapshots]
        mean = sum(utilities) / len(utilities)
        variance = sum((u - mean) ** 2 for u in utilities) / len(utilities)
        variances.append(variance)
    return variances


def compare_welfare_trajectories(
    run_a: RunData, run_b: RunData
) -> list[float]:
    """Compare welfare trajectories between two runs.

    Returns the difference (run_b - run_a) at each tick.

    Args:
        run_a: First run
        run_b: Second run

    Returns:
        List of welfare differences indexed by tick
    """
    welfare_a = welfare_over_time(run_a)
    welfare_b = welfare_over_time(run_b)

    # Handle different lengths
    min_len = min(len(welfare_a), len(welfare_b))
    return [welfare_b[i] - welfare_a[i] for i in range(min_len)]
