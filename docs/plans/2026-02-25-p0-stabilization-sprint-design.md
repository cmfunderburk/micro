# P0 Stabilization Sprint Design

**Date:** 2026-02-25
**Scope:** Issues A-001 through A-007 from Vision Workflow Execution Board
**Upstream:** `docs/VISION/VISION-WORKFLOW-EXECUTION-BOARD.md`
**Branch:** `fundamentals`

---

## Context

The P0 stabilization sprint resolves correctness bugs and quality gaps that block Gate A (Foundation Coherence). All seven issues are preconditions for the contract, schema, and modularity work that follows.

**Current state:** 716 tests passing, 15 skipped. Frontend lint has 5 errors, 2 warnings. Replay endpoint broken against current log schema. Batch runner records info_env metadata but ignores it at runtime. Proposer ID hardcoded in trade logging.

---

## Execution Order

Dependency-ordered, bottom-up from the data model:

1. **A-005** — Batch RNG isolation (standalone, no deps)
2. **A-003 + A-006** — Unified TradeEvent + proposer fix (core data model)
3. **A-002** — Batch info_env execution correctness (independent of TradeEvent)
4. **A-001** — Replay loader schema fix (needs stable TradeEvent shape)
5. **A-007** — Information-regime product surface (builds on A-002)
6. **A-004** — Frontend lint cleanup (last, after A-007 frontend changes)

---

## Issue Designs

### A-005: Batch RNG Isolation

**Problem:** `batch.py:133` calls `random.seed(seed)`, mutating global Python RNG state.

**Fix:** Delete the `random.seed(seed)` call. `create_simple_economy` already creates a per-instance `Random(seed)` at `simulation.py:853`. The global call is redundant and harmful.

**Test:** Assert `random.getstate()` is unchanged after a batch run.

**Files:** `microecon/batch.py`

---

### A-003 + A-006: Unified TradeEvent and Proposer Fix

**Problem:** Two incompatible `TradeEvent` classes connected by an ad-hoc tuple transform that hardcodes `proposer_id = agent1_id`.

- Runtime `TradeEvent` (`simulation.py:51-59`): stores `outcome: BargainingOutcome`, no proposer
- Logging `TradeEvent` (`logging/events.py:216-256`): stores flat fields including `proposer_id`
- Transform (`simulation.py:617-635`): manual tuple destruction, hardcodes proposer

**Design decision:** Unify to one canonical `TradeEvent`. The logging version (`events.py`) becomes the single model.

**Changes:**

1. Delete runtime `TradeEvent` from `simulation.py:51-59`
2. Import `TradeEvent` from `microecon.logging.events` into `simulation.py`
3. In `_execute_trade` (~line 578-589), build canonical `TradeEvent` directly:
   ```python
   event = TradeEvent(
       agent1_id=agent1.id,
       agent2_id=agent2.id,
       proposer_id=proposer.id,
       pre_holdings=(pre_holdings1, pre_holdings2),
       post_allocations=(
           (outcome.allocation_1.x, outcome.allocation_1.y),
           (outcome.allocation_2.x, outcome.allocation_2.y),
       ),
       utilities=(outcome.utility_1, outcome.utility_2),
       gains=(outcome.gains_1, outcome.gains_2),
       trade_occurred=outcome.trade_occurred,
   )
   ```
