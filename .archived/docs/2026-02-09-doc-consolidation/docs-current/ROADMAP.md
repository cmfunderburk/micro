# Platform Roadmap

**Date:** 2026-01-09
**Status:** Active — unified source of truth
**Purpose:** Define agent architecture and development roadmap for the microecon platform

This document consolidates the agent architecture design and development roadmap into a single authoritative source. It supersedes `ROADMAP-DISCUSSION-2026-01-08.md` and incorporates all content from `AGENT-ARCHITECTURE.md`.

---

## 1. Overview

### 1.1 Current Capabilities

The platform provides a solid foundation:
- Core exchange mechanics (preferences, bundles, bargaining, search, matching)
- Four bargaining protocols (Nash, Rubinstein, Asymmetric Nash, TIOLI)
- Information environments (Full, NoisyAlpha)
- Belief system (price beliefs, type beliefs, memory, update rules)
- Rich visualization and analysis infrastructure

### 1.2 Development Directions

Two interconnected expansion directions:
1. **Bilateral protocol breadth** — More bargaining mechanisms for institutional comparison
2. **Sustained economies** — Production/gathering to enable ongoing exchange

### 1.3 Guiding Principles

From VISION.md:
- **Theoretical grounding**: All agent behavior must have formal justification from canonical sources
- **Institutional visibility**: Agents operate within configurable institutional rules; the institution is the experimental variable
- **Sophistication as variable**: Agent decision-making complexity (rule-based → bounded → fully rational → learning) is itself something we study, not a fixed assumption

From Chicago Price Theory tradition:
- **Broad applicability**: The same toolkit applies to exchange, production, investment, and "noneconomic" behaviors
- **Don't over-categorize a priori**: Categories are analytical tools, not ontological primitives
- **Practical focus**: Theory serves measurement, explanation, and prediction of behavior

### 1.4 Key Architectural Insight

The platform makes **transaction costs explicit** through the tick model:
- Search costs = ticks spent moving toward partners
- Proposal costs = ticks spent initiating exchange
- Negotiation costs = ticks spent in bargaining
- Coordination failure costs = ticks wasted on rejected proposals

Different institutional configurations have different tick costs, enabling meaningful comparison.

---

## 2. Agent Architecture

### 2.1 Foundational Definition

> **An agent is an autonomous economic decision-maker characterized by:**
> 1. **Attributes**: Preferences, holdings, patience, bargaining power, spatial position
> 2. **Beliefs**: What the agent thinks about the world (architecturally present, behaviorally deferred)
> 3. **Decision rule**: How the agent maps perceived state to action choice
>
> The agent's **objective** is utility maximization, but the **decision rule** may be:
> - Fully rational (compute optimal action)
> - Boundedly rational (satisfice, use heuristics)
> - Adaptive (learn from experience)
>
> This is an experimental variable, not a fixed assumption.

### 2.2 On "Type"

The game-theoretic concept of *type* (private information determining payoffs) should **not** be reified as a class within Agent.

Instead:
- Agent has **attributes** (preferences, endowment, discount_factor, bargaining_power, etc.)
- **Information environment** determines which attributes are observable to whom
- **Game-theoretic type** is derived when needed for theoretical analysis, not stored as agent state

This cleanly separates:
- What an agent *is* (attributes)
- What others can *see* (observation function of information environment)
- What a theorist might *model* (type in mechanism design sense)

### 2.3 Self-Knowledge

**Resolved**: Agents have perfect self-knowledge of their own attributes (standard rational choice assumption).

Bounded rationality is achieved by constraining the *decision rule*, not by introducing self-uncertainty—though the architecture should not preclude that extension.

### 2.4 Attribute Structure

```
Agent
├── Preferences (interface)
│   ├── utility(bundle) → float
│   ├── MRS(bundle) → float
│   ├── indifference_curve(utility_level) → curve
│   └── [implementations: CobbDouglas, CES, Linear, Leontief, QuasiLinear]
│
├── Endowment: Bundle                    # Initial allocation (immutable)
├── Holdings: Bundle                     # Current inventory on-person (mutable)
├── StoredHoldings: Bundle | None        # At home/bank (future extension)
│
├── Metabolism: Bundle | None            # Per-tick consumption requirement (Phase B+)
│   # When active: holdings_t+1 = holdings_t - metabolism + acquired_t
│   # Enables sustained economy; see §2.12 for objective function implications
│   # Good-specific rates allow heterogeneous treatment (food vs durables)
│   # None = no metabolism (Phase A: static equilibrium)
│
├── DiscountFactor: float ∈ (0, 1]       # Universal time preference
│   # Affects ALL temporal decisions:
│   # - Partner ranking (distant = future, discounted)
│   # - Activity choice (now vs later)
│   # - Bargaining (patience = power in Rubinstein)
│
├── BargainingPower: float | None        # Exogenous leverage (for Asymmetric Nash)
│   # Distinct from patience; may derive from institutional position,
│   # outside options, commitment ability
│
├── Position: GridPosition               # Current spatial location
│
├── InteractionState                     # Agent-owned interaction constraints
│   ├── rejection_cooldowns: {agent_id: ticks_remaining}
│   ├── state: Available | ProposalPending | Negotiating
│   └── [future: fatigue, commitment state]
│
└── Beliefs: BeliefSystem | None         # See §2.6
```

