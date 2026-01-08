# Feature Parity Reference: Python DearPyGui → TypeScript Web Frontend

This document tracks feature parity between the archived Python/DearPyGui visualization and the current React/Vite web frontend.

**Source**: `.archived/visualization-dearpygui/visualization/`
**Target**: `frontend/` + `server/`

---

## Status Legend

| Status | Meaning |
|--------|---------|
| ✅ | Complete - feature exists and works |
| ⚠️ | Partial - feature exists but incomplete or buggy |
| ❌ | Missing - feature not implemented |
| 🔄 | Different - intentionally different approach |
| N/A | Not applicable to web context |

---

## 1. Layout & Structure

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Three-column layout | ✅ | ✅ | Web has metrics/overlays \| grid \| charts |
| Responsive grid (square, max 600px) | ✅ | ✅ | |
| Right-side metrics panel | ✅ | ✅ | |
| Collapsible sections | ✅ | ⚠️ | Web uses modals instead of collapsing headers |
| Window dimensions (1200x850) | ✅ | ⚠️ | Web responsive but no min-width handling |

---

## 2. Grid Visualization

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Grid background rendering | ✅ | ✅ | |
| Grid lines | ✅ | ✅ | |
| Agent circles | ✅ | ✅ | |
| Alpha-based color encoding | ✅ | ✅ | Blue (low α) → Orange (high α) |
| Cell-based positioning | ✅ | ✅ | |
| Agent hover detection | ✅ | ✅ | |
| Agent selection | ✅ | ⚠️ | Web has selection but limited feedback |
| Selection highlight (perception radius) | ✅ | ⚠️ | Perception overlay exists but not selection-linked |

---

## 3. Overlays

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Movement trails | ✅ | ✅ | Last N positions with fade |
| Perception radius - selected agent | ✅ | ⚠️ | Web shows all or none, not selected-only |
| Perception radius - all agents | ✅ | ✅ | |
| Belief connections | ✅ | ❌ | Lines between agents with beliefs |
| Trade network overlay | ✅ | ⚠️ | Exists but "doesn't work well" per review |
| Surplus heatmap | ✅ | ⚠️ | Toggle exists but non-functional per review |

---

## 4. Belief System Visualization

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Belief panel display | ✅ | ❌ | No belief panel in web |
| Price belief display | ✅ | ❌ | |
| Type beliefs list | ✅ | ❌ | |
| Belief count in hover | ✅ | ❌ | |
| `use_beliefs` config toggle | ✅ | ❌ | Config exists but no UI control |

---

## 5. Agent Perspective Mode

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Perspective mode toggle | ✅ | ❌ | See what agent sees vs omniscient |
| Agent selector dropdown | ✅ | ❌ | |
| Ground truth comparison | ✅ | ❌ | |
| Noisy observation rendering | ✅ | ❌ | |

---

## 6. Playback Controls

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Mode indicator (LIVE/REPLAY) | ✅ | ⚠️ | Web shows running state, no replay mode |
| Play/Pause button | ✅ | ✅ | |
| Step Forward | ✅ | ✅ | |
| Step Back (replay) | ✅ | ❌ | No replay mode |
| Speed slider | ✅ | ✅ | |
| Timeline slider (replay) | ✅ | ❌ | No replay mode |
| Reset button | ✅ | ⚠️ | Exists but doesn't clear UI state (review issue) |

---

## 7. Trade Visualization

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Trade animation | ✅ | ❌ | 2-second animated movement |
| Trade connections overlay | ✅ | ⚠️ | Lines exist but accumulate without pruning |

---

## 8. Edgeworth Box

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Edgeworth box popup | ✅ | ✅ | |
| Pre/post allocation points | ✅ | ✅ | |
| Indifference curves (both agents) | ✅ | ✅ | |
| Contract curve | ✅ | ✅ | |
| Trade vector arrow | ✅ | ⚠️ | Check if implemented |
| Detailed trade info | ✅ | ✅ | |
| Click from trade history | ✅ | ✅ | |

---

## 9. Trade History

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Recent trades panel | ✅ | ✅ | |
| Clickable trade entries | ✅ | ✅ | Opens Edgeworth box |
| Trade participant display | ✅ | ✅ | |

---

## 10. Trade Network Panel

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Dedicated network window | ✅ | ✅ | Web has TradeNetwork component |
| Circular layout | ✅ | ⚠️ | Check implementation |
| Force-directed layout | ✅ | ⚠️ | D3 force layout but "jittery" per review |
| Layout toggle | ✅ | ❌ | |
| Node coloring by alpha | ✅ | ⚠️ | Check |
| Edge thickness by frequency | ✅ | ⚠️ | Check |
| Edge color by recency | ✅ | ⚠️ | Check |
| Click to select node | ✅ | ❌ | |
| Network metrics display | ✅ | ❌ | Density, clustering, avg degree |
| Live/replay mode support | ✅ | ⚠️ | No replay mode |

---

