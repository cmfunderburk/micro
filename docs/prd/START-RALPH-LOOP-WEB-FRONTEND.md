# Ralph Loop Startup: Web Frontend Feature Parity

Copy and paste the prompt below to start the ralph-loop.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest`
- [ ] On correct branch: `git branch` (should be `web-frontend-exploration` or new feature branch)
- [ ] Working directory clean: `git status`
- [ ] Server starts: `uv run uvicorn server.app:create_app --factory --port 8000`
- [ ] Frontend starts: `cd frontend && npm run dev`
- [ ] PRD reviewed: `docs/prd/PRD-WEB-FRONTEND-PARITY.json`

---

## Startup Prompt

```
/ralph-loop:ralph-loop "Execute docs/prd/PRD-WEB-FRONTEND-PARITY.json systematically.

This PRD fixes critical bugs and brings the web frontend to feature parity with the archived Python/DearPyGui implementation.

PHASE ORDER:
1. Critical Fixes - WebSocket concurrency, reset semantics, config broadcast, dev script
2. Core Polish - PNG export, overlay defaults, trade network stability
3. Belief System - Panel, connections overlay, use_beliefs toggle
4. Perspective Mode - Agent selector, toggle, ground truth
5. Comparison Mode - Multi-sim server, dual grid, sync controls
6. Replay Mode - Load runs, timeline seeking, step-back
7. Finishing - Trade animation, scenario browser, keyboard shortcuts

KEY DECISIONS (from ADRs):
- WebSocket: Session-based simulation ownership (client can create multiple sims)
- Replay: Client-side preload (load full RunData, seek locally)
- Reset: Clears all UI state (history, trails, connections)

REFERENCE: docs/FEATURE-PARITY-REFERENCE.md has full Python feature inventory

Track progress via git commits. Continue through phases automatically (HOTL mode)." --max-iterations 20 --completion-promise "<promise>WEB-FRONTEND-PARITY-COMPLETE</promise>"
```

---

## Resume Prompt (if interrupted)

```
/ralph-loop:ralph-loop "Resume docs/prd/PRD-WEB-FRONTEND-PARITY.json execution.

Check current state:
1. Read PRD for feature passes values
2. Review recent git commits
3. Check which phase was in progress

Continue from where execution stopped. HOTL mode - continue through phases automatically." --max-iterations 20 --completion-promise "<promise>WEB-FRONTEND-PARITY-COMPLETE</promise>"
```

---

## Phase-Specific Prompts (if needed)

### Phase 1 Only: Critical Fixes
```
/ralph-loop:ralph-loop "Execute Phase 1 of docs/prd/PRD-WEB-FRONTEND-PARITY.json.

Focus on: FIX-001 (WebSocket concurrency), FIX-002 (reset clears UI), FIX-003 (config broadcast), FIX-004 (dev script).

Stop after Phase 1 complete." --max-iterations 10 --completion-promise "<promise>WEB-FRONTEND-PARITY-PHASE-1-COMPLETE</promise>"
```

### Phase 5 Only: Comparison Mode
```
/ralph-loop:ralph-loop "Execute Phase 5 of docs/prd/PRD-WEB-FRONTEND-PARITY.json.

Focus on: FEAT-007 (multi-sim server), FEAT-008 (dual grid), FEAT-009 (sync controls), FEAT-010 (comparison charts).

ADR-001 specifies session-based simulation ownership architecture.

Stop after Phase 5 complete." --max-iterations 10 --completion-promise "<promise>WEB-FRONTEND-PARITY-PHASE-5-COMPLETE</promise>"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/prd/PRD-WEB-FRONTEND-PARITY.json` | Full PRD specification |
| `docs/FEATURE-PARITY-REFERENCE.md` | Python feature inventory & gap analysis |
| `CODE_REVIEW_TS_FRONTEND_MIGRATION.md` | Original code review findings |
| `server/websocket.py` | WebSocket handlers (Phase 1, 5) |
| `server/simulation_manager.py` | Simulation lifecycle (Phase 1, 5) |
| `frontend/src/store/index.ts` | Zustand state management |
| `frontend/src/hooks/useSimulationSocket.ts` | WebSocket client hook |
| `.archived/visualization-dearpygui/` | Reference Python implementation |

---

## Expected Outputs by Phase

**Phase 1: Critical Fixes**
- Fixed `server/websocket.py` - no race conditions
- Fixed `frontend/src/store/index.ts` - reset clears state
- Fixed `server/routes.py` - config broadcasts
- Fixed `scripts/dev.sh` - correct entry point

**Phase 2: Core Polish**
- Fixed `frontend/src/components/Config/ExportMenu.tsx` - targets grid canvas
- Fixed overlay defaults in store
- Stable trade network rendering

**Phase 3: Belief System**
- New `frontend/src/components/Beliefs/BeliefPanel.tsx`
- Belief connections overlay in GridCanvas
- use_beliefs toggle in ConfigModal

**Phase 4: Perspective Mode**
- New `frontend/src/components/Controls/PerspectiveMode.tsx`
- Perspective rendering in GridCanvas

**Phase 5: Comparison Mode**
- Updated `server/simulation_manager.py` - multi-sim support
- New `frontend/src/components/Comparison/` directory
- Dual grid layout, sync controls, comparison charts

**Phase 6: Replay Mode**
- New replay loading endpoint in server
- New `frontend/src/components/Replay/` directory
- Timeline slider, step-back button

**Phase 7: Finishing**
- Trade animation component
- Scenario browser component
- Keyboard shortcuts hook

---

## Verification Commands

```bash
# Run existing tests (should pass throughout)
uv run pytest

# Manual verification - open two browser tabs
# 1. Both should show same simulation state
# 2. Config change in one should reflect in other
# 3. Reset should clear charts in both

# Start servers for manual testing
uv run uvicorn server.app:create_app --factory --port 8000 &
cd frontend && npm run dev
```
