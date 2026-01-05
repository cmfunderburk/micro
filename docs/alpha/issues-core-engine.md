# Core Engine Issues Checklist

**Subsystem:** `simulation.py`, `bargaining.py`, `search.py`, `matching.py`, `information.py`, `agent.py`, `grid.py`, `bundle.py`

---

## Critical

- [x] **CE-1:** Information asymmetry does not affect behavior
  - Source: REVIEW_0.1.0 §1, §6
  - Files: `search.py`, `simulation.py`, `bargaining.py`
  - Unblocks: CE-2, T-1, V-1, D-1
  - **RESOLVED (2026-01-05):** Search now uses observed types from info_env for targets. Agents evaluate potential trades based on beliefs (observed types), not true types. Test `test_noise_causes_different_target_valuations` verifies behavioral impact.

- [x] **CE-3:** Reproducibility not guaranteed
  - Source: REVIEW_0.1.0 §2
  - Files: `simulation.py`, `agent.py`, `search.py`
  - Issues: global RNG for proposer selection, uuid-based agent IDs
  - Unblocks: LA-1, T-3
  - **RESOLVED (2026-01-05):** Added local RNG (`_rng`) to Simulation class, seeded in `create_simple_economy`. Agent IDs now deterministic (`agent_NNN` format). New `test_full_reproducibility` test verifies tick-by-tick determinism.

---

## Medium

- [x] **CE-2:** Self-observation applies noise incorrectly
  - Source: REVIEW_0.1.0 §6
  - Files: `search.py`, `information.py`
  - Blocked by: CE-1
  - **RESOLVED (2026-01-05):** Observers now use `AgentType.from_private_state()` for their own type (true preferences) and `info_env.get_observable_type()` only for targets. Test `test_observer_knows_own_type` verifies this.

- [x] **CE-4:** Distance metric inconsistency
  - Source: claude-alpha-review §3.1
  - Files: `grid.py`, `search.py`, `simulation.py`
  - Note: Euclidean for perception, Chebyshev for movement
  - **RESOLVED (2026-01-05):** `agents_within_radius` now uses Chebyshev distance, consistent with movement. Perception area is now square (Chebyshev) rather than circular (Euclidean). Tests verify agents reachable in N steps are visible at radius N.

- [x] **CE-5:** Wrapped grid Chebyshev missing
  - Source: claude-alpha-review §3.3
  - Files: `grid.py`
  - Related to: CE-4
  - **RESOLVED (2026-01-05):** `Position.chebyshev_distance_to()` now accepts optional `grid_size` parameter for wrapped distance. `Grid.chebyshev_distance()` method added as convenience wrapper. Search and simulation now use wrapped Chebyshev on torus grids.

---

## Low (Cleanup)

- [x] **CE-6:** Dead Rubinstein code
  - Source: claude-alpha-review §2.2
  - Files: `bargaining.py:628-723`
  - Action: Remove `_solve_rubinstein_allocation()`, update `proposer` docstrings
  - **RESOLVED (2026-01-05):** Removed `_solve_rubinstein_allocation()` (~96 lines). Function was dead code - never called after BRW formulation was implemented.

- [x] **CE-7:** Legacy execute_trade function
  - Source: claude-alpha-review §3.4
  - Files: `bargaining.py:763-791`
  - Action: Deprecate or remove
  - **RESOLVED (2026-01-05):** Removed `execute_trade()` function and associated tests. Was unused - simulation uses `BargainingProtocol.execute()` instead.

- [x] **CE-8:** Unsafe Bundle construction
  - Source: claude-alpha-review §3.2
  - Files: `bundle.py:44-50`
  - Action: Consider type-safe alternative (future)
  - **RESOLVED (2026-01-05):** Removed `__sub__` and `_unsafe_init` entirely. Methods were unused throughout codebase. If bundle subtraction is needed in future, design proper solution (e.g., separate Transfer type).

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

### Session 2: Information Environment Fix
**Date:** 2026-01-05
**Issues addressed:** CE-1, CE-2

**Problem:** Search behavior ignored information environment. When using `NoisyAlphaInformation`, agents still made decisions based on true types rather than observed (noisy) types.

**Root causes:**
1. `evaluate_targets()` called `info_env.get_observable_type(agent)` for the observer, applying noise to own alpha
2. When `bargaining_protocol` was provided, `compute_expected_surplus(agent, target)` used true `Agent` objects instead of observed types

**Changes made:**
1. `search.py`: Observer now uses `AgentType.from_private_state()` for own type (no noise on self)
2. `search.py`: Target evaluation always uses `info_env.get_observable_type(target)` for observed type
3. `search.py`: Removed branching on `bargaining_protocol` - always use Nash surplus with beliefs for search
4. `search.py`: Updated `should_trade()` to use true self-type + observed other-type for both agents
5. `tests/test_information.py`: Added `test_noise_causes_different_target_valuations` (CE-1 regression test)
6. `tests/test_information.py`: Added `test_observer_knows_own_type` (CE-2 regression test)

**Verification:** All 53 tests pass (information, search, simulation, integration)

### Session 3: Distance Metric Consistency
**Date:** 2026-01-05
**Issues addressed:** CE-4, CE-5

**Problem:** Perception radius used Euclidean distance while movement uses Chebyshev. This meant agents could miss nearby targets that were close in movement terms but far in Euclidean terms (e.g., diagonal positions).

**Changes made:**
1. `grid.py`: Added `grid_size` parameter to `Position.chebyshev_distance_to()` for wrapped distance
2. `grid.py`: Added `Grid.chebyshev_distance()` convenience method
3. `grid.py`: Changed `agents_within_radius()` to use Chebyshev distance instead of Euclidean
4. `search.py`: Updated `evaluate_targets()` and `evaluate_targets_detailed()` to use `grid.chebyshev_distance()` for ticks-to-reach calculation
5. `simulation.py`: Updated `_maintain_commitments()` to use `grid.chebyshev_distance()` for perception checks
6. `tests/test_grid.py`: Added 4 new tests:
   - `test_chebyshev_distance`: Basic Chebyshev on Grid
   - `test_wrapped_chebyshev_distance`: Wrapped Chebyshev on torus
   - `test_agents_within_radius_uses_chebyshev`: Regression test for CE-4
   - `test_perception_movement_consistency`: Verifies perception matches movement

**Verification:** All 68 tests pass (grid, search, simulation, information)

### Session 4: Dead Code Removal
**Date:** 2026-01-05
**Issues addressed:** CE-6, CE-7, CE-8

**Changes made:**
1. `bargaining.py`: Removed `_solve_rubinstein_allocation()` (~96 lines of dead code)
2. `bargaining.py`: Removed `execute_trade()` function (~30 lines)
3. `simulation.py`: Removed unused `execute_trade` import
4. `tests/test_bargaining.py`: Removed `TestExecuteTrade` class and import
5. `bundle.py`: Removed `__sub__` and `_unsafe_init` methods (~12 lines)

**Verification:** All tests pass (bundle, bargaining, simulation, search, matching, information)

---

## Summary

All core engine issues (CE-1 through CE-8) are now resolved. The core engine is clean and ready for further development.
