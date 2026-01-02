# Session Summary: Council Review Synthesis

**Date:** 2026-01-02
**Duration:** Interactive planning session
**Output:** `docs/PLAN_theoretical_corrections.md`

---

## Context

Reviewed three independent theoretical consistency reviews in `docs/council/`:
- Gemini: Focused on search/matching protocol blindness
- GPT-5.2 Codex: Most critical, flagged Rubinstein as fundamentally misapplied
- Opus: Most generous, found no blocking issues

## Key Decisions Made

### Theoretical Correctness

| Issue | Decision | Rationale |
|-------|----------|-----------|
| **Rubinstein formulation** | Implement asymmetric Nash (BRW 1986) | Current formula is for linear utility; Cobb-Douglas needs weighted Nash |
| **Proposer assignment** | Random | Eliminates arbitrary iteration-order bias |
| **Search surplus** | Ex-ante expected value | Agents form rational expectations about protocol outcomes |
| **Matching surplus** | Same as search | Consistency in partner ranking |
| **Distance in matching** | Apply discounting | Was unintentionally missing |

### Documentation
- Address all flagged issues (STATUS.md, test terminology, paths)
- Rename `matching.py` event types to avoid collision with `logging/events.py`

### Scope
- Theoretical fixes only (not full 0.0.1 alpha)
- Research BRW 1986 before implementing Rubinstein correction

## Key Insight: The Rubinstein Issue

GPT-5.2's critique is substantive. The standard Rubinstein share formula:
```
s₁ = (1-δ₂)/(1-δ₁δ₂)
```

...is derived for splitting a **fixed pie with linear utility**. For exchange economies with Cobb-Douglas preferences, Binmore-Rubinstein-Wolinsky (1986) showed alternating offers converges to **asymmetric Nash bargaining** with weights:
```
α₁ = ln(δ₁)/(ln(δ₁)+ln(δ₂))
```

This is actually cleaner to implement and has solid theoretical grounding.

## Next Session: Implementation Priorities

1. **Research BRW 1986** - Verify asymmetric Nash formulation, edge cases, exact derivation
2. **Implement asymmetric Nash** - Foundation for correct Rubinstein
3. **Protocol-aware search** - Wire `bargaining_protocol.compute_expected_surplus()` through
4. **Fix matching** - Add distance discounting, use protocol surplus

## Files Created/Modified

- Created: `docs/PLAN_theoretical_corrections.md` (comprehensive implementation plan)
- Created: `docs/SESSION_2026-01-02_council_review_synthesis.md` (this summary)

## Open Questions Deferred

- Bounded rationality search variants (intentional heuristic use)
- Information asymmetry (agents don't know counterparty's δ)
- Walrasian equilibrium benchmark computation

---

**To resume:** Review `docs/PLAN_theoretical_corrections.md`, then begin with BRW 1986 research.
