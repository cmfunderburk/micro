# Comprehensive Planning Proposal: Open Questions Resolution

**Author:** Claude Opus 4.5 Review
**Date:** 2026-01-05
**Purpose:** Provide detailed, justified recommendations for each open question in the planning documents
**Status:** Proposal for review and iteration

---

## Executive Summary

This document addresses the ten major open questions identified in `PLANNING-REVIEW.md`, plus several implicit gaps, with concrete recommendations and rigorous justifications grounded in the project's theoretical foundations and vision. The guiding principle is **minimum viable formalism**: choose the simplest theoretical apparatus that preserves the platform's methodological commitments while enabling the first research program (market emergence).

**Key Recommendations Summary:**

| Question | Recommendation |
|----------|----------------|
| ARCH-001 | Mechanism abstraction layer with participation phases |
| Production | Defer; ensure architecture accommodates future addition |
| Roles | Endowment-derived roles with explicit role interface |
| Beliefs | Sufficient-statistics model with Bayesian option |
| Price definition | Exchange rate (Δy/Δx) as primary, MRS convergence as secondary |
| Information taxonomy | Private values first, signaling second |
| Benchmarks | Walrasian only for Phase 3; core as optional extension |
| Market emergence | Composite index with three pillars |
| Experimental design | Config-as-source-of-truth with YAML specification |
| Performance | Accept O(n²) with documented bounds and spatial indexing option |

---

## Part I: Critical Architectural Decisions

### 1. ARCH-001: Multi-Agent Mechanism Architecture

**The Question:** How should multi-agent mechanisms (double auctions, centralized markets) integrate with the existing four-phase tick loop?

**Context:** The current architecture assumes bilateral exchange with phases: evaluate → decide → move → exchange. Multi-agent mechanisms require different coordination: simultaneous order submission, market clearing, settlement. The decision here shapes all future extensibility.

#### Analysis of Options

**Option A: Extend the Tick Loop**

Add phases to the existing loop (e.g., "submit_orders", "clear_market", "settle").

*Pros:*
- Minimal conceptual overhead
- Preserves the familiar tick abstraction
- All logic remains in one temporal frame

*Cons:*
- The loop becomes a growing switchboard
- Different mechanisms have different timing semantics (call markets clear once; continuous auctions clear repeatedly)
- Phases become mechanism-specific, defeating the purpose of a generic loop

**Option B: Mechanism Abstraction Layer**

Introduce a `Mechanism` interface that owns internal steps but exposes standard methods to the simulation.

*Pros:*
- Clean separation of concerns
- Each mechanism encapsulates its own logic (order types, clearing rules, settlement)
- Multiple mechanisms can coexist (different "venues")
- Matches economic intuition: markets are institutions with their own rules

*Cons:*
- More complex architecture
- Requires careful design of what agents observe and when
- Mechanisms must coordinate with spatial movement

**Option C: Event-Driven Simulation**

Replace the tick loop with a scheduler/agenda where mechanisms post events and agents respond.

*Pros:*
- Natural for asynchronous interactions (continuous auctions, signaling games)
- Handles heterogeneous timing naturally
- More realistic for some market microstructure

*Cons:*
- Highest architectural complexity
- Harder to maintain visual intuition (ticks are pedagogically valuable)
- Potentially slower (event queue overhead)
- Major rewrite of existing code

#### Recommendation: Option B (Mechanism Abstraction Layer)

**Justification:**

1. **Theoretical alignment**: Economic theory treats markets/mechanisms as institutions with well-defined rules (O&R-B Ch 9-10 on trading procedures). A `Mechanism` abstraction makes this explicit.

2. **Preserves spatial grounding**: The grid remains primary for search/movement. Mechanisms operate at "locations" (conceptual or spatial). Agents must reach a mechanism to participate.

3. **Enables comparison**: The core research question is "what difference does the institution make?" Having mechanisms as swappable objects directly supports this.

4. **Accommodates bilateral and multilateral**: Bilateral bargaining becomes a mechanism with two participants. Auctions become mechanisms with many. The interface unifies both.

#### Proposed Interface

```python
class Mechanism(ABC):
    """Abstract base for exchange mechanisms."""

    @abstractmethod
    def can_participate(self, agent: Agent) -> bool:
        """Check if agent can join this mechanism instance."""
        pass

    @abstractmethod
    def submit_action(self, agent: Agent, action: MechanismAction) -> None:
        """Agent submits an action (bid, ask, offer, acceptance)."""
        pass

    @abstractmethod
    def ready_to_clear(self) -> bool:
        """Check if mechanism has enough participants/actions to clear."""
        pass

    @abstractmethod
    def clear(self) -> list[Transfer]:
        """Execute the mechanism and return resulting transfers."""
        pass

    @abstractmethod
    def get_observable_state(self, agent: Agent) -> MechanismObservation:
        """Return what agent can observe about this mechanism."""
        pass
```

#### Modified Tick Loop

```
Pre-tick: Commitment/mechanism membership maintenance
Phase 1: Evaluate (including mechanism opportunities)
Phase 2: Decide (movement target OR mechanism participation)
Phase 3: Move
Phase 4: Mechanism execution (for each active mechanism: collect actions, clear)
Post-tick: Logging, belief updates
```

The key insight is that Phase 4 becomes "execute all active mechanisms" rather than "execute bilateral bargaining." This accommodates:
- Bilateral bargaining (mechanism with 2 participants, clears when both present)
- Double auction (mechanism with N participants, clears on schedule or continuous)
- Posted prices (mechanism with 1 seller, clears when buyer accepts)

#### Implementation Path

1. **Refactor existing protocols**: Wrap `NashBargainingProtocol` and `RubinsteinBargainingProtocol` in `BilateralMechanism` adapter
2. **Add mechanism phase**: Modify simulation loop to iterate over active mechanisms
3. **Implement double auction**: First multi-agent mechanism as proof-of-concept
4. **Add mechanism participation to search**: Agents evaluate mechanism opportunities alongside bilateral surplus

**Blocking:** Nothing currently. This work can proceed immediately.

---

### 2. Production: Minimal Model for the Vision

