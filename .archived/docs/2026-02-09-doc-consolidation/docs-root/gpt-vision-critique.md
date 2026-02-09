# GPT Vision Critique: Where the Project Stands vs `VISION.md`

**Date:** 2026-01-11  
**Vision baseline:** `VISION.md` v2.0 (updated 2026-01-11)  
**Implementation snapshot:** git `9bc4951805e069d016dcfad5e30c76872b99df3d`  
**Status baseline:** `STATUS.md` v0.4.0 (2026-01-10)

This document is a critical, implementation-grounded review of the current codebase relative to the updated `VISION.md`. It is intentionally opinionated: it highlights the most consequential mismatches, ambiguities, and leverage points for moving the project toward its stated identity.

---

## 0. Executive Summary (the short, blunt version)

### What’s already strong (and unusually so)

- **Core identity is real**: a grid-based, agent-centric simulation with first-class visualization exists (`microecon/`, `server/`, `frontend/`). The platform is not a toy; it is a working research UI.
- **Game-theoretic coordination is credible for bargaining**: multiple bilateral bargaining protocols are implemented as swappable institutions with heavy theory test coverage (`microecon/bargaining.py`, `tests/theory/`).
- **Experiment infrastructure is mature**: structured logging → replay/analysis → UI workflows exist (`microecon/logging/`, `microecon/analysis/`, replay UI).

### The biggest “vision-threatening” gaps

1. **Information regimes and beliefs are not yet behaviorally real.** The architecture exists (`microecon/information.py`, `microecon/beliefs.py`), but current action choice and bargaining execution mostly use *true* agent state rather than observable/believed types. This undermines Layer 2 claims about information structure changing equilibrium behavior.
2. **Matching/search institutions are not theory-grounded or modular in the same way as bargaining.** The project’s flagship claim is “institutions are visible and comparable”; today that is true for bargaining, but only partially true for matching/search (see `microecon/matching.py`, `microecon/actions.py`, `microecon/simulation.py`).
3. **The Kreps I / CPT layers are present as scaffolding but not yet “computational form.”** Preferences and some consumer theory are implemented (`microecon/preferences.py`), but the simulation does not yet contain explicit price systems, budgets, production/factor markets, or competitive equilibrium benchmarks.
4. **Documentation coherence is currently fragile.** The platform is ahead of some top-level docs: parts of `README.md` and some ADR status fields describe the pre–action-budget architecture. This matters because the project explicitly treats documents as “authoritative” sources.

### Highest impact next steps (if you do only 3 things)

1. **Make information and beliefs causal** in action choice and trade outcomes (not just logged/visualized).
2. **Elevate matching/meeting/search into an explicit, swappable institution layer** with at least one theory-grounded alternative to the current bilateral propose/accept mechanism.
3. **Add a competitive equilibrium benchmark (2-good exchange)** as a reference point for “applied analysis” and for measuring how institutions deviate from equilibrium predictions.

---

## 1. Restating `VISION.md` as operational requirements

`VISION.md` is intentionally high-level. To evaluate alignment rigorously, it helps to translate the vision into concrete, testable requirements.

### 1.1 “What this is”: a research framework + platform

Operationally, this means:

- There is a **simulation core** that can run repeatable experiments (seeds, configs, batch runs).
- There is a **visualization system** that makes dynamics legible (not just final outcomes).
- The system supports **instrumentation** and **analysis** suitable for research iteration (logs, replay, summary metrics).

### 1.2 Layered theoretical architecture

From `VISION.md`, the platform claims a three-layer structure:

- **Layer 1 (Decision theory):** agents have preferences + constraints + optimization (possibly bounded/learning variants).
- **Layer 2 (Game theory):** strategic interaction is governed by explicit mechanisms with known equilibrium properties (bargaining, matching, broader mechanisms).
- **Layer 3 (Applied analysis / CPT):** the platform can illuminate applied price-theoretic questions (not necessarily by “ABM realism”, but by making price-theoretic reasoning computationally explorable).

### 1.3 Spatial representation as methodology

Grid topology operationalizes:

- search costs (ticks/movement),
- information structure (radius/visibility),
- visual explanation (patterns, clustering, networks).

### 1.4 Institutional visibility as a platform-level capability

Operationally, this means:

- Institutions are **explicit modules** (not “baked into” agent code).
- They are **swappable while holding agents fixed** (same seed, same primitives, different institution).
- The system makes **comparative outcomes measurable** (logging + analysis support).

---

## 2. Where the current codebase strongly matches the vision

### 2.1 Spatial simulation + visualization is genuinely “platform-grade”

Evidence:

