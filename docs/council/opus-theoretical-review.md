# Theoretical Consistency Review

**Date:** 2026-01-02
**Scope:** Critical evaluation of implementation against theoretical foundations
**Status:** Pre-0.0.1 alpha review

---

## Executive Summary

This review examines the microecon platform's implementation consistency with the theoretical foundations documented in `theoretical-foundations.md` and the vision articulated in `VISION.md`. Overall, the implementation demonstrates **strong theoretical grounding** in its core bargaining mechanisms but has **several issues** that warrant attention before a 0.0.1 release.

### Key Findings

| Area | Status | Severity |
|------|--------|----------|
| Nash Bargaining Solution | ✅ Sound | — |
| Rubinstein Protocol | ⚠️ Minor issue | Low |
| Cobb-Douglas Preferences | ✅ Sound | — |
| Search/Target Selection | ⚠️ Known limitation | Medium |
| Matching Protocols | ✅ Sound | — |
| Competitive Equilibrium Claims | ⚠️ Overstated | Medium |
| Test Theoretical Accuracy | ⚠️ Some inaccuracies | Medium |

---

## 1. Bargaining Implementation

### 1.1 Nash Bargaining Solution

**Reference:** O&R-B Chapter 2, Kreps II Chapter 23

**Implementation:** `src/microecon/bargaining.py:67-166`

**Theoretical Basis:**
The Nash Bargaining Solution maximizes the Nash product:
```
argmax (u₁ - d₁)(u₂ - d₂) subject to feasibility and IR
```
where d₁, d₂ are disagreement utilities (status quo = consume own endowment).

**Assessment: ✅ SOUND**

The implementation correctly:
- Uses endowment utilities as disagreement points (lines 111-112)
- Maximizes Nash product numerically via golden section search
- Enforces individual rationality constraints (lines 146-156)
- Produces Pareto-efficient allocations (equal MRS post-trade)

**Verified by tests:**
- `test_pareto_efficiency` confirms equal MRS after trade
- `test_allocation_matches_nash_solution` validates specific allocations
- `test_symmetric_solution_basic` confirms order-independence (Nash axiom symmetry)

**Minor note:** The numerical optimization approach (golden section search) is appropriate given that Cobb-Douglas NBS lacks a convenient closed-form for the general case. The 60 iterations provide ~1e-13 relative precision.

---

### 1.2 Rubinstein Alternating Offers

**Reference:** O&R-B Chapter 3, Theorem 3.4

**Implementation:** `src/microecon/bargaining.py:369-428, 430-515`

**Theoretical Basis:**
The unique SPE of infinite-horizon alternating offers with discount factors δ₁, δ₂ gives:
- Proposer 1's share: (1 - δ₂)/(1 - δ₁δ₂)
- Proposer 2's share: δ₂(1 - δ₁)/(1 - δ₁δ₂)

**Assessment: ⚠️ MINOR ISSUE**

The share computation (lines 416-426) is **correct per the Rubinstein formula**. However:

**Issue 1: Interpretation Mismatch**

The code comment on line 394 states:
> "Equal δ: proposer gets 1/(1+δ), responder gets δ/(1+δ)"

This is correct, but the *implementation* determines who is "proposer" based on who moves toward whom in the simulation (line 353: `proposer=agent`). This conflates the economic concept of "first mover" with the spatial concept of "pursuer."

**Theoretical nuance:** In Rubinstein's original formulation, the proposer advantage comes from making the first offer in the *bargaining game*, not from spatial movement. The current implementation is a reasonable modeling choice but should be documented as an interpretation rather than a direct mapping.

**Issue 2: Convergence Test Tolerance**

In `test_convergence_to_nash` (line 791), the test uses δ=0.999 and expects 50-50 split with `abs=0.01` tolerance. The theoretical share at δ₁=δ₂=0.999 is:
```
share_1 = (1 - 0.999)/(1 - 0.999*0.999) = 0.001/0.001999 ≈ 0.5003
```
This passes but the test comment "Should be close to 50-50" could note the expected deviation.

**Recommendation:** Document in `bargaining.py` docstring that the "proposer" in spatial simulation is the agent who initiated movement toward the other.

---

### 1.3 Cobb-Douglas Preferences

**Reference:** Kreps I, Chapters 2-3

**Implementation:** `src/microecon/preferences.py`

**Assessment: ✅ SOUND**

The implementation correctly:
- Defines utility as u(x,y) = x^α * y^(1-α) (line 83)
- Computes MRS = (α/(1-α)) * (y/x) (line 106)
- Handles boundary conditions (utility = 0 if x ≤ 0 or y ≤ 0)
- Implements Marshallian demand: x* = αm/p_x, y* = (1-α)m/p_y (lines 121-123)

The Marshallian demand derivation is standard from the Lagrangian first-order conditions with Cobb-Douglas utility (Kreps I, Ch 3.4).

---

## 2. Search and Target Selection

### 2.1 Discounted Surplus Evaluation

**Implementation:** `src/microecon/search.py:60-144`

