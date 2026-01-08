# Code Review: TypeScript Frontend Migration + Visualization Alignment

Scope
- Focused on `frontend/`, `server/`, `scripts/dev.sh`, `README.md`, `VISION.md`, `VISUALIZATION.md`.
- Archived Python UI at `.archived/visualization-dearpygui/` was not reviewed; call out if it should be.

Executive Summary
- The TS frontend is functional and feature-rich, but there are concurrency issues in the WebSocket loop, state-reset mismatches, and config synchronization gaps that can cause incorrect simulation behavior or stale UI.
- The current docs still describe a DearPyGui standalone visualization and explicitly call out "no web deployment," which conflicts with the new frontend direction.

Findings (ordered by severity)

Critical
- Concurrent WebSocket clients can start overlapping simulation loops on the shared manager, leading to double-stepping and race conditions. (`server/websocket.py:47`, `server/websocket.py:98`)

High
- Reset messages do not clear UI history/trade connections/trails, so charts and overlays keep stale state after reset or config change. (`frontend/src/hooks/useSimulationSocket.ts:59`, `frontend/src/store/index.ts:166`)
- Config changes go through REST only and are not broadcast to other connected clients; `running` state and config can desync across sessions. (`frontend/src/components/Config/ConfigModal.tsx:61`, `server/routes.py:87`, `server/websocket.py:98`)

Medium
- Dev script still runs `python -m backend`, but the entry point is `server`, so local dev startup fails. (`scripts/dev.sh:32`, `server/__main__.py:1`)
- PNG export uses `document.querySelector('canvas')`, which can export the wrong canvas when modals are open or multiple canvases exist. (`frontend/src/components/Config/ExportMenu.tsx:18`)
- Overlay toggles include non-functional options (`heatmap`) and defaults do not match “off-by-default” intent from VISUALIZATION. (`frontend/src/components/Controls/OverlayToggles.tsx:11`, `frontend/src/store/index.ts:148`, `frontend/src/components/Grid/GridCanvas.tsx:230`)

Low
- Agent B’s trade delta is derived by negating A’s delta; this can be wrong if allocations are not perfectly symmetric or rounding drifts. (`frontend/src/components/TradeInspection/EdgeworthModal.tsx:145`)
- Trade network fully rebuilds D3 state every update; this causes jitter and unnecessary work on each tick. (`frontend/src/components/Network/TradeNetwork.tsx:101`)
- Trade connections accumulate without pruning; long runs can grow memory and clutter. (`frontend/src/store/index.ts:186`)
- `use_beliefs` exists in config but has no UI control to toggle it. (`frontend/src/components/Config/ConfigModal.tsx:16`)

Alignment Check vs VISION.md
- Aligned: visualization-first emphasis is present; key metrics and trade inspection are prioritized. (`VISION.md:71`, `frontend/src/App.tsx:168`)
- Gaps: README still centers the old Python visualization and doesn’t mention the new TS frontend path. (`README.md:18`)

Alignment Check vs VISUALIZATION.md
- Major divergence: VISUALIZATION specifies a DearPyGui standalone app and explicitly lists web deployment as out-of-scope, which conflicts with the new React/Vite frontend. (`VISUALIZATION.md:315`, `VISUALIZATION.md:370`)
- Missing features called out in VISUALIZATION: replay mode, benchmark overlays (Nash comparison), vector/animation exports, richer aggregate metrics (e.g., Gini, trade volume), keyboard controls, and pan/zoom on grid. (`VISUALIZATION.md:142`, `VISUALIZATION.md:243`, `VISUALIZATION.md:263`)
- Terminology mismatch: default UI uses α directly instead of plain-language labels; tooltips are always technical. (`VISUALIZATION.md:299`, `frontend/src/components/Grid/AgentTooltip.tsx:21`)
- Overlays: VISUALIZATION suggests minimal-by-default with “perception radii/heatmap/trade networks” as future overlays; current UI ships them as toggles (and perception is default-on). (`VISUALIZATION.md:102`, `frontend/src/store/index.ts:148`)
- Agent color encoding: VISUALIZATION expects goods-based color mixing; UI uses α gradient. (`VISUALIZATION.md:55`, `frontend/src/components/Grid/GridCanvas.tsx:21`)

Open Questions
- Is the web frontend now the canonical visualization stack, and should `VISUALIZATION.md` be rewritten to match?
- Should each WebSocket client have its own simulation instance or share a single global simulation?
- Should config changes be driven via WebSocket commands (with broadcast) instead of REST?
- On reset/config change, should UI history/trade connections be cleared or preserved for comparison?
- Should the archived Python UI remain as a reference, or be deprecated formally in docs?

Suggested Next Steps
- Fix concurrency and state sync in the WebSocket layer (single loop, broadcast state, consistent reset semantics).
- Align docs and dev tooling: update `README.md`, `VISUALIZATION.md`, and `scripts/dev.sh` to reflect the new TS frontend.
- Close UI gaps: reset clears history, export targets the grid canvas explicitly, and remove/implement placeholder overlays.
- Decide on “plain-language by default” vs “technical by default” terminology in tooltips and panels.

Testing Notes
- No tests run during this review.

