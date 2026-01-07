# Ralph Loop Startup: Visualization Polish & Integration

Copy and paste the prompt below to execute the full visualization PRD.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest`
- [ ] On correct branch: `git branch` (should be `tweaking` or create feature branch)
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed: `docs/current/PRD-VISUALIZATION-POLISH.json`
- [ ] Visualization currently runs: `uv run python -m microecon.visualization`

---

## Full PRD Execution Prompt

```
/ralph-loop:ralph-loop "Execute PRD-VISUALIZATION-POLISH.json in full.

GOAL: Implement comprehensive visualization layer updates across all 6 phases.

PRD LOCATION: docs/current/PRD-VISUALIZATION-POLISH.json

PHASES:
1. Overlay Infrastructure & Toggles (VIZ-001 to VIZ-003)
2. Belief Visualization (VIZ-004 to VIZ-007)
3. Export Capabilities (VIZ-008 to VIZ-011)
4. Trade Zoom & Edgeworth Box (VIZ-012 to VIZ-014)
5. Agent Perspective Mode (VIZ-015 to VIZ-017)
6. Advanced Overlays (VIZ-018 to VIZ-019)

EXECUTION PROTOCOL:
- Work through phases sequentially (later phases depend on earlier ones)
- Within each phase, implement all features before moving on
- Commit after completing each feature or logical unit of work
- Mark features as passes:true in the PRD as they are completed
- Run tests frequently: uv run pytest

PHASE TRANSITION PROTOCOL:
- When a phase is complete, use the AskUserQuestion tool to request review
- Present: what was implemented, verification performed, any issues encountered
- Wait for user confirmation before proceeding to the next phase
- Do NOT use completion promises between phases

CONSTRAINTS:
- Do NOT modify core simulation logic (simulation.py, agent.py, bargaining.py, etc.)
- Visualization is a read-only consumer of simulation data
- Preserve existing functionality - new features should not break current behavior
- Follow existing code patterns in visualization/app.py

VERIFICATION:
- Run visualization after each feature: uv run python -m microecon.visualization
- Run test suite: uv run pytest
- Verify PRD feature criteria are met before marking passes:true

KEY FILES:
- src/microecon/visualization/app.py - Main visualization
- src/microecon/visualization/timeseries.py - Time-series charts
- src/microecon/beliefs.py - Belief data structures
- src/microecon/logging/events.py - BeliefSnapshot, TypeBeliefSnapshot

PHASE-SPECIFIC GUIDANCE:

Phase 1 - Overlay Infrastructure:
- Add toggle state dict to VisualizationApp
- Add UI section in metrics panel with checkboxes
- Make render_trails() and render_perception_overlay() check toggle state
- Apply same pattern to DualVisualizationApp

Phase 2 - Belief Visualization:
- Belief data is in BeliefSnapshot (logging/events.py)
- TypeBeliefSnapshot: target_agent_id, believed_alpha, confidence, n_interactions
- Extend AgentProxy or create BeliefProxy for belief data access
- Use toggle infrastructure from Phase 1 for belief connection lines

Phase 3 - Export:
- May need pillow, imageio dependencies
- PNG: dpg.output_frame_buffer() or manual rendering
- GIF: capture frames during replay, assemble with imageio
- Data export: serialize state to CSV/JSON

Phase 4 - Edgeworth Box:
- Create visualization/edgeworth.py module
- Indifference curves: y = (u / x^alpha)^(1/(1-alpha))
- Contract curve: locus where MRS_A = MRS_B
- See preferences.py for MRS calculation

Phase 5 - Agent Perspective:
- Under NoisyAlphaInformation, show observed types not true types
- Dim/hide agents outside perception radius
- Must work in both live and replay modes

Phase 6 - Advanced Overlays:
- Trade network from trade history in logs
- Surplus heatmap computed from Nash bargaining surplus
- Integrate with toggle system from Phase 1

Track progress via git commits. Update PRD passes values as features complete." --max-iterations 100 --completion-promise "<promise>VISUALIZATION-POLISH-COMPLETE</promise>"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume PRD-VISUALIZATION-POLISH.json execution.

Check current state:
1. Read PRD file for feature passes values
2. Check recent git commits: git log --oneline -10
3. Run tests: uv run pytest

Continue from where execution stopped. Follow the phase transition protocol:
use AskUserQuestion to request review when completing a phase.

Track progress via git commits." --max-iterations 50 --completion-promise "<promise>VISUALIZATION-POLISH-COMPLETE</promise>"
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

**Document Version:** 2.0
**Created:** 2026-01-07
**Updated:** 2026-01-07 - Consolidated to single prompt with AskUserQuestion phase transitions
