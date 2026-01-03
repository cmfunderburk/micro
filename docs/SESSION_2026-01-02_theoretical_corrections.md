# Session Review: Theoretical Corrections Implementation

**Date:** 2026-01-02
**Branch:** `tweaking`
**Commits:** 4 (524ede3 → 8da855b)

---

## Summary

Implemented the theoretical corrections identified by the council review (Gemini, GPT-5.2, Opus). The most significant fix was replacing the incorrect Rubinstein bargaining formula with the theoretically correct Binmore-Rubinstein-Wolinsky (1986) asymmetric Nash formulation.

---

## What Was Done

### Phase 1: Core Rubinstein Fix

**Problem:** The original Rubinstein implementation used the share formula `s₁ = (1-δ₂)/(1-δ₁δ₂)`, which is derived for splitting a **fixed pie with linear utility**. This is incorrect for exchange economies with Cobb-Douglas preferences.

**Solution:** Per BRW (1986) and O&R-B Chapter 4, for general preferences the Rubinstein alternating-offers SPE converges to the **asymmetric Nash bargaining solution** with patience-derived weights:

```
w₁ = ln(δ₂) / (ln(δ₁) + ln(δ₂))
w₂ = ln(δ₁) / (ln(δ₁) + ln(δ₂))
```

Note the counterintuitive formula: w₁ uses δ₂ in the numerator. The MORE patient player gets GREATER bargaining power.

**Implementation:**
- Added `asymmetric_nash_bargaining_solution()` - maximizes `(u₁-d₁)^w₁ × (u₂-d₂)^w₂`
- Added `compute_brw_weights()` - computes weights from discount factors
- Refactored `rubinstein_bargaining_solution()` to simply compute BRW weights and call asymmetric Nash
- **Key behavioral change:** Proposer identity no longer affects outcomes

### Phase 2: Protocol-Aware Search & Matching

**Problem:** Search and matching hardcoded `compute_nash_surplus()` regardless of the active bargaining protocol, undermining "institutional visibility."

**Solution:**
- `evaluate_targets()` now accepts optional `bargaining_protocol` parameter
- When provided, uses `protocol.compute_expected_surplus()` instead of Nash surplus
- Matching's `surplus_fn` now uses protocol AND applies distance discounting

**Distance discounting in matching** (was missing):
```python
def surplus_fn(a: Agent, b: Agent) -> float:
    base_surplus = self.bargaining_protocol.compute_expected_surplus(a, b)
    ticks_to_reach = pos_a.chebyshev_distance_to(pos_b)
    return base_surplus * (a.discount_factor ** ticks_to_reach)
```

### Phase 3: Cleanup

- **Random proposer assignment:** `proposer = random.choice([agent, other])` eliminates iteration-order bias
- **Documentation:** Updated `theoretical-foundations.md` with BRW reference
- **Test rename:** `test_competitive_equilibrium_achieved` → `test_mrs_equality_in_symmetric_case` (clarifies this is a special case, not a general property)

---

## Commits

| Hash | Description |
|------|-------------|
| `524ede3` | Implement BRW asymmetric Nash for Rubinstein bargaining |
| `43966a8` | Clean up temporary council review documents |
| `b1f9443` | Wire protocol-aware search and random proposer assignment |
| `8da855b` | Update docs for BRW theoretical correction |

---

## Test Status

All 341 tests pass. Tests that verified old proposer-advantage behavior were rewritten to verify:
- Patience determines bargaining power (not proposer identity)
- Equal δ gives symmetric Nash (weights = 0.5, 0.5)
- Proposer identity is irrelevant under BRW

---

## What Was NOT Done

### Deferred (Low Priority)

1. **Event type renaming in matching.py**
   - `CommitmentFormedEvent` → `MatchingCommitmentFormed`
   - `CommitmentBrokenEvent` → `MatchingCommitmentBroken`
   - Reason: Name collision exists but doesn't cause bugs; renaming could break downstream

2. **STATUS.md updates** (minor wording corrections)
   - Grid wrap clarification
   - Search limitation note
   - Matching stability caveat

### Out of Scope (Future Work)

Per `PLAN_theoretical_corrections.md` §9:

1. **Bounded rationality variants** - Agents could intentionally use simpler heuristics
2. **Information asymmetry in search** - Agents don't know counterparty's δ
3. **Walrasian equilibrium benchmark** - Useful for welfare comparison

---

## Behavioral Changes to Note

### Before (Old Rubinstein)
```python
# Proposer got first-mover advantage
outcome = protocol.solve(agent_a, agent_b, proposer=agent_a)
# agent_a got larger share due to proposing
```

### After (BRW Rubinstein)
```python
# Proposer identity ignored; patience determines outcome
outcome = protocol.solve(agent_a, agent_b, proposer=agent_a)
# Share determined by discount factor ratio, not who proposes
```

This is **theoretically correct** for exchange economies but changes simulation dynamics:
- Previously: The agent who "found" the other got an advantage
- Now: Patience is the only source of bargaining power

### Search Target Selection

With protocol-aware search, agents using Rubinstein will evaluate targets differently than under Nash. An agent with high patience may prefer a less-patient distant target (where they'd capture more surplus) over a nearby similar-patience target.

---

## Questions for Discussion

1. **Should we add explicit tests for protocol-aware search?**
   - The plan suggested `test_target_selection_changes_with_protocol()`
   - Currently relying on existing tests passing

2. **Event type renaming - worth doing?**
   - Low priority but could prevent future confusion
   - Would require updating imports in logging/

3. **Any behavioral regressions observed?**
   - Visualization runs fine
   - Batch comparisons still work
   - But simulation dynamics have subtly changed

4. **Next priorities?**
   - More visualization features per VISUALIZATION.md?
   - Additional bargaining protocols (TIOLI, double auction)?
   - Information environments?

---

## Files Modified

```
src/microecon/bargaining.py     # BRW implementation
src/microecon/search.py         # Protocol-aware evaluation
src/microecon/simulation.py     # Protocol wiring, random proposer
tests/test_bargaining.py        # Updated Rubinstein tests
tests/scenarios/test_two_agent.py  # Updated Rubinstein tests
tests/scenarios/test_trading_chain.py  # Renamed CE test
theoretical-foundations.md      # Added BRW reference
```

---

## References

- Binmore, K., Rubinstein, A., & Wolinsky, A. (1986). "The Nash Bargaining Solution in Economic Modelling." RAND Journal of Economics, 17(2), 176-188.
- Osborne & Rubinstein, *Bargaining and Markets* (1990), Chapter 4

---

**Next session:** Review this document, discuss questions above, decide on next priorities.
