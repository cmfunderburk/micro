---
active: true
iteration: 1
max_iterations: 50
completion_promise: "TRADE-NETWORK-PANEL-COMPLETE"
started_at: "2026-01-08T01:54:14Z"
---

Execute PRD-TRADE-NETWORK-PANEL.json in full.

GOAL: Create a dedicated Trade Network Panel as a dockable window showing trade relationships as a network graph.

PRD LOCATION: docs/current/PRD-TRADE-NETWORK-PANEL.json

PHASES:
1. Window Infrastructure (NET-001 to NET-002)
2. Graph Rendering & Layout (NET-003 to NET-005)
3. Visual Encoding & Polish (NET-006 to NET-008)
4. Interaction & Integration (NET-009 to NET-011)

EXECUTION PROTOCOL:
- Work through phases sequentially
- Within each phase, implement all features before moving on
- Commit after completing each feature or logical unit of work
- Mark features as passes:true in the PRD as they are completed
- Run tests frequently: uv run pytest
- Continue automatically between phases (no stopping for review)

CONSTRAINTS:
- Do NOT modify core simulation logic (simulation.py, agent.py, bargaining.py)
- Visualization is a read-only consumer of simulation data
- Preserve existing functionality - new window should not break current behavior
- Reuse existing code: analysis/emergence.py has TradeEdge, build_trade_network(), TradeNetworkStats
- Reuse existing code: app.py has _trade_network dict and alpha_to_color()

KEY FILES:
- src/microecon/visualization/app.py - Main visualization (add window trigger)
- src/microecon/visualization/network.py - NEW: Trade network panel module
- src/microecon/analysis/emergence.py - Existing network data structures

IMPLEMENTATION GUIDANCE:

Phase 1 - Window Infrastructure:
- Create new module: visualization/network.py
- Use dpg.add_window() for dockable window
- Add button in main app to show/hide window
- Window should have drawlist for graph rendering

Phase 2 - Graph Rendering & Layout:
- Circular layout: position nodes at angles 2*pi*i/n around center
- Force-directed: implement simple spring-force algorithm
  - Connected nodes attract (spring force)
  - All nodes repel (inverse square)
  - Iterate until stable or max iterations
- Add radio buttons or combo to toggle layout

Phase 3 - Visual Encoding:
- Use alpha_to_color() from app.py for node colors
- Edge thickness: min(1 + trade_count * 0.5, 5)
- Edge recency: track last_trade_tick, compute brightness from (current_tick - last_trade_tick)

Phase 4 - Interaction & Integration:
- Use dpg mouse handlers for click detection on nodes
- Sync with app.selected_agent
- Live mode: use app._trade_network dict
- Replay mode: use build_trade_network() from analysis/emergence.py
- Metrics: compute from TradeNetworkStats or inline

Track progress via git commits. Update PRD passes values as features complete.