### 2.5 Attribute Design Decisions

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| Preference representation | Interface with multiple implementations | Extensibility for studying how preference structure affects outcomes |
| Endowment vs Holdings | Both tracked; StoredHoldings for future | Endowment is disagreement point for Nash bargaining; holdings/stored enables spatial economy with homes/banks |
| Discount factor scope | **Universal** — affects all temporal decisions | Theoretically correct: δ discounts ANY future payoff. Distance → time → discounted surplus. |
| Bargaining power | Separate from δ, optional attribute | Different theoretical constructs. Power can derive from non-patience sources (institutional position, outside options, commitment ability). |
| Interaction state ownership | Agent-owned for unilateral constraints | Cooldowns are rules for agent's own behavior. Coordination state (mutual matching) tracked at simulation level. |
| Metabolism | Optional Bundle; None for Phase A | Enables sustained economy (Phase B+). As Bundle, allows good-specific consumption rates. Background depletion, not action choice. |

### 2.6 Beliefs Architecture

Beliefs are **architecturally present but behaviorally inert** for now.

- `BeliefSystem` remains an optional component on Agent
- The interface is defined (TypeBeliefs, PriceBeliefs, Memory)
- Decision logic does **not** query beliefs — agents act on true observed attributes
- When ready, beliefs "plug in" to decision-making without restructuring Agent

**Current Behavioral Model:**

Agents under `FullInformation` behave as standard rational actors with common knowledge.

Under `NoisyAlphaInformation`, agents observe noisy types but treat them as true (no Bayesian updating, no strategic inference about the noise). This is a well-defined behavioral model — naive agents who trust their observations.

**Belief System Interface (for future activation):**

```
BeliefSystem (interface)
│
├── TypeBeliefs
│   ├── get_belief(agent_id) → Distribution over θ
│   ├── update(agent_id, observation)
│   └── expected_type(agent_id) → point estimate
│
├── PriceBeliefs
│   ├── get_price_belief() → (mean, variance)
│   └── update(observed_trade)
│
├── OpportunityBeliefs (derived)
│   ├── expected_surplus(partner, protocol) → float
│   └── acceptance_probability(partner) → float
│
└── Memory
    ├── trade_history: [(tick, partner, bundles)]
    ├── observation_history: [(tick, agent_id, perceived_type)]
    └── interaction_history: [(tick, agent_id, outcome)]
```

**Deferred Questions:**

| Question | Options | Notes |
|----------|---------|-------|
| Point estimates vs distributions | (a) Point estimates, (b) Expected surplus, (c) Configurable | Trade-off: simplicity vs theoretical correctness |
| Protocol knowledge | (a) Common knowledge, (b) Learn from experience, (c) Protocol-specific | Standard assumption is (a) |
| Acceptance probability | (a) Assume acceptance, (b) Simple learning, (c) Strategic inference | Relevant once consent model is active |
| Belief consistency | (a) Accept inconsistency, (b) Impose structure, (c) Study as variable | (b) is standard theoretical assumption |

### 2.7 Perception Model

```
Perception
├── Perception Radius: float              # How far agent can "see"
│
├── Raw Perception: passive reception
│   - Each tick, agent receives all agents within radius
│   - Information environment determines what attributes are visible
│   - No action cost, no choice — this is sensory input
│   - Analogy: sight/hearing — what's available without calculation
│
└── Attention (future extension)
    - Filters perception radius, not a cost on top of it
    - Could model: bounded attention → smaller effective radius
    - Or: salience → some agents more "visible" than others
    - Architecture allows, but not in initial model
```

**Perception Layers:**

| Layer | What It Determines | Current Status |
|-------|-------------------|----------------|
| Physical availability | Who is within perception radius | Active |
| Information availability | What attributes are observable | Active (via InformationEnvironment) |
| Attention filtering | What subset enters decision-making | Future extension (identity function for now) |

