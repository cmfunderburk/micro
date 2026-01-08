# Current Project Status

**Version:** 0.2.0
**Date:** 2026-01-07
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
| `agent.py` | Agents with private state / observable type separation, optional belief system |
| `grid.py` | NxN toroidal grid, positions, movement, spatial queries |
| `information.py` | Information environment abstraction (`FullInformation`, `NoisyAlphaInformation`) |
| `beliefs.py` | Agent memory, type beliefs, price beliefs, Bayesian and heuristic update rules |
| `bargaining.py` | Nash and Rubinstein bargaining protocols with belief-aware surplus calculation |
| `search.py` | Target evaluation (discounted surplus), movement decisions, belief integration |
| `matching.py` | Matching protocols (Opportunistic, StableRoommates) with commitment state |
| `simulation.py` | Four-phase tick loop, `create_simple_economy()` factory with belief support |

### Bargaining Protocols

Two complete implementations with theoretical grounding:

**Nash Bargaining** (`NashBargainingProtocol`)
- Axiomatic solution maximizing Nash product
- Symmetric surplus split
- Golden section search for numerical optimization

**Rubinstein Alternating Offers** (`RubinsteinBargainingProtocol`)
- Uses BRW (1986) limit: patience determines bargaining power, not proposer identity
- More patient agent (higher δ) captures larger share of surplus
- Equal discount factors → symmetric Nash outcome
- Future: ClassicRubinsteinProtocol with finite-round first-mover advantage

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

### Agent Belief System (Phase 1)

Complete belief architecture enabling agent learning:

**Memory System**
- Trade history: Records trades with partner ID, bundles exchanged, tick
- Price observations: Observed exchange rates from trades
- Partner interaction history: Encounters and trade outcomes by partner
- Configurable memory depth (bounded or unlimited)

**Type Beliefs**
- Beliefs about trading partners' preference parameters (alpha)
- Confidence tracking based on number of interactions
- Updated after trades via configurable update rules

