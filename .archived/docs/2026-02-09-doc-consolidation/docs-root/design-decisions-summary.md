# Design Decisions Summary: Vision Discussions

**Date:** 2026-01-12
**Purpose:** Source of truth for decisions made in vision/architecture discussions
**Source documents:** `gpt-vision-critique.md`, `opus-vision-critique.md`, `matching-institutions-paradigms.md`, `vision-chat.txt`, `followup-opus.txt`

---

## 1. Strategic Direction

### 1.1 Scope Decision

**Decision:** Expand implementation toward full VISION.md scope, not narrow documentation to match current implementation.

The platform aims to cover:
- Exchange and bilateral bargaining (largely complete)
- Search and matching markets (largest current gap)
- Information asymmetry, signaling, screening (partially implemented, needs behavioral activation)
- Production and factor markets (Phase B, future)

### 1.2 Priority Ordering

**Decision:** Capability expansion over demonstration. The platform is not yet rich enough to study nontrivial questions; expanding what it can study takes precedence over demonstrating value from current capabilities.

However: theory verification via tests remains critical throughout expansion.

### 1.3 Core Research Question

**Confirmed:** "What difference does the institution make?"—across bargaining, matching, and information domains (all three, not just bargaining).

---

## 2. Matching Institutions

### 2.1 Decomposition Framework

**Decision:** Decompose "matching" into three separable components:

1. **Meeting technology** — Who can possibly match this tick (adjacency, radius, random meetings, etc.)
2. **Submission protocol** — What agents do in Decide phase (single proposal, multiple proposals, ranked lists, etc.)
3. **Clearing/conflict resolution** — How matches form from submissions (first-processed, target-choice, maximum-weight, etc.)

This enables clean comparisons: hold two components fixed, vary the third.

### 2.2 Meeting Technology

**Decision:** Treat meeting technology as **environmental constraint** (held fixed) initially, with clearing rules as the swappable institution.

Rationale: The spatial grid provides a natural meeting constraint (adjacency). Varying clearing rules while holding meeting fixed gives clean comparisons. Meeting technology itself can become a second axis of comparison later.

### 2.3 Clearing Rules to Implement

**Decision:** Three clearing rules, serving different purposes:

| Rule | Purpose | Description |
|------|---------|-------------|
| **Status quo (A)** | Baseline | Current first-processed proposer priority; order-dependent |
| **Target-choice (B)** | Improved default | Target considers all proposals, picks best acceptable; removes order artifact |
| **Centralized (C)** | Benchmark | Maximum-weight matching; enables "efficiency gap from decentralization" analysis |

Target-choice (B) is the natural improvement. Status quo (A) preserved for comparison. Centralized (C) acceptable as benchmark even though it breaks pure decentralization.

### 2.4 Coupling Between Matching and Bargaining

**Decision:** The coupling is a **feature and research question**, not a confound.

- Under full rationality/full information: agents incorporate bargaining protocol into matching decisions (tight coupling)
- Under bounded rationality or incomplete information: weak link between search evaluation and actual bargaining outcomes (loose coupling)

The degree of coupling should be a variable, not hardcoded.

### 2.5 Surplus Estimation Pluggability

**Direction (needs more design work):** Keep surplus calculation in search/matching pluggable.

Current: `bargaining_protocol.compute_expected_surplus()` (tight coupling)

