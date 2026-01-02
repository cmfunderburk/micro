# Theoretical Scenario Tests

**Status:** Reference document for theoretical validation
**Date:** 2026-01-01
**Purpose:** Document hand-verified economic scenarios that validate simulation correctness

---

## 1. Overview

The file `tests/test_theoretical_scenarios.py` contains scenarios simple enough to compute by hand, encoding expected economic outcomes as test assertions. These "theoretical unit tests" verify that simulation outcomes match analytically-derived predictions.

**Test count:** 97 tests across 14 test classes

---

## 2. Test Classes

### 2.1 TestTwoAgentSymmetricScenario (16 tests)

**Setup:**
```
Agent A: α=0.5, endowment=(10,2), position=(0,0)
Agent B: α=0.5, endowment=(2,10), position=(5,5)
```

**Hand-computed predictions:**
- u(x,y) = x^0.5 · y^0.5
- Initial utilities: √20 ≈ 4.472 for each
- Nash solution: (6, 6) for each agent
- Post-trade utility: 6.0 (gain ≈ 1.528)
- Post-trade MRS: 1.0 for both (Pareto efficient)

**Tests:**
| Phase | Tests | Verifications |
|-------|-------|---------------|
| Initial state | 2 | Utilities = √20, positions correct |
| Search | 3 | Positive surplus detected, target selected, discounting correct |
| Movement | 2 | Agents converge, meet within Chebyshev distance |
| Bargaining | 5 | Allocation=(6,6), utility=6.0, MRS=1.0, feasibility |
| Equilibrium | 4 | Zero surplus, no target, no trades, no movement |

---

### 2.2 TestTwoAgentAsymmetricScenario (9 tests)

**Setup:**
```
Agent A: α=0.25 (prefers y), endowment=(10,2)
Agent B: α=0.75 (prefers x), endowment=(2,10)
```

**Hand-computed predictions:**
- Initial utilities: ≈ 2.991 for each
- Nash solution: A gets (3, 9), B gets (9, 3)
- Post-trade utilities: ≈ 6.838 for each
- Gain per agent: ≈ 3.848 (symmetric due to mirror symmetry)

**Key insight:** Mirror symmetry (α_A + α_B = 1, complementary endowments) produces symmetric gains despite asymmetric preferences.

**Tests:** Initial utilities, trade occurrence, allocation direction, exact allocations, utility gains, MRS equality, zero post-trade surplus, equilibrium reached.

---

### 2.3 TestTwoAgentNoTradeScenario (3 tests)

**Setup:**
```
Agent A: α=0.5, endowment=(5,5), position=(5,5)
Agent B: α=0.5, endowment=(5,5), position=(5,5)
```

**Prediction:** Both agents are already on the contract curve (MRS = 1). No gains from trade exist.

**Tests:** Zero surplus computation, no trade when co-located, no movement target.

---

### 2.4 TestRubinsteinProtocol (9 tests)

**Key properties verified:**
1. **First-mover advantage:** Proposer gets share = 1/(1+δ) ≈ 0.526 with δ=0.9
2. **Surplus shares match formula:** share_1 = (1-δ₂)/(1-δ₁δ₂)
3. **Patience = power:** Higher δ → larger share (tested: δ=0.99 vs δ=0.5)
4. **Convergence to Nash:** As δ → 1, Rubinstein → 50-50 split

**Reference:** Osborne & Rubinstein, *Bargaining and Markets*, Chapter 3, Theorem 3.4

---

### 2.5 TestThreeAgentSequentialTrading (6 tests)

**Setup:**
```
A (α=0.5):  endowment=(10,2), position=(5,5)
B (α=0.5):  endowment=(2,10), position=(5,6)  [adjacent to A]
C (α=0.25): endowment=(8,4),  position=(15,15) [far from A,B]
```

**Predicted trading sequence:**
1. **Stage 1:** A-B trade → both get (6, 6)
2. **Stage 2:** A-C trade → A: (9.78, 4.36), C: (4.22, 5.64)
3. **Stage 3:** B-C trade → B: (8.10, 4.50), C: (2.13, 7.14)

