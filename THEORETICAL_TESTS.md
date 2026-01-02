# Theoretical Scenario Tests

**Status:** Reference document for theoretical validation
**Date:** 2026-01-01
**Purpose:** Document hand-verified economic scenarios that validate simulation correctness

---

## 1. Overview

The file `tests/test_theoretical_scenarios.py` contains scenarios simple enough to compute by hand, encoding expected economic outcomes as test assertions. These "theoretical unit tests" verify that simulation outcomes match analytically-derived predictions.

**Test count:** 48 tests across 7 test classes

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

## 3. Theoretical Grounding

All scenarios derive from canonical microeconomic theory:

| Concept | Source |
|---------|--------|
| Nash bargaining solution | O&R-B Ch 2, Kreps II Ch 23 |
| Rubinstein alternating offers | O&R-B Ch 3, Theorem 3.4 |
| Cobb-Douglas preferences | MWG Ch 3 |
| Pareto efficiency (MRS equality) | MWG Ch 16 |
| Individual rationality | O&R-B Ch 2 |

---

## 4. Future Test Coverage

### 4.1 High Priority

**Additional bargaining protocols:**
- Take-It-Or-Leave-It (TIOLI): Ultimatum game outcome
- Posted prices: Price-taking vs bilateral bargaining comparison
- Double auction: Multi-agent price discovery

**Information environments:**
- Private information scenarios (type ≠ observable type)
- Signaling and screening equilibria
- Compare agent perspective to omniscient view

### 4.2 Medium Priority

**N-agent scaling tests:**
- Verify equilibrium properties hold with 10, 50, 100 agents
- Test convergence speed to equilibrium
- Measure welfare efficiency relative to Walrasian benchmark

**Path dependence analysis:**
- Does final allocation depend on initial positions?
- How does meeting order affect outcomes?
- Statistical comparison across random initializations

**Edge cases:**
- Agents with identical preferences and endowments (no gains from trade)
- Extreme preference parameters (α → 0 or α → 1)
- Very small or very large endowments

### 4.3 Lower Priority

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

**Document Version:** 1.0
**Last Updated:** 2026-01-01
