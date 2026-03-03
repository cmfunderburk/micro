# Architecture Overview

**Status:** Working document for architectural decisions
**Purpose:** Single-source overview of agent architecture, simulation loop, and institutional components
**Last Updated:** 2026-01-13

This document synthesizes decisions from vision discussions into a coherent architectural picture. Unresolved branches are marked with **[OPEN]**.

---

## 1. Agent Model

### 1.1 State Structure

Agents have a layered state model:

```
Agent
├── Private State (ground truth)
│   ├── preferences: CobbDouglas(alpha)
│   ├── endowment: Bundle(x, y)
│   └── bargaining_power: float
│
├── Observable Type (what others can see)
│   └── Determined by ObservationEnvironment
│
├── Beliefs (agent's model of others)
│   ├── type_beliefs: Dict[AgentId, TypeBelief]
│   ├── price_beliefs: PriceBeliefs
│   └── memory: TradeMemory
│
└── Interaction State (cooldowns, commitments)
    ├── state: InteractionState enum
    └── cooldowns: Dict[AgentId, int]
```

**Key distinction:** Private state is ground truth. Observable type is what others perceive (may differ under noisy observation). Beliefs are the agent's subjective model of others.

### 1.2 Decision Procedure

Agents select actions via a `DecisionProcedure` interface:

```python
class DecisionProcedure(ABC):
    def choose_action(
        self,
        agent: Agent,
        available_actions: list[Action],
        context: DecisionContext
    ) -> Action
```

**Current implementation:** `RationalDecisionProcedure` — maximize expected utility from available actions.

**Future:** Bounded rationality, learning-based procedures, heuristic rules.

**[SETTLED]** Decision procedure is swappable. Rationality level is an experimental variable.

### 1.3 Beliefs

The belief system has three components:

| Component | Purpose | Current Status |
|-----------|---------|----------------|
| TypeBeliefs | What agent believes about others' types | Implemented; affects search |
| PriceBeliefs | Expected price/exchange rates | Implemented; not consumed |
| Memory | Record of past interactions | Implemented; feeds updates |

**[OPEN]** Beliefs currently affect search (target evaluation) but not acceptance decisions. Model C would change this — see §3.3.

---

## 2. Simulation Loop

### 2.1 Three-Phase Tick Model (ADR-001)

Each tick has three phases:

```
┌─────────────────────────────────────────────────────────────┐
│                         TICK N                               │
├─────────────┬─────────────────────┬─────────────────────────┤
│   PERCEIVE  │       DECIDE        │        EXECUTE          │
│             │                     │                         │
│ All agents  │ All agents select   │ Conflict resolution,    │
│ observe     │ ONE action from     │ state transitions,      │
│ frozen      │ available_actions() │ trades                  │
│ state       │                     │                         │
│ (snapshot)  │ Simultaneous        │ Batched                 │
└─────────────┴─────────────────────┴─────────────────────────┘
```

**Perceive:** Agents observe world state. What they see depends on `ObservationEnvironment`. All agents see the same frozen snapshot (simultaneity).

**Decide:** Each agent selects exactly one action. Actions include: Move, Propose, Accept, Reject, Wait. Selection uses `DecisionProcedure`.

**Execute:** Actions are processed. Conflicts resolved (multiple proposals to same target). State updated. Trades executed via `BargainingProtocol`.

**[SETTLED]** Three-phase model is stable.

### 2.2 Execute Sub-Phases (Proposed)

To support Model C (belief-based acceptance with revelation), Execute needs internal structure:

```
EXECUTE PHASE (expanded)
│
├─ 2.1 Collect Actions
│      Gather all submitted actions from Decide phase
│
├─ 2.2 Generate Revelation Events
│      Each action produces revelation events
│      (e.g., ProposeAction → ProposalEvent)
│
├─ 2.3 Apply Revelation Rules
│      RevelationRules interprets events → what agents learn
│      Agents update beliefs based on revealed information
│
├─ 2.4 Resolve Conflicts
│      Multiple proposals to same target → clearing rule decides
│      Target-choice: target picks best acceptable proposer
│
├─ 2.5 Evaluate Responses
│      Targets accept/reject using UPDATED beliefs (post-revelation)
│      This is the Model C behavior
│
├─ 2.6 Execute State Changes
│      Trades via BargainingProtocol
│      Movement applied
│      Cooldowns updated
│
├─ 2.7 Post-Resolution Revelation
│      Trade outcomes generate additional revelation
│      Rejections may reveal information
│
└─ 2.8 Final Belief Updates
       Agents incorporate trade/rejection outcomes into beliefs
```

**Rationale:** Steps 2.2-2.3 must precede 2.5 for Model C to work. Target's accept/reject decision uses posterior beliefs informed by proposal-time revelation.

