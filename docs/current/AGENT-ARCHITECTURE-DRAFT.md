# Agent Architecture: Design Document (Draft)

**Date:** 2026-01-08
**Status:** In-progress collaborative design
**Purpose:** Establish foundational agent model for the microecon platform

This document captures the ongoing discussion about agent architecture. It synthesizes resolved decisions and presents open questions for review.

---

## 1. Design Context

### 1.1 Why This Document

The platform has grown organically: bargaining protocols, information environments, beliefs, search mechanics. The roadmap discussion (ROADMAP-DISCUSSION-2026-01-08.md) introduced significant new complexity: action budgets, activity choice, consent models, production/gathering.

Before implementing these extensions, we need a coherent theoretical foundation for **what an agent IS** in this platform—independent of any particular implementation but with an eye toward its requirements.

### 1.2 Guiding Principles

From VISION.md:
- **Theoretical grounding**: All agent behavior must have formal justification from canonical sources
- **Institutional visibility**: Agents operate within configurable institutional rules; the institution is the experimental variable
- **Sophistication as variable**: Agent decision-making complexity (rule-based → bounded → fully rational → learning) is itself something we study, not a fixed assumption

From the discussion:
- **Agents are decision-makers**: Not just state containers that protocols operate on
- **Clean separation of concerns**: What an agent *is* (attributes) vs. what others *observe* (information environment) vs. what a theorist might *model* (game-theoretic type)

---

## 2. Phase 0 Resolution: Agent Identity

### 2.1 Foundational Definition

> **An agent is an autonomous economic decision-maker characterized by:**
> 1. **Attributes**: Preferences, holdings, patience, bargaining power, spatial position
> 2. **Beliefs**: What the agent thinks about the world (other agents, prices, opportunities)
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

## 3. Phase 1 Resolution: Agent Attributes

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
│   └── [future: fatigue, commitment state if unilateral]
│
└── Beliefs: BeliefSystem | None         # See Phase 2
```

### 3.2 Key Design Decisions

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| Preference representation | Interface with multiple implementations | Extensibility for studying how preference structure affects outcomes |
| Endowment vs Holdings | Both tracked; StoredHoldings for future | Endowment is disagreement point for Nash bargaining; holdings/stored enables spatial economy with homes/banks |
| Discount factor scope | **Universal** — affects all temporal decisions | Theoretically correct: δ discounts ANY future payoff. Distance → time → discounted surplus. This is already implicit in search; making it explicit and universal. |
| Bargaining power | Separate from δ, optional attribute | Different theoretical constructs. Power can derive from non-patience sources (institutional position, outside options, commitment ability). |
| Action state ownership | Agent-owned for unilateral constraints | Cooldowns are rules for agent's own behavior. Coordination state (mutual matching) tracked at simulation level. |

### 3.3 Theoretical Grounding for Each Attribute

| Attribute | Canonical Source | Key Concepts |
|-----------|-----------------|--------------|
| Preferences | Kreps I Ch 1-2 | Complete, transitive, continuous; utility representation theorem |
| Endowment | Exchange economy setup | Initial allocation; defines autarky utility (disagreement point) |
| Discount factor | O&R-B Ch 3, Kreps I Ch 7 | Patience; δ close to 1 means patient; affects all intertemporal tradeoffs |
| Bargaining power | O&R-B Ch 2.6 | Asymmetric Nash weights; can represent institutional advantages |
| Position | Platform-specific | Spatial frictions; search costs become literal distance |
| Beliefs | Kreps II Ch 20-21, O&R-B Ch 5 | Incomplete information; Bayesian updating |

---

## 4. Phase 2: Beliefs Architecture (Open Questions)

This is where we paused. Beliefs are theoretically central but operationally difficult.

### 4.1 What Are Beliefs About?

| Belief Category | Content | Theoretical Grounding |
|----------------|---------|----------------------|
| **About Other Agents** | Their preferences (α), patience (δ), bargaining power | Incomplete information games |
| **About Prices** | Expected exchange rate, variance | Rational expectations, learning |
| **About Environment** | Resource locations, market conditions | Search theory |
| **About Own Opportunities** | Expected surplus from potential trades | Derived from above |

### 4.2 How Are Beliefs Formed?

| Source | Mechanism | Example |
|--------|-----------|---------|
| **Prior** | Initial belief before observation | "Others' α ~ Uniform(0.3, 0.7)" |
| **Observation** | Perceive through info environment | See agent, get noisy signal of their α |
| **Inference from action** | Infer from observed behavior | "They rejected → good outside options" |
| **Trade outcome** | Learn from completed exchanges | "Traded at this rate → update price belief" |

### 4.3 How Do Beliefs Update?

**Bayesian updating** (canonical):
- Prior P(θ), likelihood P(s|θ), posterior P(θ|s) ∝ P(s|θ)P(θ)
- Theoretically correct
- Computationally expensive; requires specifying likelihood functions

**Heuristic updating** (bounded rationality):
- Exponential moving average: belief ← (1-λ)·belief + λ·observation
- Simpler, ad-hoc
- Needs theoretical justification for when this approximates Bayesian

**Current implementation**: Both available via swappable `UpdateRule` interface.

### 4.4 The Hard Problem: How Do Beliefs Affect Decisions?

Currently, beliefs exist but don't affect behavior. Making them affect behavior raises hard questions:

**Problem 1: What surplus function?**

If I'm uncertain about your type, I should compute expected surplus:
```
E[surplus(A, B)] = ∫ surplus(A, θ_B) · P(θ_B) dθ_B
```

This requires integrating over belief distribution. Computationally expensive. Also requires agent to "know" how surplus is computed (Nash? Rubinstein? TIOLI?).

**Problem 2: Strategic considerations**

Should my beliefs include "will this partner accept?" This is reasoning about others' strategies, not just types—much harder.

**Problem 3: Consistency across agents**

In Bayesian games, beliefs must be consistent (common prior, commonly known update rules). In simulation, agents update based on observations that depend on others' strategies that depend on their beliefs... We can't guarantee consistency.

### 4.5 Proposed Belief Architecture

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
│   │   # Uses TypeBeliefs + protocol's surplus function
│   └── acceptance_probability(partner) → float  # Future
│
└── Memory
    ├── trade_history: [(tick, partner, bundles)]
    ├── observation_history: [(tick, agent_id, perceived_type)]
    └── interaction_history: [(tick, agent_id, outcome)]
```