**Price Beliefs**
- Mean-variance representation of expected exchange rate
- Updated from observed trades (own and others')
- Currently deferred from decision logic (Phase 2)

**Update Rules**
- `BayesianUpdateRule`: Conjugate prior updates (optimal learning)
- `HeuristicUpdateRule`: Exponential moving average (bounded rationality)
- Extensible interface for custom rules

**Integration**
- Beliefs wire into search: agents use believed types for surplus calculation
- Beliefs wire into bargaining: protocols accept effective types
- Beliefs update during simulation: trades trigger belief updates
- Belief snapshots logged each tick for trajectory analysis

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

DearPyGui-based visualization with three modes plus auxiliary windows:

**Live Mode**
- Real-time simulation display
- Play/pause/step/reset controls with speed slider
- **Configuration modal** for simulation setup:
  - Basic parameters (agents, grid size, seed)
  - Institutional selection (Nash/Rubinstein bargaining, Opportunistic/Stable Roommates matching)
  - Search parameters (perception radius, discount factor)
- Agent hover tooltips with detailed state
- Click-to-select with perception radius overlay
- **Toggleable overlays**: movement trails, perception radius, surplus heatmap, trade network
- Trade animations (connection lines between trading agents)
- Metrics panel (tick count, trades, welfare, gains)
- Time-series charts (welfare and trade count over time)

**Replay Mode**
- Load and playback logged runs
- Timeline scrubbing with slider
- Step forward/backward

**Comparison Mode**
- Side-by-side dual viewport for protocol comparison
- Synchronized playback across both runs
- Trade animations and movement trails in both viewports
- Timeline with event markers (trades, commitments)
- Real-time welfare/trade difference display

**Trade Inspection**
- **Trade history panel**: Scrollable list of all trades with click-to-inspect
- **Edgeworth box popup**: Shows endowments, indifference curves, contract curve, trade outcome
- Utility breakdown with pre/post trade values and gains

**Agent Perspective Mode**
- Toggle to see the world as a selected agent sees it
- Dims agents outside perception radius
- Shows agent's beliefs about visible partners (when beliefs enabled)

**Export Capabilities**
- PNG/SVG frame export (current view)
- GIF recording (configurable duration and frame rate)
- CSV export (agent states, trade history)
- JSON export (full tick data)

**Trade Network Panel** (separate dockable window)
- Visualizes trade relationships as a network graph
- Force-directed and circular layout options
- Node color encodes preference parameter (alpha)
- Edge thickness encodes trade frequency
- Edge color encodes recency (recent trades brighter)
- Click node to select agent in main view
- Statistics display (density, clustering, degree distribution)

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

669 tests covering all core modules including theory verification and belief system. Run with: `uv run pytest`

---

## 2. Known Limitations

### Architectural

**Search uses protocol-specific surplus**
- Agents evaluate potential partners using the actual bargaining protocol's surplus calculation
- When beliefs are enabled, agents use believed types (not true types) for surplus calculation
- Search is now institution-aware

**2-good economy only**
- `Bundle(x, y)` is hardcoded for 2 goods
- Cobb-Douglas preferences assume 2 goods
- Visualization color encoding assumes 2 goods

**Belief system limitations**
- Price beliefs exist but are not yet consumed by decision logic (deferred to Phase 2)
- Type beliefs track alpha only (not full AgentType with endowments)
- No reinforcement learning or evolutionary dynamics beyond belief updates

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

**No scenario editor GUI**
- YAML scenario files can be loaded but not created/edited in UI
- Must edit YAML files manually for custom scenarios

**No MP4/video export**
- GIF export available but no MP4/video format
- For video, must screen-record or convert GIF externally

**No bargaining sequence replay**
- Edgeworth box shows final trade outcome only
- Cannot step through offer/counter-offer sequence (Rubinstein)

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
| Agent sophistication levels | **Implemented** (belief-enabled vs simple agents, Bayesian vs heuristic updates) |
| Agent beliefs and learning | **Implemented** (type beliefs, memory, belief updates during trade) |
| Market emergence metrics | **Implemented** (trade networks, welfare efficiency, spatial clustering) |

### vs VISUALIZATION.md

| Design Element | Status |
|----------------|--------|
| DearPyGui standalone app | **Implemented** |
| Grid + agents + tooltips | **Implemented** |
| Play/pause/speed controls | **Implemented** |
| Movement trails | **Implemented** (toggleable) |
| Trade animations | **Implemented** |
| Replay mode | **Implemented** |
| Dual viewport comparison | **Implemented** |
| Timeline event markers | **Implemented** (trades, commitments) |
| Comparison mode entry points | **Implemented** (bargaining + matching) |
| Time-series charts | **Implemented** (welfare, trades over time) |
| Setup/Run/Analyze modes | Partial (config modal for setup) |
| Overlay toggles | **Implemented** (trails, perception, heatmap, network) |
| Trade zoom (Edgeworth box) | **Implemented** |
| Agent perspective mode | **Implemented** |
| Export (PNG/GIF/CSV/JSON) | **Implemented** (no MP4) |
| Config files (YAML/JSON) | **Implemented** (YAML scenarios) |
| Scenario browser | **Implemented** (YAML loading) |
| Trade Network Panel | **Implemented** (separate window) |
| Live config modal | **Implemented** (institutional params) |

### vs DESIGN_dashboard_integration.md

| Phase | Status |
|-------|--------|
| Phase 1: Comparison View MVP | **Complete** |
| Phase 2: Scenario Pipeline | **Complete** (YAML scenarios, run_market_emergence) |
| Phase 3: Timeline & Charts | **Complete** (time-series panels) |
| Phase 4: Polish & Export | **Complete** (export capabilities, Edgeworth box, overlays) |

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
├── beliefs.py             # Agent memory, type/price beliefs, update rules
├── bargaining.py
├── search.py
├── matching.py
├── simulation.py
├── batch.py
├── logging/
│   ├── __init__.py
│   ├── events.py          # Includes BeliefSnapshot, TypeBeliefSnapshot
│   ├── logger.py
│   └── formats.py
├── analysis/
│   ├── __init__.py
│   ├── loader.py
│   ├── timeseries.py
│   ├── distributions.py
│   ├── tracking.py
│   └── emergence.py       # Market emergence metrics
├── scenarios/
│   ├── __init__.py
│   ├── schema.py          # YAML scenario schema
│   ├── loader.py          # Scenario loading utilities
│   └── market_emergence.py # MarketEmergenceConfig, run_market_emergence
└── visualization/
    ├── __init__.py
    ├── __main__.py
    ├── app.py             # Main visualization application
    ├── replay.py          # Replay controllers
    ├── browser.py         # Scenario browser UI, LiveConfigModal
    ├── timeseries.py      # Time-series charts (ImPlot)
    ├── edgeworth.py       # Edgeworth box trade visualization
    ├── export.py          # PNG/SVG/GIF/CSV/JSON export
    └── network.py         # Trade network panel

tests/
├── theory/                # Theory verification tests (Phase 0)
│   ├── test_nash_bargaining.py
│   ├── test_rubinstein_bargaining.py
│   ├── test_preferences.py
│   ├── test_gains_from_trade.py
│   └── test_pareto_efficiency.py
├── test_beliefs.py        # Belief system tests (Phase 1)
└── ...                    # Other test modules
```

---

**Document Version:** 0.2.0
**Last Updated:** 2026-01-07 (visualization polish complete)