- Grid + movement + spatial queries: `microecon/grid.py`
- Tick-based simulation loop with explicit actions: `microecon/simulation.py`, `microecon/actions.py`
- Live backend + WebSocket updates: `server/websocket.py`, `server/simulation_manager.py`
- Frontend grid + charts + overlays + replay/comparison UI: `frontend/src/`

Assessment:

- This part already satisfies the “platform” claim: you can explore and explain runs, not just run them.
- The UI is not “nice-to-have”; it is central to the stated methodology (“institutional visibility”).

### 2.2 Bargaining protocols are modular and theoretically grounded (Layer 2 success)

Evidence:

- Protocol interface and multiple implementations: `microecon/bargaining.py`
- Theory tests: `tests/theory/test_nash_bargaining.py`, `tests/theory/test_rubinstein_bargaining.py`, `tests/theory/test_tioli_bargaining.py`, `tests/theory/test_asymmetric_nash_protocol.py`

Assessment:

- This is the clearest, strongest embodiment of “institutions are visible”: swap protocol → observe surplus division, dynamics, and emergent network effects.
- The theory tests are a major asset: they reduce the risk that “institution comparisons” are artifacts of bugs.

### 2.3 Instrumentation and analysis are unusually complete for this kind of project

Evidence:

- Structured tick logs: `microecon/logging/`
- Emergence analysis (network structure, welfare efficiency bounds): `microecon/analysis/emergence.py`
- Scenario + batch infrastructure: `microecon/scenarios/`, `microecon/batch.py`, `scenarios/`

Assessment:

- The existence of replay and analysis changes the nature of the project: it’s already research-oriented, not just simulation.
- This strongly supports the “applied orientation” later, once the economic primitives broaden.

---

## 3. Where the codebase is *misaligned* or *under-realizes* the vision

This section focuses on mismatches that change what you can legitimately claim the platform currently “is”, relative to `VISION.md`.

### 3.1 Layer 1 (Decision theory): present, but thin and partially inconsistent

What exists:

- Explicit utility representation (Cobb-Douglas) + some consumer theory tools: `microecon/preferences.py`
- Explicit action choice abstraction: `microecon/decisions.py` (`DecisionProcedure`, `RationalDecisionProcedure`)
- Action-budget constraints implemented as time/ticks (movement/proposal/etc): `microecon/actions.py`, `microecon/simulation.py`

What is missing / unclear relative to the decision-theory claim:

- **“Optimization” is currently myopic and surrogate-based.** The default decision rule maximizes expected surplus from (move/propose/wait), not a clearly stated intertemporal utility objective.
- **Constraints are primarily procedural/time-based**, not “budget sets” in the Kreps I sense (prices, incomes, feasibility constraints beyond immediate action feasibility).
- **Alternative decision models (bounded rationality, learning, prospect theory)** are architecturally referenced but not yet implemented as behaviorally distinct procedures.

Why this matters:

- The platform can already *use* decision-theoretic objects (preferences, MRS), but it does not yet *feel like* a decision-theory engine; it feels like a (well-structured) exchange-and-search engine.
- This is fine if framed honestly (“Phase A: bilateral exchange on a grid”), but it is a mismatch if the project claims “decision theory in computational form” in a broad sense today.

### 3.2 Information regimes and beliefs exist, but do not yet shape behavior (vision-critical)

What exists:

- Information environment abstraction + examples: `microecon/information.py`
- Belief objects + update rules: `microecon/beliefs.py`
- UI toggle for beliefs: `frontend/src/components/Config/ConfigModal.tsx` (`use_beliefs`)
- Trade observations feed belief updates: `microecon/simulation.py` calls `record_trade_observation(...)`

What is misaligned / incomplete:

- **Agents’ action choice and bargaining execution are not consistently conditioned on observed/believed types.**
  - Search evaluation logs include observed alpha and “used belief” flags (`microecon/search.py`, `microecon/logging/events.py`), but the *chosen actions* are currently evaluated using the true `Agent` objects in key places (e.g., `microecon/decisions.py` calling `bargaining_protocol.compute_expected_surplus(agent, target_agent)` without passing effective observed/believed types).
  - Trade execution uses true preferences/holdings via `bargaining_protocol.execute(...)` without effective types (`microecon/simulation.py`).

Why this matters:

- `VISION.md` explicitly frames information structure as a first-class institutional variable. If agents effectively “see through” noise in their decision calculus, then changing information regimes won’t generate meaningfully different behavior—undercutting a core pillar of the platform’s methodological identity.
- The “Enable Belief System” UI toggle currently risks being interpreted as “agents behave differently because they learned”; if beliefs are not causal in choice, the UI promise is overstated.

### 3.3 Matching/search as an institution is not yet at parity with bargaining (Layer 2 gap)

