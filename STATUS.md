# Current Project Status

**Version:** 0.1.0 (community release)
**Date:** 2026-01-05
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
| `matching.py` | Matching protocols (Opportunistic, StableRoommates) with commitment state |
| `simulation.py` | Four-phase tick loop, `create_simple_economy()` factory |

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

### Matching Protocols

Two complete implementations enabling institutional comparison:

**Opportunistic Matching** (`OpportunisticMatchingProtocol`)
- Default behavior: any co-located pair can trade
- No commitment phase required
- Simple, myopic matching

**Stable Roommates Matching** (`StableRoommatesMatchingProtocol`)
- Irving's algorithm (1985) for stable matching
- Agents form committed pairs before trading
- Only committed + co-located pairs can trade
- Produces stable matching (no blocking pairs)

**Empirical finding**: In trading chain scenario (4 agents), committed matching achieves 2.2% higher welfare than opportunistic matching. Matching protocols affect outcomes, not just paths.

### Batch Runs & Logging

Infrastructure for systematic experiments:

| Module | Capability |
|--------|------------|
| `batch.py` | `BatchRunner` for parameter sweeps, bargaining and matching protocol comparisons |
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

DearPyGui-based visualization with three modes:

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

**Comparison Mode** (Phase 1 Dashboard - NEW)
- Side-by-side dual viewport for protocol comparison
- Synchronized playback across both runs
- Trade animations and movement trails in both viewports
- Timeline with event markers:
  - Yellow circles for trades
  - Green diamonds for commitments
  - White playhead showing current position
  - Dual track (one per run)
- Real-time welfare/trade difference display
- Entry points for both bargaining and matching protocol comparisons

Run with: `uv run python -m microecon.visualization`

**Comparison Entry Points:**
```python
# Compare bargaining protocols (Nash vs Rubinstein)
from microecon.visualization import run_protocol_comparison
run_protocol_comparison(n_agents=10, grid_size=15, ticks=50, seed=42)

# Compare matching protocols (Opportunistic vs StableRoommates)
from microecon.visualization import run_matching_protocol_comparison
run_matching_protocol_comparison(n_agents=10, grid_size=15, ticks=50, seed=42)
```

### Test Coverage

450+ tests covering all core modules. Run with: `uv run pytest`

---

## 2. Known Limitations

### Architectural

**Search uses Nash surplus regardless of protocol**
- Agents evaluate potential partners using Nash bargaining surplus
- This applies even when using Rubinstein protocol for actual exchange
- Intentional simplification pending information environment architecture
- Does not affect bargaining outcomes, only partner selection heuristics

**2-good economy only**
- `Bundle(x, y)` is hardcoded for 2 goods
- Cobb-Douglas preferences assume 2 goods
- Visualization color encoding assumes 2 goods

**No learning agents**
- Agents follow fixed behavioral rules
- No reinforcement learning or evolutionary dynamics
- No adaptive behavior over time

### Scale Boundaries

**Recommended agent count: 2-200**
- Minimum: 2 agents (need at least a pair for trade)
- Optimal: 50-100 agents (market emergence visible, reasonable runtime)
- Maximum tested: 200 agents (runs but slower; ~5 minutes for 100 ticks)
- Not recommended: >500 agents (untested, may be slow)

**Grid size relative to agents**
- Minimum: grid_size >= 5 (smaller grids work but limited movement)
- Recommended: grid_size >= sqrt(n_agents) to avoid excessive crowding
- Crowding is allowed (multiple agents per cell) but affects dynamics

### Edge Cases Handled

**Degenerate economic cases:**
- Zero utility (one endowment component = 0) → trades still compute, returns 0 gains
- No gains from trade (identical preferences + endowments) → graceful no-op
- Extreme endowment imbalance (1000:0.01) → handles correctly

**Invalid configurations:**
- alpha ∉ (0, 1) → clear ValueError with message
- negative endowments → clear ValueError with message
- grid_size < 1 → clear ValueError with message
- noise_std < 0 → clear ValueError with message

### Visualization

**No export capabilities**
- Cannot export PNG/SVG frames
- Cannot export GIF/MP4 animations
- No CSV/JSON data export from UI

