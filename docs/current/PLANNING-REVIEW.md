# Planning Review: Consistency & Coverage (VISION → STATUS)

**Date:** 2026-01-06  
**Purpose:** Assess how well `docs/current/DEVELOPMENT-PLAN.md` and `docs/current/WORK-ITEMS.md` cover the gap from `STATUS.md` to `VISION.md`, identify inconsistencies, and log open questions (without resolving them).

## 1. Executive Summary

The current planning docs are a strong starting point: they preserve the project’s core methodological claim (“institutional visibility”), propose a sensible phased buildout (beliefs → institutional primitives → benchmarks), and translate the biggest architectural risk into a concrete work item (ARCH-001).

The main opportunity is to make the plan *more operational* and the tracker *more complete*, by (a) tightening cross-document consistency and terminology, (b) expanding coverage of vision-critical areas that are currently implicit or missing, and (c) explicitly recording open questions/assumptions so downstream work doesn’t silently pick a path.

**Highest-impact improvements:**
- Align terminology and “what exists” claims across `VISION.md`, `STATUS.md`, `docs/current/DEVELOPMENT-PLAN.md`, `docs/current/WORK-ITEMS.md`.
- Add a small number of missing “cross-cutting” work items (performance, reproducibility/data artifacts, documentation, multi-good/production/larger market structures) so the tracker matches the vision’s scope.
- Turn each phase into a set of *verifiable deliverables* (acceptance criteria, artifacts produced, and how to validate).
- Maintain an explicit “Open Questions / Assumptions” log tied to work items (especially ARCH-001 and Phase 1 beliefs).

## 2. Document Map (Current vs Recommended)

### 2.1 Current implied hierarchy

- `VISION.md`: authoritative identity/methodology/scope
- `STATUS.md`: authoritative “what works today”
- `docs/current/DEVELOPMENT-PLAN.md`: narrative roadmap from status to framework completeness
- `docs/current/WORK-ITEMS.md`: issue-tracker breakdown of the plan

### 2.2 Recommended additions (documentation structure, not new commitments)

Consider adding one “index” document in `docs/current/` (or extending this one) to reduce drift:
- A single place that states: what each doc is for, what to update when something changes, and what “phase complete” means.

Also consider explicitly listing key supporting docs referenced by `STATUS.md`:
- `VISUALIZATION.md` (design)
- `theoretical-foundations.md` (theory mapping)
- `docs/DESIGN_dashboard_integration.md` (UI/scenario pipeline plan)
- `docs/comparative-study.md` (example analysis + performance notes)

This helps keep planning centered on `VISION.md` while acknowledging that implementation detail lives elsewhere.

## 3. Consistency Review (Across the Planning Set)

### 3.1 Minor internal inconsistencies in `STATUS.md` worth resolving

These don’t block development, but they create confusion when the plan references “current state”.

- **Information environments (what exists):** `STATUS.md`’s module table says `information.py` has “FullInformation implemented”, while later sections list **both** `FullInformation` and `NoisyAlphaInformation`. This is likely a stale table row rather than a real capability mismatch, but it reads like a contradiction.
- **“Config files (YAML/JSON) not implemented” vs YAML scenarios exist:** `STATUS.md` describes YAML scenarios and a scenario browser, but also claims config files aren’t implemented. This can be true if “config files” means “general UI-editable configs”, but as written it sounds self-contradictory.

**Recommendation:** tighten wording so each claim is unambiguous:
- If YAML scenarios exist but UI editing doesn’t, say “Scenario YAML supported; no GUI editor/general config system yet.”

### 3.2 Tension: “framework completeness before research exploitation” vs “organic module growth”

`docs/current/DEVELOPMENT-PLAN.md` advocates “framework completeness before research exploitation.” `VISION.md` also emphasizes “framework-level investment”, but pairs that with “organic module growth” and research-driven module emergence.

This isn’t a hard contradiction, but it is a strategic fork:
- A completeness-first framing implies a long “infrastructure runway” before publishable research.
- An organic-growth framing implies repeated thin slices where each new institutional primitive is immediately used to produce a comparative result (even if partial).

**Recommendation:** explicitly state a philosophy (or a hybrid) in `docs/current/DEVELOPMENT-PLAN.md`:
- e.g., “complete the minimal set of primitives needed for the first research program (market emergence), then iterate research↔framework in loops.”

### 3.3 Label semantics and statuses in `docs/current/WORK-ITEMS.md`

