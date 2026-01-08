# Visualization Reference Guide v2

**Status:** Implementation reference document
**Date:** 2026-01-08
**Purpose:** Document the current visualization layer implementation and guide future development

---

## 1. Technology Stack

### Previous: DearPyGui (Archived)
The original VISUALIZATION.md specified DearPyGui for a desktop application. This has been archived to `.archived/visualization-dearpygui/`.

### Current: Web Frontend

**Frontend (React/Vite)**
- React 19 with TypeScript
- Vite build tooling
- Zustand state management
- Tailwind CSS 4 styling
- Canvas-based grid rendering
- Recharts for time-series
- D3-force for network visualization
- Radix UI for headless components

**Backend (FastAPI/WebSocket)**
- FastAPI server
- WebSocket for real-time tick updates
- REST API for configuration and replay
- Single shared simulation instance (multi-client broadcast)

**Start Commands:**
```bash
# Server (port 8000)
uv run uvicorn server.app:create_app --factory --port 8000

# Frontend (port 5173)
cd frontend && npm run dev
```

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Browser (React)                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐  ┌─────────────────────────┐  ┌────────────────────┐  │
│  │ Left Column  │  │ Center Column           │  │ Right Column       │  │
│  │ (200px)      │  │ (flex, max 600px)       │  │ (320px)            │  │
│  │              │  │                         │  │                    │  │
│  │ - Metrics    │  │ Canvas Grid             │  │ Welfare Chart      │  │
│  │ - Overlays   │  │ ├─ Grid lines           │  │                    │  │
│  │ - Beliefs    │  │ ├─ Agents (colored)     │  ├────────────────────┤  │
│  │ - Perspective│  │ ├─ Trails (overlay)     │  │ Trade Count Chart  │  │
│  │              │  │ ├─ Perception (overlay) │  │                    │  │
│  │              │  │ └─ Connections (overlay)│  │                    │  │
│  └──────────────┘  └─────────────────────────┘  └────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Header: Controls, Mode Buttons, Export                            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  [Modals: Config | Trade History | Edgeworth Box | Network Panel]       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │ WebSocket (real-time ticks)
         │ REST API (config, replay, scenarios)
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FastAPI Server                                                          │
│  ├─ websocket.py  - Connection manager, simulation loop                 │
│  ├─ routes.py     - REST endpoints                                      │
│  └─ simulation_manager.py - Lifecycle management                        │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  microecon.simulation.Simulation                                         │
│  (Python core library)                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Operational Modes

The frontend supports three distinct modes:

### Normal Mode (Default)
Three-column layout for live simulation observation:
- Real-time agent movement and trades
- Toggle overlays independently
- Inspect individual agents and trades

### Comparison Mode
Dual-grid side-by-side for institutional comparison:
- Two simulations with different configurations (typically Nash vs Rubinstein)
- Synchronized tick advancement
- Dual welfare/trade charts with both lines
- Comparative metrics panel

### Replay Mode
Playback of saved simulation runs:
- Full run loaded into client memory
- Timeline slider for instant seeking
- Variable playback speed (0.1x-10x)
- Step forward/backward controls

---

## 4. Grid Visualization

### Rendering Technology
Canvas 2D context (not SVG) for performance at scale. Grid dimensions match simulation `grid_size` parameter (5-50 cells).

### Agent Representation

**Color encoding:**
- Alpha preference (α) maps to hue: 0 = red, 1 = blue (via purple gradient)
- HSL interpolation preserves saturation and lightness
- Consistent with economics intuition (different preferences = different colors)

**Shape and sizing:**
- Circular agents, radius = `cellSize * 0.35`
- Co-located agents arranged in circular pattern around cell center with reduced radius
- Maintains visibility even with multiple agents per cell

**Selection states:**
- Hover: White outline ring (2px)
- Selected: Amber outline ring (3px)

### Trade Animation
Recent trades (current tick) visualized as green connecting lines with 2-second fade-out. Uses requestAnimationFrame for smooth animation.

---

## 5. Overlays (All Toggleable)

All overlays default to OFF per the "start minimal" design principle.

### Implemented

| Overlay | Description | Visual |
|---------|-------------|--------|
| **Trails** | Last 20 positions per agent | Fading gradient path |
| **Perception Radius** | Selected agent's observation range | Indigo circle |
| **Trade Connections** | Lines between agents who traded | Purple lines, opacity fades with time |
| **Belief Connections** | Type beliefs between agents | Blue directional lines, opacity = confidence |

### Not Yet Implemented

- **Surplus heatmap**: Opportunity density visualization
- **Purpose-encoded trails**: Color trails by movement motivation (seeking trade, random exploration)

---

## 6. Information Panels

### Metrics Panel (Left Column)
Live aggregate statistics:
- Total welfare
- Trade count
- Current tick

### Belief Panel (Left Column)
For selected agent, displays:
- Price belief (mean, variance, n_observations)
- Memory size (number of remembered trades)
- Type beliefs about other agents (top 10 by confidence)