### 2.8 Decision Architecture

**Core Insight: Categories as Metadata, Not Structure**

The action space should **not** be hardcoded as `{Move, Trade, Gather, Produce, Wait}`.

Instead:
- Actions are **typed** with an extensible enumeration
- Categories (exchange, production, movement, investment) are **tags for analysis**, not hierarchical structure
- The decision procedure evaluates **all available actions directly** — no category-first logic

This follows the Chicago tradition: don't over-categorize a priori. Categories serve research questions, not constrain them.

**Action Interface:**

```
Action (interface)
├── type: ActionType                    # Extensible enumeration (Move, Trade, Gather, Propose, Accept, ...)
├── transform(agent_state) → agent_state # What state changes result
├── cost() → Cost                       # Time, resources, opportunity
├── preconditions(agent_state) → bool   # Can this action be taken?
└── tags: Set[str]                      # Analysis metadata: {"exchange", "bilateral"}, {"production", "unilateral"}, etc.
```

**Decision Procedure Interface:**

```
DecisionProcedure (interface)
│
├── Input: PerceivedState
│   ├── own_attributes (preferences, holdings, δ, position)
│   ├── perceived_others (within perception radius, filtered by info environment)
│   ├── environment (resource locations, market conditions)
│   ├── interaction_state (cooldowns, commitments, proposal state)
│   └── memory (history, even if not feeding beliefs)
│
├── available_actions() → Set[Action]   # Scenario-configured
├── evaluate(action) → float            # Sophistication determines method
└── choose() → Action                   # argmax, satisfice, sample, etc.
```

**Sophistication as Experimental Variable:**

| Level | Evaluation Method | Theoretical Basis |
|-------|------------------|-------------------|
| Rule-based | Heuristic scoring | Behavioral rules of thumb |
| Bounded | Simplified optimization, satisficing | Simon's bounded rationality |
| Rational | Full optimization over action space | Standard rational choice |
| Adaptive | Learned value function | Reinforcement learning, evolutionary dynamics |

Sophistication varies **how** evaluation works, not **what** is evaluated. All levels use the same Action and DecisionProcedure interfaces.

### 2.9 Tick Model

**Action Budget:**

```
Action Budget
├── Default: 1 action per tick
├── Configurable per scenario
└── Future: endogenous budgets (fatigue, energy, etc.)
```

**Tick Structure:**

Each tick follows a simple three-phase structure:

```
Tick Structure
│
├── PERCEIVE
│   └── All agents observe current state (frozen snapshot)
│   └── Perception radius and information environment apply
│
├── DECIDE
│   └── All agents select actions based on perceived state
│   └── No agent observes another's decision
│   └── DecisionProcedure.choose() executes for each agent
│
└── EXECUTE
    └── Conflict resolution (see §2.10)
    └── All actions execute, producing next state
    └── State changes are batched, not sequential
```

There is no special "co-location resolution phase" — co-located agents simply have additional actions available (Propose, Accept) which their DecisionProcedure evaluates alongside Move, Gather, Wait, etc.

### 2.10 Bilateral Exchange Sequence

Trade requires mutual consent. The default model:

```
Bilateral Exchange Sequence
│
├── Tick T: Agent A chooses Propose(target=B, terms=...)
│   ├── Proposer lock: configurable (locked = default)
│   │   - Locked: A waits for response, cannot act
│   │   - Unlocked: A can continue other activities
│   └── Multiple proposals: protocol-specific
│       - Exclusive: one active proposal at a time
│       - Broadcast: can propose to multiple; first acceptance wins
│
├── Tick T+1: Agent B observes proposal
│   ├── Visibility determined by information environment:
│   │   - Posted price → public within perception radius
│   │   - Targeted offer → private to recipient
│   └── B chooses Accept(A) | Reject | other action
│
├── Tick T+2: Negotiation phase (if accepted)
│   ├── Bargaining protocol executes
│   ├── Duration: configurable (1 tick default)
│   └── Can fail (no zone of agreement)
│
└── Tick T+3: Trade executes (if negotiation succeeds)
    └── Holdings update for both agents
```

**Failed Actions Yield Information:**

When actions fail (e.g., proposal rejected, target moved away):
- Agent learns outcome: "B rejected" or "B was unavailable"
- Information stored in Memory component
- Feeds into future belief systems when activated
- Enables learning about partner behavior

**Transaction Costs Made Explicit:**