- **`blocked` label usage is ambiguous.** ARCH-001 is labeled `blocked` but also blocks other items. This label is usually reserved for “cannot proceed due to external dependency,” whereas ARCH-001 is an internal design task that can proceed immediately.
- **Test location conventions drift.** Phase 0 items consistently target `tests/theory/*`, while Phase 2 protocol items target `tests/test_*.py`. That may be fine, but it’s not explained, and it risks muddling “theory verification” vs “feature correctness”.

**Recommendation:** add a short “conventions” section to `docs/current/WORK-ITEMS.md`:
- What “blocked” means (and how it’s used).
- Where tests for each category live (theory vs unit vs integration vs scenario regression).

### 3.4 Dependencies: a few appear under-specified

Some work items depend on conceptual decisions not captured as explicit dependencies:
- Gale–Shapley matching implies a two-sided market (roles / sides) and a definition of “preference ordering” under uncertainty.
- Posted prices and TIOLI imply role asymmetries (buyer vs seller, proposer vs responder) and strategy assumptions (how offers/prices are chosen).

**Recommendation:** either:
- Add explicit prerequisite work items (“Define roles model”, “Define offer/pricing strategy interface”), or
- Expand item descriptions to include how those decisions will be made and tested.

## 4. Coverage / Comprehensiveness Review (Relative to `VISION.md`)

This section is about *what’s missing or implicit* in the plan/tracker compared to the vision’s scope and methodological claims.

### 4.1 Strong coverage areas (already well-represented)

- **Institutional comparison framing:** bargaining + matching are front-and-center, and the docs treat institutions as explicit swappable modules.
- **Belief architecture as foundation:** Phase 1 correctly identifies beliefs/memory as hard to retrofit later.
- **Benchmarks as comparison baselines:** Phase 3 is aligned with the vision’s “equilibrium as benchmark, not truth” framing.
- **Visualization as parallel track:** work items exist, and `STATUS.md` makes visualization a first-class output.

### 4.2 Areas that appear under-scoped or absent (add to plan/tracker, or explicitly defer)

These are not necessarily “should do next,” but they are vision-relevant enough to either plan for or explicitly declare as deferred/out-of-scope for the first research program.

#### A) Multi-good generalization (beyond 2 goods)

`STATUS.md` flags a hardcoded 2-good economy and visualization assumptions tied to that. Neither `docs/current/DEVELOPMENT-PLAN.md` nor `docs/current/WORK-ITEMS.md` explicitly plans how/when this limitation is addressed.

Why it matters:
- Many benchmarks (Walrasian equilibrium, core) and market mechanisms become more meaningful as dimensionality grows.
- Some information and signaling/screening stories are clearer with richer type spaces.

Reasonable ways to treat it in planning:
- Explicitly defer multi-good generalization until after the first market emergence research program, *or*
- Add a “Phase 2.x/Parallel” track that generalizes `Bundle`, preferences, and visualization encodings.

#### B) Production and “participation choice” (partially acknowledged, not tracked)

The architectural decision note in `docs/current/DEVELOPMENT-PLAN.md` calls out production and mechanism participation decisions as drivers of the multi-agent mechanism design. `docs/current/WORK-ITEMS.md` does not yet include any production items beyond ARCH-001’s description.

If production is in-scope per `VISION.md` (it is), the planning docs should either:
- Add an explicit production phase/track, or
- Declare production a later program (post market-emergence) and define what “production-ready architecture” means.

#### C) Agent sophistication levels (beyond “beliefs”)

`VISION.md` treats agent sophistication (rule-based vs bounded vs equilibrium vs learning) as a key experimental variable. Planning currently focuses on beliefs/memory but does not yet include explicit work items for:
- Learning (RL / evolutionary)
- Alternative decision models/policies
- A way to run the same institution under different sophistication “profiles”

Recommendation direction:
- Add a dedicated phase or parallel track: “Agent sophistication framework”, even if initially it only supports switching between a small set (e.g., myopic vs belief-based vs simple learning).

#### D) “Market structure” beyond bilateral exchange (partially acknowledged)

The plan correctly calls out that double auction and other multi-agent mechanisms require architectural work. Beyond that, `VISION.md` also motivates:
- Posted prices and centralized vs decentralized structures
- Comparisons where the “market structure” itself is the independent variable

Current plan covers some of this (posted prices, TIOLI, double auction), but does not yet describe:
- How “markets” coexist (one market vs multiple venues)
- How agents choose which mechanism/venue to participate in
- Whether these are modeled as spatially grounded institutions (marketplaces) or as overlay mechanisms

#### E) Research workflow infrastructure (experiments → artifacts → analysis → figures)