**Key design choices in this proposal:**

1. **Point estimates for decisions**: Even with distributional beliefs, decisions use `expected_type()` or `expected_surplus()`. Bounded rationality: agents don't do full Bayesian integration, they use expectations.

2. **Protocol-aware surplus**: `expected_surplus(partner, protocol)` uses the active protocol's logic. Agents "know" institutional rules (standard assumption: common knowledge of game structure).

3. **UpdateRule is swappable**: Different agents/scenarios can use Bayesian vs. heuristic.

4. **Beliefs affect decisions through explicit interface**: Decision logic queries `expected_surplus()`, not raw beliefs. Auditable pathway from beliefs to actions.

---

## 5. Open Questions for Review

### 5.1 Beliefs: Point Estimates vs Full Distributions (Q2.1)

Should decision-making use:

| Option | Description | Trade-off |
|--------|-------------|-----------|
| **(a) Point estimates** | Compute expected type, then compute surplus with that type | Simpler, faster; ignores uncertainty |
| **(b) Expected surplus** | Integrate surplus over full type distribution | More correct; computationally heavier |
| **(c) Configurable** | Point estimates default; expected surplus for "sophisticated" agents | Flexibility; more complexity |

**Consideration**: (a) is a form of certainty equivalence—treating the expected type as if it were the true type. This is a boundedly rational simplification. (b) is what a fully Bayesian agent would do. Making this a sophistication variable aligns with VISION.md.

---

### 5.2 Do Agents Know the Bargaining Protocol? (Q2.2)

For `expected_surplus(partner, protocol)` to work, agents must "know" how surplus is computed.

| Option | Description | Implication |
|--------|-------------|-------------|
| **(a) Yes, common knowledge** | Agents know institutional rules | Standard game theory assumption; simplest |
| **(b) Agents learn protocol** | Experience teaches what outcomes to expect | Interesting but complex; how to formalize? |
| **(c) Protocol-specific** | Some protocols have clear rules (Nash); others don't (Nash Demand—can't predict partner's demand) | May need different treatment per protocol |