**[PROPOSED]** Execute sub-phases are directionally accepted but not yet implemented.

### 2.3 Information Flow Through Tick

```
                    TICK N                           TICK N+1
    ┌────────────────────────────────────────┐    ┌──────────
    │                                        │    │
    │  PERCEIVE ──► DECIDE ──► EXECUTE       │    │  PERCEIVE
    │     │           │           │          │    │     │
    │     │           │           ├─reveal───┼────┼─►beliefs
    │     │           │           ├─trade────┼────┼─►holdings
    │     │           │           └─move─────┼────┼─►position
    │     │           │                      │    │
    │     ▼           ▼                      │    │
    │  [observe]   [choose]                  │    │
    │  using       using                     │    │
    │  beliefs     beliefs                   │    │
    │     ▲           ▲                      │    │
    │     │           │                      │    │
    │     └───────────┴── updated by ────────┘    │
    │                     previous tick           │
    └────────────────────────────────────────┘    └──────────
```

---

## 3. Information Architecture

### 3.1 ObservationEnvironment (Ambient Information)

**What it governs:** What agents perceive about others *without interacting* — the baseline informational structure.

```python
class ObservationEnvironment(ABC):
    def observe_type(self, observer: Agent, target: Agent) -> ObservedType:
        """What observer sees about target from a distance."""
```

**Implementations:**

| Implementation | Behavior |
|----------------|----------|
| `FullInformation` | Observer sees target's true type |
| `NoisyAlphaInformation` | Observer sees noisy preference parameter |

**When it applies:** Perceive phase. Determines priors, search targeting.

**Nature:** "Physics" — inherent observability of the world.

**[SETTLED]** ObservationEnvironment is the ambient information layer.

### 3.2 RevelationRules (Interaction-Triggered Information)

**What it governs:** What gets revealed when specific interactions occur.

**Nature:** "Institution" — rules about disclosure that could be otherwise.

**Key design choice:** Revelation is conceptually tied to actions (acting generates information), but the interpretation of what's learned is configurable via `RevelationRules`.

```python
# Actions generate revelation events
class ProposeAction(Action):
    def revelation_event(self) -> RevelationEvent:
        return ProposalEvent(proposer=self.agent, target=self.target)

# Rules interpret events into learnings
class RevelationRules(ABC):
    def on_proposal(
        self, event: ProposalEvent
    ) -> tuple[TypeSignal, TypeSignal]:
        """Returns (what_proposer_learns, what_target_learns)."""

    def on_rejection(
        self, event: RejectionEvent
    ) -> TypeSignal:
        """Returns what proposer learns from rejection."""

    def on_trade(
        self, event: TradeEvent
    ) -> tuple[TypeSignal, TypeSignal]:
        """Returns (agent1_learns, agent2_learns)."""
```

**Revelation is bidirectional and potentially asymmetric:**

| Event | Proposer learns | Target learns |
|-------|-----------------|---------------|
| Proposal | Target's endowment? Preferences? | Proposer's type? Why they proposed? |
| Rejection | Target had better option (inference) | Nothing new |
| Trade | True types, actual allocation | True types, actual allocation |

**Example implementations:**

| Rule | Behavior |
|------|----------|
| `NoRevelation` | Nothing beyond ambient observation |
| `FullRevelationOnTrade` | Learn nothing until trade; then learn everything |
| `AsymmetricProposalRevelation` | Proposer reveals type to target; target reveals only endowment |
| `EndowmentOnlyRevelation` | See holdings, not preferences |

**[SETTLED]** Revelation tied to actions conceptually; configurable rules interpret what's learned.

**[OPEN]** Specific TypeSignal structure. Granularity of revelation (full type vs components vs noisy signals).

### 3.3 Belief Model Target: Model C

Three models were considered for how beliefs interact with behavior:

| Model | Revelation timing | Acceptance basis | Bargaining basis |
|-------|-------------------|------------------|------------------|
| A | Proposal reveals true type | True surplus | True types |
| B | No revelation | Believed surplus | True types |
| **C** | **Partial revelation (signal)** | **Updated beliefs (posterior)** | **TBD** |

**Model C is the target** because it:
- Enables signaling/screening research
- Creates information-strategic considerations in matching
- Is the most realistic

**Under Model C:**
1. Agent A proposes to agent B
2. Both receive revelation signals (per RevelationRules)
3. Both update beliefs (Bayesian or heuristic)
4. B decides accept/reject using *posterior* beliefs
5. If accept, bargaining executes

**[SETTLED]** Model C is the target.

**[OPEN]** What does the bargaining oracle use under Model C?

