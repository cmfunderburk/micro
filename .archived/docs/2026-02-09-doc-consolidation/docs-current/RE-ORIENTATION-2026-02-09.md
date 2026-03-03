# Microecon Reorientation

**Date:** 2026-02-09  
**Scope:** Full-project reorientation from code + docs + runtime checks

## How this guide was produced
- Reviewed core docs: `VISION.md`, `STATUS.md`, `README.md`, `theoretical-foundations.md`, ADRs, `docs/current/*`.
- Reviewed core implementation paths: `microecon/`, `server/`, `frontend/src/`.
- Ran backend test baseline: `uv run pytest`.
- Ran frontend static baseline: `cd frontend && npm run lint`.

## Executive Snapshot
The project is in a strong "research platform" state, not a prototype state. The core simulation architecture is coherent and extensively tested. The largest current issues are not core economics correctness; they are integration drift and clarity drift:

1. Replay API parser appears out of sync with current log schema.
2. Frontend lint is currently failing on several hook/refresh rules.
3. Documentation has some stale claims relative to implementation.
4. Matching/clearing remains the biggest architecture gap vs stated vision.

The core economics engine and bargaining stack are healthy.

## Verified Baseline (Today)

### Python/test status
- Command run: `uv run pytest`
- Result: `731` collected, `716 passed`, `15 skipped`, `0 failed`
- Runtime: ~2m02s

Skips are mostly intentional and documented (performance/deprecated-matching/timeouts):
- `tests/test_edge_cases.py`
- `tests/test_integration.py`
- `tests/scenarios/test_trading_chain.py`

### Frontend/lint status
- Command run: `cd frontend && npm run lint`
- Result: **fails** with `5 errors`, `2 warnings`
- Notable errors:
  - Hook immutability errors from callback self-reference timing:
    - `frontend/src/components/Grid/GridCanvas.tsx`
    - `frontend/src/components/Comparison/DualGridView.tsx`
    - `frontend/src/hooks/useSimulationSocket.ts`
  - Effect set-state warning treated as error:
    - `frontend/src/components/Config/ConfigModal.tsx`
  - Fast refresh export rule:
    - `frontend/src/components/ui/button.tsx`

## Project Intent (Still Coherent)
The identity in `VISION.md` still maps cleanly to the codebase:
- Agents optimize under constraints.
- Interaction rules are institutional modules (especially bargaining today).
- Spatial representation makes search/information frictions explicit.
- Institutional visibility is the central comparative question.

Short version: your thesis is still intact and reflected in code.

## Current Architecture (As Implemented)

### 1) Core model layer (`microecon/`)
- `bundle.py`: immutable 2-good bundle primitives.
- `preferences.py`: Cobb-Douglas utility + MRS + demand utilities.
- `agent.py`: private state vs observable type separation, mutable holdings, interaction state machine, optional belief subsystem.
- `grid.py`: discrete NxN spatial world with optional wrapping support (`wrap`), adjacency and radius queries.
- `information.py`: `FullInformation`, `NoisyAlphaInformation`, placeholder `PrivateInformation`.

### 2) Institutional layer (implemented)
- Bargaining protocols in `bargaining.py`:
  - Nash (symmetric)
  - Rubinstein via BRW patience-weight mapping
  - Asymmetric Nash via `bargaining_power`
  - TIOLI with proposer-dominant surplus extraction
- Matching is action/decision driven, not an independent protocol module (`matching.py` is documentation-only).

### 3) Tick engine (`simulation.py`)
The operational loop is:
1. Perceive: evaluate visible opportunities (`evaluate_targets_detailed`)
2. Decide: choose one action (`RationalDecisionProcedure.choose`)
3. Execute: resolve proposals/trades/fallbacks/movements

Behavioral details currently true in code:
- Proposal resolution is same-tick (not multi-tick pending state in practice).
- Opportunity cost is stored during Decide and used for acceptance tests during Execute.
- Rejections can trigger cooldowns; failed proposals can execute fallback actions.
- Mutual proposals are detected and handled before non-mutual proposals.

### 4) Belief subsystem (`beliefs.py` + integration points)
- Belief machinery is fully implemented (memory, price/type beliefs, update rules).
- Search can use believed alphas (`search.py`).
- Beliefs update on trade (`simulation.py` -> `record_trade_observation`).
- Price beliefs are tracked but still lightly used in behavior.

### 5) Logging and analysis
- Structured tick logging in `microecon/logging/`.
- Analysis toolkit in `microecon/analysis/` covers timeseries, distributions, tracking, network/emergence summaries.
- Market emergence scenario utilities are in `microecon/scenarios/market_emergence.py`.

### 6) Backend (`server/`)
- FastAPI app + WebSocket streaming.
- `SimulationManager` supports single mode and comparison mode.
- REST endpoints cover health/state/config/runs/scenarios.

### 7) Frontend (`frontend/src/`)
- Zustand stores split by mode:
  - live mode (`store/index.ts`)
  - comparison mode (`store/comparisonStore.ts`)
  - replay mode (`store/replayStore.ts`)
- UI modes are well-structured:
  - Normal live mode
  - Comparison dual-view mode
  - Replay mode
- Rich visualization exists (grid overlays, trade inspection/Edgeworth, network panel, export actions, scenario browser).

## Documentation Trust Map

### Most authoritative for intent
- `VISION.md`: purpose and methodological identity.

### Most accurate for current implementation
- `docs/current/IMPLEMENTED-ARCHITECTURE.md`
- code in `microecon/` and `server/`
- tests in `tests/`

