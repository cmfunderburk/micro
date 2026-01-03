"""
Search behavior for agents on the grid.

Agents search for trade partners by:
1. Observing other agents within perception radius
2. Evaluating each potential partner using Nash bargaining surplus
3. Discounting by distance (δ^ticks_to_reach)
4. Moving toward the partner with highest discounted value

This couples search costs (movement time) with expected gains from trade.

Reference: CLAUDE.md (First Milestone - Target selection logic)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from microecon.grid import Grid, Position
from microecon.bargaining import compute_nash_surplus, BargainingProtocol
from microecon.information import InformationEnvironment

if TYPE_CHECKING:
    from microecon.agent import Agent


@dataclass
class TargetEvaluationResult:
    """
    Evaluation of a single potential trade partner.

    Captures all information computed when evaluating a target,
    enabling analysis of search decisions and missed opportunities.
    """
    target_id: str
    target_position: Position
    distance: float  # Euclidean distance
    ticks_to_reach: int  # Chebyshev distance (movement ticks)
    expected_surplus: float  # Nash bargaining surplus
    discounted_value: float  # surplus * delta^ticks


@dataclass
class SearchResult:
    """
    Result of an agent's search for trade partners.

    Attributes:
        best_target_id: ID of the best potential trade partner, or None
        best_target_position: Position of best target
        discounted_value: Expected value of trading with best target
        visible_agents: Number of agents visible to searcher
    """
    best_target_id: Optional[str]
    best_target_position: Optional[Position]
    discounted_value: float
    visible_agents: int


def evaluate_targets(
    agent: Agent,
    grid: Grid,
    info_env: InformationEnvironment,
    agents_by_id: dict[str, Agent],
    bargaining_protocol: Optional[BargainingProtocol] = None,
) -> SearchResult:
    """
    Evaluate all visible agents and find the best trade target.

    For each agent j in perception radius:
        expected_surplus[j] = protocol.compute_expected_surplus(self, j)
        discounted_value[j] = expected_surplus[j] * δ^(ticks_to_reach_j)

    Returns the target with maximum discounted value.

    Args:
        agent: The searching agent
        grid: The grid with agent positions
        info_env: Information environment for observing types
        agents_by_id: Map from agent ID to Agent object
        bargaining_protocol: Protocol for computing expected surplus (uses Nash if None)

    Returns:
        SearchResult with best target information
    """
    agent_pos = grid.get_position(agent)
    if agent_pos is None:
        return SearchResult(
            best_target_id=None,
            best_target_position=None,
            discounted_value=0.0,
            visible_agents=0,
        )

    observer_type = info_env.get_observable_type(agent)

    best_target_id: Optional[str] = None
    best_target_pos: Optional[Position] = None
    best_value = 0.0
    visible_count = 0

    # Find all agents within perception radius
    for target_id, target_pos, distance in grid.agents_within_radius(
        agent_pos, agent.perception_radius, exclude_center=True
    ):
        target = agents_by_id.get(target_id)
        if target is None:
            continue

        # Check if we can observe this target
        if not info_env.can_observe(agent, target, distance):
            continue

        visible_count += 1

        # Get target's observable type
        target_type = info_env.get_observable_type(target)

        # Compute expected surplus using protocol (or Nash default)
        if bargaining_protocol is not None:
            expected_surplus = bargaining_protocol.compute_expected_surplus(agent, target)
        else:
            expected_surplus = compute_nash_surplus(observer_type, target_type)

        if expected_surplus <= 0:
            continue

        # Compute ticks to reach target (using Chebyshev distance for diagonal movement)
        ticks_to_reach = target_pos.chebyshev_distance_to(agent_pos)

        # Discount by time to reach
        discounted_value = expected_surplus * (agent.discount_factor ** ticks_to_reach)

        # Update if this is the best target, or tie-break by lexicographic agent ID
        if discounted_value > best_value or (
            discounted_value == best_value
            and best_target_id is not None
            and target_id < best_target_id
        ):
            best_value = discounted_value
            best_target_id = target_id
            best_target_pos = target_pos

    return SearchResult(
        best_target_id=best_target_id,
        best_target_position=best_target_pos,
        discounted_value=best_value,
        visible_agents=visible_count,
    )


def evaluate_targets_detailed(
    agent: Agent,
    grid: Grid,
    info_env: InformationEnvironment,
    agents_by_id: dict[str, Agent],
    bargaining_protocol: Optional[BargainingProtocol] = None,
) -> tuple[SearchResult, list[TargetEvaluationResult]]:
    """
    Evaluate all visible agents and return detailed evaluation data.

    Like evaluate_targets(), but also returns evaluation details for every
    visible target, enabling analysis of search decisions and missed opportunities.

    Args:
        agent: The searching agent
        grid: The grid with agent positions
        info_env: Information environment for observing types
        agents_by_id: Map from agent ID to Agent object
        bargaining_protocol: Protocol for computing expected surplus (uses Nash if None)

    Returns:
        Tuple of (SearchResult, list of TargetEvaluationResult for all evaluated targets)
    """
    agent_pos = grid.get_position(agent)
    if agent_pos is None:
        return (
            SearchResult(
                best_target_id=None,
                best_target_position=None,
                discounted_value=0.0,
                visible_agents=0,
            ),
            [],
        )

    observer_type = info_env.get_observable_type(agent)

    best_target_id: Optional[str] = None
    best_target_pos: Optional[Position] = None
    best_value = 0.0
    visible_count = 0
    evaluations: list[TargetEvaluationResult] = []

    # Find all agents within perception radius
    for target_id, target_pos, distance in grid.agents_within_radius(
        agent_pos, agent.perception_radius, exclude_center=True
    ):
        target = agents_by_id.get(target_id)
        if target is None:
            continue

        # Check if we can observe this target
        if not info_env.can_observe(agent, target, distance):
            continue

        visible_count += 1

        # Get target's observable type
        target_type = info_env.get_observable_type(target)

        # Compute expected surplus using protocol (or Nash default)
        if bargaining_protocol is not None:
            expected_surplus = bargaining_protocol.compute_expected_surplus(agent, target)
        else:
            expected_surplus = compute_nash_surplus(observer_type, target_type)

        # Compute ticks to reach target (using Chebyshev distance for diagonal movement)
        ticks_to_reach = target_pos.chebyshev_distance_to(agent_pos)

        # Discount by time to reach
        discounted_value = expected_surplus * (agent.discount_factor ** ticks_to_reach)

        # Record evaluation for all visible agents (not just those with positive surplus)
        evaluations.append(
            TargetEvaluationResult(
                target_id=target_id,
                target_position=target_pos,
                distance=distance,
                ticks_to_reach=ticks_to_reach,
                expected_surplus=expected_surplus,
                discounted_value=discounted_value,
            )
        )

        # Update if this is the best target, or tie-break by lexicographic agent ID
        if expected_surplus > 0 and (
            discounted_value > best_value or (
                discounted_value == best_value
                and best_target_id is not None
                and target_id < best_target_id
            )
        ):
            best_value = discounted_value
            best_target_id = target_id
            best_target_pos = target_pos

    result = SearchResult(
        best_target_id=best_target_id,
        best_target_position=best_target_pos,
        discounted_value=best_value,
        visible_agents=visible_count,
    )

    return result, evaluations


def compute_move_target(
    agent: Agent,
    grid: Grid,
    info_env: InformationEnvironment,
    agents_by_id: dict[str, Agent],
    bargaining_protocol: Optional[BargainingProtocol] = None,
) -> Optional[Position]:
    """
    Determine where an agent should move.

    If there's a beneficial trade target visible, move toward it.
    Otherwise, return None (agent stays put or moves randomly).

    Args:
        agent: The agent deciding where to move
        grid: The grid
        info_env: Information environment
        agents_by_id: Map of agents
        bargaining_protocol: Protocol for computing expected surplus (uses Nash if None)

    Returns:
        Target position to move toward, or None if no good target
    """
    result = evaluate_targets(agent, grid, info_env, agents_by_id, bargaining_protocol)
    return result.best_target_position


def should_trade(
    agent1: Agent,
    agent2: Agent,
    info_env: InformationEnvironment,
    bargaining_protocol: Optional[BargainingProtocol] = None,
) -> bool:
    """
    Check if two agents at the same position should trade.

    Trade occurs if there are mutual gains (both expect positive surplus).

    Args:
        agent1: First agent
        agent2: Second agent
        info_env: Information environment
        bargaining_protocol: Protocol for computing expected surplus (uses Nash if None)

    Returns:
        True if trade should occur
    """
    # Check both agents expect gains
    if bargaining_protocol is not None:
        surplus1 = bargaining_protocol.compute_expected_surplus(agent1, agent2)
        surplus2 = bargaining_protocol.compute_expected_surplus(agent2, agent1)
    else:
        type1 = info_env.get_observable_type(agent1)
        type2 = info_env.get_observable_type(agent2)
        surplus1 = compute_nash_surplus(type1, type2)
        surplus2 = compute_nash_surplus(type2, type1)

    return surplus1 > 0 and surplus2 > 0