| Option | Description | Implication |
|--------|-------------|-------------|
| **C1** | Oracle uses true types; acceptance uses beliefs | Ex-post regret possible |
| **C2** | Oracle uses beliefs | Outcomes depend on what agents think |
| **C3** | Extensive-form bargaining | Breaks oracle abstraction |

C1 is the likely choice — minimal extension that preserves the oracle while enabling belief-dependent acceptance.

### 3.4 Three Layers of Agent Knowledge

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT KNOWLEDGE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: TYPE BELIEFS                                      │
│  "What are my partners' preferences and endowments?"        │
│  [Partially implemented — affects search]                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 2: OUTCOME BELIEFS                                   │
│  "What will I get from bargaining with this partner?"       │
│  [Not implemented — enables loose coupling]                 │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 3: INSTITUTIONAL BELIEFS                             │
│  "What are the rules of this market?"                       │
│  [Future — mechanism design territory]                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Institutional Components

### 4.1 BargainingProtocol

**Status:** Complete and stable.

**Interface:**
```python
class BargainingProtocol(ABC):
    def compute_outcome(
        self, agent1: Agent, agent2: Agent
    ) -> BargainingOutcome:
        """Compute equilibrium allocation."""

    def compute_expected_surplus(
        self, agent: Agent, partner: Agent
    ) -> float:
        """Agent's expected gain from trade."""
```

**Implementations:**

| Protocol | Theory | Power Source |
|----------|--------|--------------|
| Nash | O&R Ch 2 | None (symmetric) |
| Rubinstein | BRW (1986) limit | Patience |
| Asymmetric Nash | O&R Ch 2.6 | Exogenous weights |
| TIOLI | O&R §2.8 | Commitment (proposer extracts all) |

**Abstraction:** Bargaining-as-oracle. Given types, returns equilibrium allocation in one tick. Does not model extensive-form negotiation.

**[SETTLED]** Oracle abstraction preserved for now.

### 4.2 MatchingInstitution

**Status:** Decomposition accepted; implementation pending.

**Decomposition into three components:**

```
MatchingInstitution
├── MeetingTechnology
│   "Who can possibly match this tick?"
│   Examples: adjacency, radius, random meetings
│
├── SubmissionProtocol
│   "What agents submit in Decide phase"
│   Examples: single proposal, multiple proposals, ranked list
│
└── ClearingRule
    "How matches form from submissions"
    Examples: first-processed, target-choice, maximum-weight
```

**[SETTLED]** Meeting technology treated as environmental constraint (held fixed initially). Clearing rule is the swappable institution.

**Clearing rules to implement:**

| Rule | Purpose | Description |
|------|---------|-------------|
| **Status quo (A)** | Baseline | Current first-processed priority |
| **Target-choice (B)** | Improved default | Target picks best acceptable proposer |
| **Centralized (C)** | Benchmark | Maximum-weight matching |

**[SETTLED]** Target-choice (B) as improved default. Centralized (C) acceptable as benchmark.

### 4.3 Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                    INSTITUTIONAL STACK                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ObservationEnvironment                                    │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ What agents see from a distance (ambient)           │   │
│   │ FullInformation | NoisyAlphaInformation | ...       │   │
│   └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼ informs                          │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                  PERCEIVE PHASE                     │   │
│   └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│   DecisionProcedure + Beliefs                               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Agent chooses action based on beliefs and procedure │   │
│   └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼ produces                         │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                   DECIDE PHASE                      │   │
│   │                   (actions)                         │   │
│   └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│   RevelationRules                                           │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Actions generate events → rules interpret learnings │   │
│   └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼ informs                          │
│   MatchingInstitution (ClearingRule)                        │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Resolve conflicts, determine who trades with whom   │   │
│   └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│   BargainingProtocol                                        │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Compute allocation for matched pairs                │   │
│   │ Nash | Rubinstein | Asymmetric Nash | TIOLI         │   │
│   └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                  EXECUTE PHASE                      │   │
│   │         (state changes, belief updates)             │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Coupling: Search, Matching, and Bargaining

### 5.1 The Coupling Question

How tightly should search/matching decisions be coupled to bargaining protocol?

**Current state:** Tight coupling. Agents evaluate targets using `bargaining_protocol.compute_expected_surplus()`. This means search strategy implicitly depends on which bargaining protocol is in effect.

**Issue:** This may confound comparisons. When you switch bargaining protocols, both the surplus division AND the search behavior change.

### 5.2 SurplusEstimator Interface (Proposed)

Decouple surplus estimation from bargaining execution:

