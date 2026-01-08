# Ralph Loop Startup: Layout Refactor

Copy and paste the command below to start the ralph-loop.

---

## Pre-flight Checklist

Before starting:
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Backend runs: `uv run python -m backend`
- [ ] On correct branch: `git branch` (web-frontend-exploration)
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed: `docs/PRD-LAYOUT-REFACTOR.json`

---

## Startup Prompt

```
/ralph-loop:ralph-loop "Execute docs/PRD-LAYOUT-REFACTOR.json systematically.

This PRD refactors the web frontend layout:
- FEAT-001: Three-column grid structure (grid | info | charts)
- FEAT-002: Responsive square grid canvas with max size
- FEAT-003: Controls moved to header
- FEAT-004: Compact metrics display
- FEAT-005: Charts in right column
- FEAT-006: Trade History as modal
- FEAT-007: Remove Selected Agent panel (use tooltip)

CONSTRAINTS:
- Desktop-only, minimum viewport 1280x800
- All existing functionality must be preserved
- No scrolling required at target viewport sizes
- Maintain dark theme styling

Test visually at 1280px, 1600px, 1920px widths.
Track progress via git commits and update PRD status fields." --max-iterations 25 --completion-promise "<promise>LAYOUT-REFACTOR-COMPLETE</promise>"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume docs/PRD-LAYOUT-REFACTOR.json execution.

Check current state:
1. Read PRD for feature pass status
2. Review recent git commits
3. Check frontend builds

Continue from where execution stopped." --max-iterations 20 --completion-promise "<promise>LAYOUT-REFACTOR-COMPLETE</promise>"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/PRD-LAYOUT-REFACTOR.json` | Full PRD specification |
| `frontend/src/App.tsx` | Main layout component (primary file to modify) |
| `frontend/src/components/Grid/GridCanvas.tsx` | Grid canvas sizing |
| `frontend/src/components/Charts/*.tsx` | Chart components |
| `frontend/src/components/TradeInspection/TradeHistoryPanel.tsx` | Trade history (convert to modal) |

---

## Expected Outputs

**Layout Changes:**
- `App.tsx` restructured with three-column layout
- `GridCanvas.tsx` updated for responsive sizing
- Trade History moved to modal pattern
- Controls relocated to header

**Visual Result:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Microecon Simulation      [▶][▶▶][↺] [====Speed====] 1.0x    ● Connect │
├───────────────────────┬─────────────────────┬───────────────────────────┤
│                       │  Tick: 28           │  Welfare                  │
│                       │  Trades: 30         │  ┌─────────────────────┐  │
│                       │  Welfare: 64.63     │  │~~~~~/‾‾‾‾‾          │  │
│   ┌───────────────┐   │  Gains: +20.27      │  └─────────────────────┘  │
│   │               │   ├─────────────────────┤                           │
│   │  Grid Canvas  │   │  Overlays           │  Trades                   │
│   │   (square)    │   │  ○ Trails           │  ┌─────────────────────┐  │
│   │               │   │  ● Perception       │  │   ___/‾‾‾           │  │
│   └───────────────┘   │  ○ Heatmap          │  └─────────────────────┘  │
│                       │  ○ Connections      │                           │
│                       │                     │  [Network] [History]      │
└───────────────────────┴─────────────────────┴───────────────────────────┘
```

---

## Verification

After completion:
1. Open http://localhost:5173 at different viewport sizes
2. Verify no scrolling needed at 1280x800
3. Test all controls (play/pause/step/reset/speed)
4. Test overlays toggle
5. Test Network panel opens
6. Test Trade History modal opens
7. Test Edgeworth box modal from trade history
8. Verify hover tooltips work on agents
