# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research-first agent-based microeconomics platform that gives canonical theoretical microeconomics computational form. The core insight is **institutional visibility**: making economic institutions (bargaining protocols, information structures, search mechanisms) explicit, configurable, and comparable.

See VISION.md for the authoritative statement of project identity and methodology.

## Current Implementation Status

### Simulation Core (Complete)

The core simulation infrastructure in `src/microecon/`:

| Module | Purpose |
|--------|---------|
| `bundle.py` | `Bundle(x, y)` - 2-good economy representation |
| `preferences.py` | `CobbDouglas(alpha)` - u(x,y) = x^α * y^(1-α) |
| `agent.py` | Agent with private state / observable type separation |
| `grid.py` | `Grid(size)`, `Position`, movement, spatial queries |
| `information.py` | `InformationEnvironment` abstraction, `FullInformation` implementation |
| `bargaining.py` | Nash bargaining solution, surplus calculation, trade execution |
| `search.py` | Target evaluation (discounted Nash surplus), movement decisions |
| `simulation.py` | `Simulation` engine with tick loop, `create_simple_economy()` factory |

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

92 tests covering all core modules. Run with: `uv run pytest`

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
├── simulation.py        # Main simulation engine
└── visualization/
    ├── __init__.py
    ├── __main__.py      # Entry point for -m invocation
    └── app.py           # DearPyGui visualization
```

### Key Abstractions

**Agent state vs. observable type**: Agents have private state (true preferences, endowments) separate from observable type (what others can see). Currently type = private state (full information), but the architecture supports future information environments.

**Information environment**: `InformationEnvironment` interface determines what agents can observe about each other. `FullInformation` exposes everything; future implementations can restrict visibility.

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
2. **theoretical-foundations.md** - Textbook mappings and derivations
3. **VISUALIZATION.md** - Full visualization design vision (UI/UX, technology choices, future features)
4. **VISUALIZATION_MVP_SPEC.md** - MVP requirements (complete, checklist at bottom shows all items done)
5. **CLAUDE.md** - Development guidance and current status

## Next Development Directions

The simulation and visualization foundations are complete. Potential next steps (not prioritized):

**Institutional comparisons** (core research value per VISION.md)
- Alternative bargaining protocols (Rubinstein, TIOLI, posted prices)
- Swappable matching mechanisms
- Compare outcomes under different institutional rules

**Information environments**
- Private information (type ≠ private state)
- Signaling and screening
- Partial observability
- Agent perspective mode in visualization (see what agent X sees)

**Visualization enhancements** (see VISUALIZATION.md §4-9 for full specs)
- Trade zoom view with Edgeworth box (§4)
- Time series charts via ImPlot (§9)
- Export: PNG/SVG frames, GIF/MP4 animations, CSV data logs (§12)
- Replay mode from logged history (§14)

**Analysis infrastructure**
- Equilibrium benchmarks (Walrasian prices for comparison)
- Statistical summaries across runs
- Config files for reproducible scenarios (YAML/JSON)
- Parameter sweep tools
