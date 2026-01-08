
Below is a concrete way to “push the roadmap discussion forward” by (1) making the implicit trade-offs explicit and (2) proposing **default resolutions** to each open question (Q2–Q12) that unblock implementation while preserving extensibility.

## 1. What the roadmap is really deciding

Your ROADMAP is weighing two expansions: **(A) protocol breadth** vs **(B) sustained economies**. 

The key constraint is the **exchange exhaustion problem**: with fixed initial endowments, the system tends toward stasis, which blocks repeat relationships, evolving networks, and long-run learning. 

So the decision is less “A or B” and more:

* How fast you want *institutional comparison* to broaden (new bargaining protocols), versus
* How fast you want *time* to matter (production/gathering/consumption loops that prevent exhaustion).

The roadmap’s phased plan reflects that tension (Phase A = protocols, Phase B = sustained economy foundation, etc.). 

## 2. A decision rule consistent with VISION.md

Two principles from VISION.md should dominate tie-breaks:

1. **Institutional visibility**: keep “the institution” as a clean experimental variable—swap rules, observe differences. 
2. **Theoretical grounding as constraint**: avoid ad-hoc mechanics that don’t map to canonical theory or published literature. 

That suggests a pragmatic approach: implement things in a way that is (a) *clearly interpretable* in theory, and (b) *modular*, so you can later add richer versions without tearing up the core.

## 3. Recommended “best next slice” (minimizes risk, maximizes leverage)

I would proceed as:

### Slice 1 (fast, contained): Phase A, but **sequence it**

* Implement **TIOLI**, **Kalai–Smorodinsky**, **Asymmetric Nash** first. 
* Defer **Nash Demand Game** until you’ve decided the exact “demand” object and disagreement handling (it has the most design ambiguity). 

Rationale: you immediately expand institutional comparison with minimal new world-state complexity.

### Slice 2 (unblocks long-run phenomena): Phase B minimal sustained loop

Implement the roadmap’s minimal sustained economy: **resource nodes + gathering + regeneration + minimal activity choice**. 
But pair it with a **simple consumption/depletion model** (otherwise you risk “eventual plenty” and re-stasis).

This pairing is the shortest path to “markets over time,” while staying theory-aligned.

## 4. Concrete resolutions for the Open Questions (Q2–Q12)

The roadmap lists Q2–Q12 as open. 
Here are default answers that are (i) implementable, (ii) interpretable, and (iii) extensible.

### Q2 — Asymmetric Nash: how determine β?

**Default now:** *agent-level bargaining power* (w_i>0) with pairwise
[
\beta_{i,j}=\frac{w_i}{w_i+w_j}.
]
Store (w_i) on the agent type; keep it configurable by scenario.

**Why this works:**

* Matches “bargaining power as a parameter” directly (clean institutional/agent heterogeneity). 
* Extends later to “derived” variants (e.g., (w_i=f(\delta_i)) or outside options) without changing the protocol.

### Q3 — Nash Demand Game: what is a “demand”?

**Default now (recommended):** *demand is a normalized utility-gain requirement*, not a bundle.

Each agent chooses (s_i\in[0,1]) interpreted as:
[
u_i \ge d_i + s_i,(u_i^{\max}-d_i),
]
where (u_i^{\max}) is “max feasible utility for i subject to the other meeting disagreement.”

**Compatibility check:** whether there exists a feasible allocation satisfying both constraints.

**Tie-break rule (when compatible):** choose the feasible allocation that minimizes squared deviation between realized normalized gains and demanded shares, i.e. closest “joint satisfaction.”

**Why this works:**

* Keeps “demand” scalar and comparable across runs (good for emergence/learning questions). 
* Avoids inventing a bundle-demand language that becomes a second bargaining protocol.

(If you prefer simpler mechanics, you can discretize the Pareto frontier into K focal points and treat the demand game as a pure coordination game; but the above is closer to the canonical “demand” idea while fitting your non-transferable utility environment.)

### Q4 — Nash Demand disagreement handling

**Default now:** **walk away (no trade)**.

**Why:** It preserves the “coordination failure” content of the game and makes failures empirically visible (trade counts, welfare paths, network fragmentation). 
Fallback-to-Nash can be a later toggle, but it blurs the institutional contrast.

---

### Q5 — Resource node placement

**Default now:** **scenario-specified fixed placement**, with optional seeded random placement as a second mode.

**Why:** fixed placement makes experiments reproducible and interpretable; random placement is useful for robustness sweeps later. 

### Q6 — Resource regeneration

**Default now:** **fixed per-tick regeneration up to a cap** (a standard renewable resource stock).

**Why:** gives you a controllable steady-state regime quickly, and “cap” prevents explosive accumulation. 

(Depletion-recovery is a straightforward later extension once you have node stocks and caps.)

---

### Q7 — Activity choice architecture

**Default now:** implement **one simple heuristic policy**, but behind an interface that later supports multiple policies.

Concretely: a minimal priority rule consistent with the roadmap’s Phase B idea—“gather if low, trade if opportunity.” 

**Why:** you need *something* to run sustained economies; full optimization is premature because it forces beliefs about yields/opportunities. 

### Q8 — Consumption modeling

**Default now:** **automatic per-tick consumption (active depletion) with a fixed consumption bundle or rate**, so holdings do not monotonically accumulate.

This aligns with the roadmap’s framing that consumption is required to break one-shot dynamics. 

**Why:** It is the minimal mechanism that ensures ongoing scarcity and thus ongoing trade opportunities. Without it, “sustained economies” can still drift back into “everyone eventually has enough.” 

### Q9 — Location implementation priority

**Default now:** **resource nodes only** (minimal sustained economy). 
Homes/markets/production sites can wait until sustained activity exists and you know what metrics you actually need.

---

### Q10 — Search with multiple protocols

Your roadmap asks whether search should use the active protocol’s predicted surplus or protocol preferences. 

**Default now:** treat protocol as an *environmental institution* and have search evaluate partners using that protocol’s surplus.

This is also consistent with the repo’s current direction: **search is already institution-aware and uses protocol-specific surplus**. 

Protocol preferences can be a later research module (“endogenous institution selection”), but it is a major step up in complexity.

### Q11 — Locations fixed vs emergent

**Default now:** **fixed** for resource nodes; consider **hybrid** later (resources fixed, markets emergent). 

### Q12 — Market location mechanics

**Default now:** **definitional** first (markets are where agents congregate, no special mechanics), then later add **mechanical** effects (reduced search cost / increased perception radius) once you want to quantify market advantages. 

## 5. What this gives you immediately (and how it fits existing capabilities)

* You already have comparison infrastructure (side-by-side, synchronized controls) to make protocol differences visible. 
* Phase A expands institutional comparison cleanly; Phase B prevents stasis and unlocks network/time dynamics. 
* The “defaults” above are implementable without committing you to one “final” theory of markets/production—everything is structured to be swapped or enriched later, consistent with the framework-level orientation in VISION. 

If you want, in the next step we can turn the above into a tight PRD-style checklist (epics → acceptance criteria → invariants/tests) that maps directly onto your existing module boundaries (bargaining/search/matching/simulation loop/logging).
