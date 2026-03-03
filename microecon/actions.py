"""
Action system for agent decision-making.

This module defines the Action ABC and concrete action types for the
3-phase tick model (Perceive-Decide-Execute). Actions are explicit choices
that agents make during the Decide phase.

Action types chosen during Decide phase:
- MoveAction: Move toward a target position
- ProposeAction: Initiate exchange with adjacent agent
- WaitAction: Take no action this tick

Coordination actions (evaluated during Execute, not chosen during Decide):
- AcceptAction: Accept a proposal (trade executes)
- RejectAction: Reject a proposal (proposer gets cooldown)

Whether an agent accepts a proposal depends on their opportunity cost (the
value of their chosen action). This handles the coordination constraint that
both parties must mutually want to trade for it to occur.

Reference: ADR-001-TICK-MODEL.md, ADR-003-EXCHANGE-SEQUENCE.md
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any
import uuid

if TYPE_CHECKING:
    from microecon.agent import Agent
    from microecon.grid import Position


class ActionType(Enum):
    """Enumeration of action types for categorization."""
    MOVE = auto()
    PROPOSE = auto()
    ACCEPT = auto()
    REJECT = auto()
    WAIT = auto()


class ActionTag(Enum):
    """Tags for action categorization (analytics, filtering)."""
    MOVEMENT = auto()      # Changes agent position
    EXCHANGE = auto()      # Related to trade/bargaining
    PROPOSAL = auto()      # Initiates or responds to proposal
    PASSIVE = auto()       # Takes no action


class Action(ABC):
    """
    Abstract base class for agent actions.

    Actions represent explicit choices agents make during the Decide phase.
    Each action has:
    - A type identifier
    - A cost in terms of resource/tick budget
    - Preconditions that must be satisfied
    - A transform that produces state changes
    - Tags for categorization

    Reference: ADR-001-TICK-MODEL.md
    """

    def __init__(self) -> None:
        # Unique identifier for this action instance
        self._action_id = str(uuid.uuid4())[:8]

    @property
    def action_id(self) -> str:
        """Unique identifier for this action instance."""
        return self._action_id

    @property
    @abstractmethod
    def action_type(self) -> ActionType:
        """Return the type of this action."""
        pass

    @property
    @abstractmethod
    def tags(self) -> set[ActionTag]:
        """Return tags for this action (for filtering/analytics)."""
        pass

    @abstractmethod
    def cost(self) -> int:
        """
        Return the cost of this action in action budget units.

        Most actions cost 1 (one action per tick). Some future actions
        might have different costs.
        """
        pass

    @abstractmethod
    def preconditions(self, agent: Agent, context: ActionContext) -> bool:
        """
        Check if this action can be taken by the agent.

        Args:
            agent: The agent attempting the action
            context: Current state context for validation

        Returns:
            True if all preconditions are satisfied
        """
        pass

    @abstractmethod
    def describe(self) -> str:
        """Return human-readable description of this action."""
        pass


@dataclass
class ActionContext:
    """
    Context for validating and executing actions.

    Provides the frozen state information needed to check preconditions
    and execute actions.
    """
    current_tick: int
    agent_positions: dict[str, "Position"]
    agent_interaction_states: dict[str, Any]  # AgentInteractionState copies
    co_located_agents: dict[str, set[str]]  # agent_id -> set of co-located agent_ids
    adjacent_agents: dict[str, set[str]]  # agent_id -> set of adjacent agent_ids (includes co-located)
    pending_proposals: dict[str, str]  # target_id -> proposer_id (who proposed to target)

    def get_position(self, agent_id: str) -> "Position | None":
        """Get agent's position."""
        return self.agent_positions.get(agent_id)

    def are_co_located(self, agent_a_id: str, agent_b_id: str) -> bool:
        """Check if two agents are at the same position."""
        co_located = self.co_located_agents.get(agent_a_id, set())
        return agent_b_id in co_located

    def are_adjacent(self, agent_a_id: str, agent_b_id: str) -> bool:
        """Check if two agents are adjacent (Chebyshev distance <= 1)."""
        adjacent = self.adjacent_agents.get(agent_a_id, set())
        return agent_b_id in adjacent

    def has_pending_proposal_from(self, target_id: str, proposer_id: str) -> bool:
        """Check if target has pending proposal from proposer."""
        return self.pending_proposals.get(target_id) == proposer_id


# =============================================================================
# Concrete Action Types
# =============================================================================


class MoveAction(Action):
    """
    Move toward a target position.

    The agent moves up to their movement_budget squares toward the target.
    Movement is blocked if the agent is locked (in proposal or negotiation).

    Preconditions:
    - Agent is in AVAILABLE state (not locked)

    Effects:
    - Agent position changes toward target_position
    """

    def __init__(self, target_position: "Position") -> None:
        super().__init__()
        self.target_position = target_position

    @property
    def action_type(self) -> ActionType:
        return ActionType.MOVE

    @property
    def tags(self) -> set[ActionTag]:
        return {ActionTag.MOVEMENT}

    def cost(self) -> int:
        return 1

    def preconditions(self, agent: Agent, context: ActionContext) -> bool:
        """Agent must be available (not locked in proposal/negotiation)."""
        return agent.interaction_state.is_available()

    def describe(self) -> str:
        return f"Move toward {self.target_position}"


