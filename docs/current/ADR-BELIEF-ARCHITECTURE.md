# ADR: Agent Belief Architecture

**Status:** Proposed
**Created:** 2026-01-07
**Theoretical Basis:** Kreps I Ch 5-7 (Choice under Uncertainty, Utility for Money, Dynamic Choice)

---

## Context

The current agent model has private state (true preferences, endowments) separate from observable type (what others perceive). Under `FullInformation`, agents observe true types; under `NoisyAlphaInformation`, observations are noisy. However, agents currently have no memory or learning capability—each decision is based only on current observations.

To study market emergence and learning dynamics, agents need:
1. **Memory** of past interactions and observations
2. **Beliefs** about uncertain quantities (partner types, prices)
3. **Update rules** that revise beliefs based on new evidence

This ADR defines the architecture for these capabilities.

---

## Decision

### 1. Belief Representation

#### 1.1 Price Beliefs

Agents form beliefs about the "fair" exchange rate between goods. Following Kreps I Ch 6 (Utility for Money), we represent price beliefs as a probability distribution over exchange ratios.

**Design:**
```python
@dataclass
class PriceBelief:
    """Belief about exchange rate p = x/y (units of y per unit of x)."""
    mean: float           # Expected price
    variance: float       # Uncertainty about price
    n_observations: int   # Number of price observations incorporated
```

**Rationale:**
- Mean-variance sufficient for Gaussian-family beliefs
- `n_observations` tracks confidence (Bayesian precision)
- Exchange ratio interpretation natural for bilateral trade

#### 1.2 Partner Type Beliefs

Agents form beliefs about other agents' true preference parameters. Under noisy observation, the observed alpha differs from the true alpha.

**Design:**
```python
@dataclass
class TypeBelief:
    """Belief about another agent's true preference parameter."""
    agent_id: str         # Agent this belief is about
    believed_alpha: float # Posterior mean of alpha
    confidence: float     # In [0, 1], higher = more certain
    n_interactions: int   # Number of observations of this agent
```

**Rationale:**
- Per-agent beliefs enable learning from repeated interaction (Kreps I Ch 7)
- Confidence separates from `n_interactions` to support different update rules
- Alpha in (0, 1) is the key heterogeneity parameter for Cobb-Douglas

### 2. Memory Structure

Following Kreps I Ch 7 (Dynamic Choice), agents maintain history to condition future decisions.

**Design:**
```python
@dataclass
class AgentMemory:
    """Agent's observation and interaction history."""

    # Trade history: records of completed exchanges
    trade_history: list[TradeMemory]

    # Price observations: exchange ratios observed in own trades or visible trades
    price_observations: list[PriceObservation]

    # Partner interactions: per-agent records of interactions
    partner_history: dict[str, list[InteractionRecord]]

    # Configuration
    max_depth: int | None  # None = unlimited, else keeps last N

    def add_trade(self, trade: TradeMemory) -> None: ...
    def add_price_observation(self, obs: PriceObservation) -> None: ...
    def add_interaction(self, partner_id: str, record: InteractionRecord) -> None: ...
```

**Memory Records:**
```python
@dataclass
class TradeMemory:
    """Record of a completed trade."""
    tick: int
    partner_id: str
    my_bundle_before: Bundle
    my_bundle_after: Bundle
    observed_partner_type: AgentType  # What I observed at trade time

@dataclass
class PriceObservation:
    """Observed exchange rate from a trade."""
    tick: int
    x_exchanged: float
    y_exchanged: float
    is_own_trade: bool  # vs. observed another pair trading

@dataclass
class InteractionRecord:
    """Record of interacting with a specific partner."""
    tick: int
    interaction_type: str  # 'trade', 'encounter', 'observed'
    observed_type: AgentType
    outcome: dict  # Flexible for different interaction types
```

**Eviction Policy:**
- If `max_depth` is set, drop oldest records when limit exceeded
- Drop per-list (trade_history, price_observations) independently
- Partner history evicts per-partner (keeps last N interactions with each partner)

**Serialization:**
- All memory dataclasses implement `to_dict()` for JSON logging
- Memory state captured at each tick for replay analysis

