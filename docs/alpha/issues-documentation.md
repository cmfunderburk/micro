# Documentation Issues Checklist

**Subsystem:** `STATUS.md`, `CLAUDE.md`, `README.md`, `docs/comparative-study.md`

---

## Medium

- [ ] **D-1:** STATUS.md contradictions
  - Source: REVIEW_0.1.0 §7
  - Contradictions:
    - Claims "Search uses Nash surplus regardless of protocol" (false)
    - Claims "No configuration files" (YAML scenarios exist)
    - Says info regimes implemented (behavior ignores them)
  - Blocked by: CE-1 (wait for behavior changes before documenting)

---

## Low

- [ ] **D-2:** Python version mismatch
  - Source: claude-alpha-review §4.1
  - Files: `README.md`
  - Issue: README says 3.11+, pyproject.toml requires 3.12+
  - Fix: Update README to 3.12+

- [ ] **D-3:** CLAUDE.md outdated
  - Source: claude-alpha-review §4.4
  - Files: `CLAUDE.md`
  - Issue: "Next Development Directions" lists implemented items
  - Fix: Remove time-series charts, config files from future items

- [ ] **D-4:** STATUS.md file structure outdated
  - Source: claude-alpha-review §4.2
  - Files: `STATUS.md`
  - Missing modules:
    - `scenarios/`
    - `visualization/browser.py`
    - `visualization/timeseries.py`
    - `analysis/emergence.py`

---

## Session Notes

_Use this space during work sessions:_

```
Session:
Date:
Issues addressed:
Notes:
```