## 11. Time-Series Charts

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Welfare chart | ✅ | ✅ | |
| Trades chart | ✅ | ✅ | |
| Real-time data append | ✅ | ✅ | |
| Replay playhead line | ✅ | ❌ | No replay mode |
| Auto-scaling axes | ✅ | ✅ | |

---

## 12. Configuration

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Configuration modal | ✅ | ✅ | |
| Agent count | ✅ | ✅ | |
| Grid size | ✅ | ✅ | |
| Seed | ✅ | ✅ | |
| Bargaining protocol selector | ✅ | ✅ | Nash/Rubinstein |
| Matching protocol selector | ✅ | ✅ | Opportunistic/StableRoommates |
| Perception radius | ✅ | ✅ | |
| Discount factor | ✅ | ✅ | |
| `use_beliefs` toggle | ✅ | ❌ | Config field exists, no UI |
| Config broadcast to clients | ✅ (N/A) | ❌ | Single-user Python, multi-client web issue |

---

## 13. Startup & Mode Selection

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Startup selector | ✅ | ❌ | Live/Browse/Load modes |
| Scenario browser | ✅ | ❌ | Browse pre-defined scenarios |
| Scenario cards with metadata | ✅ | ❌ | |
| Load saved run | ✅ | ❌ | Placeholder in Python too |

---

## 14. Export

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| PNG export | ✅ | ⚠️ | Exists but targets wrong canvas (review issue) |
| SVG export | ✅ | ✅ | Check implementation |
| JSON export | ✅ | ✅ | |
| CSV export | ✅ | ✅ | |
| GIF animation export | ✅ | ✅ | Web has GIF via canvas recording |
| Export status feedback | ✅ | ⚠️ | Check |

---

## 15. Dual/Comparison Mode

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Side-by-side grids | ✅ | ❌ | DualVisualizationApp in Python |
| Synchronized playback | ✅ | ❌ | |
| Overlaid time-series comparison | ✅ | ❌ | |
| Protocol labels | ✅ | ❌ | |
| Dual replay controller | ✅ | ❌ | |

---

## 16. Replay Mode

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Load logged RunData | ✅ | ❌ | |
| Timeline seeking | ✅ | ❌ | |
| Step backward | ✅ | ❌ | |
| Preloaded historical data | ✅ | ❌ | |
| Deterministic playback | ✅ | ❌ | |

---

## 17. Hover & Tooltips

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Agent hover info | ✅ | ✅ | AgentTooltip component |
| ID display | ✅ | ✅ | |
| Alpha display | ✅ | ✅ | |
| Endowment display | ✅ | ✅ | |
| Utility display | ✅ | ✅ | |
| Belief summary in hover | ✅ | ❌ | |
| Plain-language labels | ⚠️ | ❌ | VISUALIZATION.md wants this |

---

## 18. Metrics Display

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Current tick | ✅ | ✅ | |
| Cumulative trade count | ✅ | ✅ | |
| Total system welfare | ✅ | ✅ | |
| Welfare gains | ✅ | ⚠️ | Check if displayed |

---

## 19. Keyboard Controls

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Space for play/pause | ❌ | ❌ | VISUALIZATION.md requests this |
| Arrow keys for stepping | ❌ | ❌ | |

---

## 20. Server/WebSocket (Web-specific)

| Feature | Python | Web | Notes |
|---------|--------|-----|-------|
| Single simulation broadcast | N/A | ❌ | Race condition issue (review) |
| Config broadcast | N/A | ❌ | REST-only, no broadcast (review) |
| Reset state sync | N/A | ❌ | UI state not cleared (review) |
| Multiple simulation instances | N/A | ❌ | Needed for comparison mode |

---

## Priority Summary

### Critical (from code review)
1. WebSocket concurrency fix
2. Reset clears UI state
3. Config broadcast mechanism

### High (core feature gaps)
4. Belief system visualization
5. Agent perspective mode
6. Trade animation
7. Dual/comparison mode architecture

### Medium (polish & completeness)
8. Replay mode
9. Scenario browser
10. Trade network improvements (layout toggle, metrics, click-to-select)
11. Keyboard shortcuts
12. PNG export fix
13. Overlay defaults alignment

### Low (nice-to-have)
14. Plain-language tooltip labels
15. Surplus heatmap implementation
16. Belief connections overlay

---

## Architecture Decisions Needed

1. **Simulation ownership**: Single shared vs per-client instances
   - Single shared for normal mode (broadcast to observers)
   - Multiple instances for comparison mode (one per protocol)

2. **Config mechanism**: REST vs WebSocket
   - Recommendation: WebSocket for all state changes (inherent broadcast)

3. **Reset semantics**: Clear all UI state on reset (confirmed by user)

4. **Replay architecture**: How to load/seek through saved runs
   - Server-side: Load RunData, serve snapshots on demand
   - Client-side: Preload full run, seek locally

5. **Comparison mode**: How to run parallel simulations
   - Same seed, different protocols
   - Synchronized stepping
   - Separate or overlaid charts