```python
class SurplusEstimator(ABC):
    def estimate_surplus(
        self, agent: Agent, partner: Agent, context: Context
    ) -> float:
        """Agent's expected gain from trading with partner."""

# Implementations:
class ProtocolAwareSurplus(SurplusEstimator):
    """Tight coupling: use actual bargaining protocol."""

class TotalSurplusSplit(SurplusEstimator):
    """Loose coupling: assume 50/50 split of total surplus."""

class BeliefBasedSurplus(SurplusEstimator):
    """Use agent's beliefs, not true types."""

class LearnedSurplus(SurplusEstimator):
    """Updated from trade history."""
```

**Research value:** Coupling degree becomes an experimental variable.

**[OPEN]** SurplusEstimator interface design needs more thought.

---

## 6. Open Design Questions

### 6.1 Settled Decisions

| Decision | Choice | Reference |
|----------|--------|-----------|
| Scope direction | Expand implementation toward VISION.md | §1.1 |
| Matching decomposition | Meeting / Submission / Clearing | §2.1 |
| Meeting as constraint | Initially fixed; clearing is institution | §2.2 |
| Target-choice as default | Improved over status quo | §2.3 |
| Centralized as benchmark | Acceptable despite breaking decentralization | §2.3 |
| Coupling as variable | Not hardcoded | §2.4 |
| Model C for beliefs | Partial revelation at proposal | §3.1 |
| Bidirectional revelation | Asymmetric allowed | §3.2 |
| Oracle bargaining | Preserved for now | §4.1 |
| Revelation tied to actions | Conceptually; rules interpret | §3.2 |
| Execute sub-phases | Directionally accepted | §2.2 |

### 6.2 Open Questions

| Question | Options | Leaning |
|----------|---------|---------|
| Bargaining under Model C | C1 (oracle + true types) vs C2 vs C3 | C1 |
| TypeSignal granularity | Full type vs components vs noisy | TBD |
| SurplusEstimator interface | Design details | TBD |
| Belief update mechanics | Bayesian vs heuristic | Both supported |
| Revelation × cooldowns | Does revealed info persist? | TBD |

### 6.3 Implementation Sequencing

Both critiques (GPT, Opus) identify similar priorities but differ on order:

**GPT ordering:** P0 beliefs causal → P1 matching institution → P2 equilibrium benchmark

**Opus ordering:** Walrasian benchmark (low effort) → research notebooks → beliefs → matching

**[OPEN]** Sequencing needs decision. Key factors:
- Walrasian benchmark is low-effort, high-interpretive-value
- Beliefs causal unlocks Model C and information research
- Matching institution fills the largest gap vs VISION.md

---

## 7. Appendix: Current vs Target Architecture

### 7.1 What Exists Today

```
✓ Agent with private state, observable type, beliefs
✓ Three-phase tick model (Perceive, Decide, Execute)
✓ ObservationEnvironment (Full, NoisyAlpha)
✓ BargainingProtocol (Nash, Rubinstein, Asymmetric Nash, TIOLI)
✓ Action system (Move, Propose, Accept, Reject, Wait)
✓ DecisionProcedure interface (Rational implemented)
✓ Belief system (architecture present)
✗ Beliefs affecting acceptance (deferred)
✗ RevelationRules (not implemented)
✗ Execute sub-phases (not implemented)
✗ MatchingInstitution abstraction (ad-hoc bilateral proposal only)
✗ SurplusEstimator interface (not implemented)
✗ Walrasian equilibrium benchmark (not implemented)
```

### 7.2 Target Architecture

```
Agent Model
├── Private state (unchanged)
├── Observable type via ObservationEnvironment (unchanged)
├── Beliefs
│   ├── TypeBeliefs (activate for acceptance) ← NEW BEHAVIOR
│   ├── OutcomeBeliefs (new layer)
│   └── Memory (unchanged)
└── DecisionProcedure (unchanged interface; more implementations)

Simulation Loop
├── Perceive (unchanged)
├── Decide (unchanged)
└── Execute (expanded sub-phases) ← NEW STRUCTURE
    ├── Collect actions
    ├── Generate revelation events
    ├── Apply revelation rules → update beliefs
    ├── Resolve conflicts (ClearingRule)
    ├── Evaluate responses (using updated beliefs)
    ├── Execute state changes
    └── Final belief updates

Institutional Components
├── ObservationEnvironment (unchanged)
├── RevelationRules (new) ← NEW COMPONENT
├── MatchingInstitution ← NEW ABSTRACTION
│   ├── MeetingTechnology (environmental)
│   └── ClearingRule (institutional)
├── BargainingProtocol (unchanged)
└── SurplusEstimator (new) ← NEW COMPONENT

Analysis
└── Walrasian equilibrium benchmark ← NEW CAPABILITY
```

---

**Document Version:** 0.1 (draft)
**Sources:** design-decisions-summary.md, matching-institutions-paradigms.md, gpt-vision-critique.md, opus-vision-critique.md, VISION.md
