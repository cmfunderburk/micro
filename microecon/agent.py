"""
Agent representation with separation of private state and observable type.

This module implements the core abstraction where agents have:
1. Private state: True characteristics (preferences, endowments)
2. Observable type: What other agents can perceive
3. Holdings: Current goods owned (mutable, updated by trades)
4. Interaction state: State machine for exchange sequences
5. Memory and beliefs: Observation history and learned beliefs (optional)

This separation is architecturally critical for future information environments:
- Full information: type = private state (MVP default)
- Private information: type may be hidden or partially revealed
- Signaling: agents take costly actions to reveal type

Reference: CLAUDE.md, O&R-G Ch 11, Kreps II Ch 20-21
See also: ADR-BELIEF-ARCHITECTURE.md for belief system design
See also: ADR-002-INTERACTION-STATE.md for interaction state machine
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
import uuid

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas


# =============================================================================
# Interaction State Machine (ADR-002)
# =============================================================================


class InteractionState(Enum):
    """
    Possible states in the agent interaction state machine.

    State transitions:
    - AVAILABLE -> PROPOSAL_PENDING: Agent chooses Propose(target) action
    - AVAILABLE -> NEGOTIATING: Received proposal, chose Accept action
    - PROPOSAL_PENDING -> NEGOTIATING: Target accepted
    - PROPOSAL_PENDING -> AVAILABLE: Target rejected (+ cooldown), timeout, or co-location lost
    - NEGOTIATING -> AVAILABLE: Protocol completes or co-location lost

    Reference: ADR-002-INTERACTION-STATE.md
    """
    AVAILABLE = "available"
    PROPOSAL_PENDING = "proposal_pending"
    NEGOTIATING = "negotiating"


@dataclass
class AgentInteractionState:
    """
    Tracks an agent's current interaction state and context.

    This dataclass captures:
    - Current state in the interaction state machine
    - Proposal tracking (if PROPOSAL_PENDING)
    - Negotiation tracking (if NEGOTIATING)
    - Per-partner cooldowns (orthogonal to state)

    Cooldown semantics:
    - Created when own proposal is rejected: cooldowns[target] = 3
    - Decremented each tick
    - Removed when reaches 0
    - Agent cannot propose to target while cooldown active

    Reference: ADR-002-INTERACTION-STATE.md
    """
    state: InteractionState = InteractionState.AVAILABLE

    # If PROPOSAL_PENDING: who we proposed to and when
    proposal_target: str | None = None
    proposal_tick: int | None = None

    # If NEGOTIATING: who we're negotiating with and protocol details
    negotiation_partner: str | None = None
    negotiation_start_tick: int | None = None

    # Per-partner cooldowns: agent_id -> ticks remaining
    # Prevents re-proposing to recently-rejecting partners
    cooldowns: dict[str, int] = field(default_factory=dict)

    def is_available(self) -> bool:
        """Check if agent can take new actions."""
        return self.state == InteractionState.AVAILABLE

    def is_locked(self) -> bool:
        """Check if agent is locked (in proposal or negotiation)."""
        return self.state != InteractionState.AVAILABLE

    def can_propose_to(self, target_id: str) -> bool:
        """Check if agent can propose to target (available + no cooldown)."""
        return self.is_available() and target_id not in self.cooldowns

    def enter_proposal_pending(self, target_id: str, tick: int) -> None:
        """Transition to PROPOSAL_PENDING state."""
        self.state = InteractionState.PROPOSAL_PENDING
        self.proposal_target = target_id
        self.proposal_tick = tick
        # Clear negotiation tracking
        self.negotiation_partner = None
        self.negotiation_start_tick = None

    def enter_negotiating(self, partner_id: str, tick: int) -> None:
        """Transition to NEGOTIATING state."""
        self.state = InteractionState.NEGOTIATING
        self.negotiation_partner = partner_id
        self.negotiation_start_tick = tick
        # Clear proposal tracking
        self.proposal_target = None
        self.proposal_tick = None

    def enter_available(self, add_cooldown_for: str | None = None, cooldown_duration: int = 3) -> None:
        """
        Transition to AVAILABLE state.

        Args:
            add_cooldown_for: If specified, add cooldown for this agent ID
            cooldown_duration: Cooldown duration in ticks (default 3)
        """
        self.state = InteractionState.AVAILABLE
        self.proposal_target = None
        self.proposal_tick = None
        self.negotiation_partner = None
        self.negotiation_start_tick = None

        if add_cooldown_for is not None:
            self.cooldowns[add_cooldown_for] = cooldown_duration

    def tick_cooldowns(self) -> None:
        """Decrement cooldowns and remove expired ones. Called at start of tick."""
        expired = []
        for agent_id, remaining in self.cooldowns.items():
            if remaining <= 1:
                expired.append(agent_id)
            else:
                self.cooldowns[agent_id] = remaining - 1
        for agent_id in expired:
            del self.cooldowns[agent_id]

    def copy(self) -> "AgentInteractionState":
        """Create a copy of this state (for snapshots)."""
        return AgentInteractionState(
            state=self.state,
            proposal_target=self.proposal_target,
            proposal_tick=self.proposal_tick,
            negotiation_partner=self.negotiation_partner,
            negotiation_start_tick=self.negotiation_start_tick,
            cooldowns=dict(self.cooldowns),
        )

if TYPE_CHECKING:
    from microecon.beliefs import (
        AgentMemory,
        PriceBelief,
        TypeBelief,
        BeliefUpdateRule,
    )


@dataclass
class AgentPrivateState:
    """
    An agent's true private characteristics.

    These are the agent's actual preferences and holdings, which determine
    real behavior and payoffs. In complete information settings, these are
    observable; in incomplete information, they may be hidden.

    Attributes:
        preferences: The agent's utility function (Cobb-Douglas for MVP)
        endowment: The agent's current holdings of both goods
    """
    preferences: CobbDouglas
    endowment: Bundle

    def utility(self) -> float:
        """Compute utility from current endowment."""
        return self.preferences.utility(self.endowment)

    def utility_of(self, bundle: Bundle) -> float:
        """Compute utility of an arbitrary bundle."""
        return self.preferences.utility(bundle)


@dataclass(frozen=True)
class AgentType:
    """
    An agent's publicly observable characteristics.

    In game-theoretic terms, a "type" is the information available to other
    players for conditioning their strategies. The content of type depends
    on the information environment.

    For the MVP (full information), type = private state.
    Future extensions may have type reveal only partial information.

    Attributes:
        preferences: Observable preference parameter (alpha for Cobb-Douglas)
        endowment: Observable holdings
    """
    preferences: CobbDouglas
    endowment: Bundle

    @staticmethod
    def from_private_state(state: AgentPrivateState) -> AgentType:
        """Create observable type from private state (full information case)."""
        return AgentType(
            preferences=state.preferences,
            endowment=state.endowment,
        )


@dataclass
class Agent:
    """
    An economic agent in the simulation.

    Agents have:
    - A unique identifier
    - Private state (true preferences and endowments)
    - Holdings (current goods, mutable - updated by trades)
    - Search parameters (perception radius, discount factor)
    - Movement budget per tick
    - Optional: Memory and beliefs for learning (see ADR-BELIEF-ARCHITECTURE.md)

    The observable type is generated by the information environment,
    not stored directly on the agent.

    **Holdings vs Endowment:**
    - `endowment`: Initial allocation, immutable after construction. Defines the
      disagreement point for Nash bargaining (O&R Ch 2).
    - `holdings`: Current goods owned, mutable. Updated by trades. Initialized
      to a copy of endowment.

    **Interaction State (ADR-002):**
    Tracks agent's state in the exchange sequence state machine:
    - AVAILABLE: Can take actions, receive/send proposals
    - PROPOSAL_PENDING: Has outbound proposal awaiting response
    - NEGOTIATING: In active negotiation with partner

    Attributes:
        id: Unique identifier
        private_state: True characteristics (preferences, initial endowment)
        holdings: Current goods owned (mutable, updated by trades)
        interaction_state: State machine for exchange sequences (ADR-002)
        perception_radius: How far the agent can see (in grid units)
        discount_factor: Time preference (delta), used to discount future trades
        bargaining_power: Intrinsic institutional bargaining power (w_i), used by
            AsymmetricNashBargainingProtocol. Independent of discount_factor.
        movement_budget: Squares per tick the agent can move
        memory: Observation and interaction history (optional)
        price_belief: Belief about exchange rates (optional)
        type_beliefs: Beliefs about other agents' types (optional)
        update_rule: Rule for updating beliefs (optional)
    """
    private_state: AgentPrivateState
    perception_radius: float = 3.0
    discount_factor: float = 0.95
    bargaining_power: float = 1.0
    movement_budget: int = 1
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Holdings: current goods owned (mutable). Initialized from endowment in __post_init__
    _holdings: Bundle | None = field(default=None, repr=False)

    # Interaction state machine (ADR-002). Initialized in __post_init__
    _interaction_state: AgentInteractionState | None = field(default=None, repr=False)

    # Belief system (optional, for backward compatibility)
    # These are initialized to None by default; use enable_beliefs() to activate
    memory: AgentMemory | None = field(default=None, repr=False)
    price_belief: PriceBelief | None = field(default=None, repr=False)
    type_beliefs: dict[str, TypeBelief] | None = field(default=None, repr=False)
    update_rule: BeliefUpdateRule | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize holdings and interaction state if not explicitly set."""
        if self._holdings is None:
            self._holdings = Bundle(
                self.private_state.endowment.x,
                self.private_state.endowment.y
            )
        if self._interaction_state is None:
            self._interaction_state = AgentInteractionState()

    @property
    def preferences(self) -> CobbDouglas:
        """Convenience accessor for preferences."""
        return self.private_state.preferences

    @property
    def endowment(self) -> Bundle:
        """
        Initial endowment (immutable after construction).

        Defines the disagreement point for Nash bargaining (O&R Ch 2).
        For current holdings, use the `holdings` property.
        """
        return self.private_state.endowment

    @property
    def holdings(self) -> Bundle:
        """
        Current goods owned (mutable).

        Updated by trades. Use this for current state; use `endowment`
        for the disagreement point in bargaining.
        """
        assert self._holdings is not None, "Holdings not initialized"
        return self._holdings

    @holdings.setter
    def holdings(self, value: Bundle) -> None:
        """Update the agent's holdings (e.g., after trade)."""
        self._holdings = value

    @property
    def interaction_state(self) -> AgentInteractionState:
        """
        Current interaction state (ADR-002).

        Tracks the agent's state in the exchange sequence:
        - AVAILABLE: Can take actions
        - PROPOSAL_PENDING: Waiting for response to proposal
        - NEGOTIATING: In active negotiation
        """
        assert self._interaction_state is not None, "Interaction state not initialized"
        return self._interaction_state

    def utility(self) -> float:
        """Compute current utility level from holdings."""
        return self.preferences.utility(self.holdings)

    def utility_of(self, bundle: Bundle) -> float:
        """Compute utility of an arbitrary bundle."""
        return self.private_state.utility_of(bundle)

    def would_gain_from(self, new_bundle: Bundle) -> bool:
        """Check if trading to new_bundle would increase utility over current holdings."""
        return self.utility_of(new_bundle) > self.utility()

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Agent):
            return NotImplemented
        return self.id == other.id

    # =========================================================================
    # Belief System Methods
    # =========================================================================

    @property
    def has_beliefs(self) -> bool:
        """Check if belief system is enabled for this agent."""
        return self.memory is not None

    def enable_beliefs(
        self,
        update_rule: BeliefUpdateRule | None = None,
        memory_depth: int | None = 100,
    ) -> None:
        """
        Enable the belief system for this agent.

        Initializes memory, price belief, and type beliefs.
        If update_rule is not provided, uses BayesianUpdateRule.

        Args:
            update_rule: Rule for updating beliefs (default: BayesianUpdateRule)
            memory_depth: Maximum observations to store (None = unlimited)
        """
        from microecon.beliefs import (
            AgentMemory,
            PriceBelief,
            BayesianUpdateRule,
        )

        self.memory = AgentMemory(max_depth=memory_depth)
        self.price_belief = PriceBelief()
        self.type_beliefs = {}
        self.update_rule = update_rule if update_rule is not None else BayesianUpdateRule()

    def disable_beliefs(self) -> None:
        """Disable the belief system, clearing all memory and beliefs."""
        self.memory = None
        self.price_belief = None
        self.type_beliefs = None
        self.update_rule = None

    def get_believed_alpha(self, partner_id: str) -> float | None:
        """
        Get believed alpha for a partner, or None if no belief exists.

        Args:
            partner_id: ID of the partner agent

        Returns:
            Believed alpha if belief exists, else None
        """
        if self.type_beliefs is None:
            return None
        belief = self.type_beliefs.get(partner_id)
        return belief.believed_alpha if belief is not None else None


