"""
Agent belief system: memory, beliefs, and update rules.

This module implements the belief architecture described in ADR-BELIEF-ARCHITECTURE.md.
It provides:
1. Memory structures for storing observations and interaction history
2. Belief representations for prices and partner types
3. Update rule interface with Bayesian and heuristic implementations

Theoretical basis: Kreps I Ch 5-7 (Choice under Uncertainty, Utility for Money, Dynamic Choice)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from microecon.agent import AgentType
    from microecon.bundle import Bundle


# =============================================================================
# Memory Records
# =============================================================================


@dataclass
class TradeMemory:
    """
    Record of a completed trade.

    Stores information about a trade the agent participated in,
    including the partner, bundles before/after, and observed partner type.
    """
    tick: int
    partner_id: str
    my_bundle_before_x: float
    my_bundle_before_y: float
    my_bundle_after_x: float
    my_bundle_after_y: float
    observed_partner_alpha: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "tick": self.tick,
            "partner_id": self.partner_id,
            "bundle_before": [self.my_bundle_before_x, self.my_bundle_before_y],
            "bundle_after": [self.my_bundle_after_x, self.my_bundle_after_y],
            "observed_partner_alpha": self.observed_partner_alpha,
        }


@dataclass
class PriceObservation:
    """
    Observed exchange rate from a trade.

    Records the quantities exchanged, which implies an exchange rate.
    Can be from the agent's own trade or an observed trade between others.
    """
    tick: int
    x_exchanged: float
    y_exchanged: float
    is_own_trade: bool

    @property
    def exchange_rate(self) -> float:
        """Compute exchange rate p = x/y (units of y per unit of x)."""
        if self.y_exchanged == 0:
            return float('inf') if self.x_exchanged > 0 else 1.0
        return abs(self.x_exchanged / self.y_exchanged)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "tick": self.tick,
            "x_exchanged": self.x_exchanged,
            "y_exchanged": self.y_exchanged,
            "is_own_trade": self.is_own_trade,
            "exchange_rate": self.exchange_rate,
        }


@dataclass
class InteractionRecord:
    """
    Record of interacting with a specific partner.

    Flexible record type for various interaction contexts.
    """
    tick: int
    interaction_type: str  # 'trade', 'encounter', 'observed'
    observed_alpha: float
    outcome: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "tick": self.tick,
            "interaction_type": self.interaction_type,
            "observed_alpha": self.observed_alpha,
            "outcome": self.outcome,
        }


# =============================================================================
# Memory Container
# =============================================================================


@dataclass
class AgentMemory:
    """
    Agent's observation and interaction history.

    Stores:
    - Trade history: completed exchanges
    - Price observations: exchange ratios from trades
    - Partner history: per-agent interaction records

    Memory depth is configurable; if max_depth is set, oldest records
    are evicted when limit is exceeded.
    """
    max_depth: int | None = 100

    # Internal storage
    _trade_history: list[TradeMemory] = field(default_factory=list)
    _price_observations: list[PriceObservation] = field(default_factory=list)
    _partner_history: dict[str, list[InteractionRecord]] = field(default_factory=dict)

    @property
    def trade_history(self) -> list[TradeMemory]:
        """Get trade history (read-only view)."""
        return list(self._trade_history)

    @property
    def price_observations(self) -> list[PriceObservation]:
        """Get price observations (read-only view)."""
        return list(self._price_observations)

    @property
    def partner_history(self) -> dict[str, list[InteractionRecord]]:
        """Get partner history (read-only view)."""
        return {k: list(v) for k, v in self._partner_history.items()}

    def add_trade(self, trade: TradeMemory) -> None:
        """Add a trade record, evicting oldest if at capacity."""
        self._trade_history.append(trade)
        if self.max_depth is not None and len(self._trade_history) > self.max_depth:
            self._trade_history.pop(0)

    def add_price_observation(self, obs: PriceObservation) -> None:
        """Add a price observation, evicting oldest if at capacity."""
        self._price_observations.append(obs)
        if self.max_depth is not None and len(self._price_observations) > self.max_depth:
            self._price_observations.pop(0)

    def add_interaction(self, partner_id: str, record: InteractionRecord) -> None:
        """Add an interaction record for a specific partner."""
        if partner_id not in self._partner_history:
            self._partner_history[partner_id] = []
        self._partner_history[partner_id].append(record)
        if self.max_depth is not None and len(self._partner_history[partner_id]) > self.max_depth:
            self._partner_history[partner_id].pop(0)

    def get_partner_interactions(self, partner_id: str) -> list[InteractionRecord]:
        """Get all interaction records for a specific partner."""
        return list(self._partner_history.get(partner_id, []))

    def n_trades(self) -> int:
        """Count of trades in memory."""
        return len(self._trade_history)

    def n_price_observations(self) -> int:
        """Count of price observations in memory."""
        return len(self._price_observations)

    def n_partners_known(self) -> int:
        """Count of distinct partners interacted with."""
        return len(self._partner_history)

    def clear(self) -> None:
        """Clear all memory."""
        self._trade_history.clear()
        self._price_observations.clear()
        self._partner_history.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "max_depth": self.max_depth,
            "n_trades": self.n_trades(),
            "n_price_observations": self.n_price_observations(),
            "n_partners_known": self.n_partners_known(),
            "trades": [t.to_dict() for t in self._trade_history],
            "price_observations": [p.to_dict() for p in self._price_observations],
            "partner_history": {
                pid: [r.to_dict() for r in records]
                for pid, records in self._partner_history.items()
            },
        }


# =============================================================================
# Belief Representations
# =============================================================================


@dataclass
class PriceBelief:
    """
    Belief about exchange rate p = x/y (units of y per unit of x).

    Uses mean-variance representation suitable for Gaussian-family beliefs.
    """
    mean: float = 1.0        # Expected price
    variance: float = 1.0    # Uncertainty about price
    n_observations: int = 0  # Number of observations incorporated

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "mean": self.mean,
            "variance": self.variance,
            "n_observations": self.n_observations,
        }


@dataclass
class TypeBelief:
    """
    Belief about another agent's true preference parameter.

    Tracks posterior mean of alpha and confidence level.
    """
    agent_id: str
    believed_alpha: float  # Posterior mean of alpha
    confidence: float = 0.0  # In [0, 1], higher = more certain
    n_interactions: int = 0  # Number of observations

    def __post_init__(self):
        # Ensure alpha is in valid range
        self.believed_alpha = max(0.01, min(0.99, self.believed_alpha))
        self.confidence = max(0.0, min(1.0, self.confidence))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "agent_id": self.agent_id,
            "believed_alpha": self.believed_alpha,
            "confidence": self.confidence,
            "n_interactions": self.n_interactions,
        }


# =============================================================================
# Update Rule Interface
# =============================================================================


class BeliefUpdateRule(ABC):
    """
    Abstract interface for belief update strategies.

    Defines how beliefs are updated given new observations.
    Concrete implementations include Bayesian (optimal) and
    heuristic (bounded rationality) approaches.
    """

    @abstractmethod
    def update_price_belief(
        self,
        prior: PriceBelief,
        observation: PriceObservation
    ) -> PriceBelief:
        """
        Update price belief given new observation.

        Args:
            prior: Current price belief
            observation: New price observation

        Returns:
            Updated price belief
        """
        pass

    @abstractmethod
    def update_type_belief(
        self,
        prior: TypeBelief | None,
        agent_id: str,
        observed_alpha: float,
        context: dict[str, Any] | None = None
    ) -> TypeBelief:
        """
        Update belief about partner type.

        Args:
            prior: Current belief about this agent (None if first interaction)
            agent_id: ID of the agent this belief is about
            observed_alpha: Observed preference parameter
            context: Additional context (e.g., trade outcome)

        Returns:
            Updated type belief
        """
        pass


# =============================================================================
# Bayesian Update Rule
# =============================================================================


class BayesianUpdateRule(BeliefUpdateRule):
    """
    Bayesian belief updating with conjugate priors.

    Price beliefs use Gaussian-Gaussian updates.
    Type beliefs use precision-weighted averaging.
    """

    def __init__(self, observation_noise_variance: float = 0.01):
        """
        Initialize with observation noise parameter.

        Args:
            observation_noise_variance: Assumed variance of observation noise
        """
        if observation_noise_variance <= 0:
            raise ValueError("observation_noise_variance must be positive")
        self.obs_var = observation_noise_variance

    def update_price_belief(
        self,
        prior: PriceBelief,
        observation: PriceObservation
    ) -> PriceBelief:
        """
        Update price belief using Gaussian-Gaussian conjugate update.

        Posterior mean is precision-weighted average of prior and observation.
        Posterior variance decreases with each observation.
        """
        p_obs = observation.exchange_rate

        # Handle infinite or invalid observations
        if not (0 < p_obs < float('inf')):
            return PriceBelief(
                mean=prior.mean,
                variance=prior.variance,
                n_observations=prior.n_observations
            )

        # Precision-weighted average (Bayesian update for Gaussian)
        prior_precision = 1.0 / prior.variance if prior.variance > 0 else 0.0
        obs_precision = 1.0 / self.obs_var

        new_precision = prior_precision + obs_precision
        new_mean = (prior_precision * prior.mean + obs_precision * p_obs) / new_precision
        new_variance = 1.0 / new_precision

        return PriceBelief(
            mean=new_mean,
            variance=new_variance,
            n_observations=prior.n_observations + 1
        )

    def update_type_belief(
        self,
        prior: TypeBelief | None,
        agent_id: str,
        observed_alpha: float,
        context: dict[str, Any] | None = None
    ) -> TypeBelief:
        """
        Update type belief using precision-weighted averaging.

        For first observation, initializes belief at observed value with low confidence.
        Subsequent observations increase confidence as variance decreases.
        """
        observed_alpha = max(0.01, min(0.99, observed_alpha))

        if prior is None:
            # First observation: initialize at observed value
            return TypeBelief(
                agent_id=agent_id,
                believed_alpha=observed_alpha,
                confidence=self.obs_var / (self.obs_var + 1.0),  # Low initial confidence
                n_interactions=1
            )

        # Precision-weighted update
        # Prior precision grows with n_interactions
        prior_precision = prior.n_interactions / self.obs_var
        obs_precision = 1.0 / self.obs_var

        new_precision = prior_precision + obs_precision
        new_alpha = (prior_precision * prior.believed_alpha + obs_precision * observed_alpha) / new_precision

        # Confidence increases as we have more observations
        new_confidence = min(0.99, 1.0 - (1.0 / (prior.n_interactions + 2)))

        return TypeBelief(
            agent_id=agent_id,
            believed_alpha=new_alpha,
            confidence=new_confidence,
            n_interactions=prior.n_interactions + 1
        )


# =============================================================================
# Heuristic Update Rule (EMA)
# =============================================================================


# =============================================================================
# Exchange Integration Functions
# =============================================================================


def record_trade_observation(
    agent: "Agent",
    partner: "Agent",
    bundle_before: "Bundle",
    bundle_after: "Bundle",
    observed_partner_alpha: float,
    tick: int,
) -> None:
    """
    Record a trade observation in agent's memory and update beliefs.

    This function should be called after a trade is executed to:
    1. Add the trade to memory
    2. Record the price observation
    3. Update beliefs about the partner's type

    Args:
        agent: The agent whose memory/beliefs to update
        partner: The trading partner
        bundle_before: Agent's bundle before trade
        bundle_after: Agent's bundle after trade
        observed_partner_alpha: The alpha observed for the partner
        tick: Current simulation tick
    """
    if not agent.has_beliefs:
        return

    # Record trade in memory
    trade_record = TradeMemory(
        tick=tick,
        partner_id=partner.id,
        my_bundle_before_x=bundle_before.x,
        my_bundle_before_y=bundle_before.y,
        my_bundle_after_x=bundle_after.x,
        my_bundle_after_y=bundle_after.y,
        observed_partner_alpha=observed_partner_alpha,
    )
    agent.memory.add_trade(trade_record)

    # Compute exchange amounts
    x_exchanged = bundle_after.x - bundle_before.x
    y_exchanged = bundle_after.y - bundle_before.y

    # Record price observation
    if abs(y_exchanged) > 1e-9:  # Only if meaningful trade occurred
        price_obs = PriceObservation(
            tick=tick,
            x_exchanged=abs(x_exchanged),
            y_exchanged=abs(y_exchanged),
            is_own_trade=True,
        )
        agent.memory.add_price_observation(price_obs)

        # Update price belief
        if agent.update_rule is not None:
            agent.price_belief = agent.update_rule.update_price_belief(
                agent.price_belief, price_obs
            )

    # Record interaction and update type belief
    interaction = InteractionRecord(
        tick=tick,
        interaction_type="trade",
        observed_alpha=observed_partner_alpha,
        outcome={"x_exchanged": x_exchanged, "y_exchanged": y_exchanged},
    )
    agent.memory.add_interaction(partner.id, interaction)

    # Update type belief
    if agent.update_rule is not None:
        prior_belief = agent.type_beliefs.get(partner.id)
        new_belief = agent.update_rule.update_type_belief(
            prior_belief, partner.id, observed_partner_alpha
        )
        agent.type_beliefs[partner.id] = new_belief


def record_encounter(
    agent: "Agent",
    partner: "Agent",
    observed_partner_alpha: float,
    tick: int,
) -> None:
    """
    Record an encounter (non-trade interaction) and update beliefs.

    Called when agents meet but don't trade, or when observing others.

    Args:
        agent: The agent whose memory/beliefs to update
        partner: The encountered partner
        observed_partner_alpha: The alpha observed for the partner
        tick: Current simulation tick
    """
    if not agent.has_beliefs:
        return

    # Record interaction
    interaction = InteractionRecord(
        tick=tick,
        interaction_type="encounter",
        observed_alpha=observed_partner_alpha,
    )
    agent.memory.add_interaction(partner.id, interaction)

    # Update type belief
    if agent.update_rule is not None:
        prior_belief = agent.type_beliefs.get(partner.id)
        new_belief = agent.update_rule.update_type_belief(
            prior_belief, partner.id, observed_partner_alpha
        )
        agent.type_beliefs[partner.id] = new_belief


def record_observed_trade(
    agent: "Agent",
    trader1_id: str,
    trader2_id: str,
    x_exchanged: float,
    y_exchanged: float,
    tick: int,
) -> None:
    """
    Record observation of a trade between other agents.

    Allows agents to learn from observing others trade (price discovery).

    Args:
        agent: The observing agent
        trader1_id: ID of first trader
        trader2_id: ID of second trader
        x_exchanged: Amount of x exchanged
        y_exchanged: Amount of y exchanged
        tick: Current simulation tick
    """
    if not agent.has_beliefs:
        return

    if abs(y_exchanged) < 1e-9:
        return  # No meaningful price information

    # Record price observation
    price_obs = PriceObservation(
        tick=tick,
        x_exchanged=abs(x_exchanged),
        y_exchanged=abs(y_exchanged),
        is_own_trade=False,
    )
    agent.memory.add_price_observation(price_obs)

    # Update price belief
    if agent.update_rule is not None:
        agent.price_belief = agent.update_rule.update_price_belief(
            agent.price_belief, price_obs
        )


class HeuristicUpdateRule(BeliefUpdateRule):
    """
    Exponential moving average belief updates.

    Simple heuristic that weights recent observations more heavily.
    Models bounded rationality and recency bias.
    """

    def __init__(self, learning_rate: float = 0.1):
        """
        Initialize with learning rate.

        Args:
            learning_rate: Weight on new observations (higher = more responsive)
        """
        if not 0 < learning_rate <= 1:
            raise ValueError("learning_rate must be in (0, 1]")
        self.alpha = learning_rate

    def update_price_belief(
        self,
        prior: PriceBelief,
        observation: PriceObservation
    ) -> PriceBelief:
        """
        Update price belief using exponential moving average.

        new_mean = (1 - alpha) * prior_mean + alpha * observation
        """
        p_obs = observation.exchange_rate

        # Handle infinite or invalid observations
        if not (0 < p_obs < float('inf')):
            return PriceBelief(
                mean=prior.mean,
                variance=prior.variance,
                n_observations=prior.n_observations
            )

        new_mean = (1 - self.alpha) * prior.mean + self.alpha * p_obs

        # EMA variance update (tracks recent squared deviations)
        deviation_sq = (p_obs - prior.mean) ** 2
        new_variance = (1 - self.alpha) * prior.variance + self.alpha * deviation_sq

        return PriceBelief(
            mean=new_mean,
            variance=new_variance,
            n_observations=prior.n_observations + 1
        )

    def update_type_belief(
        self,
        prior: TypeBelief | None,
        agent_id: str,
        observed_alpha: float,
        context: dict[str, Any] | None = None
    ) -> TypeBelief:
        """
        Update type belief using exponential moving average.

        Simple EMA on the observed alpha values.
        """
        observed_alpha = max(0.01, min(0.99, observed_alpha))

        if prior is None:
            # First observation: initialize at observed value
            return TypeBelief(
                agent_id=agent_id,
                believed_alpha=observed_alpha,
                confidence=self.alpha,  # Initial confidence = learning rate
                n_interactions=1
            )

        new_alpha = (1 - self.alpha) * prior.believed_alpha + self.alpha * observed_alpha

        # Confidence increases with interactions (saturating)
        new_confidence = min(0.99, prior.confidence + self.alpha * (1 - prior.confidence))

        return TypeBelief(
            agent_id=agent_id,
            believed_alpha=new_alpha,
            confidence=new_confidence,
            n_interactions=prior.n_interactions + 1
        )