| Phase | Tick Cost | What It Represents |
|-------|-----------|-------------------|
| Search | Movement ticks | Physical/information search costs |
| Proposal | 1 tick (+ wait if locked) | Cost of initiating exchange |
| Negotiation | 1+ ticks (configurable) | Bargaining/contracting costs |
| Failed proposal | Wasted tick(s) | Risk of coordination failure |

This operationalizes transaction cost economics. Different protocols have different tick costs, making institutional comparison meaningful.

### 2.11 Interaction State Machine

Bilateral exchange involves interaction states that persist across ticks.

**Agent Interaction States:**

```
AgentInteractionState
│
├── Available
│   ├── Can propose to others (subject to cooldowns)
│   ├── Can receive and respond to proposals
│   └── Can take other actions (Move, Gather, Wait)
│
├── ProposalPending(target: AgentId, tick_sent: int)
│   ├── Has outbound proposal awaiting response
│   ├── CAN receive and respond to other proposals
│   │   └── Accepting another withdraws own pending proposal
│   ├── Locked mode: cannot take other actions until resolved
│   └── Unlocked mode: can take other actions (configurable)
│
├── Negotiating(partner: AgentId, protocol: Protocol, phase: int)
│   ├── In active negotiation with partner
│   ├── Cannot take other actions
│   ├── Cannot receive new proposals
│   └── Duration: protocol-specific (1+ ticks)
│
└── Cooldown: Dict[AgentId, int]  (orthogonal to above)
    ├── Cannot propose to specific agents until cooldown expires
    ├── Decrements each tick
    ├── Default duration: 3 ticks (configurable)
    └── Triggered by: own proposal rejected by that agent
```

**State Transitions:**

| From | To | Trigger |
|------|-----|---------|
| Available | ProposalPending(B) | Agent chooses Propose(B) |
| Available | Negotiating(A) | Received proposal from A, chose Accept |
| ProposalPending(B) | Negotiating(B) | B accepted proposal |
| ProposalPending(B) | Available + Cooldown(B) | B rejected proposal |
| ProposalPending(B) | Available | Proposal timeout (1 tick, configurable) |
| ProposalPending(B) | Available | Co-location lost (B moved away) |
| ProposalPending(B) | Negotiating(C) | Received proposal from C, chose Accept (withdraws proposal to B) |
| Negotiating(B) | Available | Protocol completes (trade succeeds or fails) |
| Negotiating(B) | Available | Co-location lost (negotiation fails) |

**Mutual Proposals:** If A proposes to B and B proposes to A in the same tick, this is detected as mutual interest. Both agents transition directly to Negotiating(other).

**Co-location Requirement:** Strict co-location is required throughout the exchange sequence:
- Proposal requires co-location to initiate
- Proposal expires if co-location lost before response
- Negotiation requires co-location; either agent moving causes failure
- Trade execution requires co-location

This makes "staying" a meaningful choice — agents in negotiation implicitly choose not to move.

### 2.12 Concurrency Model

All agents decide simultaneously within a tick. Conflicts are resolved deterministically.

```
Concurrency: Simultaneous Decision, Batched Execution

1. OBSERVATION
   └── All agents observe frozen state_t

2. DECISION
   └── All agents select actions based on state_t
   └── Decisions are independent; no agent sees another's choice

3. CONFLICT RESOLUTION
   ├── Multiple proposals to same target:
   │   └── Target evaluates all proposals
   │   └── Target accepts proposal with highest expected surplus
   │   └── Non-accepted proposals: treated as "target unavailable"
   │   └── No cooldown for non-accepted (not explicit rejection)
   │
   ├── Mutual proposals (A→B and B→A):
   │   └── Detected as mutual interest
   │   └── Both enter Negotiating state
   │
   └── Crossing paths (A moves from X to Y, B moves from Y to X):
       └── No special interaction ("ships in the night")
       └── A ends at Y, B ends at X
       └── They were never co-located

4. EXECUTION
   └── All actions execute against state_t
   └── State changes combine to produce state_t+1
   └── Execution order (by agent_id) is deterministic but
       should not affect outcomes due to batching

5. VALIDATION
   └── Check invariants (non-negative holdings, valid positions)
```

**Tie-Breaking Rules:**
- When choosing among proposals: higher expected surplus wins
- If surplus tied: lower agent_id wins (deterministic)
- Any other ties: seeded RNG (reproducible with same seed)

### 2.13 Acceptance Rules

When an agent receives a proposal, they must decide Accept or Reject. The default rule is surplus-based.

**Default Acceptance Rule (Rational Agent):**

