# Microecon Re-Orientation (Returner Guide)

**Date:** 2026-01-17

This document is for coming back to the repo after time away. It compresses the "what is this", "what works", "how does it fit together", and "what should we do next" into a single place.

If you only read three things:
- `VISION.md` (identity + methodology)
- `STATUS.md` (what is implemented today)
- `docs/current/ROADMAP.md` (intended next phases; also contains important design decisions)

---

## 0. 15-Minute Reboot

**What you are building**
- A research-first microeconomics simulation and visualization platform.
- The differentiator is **institutional visibility**: make institutions explicit (bargaining protocols, information regimes, matching/clearing rules) and compare outcomes holding everything else fixed.

**What exists and works today (v0.4.0 era)**
- A coherent Python simulation core with a 3-phase tick model (Perceive -> Decide -> Execute).
- Bilateral exchange with 4 bargaining protocols: Nash, Rubinstein (BRW limit), Asymmetric Nash, TIOLI.
- Spatial search on a toroidal grid with explicit movement costs.
- An action-based matching/coordination layer (propose/accept/reject + fallbacks + cooldowns).
- A belief system (memory + type/price beliefs) that is implemented and updated, but only partially causal.
- A full web UI (FastAPI WebSocket backend + React/Vite frontend) with comparison + replay + inspection tools.
- A large theory-oriented pytest suite.

**The biggest conceptual gap vs the vision**
- The economy is still mostly a **finite game**: agents trade toward a Pareto-efficient region and then activity slows/stops.
- To study long-run emergence (persistent networks, learning dynamics, market formation), you need a **sustained economy loop** (consumption/metabolism + replenishing acquisition via gathering/production).

**The biggest interpretability gap in the current mechanism stack**
- Matching/clearing is not yet a clean, swappable institution the way bargaining is.
- In particular, handling of **competing proposals to the same target** is order-dependent in code today (an implicit clearing rule).

---

## 1. Project Identity (Why This Exists)

This project is not "ABM economics" in the loose sense. Its identity is:

1) **Decision theory at the agent level**
- Agents have preferences and constraints and choose actions according to a specified decision procedure.
- The platform supports "rational" and "bounded" behavior as a **variable to study**, not a fixed assumption.

2) **Game theory / mechanisms at the interaction level**
- When agents interact (bargain, match, coordinate), outcomes are governed by explicit mechanisms with known properties.
- Bargaining protocols are implemented as modules to compare institutional differences.

3) **Applied orientation (Chicago Price Theory intuition)**
- The goal is a platform that can support rich applied questions while staying grounded.

Authoritative grounding is in:
- `VISION.md`
- `theoretical-foundations.md`

---

## 2. Repository Map (Where Things Live)

**Core library (Python):** `microecon/`
- Simulation engine and institutional modules.

**Web backend:** `server/`
- FastAPI app + WebSocket loop.

**Web frontend:** `frontend/`
- React/Vite UI with live simulation, comparison mode, replay, exports.

**Scenarios:** `scenarios/`
- YAML scenario definitions consumed by the scenario browser / pipeline.

**Tests:** `tests/`
- Theory tests in `tests/theory/` and broader scenario/unit tests elsewhere.

**Docs:**
- High-level: `VISION.md`, `STATUS.md`, `theoretical-foundations.md`
- Architecture/design: `docs/`, especially `docs/current/`
- ADRs: `docs/adr/`

---

## 3. Current Architecture (Mental Model)

### 3.1 Core objects

**Goods and preferences**
- Economy is 2-good.
- Bundles: `microecon/bundle.py`.
- Preferences: Cobb-Douglas only (for now): `microecon/preferences.py`.

**Agent state separation** (supports future incomplete information)
- Private state: true preferences + immutable endowment (disagreement point).
- Observable type: what others can see under an information environment.
- Mutable holdings: current inventory updated by trade.

Relevant code/docs:
- `microecon/agent.py`
- `microecon/information.py`

### 3.2 Tick model (Perceive -> Decide -> Execute)

This is the core "physics" of the simulation.

Per tick:

1) **Perceive**
- All agents observe a frozen snapshot.
- Visibility depends on perception radius + information environment.

2) **Decide**
- Each agent chooses exactly one action (rational baseline implemented).
- Actions include Move, Propose, Wait.
- The chosen action's value is stored as the agent's **opportunity cost**.

3) **Execute**
- Coordination/conflict resolution happens.
- Proposals may turn into trades.
- If a proposal fails, the proposer executes a pre-computed fallback.
- Movement happens for agents who did not trade (or who fall back to Move).

Key code/docs:
- `microecon/simulation.py`
- `microecon/actions.py`
- `microecon/decisions.py`
- `docs/adr/ADR-001-TICK-MODEL.md`

### 3.3 Matching/coordination (as implemented)

The current system is not a centralized matching algorithm. It is an action-based decentralized mechanism:

- In Decide, agents may submit `ProposeAction(target_id, fallback=...)`.
- In Execute, targets do not explicitly choose Accept/Reject as an action; instead the simulation calls `DecisionProcedure.evaluate_proposal(...)`.
- Acceptance is an **institutional constraint**: accept if the trade is at least as good as your chosen plan.

Acceptance rule (current rational baseline):
- Accept iff `surplus_from_trade >= opportunity_cost`.

This matters because it makes declining a trade rational when you are already pursuing a better alternative.

Key code/docs:
- `microecon/decisions.py` (acceptance logic)
- `microecon/actions.py` (proposal + fallback)
- `docs/current/IMPLEMENTED-ARCHITECTURE.md`

### 3.4 Bargaining-as-oracle (why negotiation is "1 tick")

Bargaining protocols are implemented as equilibrium outcome oracles:
- Given two agents' (effective) types, return an equilibrium allocation.
- The system does not currently simulate extensive-form bargaining dynamics over multiple ticks.

This is intentional (for now) to keep institutional comparisons crisp.

Key code/docs:
- `microecon/bargaining.py`
- `theoretical-foundations.md`

### 3.5 Beliefs and information (partially causal)

What exists:
- Type beliefs about other agents' preference parameters.
- Price beliefs (mean/variance).
- Memory of trades and interactions.
- Bayesian and heuristic update rules.

What is partially causal today:
- Beliefs can be used in **search evaluation** when `use_beliefs=True` (compute surplus using believed alpha).

What is not causal (yet):
- DecisionProcedure is still mostly "optimistic" and does not fully use beliefs in action choice.
- Acceptance decisions do not incorporate noisy observations / posteriors (Model C is planned).
- Price beliefs exist but are not consumed by decision logic.

Key code/docs:
- `microecon/beliefs.py`
- `microecon/search.py`
- `docs/design-decisions-summary.md` (Model C target)
- `docs/architecture-overview.md` (revelation rules direction)

---

## 4. How to Run Things (Practical Re-entry)

### 4.1 Install and sanity check

- Python deps: `uv sync`
- Tests: `uv run pytest`

### 4.2 Run the web UI (recommended)

- `./scripts/dev.sh`
- Or split terminals:
  - Server: `uv run uvicorn server.app:create_app --factory --port 8000`
  - Frontend: `cd frontend && npm run dev`

### 4.3 Run a small headless demo

See `STATUS.md` entry points. Typical patterns:
- Use `microecon.simulation.create_simple_economy(...)` for quick sanity.
- Use scenario pipeline for reproducible runs.

---

## 5. What Is Strong Right Now

- **Core simulation loop** is coherent, explicit, and testable.
- **Bargaining protocol suite** is already meaningful for institutional comparison.
- **Visualization workbench** is unusually mature for a research platform (comparison mode, replay, inspection).
- **Theory test culture** is strong (tests assert protocol properties, not just code behavior).

---

## 6. What Is Missing / Risky (Pay This Down Before Expanding Too Far)

### 6.1 Documentation drift (high cognitive cost)

There are multiple overlapping "sources of truth":
- `docs/current/ROADMAP.md` claims to unify some content.
- `docs/current/AGENT-ARCHITECTURE.md` has details that diverge from other docs.
- `docs/current/IMPLEMENTED-ARCHITECTURE.md` is the best "what the code actually does" reference.

Also, `README.md` and `VISUALIZATION-v2.md` still mention centralized matching protocols (e.g., Stable Roommates) that do not reflect the action-based model described in `STATUS.md`.

Practical consequence: future you (and collaborators) will build on the wrong mental model unless these are reconciled.

### 6.2 Matching institution not yet explicit

Matching is currently "whatever Execute does." For institutional visibility, you likely want:
- A named clearing rule (status quo vs target-choice vs centralized benchmark).
- Tests that make the clearing semantics explicit.

Related docs:
- `docs/matching-institutions-paradigms.md`
- `docs/design-decisions-summary.md`

### 6.3 Exchange is same-tick (multi-tick negotiation is deferred)

ADRs discuss multi-tick exchange sequences, but the implemented system resolves proposals in the same tick.

This is not necessarily wrong, but it should be treated as a deliberate choice:
- If you want transaction cost measurement via time-in-negotiation, multi-tick matters.
- If you want clean institutional comparisons under oracle bargaining, same-tick is simpler.

### 6.4 The economy exhausts itself (no sustained loop)

Without metabolism/consumption and replenishing acquisition, the system trends toward stasis.

This blocks:
- long-run network formation,
- persistent market activity,
- learning dynamics over meaningful horizons.

---

## 7. Logical Next Steps (Think Through / Implement)

This is intentionally structured as a set of "paths" you can pick based on what you want next: correctness/clarity, mechanism breadth, emergence research, or sustained economies.

### Path 0 (Very High Leverage): Make the mental model unambiguous

Goal: reduce cognitive load and prevent architecture drift.

