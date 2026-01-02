# Current Project Status

**Version:** 0.0.1 (pre-release)
**Date:** 2026-01-01
**Purpose:** Definitive reference for current capabilities

This document describes what exists and works today. For the long-term vision, see VISION.md. For the full visualization design, see VISUALIZATION.md.

---

## 1. What Works

### Simulation Core

A complete simulation engine for bilateral exchange in a spatial economy:

| Module | Capability |
|--------|------------|
| `bundle.py` | 2-good bundles with arithmetic operations |
| `preferences.py` | Cobb-Douglas utility with MRS, indifference curves, Marshallian demand |
| `agent.py` | Agents with private state / observable type separation |
| `grid.py` | NxN toroidal grid, positions, movement, spatial queries |
| `information.py` | Information environment abstraction (`FullInformation` implemented) |
| `bargaining.py` | Nash and Rubinstein bargaining protocols |
| `search.py` | Target evaluation (discounted surplus), movement decisions |
| `simulation.py` | Tick-based simulation loop, `create_simple_economy()` factory |

### Bargaining Protocols

Two complete implementations with theoretical grounding:

**Nash Bargaining** (`NashBargainingProtocol`)
- Axiomatic solution maximizing Nash product
- Symmetric surplus split
- Golden section search for numerical optimization

**Rubinstein Alternating Offers** (`RubinsteinBargainingProtocol`)
- Strategic extensive-form game solution
- First-mover advantage based on discount factors
- Converges to Nash as patience approaches 1

### Batch Runs & Logging

Infrastructure for systematic experiments:

| Module | Capability |
|--------|------------|
| `batch.py` | `BatchRunner` for parameter sweeps, protocol comparisons |
| `logging/events.py` | Structured event types (`TickRecord`, `TradeEvent`, `SearchDecision`) |
| `logging/logger.py` | `SimulationLogger` captures full simulation state |
| `logging/formats.py` | JSON lines format for human-readable logs |

**Note:** Batch runs require explicit seeds for reproducibility.

### Analysis

Post-hoc analysis of logged runs:

| Module | Capability |
|--------|------------|
| `analysis/loader.py` | Load runs from disk, group by protocol/seed |
| `analysis/timeseries.py` | Welfare and trade counts over time |
| `analysis/distributions.py` | Cross-run statistical comparisons |
| `analysis/tracking.py` | Agent-level outcome tracking |

### Visualization

DearPyGui-based visualization with two modes:

**Live Mode**
- Real-time simulation display
- Play/pause/step/reset controls
- Speed slider (ticks per second)
- Agent hover tooltips
- Click-to-select with perception radius overlay
- Movement trails
- Trade animations (connection lines)
- Metrics panel (tick count, trades, welfare, gains)

**Replay Mode**
- Load and playback logged runs
- Timeline scrubbing with slider
- Step forward/backward
- Synchronized dual viewport for side-by-side comparison

Run with: `uv run python -m microecon.visualization`

### Test Coverage

163 tests covering all core modules. Run with: `uv run pytest`

---

## 2. Known Limitations

### Architectural

**Search uses Nash surplus regardless of protocol**
- Agents evaluate potential partners using Nash bargaining surplus
- This applies even when using Rubinstein protocol for actual exchange
- Intentional simplification pending information environment architecture
- Does not affect bargaining outcomes, only partner selection heuristics

**Single information environment**
- Only `FullInformation` is implemented (agents see true types)
- Agent type = private state (no information asymmetry yet)
- Architecture supports future private/signaled information

**2-good economy only**
- `Bundle(x, y)` is hardcoded for 2 goods
- Cobb-Douglas preferences assume 2 goods
- Visualization color encoding assumes 2 goods

### Visualization

**No export capabilities**
- Cannot export PNG/SVG frames
- Cannot export GIF/MP4 animations
- No CSV/JSON data export from UI