### Useful but partially stale/mixed
- `STATUS.md` (mostly useful, but some counts/claims have drift)
- `README.md` (contains older matching protocol references)
- `docs/current/ROADMAP.md` (valuable for direction; not always current behavior)

## Important Drift / Risks To Be Aware Of

### P0: Replay API schema mismatch (likely breakage)
Evidence:
- Current logs write `agent_snapshots[].endowment` (list), not `endowment_x/endowment_y`.
  - `microecon/logging/events.py:72-87`
- Replay loader expects old keys (`endowment_x`, `agent_1_id`, etc.).
  - `server/routes.py:220-242`

This likely causes replay load failures for newly generated runs.

### P0: Frontend lint baseline is red
- `npm run lint` currently fails with multiple errors/warnings.
- This is a maintainability and CI hygiene risk even if app runs.

### P1: Trade logging proposer attribution is simplified, not true proposer
- In `_build_trade_events_data`, proposer is hard-coded to `event.agent1_id`.
  - `microecon/simulation.py:627`
- This can distort protocol analysis where proposer identity matters (especially TIOLI).

### P1: Docs drift across status/version/protocol descriptions
Examples:
- `STATUS.md` says `716 tests`; suite now collects `731` and passes `716` + skips.
- `README.md` still references `StableRoommatesMatchingProtocol` in concept list.
- `pyproject.toml` version is `0.2.0` while status docs present `0.4.0` narrative.

### P1: Roadmap architecture text does not always match current code behavior
- `docs/current/ROADMAP.md` includes multi-tick exchange narrative and simplified acceptance rules that do not fully match implementation.
- Treat roadmap as direction/backlog, not as runtime truth.

### P2: Unused/reserved fields in simulation state
- `_pending_proposals` / `_negotiating_pairs` are present but largely not part of active flow.
  - `microecon/simulation.py:109-111`
- Not harmful, but adds cognitive overhead.

### P2: Coverage gap on server/frontend integration correctness
- Python economics core is deeply tested.
- Server route schema compatibility and frontend replay integration are not equivalently protected by tests.

## What Has Matured Most (Big Wins)
- The three-phase action-budget simulation architecture is now robust.
- Bargaining protocol breadth is meaningful for institutional comparison.
- Belief architecture exists end-to-end (data model -> update -> visualization).
- Web UI is a strong research workbench, especially comparison + inspection tooling.

## Largest Conceptual Gap vs Vision
The matching/clearing institution is still underpowered relative to bargaining modularity.
- Bargaining is truly swappable and explicit.
- Matching is currently embedded in propose/accept execution logic.
- If "institutional visibility" is the thesis, matching/clearing abstraction is the highest-leverage missing piece.

## Re-Entry Playbook

### 30-minute reboot
1. Read `VISION.md`.
2. Read `docs/current/IMPLEMENTED-ARCHITECTURE.md`.
3. Skim `microecon/simulation.py` and `microecon/decisions.py`.
4. Run `uv run pytest`.

### 60-90 minute architecture refresh
1. Trace one complete tick:
   - `microecon/simulation.py`
   - `microecon/search.py`
   - `microecon/actions.py`
   - `microecon/decisions.py`
2. Refresh bargaining internals:
   - `microecon/bargaining.py`
   - `tests/theory/test_*.py`
3. Refresh backend/frontend contract:
   - `server/simulation_manager.py`
   - `server/websocket.py`
   - `frontend/src/hooks/useSimulationSocket.ts`
   - `frontend/src/types/simulation.ts`

### If you want to start coding immediately
Use this order:
1. Fix replay schema mismatch.
2. Fix lint baseline.
3. Normalize docs for current truth.
4. Choose one substantive research-direction feature.

## Suggested Next Work Packages

### Package A: Integration hardening (short, high leverage)
- Repair replay parser schema in `server/routes.py`.
- Make lint pass in frontend.
- Add regression tests for replay log parsing.

### Package B: Documentation consolidation
- Align `README.md`, `STATUS.md`, `ROADMAP.md` with actual engine behavior.
- Clarify source-of-truth hierarchy in docs.

### Package C: Matching institution explicitness
- Extract/parameterize clearing rules (status quo, target-choice, benchmark centralized matching).
- Keep meeting technology fixed initially for clean comparisons.

### Package D: Protocol extension and benchmarks
- Add remaining planned bilateral protocols (e.g., Kalai-Smorodinsky, Nash Demand Game) if still desired.
- Add equilibrium benchmark analysis paths where useful.

### Package E: Sustained economy loop (larger effort)
- Metabolism/consumption + acquisition loop for persistent dynamics.
- This unlocks long-run emergence and richer learning experiments.

## Discussion Agenda For Our Next Session
1. Choose immediate priority: `A`, `B`, `C`, `D`, or `E`.
2. Decide whether we optimize for research velocity or architecture cleanup first.
3. If research velocity: choose one tightly scoped experiment to run end-to-end.
4. If cleanup: start with replay+lint, then doc normalization.

## Appendix: Concrete File Anchors
- Tick engine: `microecon/simulation.py`
- Decision logic: `microecon/decisions.py`
- Action system: `microecon/actions.py`
- Bargaining protocols: `microecon/bargaining.py`
- Belief system: `microecon/beliefs.py`
- Logging schema: `microecon/logging/events.py`
- Replay route parser: `server/routes.py`
- WebSocket integration: `server/websocket.py`, `frontend/src/hooks/useSimulationSocket.ts`
- UI state models: `frontend/src/store/index.ts`, `frontend/src/store/comparisonStore.ts`, `frontend/src/store/replayStore.ts`