**The Question:** What is the minimal production model consistent with VISION.md?

**Context:** VISION.md mentions production is in scope ("anything that can be modeled in the microeconomic tradition"). The planning documents correctly identify that production interacts with mechanism participation (agents choosing to produce vs. trade).

#### Analysis

Production fundamentally changes the nature of the simulation:
- Without production: fixed total endowments, pure exchange economy
- With production: agents can transform goods, endogenous supply

The complication is that production decisions interact with everything:
- Timing: produce before trading? After? Simultaneously?
- Technology: fixed, chosen, learned?
- Factor markets: if production uses labor/capital, where do those come from?

#### Recommendation: Defer Production; Ensure Architecture Accommodates

**Justification:**

1. **Market emergence can be studied without production**: The first research program asks "when do markets emerge from bilateral exchange?" This is a pure exchange question. Adding production multiplies complexity without adding to the core institutional comparison.

2. **Production is a research program, not a primitive**: Production deserves its own focused development phase with careful theoretical grounding (Kreps I Ch 9, production-possibility sets).

3. **Architecture should not preclude production**: The mechanism abstraction (ARCH-001) naturally accommodates production as follows:
   - Production is a "mechanism" where the agent is both buyer and seller (self-trade)
   - Agent action in Phase 2 can be "participate in production mechanism"
   - Technology is a parameter of the production mechanism

#### Ensuring Future Compatibility

Add to the `Agent` interface:

```python
class Agent:
    # ... existing fields ...

    def can_produce(self) -> bool:
        """Whether agent has production capability."""
        return False  # Default: pure exchange economy

    def production_technology(self) -> ProductionTechnology | None:
        """Agent's technology if any."""
        return None
```

This costs nothing now and enables production later without retrofitting.

**Work Item:** Add a backlog item "PROD-001: Production Architecture" with status "deferred" and dependency on ARCH-001.

---

### 3. Roles and Asymmetry: Buyer/Seller, Proposer/Responder

**The Question:** How should "buyer/seller" and "proposer/responder" roles be modeled?

**Context:** Many protocols require role asymmetry:
- TIOLI: proposer vs. responder
- Posted prices: seller posts, buyer accepts
- Gale-Shapley: proposing vs. receiving side
- Auctions: bidders vs. auctioneer

The current model is symmetric bilateral trade between agents with endowments.

#### Analysis of Options

**Option A: Derive Roles from Endowments**

Agents with x > y are "x-sellers" (want to sell x for y). Role emerges from economic position.

*Pros:*
- No explicit role modeling needed
- Matches economic intuition (comparative advantage)
- Endogenous role assignment

*Cons:*
- Doesn't handle proposer/responder (orthogonal to goods endowment)
- Some mechanisms require exogenous role assignment
- Ambiguous when endowments are balanced

**Option B: Explicit Role Fields**

Add role/type fields to agent observable type and scenario configs.

```python
@dataclass
class AgentType:
    preferences: CobbDouglas
    endowment: Bundle
    role: MarketRole  # NEW: BUYER, SELLER, NEUTRAL
    bargaining_position: BargainingRole  # NEW: PROPOSER, RESPONDER, ALTERNATING
```

*Pros:*
- Explicit, clear
- Supports arbitrary role assignments
- Easy to configure in scenarios

*Cons:*
- More configuration burden
- May not match emergent behavior
- Artificial if roles are economically determined

**Option C: Make Role Assignment an Institution**

Role is determined by the mechanism/institution, not the agent.

*Pros:*
- Matches reality (auction rules determine who bids, who sells)
- Role is context-dependent (same agent can be buyer in one market, seller in another)
- Fits the "institutional visibility" framing

*Cons:*
- More complex
- Requires thinking through each mechanism's role semantics

#### Recommendation: Hybrid Approach (A + C)

**Primary:** Derive market-side roles (buyer/seller) from endowments, but allow mechanism override.

**Secondary:** Bargaining roles (proposer/responder) are mechanism-assigned.

**Justification:**

1. **Economic grounding**: In a 2-good exchange economy, buyer/seller is determined by who has what and who wants what. An agent with α > 0.5 and endowment (10, 0) is a "seller of x" because they have x and want y.

2. **Mechanism determines procedural roles**: Who proposes first is a rule of the bargaining game, not an agent characteristic. The Rubinstein model alternates; TIOLI has a fixed proposer. This is mechanism design, not agent typing.

3. **Flexibility**: Mechanisms can override endowment-derived roles if needed (e.g., forced buyer/seller assignment in experiments).

#### Proposed Implementation

```python
class MarketSide(Enum):
    """Economic role derived from endowments and preferences."""
    X_SELLER = "x_seller"  # Has x, wants y
    Y_SELLER = "y_seller"  # Has y, wants x
    BALANCED = "balanced"  # No clear side

def derive_market_side(agent: Agent) -> MarketSide:
    """Compute market side from preferences and endowments."""
    mrs = agent.preferences.mrs(agent.endowment)
    # If MRS > 1, agent values y more than market would (x-seller)
    # If MRS < 1, agent values x more than market would (y-seller)
    if mrs > 1 + EPSILON:
        return MarketSide.X_SELLER
    elif mrs < 1 - EPSILON:
        return MarketSide.Y_SELLER
    return MarketSide.BALANCED

class Mechanism(ABC):
    def assign_roles(self, participants: list[Agent]) -> dict[Agent, MechanismRole]:
        """Mechanism assigns procedural roles (e.g., proposer, responder)."""
        # Default: random assignment
        # Override in specific mechanisms
        ...
```

This gives:
- **TIOLI**: Mechanism randomly assigns proposer/responder
- **Posted prices**: X_SELLER posts price, Y_SELLER accepts (or vice versa)
- **Gale-Shapley**: X_SELLERs propose, Y_SELLERs receive (or configurable)

---

## Part II: Agent Architecture Decisions

### 4. Belief Representation: Minimal Model

**The Question:** What is the minimal belief model that supports meaningful comparisons?

**Context:** Phase 1 of the development plan introduces agent beliefs. Beliefs affect search (who to approach), bargaining (what to demand), and interpretation of information (updating on signals). The design space is vast.

