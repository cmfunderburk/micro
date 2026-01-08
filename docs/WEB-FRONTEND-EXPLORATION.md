# Web Frontend Exploration: Python Backend + TypeScript UI

**Status:** Brainstorming
**Date:** 2025-01-07
**Purpose:** Evaluate architecture options for replacing DearPyGui with a browser-based TypeScript frontend while keeping the Python simulation core.

---

## Table of Contents

1. [Motivation](#1-motivation)
2. [Goals and Non-Goals](#2-goals-and-non-goals)
3. [Architecture Overview](#3-architecture-overview)
4. [Communication Patterns](#4-communication-patterns)
5. [TypeScript Ecosystem Options](#5-typescript-ecosystem-options)
6. [UI Framework Comparison](#6-ui-framework-comparison)
7. [Data Flow Design](#7-data-flow-design)
8. [Migration Strategy](#8-migration-strategy)
9. [Development Workflow](#9-development-workflow)
10. [Risks and Mitigations](#10-risks-and-mitigations)
11. [Decision Points](#11-decision-points)
12. [Proof of Concept Scope](#12-proof-of-concept-scope)

---

## 0. Key Constraint: Local-Only Operation

**Important simplification:** Both backend and frontend run on the same machine. There is no requirement for remote/network access at this point.

### Implications

| Concern | Remote Deployment | Local-Only (Our Case) |
|---------|-------------------|------------------------|
| Network latency | Real concern (10-100ms) | Negligible (<1ms localhost) |
| CORS configuration | Required for security | Still needed for dev, but simpler |
| Authentication | Needed | Not needed |
| SSL/TLS | Required | Not needed |
| Deployment complexity | High | Just "run two processes" |
| Electron/Tauri viability | Overkill for web deploy | Actually viable option |

### Alternative: Electron or Tauri

Since we're local-only, wrapping in a desktop app becomes viable:

```
┌────────────────────────────────────────────────────────────┐
│                    Electron / Tauri App                     │
│  ┌─────────────────────┐    ┌─────────────────────────┐    │
│  │    Python Process   │◄──►│    Chromium WebView     │    │
│  │    (subprocess)     │IPC │    (TypeScript UI)      │    │
│  └─────────────────────┘    └─────────────────────────┘    │
└────────────────────────────────────────────────────────────┘
```

**Tauri** is particularly interesting:
- Rust-based, much smaller than Electron (~10MB vs ~150MB)
- Can spawn Python as subprocess
- IPC via commands (like REST but faster)
- Single executable distribution possible

However, for initial exploration, **two-process localhost** is simpler:
- `python -m microecon.server` (FastAPI on localhost:8000)
- `npm run dev` (Vite on localhost:5173)

We can always wrap in Tauri later if single-app distribution becomes desirable.

### Alternative: pywebview (Simplest Local Option)

**pywebview** is a Python library that creates a native window with an embedded browser:

```python
import webview
import threading

def start_server():
    # Start FastAPI in background
    uvicorn.run(app, host="127.0.0.1", port=8000)

threading.Thread(target=start_server, daemon=True).start()
webview.create_window('Microecon', 'http://127.0.0.1:8000')
webview.start()
```

**Pros:**
- Single Python entry point (`python -m microecon.webviz`)
- No Node.js needed at runtime (pre-build the frontend)
- Native window, not a browser tab
- Simple to distribute (just Python + built frontend assets)

**Cons:**
- Uses system WebView (quality varies by OS)
- Less powerful than Electron/Tauri
- No DevTools in production mode

This could be a good **deployment** option even if we use Vite dev server during development.

---

## 1. Motivation

### 1.1 Current State: DearPyGui

The visualization layer is **functionally complete** (per VISUALIZATION.md):
- Grid rendering with agent coloring
- Play/pause/step controls, speed slider
- Trade animations, hover tooltips, click selection
- Overlays (trails, perception radius, surplus heatmap, trade network)
- Time-series charts (welfare, trade count)
- Edgeworth box trade inspection
- Export (PNG/SVG/GIF/CSV/JSON)
- Live configuration modal
- Trade network panel

**What works well:**
- Direct Python integration (no serialization)
- ImPlot for charts
- Responsive immediate-mode rendering

**Pain points driving this exploration:**

| Issue | Impact |
|-------|--------|
| **Styling limitations** | Hard to achieve polished, modern aesthetics |
| **Layout inflexibility** | Widget positioning is imperative, not declarative |
| **Design iteration speed** | Changes require Python restart, no hot reload |
| **Ecosystem size** | Fewer widgets, components, examples than web |
| **Deployment friction** | Sharing requires Python environment |
| **Customization ceiling** | Complex visualizations (e.g., animated Edgeworth) hit limits |

### 1.2 Why Browser-Based?

The browser platform offers:

1. **Mature styling system** - CSS is expressive, well-documented, tooling-rich
2. **Hot module replacement** - See changes instantly without restart
3. **Visualization ecosystem** - D3, Three.js, Pixi, Observable Plot, etc.
4. **Component libraries** - Hundreds of polished UI kits
5. **Deployment options** - Static hosting, no Python needed for viewer
6. **Responsive design** - Built-in support for different screen sizes
7. **Developer tooling** - Browser DevTools, React/Svelte DevTools
8. **LLM assistance quality** - TypeScript/React are extremely well-covered

### 1.3 Why Keep Python Backend?

1. **Simulation core is proven** - 669 tests, theoretical grounding
2. **NumPy/SciPy ecosystem** - Numerical computing strength
3. **Incremental migration** - Don't rewrite everything at once
4. **Separation of concerns** - UI changes don't touch simulation logic
5. **Analysis pipeline** - Existing logging/analysis stays in Python

---

## 2. Goals and Non-Goals

### 2.1 Goals

1. **Preserve simulation fidelity** - Identical results to current Python-only system
2. **Improve visual design flexibility** - Modern, polished UI achievable
3. **Faster design iteration** - Hot reload, CSS-based styling
4. **Maintain research workflow** - Still works for parameter sweeps, analysis
5. **LLM-assisted development** - Architecture compatible with AI coding assistance
6. **Incremental adoption** - Can run old DearPyGui alongside during transition

### 2.2 Non-Goals (for now)

1. **Port simulation to TypeScript** - Keep Python as source of truth
2. **Real-time multiplayer** - Single-user research tool
3. **Mobile-first design** - Desktop browser is primary target
4. **Production deployment** - Research tool, not SaaS product
5. **Backwards compatibility with DearPyGui** - Clean break is acceptable

---

## 3. Architecture Overview

### 3.1 Recommended Architecture: FastAPI Backend + React/Svelte Frontend

```
┌────────────────────────────────────────────────────────────────────┐
│                         Browser (TypeScript)                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    React or Svelte App                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │ Grid Canvas │  │ Time Series │  │ Controls & Config   │   │  │
│  │  │ (Pixi/D3)   │  │ (Recharts)  │  │ (Component Library) │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │ Edgeworth   │  │ Trade Net   │  │ Agent Inspector     │   │  │
│  │  │ Box (D3)    │  │ (D3 Force)  │  │ (Data Tables)       │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ▲                                      │
│                              │ State Updates                        │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    State Management                           │  │
│  │              (Zustand / Jotai / Svelte Stores)                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               ▲
                               │ WebSocket (live ticks)
                               │ REST API (config, commands)
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                      Python Backend (FastAPI)                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    API Layer                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │ REST Routes │  │ WebSocket   │  │ Session Manager     │   │  │
│  │  │ /api/...    │  │ Handler     │  │ (simulation state)  │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ▲                                      │
│                              │                                      │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                 Existing Simulation Core                      │  │
│  │     (bundle, preferences, agent, grid, bargaining, etc.)      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 Why This Architecture?

| Decision | Rationale |
|----------|-----------|
| **FastAPI** | Modern, async, auto-generates OpenAPI docs, WebSocket support |
| **WebSocket for ticks** | Low-latency push for real-time simulation updates |
| **REST for commands** | Simple request/response for config, start/stop, step |
| **State management** | Decouple data fetching from rendering |
| **Modular visualization** | Different libraries for different components |

### 3.3 Alternative: Server-Sent Events (SSE)

For simpler real-time needs, SSE instead of WebSocket:

```
Browser ◄──── SSE (one-way push) ──── Python
        ────► REST (commands) ────►
```

**Pros:** Simpler server code, auto-reconnect
**Cons:** One-way only, less flexible than WebSocket

### 3.4 Alternative: Polling (Simplest)

```
Browser ────► GET /api/state (poll every 100ms) ────► Python
        ────► POST /api/command ────►
```

**Pros:** Dead simple, works everywhere
**Cons:** Latency, server load, not truly real-time

**Recommendation:** Start with WebSocket for the live simulation feed, REST for everything else.

---

## 4. Communication Patterns

### 4.1 Message Types

```typescript
// Frontend → Backend (commands)
interface Command {
  type: 'start' | 'stop' | 'step' | 'reset' | 'configure';
  payload?: any;
}

// Backend → Frontend (state updates)
interface TickUpdate {
  type: 'tick';
  tick: number;
  agents: AgentSnapshot[];
  trades: TradeEvent[];
  welfare: number;
  beliefs?: BeliefSnapshot[];  // if belief-enabled
}

interface SimulationState {
  type: 'state';
  running: boolean;
  tick: number;
  config: SimulationConfig;
}
```

### 4.2 API Endpoints (Draft)

```
REST API:
  GET  /api/health              - Health check
  GET  /api/config              - Get current configuration
  POST /api/config              - Update configuration
  POST /api/simulation/start    - Start simulation
  POST /api/simulation/stop     - Stop simulation
  POST /api/simulation/step     - Execute one tick
  POST /api/simulation/reset    - Reset to initial state
  GET  /api/simulation/state    - Get current state snapshot
  GET  /api/scenarios           - List available scenarios
  POST /api/scenarios/:name     - Load a scenario
  GET  /api/export/csv          - Export data as CSV
  GET  /api/export/json         - Export data as JSON

WebSocket:
  WS   /ws/simulation           - Real-time tick updates
```

### 4.3 Serialization Considerations

The simulation's dataclasses already have `to_dict()` methods. Key serialization points:

| Data | Size Estimate (10 agents) | Frequency |
|------|---------------------------|-----------|
| Agent snapshots | ~500 bytes | Every tick |
| Trade events | ~200 bytes each | 0-5 per tick |
| Belief snapshots | ~1KB | Every tick (if enabled) |
| Full state dump | ~5KB | On demand |

At 10 ticks/second with 10 agents: ~50KB/s — trivial for WebSocket.

At 100 agents: ~500KB/s — still manageable, but may need throttling or delta encoding.

---

## 5. TypeScript Ecosystem Options

### 5.1 Visualization Libraries

#### Grid/Agent Rendering

| Library | Approach | Performance | Learning Curve | Best For |
|---------|----------|-------------|----------------|----------|
| **Canvas 2D** | Direct draw | Good | Low | Simple grids |
| **Pixi.js** | WebGL 2D | Excellent | Medium | Many agents, animations |
| **D3 + SVG** | Declarative | Moderate | High | Small agent counts, interactions |
| **Konva** | Canvas + events | Good | Medium | Interactive elements |

**Recommendation:** Canvas 2D for MVP, Pixi.js if performance becomes an issue.

#### Charts (Time Series)

| Library | Style | Integration | Best For |
|---------|-------|-------------|----------|
| **Recharts** | React-native | Excellent | Simple charts, React apps |
| **Observable Plot** | D3-based | Good | Data exploration |
| **Chart.js** | Imperative | Good | Quick setup |
| **Plotly.js** | Full-featured | Moderate | Complex plots |
| **uPlot** | Performance | Moderate | High-frequency updates |

**Recommendation:** Recharts for React, or Observable Plot for flexibility.

#### Network Graphs (Trade Network)

| Library | Layout Algorithms | Interactivity | Best For |
|---------|-------------------|---------------|----------|
| **D3-force** | Built-in | Full control | Custom network viz |
| **Cytoscape.js** | Many options | Good | Complex graphs |
| **vis-network** | Easy setup | Good | Quick network viz |
| **Sigma.js** | WebGL | Limited | Large graphs |

**Recommendation:** D3-force for trade network (already doing force-directed in DearPyGui).

#### Specialized: Edgeworth Box

No off-the-shelf Edgeworth box component exists. Options:

1. **D3 custom** - Full control, most work
2. **Canvas 2D** - Direct drawing, moderate work
3. **SVG + React** - Declarative, good for React integration

**Recommendation:** D3 or Canvas 2D — this is a custom visualization regardless.

### 5.2 Comparison Matrix

| Component | Current (DearPyGui) | Proposed (Web) | Improvement |
|-----------|---------------------|----------------|-------------|
| Grid | Custom draw | Canvas 2D or Pixi | Smoother, more styling |
| Time series | ImPlot | Recharts/uPlot | Better styling, tooltips |
| Trade network | Custom draw | D3-force | Better physics, interaction |
| Edgeworth | Custom draw | D3/Canvas | More animation options |
| Controls | dpg widgets | UI library | Much better styling |
| Layout | Imperative | CSS Grid/Flex | Declarative, responsive |

---

## 6. UI Framework Comparison

### 6.1 React

**Pros:**
- Largest ecosystem, most examples
- Excellent LLM assistance (most training data)
- Many component libraries (Chakra, MUI, Radix, shadcn)
- React DevTools for debugging
- Strong TypeScript support

**Cons:**
- More boilerplate than alternatives
- Virtual DOM overhead (rarely matters)
- Learning curve for hooks/effects

### 6.2 Svelte

**Pros:**
- Less boilerplate, more intuitive
- Compile-time, smaller bundle
- Built-in stores for state
- Animations built-in
- Reactive statements are natural

**Cons:**
- Smaller ecosystem than React
- Fewer component libraries
- Less LLM training data (but still good)

### 6.3 Vue

**Pros:**
- Middle ground complexity
- Good tooling
- Options API for familiarity

**Cons:**
- Smaller ecosystem than React
- Composition API adds learning curve

### 6.4 Solid.js

**Pros:**
- React-like but true reactivity
- Excellent performance
- Fine-grained updates

**Cons:**
- Smallest ecosystem
- Fewer resources for learning

### 6.5 Recommendation

For this project, considering:
- LLM-assisted development (you're new to TypeScript)
- Ecosystem size matters for finding solutions
- Visualization libraries integrate well with both

**Primary recommendation: React + shadcn/ui**
- shadcn/ui provides beautiful, accessible components
- Tailwind CSS for styling (utility classes, easy to learn)
- Largest ecosystem for solving problems
- LLMs are excellent at React/TypeScript

**Alternative: Svelte + Skeleton**
- If React feels too heavy
- Svelte's reactivity model is more intuitive
- Skeleton is a good Svelte component library

---

## 7. Data Flow Design

### 7.1 Frontend State Structure

```typescript
interface AppState {
  // Connection
  connected: boolean;

  // Simulation control
  running: boolean;
  speed: number;  // ticks per second

  // Current state
  tick: number;
  agents: Map<string, AgentState>;
  trades: TradeEvent[];

  // Configuration
  config: SimulationConfig;

  // UI state
  selectedAgentId: string | null;
  overlays: {
    trails: boolean;
    perceptionRadius: boolean;
    surplusHeatmap: boolean;
    tradeNetwork: boolean;
  };

  // Historical data (for charts)
  history: {
    welfare: number[];
    tradeCounts: number[];
    ticks: number[];
  };
}
```

### 7.2 Update Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  WebSocket  │────►│    Store    │────►│  Components │
│  Message    │     │  (Zustand)  │     │  (React)    │
└─────────────┘     └─────────────┘     └─────────────┘
                           ▲
                           │ Actions
                           │
                    ┌─────────────┐
                    │  User Input │
                    │  (buttons)  │
                    └─────────────┘
```

### 7.3 Optimizations for Performance

1. **Immutable updates** - Only re-render changed components
2. **Memoization** - Cache expensive computations (e.g., surplus heatmap)
3. **Throttling** - Limit UI updates if ticks arrive faster than 60fps
4. **Virtualization** - For long lists (trade history)
5. **Web Workers** - Offload heavy computation (layout algorithms)

---

## 8. Migration Strategy

### 8.1 Phase 0: Proof of Concept (1-2 days)

**Goal:** Validate architecture with minimal investment

**Scope:**
- FastAPI server with single WebSocket endpoint
- Bare-bones React app with Vite
- Simple canvas showing agents as colored circles
- Start/stop buttons

**Success criteria:**
- Agents move on screen in real-time
- <100ms latency from tick to render

### 8.2 Phase 1: Core Visualization (1 week)

**Goal:** Replicate essential DearPyGui functionality

**Scope:**
- Grid rendering with proper styling
- Agent hover/selection
- Play/pause/step/reset controls
- Speed slider
- Basic metrics panel (tick, trades, welfare)

### 8.3 Phase 2: Charts and Analysis (3-5 days)

**Goal:** Time series and network visualization

**Scope:**
- Welfare over time chart
- Trade count chart
- Trade network panel with force layout

### 8.4 Phase 3: Advanced Features (1 week)

**Goal:** Full feature parity with DearPyGui

**Scope:**
- Edgeworth box popup
- Overlay toggles (trails, perception, heatmap)
- Configuration modal
- Export functionality

### 8.5 Phase 4: Polish and Beyond (ongoing)

**Goal:** Exceed DearPyGui capabilities

**Scope:**
- Improved animations
- Better responsive design
- Keyboard shortcuts
- Undo/redo
- Scenario comparison views
- etc.

### 8.6 Parallel Operation

During migration, both UIs can coexist:

```bash
# Run DearPyGui version
uv run python -m microecon.visualization

# Run web version
cd web && npm run dev  # Frontend
uv run python -m microecon.server  # Backend
```

---

## 9. Development Workflow

### 9.1 Project Structure (Proposed)

```
microecon/
├── src/microecon/           # Existing Python package
│   ├── ...                  # Simulation core (unchanged)
│   ├── visualization/       # DearPyGui (keep during transition)
│   └── server/              # NEW: FastAPI backend
│       ├── __init__.py
│       ├── __main__.py      # Entry point
│       ├── app.py           # FastAPI application
│       ├── routes.py        # REST endpoints
│       ├── websocket.py     # WebSocket handler
│       └── session.py       # Simulation session management
│
├── web/                     # NEW: TypeScript frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── store/           # State management
│       ├── components/      # UI components
│       │   ├── Grid/
│       │   ├── Charts/
│       │   ├── Controls/
│       │   └── ...
│       ├── hooks/           # Custom React hooks
│       ├── lib/             # Utilities
│       └── types/           # TypeScript types
│
├── pyproject.toml           # Add fastapi, uvicorn
└── ...
```

### 9.2 Running Development Environment

```bash
# Terminal 1: Python backend
uv run python -m microecon.server

# Terminal 2: TypeScript frontend (with hot reload)
cd web && npm run dev
```

### 9.3 TypeScript Learning Path (with LLM Assistance)

Since you're new to TypeScript, here's a suggested progression:

1. **Day 1:** Basic types, interfaces, function signatures
2. **Day 2:** React component structure, props, state
3. **Day 3:** Hooks (useState, useEffect, useCallback)
4. **Day 4:** Fetching data, WebSocket connections
5. **Day 5:** Styling with Tailwind, component libraries

**LLM assistance patterns:**
- "Convert this Python dataclass to TypeScript interface"
- "Write a React component that displays this data"
- "How do I handle WebSocket messages in React?"
- "Style this component with Tailwind to look like [description]"

---

## 10. Risks and Mitigations

### 10.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WebSocket latency too high | Low | Medium | Fallback to polling; optimize message size |
| Canvas performance with many agents | Low | Medium | Switch to Pixi.js/WebGL |
| State synchronization bugs | Medium | High | Clear protocol, logging, tests |
| TypeScript learning curve | Medium | Medium | Heavy LLM assistance, start simple |
| Library compatibility issues | Low | Low | Popular libraries are well-maintained |

### 10.2 Process Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep | High | Medium | Strict phase gates, MVP first |
| Abandoning before feature parity | Medium | High | Keep DearPyGui working in parallel |
| Over-engineering | Medium | Medium | Start with simplest solution |

### 10.3 Fallback Plan

If web frontend exploration fails:
1. Keep DearPyGui as primary UI
2. Potentially use web for specific features only (e.g., shareable demos)
3. Consider simpler approaches (Panel, Streamlit) for specific needs

---

## 11. Decision Points

### 11.1 Decisions to Make Before Starting

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **UI Framework** | React, Svelte, Vue, Solid | React (ecosystem, LLM support) |
| **Component Library** | shadcn, MUI, Chakra, Radix | shadcn/ui (modern, flexible) |
| **Build Tool** | Vite, Next.js, Create React App | Vite (fast, simple) |
| **State Management** | Zustand, Jotai, Redux, Context | Zustand (simple, performant) |
| **Grid Rendering** | Canvas 2D, Pixi.js, SVG, D3 | Canvas 2D (MVP), Pixi.js (if needed) |
| **Charts** | Recharts, Observable Plot, Chart.js | Recharts (React integration) |
| **Python Framework** | FastAPI, Flask, Starlette | FastAPI (modern, async, types) |

### 11.2 Decisions to Defer

- Exact styling/theming choices
- Animation library selection
- Testing framework for frontend
- Production deployment strategy
- Mobile responsiveness approach

---

## 12. Proof of Concept Scope

### 12.1 MVP Features (PoC)

**Backend (Python/FastAPI):**
- [ ] `/api/config` - GET/POST configuration
- [ ] `/api/simulation/start` - Start simulation
- [ ] `/api/simulation/stop` - Stop simulation
- [ ] `/api/simulation/step` - Single tick
- [ ] `/ws/simulation` - WebSocket for tick updates

**Frontend (React/TypeScript):**
- [ ] Connect to WebSocket, display connection status
- [ ] Canvas rendering of grid with agents (colored circles)
- [ ] Start/Stop/Step buttons
- [ ] Display current tick number
- [ ] Display total welfare

### 12.2 PoC Non-Features

- Edgeworth box
- Trade network panel
- Overlays
- Configuration modal
- Export
- Charts
- Agent selection
- Hover tooltips

### 12.3 Success Metrics

1. **Latency:** <100ms from Python tick to rendered frame
2. **Correctness:** Agent positions match Python state exactly
3. **Stability:** No connection drops over 5-minute session
4. **Responsiveness:** UI remains responsive during fast simulation

---

## Appendix A: Technology Versions (Current Best Practices)

```json
{
  "python": "3.12+",
  "fastapi": "0.109+",
  "uvicorn": "0.27+",
  "node": "20+",
  "typescript": "5.3+",
  "react": "18+",
  "vite": "5+",
  "tailwindcss": "3.4+"
}
```

## Appendix B: Resources

- [FastAPI WebSocket Tutorial](https://fastapi.tiangolo.com/advanced/websockets/)
- [Vite Getting Started](https://vitejs.dev/guide/)
- [shadcn/ui](https://ui.shadcn.com/)
- [Zustand](https://github.com/pmndrs/zustand)
- [Recharts](https://recharts.org/)
- [D3-force](https://d3js.org/d3-force)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/)

## Appendix C: Example Code Snippets

### C.1 FastAPI WebSocket Handler (Python)

```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/simulation")
async def simulation_websocket(websocket: WebSocket):
    await websocket.accept()

    # Create simulation
    sim = create_simple_economy(n_agents=10, grid_size=15, seed=42)

    try:
        while True:
            # Wait for command
            data = await websocket.receive_json()

            if data["type"] == "step":
                sim.tick()
                state = {
                    "tick": sim.tick,
                    "agents": [
                        {
                            "id": a.id,
                            "position": sim.grid.get_position(a).to_tuple(),
                            "alpha": a.preferences.alpha,
                            "utility": a.utility,
                        }
                        for a in sim.agents
                    ],
                    "welfare": sim.total_welfare,
                }
                await websocket.send_json(state)

    except WebSocketDisconnect:
        pass
```

### C.2 React WebSocket Hook (TypeScript)

```typescript
import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '../store';

export function useSimulationSocket() {
  const ws = useRef<WebSocket | null>(null);
  const setConnected = useStore(s => s.setConnected);
  const updateState = useStore(s => s.updateState);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws/simulation');

    ws.current.onopen = () => setConnected(true);
    ws.current.onclose = () => setConnected(false);
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updateState(data);
    };

    return () => ws.current?.close();
  }, []);

  const sendCommand = useCallback((type: string, payload?: any) => {
    ws.current?.send(JSON.stringify({ type, payload }));
  }, []);

  return { sendCommand };
}
```

### C.3 Simple Grid Canvas Component (TypeScript/React)

```typescript
import { useRef, useEffect } from 'react';
import { useStore } from '../store';

export function GridCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const agents = useStore(s => s.agents);
  const gridSize = useStore(s => s.config.gridSize);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const cellSize = canvas.width / gridSize;

    // Clear
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid lines
    ctx.strokeStyle = '#2a2a4e';
    for (let i = 0; i <= gridSize; i++) {
      ctx.beginPath();
      ctx.moveTo(i * cellSize, 0);
      ctx.lineTo(i * cellSize, canvas.height);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * cellSize);
      ctx.lineTo(canvas.width, i * cellSize);
      ctx.stroke();
    }

    // Draw agents
    agents.forEach(agent => {
      const x = (agent.position[0] + 0.5) * cellSize;
      const y = (agent.position[1] + 0.5) * cellSize;
      const radius = cellSize * 0.3;

      // Color based on alpha (preference parameter)
      const hue = agent.alpha * 240; // 0 = red, 1 = blue
      ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    });
  }, [agents, gridSize]);

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={600}
      className="border border-gray-700 rounded"
    />
  );
}
```

---

## Notes for Discussion

*[Space for your annotations and questions]*

1.

2.

3.