4. Delete `_build_trade_events_data` entirely
5. Update `_log_tick` to accept `TradeEvent` objects directly instead of destructured tuples
6. Update `Simulation.trades` type annotation
7. Update any downstream code accessing old field names (`event.outcome`, `event.pre_holdings_1`, etc.)
8. Keep local `outcome` variable in `_execute_trade` for belief updates (doesn't need to come from the event)

**Impact radius:** `simulation.py` (primary), `_log_tick` call sites, any test fixtures that construct old `TradeEvent`.

**Tests:**
- Deterministic test comparing logged `proposer_id` against actual proposer selected by bargaining protocol
- Existing test suite must remain green (field access updates)

**Files:** `microecon/simulation.py`, `microecon/logging/events.py` (no changes needed — it's already the target shape)

---

### A-002: Batch info_env Execution Correctness

**Problem:** `BatchRunner._create_simulation` (`batch.py:119-142`) ignores `info_env` in config dict. Uses `create_simple_economy` which hardcodes `FullInformation()`.

**Fix:**
1. Add `info_env` parameter to `create_simple_economy` (default: `FullInformation()`)
2. In `BatchRunner._create_simulation`, extract `info_env` from config and pass through
3. Metadata logging (`_config_to_simulation_config`) already handles it correctly

**Test:** Batch run configured with `NoisyAlphaInformation` — assert `sim.info_env` type matches config.

**Files:** `microecon/simulation.py` (`create_simple_economy` signature), `microecon/batch.py` (`_create_simulation`)

---

### A-001: Replay Loader Schema Mismatch

**Problem:** `server/routes.py:216-252` references field names that don't exist in `AgentSnapshot.to_dict()` or `TradeEvent.to_dict()` output.

**Specific mismatches:**

| Route code expects | Actual serialized field |
|---|---|
| `agent["endowment_x"]` | `agent["endowment"][0]` |
| `trade["agent_1_id"]` | `trade["agent1_id"]` |
| `trade["allocation_1_x"]` | `trade["post_allocations"][0][0]` |
| `trade["pre_endowment_1"]` | `trade["pre_holdings"][0]` |
| `trade["tick"]` | Not present on trade (tick is on TickRecord) |
| `trade["alpha_1"]` | Not present on trade |
| `"beliefs": {}` | Should parse from `belief_snapshots` |
| No `proposer_id` | Now available after A-003 |

**Fix:** Rewrite the transform block to map from actual `AgentSnapshot.to_dict()` and `TradeEvent.to_dict()` output to frontend `TickData` shape.

**Frontend type update:** Add optional `proposer_id?: string` to the `Trade` interface in `simulation.ts`.

**Test:** Integration test: create run via `SimulationLogger` → load via `/api/runs/{name}` → assert all fields present and correct.

**Files:** `server/routes.py`, `frontend/src/types/simulation.ts`

---

### A-007: Information-Regime Product Surface

**Problem:** No config pathway for `NoisyAlphaInformation`. Server `SimulationConfig` has no info_env fields. Simulation creation hardcodes `FullInformation()`.

**Fix:**

Backend:
1. Add `info_env_name: str = "full"` and `info_env_params: dict = {}` to server `SimulationConfig` (`simulation_manager.py:37`)
2. Add `to_dict`/`from_dict` handling for the new fields
3. Add info_env factory: `{"full": FullInformation, "noisy_alpha": lambda params: NoisyAlphaInformation(noise_std=params.get("noise_std", 0.1))}`
4. Wire `_create_simulation` in `simulation_manager.py` to use factory
5. Add `info_env_name` and `info_env_params` to `ConfigRequest` pydantic model in `routes.py`

Frontend:
1. Add `info_env_name?: string` and `info_env_params?: Record<string, number>` to `SimulationConfig` type
2. Add dropdown (Full Information / Noisy Alpha) and conditional noise_std input to `ConfigModal`

**Test:** API test: configure noisy info → run → assert persisted metadata matches. Round-trip test: config → run → replay metadata consistency.

**Files:** `server/simulation_manager.py`, `server/routes.py`, `server/websocket.py`, `frontend/src/types/simulation.ts`, `frontend/src/components/Config/ConfigModal.tsx`

---

### A-004: Frontend Lint Cleanup

**7 issues across 5 files:**

| File | Rule | Fix |
|---|---|---|
| `useSimulationSocket.ts` | `react-hooks/immutability` | Use `useRef` for reconnect callback to break self-reference |
| `GridCanvas.tsx` | `react-hooks/immutability` | Use `useRef` for rAF animation callback |
| `DualGridView.tsx` | `react-hooks/immutability` | Same pattern as GridCanvas |
| `ConfigModal.tsx` | `react-hooks/set-state-in-effect` | Conditional state update or derive from props |
| `button.tsx` | `react-refresh/only-export-components` | eslint-disable comment (shadcn/ui convention) |
| `TradeNetwork.tsx` | `react-hooks/exhaustive-deps` | Add `renderFull` to dependency array |
| `ReplayLoader.tsx` | `react-hooks/exhaustive-deps` | Add `fetchRuns` to dependency array |

**Files:** 5 frontend component/hook files listed above.

---

## Success Criteria

- All 716+ existing tests pass
- New tests cover: RNG isolation, proposer provenance, info_env execution, replay round-trip
- `npm run lint` passes clean
- Replay endpoint loads runs produced by current `SimulationLogger`
- Batch runs with noisy info actually execute with noisy info
- Logged proposer_id matches actual proposer for all bargaining protocols
