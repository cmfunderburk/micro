# Session Review: Trading Chain Scenario Development

**Date:** 2026-01-01
**Focus:** Trading chain theoretical tests (4 agents in a line with uniform endowments)

---

## 1. Session Objective

Build on previous theoretical testing work by implementing a "trading chain" scenario: 4 agents with varying preferences (α = 0.2, 0.4, 0.6, 0.8) arranged in a line. The goal was to test distance vs. surplus tradeoffs and verify emergent market dynamics.

---

## 2. What Was Accomplished

### 2.1 Theoretical Analysis

Computed hand-verified predictions for the uniform endowment case:

**Initial State (all agents at (6,6)):**
| Agent | α | MRS | Utility |
|-------|-----|-----|---------|
| A | 0.2 | 0.25 | 6.0 |
| B | 0.4 | 0.667 | 6.0 |
| C | 0.6 | 1.5 | 6.0 |
| D | 0.8 | 4.0 | 6.0 |

**Nash Surplus Matrix:**
| Pair | Total Surplus | Notes |
|------|---------------|-------|
| A-D | 2.55 | Extreme preferences, highest complementarity |
| A-C | 1.08 | Moderate |
| B-D | 1.08 | Moderate |
| C-D | 0.29 | Adjacent, similar preferences |
| B-C | 0.24 | Adjacent |
| A-B | 0.21 | Adjacent, similar preferences |

**Key insight:** A-D surplus is 12x higher than adjacent-pair surplus, and even with distance discounting (δ^15 ≈ 0.21), A-D remains the highest-value target for both A and D.

### 2.2 Test Structure Created

Three test classes following the established stage-based pattern:
- `TestTradingChainUniformStage1`: Initial state, MRS values, distances, surplus ordering, target selection
- `TestTradingChainUniformStage2`: First trade dynamics, post-trade allocations
- `TestTradingChainUniformStage3`: Equilibrium properties, welfare, MRS convergence

### 2.3 Critical Finding: Path Crossing Behavior

**Expected behavior (based on economic analysis):**
- A targets D, D targets A → they converge and trade first
- B and C trade second
- Result: 2 trades, competitive equilibrium (all MRS = 1.0)

**Actual simulation behavior:**
- A targets D, moves toward D (increasing row)
- B targets D, moves toward D (increasing row)
- C targets A, moves toward A (decreasing row)
- D targets A, moves toward A (decreasing row)
- **B and C cross paths at tick 3 and trade!** (opportunistic trade)

**Actual trade sequence:**
1. B ↔ C (tick 3) - path crossing
2. B ↔ D (tick 5) - B continues toward D
3. A ↔ B (tick 7) - A eventually meets B

**Final state:** A and D never trade directly. The system doesn't reach competitive equilibrium. Remaining surplus exists (A-D: 0.07, B-D: 0.17).

---

## 3. Design Ambiguity Surfaced

### 3.1 The Core Question

**When agents pursuing different targets cross paths, should they trade?**

**Option A: Opportunistic Trading (current behavior)**
- Any co-located agents with positive surplus can trade
- Path crossings create trading opportunities
- Emergent, unpredictable dynamics

**Option B: Committed Targeting**
- Agents only trade with their selected target
- Path crossings don't trigger trades
- More predictable, theoretically cleaner dynamics

**Option C: Target Lock-in with Re-evaluation**
- Agents commit to a target until trade completes or surplus goes to zero
- After each trade, re-evaluate and select new target

### 3.2 Implications

This design choice significantly affects:
- Whether the highest-surplus pairs actually trade first
- Whether bilateral exchange reaches competitive equilibrium
- The predictability and theoretical tractability of outcomes
- The role of spatial arrangement in determining outcomes

### 3.3 Code Location

The behavior is controlled in `src/microecon/simulation.py`:
- **Lines 160-185 (Phase 2.5):** Path-crossing detection forces agents to meet
- **Lines 208-264 (Phase 3):** Trades execute for ANY co-located agents with positive surplus

---

## 4. Value of the Testing Process

### 4.1 What the Tests Revealed

1. **Emergent dynamics can override economic predictions:** Economic analysis predicted A-D trade first, but spatial dynamics (path crossing) produced B-C first.

2. **The simulation has implicit design decisions:** The opportunistic trading behavior wasn't explicitly designed - it's a consequence of how Phase 3 was implemented.

3. **Simple scenarios surface complex questions:** A 4-agent linear arrangement seemed straightforward but revealed fundamental questions about agent commitment and decision-making.

### 4.2 The Testing Methodology Works

The process of:
1. Computing hand-verified predictions
2. Writing tests encoding those predictions
3. Running tests and observing failures
4. Investigating WHY they failed

...successfully surfaced a design ambiguity that would have been harder to notice through ad-hoc simulation runs.

### 4.3 Lessons Learned

- **Start simple:** The linear arrangement is simpler than hub-and-spoke but revealed deeper issues
- **Trace step-by-step:** The tick-by-tick analysis was essential to understanding path crossing
- **Don't circumvent surprises:** The initial instinct to redesign the scenario to avoid path crossing would have hidden the issue

---

## 5. Current State

### 5.1 Test Suite Status

- **97 tests passing** (all existing theoretical scenarios)
- **29 tests skipped** (trading chain tests, pending design decision)
- Total: 126 tests in `test_theoretical_scenarios.py`

### 5.2 Code Changes

- Added 3 test classes for trading chain scenario (marked with `@pytest.mark.skip`)
- Added documentation comments explaining the path-crossing issue
- No changes to simulation code

### 5.3 Files Modified

- `tests/test_theoretical_scenarios.py`: Added skipped trading chain tests

---

## 6. Next Steps

### 6.1 Design Decision Required

Before completing the trading chain tests, decide on path-crossing behavior:

| Option | Pros | Cons |
|--------|------|------|
| Opportunistic | Emergent, realistic (agents don't ignore opportunities) | Less predictable, harder to analyze theoretically |
| Committed | Predictable, theoretically tractable | May seem rigid, ignores profitable opportunities |
| Lock-in + re-eval | Balanced | More complex to implement |

Consider: What does the economic literature say about bilateral exchange with search? What behavior makes the simulation most useful for research?

### 6.2 Implementation Options

If committed targeting is chosen:
- Modify Phase 3 in `simulation.py` to check if agents were targeting each other
- Track agent "commitments" across ticks
- Add mechanism for commitment release (target traded with someone else, surplus exhausted)

If opportunistic is retained:
- Update test expectations to match actual behavior
- Document the behavior explicitly
- Consider whether path-crossing detection (Phase 2.5) is still needed

### 6.3 Additional Scenarios to Explore

Once the design is resolved:
1. **Preference-aligned endowments:** A=(10,2), B=(8,4), C=(4,8), D=(2,10)
2. **Clustered pairs:** Test intra-cluster vs cross-cluster dynamics
3. **Rubinstein protocol:** How does first-mover advantage compound across trades?

---

## 7. Session Summary

This session demonstrated the value of rigorous theoretical testing. What started as a straightforward test case revealed a fundamental design ambiguity in the simulation's trading behavior. The trading chain scenario is now well-documented and ready to complete once the path-crossing design decision is made.

**Key takeaway:** Simple scenarios with hand-verifiable predictions are powerful tools for surfacing implicit design decisions and ensuring the simulation behaves as intended.

---

**Document Version:** 1.0
**Author:** Claude Code session
**Status:** Complete
