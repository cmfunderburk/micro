# Project Review: Microecon Platform

**Date:** 2026-01-10
**Reviewer:** Claude (Opus 4.5)
**Purpose:** Assess current status vs vision, identify fix-ups needed before proceeding, recommend next directions

---

## 1. Current Status vs Vision

### What's Working Well

**Core Infrastructure** (Solid alignment with VISION.md)

| Vision Goal | Status |
|-------------|--------|
| Institutional visibility (swap protocols) | **Implemented** — Four bargaining protocols (Nash, Rubinstein, Asymmetric Nash, TIOLI) |
| Make transaction costs explicit | **Implemented** — Tick model operationalizes search/proposal/negotiation costs |
| Equilibrium benchmarks | **Partial** — Bargaining solutions computed; no Walrasian/GE benchmarks |
| Information regimes | **Implemented** — FullInformation, NoisyAlphaInformation |
| Agent sophistication as variable | **Implemented** — DecisionProcedure interface, belief system |
| Canonical theoretical grounding | **Strong** — O&R references throughout, theory tests verify properties |

**The tick model is well-implemented.** The three-phase structure (Perceive → Decide → Execute) in `simulation.py` correctly handles:
- Simultaneous decision-making (no agent sees another's choice)
- Conflict resolution (mutual proposals, multiple proposers)
- Cooldown semantics (explicit rejection vs. implicit non-selection)
- Fallback execution on failed proposals

**Test coverage is excellent** — 731 tests including theory verification tests that check Nash/Rubinstein/TIOLI properties mathematically.

### Gaps vs Vision

| Vision Goal | Gap |
|-------------|-----|
| **Market emergence** as first scenario | Infrastructure exists but no dedicated emergence analysis scenario |
| **Mechanism comparison research** | Only bargaining protocols; no posted prices, double auctions |
| **Sustained economies** | No metabolism, no production/gathering — economy converges to stasis |
| **Walrasian benchmarks** | No competitive equilibrium computation for comparison |

---

## 2. Architecture Alignment Issues

### Document Redundancy

There are **three overlapping documents** describing agent architecture:
1. `AGENT-ARCHITECTURE.md` — Detailed design (v0.4)
2. `ROADMAP.md` §2 — Copy of agent architecture (claims to supersede AGENT-ARCHITECTURE.md)
3. `IMPLEMENTED-ARCHITECTURE.md` — What's actually built

**Problem:** ROADMAP.md says it supersedes AGENT-ARCHITECTURE.md, but both exist in `docs/current/` with divergent content. The acceptance rule in AGENT-ARCHITECTURE.md §7.9 describes opportunity-cost-based acceptance, while ROADMAP.md §2.13 describes simpler surplus ≥ 0 logic.

**The implementation follows AGENT-ARCHITECTURE.md** (opportunity cost comparison at `decisions.py:460`), which is correct.

### Missing Attributes in Implementation

Per AGENT-ARCHITECTURE.md §3.1, these are specified but not in `agent.py`:

| Attribute | Specification | Implementation |
|-----------|--------------|----------------|
| `Metabolism: Bundle \| None` | Per-tick consumption requirement | Not implemented |
| `StoredHoldings: Bundle \| None` | At home/bank | Not implemented |

These are explicitly flagged as "Phase B+" in the design, so this is expected — but they should be added as `None` placeholders to match the architecture.

### Naming Inconsistency

- Architecture doc §3.1 uses **ActionState**
- Implementation uses **InteractionState** (`agent.py:36`)

Both refer to the same concept. Pick one name.

---

## 3. What Needs Fixing Before Proceeding

### Priority 1: Document Consolidation

**Problem:** Three documents say different things about the agent model.

**Fix:**
1. Delete `AGENT-ARCHITECTURE.md` since ROADMAP.md claims to supersede it
2. Update ROADMAP.md §2.13 to match the implemented acceptance rule (surplus ≥ opportunity_cost)
3. Keep `IMPLEMENTED-ARCHITECTURE.md` as the "what's actually built" reference

### Priority 2: Add Placeholder Attributes

Add to `agent.py`:
```python
# Phase B+ attributes (not yet active)
metabolism: Bundle | None = field(default=None, repr=False)
stored_holdings: Bundle | None = field(default=None, repr=False)
```

This maintains architecture alignment without changing behavior.

### Priority 3: Update ROADMAP.md §2.13 Acceptance Rule

The current text describes basic acceptance (surplus ≥ 0). The implementation uses:
```
Accept iff trade_surplus >= opportunity_cost
```

This is more sophisticated and correct. Update the document.

### Priority 4: Clarify StableRoommates Status

ROADMAP.md §7.3 discusses StableRoommates deprecation, but there is no `StableRoommatesMatchingProtocol` in the codebase. Either:
- Remove this section (if it was never implemented)
- Clarify that it was a planned feature that was never built

---

## 4. Solid Next Directions

### Option A: Complete Phase A (Bilateral Protocol Expansion)
*Recommended first*

Per ROADMAP.md §3.2, two protocols remain:

| Protocol | Complexity | Research Value |
|----------|------------|----------------|
| **Kalai-Smorodinsky** | Low-Medium | Alternative fairness concept; compare to Nash |
| **Nash Demand Game** | Medium | Simultaneous demands; coordination failure possible |

**Why this first:**
- Contained scope (each protocol is ~100-200 lines)
- Directly extends existing infrastructure
- Enables immediate protocol comparison research
- Doesn't require sustained economy

**Deliverables:**
- [ ] `KalaiSmorodinskyProtocol` implementation
- [ ] `NashDemandGameProtocol` implementation
- [ ] Protocol comparison scenarios
- [ ] Theory tests verifying K-S and Nash Demand properties

### Option B: Market Emergence Scenario (Research Value)

Create a dedicated analysis pipeline for the first major research scenario:

1. **Define emergence metrics:**
   - Price convergence (how close to Walrasian?)
   - Trade network clustering
   - Welfare efficiency over time

2. **Run systematic comparisons:**
   - Same economy, different protocols
   - Vary agent count, perception radius, discount factors

3. **Add Walrasian benchmark computation:**
   - Compute competitive equilibrium prices
   - Compare simulation outcomes to benchmark

### Option C: Begin Phase B Foundation (Sustained Economies)

This unlocks the research agenda's "market emergence as ongoing phenomenon":

1. **Metabolism attribute activation** — Holdings deplete each tick
2. **Resource nodes** — Fixed locations where agents gather goods
3. **Activity choice** — Agents decide between gather/trade/move

**Why this is important:** Without metabolism, the economy converges to Pareto-optimal allocations and stops. Sustained economies enable studying:
- Repeat relationships
- Network evolution
- Long-run learning

### Option D: Web Frontend Polish

Lower research value but improves user experience:
- Agent click-to-inspect (compact popover)
- Smaller viewport handling
- MP4 export (currently only GIF)

---

## 5. Recommended Sequence

```
1. Document cleanup (Priority 1-4 above)     [1-2 hours]
2. Complete Phase A protocols                [1-2 days]
   - Kalai-Smorodinsky
   - Nash Demand Game
   - Protocol comparison scenarios
3. Market emergence analysis pipeline        [2-3 days]
   - Walrasian benchmark
   - Emergence metrics
   - Systematic comparison runs
4. Phase B foundation (when ready)           [larger effort]
```

This sequence:
- Maintains architecture integrity (cleanup first)
- Delivers immediate research value (protocol comparison)
- Builds toward the vision's first major scenario (market emergence)
- Defers larger Phase B work until foundations are solid

---

## 6. Summary

The project has strong foundations: the tick model is well-designed, bargaining protocols have proper theoretical grounding, the action/decision architecture is clean. The main issues are **documentation redundancy** and **missing Phase B attributes**.

Before adding new features, consolidate the documents so there's one authoritative source for agent architecture. Then completing Phase A (two more bargaining protocols) is the highest-value next step — it's contained, extends existing infrastructure, and enables the core research question: *"What difference does the institution make?"*

---

## Appendix: Key File References

| File | Purpose |
|------|---------|
| `microecon/agent.py` | Agent, AgentPrivateState, AgentType, AgentInteractionState |
| `microecon/actions.py` | Action ABC, MoveAction, ProposeAction, WaitAction |
| `microecon/decisions.py` | DecisionProcedure, RationalDecisionProcedure |
| `microecon/simulation.py` | Simulation engine, 3-phase tick loop |
| `microecon/bargaining.py` | Nash, Rubinstein, Asymmetric Nash, TIOLI protocols |
| `microecon/search.py` | Target evaluation, discounted surplus |
| `docs/current/ROADMAP.md` | Development phases, agent architecture spec |
| `docs/current/IMPLEMENTED-ARCHITECTURE.md` | What's actually built |
| `VISION.md` | Authoritative project identity and methodology |
| `STATUS.md` | Current capabilities and limitations |