### Time-Series Charts (Right Column)

**Welfare Chart:**
- Green line plot of total welfare over time
- Auto-downsampled to ~100 points for performance
- Recharts implementation with tooltips

**Trade Count Chart:**
- Cumulative trades over simulation time
- Same rendering approach as welfare chart

---

## 7. Trade Inspection

### Trade History Panel
Scrollable list of recent trades (bounded to 100):
- Reverse chronological order
- Each entry shows: tick, agent IDs (last 6 chars), total gains
- Click to select for Edgeworth box inspection

### Edgeworth Box Modal

Full economic visualization of 2-agent, 2-good trades:

**Elements rendered:**
- Box dimensions = total endowments of both agents
- Contract curve (fuchsia): locus of Pareto-optimal allocations
- Indifference curves:
  - Agent A (blue): pre-trade and post-trade utility levels
  - Agent B (orange): reflected to A's coordinate frame
- Endowment point (amber): initial allocation
- Final allocation (green): post-trade position
- Arrow: white line showing direction of trade

**Mathematical basis:**
- Cobb-Douglas utility: u(x,y) = x^α × y^(1-α)
- Contract curve: all points where MRS_A = MRS_B
- Implemented in `edgeworthMath.ts`

---

## 8. Trade Network Visualization

D3-force network graph showing trading relationships:

### Layouts
- **Force-directed**: Physics simulation with repulsion, link attraction, collision avoidance
- **Circular**: Static ring arrangement

### Visual Encoding
- **Nodes**: Agent circles colored by alpha
- **Edges**: Purple lines between trading partners
  - Width: proportional to trade frequency
  - Opacity: decreases with time since last trade (fades after 50 ticks)

### Interaction
- Drag nodes (force layout only)
- Hover tooltips showing agent ID and alpha

---

## 9. Perspective Mode (Information Asymmetry)

View simulation from a specific agent's point of view:

**Visual changes:**
- Agents outside perception radius: grayed out (opacity 0.15) or hidden
- Perspective agent: highlighted with green circle
- Optional ground truth overlay shows true positions dimly

**Purpose:** Supports research into information structure effects by letting users experience the partial information available to each agent.

---

## 10. Configuration

### Configuration Modal

Adjustable parameters via sliders and controls:

| Parameter | Range | Notes |
|-----------|-------|-------|
| Number of Agents | 2-50 | Slider |
| Grid Size | 5-50 | Slider |
| Perception Radius | 1-20 | 0.5 step |
| Discount Factor | 0.5-1.0 | 0.01 step, affects Rubinstein bargaining |
| Bargaining Protocol | Nash / Rubinstein | Button group |
| Matching Protocol | Opportunistic / Stable Roommates | Button group |
| Use Beliefs | On/Off | Toggle |
| Random Seed | Integer or blank | Text input |

Changes trigger simulation reset via REST API.

### Scenario Browser

Pre-defined scenarios loaded from YAML files:
- Grouped by complexity level (1-4 stars)
- Shows: title, description, agent count, grid size
- Load sets configuration including specific agent positions

---

## 11. Export Capabilities

### Visual Exports

| Format | Description |
|--------|-------------|
| **PNG** | Canvas snapshot at current tick |
| **SVG** | Not yet implemented |
| **GIF** | Animation export (basic implementation) |

### Data Exports

| Format | Contents |
|--------|----------|
| **CSV** | Agents (id, position, endowment, alpha, utility), Trades, Time series |
| **JSON** | Full state snapshot (tick, config, agents, trades, history) |

### Not Yet Implemented
- High-resolution publication-quality exports
- Vector graphics (SVG/PDF) for journal figures
- Configurable export regions/selections

---

## 12. Controls & Interaction

### Mouse Interactions
- **Hover agent**: White highlight ring, tooltip with details
- **Click agent**: Select (amber ring), populate belief panel, enable perception radius overlay
- **Click empty**: Deselect
- **Grid**: Cursor changes to crosshair

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play/Pause |
| Right Arrow | Step forward (replay) or single step (paused) |
| Left Arrow | Step backward (replay only) |
| R | Reset simulation (normal mode only) |

### Not Yet Implemented
- Pan and zoom on grid
- Click-for-detail popover (vs. full modal)

---

## 13. WebSocket Protocol

### Commands (Client → Server)

| Command | Parameters | Purpose |
|---------|------------|---------|
| `start` | - | Resume simulation |
| `stop` | - | Pause simulation |
| `step` | - | Single tick advance |
| `reset` | - | Reset to initial state |
| `speed` | `speed: number` | Set ticks/second |
| `config` | `config: {...}` | Change configuration |
| `comparison` | `config1, config2, label1, label2` | Enter comparison mode |
| `exit_comparison` | - | Return to normal mode |

### Messages (Server → Client)

