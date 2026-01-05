# Logging & Analysis Issues Checklist

**Subsystem:** `logging/events.py`, `analysis/emergence.py`, `analysis/timeseries.py`, `scenarios/market_emergence.py`

---

## Critical

- [x] **LA-3:** Welfare efficiency calculation flawed
  - Source: claude-alpha-review §2.1
  - Files: `analysis/emergence.py:177-249`
  - Problems:
    1. Overcounting: sums ALL pairwise surpluses (agents trade once)
    2. Undercounting: uses `gains_1` only, not bilateral total
  - Impact: 13% efficiency ratios in comparative study may be misleading
  - **RESOLVED (2026-01-05):** Now uses greedy maximum weight matching with bilateral surplus. Test `test_greedy_matching_limits_pairs` verifies correct behavior.

---

## High

- [x] **LA-1:** Logging config missing institutional metadata
  - Source: REVIEW_0.1.0 §4
  - Files: `logging/events.py`, `batch.py`, `scenarios/market_emergence.py`, `visualization/browser.py`
  - Missing: matching protocol, info environment, noise_std
  - **RESOLVED (2026-01-05):** Added `matching_protocol_name`, `info_env_name`, `info_env_params` to `SimulationConfig`. Updated all config creation sites.

- [x] **LA-2:** MRS trend metric missing
  - Source: REVIEW_0.1.0 §5
  - Files: `analysis/timeseries.py`
  - Completion criteria expects MRS time-series
  - **RESOLVED (2026-01-05):** Added `mrs_over_time()` and `mrs_dispersion_over_time()` functions. Exported from analysis module.

---

## Low

- [x] **LA-4:** MarketEmergenceConfig lacks validation
  - Source: REVIEW_0.1.0 §9
  - Files: `scenarios/market_emergence.py`
  - Issue: Unknown endowment_types raises KeyError, not clear message
  - **RESOLVED (2026-01-05):** Added validation in `__post_init__` with `VALID_ENDOWMENT_TYPES`. Clear error messages for invalid or empty types.

---

## Session Notes

### Session 1: Logging & Analysis Cleanup
**Date:** 2026-01-05
**Issues addressed:** LA-3, LA-1, LA-2, LA-4

**Changes made:**
1. `analysis/emergence.py`: Fixed `compute_theoretical_max_gains()` to use greedy matching with bilateral surplus
2. `logging/events.py`: Added `matching_protocol_name`, `info_env_name`, `info_env_params` to `SimulationConfig`
3. `batch.py`: Added `_get_info_env_name()`, `_get_info_env_params()` helpers; updated config creation
4. `scenarios/market_emergence.py`: Updated config creation with institutional metadata; added endowment_types validation
5. `visualization/browser.py`: Updated config creation with institutional metadata
6. `analysis/timeseries.py`: Added `mrs_over_time()`, `mrs_dispersion_over_time()` functions
7. `analysis/__init__.py`: Exported new MRS functions
8. Tests: Added `test_greedy_matching_limits_pairs`, `test_mrs_over_time`, `test_mrs_dispersion_over_time`

**Verification:** All 73 tests pass (analysis, emergence, batch, logging)

---

## Summary

All logging & analysis issues (LA-1 through LA-4) are now resolved.
