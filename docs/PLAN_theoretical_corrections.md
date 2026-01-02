# Theoretical Corrections Plan

**Date:** 2026-01-02
**Scope:** Address theoretical consistency issues identified by council review
**Status:** Planning document for implementation session

---

## Executive Summary

Three independent reviews (Gemini, GPT-5.2 Codex, Opus) converged on several theoretical issues. This document captures decisions made through interactive discussion and provides a prioritized implementation plan.

### Key Decisions

| Issue | Decision |
|-------|----------|
| Rubinstein formulation | Implement asymmetric Nash with patience-derived weights |
| Proposer assignment | Random (not iteration order) |
| Search surplus | Ex-ante expected value over proposer uncertainty |
| Matching surplus | Same computation as search (consistency) |
| Distance in matching | Apply discounting (currently missing) |

---

## 1. Rubinstein Protocol Correction (High Priority)

### Problem

GPT-5.2 identified that the current Rubinstein implementation applies a formula derived for **linear utility (pie-splitting)** to **Cobb-Douglas preferences**. The share formula `(1-δ₂)/(1-δ₁δ₂)` is correct for dividing a fixed pie, but for exchange economies with non-linear utility, alternating offers converges to a **weighted Nash bargaining solution**, not a fixed share of utility gains.

Current implementation (heuristic):
```python
# Compute Rubinstein shares (linear utility formula)
share_1 = (1 - delta_2) / (1 - delta_1 * delta_2)
# Apply to divide total utility gains
gains_1 = share_1 * total_gains
# Find Pareto-efficient allocation with those utility shares
```

### Theoretical Foundation

**Binmore, Rubinstein, and Wolinsky (1986)** showed that for general preferences, the alternating-offers SPE converges to the **asymmetric Nash bargaining solution** as δ → 1. The bargaining power weights derive from patience:

```
α₁ = ln(δ₁) / (ln(δ₁) + ln(δ₂))
α₂ = 1 - α₁
```

The asymmetric Nash solution maximizes:
```
max (u₁ - d₁)^α₁ × (u₂ - d₂)^α₂
```
subject to Pareto efficiency and individual rationality.

### Implementation Plan

1. **Add `asymmetric_nash_bargaining_solution()` function** in `bargaining.py`
   - Input: preferences, endowments, bargaining weights (α₁, α₂)
   - Algorithm: Modify golden section search to maximize asymmetric Nash product
   - Output: Same `TradeSolution` structure

2. **Refactor `rubinstein_bargaining_solution()`**
   - Compute α₁, α₂ from discount factors using BRW formula
   - Call asymmetric Nash solution
   - Handle edge cases (δ = 1 → equal weights → symmetric Nash)

3. **Update `RubinsteinBargainingProtocol.execute()`**
   - Use refactored solution function
   - Proposer no longer affects outcome (asymmetric Nash handles impatience)
   - Keep proposer parameter for logging/analysis purposes

