# Proposal A (GPT-5.2): Resolve Open Planning Questions

**Date:** 2026-01-06  
**Inputs reviewed:** `VISION.md`, `STATUS.md`, `docs/current/DEVELOPMENT-PLAN.md`, `docs/current/WORK-ITEMS.md`, `docs/current/PLANNING-REVIEW.md`  
**Purpose:** Provide concrete, justified decisions for the open questions currently logged (especially `docs/current/PLANNING-REVIEW.md` §6), in a way that is consistent with the project’s methodological identity (“institutional visibility”) and the current architecture.

---

## 0. Executive Summary (Decisions at a Glance)

This proposal resolves each logged open question by choosing a default path that is (a) minimally sufficient for the first research program (“market emergence”), (b) consistent with the vision’s emphasis on explicit institutions and comparability, and (c) architecturally extensible without prematurely building an event-driven “everything engine”.

**Core decisions:**
- **Mechanisms architecture:** Keep a tick-based simulation (for visualization clarity), but introduce a **first-class `Mechanism`/`Venue` abstraction** so multi-agent markets (double auction, posted-price market) and future production can integrate without bloating the tick loop into a switchboard.
- **Production:** **Defer production** for the first market-emergence research program, but require ARCH-001 to define a **production hook** (a per-tick “resource update” step) so production can be introduced later as a swappable institution.
- **Roles/asymmetry:** Treat **buyer/seller** as **market-side roles within a mechanism/venue**, not as a global fixed agent identity; treat **proposer/responder** as an **interaction role** chosen by an explicit, configurable rule.
- **Beliefs:** Implement a **minimal, testable belief core** using **sufficient-statistics** (and conjugate updates where applicable), with a plugin interface to support multiple sophistication levels (myopic → belief-based → learning).
- **Price:** Define “price” in 2-good barter as **transaction terms-of-trade** (Δquote/Δbase) and track both **transaction prices** and **shadow prices (MRS)**; compute convergence metrics from logs (no new logging fields required).
- **Information taxonomy:** For the first program, implement **Private Values with noisy signals** as the primary “incomplete information” regime; explicitly defer signaling/screening/common-values until after beliefs + mechanism actions exist.
- **Benchmarks:** Make **Walrasian equilibrium** (for 2-good Cobb–Douglas pure exchange) the essential benchmark; treat core membership / Pareto frontier distance as **small-n optional tiers**.
- **Market emergence definition:** Use a **multi-metric operational definition** (price coherence + participation/network structure + efficiency), reported as components and (optionally) a composite index.
- **Factorial design:** Adopt a **serializable Experiment Spec** (YAML/JSON) as the canonical representation of “factorial design over institutions”, executed by the batch runner and producing a standardized artifact directory.
- **Performance:** Optimize only where it preserves conceptual clarity: add profiling + documented limits now; upgrade spatial queries to avoid global O(n) scans; treat approximate search/sampling as an optional “bounded rationality / computational constraint” institutional option.

---

## 1. Guiding Principles (Derived from `VISION.md`)

1. **Institutional visibility is the independent-variable contract.** If an assumption affects outcomes (timing, information revelation, participation rules), it should be explicit and swappable rather than buried in “the simulation”.
2. **Visualization is a first-class constraint.** Architectures that obscure the “story per tick” (e.g., fully asynchronous event-driven systems) should be avoided until their marginal value is clearly higher than the cognitive cost.
3. **Theory as constraint, not decoration.** When we pick a behavioral rule or benchmark, it should map to a canonical theory object (Nash/Rubinstein/competitive equilibrium; Bayesian or explicitly heuristic learning).
4. **Minimal completeness for a research program beats abstract completeness.** The goal is not “implement all of MWG”; it’s “build enough primitives to cleanly compare institutions for market emergence, then iterate.”
5. **Reproducibility is part of the product.** A run is not “real” unless it can be reproduced with recorded config + seed + code version, and produces analyzable artifacts.

---

## 2. Strategic Clarification: “Framework Completeness” vs “Organic Growth”

`docs/current/DEVELOPMENT-PLAN.md` says “framework completeness before research exploitation,” while `VISION.md` emphasizes framework investment but also “organic module growth.”

**Decision:** adopt a **hybrid stance**:
- Define a **Minimal Research-Complete Core (MRCC)** for the first research program (market emergence), and treat “completeness” as “complete for MRCC,” not “complete in the abstract.”
- Build MRCC with framework-quality architecture (clean abstractions, strong tests, logging), but require **each phase to produce a usable comparative result**, even if limited.