**Key insights:**
- After A-B trade, A and B are equilibrated with each other
- But A and B both have surplus with C (different preferences)
- After A-C trade, B *still* has surplus with C's new allocation
- Total of 3 trades, welfare gain: 13.70 → 17.84 (+4.14)

**Tests:** Initial state, first trade between A-B, subsequent trades with C, welfare improvement >3.0, C gains y, equilibrium reached.

---

### 2.6 TestNashSymmetry (2 tests)

**Purpose:** Verify Nash bargaining solution is invariant to agent ordering.

**Bug discovered:** The golden section search failed when the feasible region was entirely above or below W_x/2, causing different results depending on which agent was listed first.

**Fix applied:** Modified `_solve_nash_cobb_douglas` to find any feasible point first, then expand to find bounds.

---

### 2.7 TestPerceptionBoundary (3 tests)

**Tests:**
- Agent exactly at perception radius is found
- Agent just outside perception radius is not found
- Asymmetric perception: only the agent with sufficient range moves toward the other

---

### 2.8 TestTieBreakingDeterminism (3 tests)

**Purpose:** Verify that tie-breaking is deterministic and uses lexicographic agent ID ordering.

**Setup:** Multiple agents with identical preferences, endowments, and distances from a center agent, creating true ties in discounted surplus.

**Tests:**
- `test_search_tie_break_selects_smallest_id`: When targets have equal discounted value, lexicographically smallest ID wins
- `test_trade_partner_tie_break_selects_smallest_id`: When multiple trade partners available at same position, smallest ID trades first
- `test_determinism_same_seed_same_sequence`: Identical configurations produce identical trade sequences

**Implementation note:** Required fixes to `search.py` and `simulation.py` to ensure consistent lexicographic ordering.

---

### 2.9 TestFourAgentHubAndSpokeStage1 (8 tests)

**Setup (TRUE 3-way tie):**
```
Center C:      (7,7), α=0.5, endowment=(6,6)
Peripheral A:  (2,7), α=0.5, endowment=(10,2)  [distance=5]
Peripheral B: (12,7), α=0.5, endowment=(10,2)  [distance=5]
Peripheral D:  (7,2), α=0.5, endowment=(10,2)  [distance=5]
```

All peripherals have identical preferences, endowments, and distance from center—a true 3-way tie.

**Hand-computed predictions:**
- Initial utilities: C=6.0, A=B=D=√20≈4.472
- All peripherals have identical Nash surplus with C ≈ 0.42
- Tie-break: C selects A (lexicographically smallest: p_a < p_b < p_d)
- After C-A trade: C≈(9.08, 4.54), A≈(6.92, 3.46)

**Tests:**
| Test | Verification |
|------|--------------|
| Initial utilities | C=6.0, peripherals=√20 |
| Equidistant | All peripherals at distance 5 |
| Identical surplus | All peripherals have same Nash surplus with C |
| Tie-break | Center selects p_a |
| First trade | Center trades with p_a |
| Allocations | Feasibility preserved, utilities increase |
| Unchanged | p_b and p_d unchanged after first trade |
| Remaining surplus | Surplus still exists with p_b, p_d |

---

### 2.10 TestFourAgentHubAndSpokeStage2 (3 tests)

**Purpose:** Test post-first-trade dynamics.

**State after Stage 1:**
- Center: ~(9.08, 4.54), MRS ≈ 0.5
- p_a: ~(6.92, 3.46), MRS ≈ 0.5
- p_b, p_d: (10, 2), MRS = 0.2

**Key insight:** Center and p_a have equilibrated with each other, but both still have gains from trade with p_b and p_d (different MRS).

**Tests:**
- `test_mrs_changed_after_first_trade`: Center/p_a MRS equal, differs from p_b/p_d
- `test_further_trades_occur`: Additional trades happen after first
- `test_p_b_and_p_d_eventually_trade`: Remaining peripherals participate

---

