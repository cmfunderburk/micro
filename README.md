# microecon

Research-first agent-based microeconomics platform that gives canonical theoretical microeconomics computational form. Extremely early-stage development.

## Goals

**Institutional visibility**: making economic institutions (bargaining protocols, information structures, search mechanisms) explicit, configurable, and comparable.

By making institutions visible, we can ask: *What difference does the institution make?* Same preferences, same endowments, different rules - what emerges?

## Quick Start

```bash
# 1. Install dependencies (requires Python 3.12+, Node.js 18+)
pip install uv
uv sync
cd frontend && npm install && cd ..

# 2. Run the web visualization
./scripts/dev.sh
# Open http://localhost:5173

# 3. Run a market emergence analysis
uv run python -c "
from microecon.scenarios import run_demonstration
run_demonstration(n_agents=30, ticks=100)
"
```

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for Python dependency management and npm for the frontend.

```bash
# Clone the repository
git clone <repo-url>
cd microecon

# Install uv if you don't have it
pip install uv

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Run tests to verify installation
uv run pytest
```

## Key Concepts

### Agents

Agents have:
- **Preferences**: Cobb-Douglas utility function with parameter `alpha` (0 < alpha < 1)
- **Endowments**: Initial holdings of two goods (x, y)
- **Perception radius**: How far they can see other agents

Agents with different alpha values and complementary endowments have potential gains from trade.

### Protocols

The platform supports swappable institutional rules:

**Bargaining Protocols**:
- `NashBargainingProtocol`: Axiomatic solution maximizing Nash product (symmetric, fair)
- `RubinsteinBargainingProtocol`: Strategic alternating-offers (first-mover advantage, patience matters)

**Matching Protocols**:
- `OpportunisticMatchingProtocol`: Any co-located pair can trade (myopic)
- `StableRoommatesMatchingProtocol`: Irving's algorithm forms stable pairs (globally optimal)

### Information Environments

- `FullInformation`: Agents observe each other's true preferences and endowments
- `NoisyAlphaInformation`: Agents observe noisy estimates of counterparty preferences

### Simulation Loop

Each tick follows four phases:
1. **Search**: Agents evaluate visible targets and compute expected surplus
2. **Movement**: Agents move toward best opportunity
3. **Matching**: Protocol determines trading pairs
4. **Exchange**: Pairs bargain and trade

## Examples

### Run a Simple Simulation

```python
from microecon.simulation import create_simple_economy

# Create a simulation with 10 agents
sim = create_simple_economy(n_agents=10, grid_size=15, seed=42)

# Run for 100 ticks
sim.run(ticks=100)

print(f"Final welfare: {sim.total_welfare():.2f}")
print(f"Total trades: {len(sim.trades)}")
```

### Compare Bargaining Protocols

```python
from microecon.scenarios import MarketEmergenceConfig, run_market_emergence
from microecon.bargaining import NashBargainingProtocol, RubinsteinBargainingProtocol

config = MarketEmergenceConfig(n_agents=30, ticks=100, seed=42)

# Run with Nash bargaining
result_nash = run_market_emergence(config, bargaining_protocol=NashBargainingProtocol())

# Run with Rubinstein bargaining
result_rub = run_market_emergence(config, bargaining_protocol=RubinsteinBargainingProtocol())

# Compare efficiency
print(f"Nash efficiency: {result_nash.analysis.efficiency.efficiency_ratio:.1%}")
print(f"Rubinstein efficiency: {result_rub.analysis.efficiency.efficiency_ratio:.1%}")
```

### Analyze Market Emergence

```python
from microecon.scenarios import run_demonstration

# Run full comparison across protocols
results = run_demonstration(n_agents=50, ticks=150, verbose=True)

# Access detailed analysis
for name, result in results.items():
    a = result.analysis
    print(f"\n{name}:")
    print(f"  Trades: {a.network.total_trades}")
    print(f"  Efficiency: {a.efficiency.efficiency_ratio:.1%}")
    print(f"  Network density: {a.network.density:.3f}")
```

## Running the Web Visualization

The web frontend provides a full-featured visualization:

**Core Features:**
- Real-time grid view of agents colored by preference (alpha)
- Play/pause/step controls with speed adjustment
- Trade animations and movement trails
- Metrics panel (welfare, trades, gains)
- Time-series charts (welfare and trades over time)
- Keyboard shortcuts (Space: play/pause, Arrow keys: step)

**Advanced Features:**
- **Comparison Mode**: Side-by-side protocol comparison (same seed, different rules)
- **Replay Mode**: Load and seek through saved simulation runs
- **Perspective Mode**: View simulation from any agent's perspective
- **Belief Panel**: Visualize agent beliefs about others
- **Trade Inspection**: Edgeworth box analysis of any trade
- **Scenario Browser**: Load pre-defined scenarios by complexity

```bash
# Start the web frontend (recommended)
./scripts/dev.sh
# Open http://localhost:5173

# Or start server and frontend separately:
uv run uvicorn server.app:create_app --factory --port 8000  # Terminal 1
cd frontend && npm run dev                                   # Terminal 2
```

## Project Structure

```
microecon/               # Core simulation library (Python)
    bundle.py            # 2-good bundles
    preferences.py       # Utility functions (Cobb-Douglas)
    agent.py             # Agent with private state / observable type
    grid.py              # Spatial grid and positions
    information.py       # Information environment abstraction
    beliefs.py           # Agent beliefs and learning
    bargaining.py        # Bargaining protocols (Nash, Rubinstein)
    search.py            # Target evaluation and movement
    matching.py          # Matching protocols
    simulation.py        # Main simulation engine
    batch.py             # Parameter sweeps
    logging/             # Run capture and replay
    analysis/            # Time series, distributions, emergence
    scenarios/           # YAML scenarios and market emergence

server/                  # FastAPI WebSocket server
    app.py               # Application factory
    websocket.py         # WebSocket handlers
    simulation_manager.py # Simulation lifecycle
    routes.py            # REST API endpoints

frontend/                # React/Vite web UI
    src/components/      # UI components (Grid, Charts, Controls, etc.)
    src/hooks/           # WebSocket, keyboard shortcuts
    src/store/           # Zustand state management

scenarios/               # YAML scenario definitions
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=microecon

# Run specific test file
uv run pytest tests/test_simulation.py -v
```

## Documentation

- [VISION.md](VISION.md): Project identity, methodology, research agenda
- [STATUS.md](STATUS.md): Current capabilities and known limitations
- [theoretical-foundations.md](theoretical-foundations.md): Textbook mappings and derivations
- [CLAUDE.md](CLAUDE.md): Development guidance

## Platform Support

- **Linux**: Primary platform, fully tested
- **macOS/Windows**: May work but not tested

## License

[To be determined]

## Status

See [STATUS.md](STATUS.md) for current capabilities and known limitations.