Should also support:
- Protocol-agnostic total surplus (loose coupling baseline)
- Belief-based expected surplus (agent's subjective estimate)
- Learned surplus estimates (updated from trade history)

Concept: `SurplusEstimator` interface that takes (agent, partner, context) and returns expected surplus. Default delegates to bargaining protocol; alternatives enable loose coupling and belief-based evaluation.

**Status:** Conceptual direction accepted; interface design needs more thought.

---

## 3. Beliefs and Information

### 3.1 Target Model

**Decision:** Model C — Partial revelation at proposal time.

Three models were considered:

| Model | Revelation | Acceptance basis | Bargaining basis |
|-------|------------|------------------|------------------|
| A | Proposal reveals true type | True surplus | True types |
| B | No revelation | Believed surplus | True types (B1) or believed (B2) |
| C | Partial revelation (signal) | Updated beliefs (posterior) | TBD |

Model C is the target because it:
- Enables signaling/screening research
- Creates information-strategic considerations in matching
- Is the most realistic

### 3.2 Revelation Mechanism Properties

**Decision:** Revelation at proposal is **bidirectional but potentially asymmetric**.

When A proposes to B:
- A learns something about B (proposer learns about target)
- B learns something about A (target learns about proposer)
- What each learns may differ in dimension, precision, or structure

This creates information-strategic considerations:
- Proposing may reveal information about you (information cost beyond tick cost)
- Receiving proposals is informative (selection effect: "why did they pick me?")
- First-mover advantage/disadvantage depends on revelation asymmetry

### 3.3 What Could Be Revealed

Design space for revelation content:

1. **Endowment only** — Observable holdings, not preferences
2. **Noisy type signal** — Like NoisyAlphaInformation but at proposal time
3. **Proposal content as signal** — Terms reveal preferences/outside options
4. **Action history** — Past trades, rejections, movement patterns
5. **Configurable structure** — Revelation mechanism as institution parameter

### 3.4 Three Layers of Agent Knowledge/Beliefs

**Direction:** Preserve design space for three layers:

1. **Type beliefs** — What agents believe about partner preferences/endowments (partially implemented)
2. **Outcome beliefs** — What agents expect from bargaining (new; enables loose coupling)
3. **Institutional beliefs** — What agents believe about the rules (further out; mechanism design territory)

### 3.5 Current Behavior (Beliefs in Search Only)

**Status:** Current behavior (beliefs affect search but not acceptance) is intentional but under active reconsideration.

Interpretation of current behavior: "optimistic search, verified execution"—agents approach based on beliefs but verify at proposal time.

Under Model C, this changes: acceptance uses posterior beliefs after proposal-time revelation, not ground truth.

---

## 4. Bargaining

### 4.1 Oracle Abstraction

**Decision:** Bargaining-as-oracle is intentional for now.

Rationale: Abstracts from temporal structure differences between protocols. Enables studying distributional and spatial impacts while keeping protocol comparisons clean.

The alternative (extensive-form bargaining over multiple ticks) may come later but requires careful design to maintain comparability despite different temporal structures.

### 4.2 Interaction with Model C (Beliefs)

**Open question:** Under Model C, what does the bargaining oracle use?

Options:
- **C1:** Oracle uses true types; agents accept based on beliefs but outcomes use ground truth (ex-post regret possible)
- **C2:** Oracle uses beliefs; outcomes depend on what agents think, not just what's true (theoretically messy)
- **C3:** Sequential revelation through bargaining; breaks oracle abstraction entirely

C1 seems like the minimal extension that preserves the oracle while enabling belief-dependent acceptance.

---

## 5. Open Questions

### 5.1 Architectural Questions

1. **Revelation mechanism placement:** Is it institution-level (like bargaining protocol), environment-level (like information environment), or a third abstraction (`RevelationMechanism`)?

   - Institution-level argument: Different markets have different disclosure rules
   - Environment-level argument: Revelation is about observability, which is the information environment's job

2. **SurplusEstimator interface:** What's the right abstraction boundary? How does it interact with beliefs?

3. **Bargaining under Model C:** C1 (oracle with true types, belief-based acceptance) vs C2 (belief-conditioned oracle) vs C3 (extensive form)?

### 5.2 Design Questions

4. **Asymmetric revelation specifics:** Along which dimensions? What proposer learns vs what target learns? Different precision? Different type components?

5. **Belief update mechanics:** How do agents form posteriors from proposal-time signals? Bayesian update? Heuristic?

6. **Acceptance criteria under Model C:** What posterior expected surplus threshold triggers acceptance?

### 5.3 Sequencing Questions

7. **Implementation order:** Matching institutions vs beliefs activation vs equilibrium benchmark? Both critiques identify all three as important; sequencing unclear.

8. **Walrasian benchmark priority:** Both critiques flag this. Relatively low effort, high value for interpreting results. Where does it fit?

---

## 6. What's Settled vs What Needs More Thought

### Settled (can proceed with implementation)

- Matching decomposition (meeting/submission/clearing)
- Meeting as constraint, clearing as institution (initially)
- Target-choice clearing as the improved default
- Centralized matching as benchmark (not default)
- Coupling as variable, not hardcoded
- Model C as target for beliefs/revelation
- Bidirectional asymmetric revelation
- Oracle bargaining preserved for now

### Needs More Thought Before Implementation

- SurplusEstimator interface design
- Revelation mechanism placement (institution vs environment vs new abstraction)
- Specific asymmetric revelation structure
- Bargaining behavior under Model C (C1 vs C2 vs C3)
- Sequencing of matching vs beliefs vs equilibrium benchmark work

---

## 7. Context for Next Session

### Where We Left Off

Discussing whether revelation mechanism should be institution-level, environment-level, or a separate abstraction. No decision reached; user needs to think more.

### Key Documents to Reference

- `VISION.md` — Authoritative on scope and methodology
- `STATUS.md` — Current implementation state
- `docs/matching-institutions-paradigms.md` — Matching decomposition and options
- `docs/gpt-vision-critique.md` — Gap analysis with P0-P4 priorities
- `docs/opus-vision-critique.md` — Gap analysis with research demonstration emphasis
- This document — Decision summary

### Suggested Next Discussion Topics

1. Resolve revelation mechanism placement question
2. Decide on bargaining behavior under Model C (likely C1)
3. Sketch SurplusEstimator interface
4. Sequence implementation work

---

**Document Version:** 1.0
**Last Updated:** 2026-01-12