def create_agent(
    alpha: float,
    endowment_x: float,
    endowment_y: float,
    perception_radius: float = 3.0,
    discount_factor: float = 0.95,
    bargaining_power: float = 1.0,
    movement_budget: int = 1,
    agent_id: str | None = None,
) -> Agent:
    """
    Factory function to create an agent with Cobb-Douglas preferences.

    Args:
        alpha: Cobb-Douglas preference parameter in (0, 1)
        endowment_x: Initial holdings of good x
        endowment_y: Initial holdings of good y
        perception_radius: How far the agent can observe
        discount_factor: Time preference delta in (0, 1)
        bargaining_power: Intrinsic bargaining power w_i (default 1.0). Used by
            AsymmetricNashBargainingProtocol. Independent of discount_factor.
        movement_budget: Squares per tick
        agent_id: Optional explicit ID (for reproducibility). If None, uses UUID.

    Returns:
        A new Agent instance
    """
    preferences = CobbDouglas(alpha)
    endowment = Bundle(endowment_x, endowment_y)
    private_state = AgentPrivateState(preferences, endowment)

    agent = Agent(
        private_state=private_state,
        perception_radius=perception_radius,
        discount_factor=discount_factor,
        bargaining_power=bargaining_power,
        movement_budget=movement_budget,
    )

    # Override ID if explicit ID provided (for reproducibility)
    if agent_id is not None:
        agent.id = agent_id

    return agent
