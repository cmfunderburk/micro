"""
Search behavior for agents on the grid.

Agents search for trade partners by:
1. Observing other agents within perception radius
2. Evaluating each potential partner using Nash bargaining surplus
3. Discounting by distance (δ^ticks_to_reach)
4. Moving toward the partner with highest discounted value

This couples search costs (movement time) with expected gains from trade.

When agents have beliefs enabled (see ADR-BELIEF-ARCHITECTURE.md), they can use
their beliefs about partner types instead of raw observations. This allows
learning from past interactions to influence future search decisions.

Reference: CLAUDE.md (First Milestone - Target selection logic)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from microecon.grid import Grid, Position
from microecon.bargaining import compute_nash_surplus, BargainingProtocol
from microecon.information import InformationEnvironment
from microecon.preferences import CobbDouglas

if TYPE_CHECKING:
    from microecon.agent import Agent, AgentType


@dataclass
class TargetEvaluationResult:
    """
    Evaluation of a single potential trade partner.

    Captures all information computed when evaluating a target,
    enabling analysis of search decisions and missed opportunities.
    """
    target_id: str
    target_position: Position
    distance: float  # Chebyshev distance (same as ticks_to_reach, perception is square)
    ticks_to_reach: int  # Chebyshev distance (movement ticks)
    expected_surplus: float  # Nash bargaining surplus
    discounted_value: float  # surplus * delta^ticks
    observed_alpha: float  # Alpha as perceived by observer (may differ from true if noisy)
    used_belief: bool = False  # Whether belief was used instead of observation
    believed_alpha: Optional[float] = None  # Alpha from belief (if used)


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


def _get_effective_type(
    observer: Agent,
    target: Agent,
    observed_type: AgentType,
    use_beliefs: bool,
) -> tuple[AgentType, bool, Optional[float]]:
    """
    Get the type to use for surplus calculation, incorporating beliefs if enabled.

    Args:
        observer: The agent doing the evaluation
        target: The agent being evaluated
        observed_type: The type from the information environment
        use_beliefs: Whether to use beliefs if available

    Returns:
        Tuple of (effective_type, used_belief, believed_alpha)
    """
    from microecon.agent import AgentType
    from microecon.bundle import Bundle

    if not use_beliefs or not observer.has_beliefs:
        return observed_type, False, None

    believed_alpha = observer.get_believed_alpha(target.id)
    if believed_alpha is None:
        return observed_type, False, None

    # Construct type using believed alpha but observed endowment
    # (endowments are directly observable in our model)
    believed_type = AgentType(
        preferences=CobbDouglas(believed_alpha),
        endowment=observed_type.endowment,
    )
    return believed_type, True, believed_alpha


def evaluate_targets(
    agent: Agent,
    grid: Grid,
    info_env: InformationEnvironment,
    agents_by_id: dict[str, Agent],
    bargaining_protocol: Optional[BargainingProtocol] = None,
    use_beliefs: bool = True,
) -> SearchResult:
    """
    Evaluate all visible agents and find the best trade target.

    For each agent j in perception radius:
        expected_surplus[j] = protocol.compute_expected_surplus(self, j)
        discounted_value[j] = expected_surplus[j] * δ^(ticks_to_reach_j)

    Returns the target with maximum discounted value.

    If the agent has beliefs enabled and use_beliefs=True, beliefs about
    partner types are used for surplus calculation instead of raw observations.
    This allows agents to learn from past interactions.

    Args:
        agent: The searching agent
        grid: The grid with agent positions
        info_env: Information environment for observing types
        agents_by_id: Map from agent ID to Agent object
        bargaining_protocol: Protocol for computing expected surplus.
            If provided, uses protocol.compute_expected_surplus().
            If None, falls back to Nash surplus heuristic.
        use_beliefs: Whether to use beliefs instead of observations (default True)

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

    # Observer knows their own true type with current holdings (no noise applied to self)
    from microecon.agent import AgentType
    observer_type = AgentType(
        preferences=agent.preferences,
        endowment=agent.holdings,  # Use current holdings, not initial endowment
    )

    best_target_id: Optional[str] = None
    best_target_pos: Optional[Position] = None
    best_value = 0.0
    visible_count = 0

    # Find all agents within perception radius (including co-located for Propose actions)
    for target_id, target_pos, distance in grid.agents_within_radius(
        agent_pos, agent.perception_radius, exclude_center=False
    ):
        target = agents_by_id.get(target_id)
        if target is None:
            continue

        # Skip self (can't target yourself)
        if target_id == agent.id:
            continue

        # Skip targets on cooldown (FEAT-006: cooldown exclusion from search)
        # Per AGENT-ARCHITECTURE.md 7.2: cooldown targets excluded from utility calculations
        if target_id in agent.interaction_state.cooldowns:
            continue

        # Check if we can observe this target
        if not info_env.can_observe(agent, target, distance):
            continue

        visible_count += 1

        # Get target's observable type (may include noise depending on info_env)
        observed_type = info_env.get_observable_type(target)

        # Get effective type (may use beliefs if available)
        effective_type, _, _ = _get_effective_type(agent, target, observed_type, use_beliefs)

        # Compute expected surplus based on observer's beliefs about target
        if bargaining_protocol is not None:
            # Use protocol's surplus calculation for institution-aware search
            expected_surplus = bargaining_protocol.compute_expected_surplus(
                agent, target,
                effective_type_1=observer_type,
                effective_type_2=effective_type,
            )
        else:
            # Fall back to Nash surplus heuristic
            expected_surplus = compute_nash_surplus(observer_type, effective_type)

        if expected_surplus <= 0:
            continue

        # Compute ticks to reach target (using Chebyshev distance, respects grid wrapping)
        ticks_to_reach = grid.chebyshev_distance(agent_pos, target_pos)

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
    use_beliefs: bool = True,
) -> tuple[SearchResult, list[TargetEvaluationResult]]:
    """
    Evaluate all visible agents and return detailed evaluation data.

    Like evaluate_targets(), but also returns evaluation details for every
    visible target, enabling analysis of search decisions and missed opportunities.

    If the agent has beliefs enabled and use_beliefs=True, beliefs about
    partner types are used for surplus calculation instead of raw observations.

    Args:
        agent: The searching agent
        grid: The grid with agent positions
        info_env: Information environment for observing types
        agents_by_id: Map from agent ID to Agent object
        bargaining_protocol: Protocol for computing expected surplus.
            If provided, uses protocol.compute_expected_surplus().
            If None, falls back to Nash surplus heuristic.
        use_beliefs: Whether to use beliefs instead of observations (default True)

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

    # Observer knows their own true type with current holdings (no noise applied to self)
    from microecon.agent import AgentType
    observer_type = AgentType(
        preferences=agent.preferences,
        endowment=agent.holdings,  # Use current holdings, not initial endowment
    )

    best_target_id: Optional[str] = None
    best_target_pos: Optional[Position] = None
    best_value = 0.0
    visible_count = 0
    evaluations: list[TargetEvaluationResult] = []

    # Find all agents within perception radius (including co-located for Propose actions)
    for target_id, target_pos, distance in grid.agents_within_radius(
        agent_pos, agent.perception_radius, exclude_center=False
    ):
        target = agents_by_id.get(target_id)
        if target is None:
            continue

        # Skip self (can't target yourself)
        if target_id == agent.id:
            continue

        # Skip targets on cooldown (FEAT-006: cooldown exclusion from search)
        # Per AGENT-ARCHITECTURE.md 7.2: cooldown targets excluded from utility calculations
        if target_id in agent.interaction_state.cooldowns:
            continue

        # Check if we can observe this target
        if not info_env.can_observe(agent, target, distance):
            continue

        visible_count += 1

        # Get target's observable type (may include noise depending on info_env)
        observed_type = info_env.get_observable_type(target)

        # Get effective type (may use beliefs if available)
        effective_type, used_belief, believed_alpha = _get_effective_type(
            agent, target, observed_type, use_beliefs
        )

        # Compute expected surplus based on observer's beliefs about target
        if bargaining_protocol is not None:
            # Use protocol's surplus calculation for institution-aware search
            expected_surplus = bargaining_protocol.compute_expected_surplus(
                agent, target,
                effective_type_1=observer_type,
                effective_type_2=effective_type,
            )
        else:
            # Fall back to Nash surplus heuristic
            expected_surplus = compute_nash_surplus(observer_type, effective_type)

        # Compute ticks to reach target (using Chebyshev distance, respects grid wrapping)
        ticks_to_reach = grid.chebyshev_distance(agent_pos, target_pos)

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
                observed_alpha=observed_type.preferences.alpha,
                used_belief=used_belief,
                believed_alpha=believed_alpha,
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
    use_beliefs: bool = True,
) -> Optional[Position]:
    """
    Determine where an agent should move.

    If there's a beneficial trade target visible, move toward it.
    Otherwise, return None (agent stays put or moves randomly).

    If the agent has beliefs enabled and use_beliefs=True, beliefs about
    partner types are used for target evaluation.

    Args:
        agent: The agent deciding where to move
        grid: The grid
        info_env: Information environment
        agents_by_id: Map of agents
        bargaining_protocol: Protocol for computing expected surplus (uses Nash if None)
        use_beliefs: Whether to use beliefs instead of observations (default True)

    Returns:
        Target position to move toward, or None if no good target
    """
    result = evaluate_targets(
        agent, grid, info_env, agents_by_id, bargaining_protocol, use_beliefs
    )
    return result.best_target_position


def should_trade(
    agent1: Agent,
    agent2: Agent,
    info_env: InformationEnvironment,
    bargaining_protocol: Optional[BargainingProtocol] = None,
    use_beliefs: bool = True,
) -> bool:
    """
    Check if two agents at the same position should trade.

    Trade occurs if both agents believe there are mutual gains based on
    their observations (or beliefs, if enabled). Each agent knows their
    own true type but observes the other through the information environment.

    If agents have beliefs enabled and use_beliefs=True, beliefs about
    partner types are used instead of raw observations.

    Args:
        agent1: First agent
        agent2: Second agent
        info_env: Information environment
        bargaining_protocol: Protocol (ignored - trade willingness uses Nash heuristic)
        use_beliefs: Whether to use beliefs instead of observations (default True)

    Returns:
        True if both agents believe trade would be beneficial
    """
    from microecon.agent import AgentType

    # Each agent knows their own true type
    true_type1 = AgentType.from_private_state(agent1.private_state)
    true_type2 = AgentType.from_private_state(agent2.private_state)

    # Each agent observes the other through the info environment
    observed_type2 = info_env.get_observable_type(agent2)  # agent1's view of agent2
    observed_type1 = info_env.get_observable_type(agent1)  # agent2's view of agent1

    # Get effective types (may use beliefs if available)
    effective_type2, _, _ = _get_effective_type(agent1, agent2, observed_type2, use_beliefs)
    effective_type1, _, _ = _get_effective_type(agent2, agent1, observed_type1, use_beliefs)

    # Agent1 evaluates: "do I expect gains trading with what I believe about agent2?"
    surplus1 = compute_nash_surplus(true_type1, effective_type2)

    # Agent2 evaluates: "do I expect gains trading with what I believe about agent1?"
    surplus2 = compute_nash_surplus(true_type2, effective_type1)

    return surplus1 > 0 and surplus2 > 0
