# Ralph Loop Startup: Visualization Polish & Integration

Copy and paste the prompts below to execute the visualization PRD.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest`
- [ ] On correct branch: `git branch` (should be `tweaking` or create feature branch)
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed: `docs/current/PRD-VISUALIZATION-POLISH.json`
- [ ] Visualization currently runs: `uv run python -m microecon.visualization`

---

## Phase 1: Overlay Infrastructure & Toggles

```
/ralph-loop:ralph-loop "Execute Phase 1 of PRD-VISUALIZATION-POLISH.json: Overlay Infrastructure & Toggles.

GOAL: Add toggle panel and make existing overlays (trails, perception radius) toggleable.

FEATURES TO IMPLEMENT:
1. VIZ-001: Toggle Panel UI - Add collapsible panel in metrics area with toggle controls
2. VIZ-002: Movement Trails Toggle - Make trails toggleable, default ON
3. VIZ-003: Perception Radius Toggle - Add toggle for perception radius overlay

IMPLEMENTATION GUIDANCE:
- Add toggle state dict to VisualizationApp (e.g., self.overlays = {'trails': True, 'perception': True})
- Add UI section in metrics panel with dpg.add_checkbox for each toggle
- Modify render_trails() to check self.overlays['trails'] before rendering
- Modify render_perception_overlay() to check toggle state
- Apply same pattern to DualVisualizationApp for consistency

VERIFICATION:
- Run visualization: uv run python -m microecon.visualization
- Verify toggle panel appears
- Verify each toggle enables/disables its overlay
- Run existing tests: uv run pytest tests/

CONSTRAINTS:
- Do NOT modify simulation logic (simulation.py, agent.py, etc.)
- Preserve existing functionality - toggles default to current behavior
- Follow existing code patterns in app.py

Track progress via git commits. Mark features as passes:true in PRD when complete." --max-iterations 20 --completion-promise "<promise>VIZ-PHASE-1-COMPLETE</promise>"
```

---

## Phase 2: Belief Visualization

```
/ralph-loop:ralph-loop "Execute Phase 2 of PRD-VISUALIZATION-POLISH.json: Belief Visualization.

GOAL: Surface agent belief data in the UI - tooltips, selection panel, and visual encodings.

FEATURES TO IMPLEMENT:
1. VIZ-004: Belief Tooltip Extension - Add belief summary to hover tooltip
2. VIZ-005: Belief Panel for Selected Agent - Show detailed beliefs when agent selected
3. VIZ-006: Belief Connection Lines - Draw lines between agents with belief relationships
4. VIZ-007: Belief Evolution in Replay - Beliefs update when scrubbing timeline

CONTEXT:
- Belief data is in BeliefSnapshot (logging/events.py lines 355-384)
- TypeBeliefSnapshot has: target_agent_id, believed_alpha, confidence, n_interactions
- PriceBeliefSnapshot has: mean, variance, n_observations
- AgentSnapshot has: has_beliefs, n_trades_in_memory, n_type_beliefs
- In replay mode, belief_snapshots are in TickRecord

IMPLEMENTATION GUIDANCE:
- Extend AgentProxy to include belief data (or create BeliefProxy)
- Extend hover tooltip in render_hover_info() to show belief summary
- Add belief panel section in metrics panel (visible when agent selected)
- Add belief connection rendering using toggle infrastructure from Phase 1
- For replay mode, load belief_snapshots from TickRecord

VERIFICATION:
- Run with beliefs enabled: create simulation with enable_beliefs=True
- Hover over agents, verify belief info appears
- Select agent, verify belief panel shows
- Enable belief connections toggle, verify lines render
- Scrub timeline in replay, verify beliefs update

CONSTRAINTS:
- Phase 1 must be complete (toggle infrastructure required)
- Do NOT modify belief system itself, only visualize existing data
- Gracefully handle agents without beliefs (legacy runs, beliefs disabled)

Track progress via git commits. Mark features as passes:true in PRD when complete." --max-iterations 25 --completion-promise "<promise>VIZ-PHASE-2-COMPLETE</promise>"
```

---

## Phase 3: Export Capabilities

```
/ralph-loop:ralph-loop "Execute Phase 3 of PRD-VISUALIZATION-POLISH.json: Export Capabilities.

GOAL: Add export functionality for screenshots, animations, and data.

FEATURES TO IMPLEMENT:
1. VIZ-008: PNG Screenshot Export - Export current state as PNG with configurable resolution
2. VIZ-009: SVG Vector Export - Export as SVG for publication figures
3. VIZ-010: GIF Animation Export - Export replay as animated GIF
4. VIZ-011: Data Export (CSV/JSON) - Export simulation data for external analysis