What exists:

- A decentralized propose/accept/reject mechanism embedded in the tick model (`microecon/actions.py`, `microecon/simulation.py`), explicitly acknowledged as ad-hoc (`microecon/matching.py`).

What is missing:

- **Theory-grounded matching mechanisms** (e.g., deferred acceptance, stable matching, search/matching models with frictions) that can be swapped in the same spirit as bargaining protocols.
- A clean abstraction boundary that answers: “what is the matching institution here?” Is it:
  - a centralized algorithm (market designer),
  - a decentralized meeting process (search),
  - an interaction protocol (proposal/acceptance timing),
  - or all of the above?

Why this matters:

- `VISION.md` frames matching as a core game-theoretic coordination mechanism alongside bargaining.
- Without explicit matching modules, “institutional visibility” is only partially achieved: bargaining is visible, but matching is not comparably parameterized, benchmarked, or theory-tested.

### 3.4 “Applied orientation” (CPT) is not yet expressed as concrete modeling capability

What exists today:

- Emergence metrics, welfare time series, trade networks, and a strong visualization layer.
- A 2-good exchange economy with rich bilateral bargaining protocols.

What is missing relative to CPT-style questions:

- **Competitive equilibrium / Walrasian benchmark** calculations integrated into analysis for comparison.
- **Prices as objects** (even if emergent) that can be compared across runs and institutions.
- **Production, factor markets, durable goods, intertemporal choice** as first-class modeled environments (beyond discounting in search/bargaining).

Why this matters:

- The platform already has the scaffolding to do CPT-style applied work (especially via logging/analysis), but the economic primitives are still too narrow to claim that CPT is “computationally instantiated” beyond bilateral exchange.

---

## 4. Cross-cutting critical issues (architecture + conceptual clarity)

These are the places where ambiguity or drift can undermine both theory-grounding and research usability.

### 4.1 Clarify what bargaining protocols *are* in the simulation

There are (at least) two valid interpretations:

1. **Equilibrium-outcome oracle (institutional solver):** given types/endowments, the “institution” returns the equilibrium allocation directly (no explicit offer/counteroffer path).
2. **Strategic process modeled over time:** agents actually play an extensive-form bargaining game, where offers, delays, and breakdown risks are explicit and cost ticks.

Current reality is closer to (1): protocols compute outcomes directly, and negotiation is not modeled as multi-tick strategic play.

This is not “wrong”, but it interacts strongly with other vision claims:

- If the platform wants to make *transaction costs* explicit (search/proposal/negotiation), then bargaining-as-oracle makes negotiation cost hard to study unless you add protocol-specific “duration” or explicit offer actions.
- If the platform wants information asymmetry to matter, bargaining-as-oracle needs a principled choice of “whose beliefs define the feasible deal set and objective,” or else it silently reverts to full-information resolution.

### 4.2 Documentation drift is now a technical risk

This repo treats documents as foundational and hierarchical (`VISION.md` → `STATUS.md` → ADRs → conventions). Several top-level docs are now inconsistent with current architecture (e.g., `README.md` still describes a 4-phase loop and legacy matching protocols).

Why this matters:

- Drift makes it harder to onboard contributors *and* harder to keep theoretical grounding honest.
- Drift also increases the chance that future changes “re-break” resolved architectural decisions because the written sources disagree.

### 4.3 Logging and configuration fidelity needs one tightening pass

The logging layer is meant to support comparative institutional analysis. That implies:

- Logs should accurately capture the institution, including proposer identity when it matters (`microecon/logging/events.py` explicitly treats `proposer_id` as “critical”).
- Config surfaces should align (core scenario config vs backend UI config vs logged config).

This is not a philosophical issue: it directly affects the validity of empirical comparisons done from logs and replays.

---

## 5. High-impact next steps (prioritized, with rationale)

This is not a full roadmap rewrite; it is a set of “highest leverage” moves to make the project *more true* to `VISION.md` with minimal wasted motion.

### P0 — Make information regimes and beliefs behaviorally causal

**Goal:** Switching information environment / beliefs meaningfully changes behavior and outcomes, not just UI overlays.

Minimum viable success criteria:

- Under `NoisyAlphaInformation`, agents’ partner targeting and proposal acceptance patterns differ from `FullInformation` in measurable ways (trade network + welfare dynamics).
- Enabling beliefs changes outcomes over time (learning curve), not just logging fields.

Likely implementation direction (conceptually):

- In Perceive: compute an explicit per-agent “observation” object (observable types + positions + visibility).
- In Decide: evaluate actions using *only* observed/believed types; remove any implicit reliance on true partner preferences.
- In Execute/Bargain: decide whether bargaining outcome uses true types (institution-as-oracle) or perceived types (strategic/incomplete-info interpretation), and make it explicit/configurable.