**Justification:**
- This preserves the vision’s “framework-level investment” (architecture matters) while preventing an unbounded infrastructure runway that delays learning and publication.
- The platform’s methodological claim (“institutions visible”) is best demonstrated through repeated thin-slice comparisons, not by waiting for an end-state.

**Implication for docs:** Update `docs/current/DEVELOPMENT-PLAN.md` to explicitly define MRCC (for market emergence) and rephrase “framework completeness” accordingly.

---

## 3. Resolutions to Logged Open Questions (`docs/current/PLANNING-REVIEW.md` §6)

### 3.1 (6.1) ARCH-001: How should multi-agent mechanisms integrate with the simulation loop?

#### Decision
Introduce a **first-class `Mechanism` abstraction** with an optional **`Venue`/participation constraint**, while keeping the **top-level simulation tick** (for visualization coherence).

Concretely:
- Keep a fixed, readable tick structure (still “per tick”).
- Add a **Mechanism layer** that can run **bilateral** or **multi-agent** interactions without requiring new hardcoded phases per mechanism.
- Allow **multiple mechanisms** to coexist (e.g., decentralized barter + centralized market venue), enabling “market structure as independent variable.”

#### Rationale
- Extending the four-phase loop with per-mechanism phases will eventually create a growing switchboard (“submit orders”, “clear market”, “settle”, “produce”, …), which undermines modularity and institutional visibility.
- A fully event-driven scheduler increases architectural complexity and makes visualization/interpretability harder, especially for early research outputs.
- A mechanism interface keeps institutions explicit, swappable, and comparable, while preserving the “story per tick” in the UI.

#### Design sketch (conceptual, not code-committing)
Model “interaction” as a mechanism that:
- (a) defines who can participate (optionally spatial),
- (b) collects actions from participating agents,
- (c) clears/allocates/transfers,
- (d) emits events for logging/visualization.

Minimal interface concept:
- `eligible_participants(sim_state) -> set[AgentId]` (often location-constrained)
- `collect_actions(sim_state, agent_id) -> Action` (can be no-op)
- `clear(sim_state, actions) -> list[Transfer] + list[Event]`
- `apply(sim_state, transfers)` (updates endowments / commitments / inventories)

**Venue concept (optional but recommended):**
- A mechanism can specify **spatial participation**: e.g., “only agents at (r,c) can submit orders to this double auction,” which preserves the grid’s meaning and creates interpretable comparisons (decentralized search vs centralized venue with travel costs).

#### Implications for current architecture
- The existing bilateral exchange can be treated as a mechanism (“LocalBilateralTradeMechanism”) that:
  - identifies co-located pairs (or commitment-gated pairs),
  - runs `BargainingProtocol` to compute allocations,
  - records a trade event.
- Matching protocols remain meaningful as **institutions governing partner formation**; they can either remain as a separate module or be wrapped as a mechanism that outputs commitments.
- Logging should remain **mechanism-agnostic**: mechanisms emit events into the existing logger (with event-type extensions if needed).

#### Acceptance criteria (for the ARCH-001 decision)
To consider ARCH-001 “resolved,” the decision record should specify:
1. The tick structure and which parts are fixed vs pluggable.
2. The `Mechanism` interface and how it interacts with agent decisions.
3. How spatial venues work (even if only one default venue is implemented later).
4. How mechanisms emit log events in a standardized way.
5. A minimal end-to-end example: a stub multi-agent mechanism that runs without special-casing the tick loop.

---

### 3.2 (6.2) Production: what is the minimal production model consistent with the vision?

#### Decision
For the **first market-emergence research program**, **exclude production** (pure exchange only), but define production as a **swappable institution** with a minimal hook in the architecture:
- `ProductionModule` (or “resource update”) runs at a fixed point each tick (e.g., pre-interaction), and may be `NoProduction` by default.

When production is introduced later, start with the minimal model:
1. **Endowment flow** (exogenous): each tick, agents receive a small inflow of one or both goods (possibly heterogeneous).
2. **Linear transformation technology** (choice-based): agents can convert one good into the other at a fixed rate with optional convex cost.