#### Analysis of Options

**Option A: Sufficient Statistics**

Agents maintain point estimates with uncertainty:
- Price belief: (mean, variance) of observed exchange rates
- Partner belief: (estimated_alpha, confidence) for known partners

*Pros:*
- Computationally simple
- Easy to interpret and visualize
- Sufficient for many research questions

*Cons:*
- Loses distributional information
- May not capture bimodal beliefs, fat tails
- Heuristic update rules may lack theoretical grounding

**Option B: Bayesian with Conjugate Priors**

Agents maintain parametric distributions that admit closed-form updates:
- Price belief: Beta distribution (for normalized price)
- Type belief: Beta distribution (for alpha parameter)

*Pros:*
- Theoretically grounded (Bayesian rationality)
- Testable predictions
- Closed-form updates are tractable

*Cons:*
- Conjugacy constrains distribution family
- Real learning may not be Bayesian
- Computational cost for many beliefs

**Option C: Configurable Belief Plugins**

Small interface with multiple implementations (Bayesian, heuristic, learning-based).

*Pros:*
- Maximum flexibility
- Belief sophistication as experimental variable
- Accommodates future learning agents

*Cons:*
- More complex architecture
- Interface design is non-trivial
- May lead to inconsistent behavior across plugins

#### Recommendation: Sufficient Statistics with Bayesian Option

**Primary:** Implement sufficient-statistics beliefs as the default.

**Secondary:** Provide Bayesian update as a configurable option for research validation.

**Justification:**

1. **Kreps grounding**: Kreps I Ch 5-7 covers choice under uncertainty and dynamic choice. The key insight is that beliefs should be decision-relevant: agents need enough information to make choices, not full posterior distributions.

2. **Computational tractability**: With N agents each tracking beliefs about N-1 others, quadratic growth is a concern. Sufficient statistics are O(1) per agent-pair.

3. **Research value**: The interesting question is "do beliefs matter for emergence?" not "what is the optimal belief structure?" Sufficient statistics enable the comparison while Bayesian option enables theoretical validation.

4. **Extensibility**: The plugin architecture (Option C) is valuable but premature. Build the first two implementations, then extract the interface.

#### Proposed Data Structure

```python
@dataclass
class PriceBelief:
    """Belief about exchange rate (y per x)."""
    mean: float  # Point estimate
    variance: float  # Uncertainty
    n_observations: int  # Sample size

    def update(self, observed_price: float) -> None:
        """Welford's online algorithm for mean/variance."""
        self.n_observations += 1
        delta = observed_price - self.mean
        self.mean += delta / self.n_observations
        delta2 = observed_price - self.mean
        self.variance = (
            (self.n_observations - 1) * self.variance + delta * delta2
        ) / self.n_observations

@dataclass
class PartnerBelief:
    """Belief about a specific trading partner."""
    agent_id: int
    estimated_alpha: float  # Believed preference parameter
    confidence: float  # 0-1, based on interaction history
    trade_history: list[TradeOutcome]  # Last N interactions

    def update(self, outcome: TradeOutcome, info_env: InformationEnvironment) -> None:
        """Update belief based on interaction outcome."""
        # Implementation depends on info environment
        ...

@dataclass
class AgentMemory:
    """Persistent state across ticks."""
    price_belief: PriceBelief
    partner_beliefs: dict[int, PartnerBelief]
    observation_history: deque[Observation]  # Bounded, FIFO

    max_history: int = 100  # Configurable memory depth
```

#### Memory Management

- **Bounded history**: Agents remember last N observations (configurable)
- **Partner-specific**: Beliefs about specific partners persist; beliefs about strangers use priors
- **Global priors**: Configurable prior for unknown partners (default: population mean)

---

### 5. Price Definition in 2-Good Bilateral Barter

**The Question:** What is "price" in a 2-good bilateral barter world, and how should it be logged?

**Context:** VISION.md emphasizes price convergence as a key emergence metric. But in pure barter, there's no money and no obvious price. We need an operational definition.

#### Analysis

In a 2-good economy, three price concepts are relevant:

1. **Exchange rate**: Δy/Δx in each trade (how much y was exchanged per unit of x)
2. **Marginal rate of substitution (MRS)**: Each agent's willingness to trade at the margin
3. **Walrasian price**: The competitive equilibrium price ratio that clears all markets

These are related but distinct:
- Exchange rate is observed per trade
- MRS is agent-specific and changes with holdings
- Walrasian price is a theoretical benchmark

#### Recommendation: Exchange Rate as Primary, MRS Convergence as Secondary

**Justification:**

1. **Observable**: Exchange rate is directly computed from each trade. No inference needed.

2. **Comparable to benchmark**: Walrasian equilibrium predicts a single price ratio. We can compare trade exchange rates to this prediction.

3. **Emergence indicator**: Market emergence means exchange rates converge to a common value. Tracking dispersion over time directly measures this.

