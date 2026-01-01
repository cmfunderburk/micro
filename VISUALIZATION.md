# Visualization Reference Guide

**Status:** Reference document for UI/UX decisions
**Date:** 2026-01-01
**Purpose:** Guide visualization layer development based on research requirements

---

## 1. Core Purpose & Audience

### Multi-Purpose Tool

The visualization serves three audiences simultaneously:
- **Personal research**: Building intuition, exploring phenomena, debugging simulations
- **Publication outputs**: High-quality static figures and animations for papers
- **Live demonstrations**: Interactive walkthroughs for talks and collaborators

### User Profile

- Power user tool; documentation is acceptable
- Assumes economics background and familiarity with concepts
- Progressive disclosure: simple things obvious, advanced features can require learning

---

## 2. Aesthetic Direction

### Visual Style: Flat Design + Game-Like

Combines two inspirations:
- **Strategy games** (Civilization, Factorio): Complex information made readable, engaging to watch
- **Scientific visualization** (matplotlib, ggplot): Clean statistical graphics, publication quality

Characteristics:
- Modern, colorful, no 3D effects or pseudo-depth
- Distinct agent appearances with personality
- Approachable and engaging while maintaining rigor

### Grid Treatment

- **Subtle grid**: Light lines or no visible grid
- Creates continuous-space feel rather than discrete cells
- Grid can be more prominent when specifically relevant (e.g., showing cell-based mechanics)

### Animation Style

- **Discrete/snappy movement**: Clear tick-by-tick jumps between positions
- Emphasizes the discrete simulation nature despite continuous visual feel
- Contrast between smooth aesthetic and crisp state transitions

---

## 3. Agent Representation

### Primary Encoding: Color

Agent characteristics encoded through color:
- Preference parameter (α) maps to color dimension
- Goods holdings represented via color mixing
- Each good is a primary color; agent color is the mix

**Scalability note**: Color mixing works well for 2-4 goods. Beyond that, visualization approach will need rethinking or suppression of goods-level detail.

### Inspection: Hover Tooltips

- Quick information on hover (endowments, preferences, recent activity)
- Click for deeper inspection if needed
- No modal popups interrupting flow

### At Scale (100-500+ agents)

- Individual agents remain visible but detail requires zoom/selection
- Aggregate views for full-grid perspective
- Graceful degradation of per-agent detail at distance

---

## 4. Trade Visualization

### Layered Approach

Default behavior:
- Quick animation when trade occurs
- Brief visual indication (highlight, connection line, goods flow)
- Doesn't interrupt simulation flow

On-demand detail:
- Slow down or pause to inspect specific trades
- Zoom into trading partnership for comprehensive view

### Trade Zoom View (Comprehensive)

When focusing on a specific trade, show all relevant information:
- **Edgeworth box**: Classic 2-agent, 2-good diagram with endowments, indifference curves, contract curve, outcome point
- **Utility breakdown**: Each agent's utility function, pre/post trade welfare
- **Bargaining dynamics**: If using Rubinstein-style protocol, offer/counteroffer sequence

This comprehensive view supports research into bargaining mechanics and individual trade outcomes.

---

## 5. Information Overlays

### Design Principle: Start Minimal

Clutter is a serious concern at N-agent scale. Overlays should be:
- Toggleable (off by default in most cases)
- Purpose-specific (not decorative)
- Clearly valuable for the information they add

### Movement Trails