Why this is high-impact:

- It unlocks the entire “information asymmetry / learning” branch of the vision with a single coherent refactor.

### P1 — Promote matching/meeting/search into an explicit institutional module layer

**Goal:** Match the bargaining module maturity: multiple matching/meeting mechanisms, measurable differences, theory-grounded alternatives.

Concrete MVP options (choose one, not all):

- **Centralized matching module** (deferred acceptance / stable matching) used as an explicit institution, even if it breaks pure decentralization.
- **Decentralized meeting/search module** grounded in search theory (e.g., random meetings within radius + acceptance thresholds) with explicit frictions and equilibrium benchmarks.

Success criteria:

- Same agent primitives + same bargaining protocol + different matching/meeting rule ⇒ different efficiency / network structure in predictable directions.

Why this is high-impact:

- `VISION.md` treats matching as co-equal to bargaining as a coordination institution. Today, that’s the largest “institutional visibility” gap after information.

### P2 — Add a competitive equilibrium benchmark for the current 2-good exchange model

**Goal:** Make the “Kreps I / CPT” layer tangible without expanding primitives yet.

Concrete deliverable:

- A function that computes (or numerically solves for) a Walrasian equilibrium price ratio and implied allocations for the initial endowments/preferences of a run, and reports:
  - equilibrium welfare,
  - predicted marginal rates (MRS ≈ price ratio),
  - efficiency gap between simulated outcomes and equilibrium benchmark.

Why this is high-impact:

- It provides an external anchor: institutional comparisons become “how do different institutions deviate from competitive equilibrium (and why)?”
- It also helps prevent a subtle failure mode: mistaking “cool emergent patterns” for economically interpretable results without benchmarks.

### P3 — Clarify and/or implement negotiation time costs as an institution parameter

Two viable paths:

- **Outcome-oracle with explicit duration:** each protocol carries a negotiation cost (ticks) even if it outputs the equilibrium allocation directly.
- **Explicit extensive-form bargaining actions:** implement offer/counteroffer over multiple ticks (larger scope, but truer to O&R Ch 3–4 dynamics).

Why this is high-impact:

- Transaction costs are a stated methodological payoff of the architecture; negotiation is currently the least-visible cost component.

### P4 — Documentation + terminology consolidation (a “trust restore” sprint)

This is not glamorous but has high leverage because documents are treated as authoritative:

- Update `README.md` to reflect the 3-phase tick model, current matching mechanism, and current protocol set.
- Reconcile terminology: “endowment” vs “holdings” vs “allocation” across code, logs, docs.
- Ensure ADR statuses reflect reality (several are still marked “Proposed” even though implemented).

Why this is high-impact:

- It prevents conceptual drift from turning into architectural regressions, and it makes the project easier to extend in a theory-disciplined way.

---

## 6. Suggested sequencing (to minimize thrash)

If you want the shortest path to “more true to the vision”:

1. **P0 (information + beliefs causal)** — because it forces you to define the “agent epistemic boundary,” which everything else depends on.
2. **P4 (docs/terminology/logging alignment)** — immediately after P0 while context is fresh, to prevent re-drift.
3. **P1 (matching as institution)** — once perception/decision semantics are clean, you can compare matching rules honestly.
4. **P2 (equilibrium benchmarks)** — once the above are stable, you can interpret comparisons against equilibrium rather than just against each other.
5. **P3 (negotiation time)** — after the institution boundaries are clearer; otherwise it’s easy to implement the wrong “game”.

---

## 7. Appendix: “Evidence map” (where to look in the repo)

Core simulation and theory:

- Tick model + coordination: `microecon/simulation.py`, `microecon/actions.py`, `microecon/decisions.py`
- Bargaining mechanisms: `microecon/bargaining.py`, `tests/theory/`
- Information environments: `microecon/information.py`
- Beliefs and learning: `microecon/beliefs.py`
- Search evaluation: `microecon/search.py`

Experiment + analysis:

- Logging schema: `microecon/logging/events.py`
- Emergence analysis: `microecon/analysis/emergence.py`
- Scenario runner: `microecon/scenarios/market_emergence.py`
- YAML scenarios: `scenarios/`

Platform/UI:

- Backend simulation lifecycle: `server/simulation_manager.py`
- Frontend config and visualization: `frontend/src/`

Authoritative project docs:

- Vision: `VISION.md`
- Current state: `STATUS.md`
- Roadmap/design vs implementation comparisons: `docs/current/ROADMAP.md`, `docs/current/IMPLEMENTED-ARCHITECTURE.md`

