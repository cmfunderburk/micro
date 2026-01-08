"""Agent-level tracking and analysis.

Track individual agents across runs and analyze their outcomes.
"""

from dataclasses import dataclass
from typing import Callable

from microecon.logging import RunData, AgentSnapshot, SearchDecision


@dataclass
class AgentOutcome:
    """Summary of an agent's outcome from a simulation run."""

    agent_id: str
    alpha: float  # Preference parameter
    initial_utility: float
    final_utility: float
    utility_gain: float
    num_trades: int
    initial_endowment: tuple[float, float]
    final_endowment: tuple[float, float]


def agent_outcomes(run: RunData) -> list[AgentOutcome]:
    """Extract outcome summaries for all agents in a run.

    Args:
        run: RunData object

    Returns:
        List of AgentOutcome for each agent
    """
    if not run.ticks:
        return []

    # Get initial and final snapshots
    initial_tick = run.ticks[0]
    final_tick = run.ticks[-1]

    # Build lookup for final snapshots
    final_by_id = {s.agent_id: s for s in final_tick.agent_snapshots}

    # Count trades per agent
    trade_counts: dict[str, int] = {}
    for tick in run.ticks:
        for trade in tick.trades:
            trade_counts[trade.agent1_id] = trade_counts.get(trade.agent1_id, 0) + 1
            trade_counts[trade.agent2_id] = trade_counts.get(trade.agent2_id, 0) + 1

    outcomes = []
    for initial in initial_tick.agent_snapshots:
        final = final_by_id.get(initial.agent_id)
        if final is None:
            continue

        outcomes.append(
            AgentOutcome(
                agent_id=initial.agent_id,
                alpha=initial.alpha,
                initial_utility=initial.utility,
                final_utility=final.utility,
                utility_gain=final.utility - initial.utility,
                num_trades=trade_counts.get(initial.agent_id, 0),
                initial_endowment=initial.endowment,
                final_endowment=final.endowment,
            )
        )

    return outcomes


def gains_by_alpha(run: RunData) -> list[tuple[float, float]]:
    """Get utility gains grouped by preference parameter.

    Args:
        run: RunData object

    Returns:
        List of (alpha, utility_gain) tuples
    """
    outcomes = agent_outcomes(run)
    return [(o.alpha, o.utility_gain) for o in outcomes]


def compare_agent_outcomes(
    run_a: RunData, run_b: RunData
) -> list[tuple[str, float, float, float]]:
    """Compare agent outcomes between two runs with same initial conditions.

    Useful for paired comparisons where agents have the same IDs.

    Args:
        run_a: First run
        run_b: Second run

    Returns:
        List of (agent_id, alpha, gain_a, gain_b) tuples
    """
    outcomes_a = {o.agent_id: o for o in agent_outcomes(run_a)}
    outcomes_b = {o.agent_id: o for o in agent_outcomes(run_b)}

    comparisons = []
    for agent_id, outcome_a in outcomes_a.items():
        outcome_b = outcomes_b.get(agent_id)
        if outcome_b is None:
            continue

        comparisons.append(
            (
                agent_id,
                outcome_a.alpha,
                outcome_a.utility_gain,
                outcome_b.utility_gain,
            )
        )

    return comparisons


def winners_and_losers(
    run_a: RunData, run_b: RunData
) -> tuple[list[str], list[str], list[str]]:
    """Identify agents who benefit more from one protocol vs another.

    Args:
        run_a: First run (e.g., Nash)
        run_b: Second run (e.g., Rubinstein)

    Returns:
        Tuple of (winners, losers, ties) where:
        - winners: agents with higher utility_gain in run_b
        - losers: agents with lower utility_gain in run_b
        - ties: agents with equal utility_gain
    """
    comparisons = compare_agent_outcomes(run_a, run_b)

    winners = []
    losers = []
    ties = []

    for agent_id, alpha, gain_a, gain_b in comparisons:
        if gain_b > gain_a + 1e-9:
            winners.append(agent_id)
        elif gain_b < gain_a - 1e-9:
            losers.append(agent_id)
        else:
            ties.append(agent_id)

    return winners, losers, ties


@dataclass
class SearchEfficiencyStats:
    """Statistics about an agent's search behavior."""

    agent_id: str
    total_evaluations: int  # Total targets evaluated across all ticks
    total_movements: int  # Number of ticks with movement
    successful_pursuits: int  # Movements that led to trade
    average_visible: float  # Average visible agents per tick
    average_surplus_available: float  # Average surplus across all visible targets


def search_efficiency(run: RunData) -> list[SearchEfficiencyStats]:
    """Analyze search efficiency for all agents.

    Args:
        run: RunData object

    Returns:
        List of SearchEfficiencyStats for each agent
    """
    # Track data per agent
    agent_data: dict[str, dict] = {}

    for tick in run.ticks:
        for decision in tick.search_decisions:
            aid = decision.agent_id
            if aid not in agent_data:
                agent_data[aid] = {
                    "total_evaluations": 0,
                    "total_visible": 0,
                    "total_surplus": 0.0,
                    "tick_count": 0,
                }

            data = agent_data[aid]
            data["total_evaluations"] += len(decision.evaluations)
            data["total_visible"] += decision.visible_agents
            data["total_surplus"] += sum(
                e.expected_surplus for e in decision.evaluations if e.expected_surplus > 0
            )
            data["tick_count"] += 1

    # Count movements
    movement_counts: dict[str, int] = {}
    for tick in run.ticks:
        for movement in tick.movements:
            if movement.from_pos != movement.to_pos:
                movement_counts[movement.agent_id] = (
                    movement_counts.get(movement.agent_id, 0) + 1
                )

    # Count successful pursuits (movements that led to trades)
    # A pursuit is successful if the agent traded in the tick after moving
    successful_pursuits: dict[str, int] = {}
    for i, tick in enumerate(run.ticks[:-1]):
        next_tick = run.ticks[i + 1]
        traders = set()
        for trade in next_tick.trades:
            traders.add(trade.agent1_id)
            traders.add(trade.agent2_id)

        for movement in tick.movements:
            if movement.from_pos != movement.to_pos and movement.agent_id in traders:
                successful_pursuits[movement.agent_id] = (
                    successful_pursuits.get(movement.agent_id, 0) + 1
                )

    stats = []
    for aid, data in agent_data.items():
        tick_count = data["tick_count"]
        stats.append(
            SearchEfficiencyStats(
                agent_id=aid,
                total_evaluations=data["total_evaluations"],
                total_movements=movement_counts.get(aid, 0),
                successful_pursuits=successful_pursuits.get(aid, 0),
                average_visible=(
                    data["total_visible"] / tick_count if tick_count > 0 else 0
                ),
                average_surplus_available=(
                    data["total_surplus"] / tick_count if tick_count > 0 else 0
                ),
            )
        )

    return stats


def trade_partners(run: RunData, agent_id: str) -> list[str]:
    """Get list of all agents that traded with a given agent.

    Args:
        run: RunData object
        agent_id: ID of the agent

    Returns:
        List of partner agent IDs (may contain duplicates for multiple trades)
    """
    partners = []
    for tick in run.ticks:
        for trade in tick.trades:
            if trade.agent1_id == agent_id:
                partners.append(trade.agent2_id)
            elif trade.agent2_id == agent_id:
                partners.append(trade.agent1_id)
    return partners


def unique_trade_partners(run: RunData, agent_id: str) -> set[str]:
    """Get set of unique agents that traded with a given agent.

    Args:
        run: RunData object
        agent_id: ID of the agent

    Returns:
        Set of unique partner agent IDs
    """
    return set(trade_partners(run, agent_id))
