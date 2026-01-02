# Dashboard Integration Design

**Status:** Planning document
**Date:** 2026-01-02
**Purpose:** Comprehensive design for dashboard integration, derived from interactive requirements gathering

---

## 1. Vision

A **multi-purpose dashboard** serving three use cases:

1. **Research exploration** - Interactive experimentation, parameter tweaking, hypothesis testing
2. **Presentation/demonstration** - Polished visualizations for papers, talks, collaborators
3. **Systematic comparison** - Batch analysis, statistical comparisons across protocols

The dashboard makes **institutional visibility** tangible: same scenario, different protocols, observable differences.

---

## 2. Entry Points

### Primary: Scenario Browser

Pre-defined scenarios organized by **progressive complexity**:

```
Level 1: Fundamentals
├── Two-Agent Baseline
└── Simple Exchange

Level 2: Spatial Patterns
├── Trading Chain (4 agents)
└── Hub and Spoke

Level 3: Protocol Comparisons
├── Matching Protocol Comparison
└── Bargaining Protocol Comparison

Level 4: Complex Dynamics
├── Random Placement (stochastic)
└── Market Emergence
```

### Future Extensions

- **Parameter configuration**: Set up custom scenarios via UI
- **Load logged runs**: Import previously-run simulations for replay/analysis

---

## 3. Scenario Architecture

### 3.1 Scenario vs Test Relationship

**Separate concerns:**
- **Tests** verify code correctness (assertions, edge cases, regression)
- **Scenarios** demonstrate economic phenomena (narrative, educational, comparative)

Tests and scenarios may share configuration, but serve different purposes.

### 3.2 Authoring Workflow

Current stage:
1. Build theoretical tests with well-specified configurations
2. Extract config from test fixtures (manual or CLI helper)
3. Add narrative/comparison metadata to create scenario file

Future extensions:
- Visual builder for placing agents
- Template + fill for common patterns

### 3.3 Scenario File Format

**YAML with minimal schema** - define required fields only, allow extensions.

```yaml
# scenarios/trading_chain_4.yaml

meta:
  title: "Trading Chain (4 Agents)"
  description: |
    Four agents arranged linearly with complementary preferences.
    Demonstrates how matching protocol affects welfare outcomes.
  complexity: 2  # for progressive ordering
  tags: [matching, spatial, bilateral]

  # Narrative guidance for viewer
  what_to_watch:
    - "Committed matching finds globally optimal pairs (A-D, B-C)"
    - "Opportunistic matching may create suboptimal trade sequences"
    - "Watch MRS convergence: optimal pairs reach MRS=1"

  # Educational context (optional)
  theory:
    concept: "Stable matching vs myopic matching"
    reference: "Irving (1985), Stable Roommates"

config:
  grid_size: 10
  perception_radius: 7.0
  discount_factor: 0.95

  agents:
    - id: A
      position: [0, 0]
      alpha: 0.2
      endowment: [8, 2]
    - id: B
      position: [3, 0]
      alpha: 0.4
      endowment: [2, 8]
    - id: C
      position: [6, 0]
      alpha: 0.6
      endowment: [8, 2]
    - id: D
      position: [9, 0]
      alpha: 0.8
      endowment: [2, 8]

comparison:
  protocols:
    - type: matching
      values: [opportunistic, stable_roommates]
    # Could also compare bargaining protocols:
    # - type: bargaining
    #   values: [nash, rubinstein]

  expected_outcomes:
    stable_roommates:
      trades: 2
      final_mrs: "all ~1.0"
      welfare: "~26.8"
    opportunistic:
      trades: 3
      final_mrs: "varies (0.66-1.88)"
      welfare: "~26.2"

  key_insight: |
    Committed matching achieves ~2.2% higher welfare by finding
    globally optimal pairs rather than greedy local trades.

# Optional: checkpoints for timeline markers
checkpoints:
  - tick: 1
    label: "Commitments form"
    highlight: [A, D, B, C]
  - tick: 5
    label: "First trade (optimal pair)"
  - tick: 8
    label: "Equilibrium reached"
```

### 3.4 Schema Evolution

Start minimal:
- `meta.title` (required)
- `meta.complexity` (required for ordering)
- `config.grid_size` (required)
- `config.agents` (required)

All other fields optional. Schema formalized after patterns emerge from real usage.

---

## 4. UI Layout

