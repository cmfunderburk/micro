# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research-first agent-based microeconomics platform that gives canonical theoretical microeconomics computational form. The core insight is **institutional visibility**: making economic institutions (bargaining protocols, information structures, search mechanisms) explicit, configurable, and comparable.

See VISION.md for the authoritative statement of project identity and methodology. See STATUS.md for current capabilities and known limitations.

## Current Implementation Status (Summary)

### Simulation Core (Complete)

The core simulation infrastructure in `microecon/`:

| Module | Purpose |
|--------|---------|
| `bundle.py` | `Bundle(x, y)` - 2-good economy representation |
| `preferences.py` | `CobbDouglas(alpha)` - u(x,y) = x^α * y^(1-α) |
| `agent.py` | Agent with private state / observable type separation |
| `grid.py` | `Grid(size)`, `Position`, movement, spatial queries |
| `information.py` | `InformationEnvironment` abstraction (`FullInformation`, `NoisyAlphaInformation`) |
| `beliefs.py` | Agent beliefs (type beliefs, price beliefs, memory, update rules) |
| `bargaining.py` | Bargaining protocols (Nash, Rubinstein, Asymmetric Nash, TIOLI) |
| `search.py` | Target evaluation (discounted surplus), movement decisions, belief integration |
| `matching.py` | Matching protocols (Opportunistic; StableRoommates deprecated), commitment state |
| `simulation.py` | `Simulation` engine with four-phase tick loop, `create_simple_economy()` factory |
| `batch.py` | `BatchRunner` for parameter sweeps and systematic comparisons |

### Logging & Analysis (Complete)

Infrastructure for capturing simulation state and analyzing results:

| Module | Purpose |
|--------|---------|
| `logging/events.py` | Event dataclasses (`TickRecord`, `SearchDecision`, `TradeEvent`, etc.) |
| `logging/logger.py` | `SimulationLogger` hooks into simulation, captures full state |
| `logging/formats.py` | JSON lines format for human-readable logs |
| `analysis/loader.py` | `load_run()`, `load_batch()`, grouping utilities |
| `analysis/timeseries.py` | Welfare/trades over time, agent trajectories |
| `analysis/distributions.py` | Cross-run comparisons, statistical tests |
| `analysis/tracking.py` | Agent-level outcomes, search efficiency analysis |

### Web Frontend (Primary UI)

Browser-based visualization in `frontend/` (React/Vite) with `server/` (FastAPI/WebSocket):

```bash
# Start server
uv run uvicorn server.app:create_app --factory --port 8000

# Start frontend (in separate terminal)
cd frontend && npm run dev
```

**Features:**
- Three-column layout: metrics/overlays | grid | charts
- Real-time WebSocket updates
- Responsive grid canvas (square, max 600px)
- Live welfare and trade count charts
- Trade history modal with Edgeworth box inspection
- Overlay toggles (trails, perception radius, heatmap, trade connections)
- Configuration modal for simulation parameters
- Export (PNG/SVG/GIF/CSV/JSON)
- Trade network panel

### Archived: DearPyGui Visualization

The original desktop GUI has been archived to `.archived/visualization-dearpygui/`. See the README there for restoration instructions if needed

### Test Coverage

667 tests covering all core modules. Run with: `uv run pytest`

## Architecture

```
microecon/
├── microecon/               # Core simulation library (Python)
│   ├── __init__.py          # Public API exports
│   ├── bundle.py            # 2-good bundles
│   ├── preferences.py       # Utility functions (Cobb-Douglas)
│   ├── agent.py             # Agent, AgentPrivateState, AgentType
│   ├── grid.py              # Spatial grid and positions
│   ├── information.py       # Information environments (Full, NoisyAlpha)
│   ├── beliefs.py           # Agent beliefs (type beliefs, price beliefs, memory)
│   ├── bargaining.py        # Bargaining protocols (Nash, Rubinstein, Asymmetric Nash, TIOLI)
│   ├── search.py            # Target selection and movement
│   ├── matching.py          # Matching protocols (Opportunistic; StableRoommates deprecated)
│   ├── simulation.py        # Main simulation engine (four-phase tick)
│   ├── batch.py             # BatchRunner for parameter sweeps
│   ├── logging/             # Event logging infrastructure
│   ├── analysis/            # Post-hoc analysis utilities
│   └── scenarios/           # Scenario definitions and loading
├── server/                  # FastAPI WebSocket server
│   ├── app.py               # Application factory
│   ├── websocket.py         # WebSocket handlers
│   ├── simulation_manager.py # Simulation lifecycle management
│   └── routes.py            # REST API routes
├── frontend/                # React/Vite web UI
│   └── src/
│       ├── App.tsx          # Main application layout
│       ├── components/      # UI components (Grid, Charts, etc.)
│       ├── hooks/           # WebSocket hook
│       └── store/           # Zustand state management
└── tests/                   # pytest test suite
```