4. **MRS as secondary**: MRS convergence across agents is another emergence indicator (agents' willingness to trade aligns). But MRS is not directly observable to other agents; it's an omniscient metric.

#### Proposed Logging

```python
@dataclass
class TradeEvent:
    tick: int
    agent_a_id: int
    agent_b_id: int
    bundle_a_before: Bundle
    bundle_a_after: Bundle
    bundle_b_before: Bundle
    bundle_b_after: Bundle

    @property
    def exchange_rate(self) -> float:
        """Compute y per x exchanged."""
        delta_x_a = self.bundle_a_after.x - self.bundle_a_before.x
        delta_y_a = self.bundle_a_after.y - self.bundle_a_before.y
        # Agent A gave up delta_y to get delta_x
        # Exchange rate = -delta_y / delta_x (for x-buyer)
        if abs(delta_x_a) < EPSILON:
            return float('inf')  # Degenerate trade
        return -delta_y_a / delta_x_a

    @property
    def normalized_price(self) -> float:
        """Price on [0, 1] scale for visualization."""
        # Map exchange_rate to probability scale
        # p = 1 means x is infinitely expensive
        # p = 0 means x is free
        rate = self.exchange_rate
        return rate / (1 + rate) if rate > 0 else 0
```

#### Emergence Metrics

1. **Price dispersion**: Standard deviation of exchange rates over last N trades
2. **Price level**: Mean exchange rate over last N trades
3. **MRS convergence**: Variance of MRS across agents after trades
4. **Walrasian gap**: Distance between mean exchange rate and Walrasian equilibrium price

---

## Part III: Institutional Design Decisions

### 6. Information Taxonomy: Minimal Set

**The Question:** What is the minimal set of information regimes worth implementing first?

**Context:** Information is central to "institutional visibility." The planning documents list: Private Values, Common Values, Signaling, Screening. The current implementation has FullInformation and NoisyAlphaInformation.

#### Analysis

The information regimes form a hierarchy of complexity:

1. **FullInformation**: Everyone knows everything (baseline)
2. **Private Values + Noise**: Agents know own type perfectly, observe noisy signals of others
3. **Common Values**: Types are correlated; agents observe noisy signals of a common underlying value
4. **Signaling**: Agents can send costly signals about their type
5. **Screening**: Uninformed agents design menus to separate types

Each regime adds significant complexity:
- Common values requires modeling the correlation structure
- Signaling requires modeling signal production and costs
- Screening requires modeling menu design and optimization

#### Recommendation: Private Values First, Signaling Second

**Phase 2A:** Complete Private Values with configurable noise structures.
**Phase 2B:** Add Signaling as the first asymmetric-information mechanism.
**Defer:** Common Values and Screening to future research programs.

**Justification:**

1. **Private values is foundational**: Most auction theory assumes private values (Kreps II Ch 24). It's the cleanest information structure for studying bilateral bargaining under uncertainty.

2. **NoisyAlphaInformation is almost private values**: The current implementation adds noise to observed alpha. Extending to general private values is incremental.

3. **Signaling is central to VISION.md**: The vision explicitly mentions signaling as an institutional dimension. Spence signaling (Kreps II Ch 20) is canonical.

4. **Common values is complex**: Common values requires correlation structure and winner's curse dynamics. This is a research program in itself (auctions, asset markets).

5. **Screening requires mechanism design**: Rothschild-Stiglitz screening involves menu optimization, which requires sophisticated agent behavior or mechanism intervention.

#### Proposed Implementation Order

```
Current:      FullInformation, NoisyAlphaInformation
Phase 2 add:  PrivateValuesEnvironment (generalized noise)
              ConfigurableSignalEnvironment (noise distribution choices)
Phase 2B add: SignalingEnvironment (costly signals, belief updating)
Future:       CommonValuesEnvironment, ScreeningEnvironment
```

#### PrivateValuesEnvironment Specification

```python
@dataclass
class PrivateValuesConfig:
    """Configuration for private values information structure."""

    # What dimensions are private?
    alpha_private: bool = True
    endowment_private: bool = False  # Usually observable
    discount_factor_private: bool = False

    # Signal noise structure
    noise_distribution: Literal["normal", "uniform", "beta"] = "normal"
    noise_params: dict = field(default_factory=lambda: {"std": 0.1})

    # Observation limits
    observation_radius: float = float('inf')  # Spatial limit
    signal_delay: int = 0  # Ticks before signal arrives

class PrivateValuesEnvironment(InformationEnvironment):
    def observe(self, observer: Agent, target: Agent) -> AgentType:
        """Observer receives noisy signal about target's type."""
        true_type = target.get_type()
        if not self.can_observe(observer, target):
            return None

        observed = AgentType(
            preferences=self._add_noise(true_type.preferences),
            endowment=true_type.endowment if not self.config.endowment_private
                     else self._add_noise(true_type.endowment),
            discount_factor=true_type.discount_factor
        )
        return observed
```

---

### 7. Benchmarks: Essential Set for First Research Program

**The Question:** Which benchmarks are essential for the market emergence research program?

**Context:** VISION.md emphasizes equilibrium as comparison baselines. The planning documents propose Walrasian equilibrium, core membership, and efficiency metrics.

#### Analysis

**Walrasian Equilibrium**
- Computes competitive equilibrium price and allocation
- For Cobb-Douglas with N agents: closed-form solution exists
- Computational cost: O(N) for Cobb-Douglas, O(N²) or worse for general preferences
- Research value: **High** (the primary benchmark for price convergence)

**Core**
- The set of allocations that no coalition can block
- For 2-agent exchange: equals the contract curve
- For N agents: computation is exponential in worst case (2^N coalitions)
- For 2 goods with Cobb-Douglas: tractable approximations exist
- Research value: **Medium** (important for welfare, but expensive)

**Efficiency Metrics**
- Distance from Pareto frontier
- Realized gains from trade vs. potential
- Distributional measures (Gini, variance of welfare)
- Computational cost: O(N) per allocation
- Research value: **High** (directly measures "how well did the market work?")

#### Recommendation: Walrasian + Efficiency Metrics; Core Optional

**Phase 3 core:** Walrasian equilibrium computation + efficiency metrics.
**Phase 3 optional:** Core membership for small N (≤ 10).
**Defer:** General core computation for large N.

**Justification:**

1. **Walrasian is the canonical benchmark**: "Did prices converge to competitive equilibrium?" is the central emergence question.

2. **Efficiency metrics are cheap and informative**: We can always compute realized utility vs. initial endowment. Comparing to Walrasian allocation gives a natural efficiency ratio.

3. **Core is expensive but theoretically important**: For the first research program, N will likely be 10-100. Core computation is feasible for N ≤ 10; beyond that, we can use Walrasian as a proxy (they coincide in the limit).

4. **Core convergence is a separate research question**: Edgeworth's conjecture (core shrinks to Walrasian as economy replicates) is itself a fascinating emergence phenomenon. But it's not the first question.

#### Proposed Implementation

```python
# analysis/equilibrium.py

def compute_walrasian_equilibrium(
    agents: list[Agent],
) -> WalrasianEquilibrium:
    """
    Compute competitive equilibrium for the exchange economy.

    For Cobb-Douglas preferences:
    - Total endowments: E_x = sum(e_i.x), E_y = sum(e_i.y)
    - Equilibrium price ratio: p = E_y / E_x (normalized p_x = 1)
    - Agent i's demand: x_i = alpha_i * I_i, y_i = (1-alpha_i) * I_i / p
      where I_i = p_x * e_i.x + p_y * e_i.y (income)
    """
    ...

def compute_efficiency_metrics(
    initial_allocation: dict[int, Bundle],
    final_allocation: dict[int, Bundle],
    preferences: dict[int, CobbDouglas],
    walrasian: WalrasianEquilibrium,
) -> EfficiencyMetrics:
    """
    Compute efficiency of simulation outcome relative to benchmarks.
    """
    realized_gain = sum(
        pref.utility(final_allocation[i]) - pref.utility(initial_allocation[i])
        for i, pref in preferences.items()
    )

    potential_gain = sum(
        pref.utility(walrasian.allocation[i]) - pref.utility(initial_allocation[i])
        for i, pref in preferences.items()
    )

    efficiency_ratio = realized_gain / potential_gain if potential_gain > 0 else 1.0

    # Also compute: Gini of final utilities, variance, etc.
    ...
```

---

### 8. Market Emergence: Operational Definition

**The Question:** What is the definition of "market has emerged"?

**Context:** The first research program is "market emergence." Without an operational definition, experiments become anecdotal.

#### Analysis

"Market" is a complex concept. Different aspects can be measured:

1. **Price convergence**: Do exchange rates converge to a common value?
2. **Price efficiency**: Does the common value approach Walrasian equilibrium?
3. **Network structure**: Do stable trading relationships form?
4. **Welfare efficiency**: Do gains from trade approach theoretical maximum?
5. **Coordination**: Do agents find trading partners reliably?

These are correlated but distinct. A simulation might have:
- Converged prices but low efficiency (trading at wrong price)
- High efficiency but dispersed prices (bilateral bargaining captures surplus differently)
- Stable networks but frequent non-trade (matching failure)

#### Recommendation: Composite Index with Three Pillars

Define market emergence as a conjunction of three measurable conditions:

**Pillar 1: Price Convergence**
- Metric: Coefficient of variation (CV) of exchange rates
- Threshold: CV < 0.1 for sustained period (e.g., last 20 ticks)
- Interpretation: Agents are trading at approximately the same terms

**Pillar 2: Price Efficiency**
- Metric: |mean exchange rate - Walrasian price| / Walrasian price
- Threshold: < 0.05 for sustained period
- Interpretation: The converged price is close to competitive equilibrium

**Pillar 3: Trade Frequency**
- Metric: Trades per tick per agent pair opportunity
- Threshold: > 0 for sustained period (no trade breakdown)
- Interpretation: The market continues to function

**Composite:**
Market emergence = (Pillar 1 met) AND (Pillar 2 met) AND (Pillar 3 met)

#### Justification

1. **Multi-dimensional**: Markets can fail in different ways. A single metric misses important failure modes.

2. **Empirically verifiable**: Each pillar is directly computable from logged data.

3. **Theoretically grounded**:
   - Price convergence → law of one price (Kreps I Ch 14)
   - Price efficiency → First Welfare Theorem prediction
   - Trade frequency → market liquidity/viability

4. **Threshold flexibility**: The specific thresholds are parameters. Research can explore how thresholds affect conclusions.

#### Proposed Implementation

```python
# analysis/emergence.py

@dataclass
class EmergenceMetrics:
    """Metrics for assessing market emergence."""
    price_cv: float  # Coefficient of variation of prices
    price_efficiency: float  # |mean - walrasian| / walrasian
    trade_rate: float  # Trades per tick per agent-pair

    # Sustained versions (over window)
    price_cv_sustained: bool
    price_efficiency_sustained: bool
    trade_rate_sustained: bool

    @property
    def market_emerged(self) -> bool:
        return (
            self.price_cv_sustained and
            self.price_efficiency_sustained and
            self.trade_rate_sustained
        )

def compute_emergence_metrics(
    run: SimulationRun,
    walrasian_price: float,
    window_size: int = 20,
    price_cv_threshold: float = 0.1,
    efficiency_threshold: float = 0.05,
    min_trade_rate: float = 0.01,
) -> EmergenceMetrics:
    """Compute emergence metrics for a simulation run."""
    ...
```

#### Secondary Metrics

Beyond the three pillars, track these for research insight:

- **Network metrics**: Clustering coefficient, average path length, degree distribution
- **Welfare distribution**: Gini coefficient, share of gains by agent type
- **Search efficiency**: Ticks to first trade, search distance traveled
- **Convergence speed**: Ticks until emergence criteria met

---

## Part IV: Research Infrastructure Decisions

### 9. Experimental Design: Factorial Design Representation

**The Question:** How should the platform represent "factorial design over institutions"?

**Context:** Framework completeness serves clean institutional comparisons. A factorial design needs consistent parameterization, naming, and metadata.

#### Analysis of Options

**Option A: Explicit DSL (YAML/JSON)**

Create a domain-specific language for experiment specification:

```yaml
experiment:
  name: "market_emergence_factorial"
  factors:
    bargaining: [nash, rubinstein, tioli]
    matching: [opportunistic, stable_roommates]
    information: [full, private_values]
  levels:
    n_agents: [10, 50, 100]
    grid_size: [15, 25, 50]
  replicates: 10
  seeds: "sequential"  # or "random"
```

*Pros:*
- Declarative, readable, version-controllable
- Separation of experiment design from code
- Enables experiment browsing/management tools

*Cons:*
- Another language to maintain
- Schema evolution challenges
- May not capture all configuration nuances

**Option B: Config Object as Source of Truth**

Keep experiment specification in Python but enforce serialization:

```python
@dataclass
class ExperimentConfig:
    """Must be fully serializable to JSON/YAML."""
    factors: dict[str, list[Any]]
    base_config: SimulationConfig
    replicates: int

    def to_yaml(self) -> str: ...
    @classmethod
    def from_yaml(cls, path: Path) -> "ExperimentConfig": ...
```

*Pros:*
- Python flexibility for complex configurations
- Type checking, IDE support
- No DSL maintenance

*Cons:*
- Serialization constraints on config values
- Less readable for non-programmers
- Config sprawl across files

**Option C: Thin CLI Wrapper**

Command-line interface that enumerates configs and manages runs:

```bash
microecon experiment run \
  --config experiments/market_emergence.yaml \
  --output runs/market_emergence_2026-01-05/
```

*Pros:*
- Familiar interface (like pytest, dvc)
- Integrates with shell automation
- Reproducibility through command history

*Cons:*
- Still needs underlying config format
- CLI argument parsing is error-prone

#### Recommendation: Option B with YAML Serialization and CLI Wrapper

**Core:** Config object is the source of truth. Must be serializable.
**Interface:** YAML files for experiment specification.
**Execution:** CLI wrapper for running experiments.

**Justification:**

1. **Config-as-code is fundamental**: Reproducibility requires exact config preservation. Python dataclasses with forced serialization ensure this.

2. **YAML for human interface**: Researchers edit YAML files. Python loads them into typed config objects. Best of both worlds.

3. **CLI for automation**: Shell scripts, CI/CD, cluster submission all benefit from CLI.

#### Proposed Implementation

```python
# scenarios/experiment.py

@dataclass
class FactorialExperiment:
    """Specification for a factorial experimental design."""

    name: str
    description: str

    # Base configuration (all non-varied parameters)
    base_config: SimulationConfig

    # Factors to vary (cartesian product)
    factors: dict[str, list[Any]]

    # Replication
    n_replicates: int
    seed_strategy: Literal["sequential", "random"] = "sequential"

    def enumerate_configs(self) -> Iterator[tuple[dict, SimulationConfig]]:
        """Yield (factor_values, config) for each cell of the design."""
        from itertools import product
        factor_names = list(self.factors.keys())
        for values in product(*self.factors.values()):
            factor_dict = dict(zip(factor_names, values))
            config = self._apply_factors(factor_dict)
            for rep in range(self.n_replicates):
                seed = self._compute_seed(factor_dict, rep)
                yield factor_dict | {"replicate": rep, "seed": seed}, config

# scenarios/schema.py - extend YAML schema

experiment_schema = """
type: experiment
name: string
description: string
base_config:
  n_agents: int
  grid_size: int
  ticks: int
  bargaining_protocol: string
  matching_protocol: string
  information_environment: string
factors:
  <factor_name>: [<values>]
n_replicates: int
seed_strategy: sequential | random
"""
```

#### CLI Interface

```bash
# List experiments
microecon experiment list

# Run experiment
microecon experiment run experiments/market_emergence.yaml \
  --output runs/market_emergence/ \
  --parallel 4

# Analyze results
microecon analyze runs/market_emergence/ \
  --metrics emergence,efficiency \
  --output results/market_emergence_analysis.json

# Generate figures
microecon visualize runs/market_emergence/ \
  --style publication \
  --output figures/
```

---

### 10. Performance and Scaling: O(n²) Strategy

**The Question:** What's the plan for O(n²) components?

**Context:** Comparative studies with 50-200 agents and many seeds can become time-expensive. Performance constraints affect feasible research designs.

Several components have O(n²) complexity:
- Search phase: Each agent evaluates all visible others
- Matching: Stable matching algorithms are O(n²) to O(n³)
- Belief updates: Each agent may track beliefs about all others

#### Analysis

**Current situation:**
- 200 agents, 100 ticks: ~5 minutes (per STATUS.md)
- Factorial design with 100 cells × 10 replicates = 1000 runs
- 1000 runs × 5 minutes = 83 hours (!!)

**Performance is a research constraint**, not just an engineering inconvenience.

#### Options

**Option A: Accept O(n²) with Documented Limits**

Profile, document limits, let researchers choose n accordingly.

*Pros:*
- No code changes
- Honest about constraints
- n ≤ 100 may be sufficient for many questions

*Cons:*
- Limits research scope
- Larger n is often theoretically interesting (convergence, scaling laws)

**Option B: Spatial Indexing / Locality**

Only evaluate nearby agents (within perception radius). Use grid-based bucketing for O(1) neighbor lookup.

*Pros:*
- Reduces practical complexity
- Economically meaningful (agents can't see everyone)
- Already have grid structure

*Cons:*
- Changes search semantics (can't evaluate distant agents)
- May require tuning perception radius

**Option C: Approximate Search (Sampling)**

Sample k random visible agents instead of evaluating all.

*Pros:*
- O(k) instead of O(n)
- Randomness may average out
- Bounded rationality justification

*Cons:*
- Introduces noise
- May miss best opportunities
- Another parameter to tune

**Option D: Parallelization**

Parallelize agent evaluation across cores.

*Pros:*
- Uses modern hardware
- No semantic changes
- Linear speedup with cores

*Cons:*
- Implementation complexity
- Python GIL limitations
- Still O(n²) work, just faster

#### Recommendation: Option B (Spatial Indexing) + Option A (Documented Limits) + Future Option D

**Now:** Implement spatial indexing for search. This is economically motivated (finite perception radius) and technically beneficial.

**Now:** Profile and document performance bounds at various n.

**Later:** Add parallelization for batch runs (embarrassingly parallel across seeds/configs).

**Justification:**

1. **Spatial indexing fits the model**: The platform has a grid. Perception radius already exists conceptually. Making search local is economically meaningful.

2. **Batch parallelization is easy**: Different seeds are independent. Running 4 parallel processes on 4 cores gives 4x speedup with no algorithmic changes.

3. **O(n²) matching may be unavoidable**: Stable matching algorithms are inherently expensive. But matching happens once per tick, not per agent. It's less of a bottleneck.

#### Proposed Implementation

```python
# grid.py - add spatial index

class SpatialIndex:
    """O(1) lookup of agents by grid cell."""

    def __init__(self, grid_size: int):
        self.grid_size = grid_size
        self.buckets: dict[tuple[int, int], set[int]] = defaultdict(set)

    def update(self, agent_id: int, old_pos: Position, new_pos: Position):
        if old_pos:
            self.buckets[old_pos.as_tuple()].discard(agent_id)
        self.buckets[new_pos.as_tuple()].add(agent_id)

    def agents_within_radius(self, center: Position, radius: int) -> set[int]:
        """Return agent IDs within Manhattan distance radius of center."""
        result = set()
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) <= radius:
                    x = (center.x + dx) % self.grid_size
                    y = (center.y + dy) % self.grid_size
                    result.update(self.buckets[(x, y)])
        return result

# search.py - use spatial index

def evaluate_visible_agents(
    agent: Agent,
    all_agents: dict[int, Agent],
    spatial_index: SpatialIndex,
    perception_radius: int,
) -> list[tuple[Agent, float]]:
    """Evaluate agents within perception radius. O(radius²) not O(n)."""
    visible_ids = spatial_index.agents_within_radius(
        agent.position, perception_radius
    )
    visible_ids.discard(agent.id)  # Don't evaluate self

    evaluations = []
    for other_id in visible_ids:
        other = all_agents[other_id]
        surplus = compute_nash_surplus(agent, other)
        evaluations.append((other, surplus))

    return sorted(evaluations, key=lambda x: x[1], reverse=True)
```

#### Performance Targets

| n_agents | Perception Radius | Expected Ticks/sec |
|----------|-------------------|--------------------|
| 50 | 5 | > 10 |
| 100 | 7 | > 5 |
| 200 | 10 | > 2 |
| 500 | 15 | > 0.5 |

These are aspirational; actual performance will be measured and documented.

---

## Part V: Consistency and Documentation

### 11. Resolving STATUS.md Inconsistencies

The PLANNING-REVIEW.md identified two minor inconsistencies in STATUS.md:

**Issue 1:** Information environment table says "FullInformation implemented" but later text mentions NoisyAlphaInformation.

**Resolution:** Update table row to: `information.py | FullInformation, NoisyAlphaInformation implemented`

**Issue 2:** "Config files (YAML/JSON) not implemented" contradicts YAML scenario description.

**Resolution:** Clarify: "YAML scenario files exist and are loadable. No GUI editor for config files."

### 12. Framework Completeness vs. Organic Growth Tension

**The Tension:** DEVELOPMENT-PLAN.md advocates "framework completeness before research exploitation" while VISION.md emphasizes "organic module growth."

**Resolution:** These are compatible with the right framing:

> Complete the minimal framework for the first research program (market emergence), then iterate research → framework in loops. Each research program may drive new institutional primitives.

Add to DEVELOPMENT-PLAN.md:

> **Philosophy:** "Minimal completeness, then iterate." Build the smallest set of primitives that enables meaningful institutional comparison for market emergence. Subsequent research programs will drive additional primitives. The framework grows organically, but each research program requires a complete (for that program) set of tools.

### 13. Label and Convention Definitions

Add to WORK-ITEMS.md header:

```markdown
## Conventions

### Labels

| Label | Meaning |
|-------|---------|
| `blocked` | Cannot proceed until a specific dependency (listed) is resolved. The blocking item may be internal (another work item) or external (architectural decision). |
| `foundational` | Changes this item makes affect multiple downstream items. Extra care required. |
| `critical` | Failure to resolve this item would significantly impair the research program. |

### Test Locations

| Category | Location | Purpose |
|----------|----------|---------|
| Theory verification | `tests/theory/` | Tests that verify implementation matches theoretical predictions (e.g., Nash product maximized) |
| Unit tests | `tests/test_*.py` | Standard unit tests for module functionality |
| Integration tests | `tests/integration/` | Tests that span multiple modules |
| Scenario regression | `tests/scenarios/` | End-to-end tests using YAML scenarios |

### Definition of Done

A work item is complete when:
1. Code is implemented and passes tests
2. Relevant theory verification tests added (for new primitives)
3. Documentation updated (STATUS.md, CLAUDE.md as appropriate)
4. Example scenario added (if applicable)
```

### 14. Glossary

Add to DEVELOPMENT-PLAN.md or as separate GLOSSARY.md:

```markdown
## Glossary

| Term | Definition |
|------|------------|
| **Protocol** | A specific set of rules for agent interaction, typically bargaining (Nash, Rubinstein, TIOLI) |
| **Mechanism** | A broader abstraction than protocol; includes multi-agent coordination (auctions, markets) |
| **Information Environment** | Rules governing what agents can observe about each other |
| **Private State** | Agent's true characteristics (preferences, endowments) |
| **Observable Type** | What other agents perceive; may differ from private state |
| **Beliefs** | Agent's probabilistic estimates about uncertain quantities (prices, partner types) |
| **Market Side** | Economic role derived from endowments (x-seller, y-seller) |
| **Exchange Rate** | The ratio Δy/Δx in a trade; operational definition of "price" |
| **Emergence** | Macro patterns arising from micro interactions; market emergence = price convergence + efficiency + liquidity |
| **Benchmark** | Theoretical prediction for comparison (Walrasian equilibrium, core) |
```

---

## Part VI: Work Item Additions

### Proposed New Work Items

Based on gaps identified in PLANNING-REVIEW.md, add these items to WORK-ITEMS.md:

```markdown
## Backlog (Deferred)

### PROD-001: Production Architecture
**Labels:** `backlog`, `deferred`
**Dependencies:** ARCH-001

**Description:**
Design and implement production capabilities. Deferred until after market emergence research program.

**Scope:**
- Production technology abstraction
- Integration with mechanism architecture
- Factor market implications

**Status:** Deferred

---

### MULTIGOOD-001: Multi-Good Generalization
**Labels:** `backlog`, `deferred`

**Description:**
Extend from 2-good to N-good economy. Deferred until research demands it.

**Scope:**
- Generalize Bundle to N dimensions
- Extend preference representations
- Update visualization for N > 2

**Status:** Deferred

---

### LEARN-001: Learning Agent Framework
**Labels:** `backlog`, `deferred`
**Dependencies:** BELIEF-006

**Description:**
Framework for learning agents (RL, evolutionary). Deferred until belief architecture stable.

**Scope:**
- Policy interface for agent decisions
- Integration points for learning algorithms
- Sophistication as experimental variable

**Status:** Deferred

---

### PERF-001: Performance Profiling and Bounds
**Labels:** `phase:0`
**Dependencies:** None

**Description:**
Profile current implementation and document performance bounds.

**Scope:**
- Identify O(n²) bottlenecks
- Measure actual performance at n = 50, 100, 200
- Document recommended limits
- Implement spatial indexing for search

**Status:** Not started

---

### REPRO-001: Reproducibility Infrastructure
**Labels:** `phase:2`
**Dependencies:** SCENARIO-001

**Description:**
Ensure experiments are fully reproducible.

**Scope:**
- Config + seed + code version = deterministic outcome
- Artifact bundle format (logs, config, version)
- Validation: re-running produces identical results

**Status:** Not started

---

### DOC-001: Documentation Maintenance Process
**Labels:** `cross-cutting`
**Dependencies:** None

**Description:**
Establish checklist for documentation updates when work items complete.

**Scope:**
- Update STATUS.md when capabilities change
- Add scenario for new primitives
- Update theoretical-foundations.md for new protocols
- CLAUDE.md architecture notes

**Status:** Not started
```

---

## Part VII: Summary and Prioritization

### Decision Summary

| Question | Decision | Confidence | Risk if Wrong |
|----------|----------|------------|---------------|
| ARCH-001 | Mechanism abstraction layer | High | Medium (architectural debt) |
| Production | Defer; ensure compatibility | High | Low |
| Roles | Endowment-derived + mechanism-assigned | Medium | Low (can refactor) |
| Beliefs | Sufficient stats default, Bayesian option | Medium | Low (can extend) |
| Price | Exchange rate primary | High | Low |
| Information | Private values → signaling | Medium | Low |
| Benchmarks | Walrasian + efficiency | High | Low |
| Emergence | Three-pillar composite | Medium | Medium (may need tuning) |
| Experiment design | Config-as-truth + YAML + CLI | Medium | Low |
| Performance | Spatial indexing + documented limits | High | Medium |

### Recommended Execution Order

1. **Immediate (before Phase 0):**
   - PERF-001: Profile and document current limits
   - DOC-001: Establish documentation process
   - STATUS.md fixes (inconsistencies)

2. **Phase 0 (Theoretical Alignment):**
   - THEORY-001 through THEORY-006 as specified
   - Add PERF-001 spatial indexing if not already done

3. **Phase 0.5 (Architecture - NEW):**
   - ARCH-001: Mechanism abstraction design session
   - Refactor existing protocols into mechanism framework
   - Validate with existing tests

4. **Phase 1 (Beliefs):**
   - BELIEF-001 through BELIEF-006 as specified
   - Use sufficient-statistics approach
   - Add Bayesian option as configuration

5. **Phase 2 (Primitives):**
   - Prioritize: TIOLI, Posted Prices, Random Matching
   - Then: Private Values, Signaling
   - Defer: Double Auction (needs ARCH-001), Common Values, Screening

6. **Phase 3 (Benchmarks):**
   - Walrasian equilibrium computation
   - Efficiency metrics
   - Emergence metrics (three pillars)
   - Optional: Core for small N

7. **Phase 4 (Research):**
   - Design factorial experiment
   - Run and analyze
   - Write up findings

### Open Items for Future Review

These decisions are provisional and should be revisited:

1. **Emergence thresholds**: The specific CV < 0.1, efficiency < 0.05 thresholds need empirical validation
2. **Belief update rules**: Sufficient statistics vs. Bayesian may need comparison study
3. **Multi-agent mechanism details**: ARCH-001 design session will refine the interface
4. **Signaling implementation**: Costliness structure, signal space need specification

---

## Appendix A: Cross-Reference to Source Documents

| This Document Section | Source Document | Relevant Section |
|-----------------------|-----------------|------------------|
| ARCH-001 | DEVELOPMENT-PLAN.md | Critical Architectural Decision Point |
| ARCH-001 | PLANNING-REVIEW.md | §6.1 |
| Production | PLANNING-REVIEW.md | §4.2B, §6.2 |
| Roles | PLANNING-REVIEW.md | §6.3 |
| Beliefs | DEVELOPMENT-PLAN.md | Phase 1 |
| Beliefs | PLANNING-REVIEW.md | §6.4 |
| Price | PLANNING-REVIEW.md | §6.5 |
| Information | DEVELOPMENT-PLAN.md | Phase 2B |
| Information | PLANNING-REVIEW.md | §6.6 |
| Benchmarks | DEVELOPMENT-PLAN.md | Phase 3 |
| Benchmarks | PLANNING-REVIEW.md | §6.7 |
| Emergence | PLANNING-REVIEW.md | §6.8 |
| Experiment Design | PLANNING-REVIEW.md | §6.9 |
| Performance | PLANNING-REVIEW.md | §6.10 |
| Multi-good | PLANNING-REVIEW.md | §4.2A |
| Learning | PLANNING-REVIEW.md | §4.2C |

---

## Appendix B: Theoretical Grounding Summary

| Decision | Theoretical Reference |
|----------|----------------------|
| Mechanism abstraction | O&R-B Ch 9-10 (trading procedures) |
| Role derivation from endowments | Kreps I Ch 14 (exchange economy) |
| Sufficient-statistics beliefs | Kreps I Ch 5-7 (decision theory) |
| Bayesian updating | Kreps II Ch 20 (adverse selection) |
| Exchange rate as price | Standard (Δy/Δx in barter) |
| Private values information | Kreps II Ch 24 (auctions) |
| Signaling | Kreps II Ch 20, Spence (1973) |
| Walrasian equilibrium | Kreps I Ch 14-15 |
| Core | Kreps I Ch 15.3, O&R-G Ch 13 |
| Nash bargaining | O&R-B Ch 2, O&R-G Ch 15 |
| Rubinstein SPE | O&R-B Ch 3, Kreps II Ch 23 |

---

**Document Version:** 1.0
**Created:** 2026-01-05
**Author:** Claude Opus 4.5 automated review
**Status:** Proposal for human review and iteration
