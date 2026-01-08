---
active: true
iteration: 1
max_iterations: 20
completion_promise: "WEB-FRONTEND-PARITY-COMPLETE"
started_at: "2026-01-08T15:59:13Z"
---

Execute docs/prd/PRD-WEB-FRONTEND-PARITY.json systematically.

This PRD fixes critical bugs and brings the web frontend to feature parity with the archived Python/DearPyGui implementation.

PHASE ORDER:
1. Critical Fixes - WebSocket concurrency, reset semantics, config broadcast, dev script
2. Core Polish - PNG export, overlay defaults, trade network stability
3. Belief System - Panel, connections overlay, use_beliefs toggle
4. Perspective Mode - Agent selector, toggle, ground truth
5. Comparison Mode - Multi-sim server, dual grid, sync controls
6. Replay Mode - Load runs, timeline seeking, step-back
7. Finishing - Trade animation, scenario browser, keyboard shortcuts

KEY DECISIONS (from ADRs):
- WebSocket: Session-based simulation ownership (client can create multiple sims)
- Replay: Client-side preload (load full RunData, seek locally)
- Reset: Clears all UI state (history, trails, connections)

REFERENCE: docs/FEATURE-PARITY-REFERENCE.md has full Python feature inventory

Track progress via git commits. Continue through phases automatically (HOTL mode).