### 2.11 TestFourAgentHubAndSpokeStage3 (6 tests)

**Purpose:** Verify equilibrium properties after all trades complete.

**Key theoretical insight:** In bilateral exchange, zero bilateral surplus ≠ MRS equality.

The simulation reaches **bilateral exchange equilibrium** (no pair has positive Nash surplus), not **competitive equilibrium** (all MRS equal). This is economically correct—MRS equality requires a complete market (Walrasian auctioneer), not bilateral bargaining.

**Tests:**
| Test | Verification |
|------|--------------|
| MRS convergence | MRS variance decreases from initial state |
| Zero bilateral surplus | No pair has remaining gains from trade |
| Welfare improved | Total welfare increased |
| Feasibility | Total resources unchanged |
| Multiple trades | At least 2 trades occurred |
| Stasis | No trades after equilibrium |

---

### 2.12 TestMixedHubAndSpokeStage1 (14 tests)

**Setup (Asymmetric endowments):**
```
Center C:     (7,7), α=0.5, endowment=(6,6)   MRS=1.0
Peripheral A: (2,7), α=0.5, endowment=(10,2)  MRS=0.2
Peripheral B: (12,7), α=0.5, endowment=(10,2) MRS=0.2
Peripheral D: (7,2), α=0.5, endowment=(2,10)  MRS=5.0  ← DIFFERENT
```

Unlike the symmetric hub-and-spoke, D has **complementary endowment** to A and B.

**Hand-computed Nash surplus:**
| Pair | Surplus (each) | Notes |
|------|----------------|-------|
| A↔D, B↔D | 1.53 | Complementary endowments |
| C↔A, C↔B, C↔D | 0.42 | C is indifferent |
| A↔B | 0.0 | Identical types |

**Key insight:** A↔D surplus is 3.6x higher than C↔A. Despite C being at the spatial hub, A and D should find each other and trade first.

**Tests:**
| Phase | Tests | Verifications |
|-------|-------|---------------|
| Initial state | 3 | Utilities, MRS values, distances |
| Surplus ordering | 4 | A↔D >> C↔A, A↔B = 0, C indifferent |
| Target selection | 2 | A→D, D→A (tie-break to p_a) |
| First trade | 5 | A-D trade first, (6,6) allocations |

---

### 2.13 TestMixedHubAndSpokeStage2 (8 tests)

**State after A-D trade:**
```
A: (6, 6), MRS = 1.0, utility = 6.0
D: (6, 6), MRS = 1.0, utility = 6.0
C: (6, 6), MRS = 1.0, utility = 6.0 (unchanged)
B: (10, 2), MRS = 0.2, utility = √20 (unchanged)
```

**Key insight:** A, D, and C all now have identical (6, 6) bundles. They have NO gains from trading with each other. B is the ONLY remaining trade opportunity.

**Hand-computed surplus:**
- A↔C = A↔D = C↔D = 0 (identical bundles)
- A↔B = D↔B = C↔B ≈ 0.42 each

**Tests:**
| Test | Verification |
|------|--------------|
| Post-trade MRS | A, D have MRS=1 after trade |
| C unchanged | Still at (6,6) with MRS=1 |
| B unchanged | Still at (10,2) with MRS=0.2 |
| Zero internal surplus | A, D, C cannot trade with each other |
| Positive B surplus | All have ~0.42 surplus with B |
| B eventually trades | B's endowment changes |
| B in trade log | B appears in trade records |
| Welfare improves | Total welfare increases |

---

### 2.14 TestMixedHubAndSpokeStage3 (7 tests)

**Purpose:** Verify equilibrium properties after all trades complete.

**Tests:**
| Test | Verification |
|------|--------------|
| Zero bilateral surplus | No pair has remaining gains |
| Welfare improved | Total utility > initial + 2.0 |
| Feasibility | (28, 20) total preserved |
| Multiple trades | At least 2 trades occurred |
| All participated | All 4 agents traded |
| Stasis | No trades after equilibrium |
| MRS convergence | Variance decreased from (0.2, 1.0, 0.2, 5.0) |