Concrete tasks:
- Decide and document "authority" rules: which docs are normative vs descriptive.
- Update `README.md` to match the actions-based matching model.
- Update `VISUALIZATION-v2.md` config section (it references matching protocols that are no longer in play).
- Update `docs/current/ROADMAP.md` where it contradicts the implemented acceptance rule.

Why now:
- This work pays down the ongoing "drift tax" before you add Phase B complexity.

### Path 1: Make matching a first-class, swappable institution

Goal: institutional visibility for matching, analogous to bargaining protocols.

Minimal implementation sequence:
1) Implement **target-choice clearing** for competing proposals (target considers all proposals in a tick).
2) Keep current behavior as "status quo clearing" for comparison.
3) Optionally add "centralized max-weight matching" as a benchmark.

Why it matters:
- Removes order dependence and makes results easier to interpret.
- Unlocks clean experiments: same agents + same bargaining + same meeting tech, different clearing rule.

### Path 2: Finish Phase A bargaining breadth

Goal: complete the bilateral protocol suite for controlled comparisons.

From `docs/current/ROADMAP.md`:
- Kalai-Smorodinsky bargaining solution.
- Nash Demand Game (simultaneous demands; introduces coordination failure).

Why it is attractive:
- Contained implementation scope.
- Directly advances the "institution matters" narrative.
- Extends theory test suite naturally.

### Path 3: Implement a transaction cost wedge (practical + interpretability)

Goal: prevent micro-trades with vanishing surplus and align outcomes with transaction cost economics.

Design exists:
- `docs/current/transaction-costs-design.md`

This can be a small, high-impact addition:
- A fixed minimum surplus threshold (epsilon).
- Applied in search evaluation and/or trade execution.

### Path 4: Add equilibrium benchmarks (interpretation and calibration)

Goal: strengthen "equilibrium as baseline" alignment.

Near-term approach:
- For 2-good Cobb-Douglas, compute competitive/Walrasian benchmark allocations/prices for the initial endowment distribution.
- Add analysis utilities to report "distance to benchmark".

Why:
- Makes it easier to interpret institutional differences: faster/slower convergence, higher/lower efficiency, distributional effects.

### Path 5: Phase B sustained economy MVP (biggest research unlock)

Goal: stop the economy from exhausting itself.

MVP ingredients (from ROADMAP):
- Metabolism / consumption (holdings deplete per tick).
- Resource nodes + gathering action.
- Simple activity choice heuristic (swappable later).

Why:
- Enables persistent trade, repeated relationships, evolving networks, and meaningful learning dynamics.

### Path 6: Make beliefs causal (Model C) for information economics

Goal: move from "beliefs updated" to "beliefs drive behavior".

Key ideas from the design docs:
- Proposal-time **revelation rules** (bidirectional, potentially asymmetric).
- Acceptance based on posterior beliefs.
- Keep bargaining oracle on true types (C1) as minimal extension.

This is the route toward signaling/screening/matching under incomplete information.

---

## 8. Recommended Near-Term Ordering (If You Want One)

If the goal is to reduce cognitive load and move the research frontier forward with minimal risk:

1) Path 0: doc/authority cleanup + bring README/UI docs in line with reality
2) Path 1: explicit matching clearing rule (target-choice) + tests (removes hidden ordering artifacts)
3) Path 2: implement remaining bargaining protocols (K-S, Nash Demand) + theory tests
4) Path 4: add a Walrasian benchmark computation (interpretability win)
5) Path 5: Phase B sustained economy MVP (bigger lift, but largest unlock)
6) Path 6: beliefs causal (Model C) when ready to do information research

---

## 9. Quick Reference: Important Files

**Identity / status**
- `VISION.md`
- `STATUS.md`
- `theoretical-foundations.md`

**Architecture / decisions**
- `docs/current/ROADMAP.md`
- `docs/current/IMPLEMENTED-ARCHITECTURE.md`
- `docs/current/AGENT-ARCHITECTURE.md`
- `docs/architecture-overview.md`
- `docs/design-decisions-summary.md`

**Core code**
- `microecon/simulation.py`
- `microecon/agent.py`
- `microecon/actions.py`
- `microecon/decisions.py`
- `microecon/bargaining.py`
- `microecon/search.py`

**Web stack**
- `server/app.py`
- `server/websocket.py`
- `frontend/src/App.tsx`

---

## 10. Open Questions to Keep in View

These are recurring design choices that will shape the next phase:

- Should "meeting technology" be treated as an environmental constraint (held fixed) while varying clearing rules first?
- Do we want to keep same-tick proposal resolution, or intentionally reintroduce multi-tick negotiation to measure bargaining time costs?
- When beliefs become causal, does the bargaining oracle use true types (C1) or beliefs (C2)?
- Do we want to decouple search evaluation from the active bargaining protocol via a `SurplusEstimator` (coupling as a variable)?
- What is the next "flagship" research scenario: protocol comparison, matching institution comparison, sustained market emergence, or information asymmetry dynamics?
