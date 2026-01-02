# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research-first agent-based microeconomics platform that gives canonical theoretical microeconomics computational form. The core insight is **institutional visibility**: making economic institutions (bargaining protocols, information structures, search mechanisms) explicit, configurable, and comparable.

See VISION.md for the authoritative statement of project identity and methodology. See STATUS.md for current capabilities and known limitations.

## Current Implementation Status (Summary)

### Simulation Core (Complete)

The core simulation infrastructure in `src/microecon/`:

| Module | Purpose |
|--------|---------|
| `bundle.py` | `Bundle(x, y)` - 2-good economy representation |
| `preferences.py` | `CobbDouglas(alpha)` - u(x,y) = x^α * y^(1-α) |
| `agent.py` | Agent with private state / observable type separation |
| `grid.py` | `Grid(size)`, `Position`, movement, spatial queries |
| `information.py` | `InformationEnvironment` abstraction, `FullInformation` implementation |
| `bargaining.py` | Bargaining solutions (Nash, Rubinstein), protocol abstraction |
| `search.py` | Target evaluation (discounted Nash surplus), movement decisions |
| `matching.py` | Matching protocols (Opportunistic, StableRoommates), commitment state |
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
| `visualization/replay.py` | `ReplayController`, `DualReplayController` for playback |

### Visualization (MVP Complete)

DearPyGui-based visualization in `src/microecon/visualization/`. See VISUALIZATION.md for full design vision.

**Implemented:**
- Grid rendering with agents colored by preference parameter (alpha)
- Play/pause/step/reset controls with speed slider
- Trade animations (line flash between trading agents)
- Metrics panel (tick, trades, welfare, gains)
- Hover tooltips showing agent details
- Click-to-select with perception radius overlay
- Movement trails

**From VISUALIZATION.md, not yet implemented:**
- Trade zoom view / Edgeworth box
- Time series charts (ImPlot integration)
- Agent perspective mode (for information asymmetry)
- Export capabilities (PNG, GIF, CSV, SVG)
- Config file support (YAML/JSON scenarios)
- Replay mode (currently live-only)

Run with: `uv run python -m microecon.visualization`

### Test Coverage

341 tests covering all core modules. Run with: `uv run pytest`

## Architecture

```
src/microecon/
├── __init__.py          # Public API exports
├── bundle.py            # 2-good bundles
├── preferences.py       # Utility functions (Cobb-Douglas)
├── agent.py             # Agent, AgentPrivateState, AgentType
├── grid.py              # Spatial grid and positions
├── information.py       # Information environment abstraction
├── bargaining.py        # Nash bargaining solution
├── search.py            # Target selection and movement
├── matching.py          # Matching protocols (Opportunistic, StableRoommates)
├── simulation.py        # Main simulation engine (four-phase tick)
├── batch.py             # BatchRunner for parameter sweeps
├── logging/
│   ├── __init__.py
│   ├── events.py        # Event dataclasses
│   ├── logger.py        # SimulationLogger
│   └── formats.py       # JSON lines format
├── analysis/
│   ├── __init__.py
│   ├── loader.py        # Run loading utilities
│   ├── timeseries.py    # Time series analysis
│   ├── distributions.py # Cross-run comparisons
│   └── tracking.py      # Agent-level tracking
└── visualization/
    ├── __init__.py
    ├── __main__.py      # Entry point for -m invocation
    ├── app.py           # DearPyGui visualization
    └── replay.py        # Replay controllers
```

### Key Abstractions

**Agent state vs. observable type**: Agents have private state (true preferences, endowments) separate from observable type (what others can see). Currently type = private state (full information), but the architecture supports future information environments.

**Information environment**: `InformationEnvironment` interface determines what agents can observe about each other. `FullInformation` exposes everything; future implementations can restrict visibility.

**Bargaining protocol**: `BargainingProtocol` ABC enables swapping institutional rules. Two implementations:
- `NashBargainingProtocol`: Axiomatic solution (symmetric, maximizes Nash product)
- `RubinsteinBargainingProtocol`: Strategic alternating-offers (first-mover advantage, patience = power)

**Matching protocol**: `MatchingProtocol` ABC determines how agents form trading pairs. Two implementations:
- `OpportunisticMatchingProtocol`: Any co-located pair can trade (default, myopic)
- `StableRoommatesMatchingProtocol`: Irving's algorithm forms committed pairs (stable, globally optimal)

Both abstractions enable the core research question: "What difference does the institution make?"

**Search with discounted surplus**: Agents evaluate visible others by computing Nash bargaining surplus, discounted by distance. This couples search meaningfully to exchange - agents pursue opportunities that maximize expected gains from trade.

## Development Commands

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=microecon

# Run visualization
uv run python -m microecon.visualization

# Run visualization with custom parameters
uv run python -c "from microecon.visualization import run_visualization; run_visualization(n_agents=20, grid_size=20, seed=42)"

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

See STATUS.md §5 for a detailed gap analysis vs VISION.md and VISUALIZATION.md.

**Visualization enhancements** (see VISUALIZATION.md for full specs)
- Trade zoom view with Edgeworth box
- Time series charts via ImPlot
- Export: PNG/SVG frames, GIF/MP4 animations
- Overlay toggles (trails, perception radius)

**Institutional comparisons** (core research value per VISION.md)
- Additional bargaining protocols (TIOLI, posted prices, double auction)
- Protocol-aware search (currently uses Nash surplus for all protocols)

**Information environments**
- Private information (type ≠ private state)
- Signaling and screening
- Agent perspective mode in visualization

**Analysis extensions**
- Equilibrium benchmarks (Walrasian prices for comparison)
- Config files for reproducible scenarios (YAML/JSON)