### 4.1 Comparison View (Primary)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Scenario: Trading Chain (4 Agents)                          [?] [×]│
│  [Opportunistic ▼]              vs              [StableRoommates ▼] │
├─────────────────────────────────┬───────────────────────────────────┤
│                                 │                                   │
│                                 │                                   │
│      Protocol A Grid            │        Protocol B Grid            │
│         (10×10)                 │           (10×10)                 │
│                                 │                                   │
│   Welfare: 26.20                │       Welfare: 26.80              │
│   Trades: 3                     │       Trades: 2                   │
│                                 │                                   │
├─────────────────────────────────┴───────────────────────────────────┤
│                                                                     │
│  ◀◀  ◀  ▐▐  ▶  ▶▶   [●════|C|════|T|════|T|════|C|══════●]  12/20  │
│                      ↑                                              │
│              Timeline with event markers:                           │
│              C = Commitment formed/broken                           │
│              T = Trade executed                                     │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐  │
│  │     Welfare Over Time       │  │    Cumulative Trades        │  │
│  │  28┤                        │  │   4┤         ___________    │  │
│  │    │         ___________    │  │    │    ____/               │  │
│  │  26┤    ____/   ········    │  │   2┤___/    ············    │  │
│  │    │___/                    │  │    │                        │  │
│  │  24┼────────────────────    │  │   0┼────────────────────    │  │
│  │    0    5    10   15   20   │  │    0    5    10   15   20   │  │
│  │    ── Protocol A            │  │    ── Protocol A            │  │
│  │    ·· Protocol B            │  │    ·· Protocol B            │  │
│  └─────────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Scenario Browser

```
┌─────────────────────────────────────────────────────────────────────┐
│  Example Scenarios                                    [+ New] [⚙]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ▼ Fundamentals                                                     │
│    ┌─────────────────────────────────────────────────────────────┐  │
│    │ Two-Agent Baseline                                          │  │
│    │ Simplest exchange: two agents with complementary preferences│  │
│    │ [matching] [bilateral]                           [Run ▶]    │  │
│    └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ▼ Spatial Patterns                                                 │
│    ┌─────────────────────────────────────────────────────────────┐  │
│    │ Trading Chain (4 Agents)                                    │  │
│    │ Linear arrangement demonstrating matching optimality        │  │
│    │ [matching] [spatial] [comparison]                [Run ▶]    │  │
│    └─────────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────────┐  │
│    │ Hub and Spoke                                               │  │
│    │ Central agent with peripheral ring                          │  │
│    │ [spatial] [asymmetric]                           [Run ▶]    │  │
│    └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ▶ Protocol Comparisons (collapsed)                                 │
│  ▶ Complex Dynamics (collapsed)                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Playback Controls

| Control | Function |
|---------|----------|
| ◀◀ | Jump to start |
| ◀ | Step back one tick |
| ▐▐ / ▶ | Pause / Play |
| ▶ | Step forward one tick |
| ▶▶ | Jump to end |
| Timeline bar | Scrub to any tick |
| Event markers | Click to jump to trade/commitment |
| Speed slider | Adjust playback speed |

### 4.4 Information Panel

When hovering/clicking agents or events:

```
┌─────────────────────────┐
│ Agent B (tick 7)        │
├─────────────────────────┤
│ Position: (5, 2)        │
│ α: 0.4                  │
│ Endowment: (5.2, 4.8)   │
│ Utility: 5.01           │
│ MRS: 1.08               │
│ Committed to: Agent C   │
└─────────────────────────┘
```

---

## 5. Comparison Workflow

### 5.1 Pre-computed Comparison

When user selects a scenario for comparison:

1. **Load scenario** from YAML
2. **Run both protocols** to completion (background, fast)
3. **Store complete tick history** for both runs
4. **Display** with synchronized playback

Benefits:
- Instant scrubbing and navigation
- Summary statistics available immediately
- No synchronization complexity during playback

### 5.2 Comparison Metrics

Display in real-time during playback:

| Metric | Description |
|--------|-------------|
| Welfare | Total utility, per-agent breakdown |
| Trades | Count, participants, sequence |
| Efficiency | % of theoretical maximum gains |
| MRS convergence | How close agents are to equilibrium |
| Commitments | Active pairs, formation/breakage history |

---

## 6. Time-Series Charts

### 6.1 Required Charts

**Welfare over time:**
- Y-axis: Total welfare (sum of utilities)
- Both protocols overlaid with distinct styling
- Vertical markers for trade events

**Trade frequency:**
- Y-axis: Cumulative trades
- Step function showing when trades occur
- Both protocols overlaid

### 6.2 Future Charts

- MRS convergence (per-agent lines converging to 1.0)
- Active commitments over time
- Search efficiency (distance traveled per trade)

### 6.3 Implementation

Use **ImPlot** (DearPyGui's plotting extension):
- Already compatible with DearPyGui
- Supports interactive charts (zoom, pan)
- Real-time updates during playback

---

## 7. Export Capabilities

### 7.1 Static Images

| Format | Use Case |
|--------|----------|
| PNG | Papers, slides, web |
| SVG | Vector graphics, high-quality print |

Export current frame or specific tick.

### 7.2 Animations

| Format | Use Case |
|--------|----------|
| GIF | Quick demos, documentation |
| MP4 | Presentations, high quality |

Export range of ticks with configurable frame rate.

### 7.3 Data Export

| Format | Use Case |
|--------|----------|
| CSV | External analysis (R, Excel) |
| JSON | Programmatic access, archival |

Export complete run data or selected metrics.

---

## 8. Implementation Phases

### Phase 1: Comparison View MVP (Priority: P0)

**Goal:** Prove core value proposition - side-by-side protocol comparison

**Tasks:**
1. Extend existing `DualReplayController` for comparison mode
2. Pre-compute both protocol runs before display
3. Synchronized playback with basic controls
4. Display welfare/trade counts in real-time

**Entry point:** Hardcoded scenario (trading chain) for initial development

**Success criteria:** Can watch Opportunistic vs StableRoommates side-by-side, see welfare difference

### Phase 2: Scenario Pipeline (Priority: P1)

**Goal:** Load scenarios from files, browse and select

**Tasks:**
1. Define minimal YAML schema
2. Implement scenario loader
3. Create extract-from-test helper (CLI or script)
4. Build scenario browser UI (simple list)
5. Create 2-3 initial scenarios from existing tests

**Success criteria:** Can select scenario from browser, runs comparison automatically

### Phase 3: Timeline & Charts (Priority: P1)

**Goal:** Rich playback controls and analysis

**Tasks:**
1. Implement timeline scrubber bar
2. Add event markers (trades, commitments)
3. Integrate ImPlot for time-series
4. Implement welfare and trade charts

**Success criteria:** Can scrub timeline, click event markers, see charts update

### Phase 4: Polish & Export (Priority: P2)

**Goal:** Production-ready for papers/presentations

**Tasks:**
1. PNG/SVG frame export
2. GIF/MP4 animation export
3. CSV/JSON data export
4. Narrative display panel (scenario description, what-to-watch)
5. Keyboard shortcuts

**Success criteria:** Can generate publication-quality figures and animations

---

## 9. Technical Considerations

### 9.1 Architecture

```
scenarios/
├── trading_chain_4.yaml
├── hub_and_spoke.yaml
└── two_agent_baseline.yaml

