# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Python (always use uv, never pip/poetry/conda)
uv sync                                    # Install deps
uv run pytest                              # All tests
uv run pytest tests/test_simulation.py -v  # One file
uv run pytest tests/test_simulation.py::TestSimulationSetup::test_create_simulation -v  # One test
uv run pytest -m "not slow"               # Skip slow tests
uv run pytest -m contract                 # Schema contract conformance
uv run pytest -m determinism              # Deterministic rerun equivalence
uv run pytest -m theory                   # Bargaining theory verification
uv run pytest -m orchestrator             # Manifest/orchestrator service tests
uv run pytest --cov=microecon             # Coverage

# Frontend
cd frontend && npm install                 # Install deps
cd frontend && npm run dev                 # Vite dev server (:5173)
cd frontend && npm run lint                # ESLint
cd frontend && npm run build               # Build + typecheck

# Full stack
./scripts/dev.sh                           # Backend (:8000) + frontend (:5173)
uv run uvicorn server.app:create_app --factory --port 8000  # Backend only
```

## Architecture

Research-first agent-based microeconomics platform. Python simulation core + FastAPI/WebSocket server + React/TypeScript frontend.

### Simulation Core (`microecon/`)

The simulation runs a **3-phase tick model** (ADR-001): Perceive → Decide → Execute. Each tick, all agents simultaneously perceive a frozen state snapshot, independently decide on one action, then actions are conflict-resolved and executed.

**Key abstractions** (all in `microecon/`):
- `Bundle` - immutable 2-good bundle (x, y)
- `Preferences` / `CobbDouglas` - utility functions
- `Agent` - private state (true preferences) vs observable type (what others see, controlled by InformationEnvironment)
- `BargainingProtocol` - determines trade outcome (Nash, Rubinstein, TIOLI, AsymmetricNash)
- `MatchingProtocol` - determines who trades (BilateralProposalMatching, CentralizedClearingMatching)
- `InformationEnvironment` - determines what agents observe (FullInformation, NoisyAlphaInformation)
- `DecisionProcedure` - determines how agents choose actions (RationalDecisionProcedure)
- `Simulation` - orchestrates the tick loop; `create_simple_economy()` is the main factory

**Logging** (`microecon/logging/`): Canonical event schema in `events.py` — `TradeEvent`, `TickRecord`, `RunSummary`, etc. All events use primitive types for JSON serialization. `SCHEMA_VERSION` tracks compatibility.

**Analysis** (`microecon/analysis/`): Post-hoc analysis — timeseries, distributions, tracking, emergence detection.

### Server (`server/`)

FastAPI app with REST endpoints (`/api/*`) and WebSocket (`/ws/simulation`). `SimulationManager` wraps a single simulation instance. Note: `SimulationConfig` in `server/simulation_manager.py` is **different** from `SimulationConfig` in `microecon/logging/events.py`.

### Frontend (`frontend/src/`)

React 19 + Zustand + Vite. Three modes: Normal (single sim), Comparison (dual sims), Replay (historical logs). Shadcn-style Radix UI components in `components/ui/`. `types/canonical.ts` is **auto-generated** from Python schema via `scripts/generate_ts_types.py`.

## Schema Change Protocol

When modifying `microecon/logging/events.py`:
1. Update `docs/contracts/schema-v1.md`
2. Regenerate types: `uv run python scripts/generate_ts_types.py --write`
3. Commit regenerated `frontend/src/types/canonical.ts`
4. If removing/renaming fields: bump `SCHEMA_VERSION` in `events.py` and update `_SUPPORTED_VERSIONS` in `formats.py`
5. Run: `uv run pytest -m contract` and `uv run pytest -m determinism`

When modifying bargaining, matching, or decision procedures: run `uv run pytest -m theory`.

## Style

- **Python**: 4-space indent, snake_case functions/variables, PascalCase classes
- **Frontend**: 2-space indent, TypeScript with semicolons, PascalCase components, `useX` hooks
- **Commits**: `feat(scope): ...`, `test(scope): ...`, `fix(scope): ...` — imperative summary with scope

## Test Markers

Markers in `pyproject.toml` indicate which tests to run when specific modules change:
- `core` — bundle, preferences, agent, grid, information (fast, always safe)
- `bargaining` / `matching` / `beliefs` / `search` — run when corresponding module changes
- `simulation` — simulation.py or batch.py changes
- `analysis` — logging/ or analysis/ changes
- `contract` — events.py, routes.py, or simulation_manager.py changes
- `determinism` — simulation.py or batch.py changes
- `integration` — full pipeline (run before commits)
- `theory` — bargaining protocol changes