class ProposeAction(Action):
    """
    Propose exchange to an adjacent agent.

    Initiates the exchange sequence. The proposer attempts to trade with
    the target. If the proposal fails (rejected or not selected), the
    proposer executes their fallback action instead.

    Preconditions:
    - Agent is in AVAILABLE state
    - Agent not in cooldown for target
    - Agent and target are adjacent (Chebyshev distance <= 1)

    Effects:
    - If accepted: trade executes, both parties consume action budget
    - If rejected: proposer executes fallback, cooldown added for target
    - If not selected: proposer executes fallback, no cooldown

    Attributes:
        target_id: ID of the agent to propose to
        exchange_id: Unique identifier for this exchange attempt
        fallback: Action to execute if proposal fails (MoveAction or WaitAction)

    Reference: AGENT-ARCHITECTURE.md §7.1-7.4
    """

    def __init__(
        self,
        target_id: str,
        exchange_id: str | None = None,
        fallback: Action | None = None,
    ) -> None:
        super().__init__()
        self.target_id = target_id
        # exchange_id generated when action is created, propagates through events
        self.exchange_id = exchange_id or str(uuid.uuid4())[:8]
        # Validate fallback is not a ProposeAction (would cause recursion)
        if fallback is not None and isinstance(fallback, ProposeAction):
            raise ValueError(
                "ProposeAction fallback cannot be another ProposeAction. "
                "Use MoveAction or WaitAction instead."
            )
        self.fallback = fallback

    @property
    def action_type(self) -> ActionType:
        return ActionType.PROPOSE

    @property
    def tags(self) -> set[ActionTag]:
        return {ActionTag.EXCHANGE, ActionTag.PROPOSAL}

    def cost(self) -> int:
        return 1

    def preconditions(self, agent: Agent, context: ActionContext) -> bool:
        """
        Agent must be available, not in cooldown, and adjacent to target.

        Note: "Adjacent" includes both co-located (same position) and
        neighboring positions (Chebyshev distance = 1). This allows trades
        between agents in adjacent squares, preventing the coordination
        failure where agents oscillate between adjacent positions.
        """
        # Must be available
        if not agent.interaction_state.is_available():
            return False

        # Must not be in cooldown for this target
        if not agent.interaction_state.can_propose_to(self.target_id):
            return False

        # Must be adjacent to target (includes co-located)
        if not context.are_adjacent(agent.id, self.target_id):
            return False

        return True

    def describe(self) -> str:
        return f"Propose exchange to {self.target_id}"


class AcceptAction(Action):
    """
    Accept a pending proposal from another agent.

    Note: This action type exists for architectural completeness but is NOT
    currently enumerated during the Decide phase. In the current same-tick
    proposal resolution model, acceptance is evaluated as an institutional
    constraint during Execute (based on opportunity cost), not as an explicit
    agent action choice.

    This class is retained for potential future multi-tick negotiation support.

    Reference: ADR-002-INTERACTION-STATE.md
    """

    def __init__(self, proposer_id: str) -> None:
        super().__init__()
        self.proposer_id = proposer_id

    @property
    def action_type(self) -> ActionType:
        return ActionType.ACCEPT

    @property
    def tags(self) -> set[ActionTag]:
        return {ActionTag.EXCHANGE, ActionTag.PROPOSAL}

    def cost(self) -> int:
        return 1

    def preconditions(self, agent: Agent, context: ActionContext) -> bool:
        """Agent must have pending proposal from proposer."""
        return context.has_pending_proposal_from(agent.id, self.proposer_id)

    def describe(self) -> str:
        return f"Accept proposal from {self.proposer_id}"


class RejectAction(Action):
    """
    Reject a pending proposal from another agent.

    Note: This action type exists for architectural completeness but is NOT
    currently enumerated during the Decide phase. In the current same-tick
    proposal resolution model, rejection happens during Execute when the
    target's surplus is less than their opportunity cost.

    This class is retained for potential future multi-tick negotiation support.

    The proposer returns to AVAILABLE state with a cooldown for this target.

    Preconditions:
    - Agent has pending proposal from specified proposer

    Effects:
    - Proposer enters AVAILABLE state
    - Proposer gets cooldown for this agent (cannot re-propose for 3 ticks)

    Reference: ADR-002-INTERACTION-STATE.md
    """

    def __init__(self, proposer_id: str) -> None:
        super().__init__()
        self.proposer_id = proposer_id

    @property
    def action_type(self) -> ActionType:
        return ActionType.REJECT

    @property
    def tags(self) -> set[ActionTag]:
        return {ActionTag.EXCHANGE, ActionTag.PROPOSAL}

    def cost(self) -> int:
        return 1

    def preconditions(self, agent: Agent, context: ActionContext) -> bool:
        """Agent must have pending proposal from proposer."""
        return context.has_pending_proposal_from(agent.id, self.proposer_id)

    def describe(self) -> str:
        return f"Reject proposal from {self.proposer_id}"


class WaitAction(Action):
    """
    Take no action this tick.

    Used when agent has no beneficial action to take, or is waiting
    for something (e.g., proposal response timeout).

    Preconditions:
    - None (can always wait)

    Effects:
    - No state change (except time passing)
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def action_type(self) -> ActionType:
        return ActionType.WAIT

    @property
    def tags(self) -> set[ActionTag]:
        return {ActionTag.PASSIVE}

    def cost(self) -> int:
        return 1

    def preconditions(self, agent: Agent, context: ActionContext) -> bool:
        """Can always wait."""
        return True

    def describe(self) -> str:
        return "Wait"


# =============================================================================
# Action Result (for execution phase)
# =============================================================================


@dataclass
class ActionResult:
    """
    Result of executing an action.

    Captures what happened when an action was executed, including
    success/failure and any side effects.
    """
    action: Action
    success: bool
    message: str = ""
    # For tracking through events
    exchange_id: str | None = None