### Key Abstractions

**Agent state vs. observable type**: Agents have private state (true preferences, endowments) separate from observable type (what others can see). Under `FullInformation`, type = private state. Under `NoisyAlphaInformation`, observed types differ from true types.

**Information environment**: `InformationEnvironment` interface determines what agents can observe about each other. `FullInformation` exposes everything; `NoisyAlphaInformation` adds noise to observed preference parameters, enabling information asymmetry studies.

**Bargaining protocol**: `BargainingProtocol` ABC enables swapping institutional rules. Four implementations:
- `NashBargainingProtocol`: Axiomatic solution (symmetric, maximizes Nash product). O&R Ch 2.
- `RubinsteinBargainingProtocol`: BRW limit of alternating-offers (patience = power). O&R Ch 3.
- `AsymmetricNashBargainingProtocol`: Weighted Nash product using `agent.bargaining_power`. O&R Ch 2.6.
- `TIOLIBargainingProtocol`: Take-it-or-leave-it (proposer extracts all surplus). O&R §2.8.

**Matching protocol**: `MatchingProtocol` ABC determines how agents form trading pairs:
- `OpportunisticMatchingProtocol`: Any co-located pair can trade (default, myopic)
- `StableRoommatesMatchingProtocol`: *Deprecated* — centralized Irving's algorithm conflicts with agent-autonomous action-budget model. See `docs/current/stablematching-roadmap-thinking.md`.

The abstraction enables the core research question: "What difference does the institution make?"

**Search with discounted surplus**: Agents evaluate visible others by computing Nash bargaining surplus, discounted by distance. This couples search meaningfully to exchange - agents pursue opportunities that maximize expected gains from trade.

## Development Commands

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=microecon

# Start web frontend (two terminals needed)
# Terminal 1: Server
uv run uvicorn server.app:create_app --factory --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
# Then open http://localhost:5173

# Run batch comparison (Nash vs Rubinstein)
uv run python -c "
from microecon.batch import run_comparison
from microecon.analysis import compare_protocols
results = run_comparison(n_agents=10, ticks=100, seeds=range(5))
for name, comp in compare_protocols([r.run_data for r in results]).items():
    print(comp.summary())
"

# Run with logging to disk
uv run python -c "
from pathlib import Path
from microecon.batch import BatchRunner
from microecon.bargaining import NashBargainingProtocol
runner = BatchRunner(
    base_config={'n_agents': 10, 'grid_size': 15, 'seed': 42},
    output_dir=Path('./runs/test')
)
results = runner.run(ticks=100)
print(f'Saved to {results[0].log_path}')
"
```

## Theoretical Grounding Requirements

All behavioral rules, bargaining protocols, and institutional mechanisms must have formal justification from:
- Canonical texts: Kreps (I/II), Osborne & Rubinstein (Bargaining, Game Theory), MWG
- Axiomatic foundations (Nash bargaining)
- Game-theoretic equilibrium (Rubinstein SPE)
- Learning theory (RL, evolutionary dynamics)
- Published literature

"It works" or "intuitive heuristic" are not valid justifications.

## Document Hierarchy

1. **VISION.md** - Authoritative on identity, scope, methodology
2. **STATUS.md** - Current capabilities and known limitations (what exists today)
3. **theoretical-foundations.md** - Textbook mappings and derivations
4. **VISUALIZATION.md** - Full visualization design vision (UI/UX, technology choices, future features)
5. **CLAUDE.md** - Development guidance and conventions

## Next Development Directions

See STATUS.md §5 for a detailed gap analysis vs VISION.md.

**Web frontend polish**
- Keyboard shortcuts (space for play/pause)
- Smaller viewport handling (<1280px)
- Agent details on click (compact popover)

**Institutional comparisons** (core research value per VISION.md)
- Additional bargaining protocols (posted prices, double auction)
- Protocol-aware search (currently uses Nash surplus for all protocols)

**Information environments**
- Signaling and screening mechanisms
- Additional noise models beyond NoisyAlphaInformation

**Analysis extensions**
- Equilibrium benchmarks (Walrasian prices for comparison)
