# Ralph Loop Startup: Web Frontend

Copy and paste the command below to start the ralph-loop.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest`
- [ ] On correct branch: `git checkout -b web-frontend` (or use existing branch)
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed: `docs/PRD-WEB-FRONTEND.json`
- [ ] Node.js 20+ installed: `node --version`

---

## Startup Prompt

```
/ralph-loop:ralph-loop "Execute docs/PRD-WEB-FRONTEND.json systematically.

This PRD builds a web frontend for the microecon simulation:
- Phase 1: Infrastructure (backend/, frontend/, WebSocket, REST endpoints)
- Phase 2: Grid & Controls (canvas rendering, play/pause/step/reset, metrics)
- Phase 3: Interaction (hover tooltips, click selection, agent details)
- Phase 4: Charts (welfare and trade count time-series with Recharts)
- Phase 5: Overlays (trails, perception radius, heatmap, trade connections)
- Phase 6: Trade Inspection (Edgeworth box modal)
- Phase 7: Network Panel (D3-force graph visualization)
- Phase 8: Configuration & Export (config modal, PNG/CSV/JSON export)

CONSTRAINTS:
- Existing 669 tests must continue to pass
- Use Canvas 2D for grid rendering (Pixi.js only if performance issues)
- Follow design sketches in the interview discussion
- Backend in backend/, frontend in frontend/
- Add fastapi, uvicorn, websockets as core dependencies

Track progress via git commits, update PRD status fields as features complete, write progress.txt updates." --max-iterations 20 --completion-promise "<promise>WEB-FRONTEND-COMPLETE</promise>"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume docs/PRD-WEB-FRONTEND.json execution.

Check current state:
1. Read progress.txt for last known state
2. Check PRD for feature passes values
3. Review recent git commits
4. Check what files exist in backend/ and frontend/

Continue from where execution stopped. Complete remaining features in order." --max-iterations 20 --completion-promise "<promise>WEB-FRONTEND-COMPLETE</promise>"
```

---

## Phase-Specific Prompts (if resuming at specific phase)

### Resume at Phase 2 (Grid & Controls)
```
/ralph-loop:ralph-loop "Continue docs/PRD-WEB-FRONTEND.json from Phase 2: Grid & Controls.

Phase 1 (Infrastructure) is complete. Now implement:
- Canvas grid rendering
- Agent rendering with alpha-based colors
- Play/Pause/Step/Reset buttons
- Speed slider
- Metrics panel
- Trade flash animations

Continue through remaining phases." --max-iterations 20 --completion-promise "<promise>WEB-FRONTEND-COMPLETE</promise>"
```

### Resume at Phase 4 (Charts)
```
/ralph-loop:ralph-loop "Continue docs/PRD-WEB-FRONTEND.json from Phase 4: Charts.

Phases 1-3 complete. Now implement:
- Welfare time-series chart (Recharts)
- Trade count time-series chart
- Chart synchronization with simulation

Continue through remaining phases." --max-iterations 20 --completion-promise "<promise>WEB-FRONTEND-COMPLETE</promise>"
```

### Resume at Phase 6 (Trade Inspection)
```
/ralph-loop:ralph-loop "Continue docs/PRD-WEB-FRONTEND.json from Phase 6: Trade Inspection.

Phases 1-5 complete. Now implement:
- Trade history tracking
- Edgeworth box modal
- Indifference curves rendering
- Contract curve rendering
- Trade details display

Continue through remaining phases." --max-iterations 20 --completion-promise "<promise>WEB-FRONTEND-COMPLETE</promise>"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/PRD-WEB-FRONTEND.json` | Full PRD specification |
| `docs/WEB-FRONTEND-EXPLORATION.md` | Vision and architecture decisions |
| `src/microecon/logging/events.py` | Data structures to serialize (TickRecord, etc.) |
| `src/microecon/simulation.py` | Simulation engine to wrap |
| `src/microecon/visualization/app.py` | DearPyGui reference implementation |

---

## Expected Outputs

### Phase 1: Infrastructure
- `backend/__init__.py`, `backend/__main__.py`, `backend/app.py`
- `backend/routes.py`, `backend/websocket.py`
- `frontend/` with Vite + React + TypeScript scaffold
- `frontend/src/hooks/useSimulationSocket.ts`
- `frontend/src/store/index.ts` (Zustand)
- `scripts/dev.sh` (convenience script)
- Updated `pyproject.toml` with fastapi, uvicorn, websockets

### Phase 2: Grid & Controls
- `frontend/src/components/Grid/GridCanvas.tsx`
- `frontend/src/components/Controls/ControlBar.tsx`
- `frontend/src/components/Metrics/MetricsPanel.tsx`

### Phase 3: Interaction
- Hover tooltip component
- Agent selection logic in store
- Agent details panel component

### Phase 4: Charts
- `frontend/src/components/Charts/WelfareChart.tsx`
- `frontend/src/components/Charts/TradeCountChart.tsx`

### Phase 5: Overlays
- Overlay toggle component
- Canvas overlay rendering functions

### Phase 6: Trade Inspection
- `frontend/src/components/Edgeworth/EdgeworthModal.tsx`
- Indifference curve calculation utilities

### Phase 7: Network Panel
- `frontend/src/components/Network/NetworkPanel.tsx`
- D3-force integration

### Phase 8: Configuration & Export
- `frontend/src/components/Config/ConfigModal.tsx`
- `backend/routes.py` config endpoints
- Export functionality

---

## Verification Commands

```bash
# Backend health check
python -m backend & sleep 2 && curl http://localhost:8000/api/health && kill %1

# Frontend builds
cd frontend && npm run build

# Full test suite still passes
uv run pytest

# Run both (development)
./scripts/dev.sh
```

---

## Success Criteria

1. **Latency**: <100ms from Python tick to rendered frame
2. **Correctness**: Agent positions match Python state exactly
3. **Stability**: No connection drops over 5-minute session
4. **Responsiveness**: UI remains responsive at 10+ ticks/second
5. **Feature parity**: All DearPyGui live-mode features available
