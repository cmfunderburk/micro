# Ralph Loop Startup: Live Config Modal

Copy and paste the command below to start the ralph-loop.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest`
- [ ] On correct branch: `git branch`
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed and any edits made

---

## Startup Prompt

```
/ralph-loop:ralph-loop "Execute PRD-LIVE-CONFIG-MODAL.json systematically.

This PRD adds a configuration modal to Live Mode, exposing institutional parameters (bargaining/matching protocols) and search parameters (perception radius, discount factor).

IMPLEMENTATION ORDER:
1. CFG-001: Extend LaunchConfig dataclass with new fields
2. CFG-002: Create LiveConfigModal class in browser.py
3. CFG-003: Wire modal to StartupSelector (rename button, open modal)
4. CFG-004: Extend run_visualization() signature in app.py
5. CFG-005: Pass parameters through VisualizationApp to create_simple_economy()
6. CFG-006: Integration testing - full flow verification

KEY FILES:
- src/microecon/visualization/browser.py - StartupSelector, new LiveConfigModal
- src/microecon/visualization/app.py - run_visualization(), VisualizationApp

DESIGN REFERENCE (from PRD):
- Modal has 3 collapsible sections: Basic, Institutions, Search
- Button renamed to 'Configure Simulation...'
- Protocol radio buttons with friendly names
- Slider+input for float params (radius, discount)

Track progress via git commits. Update PRD passes fields as features complete." --max-iterations 10 --completion-promise "<promise>LIVE-CONFIG-MODAL-COMPLETE</promise>"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume PRD-LIVE-CONFIG-MODAL.json execution.

Check current state:
1. Read PRD for feature passes values
2. Review recent git commits
3. Check browser.py and app.py for partial implementation

Continue from where execution stopped." --max-iterations 10 --completion-promise "<promise>LIVE-CONFIG-MODAL-COMPLETE</promise>"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/ralph/PRD-LIVE-CONFIG-MODAL.json` | Full PRD specification |
| `src/microecon/visualization/browser.py` | StartupSelector, new LiveConfigModal class |
| `src/microecon/visualization/app.py` | run_visualization(), VisualizationApp |
| `src/microecon/simulation.py` | create_simple_economy() - already accepts all needed params |
| `VISUALIZATION.md` | Vision reference for configuration UI |

---

## Expected Outputs

**Phase 1 (all features):**
- Modified `browser.py`:
  - Extended `LaunchConfig` dataclass
  - New `LiveConfigModal` class (~150-200 lines)
  - Updated `StartupSelector._on_live_mode()` to open modal
  - Renamed button label
- Modified `app.py`:
  - Extended `run_visualization()` signature
  - Extended `VisualizationApp.__init__()` to accept and store new params
  - Updated `create_simple_economy()` calls to pass all params

**Verification:**
- Run `uv run python -m microecon.visualization`
- Click "Configure Simulation..."
- Modal opens with defaults
- Change bargaining to Rubinstein, click Start
- Verify simulation uses Rubinstein (different trade outcomes)