**No configuration files**
- Parameters set via code only
- No YAML/JSON scenario files
- No GUI parameter editing

**Overlays always on**
- Movement trails cannot be toggled
- Perception radius shown on selection (not toggleable)
- No heatmaps or trade network overlays

**No trade zoom view**
- Cannot inspect individual trades in detail
- No Edgeworth box visualization
- No bargaining sequence replay

**No time-series charts**
- Metrics panel shows current values only
- No ImPlot integration yet
- No welfare/trade graphs over time

---

## 3. Architecture Notes

### Agent State Separation

Agents have architecturally distinct components:

```
AgentPrivateState     AgentType (Observable)
├── preferences       ├── preferences*
├── endowment         ├── endowment*
└── discount_factor   └── discount_factor*

* Currently identical (FullInformation)
  Future: type may differ from private state
```

This separation exists specifically to support future information asymmetry work.

### Bargaining Protocol Interface

```python
class BargainingProtocol(ABC):
    @abstractmethod
    def execute(self, agent_a, agent_b, info_env) -> TradeResult | None:
        """Execute bargaining between two agents."""
        pass
```

New protocols (TIOLI, posted prices, double auction) implement this interface.

### Simulation Phases

Each tick executes in order:
1. **Search**: Agents evaluate visible others, select targets
2. **Move**: Agents move toward targets (or random if none)
3. **Exchange**: Co-located agents execute bargaining protocol

---

## 4. Entry Points

```bash
# Run visualization (live mode, default parameters)
uv run python -m microecon.visualization

# Run visualization with custom parameters
uv run python -c "
from microecon.visualization import run_visualization
run_visualization(n_agents=20, grid_size=20, seed=42)
"

# Run batch comparison (Nash vs Rubinstein)
uv run python -c "
from microecon.batch import run_comparison
results = run_comparison(n_agents=10, ticks=100, seeds=range(5))
for r in results:
    print(f'{r.config.protocol_name}: {r.summary}')
"

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=microecon
```

---

## 5. Gaps vs Vision Documents

### vs VISION.md

| Vision Goal | Status |
|-------------|--------|
| Institutional visibility (swap protocols) | **Implemented** for bargaining |
| Equilibrium benchmarks | Bargaining only; no Walrasian/GE |
| Information regimes | Architecture ready; only FullInformation |
| Search/matching mechanisms | Single implementation; not modular |
| Agent sophistication levels | Single level; no learning agents |
| Market emergence metrics | Basic welfare only; no price/network analysis |

### vs VISUALIZATION.md

| Design Element | Status |
|----------------|--------|
| DearPyGui standalone app | **Implemented** |
| Grid + agents + tooltips | **Implemented** |
| Play/pause/speed controls | **Implemented** |
| Movement trails | **Implemented** (always on) |
| Trade animations | **Implemented** |
| Replay mode | **Implemented** |
| Dual viewport comparison | **Implemented** |
| Setup/Run/Analyze modes | Not implemented |
| Overlay toggles | Not implemented |
| Trade zoom (Edgeworth box) | Not implemented |
| Time-series charts | Not implemented |
| Agent perspective mode | Not implemented |
| Export (PNG/GIF/MP4) | Not implemented |
| Config files (YAML/JSON) | Not implemented |

---

## 6. File Structure

```
src/microecon/
├── __init__.py
├── bundle.py
├── preferences.py
├── agent.py
├── grid.py
├── information.py
├── bargaining.py
├── search.py
├── simulation.py
├── batch.py
├── logging/
│   ├── __init__.py
│   ├── events.py
│   ├── logger.py
│   └── formats.py
├── analysis/
│   ├── __init__.py
│   ├── loader.py
│   ├── timeseries.py
│   ├── distributions.py
│   └── tracking.py
└── visualization/
    ├── __init__.py
    ├── __main__.py
    ├── app.py
    └── replay.py
```

---

**Document Version:** 0.0.1
**Last Updated:** 2026-01-01
