"""
Decision procedure system for agent action selection.

This module defines the DecisionProcedure interface and concrete implementations
for how agents choose actions during the Decide phase.

The DecisionProcedure abstraction enables agent sophistication as an
experimental variable (per VISION.md). Different procedures can implement:
- Full rationality (maximize expected utility)
- Bounded rationality (satisficing, heuristics)
- Learning (RL, evolutionary dynamics)

Reference: ADR-001-TICK-MODEL.md, VISION.md
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from microecon.agent import Agent
    from microecon.actions import Action, ActionContext
    from microecon.bargaining import BargainingProtocol
    from microecon.grid import Position


@dataclass
class DecisionContext:
    """
    Extended context for decision-making.

    Includes ActionContext plus additional information needed for
    evaluating action values (e.g., visible agents, surplus estimates).
    """
    action_context: "ActionContext"
    visible_agents: dict[str, "Agent"]  # agent_id -> Agent (visible to deciding agent)
    bargaining_protocol: "BargainingProtocol"
    agent_positions: dict[str, "Position"]  # All agent positions

    @property
    def current_tick(self) -> int:
        return self.action_context.current_tick


class DecisionProcedure(ABC):
    """
    Abstract base class for agent decision procedures.

    A decision procedure determines how an agent selects actions from
    their available action set. Different procedures model different
    levels of rationality and sophistication.

    Interface:
    - available_actions(): Enumerate valid actions for current state
    - evaluate(): Score an action by expected value
    - choose(): Select the best action

    Reference: ADR-001-TICK-MODEL.md
    """

    @abstractmethod
    def available_actions(
        self,
        agent: "Agent",
        context: DecisionContext,
    ) -> list["Action"]:
        """
        Enumerate all valid actions for the agent in current state.

        Args:
            agent: The deciding agent
            context: Current state context

        Returns:
            List of Action instances that satisfy preconditions
        """
        pass

    @abstractmethod
    def evaluate(
        self,
        agent: "Agent",
        action: "Action",
        context: DecisionContext,
    ) -> float:
        """
        Evaluate an action by its expected value.

        Args:
            agent: The deciding agent
            action: Action to evaluate
            context: Current state context

        Returns:
            Expected value/utility of taking this action
        """
        pass

    @abstractmethod
    def choose(
        self,
        agent: "Agent",
        context: DecisionContext,
    ) -> "Action":
        """
        Choose the best action for the agent.

        Args:
            agent: The deciding agent
            context: Current state context

        Returns:
            The selected Action
        """
        pass

    @abstractmethod
    def evaluate_proposal(
        self,
        agent: "Agent",
        proposer: "Agent",
        context: DecisionContext,
    ) -> bool:
        """
        Evaluate whether to accept a proposal from another agent.

        This is called during Execute phase when the agent receives a proposal.
        The agent decides immediately whether to accept or reject, allowing
        proposal and response to happen in the same tick.

        Args:
            agent: The agent receiving the proposal
            proposer: The agent making the proposal
            context: Current state context

        Returns:
            True to accept the proposal, False to reject
        """
        pass


class RationalDecisionProcedure(DecisionProcedure):
    """
    Baseline rational decision procedure.

    Implements fully rational choice: enumerate available actions,
    evaluate each by expected utility, choose the maximum.

    Evaluation heuristics:
    - Move: Discounted surplus at destination (existing search logic)
    - Propose: Expected trade surplus with target
    - Accept: Surplus from accepting proposal
    - Reject: 0 (return to baseline)
    - Wait: 0 (baseline utility)

    This is the reference implementation for rational behavior.
    Future extensions can add bounded rationality, learning, etc.
    """

    def available_actions(
        self,
        agent: "Agent",
        context: DecisionContext,
    ) -> list["Action"]:
        """
        Enumerate all valid actions.

        Actions considered:
        1. WaitAction (always available)
        2. MoveAction toward each visible agent (if available)
        3. ProposeAction to each co-located agent (if available, no cooldown)

        Note: AcceptAction/RejectAction are not enumerated here. Proposal responses
        are handled immediately during the Execute phase via evaluate_proposal().
        """
        from microecon.actions import (
            WaitAction,
            MoveAction,
            ProposeAction,
        )

        actions: list["Action"] = []

        # Wait is always available
        actions.append(WaitAction())

        # Check interaction state
        interaction = agent.interaction_state

        if interaction.is_available():
            # Can move toward visible agents (excluding cooldown targets)
            # FEAT-006: cooldown targets excluded from utility calculations
            for target_id, target_agent in context.visible_agents.items():
                if target_id == agent.id:
                    continue
                # Skip cooldown targets - no point moving toward them
                if target_id in interaction.cooldowns:
                    continue
                target_pos = context.agent_positions.get(target_id)
                if target_pos is not None:
                    action = MoveAction(target_position=target_pos)
                    if action.preconditions(agent, context.action_context):
                        actions.append(action)

            # Can propose to adjacent agents (includes co-located)
            adjacent = context.action_context.adjacent_agents.get(agent.id, set())
            for target_id in adjacent:
                action = ProposeAction(target_id=target_id)
                if action.preconditions(agent, context.action_context):
                    actions.append(action)

        return actions

    def evaluate(
        self,
        agent: "Agent",
        action: "Action",
        context: DecisionContext,
    ) -> float:
        """
        Evaluate action by expected utility.

        Uses the bargaining protocol to estimate trade surplus.

        Note: Accept/Reject actions are not evaluated here since proposal
        responses are handled immediately during Execute phase.
        """
        from microecon.actions import (
            MoveAction,
            ProposeAction,
            ActionType,
        )

        if action.action_type == ActionType.WAIT:
            # Waiting has zero expected gain
            return 0.0

        if action.action_type == ActionType.MOVE:
            assert isinstance(action, MoveAction)
            return self._evaluate_move(agent, action, context)

        if action.action_type == ActionType.PROPOSE:
            assert isinstance(action, ProposeAction)
            return self._evaluate_propose(agent, action, context)

        return 0.0

    def _evaluate_move(
        self,
        agent: "Agent",
        action: "MoveAction",
        context: DecisionContext,
    ) -> float:
        """
        Evaluate move action by discounted surplus at destination.

        Uses the search module's logic: surplus with best target at destination,
        discounted by distance.

        Note: If already at target position, returns 0 since Propose should be
        preferred over Move when co-located with potential trade partners.
        """
        from microecon.grid import Position

        agent_pos = context.agent_positions.get(agent.id)
        if agent_pos is None:
            return 0.0

        target_pos = action.target_position

        # If already at target position, Move has no value - use Propose instead
        distance = agent_pos.distance_to(target_pos)
        if distance == 0:
            return 0.0

        # Find the best potential trade partner at destination
        best_surplus = 0.0
        for target_id, target_agent in context.visible_agents.items():
            if target_id == agent.id:
                continue

            target_agent_pos = context.agent_positions.get(target_id)
            if target_agent_pos is None:
                continue

            # If this agent is at our target position
            if target_agent_pos == target_pos:
                # Compute expected surplus
                surplus = context.bargaining_protocol.compute_expected_surplus(
                    agent, target_agent
                )
                if surplus > best_surplus:
                    best_surplus = surplus

        # Discount by distance
        discount = agent.discount_factor ** distance

        return best_surplus * discount

    def _evaluate_propose(
        self,
        agent: "Agent",
        action: "ProposeAction",
        context: DecisionContext,
    ) -> float:
        """
        Evaluate propose action by expected trade surplus.

        The target might accept or reject. For now, assume they accept
        if mutual gains exist (optimistic evaluation).
        """
        target_agent = context.visible_agents.get(action.target_id)
        if target_agent is None:
            return 0.0

        # Expected surplus if trade occurs
        surplus = context.bargaining_protocol.compute_expected_surplus(
            agent, target_agent
        )

        # Discount by probability of acceptance (simplified: assume they accept if gains > 0)
        # In reality, we'd model their decision process
        if surplus > 0:
            return surplus
        return 0.0

    def choose(
        self,
        agent: "Agent",
        context: DecisionContext,
    ) -> "Action":
        """
        Choose action with maximum expected utility.

        Tie-breaking (when values are equal):
        - ProposeAction: lexicographically smallest target_id
        - MoveAction: lexicographically smallest target position (row, col)
        - Action type priority: Propose (0) > Move (1) > Wait (2)

        When returning ProposeAction, computes and attaches fallback action
        (MoveAction toward target, or WaitAction if at same position).
        """
        from microecon.actions import WaitAction, ProposeAction, MoveAction

        actions = self.available_actions(agent, context)

        if not actions:
            # Should never happen - Wait is always available
            return WaitAction()

        # Evaluate all actions
        evaluated = [(action, self.evaluate(agent, action, context)) for action in actions]

        # Choose maximum with deterministic tie-breaking
        best_action = None
        best_value = float('-inf')
        best_tie_breaker: tuple = ()

        for action, value in evaluated:
            # Compute tie-breaker: (action_type_priority, secondary_key)
            # When value > 0: prefer Propose > Move > Wait (take beneficial action)
            # When value <= 0: prefer Wait > Move > Propose (don't act without benefit)
            if value > 0:
                # Positive value: prefer actions over waiting
                if isinstance(action, ProposeAction):
                    tie_breaker = (0, action.target_id)
                elif isinstance(action, MoveAction):
                    tie_breaker = (1, (action.target_position.row, action.target_position.col))
                else:
                    tie_breaker = (2, "")
            else:
                # Zero or negative value: prefer waiting over acting
                if isinstance(action, WaitAction):
                    tie_breaker = (0, "")
                elif isinstance(action, MoveAction):
                    tie_breaker = (1, (action.target_position.row, action.target_position.col))
                else:
                    # ProposeAction with no benefit - lowest priority
                    tie_breaker = (2, action.target_id if isinstance(action, ProposeAction) else "")

            # Update if better value, or same value with smaller tie-breaker
            if value > best_value or (value == best_value and tie_breaker < best_tie_breaker):
                best_action = action
                best_value = value
                best_tie_breaker = tie_breaker

        if best_action is None:
            agent.opportunity_cost = 0.0
            return WaitAction()

        # Store opportunity cost: the value of the chosen action
        # This is what the agent gives up if they accept an incoming proposal instead
        # Per AGENT-ARCHITECTURE.md 7.9: acceptance iff surplus >= opportunity_cost
        if isinstance(best_action, WaitAction):
            agent.opportunity_cost = 0.0
        else:
            agent.opportunity_cost = best_value

        # If best action is ProposeAction, compute and attach fallback
        if isinstance(best_action, ProposeAction):
            best_action = self._attach_fallback(agent, best_action, context)

        return best_action

    def _attach_fallback(
        self,
        agent: "Agent",
        propose_action: "ProposeAction",
        context: DecisionContext,
    ) -> "ProposeAction":
        """
        Compute and attach fallback to a ProposeAction.

        Fallback is:
        - MoveAction toward target if not at same position
        - WaitAction if at same position as target

        Per ADR-001: if fallback would be ProposeAction, use WaitAction instead.
        """
        from microecon.actions import WaitAction, ProposeAction, MoveAction

        agent_pos = context.agent_positions.get(agent.id)
        target_pos = context.agent_positions.get(propose_action.target_id)

        if agent_pos is None or target_pos is None:
            # Can't determine positions, use WaitAction as safe fallback
            fallback = WaitAction()
        elif agent_pos == target_pos:
            # Already at same position, can't move closer
            fallback = WaitAction()
        else:
            # Move toward target
            fallback = MoveAction(target_pos)

        # Create new ProposeAction with fallback attached
        return ProposeAction(
            target_id=propose_action.target_id,
            exchange_id=propose_action.exchange_id,
            fallback=fallback,
        )

    def evaluate_proposal(
        self,
        agent: "Agent",
        proposer: "Agent",
        context: DecisionContext,
    ) -> bool:
        """
        Accept proposal if surplus >= opportunity cost.

        Per AGENT-ARCHITECTURE.md 7.9: acceptance is an institutional constraint
        where agent accepts iff trade surplus >= opportunity cost of their
        chosen action. This ensures agents don't give up better alternatives
        for mediocre proposals.

        Opportunity cost was computed and stored during choose() (FEAT-003).
        """
        surplus = context.bargaining_protocol.compute_expected_surplus(agent, proposer)
        return surplus >= agent.opportunity_cost