**Consideration**: (a) is the standard theoretical assumption and probably the right default. But (c) raises an interesting point: in Nash Demand Game, agents can't compute expected surplus because they don't know what the partner will demand. This is qualitatively different from Nash or Rubinstein.

---

### 5.3 Should Beliefs Include Acceptance Probability? (Q2.3)

Should beliefs include "will this partner accept my proposal?"

| Option | Description | Implication |
|--------|-------------|-------------|
| **(a) No** | Assume positive-surplus trades execute | Current model; simpler |
| **(b) Yes, simple** | Acceptance probability from observed rejection rates | Enables learning about partner behavior |
| **(c) Yes, strategic** | Infer acceptance from beliefs about partner's outside options | Full strategic reasoning; complex |

**Consideration**: The roadmap introduces a consent model where trades require mutual selection + acceptance. If agents can reject, beliefs about acceptance become relevant. (a) may be too simple for the new model.

---

### 5.4 Belief Consistency Across Agents (Q2.4)

In Bayesian games, beliefs must be consistent (common prior, common update rules). We can't guarantee this in simulation.

| Option | Description | Implication |
|--------|-------------|-------------|
| **(a) Accept inconsistency** | Agents have subjective, potentially contradictory beliefs | Realistic; hard to interpret theoretically |
| **(b) Impose structure** | Common prior + common update rule; divergence only from different observations | Standard assumption; enables cleaner analysis |
| **(c) Study as variable** | Inconsistency itself is experimental variable | Research question: how does belief heterogeneity affect outcomes? |

**Consideration**: (b) is the standard theoretical assumption and probably the right starting point. (c) is an interesting extension once (b) is working.

---

## 6. Phases Still Ahead

Once beliefs are resolved, we still need to specify:

### Phase 3: Agent Perception

- How does the information environment interface with agent observation?
- What is the observation process each tick?
- How do observations feed into belief updates?

### Phase 4: Agent Decision Architecture

- What is the decision procedure?
- How does it query beliefs?
- How does it interact with the tick model's action budget?
- How do we formalize different sophistication levels?

### Phase 5: Agent in the Tick Model

- How does the action-budget model constrain decisions?
- Move | Trade | Gather | Produce | Wait — how does agent choose?
- Consent model: mutual selection + proposal + acceptance

### Phase 6: Agent Objectives and Welfare

- Utility maximization as objective
- How is welfare measured and compared?
- Gains from trade relative to endowment vs. relative to holdings

---

## 7. Theoretical References

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

---

## 8. Summary: What's Resolved vs. Open

### Resolved

| Item | Decision |
|------|----------|
| Agent identity | Autonomous decision-maker with attributes, beliefs, decision rule |
| Type as class | No — derive from attributes + info environment when needed |
| Self-knowledge | Perfect (standard assumption); bounded rationality via decision rule |
| Preference representation | Interface with implementations (CobbDouglas, CES, etc.) |
| Endowment vs Holdings | Both tracked; StoredHoldings for future |
| Discount factor scope | Universal — affects all temporal decisions |
| Bargaining power | Separate from δ; optional attribute |
| Action state ownership | Agent-owned for unilateral; simulation for coordination |
| Belief architecture | Proposed structure with TypeBeliefs, PriceBeliefs, Memory |

### Open

| Question | Options Under Consideration |
|----------|----------------------------|
| Q2.1: Point estimates vs distributions | (a) Point estimates, (b) Expected surplus, (c) Configurable |
| Q2.2: Protocol knowledge | (a) Common knowledge, (b) Learn from experience, (c) Protocol-specific |
| Q2.3: Acceptance probability | (a) Assume acceptance, (b) Simple learning, (c) Strategic inference |
| Q2.4: Belief consistency | (a) Accept inconsistency, (b) Impose structure, (c) Study as variable |

---

**Document Version:** 0.1 (Draft)
**Created:** 2026-01-08
**Next:** Review open questions; continue to Phase 3 (Perception) and Phase 4 (Decision Architecture)
