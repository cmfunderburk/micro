# Session Summary: Planning Discussion 2026-01-06

**Purpose:** Capture decisions, clarifications, and open items from interactive planning discussion
**Status:** Draft for review and continuation next session

---

## Context

This session reviewed `DEVELOPMENT-PLAN.md`, `WORK-ITEMS.md`, `PLANNING-REVIEW.md`, and three model proposals (`opus-review-a.md`, `gemini3pro-review-a.md`, `gpt52xhigh-review-a.md`) to resolve open questions and refine the development roadmap.

---

## Key Decisions & Clarifications

### 1. Mechanism Architecture (ARCH-001)

**Decision:** Mechanisms own their matching logic, but matching strategy is injected.

**Rationale:**
- Mechanisms should own the *call site* for matching (when and how matching is invoked)
- Matching *logic* is injected as a strategy/policy parameter
- This preserves institutional visibility (matching as independent variable) while keeping mechanisms as the owning abstraction
- Different mechanisms may need different "shapes" of matching:
  - One-to-one (bilateral bargaining)
  - Many-to-one (posted prices with multiple buyers)
  - Many-to-many (double auction)

**Implication:** The current `MatchingProtocol` abstraction evolves into a `MatchingStrategy` interface that mechanisms accept as a constructor parameter. Mechanisms define what kind of matching they need; strategies provide how.

---

### 2. Belief Architecture (Phase 1)

**Decision:** MRCC beliefs are "memory infrastructure, not inference sophistication."

**Details:**
| Aspect | MRCC Scope |
|--------|------------|
| What agents use for decisions | Current tick's noisy observation |
| Memory infrastructure | Built into foundation, stores observations |
| Memory use by agents | NOT used for decisions yet (analysis only) |
| Unknown partners | Agent's configured personal prior |
| Belief updates | No probabilistic inference in MRCC |
| Future expansion | More sophisticated belief use is upgrade path |

**Key insight:** This separates "memory infrastructure" from "inference sophistication." The memory system exists and logs observations, but agents don't aggregate or infer from history in the minimal version. This keeps Phase 1 focused on infrastructure, with belief sophistication as a clear future research variable.

**Open item:** Belief consistency/rationality as a sophistication variable needs more theoretical grounding before implementation.

---

### 3. Market Emergence Definition

**Decision:** Continuous measures across three pillars, no binary threshold.

**Details:**
- **Preferred approach:** Report price dispersion, efficiency, connectivity as continuous metrics over time
- **Avoid:** Arbitrary binary thresholds for "market emerged"
- **All three pillars equally important:**
  1. Price convergence (law of one price)
  2. Allocative efficiency (gains from trade realized)
  3. Network integration (systemic trade, not isolated pairs)

**Implication:** Analysis outputs time series and distributions. Let researchers interpret patterns. Binary classification available as optional summary statistic but not the primary output.

---

### 4. First Research Program Scope

**Decision:** Focused protocol comparison with clear factorial design.

| Dimension | Value |
|-----------|-------|
| **Bargaining protocols** | Nash, Rubinstein, TIOLI (3 levels) |
| **Information regime** | Full info (Study 1), Noisy info (Study 2) |
| **Matching** | Held constant (opportunistic) |
| **Replicates** | 5-10 seeds per cell |
| **Total runs** | ~30 per study, ~60 total |

**Research narrative:**
1. Study 1: "Do different bargaining protocols lead to different emergence patterns?" (full info)
2. Study 2: "How does information friction interact with protocol effects?" (noisy info)

**Implication:** TIOLI is required for first study (provides extreme contrast). This scopes what must be built before research begins.

---

### 5. Development Sequencing

**Decision:** Phase 0 (theoretical alignment) is **blocking** for research.

**Rationale:** Can't trust research results if foundation isn't verified. Theory verification must complete before first study runs.

**Open item:** Whether Phase 1 (beliefs) and Phase 2 (TIOLI) can proceed in parallel was not resolved in this session.

---

## Implications for Planning Documents

### Updates to DEVELOPMENT-PLAN.md

1. **Clarify MRCC scope:** Define "Minimal Research-Complete Core" explicitly:
   - Nash, Rubinstein, TIOLI protocols
   - Memory infrastructure (no inference)
   - Full info + Noisy info environments
   - Opportunistic matching only
   - Walrasian benchmark
   - Continuous emergence metrics

