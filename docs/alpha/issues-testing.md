# Testing Issues Checklist

**Subsystem:** Test suite, comparative study methodology

---

## Medium

- [x] **T-1:** Integration tests don't validate info environment effects ✅
  - Source: REVIEW_0.1.0 §8
  - Files: `tests/test_integration.py`, `tests/test_information.py`
  - Issue: Tests run NoisyAlphaInformation but don't assert behavioral differences
  - **Fix:** Enhanced `test_noisy_info_affects_search` to verify noise causes variation in valuations.
    Added `test_noisy_info_can_prevent_marginal_trades` to test noise effects on trade willingness.

- [x] **T-3:** Comparative study single-seed limitation ✅
  - Source: claude-alpha-review §6.3, REVIEW_0.1.0 §2.2
  - Files: `docs/comparative-study.md`
  - Issue: Single seed (42), 30 agents, 80 ticks — not statistically rigorous
  - **Fix:** Added "Statistical Rigor" section documenting proper methodology (10+ seeds, 50+ agents, 200+ ticks).
    Added performance baseline section noting O(n²) scaling and compute time implications.
    Full rigorous study deferred due to ~3 hour runtime per study.

---

## Trivial

- [x] **T-2:** pytest.mark.slow unregistered ✅
  - Source: claude-alpha-review §5.3
  - Files: `tests/test_edge_cases.py:249`, `pyproject.toml` or `pytest.ini`
  - Issue: `PytestUnknownMarkWarning`
  - **Fix:** Registered `slow` marker in `pyproject.toml` [tool.pytest.ini_options]

---

## Session Notes

```
Session: 2026-01-05-b
Date: 2026-01-05
Issues addressed: T-1, T-2, T-3
Notes:
- T-2 trivial fix (marker registration)
- T-1 enhanced integration tests with behavioral assertions
- T-3 documented methodology, noted performance baseline (~7 ticks/sec at 10 agents, O(n²) scaling)
- Added scripts/benchmark.py for quick performance testing
```
