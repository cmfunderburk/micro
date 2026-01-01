# Visualization MVP Specification

**Status:** Implementation spec for Ralph
**Date:** 2026-01-01
**Goal:** Minimal viable visualization of the search-and-exchange simulation

---

## 1. Context

### What Exists

The simulation core is complete in `src/microecon/`:

```
bundle.py        - Bundle(x, y) for 2-good economy
preferences.py   - CobbDouglas(alpha) utility functions
agent.py         - Agent with private_state, perception_radius, discount_factor
grid.py          - Grid(size) with Position, movement, spatial queries
bargaining.py    - Nash bargaining solution and trade execution
search.py        - Target evaluation and movement decisions
simulation.py    - Simulation engine with step(), run(), get_state()
```

### Key APIs for Visualization

```python
from microecon import (
    Simulation, Grid, Position, Agent, Bundle,
    create_simple_economy
)

# Create a simulation
sim = create_simple_economy(n_agents=10, grid_size=15, seed=42)

# Access agents and positions
for agent in sim.agents:
    pos = sim.grid.get_position(agent)
    # pos.row, pos.col (0-indexed, origin top-left)
    # agent.id (unique string like "agent_0")
    # agent.preferences.alpha (float in 0-1)
    # agent.endowment (Bundle with .x, .y)
    # agent.utility() -> float

# Step simulation
trades = sim.step()  # Returns list[TradeEvent]

# TradeEvent has:
#   .tick, .agent1_id, .agent2_id, .outcome
# BargainingOutcome has:
#   .allocation_1, .allocation_2, .gains_1, .gains_2, .trade_occurred

# State snapshot
state = sim.get_state()  # SimulationState
# state.tick, state.total_trades, state.agent_positions, state.agent_utilities

# Aggregate metrics
sim.total_welfare()   # Sum of all utilities
sim.welfare_gains()   # Cumulative gains from trade
```

---

## 2. Technology

**Framework:** DearPyGui (as specified in VISUALIZATION.md)

```bash
uv add dearpygui
```

DearPyGui provides:
- GPU-accelerated rendering (handles 100-500 agents easily)
- `drawlist` with layers for grid/agents/overlays
- Built-in widgets for controls, panels, sliders
- ImPlot integration for charts
- Immediate-mode paradigm

---

## 3. MVP Scope

### In Scope (Must Have)

1. **Grid rendering**
   - NxN grid with subtle grid lines
   - Scales to fit window while maintaining aspect ratio

2. **Agent rendering**
   - Circles/dots at grid positions
   - Color encodes agent's alpha parameter (preference for good x)
   - Use a perceptually uniform colormap (e.g., viridis or a warm-cool diverging scale)
   - Multiple agents at same position: offset slightly or show count indicator

3. **Animation**
   - Discrete tick-by-tick updates (snappy, not interpolated)
   - Configurable tick rate (ticks per second)

4. **Playback controls**
   - Play / Pause toggle
   - Step forward (single tick)
   - Speed slider (0.5x to 10x)
   - Reset button (restart simulation)

5. **Agent inspection**
   - Hover tooltip showing: agent_id, alpha, endowment (x, y), current utility
   - No click interactions needed for MVP

6. **Trade indication**
   - Brief visual flash or highlight when trade occurs
   - Draw line between trading agents for ~0.5 seconds

7. **Metrics panel**
   - Current tick
   - Total trades
   - Total welfare
   - Welfare gains from trade

### Out of Scope (Defer)

- Movement trails
- Trade zoom view / Edgeworth box
- Time series charts
- Export (PNG, GIF, CSV)
- Configuration GUI (use code to set parameters)
- Information asymmetry visualization
- Perception radius overlay
- Agent selection / detailed inspection panel

---

## 4. Architecture

### Coupling: Live Mode

The visualization directly observes a running simulation. No replay/logging infrastructure needed for MVP.

```
┌─────────────────┐         ┌─────────────────┐
│   Simulation    │────────▶│  Visualization  │
│   (microecon)   │  reads  │   (DearPyGui)   │
└─────────────────┘         └─────────────────┘
```

### Control Flow

```python
# Main loop (conceptual)
while running:
    if playing and time_for_next_tick():
        trades = simulation.step()
        pending_trade_animations.extend(trades)

    render_grid()
    render_agents()
    render_trade_animations()
    render_metrics()

    dpg.render_dearpygui_frame()
```

### File Structure

```
src/microecon/
    visualization/
        __init__.py
        app.py          # Main application, window setup, main loop
        renderer.py     # Grid and agent rendering
        controls.py     # Playback controls widget
        metrics.py      # Metrics panel widget
        colors.py       # Color scheme and mapping functions
```

Or simpler for MVP:
```
src/microecon/
    visualization/
        __init__.py
        app.py          # Everything in one file initially
```

---

## 5. Detailed Requirements

### 5.1 Window Layout

```
┌────────────────────────────────────────────────────────────┐
│  Microecon Simulation                              [_][□][X]│
├────────────────────────────────────┬───────────────────────┤
│                                    │  Metrics              │
│                                    │  ────────             │
│         Grid Canvas                │  Tick: 42             │
│         (square, centered)         │  Trades: 7            │
│                                    │  Welfare: 156.3       │
│                                    │  Gains: 23.4          │
│                                    │                       │
├────────────────────────────────────┴───────────────────────┤
│  [▶ Play]  [Step]  Speed: [━━━●━━━━━]  [Reset]             │
└────────────────────────────────────────────────────────────┘
```