```
For agent B receiving proposal from A:

1. Compute expected outcome under active protocol
   outcome = protocol.compute_outcome(A, B, info_environment)

2. Compute expected surplus for self
   surplus_B = u_B(outcome.holdings_B) - u_B(current_holdings_B)

3. Decision
   if surplus_B ≥ 0: Accept
   else: Reject
```

**Information Environment Variants:**

| Environment | Surplus Calculation |
|-------------|---------------------|
| FullInformation | Exact: uses true types of both agents |
| NoisyAlphaInformation | Naive: uses perceived (noisy) types, no Bayesian correction |

Under noisy information, agents may:
- Accept trades that are actually unfavorable (noise was favorable)
- Reject trades that would be beneficial (noise was unfavorable)

These "mistakes" are features, not bugs — they enable study of information asymmetry effects.

**Protocol-Specific Notes:**

- **TIOLI (Take-it-or-leave-it):** Responder's surplus = 0 (proposer extracts all). Under ≥ 0 rule, responder accepts when indifferent.
- **Nash/Rubinstein:** Surplus split according to protocol; both parties typically have positive surplus.

**Configurable Parameters:**
- `acceptance_threshold: float = 0.0` — change to require strictly positive surplus
- `acceptance_noise: float = 0.0` — add stochastic element to accept/reject decision

### 2.14 Agent Objectives

**Phase A Objective (Static Equilibrium):**

```
Agent Objective (Phase A)
├── Maximize: Σ δ^t · u(holdings_t)
│   └── Present discounted value of utility from holdings
│
└── Interpretation: Holdings are durable; utility flows from possession
    └── Valid for: bargaining protocol comparison, convergence studies
    └── Limitation: economy reaches static equilibrium and trade stops
```

This formulation is sufficient for Phase A research (bargaining protocol comparison). Agents trade until reaching Pareto-optimal allocation, then stop. Static equilibrium is a valid and interesting outcome for studying protocol properties.

**Phase B+ Objective (Sustained Economy):**

```
Agent Objective (Phase B+)
├── Maximize: Σ δ^t · u(c_t)
│   └── Present discounted value of utility from CONSUMPTION
│
├── Consumption as metabolism (background process)
│   ├── Each tick: holdings_t+1 = holdings_t - metabolism + acquired_t
│   ├── metabolism: Bundle specifying per-tick consumption requirement
│   ├── c_t = metabolism (automatic consumption each tick)
│   └── Agent's problem: acquire enough to sustain metabolism
│
└── Implications:
    └── Creates ongoing demand ("demand sink")
    └── Enables sustained market activity
    └── Makes production/gathering economically necessary
```

The transition from Phase A to Phase B objective is what enables "market emergence" as an ongoing phenomenon rather than a one-time convergence.

**Holdings Complexity (Future Extension):**

```
├── On-person: Holdings (immediately accessible)
├── Stored: StoredHoldings (at home/bank/etc.)
└── Utility evaluation options (configurable):
    - u(accessible) — only what's on-person
    - u(total_wealth) — all assets regardless of location
    - u(accessible) + δ_storage · u(stored) — stored goods discounted

Research variable: How does "value of storage" affect behavior?
- Foraging economy: only accessible matters
- Secure property rights: total wealth matters
- Imperfect storage: discounted by retrieval cost/risk
```

### 2.15 Welfare Measurement

Multiple measures tracked; researcher selects for analysis:

| Measure | Formula | Use Case |
|---------|---------|----------|
| Utilitarian | Σ u_i | Aggregate welfare |
| Pareto improvements | Count of trades improving both parties | Efficiency |
| Gini coefficient | Inequality of utility/holdings | Distribution |
| vs Walrasian | Compare to competitive equilibrium | Benchmark efficiency |
| vs Initial | Compare to endowment allocation | Total gains from trade |

**Gains from Trade:**

| Baseline | Calculation | Interpretation |
|----------|-------------|----------------|
| vs Endowment | u(holdings) - u(endowment) | Total gain from participation in economy |
| vs Previous | u(holdings_t) - u(holdings_{t-1}) | Marginal gain from most recent activity |

### 2.16 Theoretical References for Agent Model

| Attribute | Canonical Source | Key Concepts |
|-----------|-----------------|--------------|
| Preferences | Kreps I Ch 1-2 | Complete, transitive, continuous; utility representation theorem |
| Endowment | Exchange economy setup | Initial allocation; defines autarky utility (disagreement point) |
| Discount factor | O&R-B Ch 3, Kreps I Ch 7 | Patience; δ close to 1 means patient; affects all intertemporal tradeoffs |
| Bargaining power | O&R-B Ch 2.6 | Asymmetric Nash weights; can represent institutional advantages |
| Position | Platform-specific | Spatial frictions; search costs become literal distance |
| Beliefs | Kreps II Ch 20-21, O&R-B Ch 5 | Incomplete information; Bayesian updating |