IMPLEMENTATION GUIDANCE:
- Add Export section to UI (button group or menu)
- For PNG: Use dpg.output_frame_buffer() or manual rendering to Pillow Image
- For SVG: May need custom SVG generation from draw commands (or skip if too complex)
- For GIF: Capture frames during replay, assemble with imageio
- For data export: Serialize current state or full run to CSV/JSON
- Add file dialog for save location (dpg.add_file_dialog)

DEPENDENCIES:
- May need to add: pillow, imageio to pyproject.toml
- Check existing dependencies first: uv pip list

VERIFICATION:
- Export PNG, verify file opens in image viewer
- Export GIF from replay, verify animation plays
- Export CSV/JSON, verify data is valid and matches simulation

CONSTRAINTS:
- Export should not interrupt running simulation
- Large exports (long GIFs) should show progress indicator
- Handle errors gracefully (disk full, permissions, etc.)

Track progress via git commits. Mark features as passes:true in PRD when complete." --max-iterations 25 --completion-promise "<promise>VIZ-PHASE-3-COMPLETE</promise>"
```

---

## Phase 4: Trade Zoom & Edgeworth Box

```
/ralph-loop:ralph-loop "Execute Phase 4 of PRD-VISUALIZATION-POLISH.json: Trade Zoom & Edgeworth Box.

GOAL: Implement trade detail view with Edgeworth box visualization.

FEATURES TO IMPLEMENT:
1. VIZ-012: Trade Click Detection - Click on trade to open detail view
2. VIZ-013: Edgeworth Box Rendering - Render 2-agent 2-good allocation space
3. VIZ-014: Edgeworth Box Content - Draw allocations, indifference curves, contract curve

THEORETICAL CONTEXT:
- Edgeworth box: Rectangle where width = total X endowment, height = total Y endowment
- Agent A's origin at bottom-left, Agent B's origin at top-right
- Any point represents a feasible allocation
- Indifference curves: For Cobb-Douglas u = x^alpha * y^(1-alpha), solve for y given u and x
- Contract curve: Locus of Pareto efficient allocations (MRS_A = MRS_B)
- See preferences.py for MRS calculation

IMPLEMENTATION GUIDANCE:
- Create new module: visualization/edgeworth.py
- EdgeworthBoxView class with DearPyGui modal window
- Store trade data: agent types, pre/post allocations
- Numerical indifference curve: sample x values, compute y = (u / x^alpha)^(1/(1-alpha))
- Contract curve: sample allocations where MRS_A = MRS_B (numerical search)
- Click detection: check if click is on active trade animation or timeline marker

VERIFICATION:
- Click on trade animation, verify detail view opens
- Verify Edgeworth box has correct dimensions
- Verify initial and final allocations are marked
- Verify indifference curves pass through correct points
- Verify final allocation is on contract curve

CONSTRAINTS:
- Must handle edge cases (zero allocations, extreme preferences)
- Modal should be closeable (click outside or X button)
- Performance: curves should render smoothly

Track progress via git commits. Mark features as passes:true in PRD when complete." --max-iterations 30 --completion-promise "<promise>VIZ-PHASE-4-COMPLETE</promise>"
```

---

## Phase 5: Agent Perspective Mode

```
/ralph-loop:ralph-loop "Execute Phase 5 of PRD-VISUALIZATION-POLISH.json: Agent Perspective Mode.

GOAL: Add mode to view simulation from a specific agent's information state.

FEATURES TO IMPLEMENT:
1. VIZ-015: Perspective Mode Toggle - Switch between omniscient and agent perspective
2. VIZ-016: Agent Perspective Rendering - Show what selected agent observes
3. VIZ-017: Perspective Comparison - Compare agent's view vs ground truth

CONTEXT:
- Under FullInformation: agents see true types (no difference from omniscient)
- Under NoisyAlphaInformation: agents see noisy observations of alpha
- Perception radius determines which agents are visible
- Belief system stores agent's beliefs about others

IMPLEMENTATION GUIDANCE:
- Add perspective mode toggle to control panel
- When enabled, show agent selector dropdown
- In perspective mode rendering:
  - Dim/hide agents outside selected agent's perception radius
  - Color agents by OBSERVED alpha (from info environment) not TRUE alpha
  - Highlight the selected perspective agent
  - Show perception radius circle
- For comparison: could use split view or overlay showing differences

VERIFICATION:
- Run with NoisyAlphaInformation to see meaningful differences
- Toggle perspective mode, verify display changes
- Select different agents, verify perspective updates
- Compare observed vs true types, verify they differ under noisy info

CONSTRAINTS:
- Must work in both live and replay modes
- Perspective agent selector should only show existing agents
- Graceful fallback when info environment is FullInformation