- Window default size: 1200 x 800
- Grid canvas: square, takes most of left side
- Metrics panel: right side, ~200px wide
- Controls: bottom strip, ~50px tall

### 5.2 Grid Rendering

- Draw grid lines in light gray (#DDDDDD or similar)
- Grid cell size = canvas_size / grid.size
- Leave small margin around grid
- Position (0, 0) is top-left corner

### 5.3 Agent Rendering

**Position mapping:**
```python
def grid_to_canvas(pos: Position, cell_size: float, margin: float) -> tuple[float, float]:
    x = margin + (pos.col + 0.5) * cell_size
    y = margin + (pos.row + 0.5) * cell_size
    return (x, y)
```

**Color mapping (alpha → color):**
- Low alpha (prefers good y): one color (e.g., blue)
- High alpha (prefers good x): another color (e.g., orange)
- Use linear interpolation or a colormap

```python
def alpha_to_color(alpha: float) -> tuple[int, int, int]:
    # Example: interpolate between blue and orange
    # alpha=0 → blue (70, 130, 180)
    # alpha=1 → orange (255, 140, 0)
    r = int(70 + alpha * (255 - 70))
    g = int(130 + alpha * (140 - 130))
    b = int(180 + alpha * (0 - 180))
    return (r, g, b)
```

**Size:** Agent radius ~40% of cell size

**Multiple agents at same position:**
- Offset each by small amount in a circle pattern, or
- Draw single circle with count badge

### 5.4 Trade Animation

When a trade occurs:
1. Draw a line between the two trading agents
2. Briefly highlight both agents (glow or size pulse)
3. Fade out over ~0.3-0.5 seconds (real time, not ticks)

Track pending animations:
```python
@dataclass
class TradeAnimation:
    agent1_pos: Position
    agent2_pos: Position
    start_time: float
    duration: float = 0.5
```

### 5.5 Hover Tooltip

Use DearPyGui's tooltip or draw custom overlay:

```python
# On hover over agent circle:
with dpg.tooltip(parent=agent_item):
    dpg.add_text(f"Agent: {agent.id}")
    dpg.add_text(f"Alpha: {agent.preferences.alpha:.2f}")
    dpg.add_text(f"Endowment: ({agent.endowment.x:.1f}, {agent.endowment.y:.1f})")
    dpg.add_text(f"Utility: {agent.utility():.2f}")
```

For drawlist-based rendering, detect hover via mouse position + hit testing.

### 5.6 Playback Controls

| Control | Behavior |
|---------|----------|
| Play/Pause | Toggle auto-advance. Shows "▶" when paused, "⏸" when playing |
| Step | Advance one tick (only enabled when paused) |
| Speed | Slider from 0.5 to 10 ticks/second |
| Reset | Create new simulation with same parameters |

### 5.7 Metrics Panel

Update every frame:
```python
dpg.set_value(tick_text, f"Tick: {sim.tick}")
dpg.set_value(trades_text, f"Trades: {sim.get_state().total_trades}")
dpg.set_value(welfare_text, f"Welfare: {sim.total_welfare():.1f}")
dpg.set_value(gains_text, f"Gains: {sim.welfare_gains():.1f}")
```

---

## 6. Entry Point

Create a runnable script:

```python
# src/microecon/visualization/app.py

def run_visualization(
    n_agents: int = 10,
    grid_size: int = 15,
    seed: int | None = None
):
    """Launch the visualization window."""
    sim = create_simple_economy(n_agents, grid_size, seed=seed)
    # ... setup DearPyGui window and run loop
```

And a convenience entry:

```python
# Can be run as: uv run python -m microecon.visualization
# or add a script entry point
```

---

## 7. Testing Approach

### Manual Testing Priorities

1. Agents render at correct grid positions
2. Colors correctly reflect alpha values
3. Play/pause/step controls work
4. Speed slider affects tick rate
5. Trades show visual indication
6. Metrics update correctly
7. Hover tooltips appear with correct data
8. Window resizing maintains aspect ratio

### Automated Tests (Optional for MVP)

- Unit test color mapping function
- Unit test grid-to-canvas coordinate conversion

---

## 8. Example Session

```python
from microecon.visualization import run_visualization

# Launch with defaults
run_visualization()

# Or customize
run_visualization(n_agents=20, grid_size=20, seed=123)
```

User should see:
1. Window opens with grid and scattered agents
2. Agents colored by their alpha (preference parameter)
3. Click Play → agents start moving toward each other
4. When two agents meet, trade flash appears
5. Metrics update showing trades and welfare increasing
6. Hover over agent to see details

---

## 9. Success Criteria

MVP is complete when:

- [x] Window launches without errors
- [x] Grid displays with correct dimensions
- [x] Agents render at correct positions with alpha-based colors
- [x] Play/Pause toggles automatic stepping
- [x] Step button advances one tick
- [x] Speed slider changes tick rate
- [x] Trade events show visual indication
- [x] Hover tooltips show agent details
- [x] Metrics panel shows tick, trades, welfare, gains
- [x] Reset creates fresh simulation

---

## 10. References

- **VISUALIZATION.md** - Full design vision and rationale
- **DearPyGui docs** - https://dearpygui.readthedocs.io/
- **DearPyGui drawing API** - https://dearpygui.readthedocs.io/en/latest/documentation/drawing-api.html

---

**Document Version:** 1.0
**Created:** 2026-01-01