| Type | Payload | When |
|------|---------|------|
| `init` | Full tick data + config | On connect |
| `tick` | Agents, trades, metrics | Each simulation tick |
| `status` | `{running: boolean}` | Start/stop |
| `config` | Full data + new config | After config change |
| `comparison_tick` | Both simulations' data | Each comparison tick |

---

## 14. Performance Characteristics

### Memory Bounds
- Time series history: 1000 points max
- Position trails: 20 positions per agent
- Trade connections: 100 most recent
- Trade history: 100 most recent

### Rendering Optimizations
- Canvas requestAnimationFrame only when animating trades
- Charts downsample to ~100 points
- D3 network: full re-render only on structure change
- Zustand selectors prevent unnecessary re-renders

### Tested Scale
- Designed for 100-500 agents per VISION.md
- Practical testing up to 50 agents in current UI
- Grid size 5-50 cells

---

## 15. Visual Design

### Color Palette

| Element | Color | Tailwind |
|---------|-------|----------|
| Background | Near-black | zinc-950 |
| Panels | Dark gray | zinc-900 |
| Borders | | zinc-800 |
| Primary text | Off-white | zinc-50 |
| Secondary text | | zinc-400 |
| Trade animations | Green | green-500 |
| Selection | Amber | amber-400 |
| Perception | Indigo | indigo-500 |
| Connections | Purple | purple-500 |

### Agent Colors
HSL interpolation from α=0 (red, hue 0°) to α=1 (blue, hue 240°).

### Typography
System fonts via Tailwind defaults. Monospace for technical values.

### Grid Treatment
Subtle gray grid lines (zinc-700). Achieves continuous-space feel per original design.

---

## 16. Gap Analysis vs. Original VISUALIZATION.md

### Fully Implemented
- Multi-purpose tool (research, demonstration)
- Flat design + game-like aesthetic
- Subtle grid treatment
- Color-based agent encoding
- Hover tooltips
- Layered trade visualization (quick animation + detailed inspection)
- Edgeworth box with indifference curves and contract curve
- Toggleable overlays (trails, perception, connections)
- Agent perspective mode
- Speed control
- Modal/adaptive layout (normal, comparison, replay)
- Hybrid configuration (GUI sliders + config/scenario files)
- Time series charts
- Keyboard shortcuts (basic)
- Mouse interaction (hover, click, select)

### Partially Implemented
- **Export formats**: PNG, CSV, JSON implemented; SVG/vector not yet
- **Animation**: GIF export exists; publication-quality not yet
- **Scale**: Tested to 50 agents; 100-500 target requires further optimization

### Not Yet Implemented
- Pan and zoom on grid
- Click-for-detail popover (currently uses modals)
- Purpose-encoded trails (color by movement motivation)
- Surplus heatmaps
- Benchmark comparison overlays (Nash bargaining prediction vs. actual)
- Protocol-aware search visualization
- Colorblind accessibility (noted as out of scope)

---

## 17. Future Development Priorities

Based on CLAUDE.md and original VISUALIZATION.md:

**Near-term polish:**
1. Smaller viewport handling (<1280px breakpoints)
2. Agent details compact popover on click
3. SVG export for publication figures

**Research value additions:**
4. Benchmark comparison overlays (show theoretical prediction vs. actual)
5. Protocol-aware search visualization (different protocols, different search logic)
6. Additional bargaining protocols (TIOLI, posted prices, double auction)

**Scale and performance:**
7. Pan and zoom for large grids
8. WebGL rendering for 500+ agents
9. Efficient replay seeking for runs >1000 ticks

---

## 18. File Structure Reference

```
frontend/src/
├── App.tsx                    # Main layout, mode routing
├── main.tsx                   # Entry point
├── types/simulation.ts        # TypeScript interfaces
├── hooks/
│   ├── useSimulationSocket.ts # WebSocket connection
│   └── useKeyboardShortcuts.ts
├── store/
│   ├── index.ts               # Main Zustand store
│   ├── comparisonStore.ts     # Comparison mode state
│   └── replayStore.ts         # Replay mode state
└── components/
    ├── Grid/                  # Canvas rendering
    ├── Charts/                # Recharts time-series
    ├── Config/                # ConfigModal, ExportMenu
    ├── Controls/              # Overlays, perspective
    ├── TradeInspection/       # History, Edgeworth box
    ├── Network/               # D3-force graph
    ├── Beliefs/               # Agent belief panel
    ├── Comparison/            # Dual-grid view
    ├── Replay/                # Playback interface
    ├── Scenarios/             # Scenario browser
    └── ui/                    # Primitives (button, slider, dialog)

server/
├── app.py                     # FastAPI factory
├── websocket.py               # WebSocket handlers
├── routes.py                  # REST API
└── simulation_manager.py      # Simulation lifecycle
```

---

**Document Version:** 2.0
**Created:** 2026-01-08
**Supersedes:** VISUALIZATION.md v1.1 (DearPyGui specification)
**Changes:** Complete rewrite reflecting web frontend implementation
