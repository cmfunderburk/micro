# Logging & Analysis Issues Checklist

**Subsystem:** `logging/events.py`, `analysis/emergence.py`, `scenarios/market_emergence.py`

---

## Critical

- [ ] **LA-3:** Welfare efficiency calculation flawed
  - Source: claude-alpha-review §2.1
  - Files: `analysis/emergence.py:177-219`
  - Problems:
    1. Overcounting: sums ALL pairwise surpluses (agents trade once)
    2. Undercounting: uses `gains_1` only, not bilateral total
  - Impact: 13% efficiency ratios in comparative study may be misleading

---

## High

- [ ] **LA-1:** Logging config missing institutional metadata
  - Source: REVIEW_0.1.0 §4
  - Files: `logging/events.py`, `scenarios/market_emergence.py`
  - Missing: matching protocol, info environment, noise_std
  - Blocked by: CE-3 (reproducibility)

- [ ] **LA-2:** MRS trend metric missing
  - Source: REVIEW_0.1.0 §5
  - Files: `analysis/emergence.py`
  - Completion criteria expects MRS time-series

---

## Low

- [ ] **LA-4:** MarketEmergenceConfig lacks validation
  - Source: REVIEW_0.1.0 §9
  - Files: `scenarios/market_emergence.py`
  - Issue: Unknown endowment_types raises KeyError, not clear message

---

## Session Notes

_Use this space during work sessions:_

```
Session:
Date:
Issues addressed:
Notes:
```