#### Rationale
- Production fundamentally changes what “market emergence” means (agents can satisfy needs by producing rather than trading), which complicates the first demonstration.
- Pure exchange is the cleanest setting for:
  - defining transaction prices (terms-of-trade),
  - computing Walrasian benchmarks,
  - interpreting welfare/efficiency metrics.
- Defining a production hook now prevents later retrofits that would contaminate institutional comparisons (“production is hardcoded into the simulation”).

#### Consequences / follow-on planning
- Add an explicit statement in `docs/current/DEVELOPMENT-PLAN.md` that production is deferred for MRCC, but the architecture must remain production-ready.
- Add work items for a “Production Track” in `docs/current/WORK-ITEMS.md` (even if labeled “deferred”), so the vision’s scope remains visible rather than implicit.

---

### 3.3 (6.3) Roles and asymmetry: how are buyer/seller and proposer/responder modeled?

#### Decision
Separate **roles** into two distinct concepts:

1. **Interaction role (proposer/responder)**: determined **per encounter** by a configurable **proposer-selection rule**, logged explicitly.
2. **Market side (buyer/seller)**: determined **within a specific mechanism/venue**, not as a permanent global agent identity.

Defaults:
- **Proposer selection rule:** deterministic and configurable; default = `initiator` if meaningful, else `random(seed)` (reproducible) or `lexicographic(agent_id)` (fully deterministic).
- **Buyer/seller assignment for two-sided mechanisms:** default = **endowment-based initial assignment** for the chosen base/quote good (e.g., x-rich are sellers of x), with the option to evolve later to endogenous side choice.

#### Rationale
- Mixing proposer/responder with buyer/seller creates conceptual confusion: a proposer in Rubinstein is a bargaining-timing role; a buyer/seller is a market-side role.
- Keeping buyer/seller within the mechanism makes “role assignment” itself a visible institutional choice, consistent with the platform’s central claim.
- Deterministic proposer assignment is necessary for clean comparisons (Rubinstein’s first-mover advantage is sensitive to proposer identity).

#### Minimal definition needed for posted prices / auctions
To define posted prices or a double auction in a 2-good world, the mechanism must choose:
- A **base good** (the traded good) and a **quote good** (the numeraire used to quote prices).
- This choice is part of the institution and should be explicit in configs and logs.

---

### 3.4 (6.4) Belief representation: what is the minimal belief model that still supports meaningful comparisons?

#### Decision
Implement a **belief core** that is:
- **Minimal** (sufficient statistics, bounded memory),
- **Testable** (deterministic updates given observations),
- **Configurable** (plug-in belief models), enabling agent sophistication as an experimental variable.

Minimum set of beliefs for MRCC:
1. **Price beliefs** over the base/quote terms-of-trade (mean + dispersion; optionally robust EMA).
2. **Partner beliefs** over opponent attributes that are noisy under information regimes (initially: alpha), updated with a conjugate or near-conjugate rule.

Beliefs affect:
- **Search** (expected surplus uses believed type / expected price, not raw noisy observation).
- **Trade acceptance** (risk-adjusted expected gain over disagreement point).

#### Rationale
- Without beliefs, information regimes beyond full info become superficial: “noise” is just random perturbation with no learning dynamics.
- Full Bayesian state over types + strategies is overkill and will dominate both code and runtime.
- Sufficient-statistics beliefs (with optional conjugate updates) are:
  - theoretically interpretable (beliefs as distributions),
  - computationally light,
  - easy to test.

#### Concrete belief choices (recommended defaults)
**Alpha belief (partner type):**
- Prior: truncated Normal on (0,1) with configurable mean/variance.
- Observation model: `observed_alpha = alpha + ε`, ε ~ Normal(0, σ²) (as in `NoisyAlphaInformation`).
- Update: Normal–Normal conjugate update, then truncate/clamp to (0,1).

**Price belief (transaction price):**
- Track transaction prices `p_t` from observed trades.
- Maintain mean/variance with either:
  - conjugate Normal updates (if assuming known observation variance), or
  - robust EMA + running MAD/IQR (less assumption-heavy).

#### Memory management
- Store **sufficient statistics** as the default, not full histories.
- Permit bounded “last N observations” buffers only when needed for visualization/analysis (and make N configurable).

---

### 3.5 (6.5) What is “price” in a 2-good bilateral barter world, and how is it logged?

#### Decision
Define and measure price using **two complementary objects**:

1. **Transaction price (terms-of-trade)** for a chosen base good `x` in units of quote good `y`:
   - For a trade, compute goods transferred from pre- to post-allocation.
   - If an agent receives Δx > 0 and gives up Δy < 0, then the transaction price of x is:
     - `p_x = (-Δy) / Δx`
2. **Shadow price (agent-level MRS)** implied by Cobb–Douglas at the agent’s current bundle:
   - `MRS = MU_x / MU_y = (α/(1-α)) * (y/x)`

Logging approach:
- Do **not** add new mandatory log fields initially; compute transaction prices from existing `TradeEvent` pre/post allocations.
- Add analysis utilities that produce:
  - per-tick price distribution (median/mean, IQR/MAD),
  - time-series convergence metrics,
  - comparison of transaction prices vs MRS distribution and (when available) Walrasian p*.

#### Rationale
- In barter, “price” is inherently an exchange rate. Terms-of-trade is the correct primitive.
- Shadow prices (MRS) provide a theoretically grounded comparator and help distinguish “price dispersion due to heterogeneity” from “institution-induced price incoherence.”
- Computing from logs avoids binding the architecture to a particular “price field” too early.

---

### 3.6 (6.6) Information taxonomy: what is the minimal set of information regimes worth implementing first?

#### Decision
For MRCC, implement information regimes in this order:

1. **Full information** (already).
2. **Private values + noisy signals** (primary incomplete-information regime):
   - Start with noisy preference parameter signals (generalizing `NoisyAlphaInformation` into a “noisy signal” concept).
   - Require beliefs to accumulate information over time (Phase 1).

Explicitly defer for later (post-MRCC, once beliefs + mechanism actions exist):
- **Signaling** (costly messages/actions)
- **Screening** (menus / mechanism design)
- **Common values** (primarily relevant once auctions are present)

#### Rationale
- Private values with noisy signals is the minimal nontrivial step that:
  - forces belief dynamics,
  - affects search/matching/bargaining,
  - stays interpretable and testable.
- Signaling/screening require a richer action space and belief updating over strategic messages, which should not be bolted onto a myopic agent model.

---

### 3.7 (6.7) Benchmarks: which benchmarks are essential for the first research program?

#### Decision
Adopt a **tiered benchmark strategy**:

**Tier 1 (required for MRCC): Walrasian equilibrium for 2-good Cobb–Douglas pure exchange**
- Compute equilibrium price ratio `p*` and competitive allocations from initial endowments and preference parameters.
- Provide “distance to Walrasian” metrics:
  - transaction price median vs `p*`,
  - welfare vs Walrasian welfare,
  - allocation distance (optional).

**Tier 0 (always available, already partly implemented):**
- Welfare time series, total gains, trade network stats.
- “Theoretical max gains” bounds (e.g., greedy matching bound already in `analysis/emergence.py`).

**Tier 2 (optional, small-n only):**
- Core membership checks and/or Pareto frontier distance for n small enough to be tractable.

#### Rationale
- The vision explicitly frames equilibrium as a baseline comparator; Walrasian equilibrium is the most central baseline for exchange economies.
- For the sizes relevant to “market emergence” (50–200 agents), core computation is not a practical default benchmark.
- Tiering preserves rigor without forcing the research program into only tiny toy economies.

---

### 3.8 (6.8) Market emergence: what is the definition of “market has emerged”?

#### Decision
Define market emergence as a **multi-dimensional operational construct** rather than a single anecdotal judgment.

For each run, report **component metrics** and (optionally) a composite score:
1. **Price coherence and stability**
   - dispersion of transaction prices over time (IQR/MAD),
   - volatility of median transaction price (rolling window),
   - distance of median price to Walrasian `p*` (when available).
2. **Participation and connectivity**
   - fraction of agents trading (isolates ↓),
   - trade network density / giant component size / degree distribution stability.
3. **Efficiency**
   - welfare efficiency ratio vs Tier 0 bound and/or Walrasian welfare,
   - time-to-threshold (e.g., reach 80% of benchmark welfare).
4. **Spatial organization (optional but aligned with current analysis)**
   - trading cluster existence, persistence, and agent convergence to hotspots.

Optional binary classification (if needed for summaries):
- “Market emerged” if, over the final window of ticks:
  - transaction price dispersion is below a configurable threshold,
  - participation exceeds a threshold (few isolates),
  - efficiency exceeds a threshold.