**Claimed Basis:** Search behavior with expected surplus discounted by time to reach partner.

**Assessment: ⚠️ KNOWN LIMITATION**

**Issue: Protocol Mismatch (Documented in STATUS.md)**

The implementation always uses `compute_nash_surplus()` (line 118) regardless of which bargaining protocol is configured:

```python
# From search.py:118
expected_surplus = compute_nash_surplus(observer_type, target_type)
```

This means:
- When using `RubinsteinBargainingProtocol`, agents evaluate targets using Nash surplus
- But actual trade uses Rubinstein surplus division (with proposer advantage)

**Theoretical concern:** This creates a potential inconsistency where:
1. Agent A evaluates B expecting Nash split (50-50)
2. Actual trade gives A proposer advantage (>50%)
3. A's search decision was based on incorrect expectations

**Severity:** Medium. For now this is acceptable because:
- Nash and Rubinstein produce identical efficiency (same total surplus)
- Only the *division* differs, not the decision to trade
- With high δ (common case), the difference is small

**Recommendation:** Consider adding `BargainingProtocol.compute_expected_surplus()` calls in search evaluation, or document this as an intentional simplification.

---

### 2.2 Tie-Breaking

**Implementation:** `src/microecon/search.py:130-137`

**Assessment: ✅ SOUND**

Lexicographic tie-breaking by agent ID ensures deterministic behavior:
```python
if discounted_value > best_value or (
    discounted_value == best_value
    and best_target_id is not None
    and target_id < best_target_id
):
```

This is correctly tested in `test_properties.py:TestTieBreakingDeterminism`.

---

## 3. Matching Protocols

### 3.1 Stable Roommates (Irving's Algorithm)

**Reference:** Irving, R.W. (1985). "An efficient algorithm for the stable roommates problem."

**Implementation:** `src/microecon/matching.py:188-478`

**Assessment: ✅ SOUND**

The implementation correctly follows Irving's two-phase algorithm:
1. **Phase 1 (Proposal):** Gale-Shapley style proposals (lines 298-353)
2. **Phase 2 (Rotation Elimination):** Find and eliminate rotations (lines 357-403)

Key properties verified:
- Produces stable matching when one exists
- Handles cases where no stable matching exists
- Uses bilateral surplus as preference ranking (correct adaptation to spatial/economic context)

**Note on adaptation:** The original Irving algorithm assumes complete preference lists. This implementation handles partial visibility (perception-constrained matching), which is a reasonable extension for the spatial context.

---

### 3.2 Opportunistic Matching

**Implementation:** `src/microecon/matching.py:162-186`

**Assessment: ✅ SOUND**

Correctly implements "any co-located pair can trade" semantics with no explicit matching phase.

---

## 4. Equilibrium Claims in Tests

### 4.1 "Competitive Equilibrium" Terminology

**Tests:** `test_trading_chain.py`, particularly lines 667-688

**Issue: ⚠️ OVERSTATED CLAIM**

The test `test_competitive_equilibrium_achieved` (line 667) claims:
> "With uniform endowments, bilateral exchange achieves competitive equilibrium."

This is **technically correct for the specific scenario** but potentially misleading:

**Why it works here:**
- Uniform endowments (6,6) for all agents
- Cobb-Douglas preferences with α values symmetric around 0.5
- Bilateral Nash bargaining happens to achieve MRS = 1.0 for all

**Why it's not general:**
- Bilateral exchange does NOT generally achieve competitive equilibrium
- The claim relies on the specific setup where all trades exhaust bilateral surplus AND happen to equalize MRS globally
- With non-uniform endowments or different preference distributions, bilateral exchange typically leaves unrealized multilateral gains

**Recommendation:** Rename test to `test_mrs_equality_achieved_in_symmetric_case` or add docstring clarifying this is a special case property, not a general result.

---

### 4.2 MRS Convergence vs Zero Bilateral Surplus

**Tests:** `test_hub_and_spoke.py:449-478`, `test_hub_and_spoke.py:1218-1246`

**Assessment: ✅ CORRECT NUANCE**

The tests correctly distinguish between:
1. **Zero bilateral surplus:** No pair has remaining gains from trade
2. **MRS equality:** All agents have equal MRS (competitive equilibrium)

The docstrings appropriately note:
> "At equilibrium, zero bilateral surplus does NOT imply perfect MRS equality (which requires a complete market/Walrasian auctioneer)."

This is theoretically sound. The tests verify MRS *convergence* rather than MRS *equality*.

---

## 5. Specific Test Issues

### 5.1 Hand-Computed Constants

**Files:** All scenario tests

**Issue: ⚠️ SOME INACCURACIES**

Several tests include hand-computed constants that should be verified:

**Example 1:** `test_trading_chain.py:84-88`
```python
# Nash surplus values (hand-computed)
SURPLUS_A_D = 1.2754  # Each agent's gain from A-D trade
SURPLUS_A_C = 0.5441  # A's gain from A-C
SURPLUS_B_D = 0.5374  # B's gain from B-D
SURPLUS_A_B = 0.0975  # A's gain from A-B (neighbors, similar prefs)
SURPLUS_B_C = 0.1220  # B's gain from B-C
```