---

## 3. Phase A: Bilateral Protocol Expansion

**Scope:** Complete the bilateral bargaining protocol suite for institutional comparison.

**Why first:**
- Relatively contained
- Extends existing infrastructure
- Enables immediate comparison research
- Doesn't require sustained economy

### 3.1 Currently Implemented

| Protocol | Type | Key Property | Reference |
|----------|------|--------------|-----------|
| Nash Bargaining | Axiomatic | Symmetric, efficient, IIA | O&R Ch 2 |
| Rubinstein | Strategic (SPE) | Patience = power, first-mover advantage | O&R Ch 4 |
| Asymmetric Nash | Axiomatic | β-weighted Nash product | O&R Ch 2.6 |
| TIOLI | Strategic | Proposer extracts all surplus | O&R §2.8 |

### 3.2 Remaining Protocols

#### Kalai-Smorodinsky Solution

**Mechanism:**
- Axiomatic solution like Nash
- Replace Independence of Irrelevant Alternatives (IIA) with monotonicity
- Outcome: Point on Pareto frontier where ratio of gains equals ratio of maximal possible gains

**Theoretical significance:**
- Alternative fairness concept
- More sensitive to bargaining set shape than Nash
- Same information requirements as Nash (full knowledge of preferences)

**Comparison value:**
- When do Nash and K-S diverge significantly?
- Which better predicts observed behavior?

**Reference:** Kalai & Smorodinsky (1975), O&R Ch 2

#### Nash Demand Game

**Mechanism:**
- Simultaneous move game
- Each agent states a demand (share of surplus)
- If demands compatible (sum ≤ total), trade at stated terms
- If incompatible (sum > total), no trade (disagreement)

**Theoretical significance:**
- Tests coordination without communication
- Multiple equilibria (any split is an equilibrium)
- Focal points matter

**Comparison value:**
- Very different from sequential protocols
- How do agents coordinate?
- Does learning lead to conventions?

**Reference:** Nash (1953), game theory texts

### 3.3 Protocol Design Decisions (Resolved)

| ID | Question | Resolution | Rationale |
|----|----------|------------|-----------|
| Q1 | TIOLI proposer selection | **Configurable** | Random / First-mover / By type / Fixed role — all valid research configurations |
| Q2 | Asymmetric Nash β determination | **Per-agent w_i, β = w_i/(w_i+w_j)** | Configurable per scenario; can derive from δ or make situational later |
| Q3 | Nash Demand demand representation | **Surplus share** | Scalar s_i ∈ [0,1], compatible if s_A + s_B ≤ 1 |
| Q4 | Nash Demand disagreement handling | **Walk away** | Preserves coordination failure content; no fallback protocol |

### 3.4 Protocol Comparison Matrix

| Protocol | Power Distribution | Information Required | Strategic Complexity | Efficiency |
|----------|-------------------|---------------------|---------------------|------------|
| Nash | Symmetric | Full (preferences) | None (axiomatic) | Pareto optimal |
| Rubinstein | Patience-weighted | Full + discount factors | High (SPE) | Pareto optimal |
| TIOLI | Proposer takes all | Full | Low | Pareto optimal |
| K-S | Symmetric | Full | None (axiomatic) | Pareto optimal |
| Asymmetric Nash | β-weighted | Full + power parameter | None (axiomatic) | Pareto optimal |
| Nash Demand | Emergent | Partial? | Medium (coordination) | May fail |

### 3.5 Implementation Considerations

**Shared infrastructure:**
- All protocols take: two agents, their preferences, endowments, disagreement point
- All return: trade outcome (bundles exchanged) or no-trade

**Protocol-specific needs:**
- K-S: Computation of ideal points (maximal individual gains)
- Nash Demand: demand representation, compatibility check, coordination failure handling

**Search integration:**
- Search uses active protocol's surplus for target evaluation
- Agent protocol preferences deferred to later phase

### 3.6 Phase A Deliverables

- [ ] Kalai-Smorodinsky protocol implementation
- [ ] Nash Demand Game implementation
- [ ] Protocol comparison scenarios
- [ ] Updated analysis tools for protocol comparison

---

## 4. Phase B: Sustained Economies

**Scope:** Resource nodes, gathering mechanic, minimal activity choice

**Purpose:** Enable sustained economies that don't converge to stasis

### 4.1 The Exchange Exhaustion Problem

The current model is a **finite game**:

```
Initialize(endowments) → Search → Match → Bargain → Trade → ... → Exhaustion → Stasis
```

Without resource regeneration, the simulation converges to a state where:
1. All agents have traded to contract curve (no more mutually beneficial trades), or
2. Agents are spatially separated with no reachable partners

**Consequence:** Cannot study:
- Repeat relationships (nothing to trade after first exchange)
- Network evolution over time
- Sustained "market-like" activity
- Long-run learning effects

### 4.2 What Production/Gathering Enables

With resource acquisition:

```
Initialize → [Produce/Gather] → Search → Match → Bargain → Trade → [Consume] → Loop
```

This creates a **sustained economy** where:
- Agents regularly acquire heterogeneous goods
- Trade opportunities regenerate
- Networks can evolve over time
- Learning has time to show effects
- Spatial patterns can emerge and persist

### 4.3 Production (Theoretical Grounding)

**Core concept:** Transformation of inputs to outputs via production function. (Kreps I, Ch 7-9)

**For 2-good economy:**
- Agent can transform good X into good Y (or vice versa)
- Production function: y = f(x) with standard properties
- Heterogeneous production capabilities create comparative advantage

**Gains from specialization:**
- Even with identical preferences, different production functions create trade gains
- Connects to classical trade theory (Ricardo)

### 4.4 Gathering/Harvesting

**Core concept:** Resource extraction from environment.

**Mechanism:**
- Resource nodes exist at grid locations
- Agents at node can extract goods
- Extraction rate may depend on: time spent, agent skill, node richness, crowding

**Design:**
- "Crude harvesting mechanic" — agents gather resources from locations
- Makes spatial positioning meaningful beyond search

### 4.5 Consumption

**Resolution:** Active depletion (either fixed consumption or % decay)

This breaks one-shot dynamics by creating ongoing need. The metabolism attribute on Agent (§2.4) implements this:
- `holdings_t+1 = holdings_t - metabolism + acquired_t`
- Creates demand sink
- Makes production/gathering economically necessary

### 4.6 Economy Design Decisions (Resolved)

| ID | Question | Resolution | Rationale |
|----|----------|------------|-----------|
| Q5 | Resource node placement | **Fixed** | Scenario-specified; random as optional mode for robustness |
| Q6 | Resource regeneration | **Fixed rate with cap** | Standard renewable resource; depletion-recovery as future extension |
| Q7 | Activity choice architecture | **Heuristic first** | "Gather if low, trade if opportunity" behind swappable interface |
| Q8 | Consumption modeling | **Active depletion** | Either fixed consumption or % decay; breaks one-shot dynamics |
| Q9 | Location priority | **Nodes only** | Minimal sustained economy first; homes/markets later |

### 4.7 Phase B Deliverables

- [ ] Resource node infrastructure (placement, capacity, regeneration)
- [ ] Gathering mechanic (action type, extraction rate)
- [ ] Metabolism implementation (per-tick consumption)
- [ ] Basic activity choice heuristic behind swappable interface
- [ ] Scenarios demonstrating sustained exchange

---

## 5. Phase C: Spatial Structure

**Scope:** Homes, production sites, market locations

**Purpose:** Full spatial economy with differentiated locations

### 5.1 Current Grid: Undifferentiated Space

Every cell is identical. Space matters only for:
- Search friction (must be within perception radius)
- Movement cost (takes time to traverse)

### 5.2 Differentiated Space: Location Types

| Location Type | Function | What Happens There | Theoretical Basis |
|---------------|----------|-------------------|-------------------|
| **Resource Node** | Extraction | Agents gather goods | Resource economics |
| **Home** | Anchor | Rest, storage, consumption | Household production |
| **Production Site** | Transformation | Agents produce goods | Theory of the firm |
| **Market** | Exchange facilitation | Reduced search friction | Market microstructure |

### 5.3 Architecture Design Decisions (Resolved)

| ID | Question | Resolution | Rationale |
|----|----------|------------|-----------|
| Q10 | Search with multiple protocols | **Use active protocol** | Search evaluates using protocol's surplus; agent preferences later |
| Q11 | Locations: fixed vs emergent | **Fixed** | For resources; markets may emerge definitionally |
| Q12 | Market location mechanics | **Definitional first** | Markets are where agents congregate; mechanical effects later |

### 5.4 What Locations Provide

**Resource Nodes:**
- Extraction of specific goods
- May have capacity limits
- May have crowding effects (future)

**Homes (future):**
- Storage (inventory beyond carried goods)
- Consumption site (utility realized only at home)
- Safety (cannot be approached while at home)
- Production (home production function)

