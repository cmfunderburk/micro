# Core Engine Issues Checklist

**Subsystem:** `simulation.py`, `bargaining.py`, `search.py`, `matching.py`, `information.py`, `agent.py`, `grid.py`, `bundle.py`

---

## Critical

- [ ] **CE-1:** Information asymmetry does not affect behavior
  - Source: REVIEW_0.1.0 §1, §6
  - Files: `search.py`, `simulation.py`, `bargaining.py`
  - Unblocks: CE-2, T-1, V-1, D-1

- [x] **CE-3:** Reproducibility not guaranteed
  - Source: REVIEW_0.1.0 §2
  - Files: `simulation.py`, `agent.py`, `search.py`
  - Issues: global RNG for proposer selection, uuid-based agent IDs
  - Unblocks: LA-1, T-3
  - **RESOLVED (2026-01-05):** Added local RNG (`_rng`) to Simulation class, seeded in `create_simple_economy`. Agent IDs now deterministic (`agent_NNN` format). New `test_full_reproducibility` test verifies tick-by-tick determinism.

---

## Medium

- [ ] **CE-2:** Self-observation applies noise incorrectly
  - Source: REVIEW_0.1.0 §6
  - Files: `search.py`, `information.py`
  - Blocked by: CE-1

- [ ] **CE-4:** Distance metric inconsistency
  - Source: claude-alpha-review §3.1
  - Files: `grid.py`, `search.py`, `simulation.py`
  - Note: Euclidean for perception, Chebyshev for movement

- [ ] **CE-5:** Wrapped grid Chebyshev missing
  - Source: claude-alpha-review §3.3
  - Files: `grid.py`
  - Related to: CE-4

---

## Low (Cleanup)

- [ ] **CE-6:** Dead Rubinstein code
  - Source: claude-alpha-review §2.2
  - Files: `bargaining.py:628-723`
  - Action: Remove `_solve_rubinstein_allocation()`, update `proposer` docstrings

- [ ] **CE-7:** Legacy execute_trade function
  - Source: claude-alpha-review §3.4
  - Files: `bargaining.py:763-791`
  - Action: Deprecate or remove

- [ ] **CE-8:** Unsafe Bundle construction
  - Source: claude-alpha-review §3.2
  - Files: `bundle.py:44-50`
  - Action: Consider type-safe alternative (future)

---

## Session Notes

### Session 1: Reproducibility Fix
**Date:** 2026-01-05
**Issues addressed:** CE-3

**Changes made:**
1. `simulation.py`: Added `_rng: Random` field to `Simulation` dataclass
2. `simulation.py`: Changed `add_agent_random()` to use `self._rng.randint()` instead of global `random.randint()`
3. `simulation.py`: Changed proposer selection to use `self._rng.choice()` instead of global `random.choice()`
4. `simulation.py`: Updated `create_simple_economy()` to create seeded `Random(seed)` instance and pass to Simulation
5. `agent.py`: Added optional `agent_id` parameter to `create_agent()` for explicit ID assignment
6. `simulation.py`: Generate deterministic agent IDs (`agent_000`, `agent_001`, etc.) in `create_simple_economy()`
7. `tests/test_simulation.py`: Added `test_full_reproducibility()` that verifies agent IDs, trade events, and positions match across runs

**Verification:** All 38 related tests pass (simulation, batch, search)
