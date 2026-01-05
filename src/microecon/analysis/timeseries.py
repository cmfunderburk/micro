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


def _compute_mrs(alpha: float, x: float, y: float) -> float:
    """Compute Marginal Rate of Substitution for Cobb-Douglas preferences.

    MRS = (α / (1-α)) * (y / x)

    Returns inf if x = 0, 0 if α = 1, and handles edge cases.
    """
    if x <= 0:
        return float("inf")
    if alpha >= 1.0:
        return 0.0
    if alpha <= 0.0:
        return float("inf")
    return (alpha / (1.0 - alpha)) * (y / x)


def mrs_over_time(run: RunData) -> list[dict[str, float]]:
    """Extract MRS for each agent at each tick.

    Marginal Rate of Substitution indicates willingness to trade y for x.
    For Cobb-Douglas: MRS = (α / (1-α)) * (y / x).

    In efficient markets, MRS should converge across agents as trade
    equalizes marginal valuations.

    Args:
        run: RunData object

    Returns:
        List of dicts mapping agent_id -> MRS at each tick
    """
    result = []
    for tick in run.ticks:
        tick_mrs = {}
        for snapshot in tick.agent_snapshots:
            x, y = snapshot.endowment
            mrs = _compute_mrs(snapshot.alpha, x, y)
            tick_mrs[snapshot.agent_id] = mrs
        result.append(tick_mrs)
    return result


def mrs_dispersion_over_time(run: RunData) -> list[float]:
    """Track MRS dispersion (coefficient of variation) over time.

    Lower dispersion indicates convergence toward market-clearing prices.
    Uses coefficient of variation (std/mean) to normalize across scales.

    Args:
        run: RunData object

    Returns:
        List of MRS CV values indexed by tick (lower = more convergence)
    """
    import math

    dispersions = []
    for tick in run.ticks:
        mrs_values = []
        for snapshot in tick.agent_snapshots:
            x, y = snapshot.endowment
            mrs = _compute_mrs(snapshot.alpha, x, y)
            if math.isfinite(mrs):
                mrs_values.append(mrs)

        if len(mrs_values) < 2:
            dispersions.append(float("nan"))
            continue

        mean = sum(mrs_values) / len(mrs_values)
        if mean <= 0:
            dispersions.append(float("nan"))
            continue

        variance = sum((m - mean) ** 2 for m in mrs_values) / len(mrs_values)
        std = math.sqrt(variance)
        cv = std / mean  # Coefficient of variation
        dispersions.append(cv)

    return dispersions