**Markets (future):**
- Reduced search cost (larger effective perception radius)
- Different matching/bargaining rules (e.g., posted prices)
- Network effects from concentration

### 5.5 Phase C Deliverables

- [ ] Location type system
- [ ] Home locations (agent anchors, storage)
- [ ] Production sites (transformation mechanics)
- [ ] Market location effects
- [ ] Complex spatial scenarios

---

## 6. Phase D: Emergence Analysis

**Scope:** Tools and scenarios for studying emergence

### 6.1 Focus Areas

**Network Metrics:**
- Clustering coefficient
- Degree distribution
- Path length
- Community detection

**Spatial Clustering:**
- Autocorrelation
- Hotspot detection
- Movement patterns

**Learning Dynamics:**
- Belief convergence
- Partner preferences
- Strategy evolution

**Cross-Protocol Comparison:**
- Same economy, different institutions
- Welfare comparisons
- Efficiency measures

### 6.2 Phase D Deliverables

- [ ] Network analysis module extensions
- [ ] Spatial clustering metrics
- [ ] Emergence visualization overlays
- [ ] Benchmark scenarios for each phenomenon
- [ ] Documentation of emergence patterns

---

## 7. Deferred Work

### 7.1 From Agent Architecture

| Component | Status |
|-----------|--------|
| Beliefs affecting behavior | Architecture ready; activation requires resolving belief deferred questions |
| Attention filtering | Interface allows; not in initial model |
| StoredHoldings | Attribute defined; utility implications need specification |
| Metabolism implementation | Attribute defined; good-specific rates need specification for diverse economies |
| Multilateral exchange | Extension point identified; not implemented |
| Endogenous action budgets | Configurable defined; endogenous logic deferred |
| Production/Technology | Needed for Phase B comparative advantage; attribute not yet defined |

### 7.2 From Economy Design

| Item | Notes |
|------|-------|
| Crowding externalities at resource nodes | Flagged in reviews; implement in Phase B |
| Nash Demand Game demand formation | How agents form demands (beliefs? focal points? learning?) |
| Consumption model specifics | Fixed rate vs % decay — decide during Phase B implementation |

### 7.3 Architectural Decisions

**StableRoommates Deprecation:**

The `StableRoommatesMatchingProtocol` implementation conflicts with the action-budget tick model:
1. **Centralized vs agent-autonomous**: StableRoommates runs Irving's algorithm centrally
2. **Commitment overrides action budget**: Bypasses consent mechanisms
3. **Paradigm mismatch**: Computes and imposes outcomes rather than letting coordination emerge

**Resolution:** Deprecated. A properly integrated stable matching mechanism would:
- Have agents *propose* commitments as an action (not computed centrally)
- Make proposals visible within some information environment
- Define acceptance rules that agents follow autonomously
- Let stability emerge from repeated proposal/acceptance decisions
- Use Irving's algorithm as a theoretical benchmark, not a runtime mechanism

---

## 8. References

### Canonical Sources

- **Kreps I (Microeconomic Foundations I: Choice and Competitive Markets)**
  - Ch 1-2: Preferences and utility
  - Ch 3-4: Consumer choice
  - Ch 5-6: Intertemporal choice
  - Ch 7-9: Production

- **Osborne & Rubinstein (Bargaining and Markets)**
  - Ch 2: Axiomatic bargaining (Nash, K-S, Asymmetric)
  - Ch 3: Strategic bargaining introduction
  - Ch 4: Rubinstein alternating offers
  - Ch 5: Incomplete information bargaining

- **Nash (1950, 1953)**
  - "The Bargaining Problem" — axiomatic solution
  - "Two-Person Cooperative Games" — demand game

- **Kalai & Smorodinsky (1975)**
  - "Other Solutions to Nash's Bargaining Problem"

### Additional Sources

- Becker (1965) — Household production theory
- Resource economics texts — Common pool extraction
- Network economics — Trade network formation
- Market microstructure — Location and market formation
- Coase (1937), Williamson (1985) — Transaction costs

---

## 9. Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-09 | Initial unified document consolidating AGENT-ARCHITECTURE.md v0.3 and ROADMAP-DISCUSSION.md v2.1 |

**Supersedes:**
- `AGENT-ARCHITECTURE.md` — content integrated into §2
- `ROADMAP-DISCUSSION-2026-01-08.md` — content integrated throughout; tick model from §6.2 superseded by §2.9-2.13

**Authoritative for:**
- Agent definition and attributes
- Tick model and interaction semantics
- Development phases and priorities
- Resolved design decisions