Track progress via git commits. Mark features as passes:true in PRD when complete." --max-iterations 20 --completion-promise "<promise>VIZ-PHASE-5-COMPLETE</promise>"
```

---

## Phase 6: Advanced Overlays

```
/ralph-loop:ralph-loop "Execute Phase 6 of PRD-VISUALIZATION-POLISH.json: Advanced Overlays.

GOAL: Add trade network overlay and surplus heatmap overlay.

FEATURES TO IMPLEMENT:
1. VIZ-018: Trade Network Overlay - Show trade relationships between agents
2. VIZ-019: Surplus Heatmap Overlay - Show potential gains from trade across grid

IMPLEMENTATION GUIDANCE:

Trade Network:
- Track which agent pairs have traded (from trade history in logs)
- Draw edges between agents who have traded
- Edge encoding options: thickness = trade count, color = recency, opacity = surplus
- Integrate with toggle system from Phase 1

Surplus Heatmap:
- For each grid cell, compute aggregate surplus potential
- Surplus between agents = Nash bargaining surplus (see bargaining.py)
- Render as color gradient overlay on grid (behind agents)
- Legend showing surplus scale
- Performance consideration: compute once per tick, not per frame

VERIFICATION:
- Enable trade network toggle, verify edges appear after trades occur
- Verify edges connect correct agent pairs
- Enable surplus heatmap, verify color gradient renders
- Verify high-surplus areas correspond to complementary agent pairs

CONSTRAINTS:
- Must use toggle infrastructure from Phase 1
- Overlays should not obscure agent visibility
- Performance: heatmap computation should not cause lag

Track progress via git commits. Mark features as passes:true in PRD when complete." --max-iterations 20 --completion-promise "<promise>VIZ-PHASE-6-COMPLETE</promise>"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume PRD-VISUALIZATION-POLISH.json execution.

Check current state:
1. Read PRD file for feature passes values and phase status
2. Check recent git commits: git log --oneline -10
3. Run tests: uv run pytest tests/ -v

Continue from where execution stopped. Identify which features are incomplete and proceed.

Ask before proceeding to a new phase." --max-iterations 30 --completion-promise "<promise>VIZ-RESUME</promise>"
```

---

## Phase Continuation Prompt

After reviewing a completed phase and approving continuation:

```
/ralph-loop:ralph-loop "Continue PRD-VISUALIZATION-POLISH.json to Phase [N]: [Phase Name].

Previous phase verified complete. All tests pass. Proceed with Phase [N] features.

See START-RALPH-LOOP-VISUALIZATION.md for phase-specific guidance." --max-iterations 25 --completion-promise "<promise>VIZ-PHASE-[N]-COMPLETE</promise>"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/current/PRD-VISUALIZATION-POLISH.json` | Full PRD specification |
| `VISUALIZATION.md` | UI/UX design vision |
| `VISION.md` | Project vision (institutional visibility) |
| `src/microecon/visualization/app.py` | Main visualization code |
| `src/microecon/visualization/timeseries.py` | Time-series charts |
| `src/microecon/visualization/browser.py` | Startup selector |
| `src/microecon/visualization/replay.py` | Replay controllers |
| `src/microecon/beliefs.py` | Belief data structures |
| `src/microecon/logging/events.py` | BeliefSnapshot, TypeBeliefSnapshot |

---

## Expected Outputs by Phase

**Phase 1: Overlay Infrastructure**
- Modified `app.py` with toggle state and UI
- Toggle panel in metrics area
- Toggleable trails and perception radius

**Phase 2: Belief Visualization**
- Extended tooltip with belief info
- Belief panel for selected agent
- Belief connection lines overlay
- Belief updates in replay mode

**Phase 3: Export**
- Export UI (buttons/menu)
- PNG export functionality
- GIF export functionality
- CSV/JSON data export
- Possibly new dependencies in pyproject.toml

**Phase 4: Edgeworth Box**
- New module: `visualization/edgeworth.py`
- Trade click detection
- Edgeworth box modal with theoretical content

**Phase 5: Agent Perspective**
- Perspective mode toggle and agent selector
- Modified rendering for perspective view
- Comparison view (optional)

**Phase 6: Advanced Overlays**
- Trade network overlay
- Surplus heatmap overlay
- Integration with toggle system

---

## Final Verification

When all phases complete:

```bash
# Run all tests
uv run pytest

# Run visualization and verify all features
uv run python -m microecon.visualization

# Verify in PRD that all features have passes: true
cat docs/current/PRD-VISUALIZATION-POLISH.json | grep '"passes"'
```

---

**Document Version:** 1.0
**Created:** 2026-01-07
