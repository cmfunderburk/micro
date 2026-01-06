# Visualization Issues Checklist

**Subsystem:** `visualization/app.py`, `visualization/replay.py`

---

## High

- [x] **V-1:** Perceived vs true visualization - data path ✅
  - Source: REVIEW_0.1.0 §3
  - Files: `logging/events.py`, `search.py`, `simulation.py`, `logging/logger.py`
  - Issue: Only true alpha logged, no data path for observed types
  - **Fix:** Added `observed_alpha` field to `TargetEvaluation` and `TargetEvaluationResult`.
    Search decisions now log the perceived alpha for each evaluated target.
    This enables "agent perspective mode" visualization (UI enhancement deferred).
  - **Test:** `test_observed_alpha_logged_in_search_decisions` in `test_information.py`

---

## Low (Maintainability)

- [ ] **V-2:** Monolithic app.py
  - Source: claude-alpha-review §7.1
  - Files: `visualization/app.py` (1,912 lines)
  - Suggested decomposition:
    - `colors.py` (alpha_to_color, lerp_color)
    - `proxies.py` (AgentProxy, TradeAnimation)
    - `rendering.py` (grid, agents, animations)
    - `controls.py` (play/pause, timeline)
    - `metrics.py` (welfare panel, stats)

- [ ] **V-3:** Hardcoded layout dimensions
  - Source: claude-alpha-review §7.2
  - Files: `visualization/app.py`
  - Issue: Fixed WINDOW_WIDTH/HEIGHT don't scale for different displays

---

## Session Notes

```
Session: 2026-01-05-b
Date: 2026-01-05
Issues addressed: V-1 (data path)
Notes:
- Added observed_alpha to TargetEvaluationResult (search.py) and TargetEvaluation (events.py)
- Updated simulation.py and logger.py to wire observed_alpha through
- Added test_observed_alpha_logged_in_search_decisions
- UI enhancement for "agent perspective mode" deferred (V-2/V-3 lower priority)
```
