# Agent Architecture: Design Document

**Date:** 2026-01-09
**Status:** Draft — pending review
**Purpose:** Establish foundational agent model for the microecon platform

This document captures the agent architecture designed through collaborative discussion. It synthesizes resolved decisions across six phases of design.

---

## 1. Design Context

### 1.1 Why This Document

The platform has grown organically: bargaining protocols, information environments, beliefs, search mechanics. The roadmap discussion introduced significant new complexity: action budgets, activity choice, consent models, production/gathering.

Before implementing these extensions, we need a coherent theoretical foundation for **what an agent IS** in this platform—independent of any particular implementation but with an eye toward its requirements.

### 1.2 Guiding Principles

From VISION.md:
- **Theoretical grounding**: All agent behavior must have formal justification from canonical sources
- **Institutional visibility**: Agents operate within configurable institutional rules; the institution is the experimental variable
- **Sophistication as variable**: Agent decision-making complexity (rule-based → bounded → fully rational → learning) is itself something we study, not a fixed assumption

From Chicago Price Theory tradition:
- **Broad applicability**: The same toolkit applies to exchange, production, investment, and "noneconomic" behaviors (discrimination, crime, family, health)
- **Don't over-categorize a priori**: Categories are analytical tools, not ontological primitives
- **Practical focus**: Theory serves measurement, explanation, and prediction of behavior

### 1.3 Key Architectural Insight

The platform makes **transaction costs explicit** through the tick model:
- Search costs = ticks spent moving toward partners
- Proposal costs = ticks spent initiating exchange
- Negotiation costs = ticks spent in bargaining
- Coordination failure costs = ticks wasted on rejected proposals

Different institutional configurations have different tick costs, enabling meaningful comparison.

---

## 2. Phase 0: Agent Identity

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

---

## 3. Phase 1: Agent Attributes