There’s good batch/logging/analysis infrastructure in `STATUS.md`, and the plan mentions factorial design. However, neither planning doc explicitly describes:
- What constitutes a reproducible research artifact set (config, seed, code version, log bundle)
- How results become figures/tables (export formats, plotting pipeline, or “analysis notebooks/scripts” conventions)

If the end state is “publication-quality,” it helps to plan for the artifact pipeline early, even if the plotting is minimal.

#### F) Documentation as a first-class workstream

The planning set implicitly relies on many documents (vision, theoretical foundations, visualization spec, scenario design). But there are no work items that ensure documentation stays coherent as features ship (e.g., “update STATUS + add scenario + add theory mapping” as part of completing a protocol).

Recommendation direction:
- Add a recurring documentation checklist per phase/item, rather than a separate “docs phase”.

## 5. Recommendations (Concrete edits to planning docs)

These are documentation/planning improvements (not implementation decisions).

### 5.1 Make “phase complete” verifiable

For each phase in `docs/current/DEVELOPMENT-PLAN.md`, add:
- **Deliverables:** code modules, tests, docs, and one representative scenario.
- **Acceptance criteria:** what to run/inspect to declare completion.
- **Non-goals:** what is explicitly *not* included in the phase.

This reduces ambiguity and prevents the plan from expanding invisibly.

### 5.2 Expand `docs/current/WORK-ITEMS.md` with a few cross-cutting items

Add work items (or a small “Backlog” section) for topics that are currently only mentioned as limitations or implied needs:
- Multi-good generalization (even if deferred)
- Production track (even if deferred)
- Agent sophistication/learning track (even if deferred)
- Performance/profiling and scaling strategy (documented, not necessarily optimized)
- Research artifact conventions (log bundles, metadata, export targets)
- Documentation maintenance conventions (what gets updated when an item lands)

The goal is completeness of the overview, not immediate commitment.

### 5.3 Tighten the “critical architecture decision point” into a decision record

ARCH-001 is correctly highlighted. To make it actionable, consider creating a short “ADR-style” decision record when it’s tackled:
- Problem statement
- Options considered
- Decision
- Consequences / follow-on work items

This prevents repeated re-litigation and clarifies what downstream work assumes.

### 5.4 Add a glossary and naming conventions

This plan uses terms like “protocol”, “mechanism”, “market structure”, “information environment”, “type”, “private state”, and “beliefs”. A short glossary in either `docs/current/DEVELOPMENT-PLAN.md` or `docs/current/WORK-ITEMS.md` would prevent subtle confusion as features expand.

## 6. Open Questions (Log Only) + Plausible Directions

This section does not resolve questions; it records them and outlines plausible paths so future work can choose intentionally.

### 6.1 ARCH-001: How should multi-agent mechanisms integrate with the simulation loop?

Why it matters:
- Determines how double auctions, centralized markets, and production will be modeled and compared.
- Affects logging/visualization, agent decision interfaces, and extensibility.

Plausible directions:
1. **Extend the existing four-phase tick loop** with additional phases (e.g., “submit orders”, “clear market”, “settle”).  
   - Pros: minimal conceptual overhead; keeps everything “per tick”.  
   - Cons: risks turning the loop into a growing switchboard; mechanisms may want different timing semantics.
2. **Introduce a `Mechanism` abstraction** that owns its own internal steps but exposes a standard interface to the simulation (e.g., `propose_actions()`, `clear()`, `apply_transfers()`).  
   - Pros: modularity; different mechanisms can have different internal logic.  
   - Cons: requires careful design of what agents observe and when.
3. **Event-driven simulation (scheduler/agenda)** where mechanisms post events and agents respond.  
   - Pros: natural for auctions, signaling, and asynchronous interactions.  
   - Cons: higher architectural complexity; harder to keep visualization intuitive.

### 6.2 Production: what is the minimal production model consistent with the vision?

Why it matters:
- Production changes the meaning of “market emergence” (agents can produce instead of trade).
- Interacts with mechanism participation decisions and potentially with spatial frictions.

Plausible directions:
1. **No production for the first research program**; defer explicitly and ensure ARCH-001 still keeps a path open.  
2. **Simple endowment transformation** (e.g., linear technology each tick) with a production decision in the agent policy.  
3. **Technology as institution** (production module is itself swappable) enabling mechanism comparisons with different production rules.

### 6.3 Roles and asymmetry: how are “buyer/seller” and “proposer/responder” modeled?

