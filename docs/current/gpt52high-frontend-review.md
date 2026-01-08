# PR Review: Web Frontend Exploration

## Findings (ordered by severity)

### High
- `frontend/src/hooks/useSimulationSocket.ts:72-84`: Tick messages overwrite the full `SimulationConfig` with a `{ grid_size }` fragment. The backend only includes `grid_size` in tick payloads, so `setConfig(data.config)` clobbers required fields (e.g., `n_agents`, `perception_radius`). This breaks config-dependent UI (Config modal defaults, export metadata, comparison defaults) after the first tick. Consider only setting config on `init`/`reset`/`config` messages or merging with the existing config when `data.type === 'tick'`.
- `frontend/src/components/Config/ConfigModal.tsx:61-75` + `server/routes.py:91-105`: The modal posts to `/api/config`, which resets the server simulation without broadcasting a `config/reset` WebSocket event. Other connected clients are never notified, and the local client only resets because the modal manually calls `reset()`. The WebSocket loop keeps running with the new sim, so history/overlays can desync. Prefer sending the WebSocket `config` command (so it uses `ConnectionManager.update_config`) or have the REST endpoint coordinate with the WebSocket manager and broadcast reset/config events.

### Medium
- `server/routes.py:50-55` + `server/simulation_manager.py:461-484`: `/api/state` declares `StateResponse` with `config` and `tick_data`, but `manager.get_state()` returns a different shape in comparison mode (`simulations` list). This will raise a Pydantic validation error whenever comparison mode is active, making the endpoint unreliable for monitoring/debugging. Consider a union response model or a separate comparison endpoint.
- `server/routes.py:174-190`: `/api/runs/{run_name}` uses `run_name` directly in a filesystem path. A crafted `run_name` containing `../` can escape `RUNS_DIR` and read any directory with `config.json` and `ticks.jsonl`. Add a path normalization check (e.g., resolve and ensure the path stays under `RUNS_DIR`) or restrict `run_name` to a single path segment.

### Low
- `frontend/src/components/Replay/ReplayView.tsx:31-35`: Replay grid size is derived from current agent positions rather than the run’s configured grid size. If agents never occupy the max row/col, the replay grid shrinks and positions render at the wrong scale. Use the loaded run’s `config.grid_size` instead.
- `frontend/src/hooks/useSimulationSocket.ts:51-60`: The reconnect timer always schedules on `onclose`, even when the component intentionally disconnects. This can spawn zombie reconnects after unmount. Add a `shouldReconnect` flag or clear `onclose` before closing to avoid background reconnections.

## Questions / Assumptions
- Is `/api/config` intended to be a primary control path for the UI, or should all runtime config changes route through the WebSocket command path?
- Are replay run directories considered fully trusted and only local? If not, the `/runs/{run_name}` path traversal needs tightening.

## Change Summary
- Adds a new Vite/React frontend with comparison, replay, network, and inspection tooling, plus a FastAPI backend and WebSocket streaming. The legacy visualization package is removed, and the Python package layout is flattened.

## Testing Gaps
- No automated coverage for WebSocket config/reset flows or comparison mode API shapes. Consider integration tests that exercise `config` updates and comparison mode state via `/api/state` and the WebSocket stream.