### 3.1 Attribute Structure

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
│   # Enables sustained economy; see §8.1 for objective function implications
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
├── ActionState                          # Agent-owned action constraints
│   ├── rejection_cooldowns: {agent_id: ticks_remaining}
│   ├── proposal_state: Waiting | Available
│   └── [future: fatigue, commitment state]
│
└── Beliefs: BeliefSystem | None         # See Phase 2
```

### 3.2 Key Design Decisions

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| Preference representation | Interface with multiple implementations | Extensibility for studying how preference structure affects outcomes |
| Endowment vs Holdings | Both tracked; StoredHoldings for future | Endowment is disagreement point for Nash bargaining; holdings/stored enables spatial economy with homes/banks |
| Discount factor scope | **Universal** — affects all temporal decisions | Theoretically correct: δ discounts ANY future payoff. Distance → time → discounted surplus. |
| Bargaining power | Separate from δ, optional attribute | Different theoretical constructs. Power can derive from non-patience sources (institutional position, outside options, commitment ability). |
| Action state ownership | Agent-owned for unilateral constraints | Cooldowns are rules for agent's own behavior. Coordination state (mutual matching) tracked at simulation level. |
| Metabolism | Optional Bundle; None for Phase A | Enables sustained economy (Phase B+). As Bundle, allows good-specific consumption rates. Background depletion, not action choice. |

### 3.3 Theoretical Grounding

| Attribute | Canonical Source | Key Concepts |
|-----------|-----------------|--------------|
| Preferences | Kreps I Ch 1-2 | Complete, transitive, continuous; utility representation theorem |
| Endowment | Exchange economy setup | Initial allocation; defines autarky utility (disagreement point) |
| Discount factor | O&R-B Ch 3, Kreps I Ch 7 | Patience; δ close to 1 means patient; affects all intertemporal tradeoffs |
| Bargaining power | O&R-B Ch 2.6 | Asymmetric Nash weights; can represent institutional advantages |
| Position | Platform-specific | Spatial frictions; search costs become literal distance |
| Beliefs | Kreps II Ch 20-21, O&R-B Ch 5 | Incomplete information; Bayesian updating |

---

## 4. Phase 2: Beliefs Architecture

### 4.1 Resolution: Deferred Implementation

Beliefs are **architecturally present but behaviorally inert** for now.

- `BeliefSystem` remains an optional component on Agent
- The interface is defined (TypeBeliefs, PriceBeliefs, Memory)
- Decision logic does **not** query beliefs — agents act on true observed attributes
- When ready, beliefs "plug in" to decision-making without restructuring Agent

### 4.2 Current Behavioral Model

Agents under `FullInformation` behave as standard rational actors with common knowledge.

Under `NoisyAlphaInformation`, agents observe noisy types but treat them as true (no Bayesian updating, no strategic inference about the noise). This is a well-defined behavioral model — naive agents who trust their observations.

### 4.3 Belief System Interface (for future activation)

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

### 4.4 Deferred Questions

The following questions are deferred until beliefs are activated:

| Question | Options | Notes |
|----------|---------|-------|
| Point estimates vs distributions | (a) Point estimates, (b) Expected surplus, (c) Configurable | Trade-off: simplicity vs theoretical correctness |
| Protocol knowledge | (a) Common knowledge, (b) Learn from experience, (c) Protocol-specific | Standard assumption is (a) |
| Acceptance probability | (a) Assume acceptance, (b) Simple learning, (c) Strategic inference | Relevant once consent model is active |
| Belief consistency | (a) Accept inconsistency, (b) Impose structure, (c) Study as variable | (b) is standard theoretical assumption |

---

## 5. Phase 3: Agent Perception

### 5.1 Perception Model

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

### 5.2 Perception Layers

| Layer | What It Determines | Current Status |
|-------|-------------------|----------------|
| Physical availability | Who is within perception radius | Active |
| Information availability | What attributes are observable | Active (via InformationEnvironment) |
| Attention filtering | What subset enters decision-making | Future extension (identity function for now) |

---

## 6. Phase 4: Agent Decision Architecture

### 6.1 Core Insight: Categories as Metadata, Not Structure

The action space should **not** be hardcoded as `{Move, Trade, Gather, Produce, Wait}`.

Instead:
- Actions are **typed** with an extensible enumeration
- Categories (exchange, production, movement, investment) are **tags for analysis**, not hierarchical structure
- The decision procedure evaluates **all available actions directly** — no category-first logic

This follows the Chicago tradition: don't over-categorize a priori. Categories serve research questions, not constrain them.

### 6.2 Action Interface

```
Action (interface)
├── type: ActionType                    # Extensible enumeration (Move, Trade, Gather, Propose, Accept, ...)
├── transform(agent_state) → agent_state # What state changes result
├── cost() → Cost                       # Time, resources, opportunity
├── preconditions(agent_state) → bool   # Can this action be taken?
└── tags: Set[str]                      # Analysis metadata: {"exchange", "bilateral"}, {"production", "unilateral"}, etc.
```

### 6.3 Decision Procedure Interface

```
DecisionProcedure (interface)
│
├── Input: PerceivedState
│   ├── own_attributes (preferences, holdings, δ, position)
│   ├── perceived_others (within perception radius, filtered by info environment)
│   ├── environment (resource locations, market conditions)
│   ├── action_state (cooldowns, commitments, proposal state)
│   └── memory (history, even if not feeding beliefs)
│
├── available_actions() → Set[Action]   # Scenario-configured
├── evaluate(action) → float            # Sophistication determines method
└── choose() → Action                   # argmax, satisfice, sample, etc.
```

### 6.4 Sophistication as Experimental Variable

| Level | Evaluation Method | Theoretical Basis |
|-------|------------------|-------------------|
| Rule-based | Heuristic scoring | Behavioral rules of thumb |
| Bounded | Simplified optimization, satisficing | Simon's bounded rationality |
| Rational | Full optimization over action space | Standard rational choice |
| Adaptive | Learned value function | Reinforcement learning, evolutionary dynamics |

Sophistication varies **how** evaluation works, not **what** is evaluated. All levels use the same Action and DecisionProcedure interfaces.

---

## 7. Phase 5: Agent in the Tick Model

### 7.1 Action Budget

```
Action Budget
├── Default: 1 action per tick
├── Configurable per scenario
└── Future: endogenous budgets (fatigue, energy, etc.)
```

### 7.2 Bilateral Exchange Sequence

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

### 7.3 Failed Actions Yield Information

When actions fail (e.g., proposal rejected, target moved away):
- Agent learns outcome: "B rejected" or "B was unavailable"
- Information stored in Memory component
- Feeds into future belief systems when activated
- Enables learning about partner behavior

### 7.4 Transaction Costs Made Explicit

| Phase | Tick Cost | What It Represents |
|-------|-----------|-------------------|
| Search | Movement ticks | Physical/information search costs |
| Proposal | 1 tick (+ wait if locked) | Cost of initiating exchange |
| Negotiation | 1+ ticks (configurable) | Bargaining/contracting costs |
| Failed proposal | Wasted tick(s) | Risk of coordination failure |

This operationalizes transaction cost economics. Different protocols have different tick costs, making institutional comparison meaningful.

### 7.5 Multilateral Extension Point

The architecture supports future multilateral exchange by:
- Proposals can specify multiple targets (protocol-specific)
- Acceptance logic can require N-of-M responses
- Negotiation protocols can involve >2 parties

### 7.6 Tick Structure

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
    └── Conflict resolution (see §7.8)
    └── All actions execute, producing next state
    └── State changes are batched, not sequential
```