Why it matters:
- Posted prices, TIOLI, Gale–Shapley, and auctions all assume role asymmetries.
- The current exchange model is symmetric bilateral trade between two agents with endowments.

Plausible directions:
1. **Derive roles endogenously from endowments** (x-rich agents act as sellers of x, etc.).  
2. **Add explicit role/type fields** in agent observable types and scenario configs.  
3. **Make “role assignment” an institution/mechanism** (e.g., market assigns roles via entry rules).

### 6.4 Belief representation: what is the minimal belief model that still supports meaningful comparisons?

Why it matters:
- Beliefs affect search, bargaining, and the interpretation of information regimes.
- Belief complexity can dominate both runtime and design complexity.

Plausible directions:
1. **Sufficient-statistics beliefs** (e.g., mean/variance of price ratio; simple opponent-type estimator).  
2. **Bayesian update with conjugate priors** (where possible) for tractable, testable updates.  
3. **Configurable belief “plugins”**: a small interface with multiple implementations (Bayesian, heuristic, learning-based).

### 6.5 What is “price” in a 2-good bilateral barter world, and how is it logged?

Why it matters:
- Price convergence is a headline emergence metric in `VISION.md`.
- Benchmarks and comparisons need a consistent definition of transaction price (or terms-of-trade).

Plausible directions:
1. Define price as **the exchange rate** in each trade (Δy/Δx), and track a distribution over time.  
2. Define price as **shadow prices from marginal rates** (agents’ MRS) and track convergence of MRS vs trade prices.  
3. Track both and define emergence metrics using their relationship (e.g., dispersion and bias).

### 6.6 Information taxonomy: what is the minimal set of information regimes worth implementing first?

Why it matters:
- Information regimes are central to “institutional visibility”.
- Signaling/screening/common values can multiply complexity quickly.

Plausible directions:
1. Start with **private values + noisy signals** as the base; treat signaling/screening as later.  
2. Implement a **generic signal model** first (signals as messages with costs/noise), then build regimes as configurations.  
3. Implement regimes incrementally as separate classes with strong tests and explicit scope boundaries.

### 6.7 Benchmarks: which benchmarks are essential for the first research program?

Why it matters:
- `VISION.md` emphasizes equilibrium as comparison baselines.
- Some benchmarks are costly/complex (core computation, Pareto frontier distance).

Plausible directions:
1. **Walrasian equilibrium only** (baseline), plus a small set of efficiency metrics.  
2. Add **core membership** only for small-n scenarios (where computation is tractable).  
3. Define “benchmarks tiering”: small-n exact benchmarks, large-n approximate metrics.

### 6.8 Market emergence: what is the definition of “market has emerged”?

Why it matters:
- The plan proposes “market emergence” as the first major research output.
- Without an operational definition, experiments risk becoming anecdotal.

Plausible directions:
1. Define emergence via **price convergence** (dispersion ↓, stability ↑).  
2. Define emergence via **network structure** (connectivity, degree distribution, clustering stability).  
3. Define emergence via **efficiency** (welfare ratio ↑, distance to benchmark ↓).  
4. Use a composite index and report components separately.

### 6.9 Experimental design: how should the platform represent “factorial design over institutions”?

Why it matters:
- Framework completeness is in service of clean institutional comparisons.
- A factorial design needs consistent parameterization, naming, and metadata.

Plausible directions:
1. Expand existing batch runner into an explicit **experiment specification DSL** (YAML/JSON).  
2. Keep it code-driven but enforce conventions: **config object is the source of truth** and must be serializable.  
3. Implement a thin CLI wrapper that enumerates configs, runs them, and produces a standardized results directory.

### 6.10 Performance/scaling: what’s the plan for O(n²) components?

Why it matters:
- Comparative studies with 50–200 agents and many seeds can become time-expensive.
- Performance constraints affect feasible research designs.

Plausible directions:
1. Accept O(n²) for now but add **profiling + documented limits** as part of planning.  
2. Reduce comparisons via **spatial indexing / locality** (only evaluate nearby agents).  
3. Add optional **approximate search** (sampling) as an institution/agent capability.

## 7. Suggested Next Doc Updates (Small, High-Leverage)

If you want to keep changes minimal while improving coherence:
- Update `STATUS.md` to remove/clarify the two small contradictions called out in §3.1.
- Add a short conventions block to `docs/current/WORK-ITEMS.md` (labels, test locations, what “blocked” means).
- Add a short “Assumptions/Open Questions” appendix to `docs/current/DEVELOPMENT-PLAN.md` that links to ARCH-001 and Phase 1.