When enabled:
- Show agent paths (where they've been, direction of travel)
- **Purpose-encoded**: Color/style indicates why agent moved (seeking trade partner, random exploration, etc.)
- Fading over time to avoid permanent clutter

### Future Overlays (As Needed)

Consider carefully before adding:
- Perception radii (show observation range)
- Surplus heatmaps (opportunity density)
- Trade networks (who has traded with whom)

Each overlay must earn its place by demonstrating clear research value.

---

## 6. Information Asymmetry Visualization

### Agent Perspective Mode

For private information scenarios (future development):
- Toggle to see the world "as agent X sees it"
- Compare agent's partial view to omniscient view
- Supports research into information structure effects

This is architecturally important: the visualization must support showing different information states, not just ground truth.

---

## 7. Benchmark Comparison

### Nuanced Approach

Different comparison methods for different benchmarks:

**General equilibrium (Walrasian)**:
- Post-run analysis preferred
- GE comparisons require careful interpretation
- Not simple 1-to-1 mapping with spatial agent-based outcomes

**Individual bargaining**:
- Mid-run zoom on trading partnerships potentially valuable
- Compare actual trade outcome to Nash bargaining prediction
- Visual overlay of theoretical vs. actual in trade zoom view

---

## 8. Temporal Controls

### Primary: Speed Control

- Adjustable playback speed (slow motion to fast forward)
- Consistent speed (no automatic fast-forward during quiet periods)
- User controls pacing manually

### No Special Quiet Period Handling

- Watching agents search is part of the simulation
- Users can speed up if desired
- No automatic "skip to interesting parts"

---

## 9. Aggregate Metrics

### Comprehensive and Toggleable

Three categories of metrics, all available with toggle control:

**Trade statistics**:
- Number of trades over time
- Average surplus captured
- Trade volume trends

**Welfare measures**:
- Total utility
- Efficiency vs. benchmark
- Distribution (Gini coefficient or similar)

**Spatial statistics**:
- Clustering measures
- Average search time
- Movement pattern analysis

---

## 10. Layout & Modes

### Adaptive/Modal Design

Different layouts for different tasks, combining multiple mode dimensions:

**Phase modes**:
- **Setup**: Configuration panels prominent, grid preview
- **Run**: Grid dominant, controls and basic metrics visible
- **Analyze**: Charts and statistics prominent, grid available for reference

**Zoom modes**:
- **Overview**: Full grid, aggregate view, individual agents small
- **Detail**: Focused view, individual agents inspectable, trade zoom available

**View modes**:
- **Grid**: Spatial visualization primary
- **Charts**: Time-series and statistical views primary

Users can navigate between modes fluidly based on current task.

---

## 11. Configuration

### Hybrid Approach

**Config files (base)**:
- YAML or JSON scenario definitions
- Reproducible experiment specifications
- Version controllable

**GUI (tweaking)**:
- Visual sliders/forms for parameter adjustment
- Quick iteration without editing files
- See effects of changes immediately

**Code (advanced)**:
- Python API for programmatic configuration
- Batch runs, parameter sweeps
- Full control for complex experiments

---

## 12. Data Export

### Visual Exports

All formats supported:
- **Static frames**: High-resolution PNG/SVG at key moments
- **Animations**: GIF/MP4 of simulation runs or segments
- **Vector graphics**: Editable SVG/PDF for journal figure requirements

### Data Exports

Comprehensive logging for offline analysis:
- **Time series CSV**: Tick-by-tick agent states and metrics
- **Snapshot states**: Full simulation state at key moments (JSON/pickle)
- **Trade logs**: Detailed record of every trade (parties, goods, terms, timing)

---

## 13. Interaction Model

### Hybrid Input

**Mouse (spatial)**:
- Hover for tooltips
- Click for selection/inspection
- Pan and zoom on grid

**Keyboard (controls)**:
- Playback controls (play, pause, speed)
- Mode switching
- Quick toggles for overlays

---

## 14. Technical Architecture

### Flexibility as Priority

The visualization architecture should enable rapid iteration on visual choices as research needs evolve.

### Simulation-Visualization Coupling

Support both modes:
- **Live observation**: Visualization directly watches running simulation
- **Replay**: Visualization reads from logged history

This enables both real-time exploration and post-hoc analysis of recorded runs.

### Grid Sizing

- Grid dimensions (NxN) are a simulation parameter (user-configured)
- Visualization scales to fit available window space
- Maintains aspect ratio

---

## 15. Terminology

### Layered Approach

**Default**: Accessible plain language
- "preference strength" not "α parameter"
- "trade gain" not "Nash bargaining surplus"

**On hover/detail**: Technical terms available
- Precise terminology for those who want it
- Tooltips and detail views use canonical economic language

---

## 16. Technology

### Standalone Application

Primary deployment is a dedicated application window, not embedded in notebooks or web pages.

### Technology Choice

No strong constraint. Selection should optimize for:
- Flat design aesthetic capability
- Smooth animation at scale (100-500+ agents)
- Export flexibility (static, animated, vector)
- Event-driven architecture for live + replay modes

Candidate stacks to evaluate:
- **Python native**: Pygame, PyQt + custom rendering, Arcade
- **Web-based**: Electron + D3/Canvas, Tauri + web tech
- **Game engines**: Godot (has Python bindings), custom lightweight

Decision deferred to implementation planning.

---

## 17. What's Explicitly Out of Scope (For Now)

- Colorblind accessibility (standard attractive palette is sufficient)
- Jupyter notebook embedding
- Web deployment
- Real-time collaborative viewing

These may be reconsidered as needs evolve.

---

## 18. Open Questions for Implementation

1. **Specific color palette**: What exact colors for goods, agents, UI elements?
2. **Font and typography**: What typeface supports both game-like feel and scientific clarity?
3. **Exact layout proportions**: How much screen real estate for grid vs. panels in each mode?
4. **Animation timing**: Exact tick duration, interpolation curves?
5. **Technology stack**: Final selection among candidates

These will be resolved during implementation phase.

---

**Document Version:** 1.0
**Created:** 2026-01-01