This replaces any notion of mandatory "phases" within the tick. There is no special "co-location resolution phase" — co-located agents simply have additional actions available (Propose, Accept) which their DecisionProcedure evaluates alongside Move, Gather, Wait, etc.

### 7.7 Interaction State Machine

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

### 7.8 Concurrency Model

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

### 7.9 Acceptance Rules

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

---

## 8. Phase 6: Agent Objectives and Welfare

### 8.1 Agent Objective Function

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

### 8.2 Welfare Measurement (Analysis Infrastructure)

Multiple measures tracked; researcher selects for analysis:

| Measure | Formula | Use Case |
|---------|---------|----------|
| Utilitarian | Σ u_i | Aggregate welfare |
| Pareto improvements | Count of trades improving both parties | Efficiency |
| Gini coefficient | Inequality of utility/holdings | Distribution |
| vs Walrasian | Compare to competitive equilibrium | Benchmark efficiency |
| vs Initial | Compare to endowment allocation | Total gains from trade |

### 8.3 Gains from Trade

Both baselines tracked:

| Baseline | Calculation | Interpretation |
|----------|-------------|----------------|
| vs Endowment | u(holdings) - u(endowment) | Total gain from participation in economy |
| vs Previous | u(holdings_t) - u(holdings_{t-1}) | Marginal gain from most recent activity |

---

## 9. Summary: Architecture Overview

### 9.1 Complete Agent Structure

```
Agent
├── Identity
│   └── Autonomous decision-maker; type derived not stored
│
├── Attributes
│   ├── Preferences: interface (CobbDouglas, CES, Linear, Leontief, QuasiLinear)
│   ├── Endowment: Bundle (immutable)
│   ├── Holdings: Bundle (mutable, on-person)
│   ├── StoredHoldings: Bundle | None (future)
│   ├── Metabolism: Bundle | None (Phase B+; enables sustained economy)
│   ├── DiscountFactor: float ∈ (0, 1]
│   ├── BargainingPower: float | None
│   ├── Position: GridPosition
│   └── InteractionState: Available | ProposalPending | Negotiating + Cooldowns
│
├── Beliefs (architecturally present, behaviorally deferred)
│   ├── TypeBeliefs
│   ├── PriceBeliefs
│   ├── OpportunityBeliefs
│   └── Memory
│
├── Perception
│   ├── perception_radius: float
│   └── Passive reception; attention filtering future
│
├── Decision
│   ├── available_actions: Set[Action] (scenario-configured)
│   ├── evaluate: Action → float (sophistication-dependent)
│   └── choose: () → Action
│
├── Interaction (see §7.6-7.9)
│   ├── Tick structure: Perceive → Decide → Execute
│   ├── State machine: Available/ProposalPending/Negotiating
│   ├── Concurrency: simultaneous decision, batched execution
│   └── Acceptance: surplus ≥ 0 (naive under noisy info)
│
└── Objective
    ├── Phase A: Maximize Σ δ^t · u(holdings_t)
    └── Phase B+: Maximize Σ δ^t · u(c_t) with metabolism
```

