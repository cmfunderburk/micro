# Ralph Loop Startup: Bilateral Protocols Expansion

Copy and paste the command below to start the ralph-loop.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest`
- [ ] On correct branch: `git branch` (should be `fundamentals` or feature branch)
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed and any edits made
- [ ] Frontend dependencies installed: `cd frontend && npm install`

---

## Startup Prompt

```
/ralph-loop:ralph-loop "Execute docs/prd/PRD-BILATERAL-PROTOCOLS-EXPANSION.json systematically.

PHASE ORDER:
1. Core Protocol Implementation (bargaining_power attr, TIOLI, Asymmetric Nash)
2. Theory Tests (O&R Ch 2-3 properties)
3. Server & UI Integration (routing, selector, tooltips, power distribution)
4. Documentation (CLAUDE.md, STATUS.md, docstrings)

Phases 2 and 3 can run in parallel after Phase 1.

CRITICAL REQUIREMENTS:
- TIOLI must use closed-form solution (responder exactly at disagreement utility)
- Asymmetric Nash uses agent.bargaining_power, NOT discount_factor
- Theory tests are PRIMARY verification (research software)
- UI must have tooltips explaining each protocol's power source

NAMING CONVENTION (per ADR-BP-001):
- 'Nash (Symmetric)' - NashBargainingProtocol
- 'Nash (Patience)' - RubinsteinBargainingProtocol
- 'Nash (Power)' - AsymmetricNashBargainingProtocol
- 'Take-It-Or-Leave-It' - TIOLIBargainingProtocol

ESCALATION: Stop if theory tests show divergence > 1e-3 or if TIOLI responder not at indifference.

Track progress via git commits and progress.txt. Update PRD feature passes as completed." --max-iterations 55 --completion-promise "BILATERAL-PROTOCOLS-EXPANSION-COMPLETE"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume docs/prd/PRD-BILATERAL-PROTOCOLS-EXPANSION.json execution.

Check current state:
1. Read progress.txt for last known state
2. Check PRD for feature passes values
3. Review recent git commits
4. Run uv run pytest to see current test status

Continue from where execution stopped. Maintain the naming convention and theory test requirements." --max-iterations 55 --completion-promise "BILATERAL-PROTOCOLS-EXPANSION-COMPLETE"
```

---

## Phase Continuation Prompts

### After Phase 1 (Core Implementation)

```
/ralph-loop:ralph-loop "Continue docs/prd/PRD-BILATERAL-PROTOCOLS-EXPANSION.json to Phase 2 (Theory Tests) and Phase 3 (Server & UI).

Phase 1 verified complete. These phases can run in parallel.

Focus on:
- Phase 2: Theory tests in tests/theory/ verifying O&R properties
- Phase 3: Server routing and UI with tooltips

Theory test tolerance: 1e-6 for closed-form solutions." --max-iterations 40 --completion-promise "BILATERAL-PROTOCOLS-EXPANSION-COMPLETE"
```

### After Phases 2 & 3 (Tests and UI)

```
/ralph-loop:ralph-loop "Continue docs/prd/PRD-BILATERAL-PROTOCOLS-EXPANSION.json to Phase 4 (Documentation).

Phases 1-3 verified complete. Update documentation:
- CLAUDE.md: Add new protocols to bargaining section
- STATUS.md: Update protocols table with O&R references
- Docstrings: Ensure all protocols explain their power source" --max-iterations 20 --completion-promise "BILATERAL-PROTOCOLS-EXPANSION-COMPLETE"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/prd/PRD-BILATERAL-PROTOCOLS-EXPANSION.json` | Full PRD specification |
| `VISION.md` | Authoritative project vision |
| `docs/current/ROADMAP-DISCUSSION-2026-01-08.md` | Design decisions context |
| `microecon/bargaining.py` | Main implementation file |
| `microecon/agent.py` | Agent class (add bargaining_power) |
| `tests/theory/test_nash_bargaining.py` | Existing theory test patterns |
| `server/simulation_manager.py` | Server protocol routing |
| `frontend/src/components/Config/ConfigModal.tsx` | UI protocol selector |

---

## Expected Outputs

### Phase 1: Core Protocol Implementation
- `microecon/agent.py`: `bargaining_power` attribute added
- `microecon/bargaining.py`: `tioli_bargaining_solution()`, `TIOLIBargainingProtocol`, `AsymmetricNashBargainingProtocol`
- `microecon/__init__.py`: New exports added
- Basic unit tests passing

### Phase 2: Theory Tests
- `tests/theory/test_tioli_bargaining.py`: TIOLI properties (proposer surplus, responder indifference, proposer identity)
- `tests/theory/test_asymmetric_nash_protocol.py`: Asymmetric Nash properties (reduces to symmetric, power→utility, maximizes weighted product)

### Phase 3: Server & UI
- `server/simulation_manager.py`: Protocol routing for 'tioli', 'asymmetric_nash'
- `frontend/src/components/Config/ConfigModal.tsx`: Four protocol options with tooltips
- `frontend/src/types/simulation.ts`: Updated protocol types
- Bargaining power distribution selector (when asymmetric_nash selected)

### Phase 4: Documentation
- `CLAUDE.md`: Updated bargaining protocols section
- `STATUS.md`: Updated protocols table
- Enhanced docstrings in `bargaining.py`

---

## Progress Tracking Template

Create `progress.txt` with this structure:

```markdown
# Progress Log: Bilateral Protocols Expansion

## Format
Each entry: [timestamp] [phase] [status] [description]

---

## Log

### Phase 1: Core Protocol Implementation

#### Completed
- [timestamp] FEAT-001: bargaining_power attribute - Added to Agent dataclass
- [timestamp] FEAT-002: tioli_bargaining_solution - Closed-form implementation

#### Issues Encountered
- [timestamp] ISSUE: [description]
  - Root cause: [cause]
  - Resolution: [resolution]

#### Skipped/Deferred
- [timestamp] SKIPPED: [feature] - [reason]

---

### Phase 2: Theory Tests
[same structure]

### Phase 3: Server & UI Integration
[same structure]

### Phase 4: Documentation
[same structure]

---

## Summary Statistics
| Metric | Count |
|--------|-------|
| Features completed | X/17 |
| Features skipped | X |
| Issues encountered | X |
| Phases completed | X/4 |
```

---

## Theory Test Reference

### TIOLI Properties (O&R Ch 3)

1. **Proposer extracts full surplus**: No feasible allocation gives proposer more while responder ≥ disagreement
2. **Responder at indifference**: `responder_utility == disagreement_utility` (within 1e-6)
3. **Pareto efficiency**: Allocation on contract curve
4. **Proposer identity matters**: Swapping proposer swaps surplus recipient

### Asymmetric Nash Properties (O&R Ch 2)

1. **Reduces to symmetric**: When w1 == w2, equals NashBargainingProtocol result
2. **Power monotonicity**: Higher bargaining_power → higher utility share
3. **Weighted product maximization**: Outcome maximizes (u1-d1)^β × (u2-d2)^(1-β)
4. **Individual rationality**: Both agents ≥ disagreement utility

---

## Verification Commands

```bash
# Run all tests
uv run pytest

# Run only theory tests
uv run pytest tests/theory/ -v

# Run new protocol tests specifically
uv run pytest tests/theory/test_tioli_bargaining.py tests/theory/test_asymmetric_nash_protocol.py -v

# Check imports work
uv run python -c "from microecon import TIOLIBargainingProtocol, AsymmetricNashBargainingProtocol"

# Start frontend for manual UI testing
./scripts/dev.sh
```

---

**Document Created:** 2026-01-08
**PRD Version:** 1.0