### 3. Update Rule Interface

Per Kreps I Ch 5 (Choice under Uncertainty), beliefs should be updated consistently with probability theory. However, bounded rationality research (cited in VISION.md) requires comparing optimal vs. heuristic learning.

**Interface:**
```python
from abc import ABC, abstractmethod

class BeliefUpdateRule(ABC):
    """Abstract interface for belief update strategies."""

    @abstractmethod
    def update_price_belief(
        self,
        prior: PriceBelief,
        observation: PriceObservation
    ) -> PriceBelief:
        """Update price belief given new observation."""
        pass

    @abstractmethod
    def update_type_belief(
        self,
        prior: TypeBelief | None,
        observation: AgentType,
        context: dict  # Additional context (e.g., trade outcome)
    ) -> TypeBelief:
        """Update belief about partner type."""
        pass
```

### 4. Concrete Implementations

#### 4.1 Bayesian Update Rule

Optimal updating per probability theory. Uses conjugate priors where tractable.

**Price Belief (Gaussian-Gaussian):**
- Prior: p ~ N(μ₀, σ₀²)
- Observation: p_obs with noise variance σ_n²
- Posterior: p ~ N(μ₁, σ₁²) where:
  - μ₁ = (μ₀/σ₀² + p_obs/σ_n²) / (1/σ₀² + 1/σ_n²)
  - σ₁² = 1 / (1/σ₀² + 1/σ_n²)

**Type Belief (Beta-Binomial approx):**
- For alpha ∈ (0, 1), use Beta distribution as prior
- Update based on observed alpha with noise model
- Simplified: track sufficient statistics (sum, count) for mean update

**Implementation:**
```python
class BayesianUpdateRule(BeliefUpdateRule):
    """Bayesian belief updating with conjugate priors."""

    def __init__(self, observation_noise_variance: float = 0.01):
        self.obs_var = observation_noise_variance

    def update_price_belief(self, prior: PriceBelief, obs: PriceObservation) -> PriceBelief:
        p_obs = obs.x_exchanged / obs.y_exchanged if obs.y_exchanged > 0 else prior.mean

        # Precision-weighted average
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
```

#### 4.2 Heuristic Update Rule (EMA)

Exponential moving average—simple, bounded rationality model.

**Design:**
```python
class HeuristicUpdateRule(BeliefUpdateRule):
    """Exponential moving average belief updates."""

    def __init__(self, learning_rate: float = 0.1):
        self.alpha = learning_rate  # Higher = weight recent observations more

    def update_price_belief(self, prior: PriceBelief, obs: PriceObservation) -> PriceBelief:
        p_obs = obs.x_exchanged / obs.y_exchanged if obs.y_exchanged > 0 else prior.mean

        new_mean = (1 - self.alpha) * prior.mean + self.alpha * p_obs
        # Variance also updated via EMA of squared deviations
        deviation_sq = (p_obs - prior.mean) ** 2
        new_variance = (1 - self.alpha) * prior.variance + self.alpha * deviation_sq

        return PriceBelief(
            mean=new_mean,
            variance=new_variance,
            n_observations=prior.n_observations + 1
        )
```

**Comparison Rationale:**
- Bayesian optimal for Gaussian noise; computationally tractable
- EMA simpler, models recency bias, robust to non-stationarity
- Comparison reveals value of optimal learning vs. bounded rationality

### 5. Agent Integration

**Extended Agent Class:**
```python
@dataclass
class Agent:
    # ... existing fields ...

    # New belief-related fields
    memory: AgentMemory = field(default_factory=lambda: AgentMemory(max_depth=100))
    price_belief: PriceBelief = field(default_factory=lambda: PriceBelief(1.0, 1.0, 0))
    type_beliefs: dict[str, TypeBelief] = field(default_factory=dict)
    update_rule: BeliefUpdateRule = field(default_factory=BayesianUpdateRule)
```

**Belief-Enabled Behavior:**
1. **Search:** Use believed types (not raw observations) for surplus calculation
2. **Exchange:** Use believed types for bargaining strategy
3. **Post-Trade:** Update beliefs based on trade outcome and revealed information