I verified the A-D surplus computation:
- Agents: α_A=0.2, α_D=0.8, both with endowment (6,6)
- Total: (12, 12)
- Nash solution: A gets (2.4, 9.6), D gets (9.6, 2.4)
- u_A(2.4, 9.6) = 2.4^0.2 * 9.6^0.8 ≈ 7.28
- u_A(6, 6) = 6^0.2 * 6^0.8 = 6.0
- Surplus_A = 7.28 - 6.0 = 1.28 ≈ 1.2754 ✓

The constants appear correct.

**Example 2:** `test_two_agent.py:475-479`
```python
INITIAL_UTILITY = 2.9907
POST_TRADE_ALLOCATION_A = (3.0, 9.0)
POST_TRADE_ALLOCATION_B = (9.0, 3.0)
POST_TRADE_UTILITY = 6.8385
```

Verification for α_A=0.25, α_B=0.75, endowments (10,2) and (2,10):
- u_A(10,2) = 10^0.25 * 2^0.75 ≈ 1.778 * 1.682 ≈ 2.99 ✓
- Post-trade (3,9): u_A = 3^0.25 * 9^0.75 ≈ 1.316 * 5.196 ≈ 6.84 ✓

The constants are accurate.

---

### 5.2 Opportunistic Mode Welfare Predictions

**File:** `test_trading_chain.py:1011-1017`

```python
FINAL_WELFARE = 26.20  # Suboptimal (committed achieves 26.80)
WELFARE_GAIN = 2.20    # Less than committed mode's 2.80
```

**Concern:** These values depend on the exact trade sequence, which depends on spatial dynamics. The test `test_welfare_improvement_suboptimal` uses `rel=0.02` tolerance (2%), which is appropriate given the stochastic nature of spatial movement.

**Recommendation:** Consider adding a note that these values are scenario-specific and may vary slightly with different grid configurations.

---

## 6. Alignment with VISION.md

### 6.1 Institutional Visibility

**Vision claim:** "The central innovation is making institutions visible."

**Assessment: ✅ ACHIEVED**

The platform successfully implements swappable:
- Bargaining protocols (Nash, Rubinstein)
- Matching protocols (Opportunistic, StableRoommates)

The trading chain scenario demonstrates measurable outcome differences (~2.2% welfare gap between matching protocols).

---

### 6.2 Theoretical Grounding

**Vision claim:** "No ad-hoc solutions. Every behavioral rule must have formal justification."

**Assessment: ✅ LARGELY ACHIEVED**

All implemented mechanisms have textbook references:
- Nash bargaining: O&R-B Ch 2
- Rubinstein: O&R-B Ch 3
- Irving's algorithm: Irving (1985)
- Cobb-Douglas: Kreps I Ch 2-3

**Minor gap:** The discounted surplus search heuristic (surplus * δ^distance) lacks an explicit textbook citation. It's a reasonable construction but should be documented as a modeling choice.

---

### 6.3 Equilibrium Benchmarks

**Vision claim:** "Compute equilibrium benchmarks as comparison baselines."

**Assessment: ⚠️ PARTIALLY ACHIEVED**

Current state:
- ✅ Nash bargaining benchmark for bilateral exchange
- ✅ Rubinstein SPE benchmark
- ❌ No Walrasian/competitive equilibrium benchmark

The trading chain scenario claims to achieve "competitive equilibrium" but this is incidental to the symmetric setup, not a computed benchmark.

**Recommendation for 0.0.1:** Add a note in STATUS.md acknowledging that Walrasian equilibrium benchmarks are not yet implemented.

---

## 7. Recommendations for 0.0.1 Release

### Must Fix (Blocking)

None identified. The core implementation is theoretically sound.

### Should Fix (Important)

1. **Clarify competitive equilibrium claims** in test docstrings
   - Rename or annotate `test_competitive_equilibrium_achieved`
   - Clarify this is a special-case property

2. **Document search-protocol mismatch** more prominently
   - Already noted in STATUS.md but could be clearer in CLAUDE.md

3. **Add theoretical citation for discounted surplus search**
   - Document as a modeling choice in `search.py`

### Could Fix (Nice to Have)

1. Add computed Walrasian equilibrium as benchmark for comparison scenarios
2. Implement protocol-aware search evaluation
3. Add tolerance documentation for hand-computed test constants

---

## 8. Conclusion

The microecon platform demonstrates **strong alignment with canonical microeconomic theory**. The core bargaining mechanisms (Nash, Rubinstein) are correctly implemented with appropriate references. The matching protocols enable meaningful institutional comparison as envisioned.

The identified issues are primarily:
- Presentation/documentation (competitive equilibrium terminology)
- Known limitations (search-protocol mismatch)
- Minor theoretical gaps (discounted surplus justification)

None of these block a 0.0.1 release. The platform is suitable for use as a research instrument with the documented limitations.

---

**Review completed:** 2026-01-02
**Reviewer:** Claude Code (automated review)