**No GUI parameter editing**
- YAML scenario files exist (`scenarios/*.yaml`) but no GUI editor
- Parameters can be set via code or YAML scenarios

**Overlays always on**
- Movement trails cannot be toggled
- Perception radius shown on selection (not toggleable)
- No heatmaps or trade network overlays

**No trade zoom view**
- Cannot inspect individual trades in detail
- No Edgeworth box visualization
- No bargaining sequence replay

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

### Simulation Phases (Four-Phase Tick)

Each tick executes in order:
1. **Evaluate**: Agents observe visible others, compute surplus rankings
2. **Decide**: Form commitments (committed mode) or select targets (opportunistic)
3. **Move**: Agents move toward committed partner or selected target
4. **Exchange**: Execute bargaining (commitment-gated or any co-located)

Pre-tick: Commitment maintenance breaks stale commitments when partners exit perception radius.

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

# Run bargaining protocol comparison (Nash vs Rubinstein) with visualization
uv run python -c "
from microecon.visualization import run_protocol_comparison
run_protocol_comparison(n_agents=10, grid_size=15, ticks=50, seed=42)
"

# Run matching protocol comparison (Opportunistic vs StableRoommates) with visualization
uv run python -c "
from microecon.visualization import run_matching_protocol_comparison
run_matching_protocol_comparison(n_agents=10, grid_size=15, ticks=50, seed=42)
"

# Run batch comparison (bargaining protocols)
uv run python -c "
from microecon.batch import run_comparison
results = run_comparison(n_agents=10, ticks=100, seeds=range(5))
for r in results:
    print(f'{r.config.protocol_name}: {r.summary}')
"

# Run batch comparison (matching protocols)
uv run python -c "
from microecon.batch import run_matching_comparison
results = run_matching_comparison(n_agents=10, ticks=100, seeds=range(5))
for r in results:
    print(f'Trades: {r.summary[\"total_trades\"]}, Welfare: {r.summary[\"final_welfare\"]:.2f}')
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
| Institutional visibility (swap protocols) | **Implemented** for bargaining and matching |
| Equilibrium benchmarks | Bargaining only; no Walrasian/GE |
| Information regimes | **Implemented** (FullInformation, NoisyAlphaInformation) |
| Search/matching mechanisms | **Implemented** (Opportunistic, StableRoommates) |
| Agent sophistication levels | Single level; no learning agents |
| Market emergence metrics | **Implemented** (trade networks, welfare efficiency, spatial clustering) |

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
| Timeline event markers | **Implemented** (trades, commitments) |
| Comparison mode entry points | **Implemented** (bargaining + matching) |
| Time-series charts | **Implemented** (welfare, trades over time) |
| Setup/Run/Analyze modes | Not implemented |
| Overlay toggles | Not implemented |
| Trade zoom (Edgeworth box) | Not implemented |
| Agent perspective mode | Not implemented |
| Export (PNG/GIF/MP4) | Not implemented |
| Config files (YAML/JSON) | Not implemented |
| Scenario browser | **Implemented** (YAML loading) |

### vs DESIGN_dashboard_integration.md

| Phase | Status |
|-------|--------|
| Phase 1: Comparison View MVP | **Complete** |
| Phase 2: Scenario Pipeline | **Complete** (YAML scenarios, run_market_emergence) |
| Phase 3: Timeline & Charts | **Complete** (time-series panels) |
| Phase 4: Polish & Export | Not started |

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
├── matching.py
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
│   ├── tracking.py
│   └── emergence.py      # Market emergence metrics
├── scenarios/
│   ├── __init__.py
│   ├── schema.py          # YAML scenario schema
│   ├── loader.py          # Scenario loading utilities
│   └── market_emergence.py # MarketEmergenceConfig, run_market_emergence
└── visualization/
    ├── __init__.py
    ├── __main__.py
    ├── app.py
    ├── replay.py
    ├── browser.py         # Scenario browser UI
    └── timeseries.py      # Time-series charts (ImPlot)
```

---

**Document Version:** 0.0.1
**Last Updated:** 2026-01-02