### 6. Search Integration

**Modified Target Evaluation:**
```python
def evaluate_target(
    self,
    agent: Agent,
    target: Agent,
    observed_type: AgentType,
    use_beliefs: bool = True
) -> float:
    """Compute expected surplus from trading with target."""
    if use_beliefs and target.id in agent.type_beliefs:
        # Use believed type instead of noisy observation
        belief = agent.type_beliefs[target.id]
        believed_type = AgentType(
            preferences=CobbDouglas(belief.believed_alpha),
            endowment=observed_type.endowment  # Endowments still observed
        )
        return self._compute_surplus(agent, believed_type)
    else:
        return self._compute_surplus(agent, observed_type)
```

### 7. Exchange Integration

**Belief-Aware Bargaining:**
- Protocols accept optional `believed_types` parameter
- If provided, bargaining uses believed types for strategy computation
- True types still determine actual payoffs (private state unchanged)

**Post-Trade Updates:**
- After trade, both agents update beliefs about partner's type
- Trade outcome (bundle received) reveals information about partner preferences
- Price observation added to memory

---

## Theoretical Grounding

### Kreps I Ch 5: Choice under Uncertainty

- **Expected utility:** Beliefs combined with utility via expectation
- **Subjective probability:** Agents form probability distributions over uncertain states
- **Consistency axioms:** Updates should satisfy probability laws (Bayesian is unique consistent update)

### Kreps I Ch 6: Utility for Money

- **Price as random variable:** Exchange rate uncertain before trade
- **Risk attitudes:** Variance of price belief affects willingness to trade
- **Information value:** Beliefs improve with observation, reducing uncertainty

### Kreps I Ch 7: Dynamic Choice

- **Conditioning on history:** Optimal strategies depend on past observations
- **Sequential rationality:** Each decision optimal given beliefs and continuation value
- **Learning:** Beliefs converge to truth with sufficient observations (law of large numbers)

---

## Alternatives Considered

### 1. Full Distribution Storage

Store complete probability distributions (e.g., histograms, kernel density estimates) instead of mean-variance summaries.

**Rejected:**
- Much higher memory/computation cost
- Mean-variance sufficient for Gaussian families
- Summaries adequate for initial research questions

### 2. Global Price Belief Only

Single market-wide price belief rather than per-agent type beliefs.

**Rejected:**
- Per-agent beliefs critical for studying reputation and relationship effects
- Market price belief can be derived from aggregating type beliefs
- Per-agent structure more flexible

### 3. No Memory (Beliefs Only)

Store only current beliefs, not raw observation history.

**Rejected:**
- Loses ability to replay with different update rules
- Loses ability to analyze what agents observed vs. believed
- Memory overhead acceptable for research platform

---

## Implementation Plan

| Feature | Files | Depends On |
|---------|-------|------------|
| BELIEF-002: Agent Memory | agent.py, test_beliefs.py | This ADR |
| BELIEF-003: Update Rules | beliefs.py, test_beliefs.py | BELIEF-002 |
| BELIEF-004: Search Integration | search.py, test_search.py | BELIEF-003 |
| BELIEF-005: Exchange Integration | bargaining.py, test_bargaining.py | BELIEF-003 |
| BELIEF-006: Integration Tests | test_integration.py | BELIEF-004, BELIEF-005 |

---

## Success Criteria

1. **Correctness:** Bayesian updates match analytical posterior formulas
2. **Convergence:** With consistent observations, beliefs converge to true values
3. **Comparability:** Can run same scenario with different update rules
4. **Non-regression:** All 580+ existing tests still pass
5. **Logging:** Belief state captured in simulation logs
6. **Performance:** <10% overhead vs. belief-free simulation

---

## Open Questions for Discussion

1. **Initial beliefs:** What should uninformative priors be? (Currently: mean=1.0, var=1.0 for prices)
2. **Information revelation:** How much does a trade reveal about partner type?
3. **Forgetting:** Should old observations be down-weighted even without eviction?