#### Rationale
- The vision’s “market emergence” is not a single phenomenon; institutions can affect prices, networks, and welfare differently.
- Reporting components avoids hiding mechanisms (“it converged” vs “it converged in prices but not in network connectivity”).
- A composite score can be useful, but only if components remain visible to prevent overfitting to a single index.

---

### 3.9 (6.9) Experimental design: how should the platform represent factorial design over institutions?

#### Decision
Make a **serializable Experiment Spec** the canonical representation of factorial institutional comparisons, executed by batch tooling and producing standardized artifacts.

Recommended structure:
- **Experiment metadata:** title, description, tags, version.
- **Scenario:** either a scenario YAML reference or a generator config (e.g., MarketEmergenceConfig-like parameters).
- **Factors:** protocols, matching mechanisms, info regimes, belief model, etc.
- **Replication:** explicit seeds (required) + number of replications per cell.
- **Outputs:** results directory naming scheme + stored run manifests.
- **Analysis recipe:** which metrics/reports to compute.

#### Rationale
- Institutional comparison is the research method; the experiment definition should be first-class and reproducible.
- A spec file makes it easy to compare proposals, rerun experiments, and attach results to papers.
- The existing `BatchRunner` already embodies the “cartesian product of variations” idea; the spec should compile down to that engine.

---

### 3.10 (6.10) Performance/scaling: what’s the plan for O(n²) components?

#### Decision
Adopt a staged performance plan that keeps performance work “research-enabling” rather than speculative:

1. **Measure first (immediate):**
   - Add phase-level timing/profiling for typical MRCC runs (e.g., 100 agents × 200 ticks).
   - Document performance envelopes and recommended parameter ranges (update `STATUS.md` and planning docs).
2. **Fix the biggest structural hotspot (early):**
   - Replace global scans in spatial queries (e.g., `agents_within_radius`) with occupancy-based neighborhood iteration so perception checks are O(r² + local agents), not O(n).
3. **Treat approximation as an institution (later):**
   - If needed for larger n, implement “sampled search” / “approximate partner evaluation” as an agent capability or institutional rule (bounded rationality), making the computational constraint itself visible and comparable.

#### Rationale
- For research iteration, speed matters, but premature micro-optimization risks adding complexity that obscures institutional comparisons.
- The grid already maintains occupancy; leveraging it is low-risk and keeps the conceptual model intact.
- Turning approximation into an explicit option aligns with the vision: “agent sophistication as experimental variable.”

---

## 4. Concrete Documentation Updates Implied by These Decisions

This proposal is not a patch, but it implies a small set of high-leverage doc edits:

1. Add an **“Assumptions / Decisions” appendix** to `docs/current/DEVELOPMENT-PLAN.md` summarizing the defaults chosen here (and linking to an ADR for ARCH-001).
2. Update `docs/current/WORK-ITEMS.md` with:
   - conventions for labels (`blocked`) and test locations,
   - explicit deferred tracks (production, multi-good generalization, learning/sophistication),
   - a work item for “Experiment Spec + artifact directory standard”.
3. Add an ADR-style document for ARCH-001 once the architecture session is actually performed (this proposal can serve as the starting option set).

---

## 5. Risks, Tradeoffs, and Why This Proposal Still Fits the Vision

- **Risk:** Mechanism abstraction is “too much abstraction too early.”  
  **Mitigation:** Keep the interface minimal and prove it with one stub multi-agent mechanism before refactoring everything.

- **Risk:** Deferring production under-delivers on the full microeconomics scope.  
  **Mitigation:** Make the deferral explicit and ensure the architecture includes a production hook; add a tracked production roadmap item.

- **Risk:** Price convergence metrics could dominate the definition of emergence.  
  **Mitigation:** Use multi-metric reporting and avoid a single magic threshold as the core claim.

- **Risk:** Experiment specs become a parallel configuration system.  
  **Mitigation:** Declare one source of truth: the spec compiles to fully serializable run configs and is stored with results; code-driven configs remain possible but must serialize equivalently.

---

## 6. Summary of What to Decide Next (If You Want a Tight Next Session)

If the next session is a dedicated “decision session,” the highest leverage is:
1. **Finalize ARCH-001** in ADR form: mechanism interface + venue model + event/logging schema.
2. **Lock MRCC scope**: what must exist to run a clean first market-emergence factorial experiment with at least 2–3 institutions per axis.
3. **Choose benchmark tier defaults**: implement Walrasian equilibrium first and define exactly which emergence metrics are “primary”.