src/microecon/
├── scenarios/
│   ├── __init__.py
│   ├── loader.py      # YAML parsing, validation
│   ├── schema.py      # Dataclasses for scenario structure
│   └── extractor.py   # Extract config from test fixtures
└── visualization/
    ├── comparison.py  # Comparison mode logic
    ├── timeline.py    # Timeline controls, markers
    ├── charts.py      # ImPlot integration
    └── export.py      # Image/animation/data export
```

### 9.2 Dependencies

Current:
- DearPyGui (visualization framework)

To add:
- ImPlot (charting, via dearpygui.demo)
- Pillow (PNG export)
- imageio (GIF/MP4 export)
- PyYAML (scenario loading)

### 9.3 Performance

- Pre-compute runs for instant scrubbing
- Cache rendered frames for smooth playback
- Lazy-load scenarios (metadata first, full config on selection)

---

## 10. Open Questions

### Deferred Decisions

1. **Scenario versioning**: How to handle schema evolution?
2. **Scenario validation**: How strict? Fail fast or warn?
3. **Multi-protocol comparison**: More than 2 protocols at once?
4. **Batch integration**: Trigger batch runs from dashboard?

### Future Features (Not in Scope)

- Real-time parameter editing during simulation
- Agent perspective mode (information asymmetry visualization)
- Network graph view (trade relationships)
- 3D visualization (for higher-dimensional goods)

---

## 11. Success Metrics

### Phase 1 Complete When:
- [ ] Side-by-side comparison runs smoothly
- [ ] Can observe welfare gap between protocols
- [ ] Playback controls work (play/pause/step)

### Phase 2 Complete When:
- [ ] 2-3 scenarios loadable from YAML
- [ ] Scenario browser displays and selects
- [ ] Scenarios extracted from existing tests

### Phase 3 Complete When:
- [ ] Timeline scrubbing works
- [ ] Event markers clickable
- [ ] Welfare/trade charts display and update

### Phase 4 Complete When:
- [ ] Can export PNG for paper figure
- [ ] Can export GIF for demo
- [ ] Can export CSV for analysis

---

**Document Version:** 1.0
**Author:** Session 2026-01-02 (interactive design)