2. **Add hybrid philosophy statement:** "Minimal completeness for a research program, then iterate. Complete enough to cleanly compare institutions for market emergence, not complete in the abstract."

3. **Restructure Phase 1:** Focus on memory infrastructure, not inference sophistication. Rename or scope more clearly.

### Updates to WORK-ITEMS.md

1. **ARCH-001:** Add design details from this session:
   - Mechanisms own matching call site
   - MatchingStrategy injected as parameter
   - Matching shape varies by mechanism type

2. **BELIEF-001 through BELIEF-006:** Rescope to "memory infrastructure":
   - Observation storage and retrieval
   - Prior configuration per agent
   - Analysis utilities for belief/memory data
   - Defer: belief updates, inference, decision integration

3. **Add PROT-001 (TIOLI):** Elevate priority - needed for first study

4. **Add research study work items:**
   - STUDY-001: Protocol comparison (full info)
   - STUDY-002: Protocol comparison (noisy info)

### Potential New Document: ADR-001 (Mechanism Architecture)

Create Architecture Decision Record for ARCH-001 capturing:
- Problem: How to integrate multi-agent mechanisms
- Decision: Mechanism abstraction with injected matching strategy
- Consequences: Current MatchingProtocol evolves to strategy interface
- Follow-on work: Spatial venue concept (mechanisms at locations)

---

## Open Questions for Next Session

### 1. Phase Parallelization
Can Phase 1 (memory infrastructure) and Phase 2 (TIOLI) proceed in parallel, or should they be sequential?

**Arguments for parallel:**
- Memory infrastructure and TIOLI are largely independent
- Faster time to first study

**Arguments for sequential:**
- Even minimal infrastructure should stabilize before adding protocols
- Sequential is safer

### 2. Spatial Venue Concept
The proposals mention mechanisms having spatial presence (agents must travel to a "marketplace"). How important is this for the first research program?

**Considerations:**
- Current bilateral exchange is implicitly spatial (agents must be co-located)
- Double auction might be non-spatial (everyone in the "venue")
- Posted prices could be either

### 3. Mechanism Interface Details
What exactly does the `Mechanism` interface look like? Draft from proposals:
```python
class Mechanism(ABC):
    def eligible_participants(self, state) -> set[AgentId]: ...
    def collect_actions(self, agent_id) -> Action: ...
    def clear(self, actions) -> list[Transfer]: ...
```

How does this interact with:
- The existing four-phase tick loop?
- Logging and visualization?
- Agent decision models (when do agents choose mechanism vs movement)?

### 4. TIOLI Design Details
How exactly does TIOLI work in a symmetric 2-good world?
- How is proposer determined? (Random? First-arrival? Configurable?)
- What's the proposer's offer strategy? (Extract all surplus? Use beliefs?)
- How does responder decide to accept/reject?

### 5. Walrasian Benchmark Priority
Is Walrasian equilibrium computation needed before the first study, or can we start with simpler efficiency bounds?

---

## Summary Table: Proposal Convergence

| Topic | All 3 Proposals Agree | This Session Refined |
|-------|----------------------|---------------------|
| Mechanism abstraction | Yes | Matching strategy injected into mechanism |
| Defer production | Yes | Confirmed |
| Spatial indexing for performance | Yes | Not discussed in depth |
| Walrasian as primary benchmark | Yes | Confirmed (blocking unclear) |
| Sufficient-statistics beliefs | Yes | **Overridden:** MRCC is simpler (memory only, no inference) |
| Price = exchange rate | Yes | Confirmed |
| Private values first | Yes | Confirmed |
| Multi-metric emergence | Yes | **Refined:** Continuous measures, no binary threshold |

---

## Action Items for Next Session

1. **Decide:** Phase 1/2 parallelization
2. **Draft:** Mechanism interface specification
3. **Draft:** TIOLI protocol specification
4. **Clarify:** What exactly needs to be verified in Phase 0 before first study?
5. **Scope:** Is Walrasian benchmark blocking for Study 1?

---

**Session ended:** User paused for break
**Document Version:** 1.0
**Created:** 2026-01-06
