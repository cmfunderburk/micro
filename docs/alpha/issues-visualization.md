# Visualization Issues Checklist

**Subsystem:** `visualization/app.py`, `visualization/replay.py`

---

## High

- [ ] **V-1:** Perceived vs true visualization missing
  - Source: REVIEW_0.1.0 §3
  - Files: `logging/events.py` (AgentSnapshot), `visualization/app.py`
  - Issue: Only true alpha logged, no data path for observed types
  - Blocked by: CE-1 (info env must affect behavior first)

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

_Use this space during work sessions:_

```
Session:
Date:
Issues addressed:
Notes:
```