4. **Add tests**
   - Asymmetric preferences/endowments (GPT-5.2's example case)
   - Verify convergence to symmetric Nash as δ₁, δ₂ → 1
   - Verify extreme patience asymmetry (δ₁=0.99, δ₂=0.5)

### References
- Binmore, K., Rubinstein, A., & Wolinsky, A. (1986). "The Nash Bargaining Solution in Economic Modelling." RAND Journal of Economics, 17(2), 176-188.
- Theoretical-foundations.md §3.3 (update required)

---

## 2. Proposer Assignment (High Priority)

### Problem

Currently, the proposer in Rubinstein bargaining is determined by iteration order in `simulation.py`, which creates arbitrary deterministic bias unrelated to any economic concept.

### Decision

**Random assignment** with equal probability. This:
- Eliminates arbitrary bias
- Aligns with theoretical treatments where proposer order is often randomized or alternates
- Simplifies reasoning about expected outcomes

### Implementation Plan

1. In `simulation.py`, where trades are executed:
   ```python
   proposer = random.choice([agent1, agent2])
   ```

2. Ensure RNG is seeded via simulation seed for reproducibility

3. Note: With asymmetric Nash Rubinstein (section 1), proposer identity has minimal effect on outcomes. It mainly affects first-offer advantage, which vanishes as δ → 1.

---

## 3. Protocol-Aware Search and Matching (High Priority)

### Problem

All three reviewers flagged: `search.py` and `matching.py` hardcode `compute_nash_surplus()` regardless of the active bargaining protocol. This undermines "institutional visibility" because:
- Agents search/match as if Nash bargaining will occur
- But actual trade may use Rubinstein (with different surplus division)
- Agent decisions are based on incorrect expectations

### Conceptual Decision

**Ex-ante expected value approach**: Agents form rational expectations about bargaining outcomes given:
- The active bargaining protocol
- Protocol rules they understand (e.g., "proposer is random")
- Type information about potential partners

For Rubinstein with random proposer:
```
E[surplus_i] = 0.5 × surplus_if_i_proposes + 0.5 × surplus_if_other_proposes
```

Since asymmetric Nash Rubinstein doesn't depend on proposer (section 1), this simplifies to: compute expected surplus using asymmetric Nash weights.

### Implementation Plan

1. **Ensure `BargainingProtocol.compute_expected_surplus()` is protocol-specific**
   - `NashBargainingProtocol`: Returns Nash surplus (current behavior)
   - `RubinsteinBargainingProtocol`: Returns asymmetric Nash surplus with patience-derived weights

2. **Modify `search.py:evaluate_targets()`**
   - Accept `bargaining_protocol` parameter
   - Call `protocol.compute_expected_surplus()` instead of `compute_nash_surplus()`

3. **Modify `simulation.py:step()` DECIDE phase**
   - Pass `self.bargaining_protocol` to search and matching functions

4. **Modify `StableRoommatesMatchingProtocol`**
   - Accept bargaining protocol for surplus computation
   - Use protocol's expected surplus for preference ranking

### Consistency Principle

Search and matching use the **same** surplus computation. An agent's ranking of potential partners should be consistent whether they're:
- Searching (deciding who to move toward)
- Matching (committing in StableRoommates algorithm)

---

## 4. Distance Discounting in Matching (Medium Priority)

### Problem

GPT-5.2 and user notes identify that `StableRoommatesMatchingProtocol` ignores distance when building preference lists. This was unintentional.

Search correctly discounts:
```
discounted_surplus = surplus × δ^distance
```

Matching should apply the same logic: a distant partner means delayed payoff.

### Implementation Plan

1. **Modify `StableRoommatesMatchingProtocol.compute_matches()`**
   - Accept agent positions and discount factor
   - Apply distance discounting to surplus when building preference lists:
     ```python
     adjusted_surplus = expected_surplus * (discount ** distance)
     ```

2. **Consistency with search**
   - Use same δ parameter as search
   - Preference ranking now accounts for travel time

3. **Tests**
   - Verify preference lists change when agents are at different distances
   - Scenario: verify matching choices differ from zero-distance baseline

---

## 5. Documentation Corrections (Medium Priority)

### 5.1 STATUS.md Updates

| Issue | Current | Correction |
|-------|---------|------------|
| Grid wrap | "NxN toroidal grid" | "NxN grid (bounded by default, wrap configurable)" |
| Search limitation | Mentioned | Clarify: intentionally simplified pending protocol-aware search |
| Stability claims | "Produces stable matching (no blocking pairs)" | "Produces stable matching when one exists under truncated/perception-limited preferences" |

### 5.2 Competitive Equilibrium Terminology

In `test_trading_chain.py`, rename:
- `test_competitive_equilibrium_achieved` → `test_mrs_equality_in_symmetric_case`

Add docstring clarification:
> Bilateral Nash bargaining achieves MRS equality (competitive equilibrium) **in this specific symmetric scenario**. This is not a general property of bilateral exchange.

### 5.3 Stale Session Documents

Review and update or annotate:
- `docs/SESSION_2026_01_02_matching_implementation.md` - commitment events ARE now wired (code updated since doc written)

### 5.4 THEORETICAL_TESTS.md Path Correction

Update file paths from `tests/test_theoretical_scenarios.py` to `tests/scenarios/` structure.

### 5.5 theoretical-foundations.md

Update section 3.3 (Rubinstein) to:
- Reference Binmore, Rubinstein, Wolinsky (1986)
- Document asymmetric Nash formulation
- Clarify relationship between patience and bargaining power

---

## 6. Code Quality: Event Type Naming (Low Priority)

### Problem

Duplicate class names `CommitmentFormedEvent` and `CommitmentBrokenEvent` exist in:
- `matching.py` (domain events with tick field)
- `logging/events.py` (serializable log records, frozen, no tick)

### Decision

Rename `matching.py` versions to clarify purpose:
- `CommitmentFormedEvent` → `MatchingCommitmentFormed`
- `CommitmentBrokenEvent` → `MatchingCommitmentBroken`

This preserves both classes for their distinct purposes while eliminating name collision.

---

## 7. Test Coverage Additions

### 7.1 Asymmetric Rubinstein Tests

GPT-5.2 provided a concrete test case:
```python
prefs1 = CobbDouglas(0.2)
prefs2 = CobbDouglas(0.7)
endow1 = Bundle(10.0, 2.0)
endow2 = Bundle(3.0, 9.0)
```

Add test verifying:
- With δ₁ = δ₂ = 0.999, converges to symmetric Nash
- With δ₁ = 0.99, δ₂ = 0.5, asymmetric outcome favors patient agent

### 7.2 Protocol-Aware Search Test

Once search is protocol-aware (section 3):
```python
def test_target_selection_changes_with_protocol():
    """Verify that best target changes when switching from Nash to Rubinstein."""
    # Setup: Agent A with two potential targets B and C
    # B is closer but similar patience to A
    # C is farther but much less patient than A
    # Under Nash: prefer B (closer, distance matters)
    # Under Rubinstein: might prefer C (patience advantage dominates)
```

### 7.3 Distance-Discounted Matching Test

```python
def test_matching_preferences_include_distance():
    """Verify stable roommates preferences account for travel distance."""
    # Setup: Agent A equidistant from B and C
    # B and C have equal surplus potential with A
    # Move C farther away
    # A should now prefer B
```

---

## 8. Implementation Order

Recommended sequence based on dependencies:

### Phase 1: Core Theoretical Fixes
1. Implement `asymmetric_nash_bargaining_solution()` (foundation for everything)
2. Refactor `rubinstein_bargaining_solution()` to use it
3. Update `RubinsteinBargainingProtocol.compute_expected_surplus()`
4. Add asymmetric Rubinstein tests

### Phase 2: Protocol-Aware Agents
5. Modify `evaluate_targets()` to accept bargaining protocol
6. Modify `StableRoommatesMatchingProtocol` for protocol-aware surplus
7. Add distance discounting to matching
8. Wire through simulation.py
9. Add protocol-aware search/matching tests

### Phase 3: Cleanup
10. Random proposer assignment
11. Event type renaming
12. Documentation updates
13. Test naming/docstring corrections

---

## 9. Open Questions for Future Work

These emerged from discussion but are **out of scope** for this plan:

1. **Bounded rationality variants**: Search could intentionally use simpler heuristics (Nash surplus) even when Rubinstein protocol is active. This would be a modeling choice, not an error. Defer to future work on cognitive constraints.

2. **Information asymmetry in search**: Current plan assumes agents know counterparty's discount factor for Rubinstein expectations. Under private information, agents might not know partner's patience. Needs information environment integration.

3. **Walrasian equilibrium benchmark**: Opus noted no computed CE benchmark exists. Useful for welfare comparison but separate from this theoretical correction work.

---

## 10. Success Criteria

This plan is complete when:

- [ ] Rubinstein protocol produces asymmetric Nash outcomes
- [ ] δ₁ = δ₂ → 1 converges to symmetric Nash (verified by test)
- [ ] Search uses protocol-specific expected surplus
- [ ] Matching uses same surplus computation as search
- [ ] Matching applies distance discounting
- [ ] Proposer is randomly assigned
- [ ] All documentation issues addressed
- [ ] New tests pass for asymmetric cases

---

**Document prepared:** 2026-01-02
**For implementation in:** Future session