### 9.2 Key Design Principles

| Principle | Implementation |
|-----------|---------------|
| Theoretical grounding | All behavior justified from canonical sources |
| Institutional visibility | Transaction costs explicit through tick model |
| Extensibility | Interfaces for Preferences, Actions, DecisionProcedure, Beliefs |
| Sophistication as variable | Same interfaces, different evaluation methods |
| Categories as metadata | Action tags for analysis, not decision structure |
| Clean separation | Attributes vs. observables vs. theoretical types |

### 9.3 What's Resolved vs. Deferred

**Resolved:**

| Component | Decision |
|-----------|----------|
| Agent identity | Autonomous decision-maker; type derived from attributes + info environment |
| Self-knowledge | Perfect (standard assumption) |
| Attributes | Full structure defined; Metabolism for Phase B+ |
| Beliefs | Interface defined; behaviorally inert for now |
| Perception | Passive reception within radius; attention filtering future |
| Actions | Typed enumeration with tags; not hierarchical categories |
| Decision procedure | Evaluation-based; sophistication varies method |
| Tick structure | Perceive → Decide → Execute (no special co-location phase) |
| Interaction states | Available / ProposalPending / Negotiating with explicit transitions |
| Co-location | Strict: required throughout proposal → negotiation → execution |
| Concurrency | Simultaneous decision, batched execution; target chooses among proposals |
| Acceptance rule | Accept iff surplus ≥ 0; naive (trust observations) under noisy info |
| Bilateral exchange | Multi-tick sequence with configurable protocol duration |
| Objective (Phase A) | Maximize Σ δ^t · u(holdings_t); static equilibrium valid |
| Objective (Phase B+) | Maximize Σ δ^t · u(c_t) with metabolism; sustained economy |
| Welfare | Multiple measures tracked |

**Deferred:**

| Component | Status |
|-----------|--------|
| Beliefs affecting behavior | Architecture ready; activation requires resolving Q2.1-Q2.4 |
| Attention filtering | Interface allows; not in initial model |
| StoredHoldings | Attribute defined; utility implications need specification |
| Metabolism implementation | Attribute defined; good-specific rates need specification for diverse economies |
| Multilateral exchange | Extension point identified; not implemented |
| Endogenous action budgets | Configurable defined; endogenous logic deferred |
| Production/Technology | Needed for Phase B comparative advantage; attribute not yet defined |

---

## 10. Theoretical References

| Topic | Primary Source | Key Sections |
|-------|---------------|--------------|
| Preferences & Utility | Kreps I | Ch 1-2 |
| Consumer Choice | Kreps I | Ch 3-4 |
| Intertemporal Choice | Kreps I | Ch 5-7 |
| Bargaining (Axiomatic) | O&R-B | Ch 2 |
| Bargaining (Strategic) | O&R-B | Ch 3-4 |
| Incomplete Information | Kreps II | Ch 20-21 |
| Incomplete Info Bargaining | O&R-B | Ch 5 |
| Search & Matching | Kreps II | Ch 25 |
| Bayesian Games | O&R-G | Ch 11-12 |
| Transaction Costs | Coase (1937), Williamson (1985) | — |
| Price Theory Applications | Chicago Price Theory (Mulligan) | Introduction |

---

**Document Version:** 0.3
**Created:** 2026-01-08
**Updated:** 2026-01-09
**Status:** Revised with interaction semantics, concurrency model, acceptance rules, and Phase A/B objective clarification
