# Testing Issues Checklist

**Subsystem:** Test suite, comparative study methodology

---

## Medium

- [ ] **T-1:** Integration tests don't validate info environment effects
  - Source: REVIEW_0.1.0 §8
  - Files: `tests/test_integration.py`, `tests/test_information.py`
  - Issue: Tests run NoisyAlphaInformation but don't assert behavioral differences
  - Blocked by: CE-1 (can't test effects that don't exist)

- [ ] **T-3:** Comparative study single-seed limitation
  - Source: claude-alpha-review §6.3, REVIEW_0.1.0 §2.2
  - Files: `docs/comparative-study.md`
  - Issue: Single seed (42), 30 agents, 80 ticks — not statistically rigorous
  - Blocked by: CE-3 (multi-seed meaningful only with determinism)
  - Recommended: 10+ seeds, 50+ agents, 200+ ticks, confidence intervals

---

## Trivial

- [ ] **T-2:** pytest.mark.slow unregistered
  - Source: claude-alpha-review §5.3
  - Files: `tests/test_edge_cases.py:249`, `pyproject.toml` or `pytest.ini`
  - Issue: `PytestUnknownMarkWarning`
  - Fix: Register mark in pytest config

---

## Session Notes

_Use this space during work sessions:_

```
Session:
Date:
Issues addressed:
Notes:
```