---

## 3. Theoretical Grounding

All scenarios derive from canonical microeconomic theory:

| Concept | Source |
|---------|--------|
| Nash bargaining solution | O&R-B Ch 2, Kreps II Ch 23 |
| Rubinstein alternating offers | O&R-B Ch 3, Theorem 3.4 |
| Cobb-Douglas preferences | MWG Ch 3 |
| Pareto efficiency (MRS equality) | MWG Ch 16 |
| Individual rationality | O&R-B Ch 2 |
| Bilateral vs competitive equilibrium | MWG Ch 15-16 |

### 3.1 Bilateral vs Competitive Equilibrium

A key distinction discovered during 4-agent testing:

**Competitive equilibrium** (Walrasian): All agents face the same prices, trade optimally, markets clear. Result: MRS equal across all agents.

**Bilateral exchange equilibrium**: Agents trade pairwise via Nash bargaining until no pair has positive surplus. Result: Zero bilateral surplus for all pairs, but MRS may differ.

The simulation implements bilateral exchange. The correct equilibrium criterion is `compute_nash_surplus() ≈ 0` for all pairs, not MRS equality.

---

## 4. Future Test Coverage

### 4.1 High Priority

**Trading chain scenario:**
- 4 agents with α = 0.2, 0.4, 0.6, 0.8
- Linear spatial arrangement
- Tests preference heterogeneity effects on trade sequence

**Clustered pairs scenario:**
- Two pairs of nearby agents, far apart from each other
- Tests intra-cluster vs inter-cluster dynamics
- When do agents leave their cluster to trade with distant partners?

**Additional bargaining protocols:**
- Take-It-Or-Leave-It (TIOLI): Ultimatum game outcome
- Posted prices: Price-taking vs bilateral bargaining comparison
- Double auction: Multi-agent price discovery

### 4.2 Medium Priority

**Path dependence investigation:**
- Same agents, different initial positions
- Does final allocation depend on meeting order?
- Statistical comparison across random initializations

**Rubinstein protocol with 4+ agents:**
- Test proposer advantage in multi-agent settings
- How does first-mover advantage compound across trades?

**Numerical precision audit:**
- Investigate cases where small gains exist but Nash solver returns no trade
- Consider tightening tolerances in bargaining.py

**Information environments:**
- Private information scenarios (type ≠ observable type)
- Signaling and screening equilibria
- Compare agent perspective to omniscient view

### 4.3 Lower Priority

**N-agent scaling tests:**
- Verify equilibrium properties hold with 10, 50, 100 agents
- Test convergence speed to equilibrium
- Measure welfare efficiency relative to Walrasian benchmark

**Edge cases:**
- Agents with identical preferences and endowments (no gains from trade)
- Extreme preference parameters (α → 0 or α → 1)
- Very small or very large endowments

**Protocol comparison experiments:**
- Same scenario, different protocols: measure outcome differences
- Welfare comparison: which protocol captures more surplus?
- Distributional effects: who benefits from which protocol?

**Behavioral extensions:**
- Bounded rationality: agents with imperfect optimization
- Learning agents: RL or evolutionary dynamics
- Behavioral surplus calculation (non-Nash)

---

## 5. Running the Tests

```bash
# Run all theoretical scenario tests
uv run pytest tests/test_theoretical_scenarios.py -v

# Run specific test class
uv run pytest tests/test_theoretical_scenarios.py::TestRubinsteinProtocol -v

# Run with coverage
uv run pytest tests/test_theoretical_scenarios.py --cov=microecon.bargaining
```

---

**Document Version:** 1.2
**Last Updated:** 2026-01-01
**Changes:**
- v1.2: Added mixed hub-and-spoke scenario (3 test classes, 29 tests). Tests surplus ordering with asymmetric endowments - complementary pairs (A↔D) have 3.6x more surplus than balanced pairs (C↔A).
- v1.1: Added 4 new test classes (20 tests), bilateral vs competitive equilibrium discussion, updated future coverage priorities
