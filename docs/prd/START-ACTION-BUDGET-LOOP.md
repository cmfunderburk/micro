# Ralph Loop Startup: ACTION-BUDGET-MODEL

Copy and paste the command below to start the ralph-loop.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest -m "not slow" -q`
- [ ] On correct branch: `git branch` (should be `fundamentals` or feature branch)
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed: `docs/prd/ACTION-BUDGET-MODEL.json`
- [ ] Architecture doc current: `docs/current/AGENT-ARCHITECTURE.md` (v0.4)

---

## Startup Prompt

```
/ralph-loop:ralph-loop "Execute docs/prd/ACTION-BUDGET-MODEL.json systematically.

This PRD implements the action budget model from AGENT-ARCHITECTURE.md:
- Trade execution costs 1 action for BOTH parties
- Coordination (propose/accept/reject) is free
- Failed proposals trigger fallback execution
- Acceptance uses opportunity cost comparison

PHASE 1 (Core Mechanics):
- FEAT-001: Add fallback field to ProposeAction
- FEAT-002: Compute fallback in choose()
- FEAT-003: Store opportunity cost in agent state
- FEAT-004: Update evaluate_proposal for opportunity cost
- FEAT-005: Execute fallback on proposal failure

PHASE 2 (Integration & Polish):
- FEAT-006: Exclude cooldown targets from search
- FEAT-007: Theory verification tests
- FEAT-008: Scenario tests (5 key scenarios)
- FEAT-009: Edge case handling

CONSTRAINTS:
- Do NOT modify bargaining protocol behavior
- Maintain backward compatibility where possible
- Each feature should have tests before moving to next
- Run existing tests after each change to catch regressions

Track progress via git commits. Update PRD status fields as features complete." --max-iterations 40 --completion-promise "ACTION-BUDGET-MODEL-COMPLETE"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume docs/prd/ACTION-BUDGET-MODEL.json execution.

Check current state:
1. Read progress.txt for last known state
2. Check PRD for feature passes values
3. Review recent git commits

Continue from where execution stopped." --max-iterations 40 --completion-promise "ACTION-BUDGET-MODEL-COMPLETE"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/prd/ACTION-BUDGET-MODEL.json` | Full PRD specification |
| `docs/current/AGENT-ARCHITECTURE.md` | Authoritative architecture (§7.1-7.9) |
| `microecon/actions.py` | ProposeAction modification |
| `microecon/decisions.py` | choose() and evaluate_proposal() |
| `microecon/simulation.py` | _execute_actions() fallback execution |
| `microecon/search.py` | Cooldown exclusion |

---

## Expected Outputs

**Phase 1:**
- Modified `microecon/actions.py` - ProposeAction.fallback field
- Modified `microecon/decisions.py` - fallback computation, opportunity cost storage, acceptance check
- Modified `microecon/simulation.py` - fallback execution in _execute_actions()
- New/updated tests in `tests/test_decisions.py`
- New/updated tests in `tests/test_simulation.py`

**Phase 2:**
- Modified `microecon/search.py` - cooldown exclusion
- New test file `tests/test_action_budget.py` - theory verification
- New test file `tests/scenarios/test_action_budget.py` - scenario tests
- Updated `tests/test_edge_cases.py` - edge case tests

---

## Progress Tracking Template

Create `progress.txt` in project root:

```markdown
# Progress Log: ACTION-BUDGET-MODEL

## Format
Each entry follows: [timestamp] [phase] [status] [description]

---

## Log

### Phase 1: Core Mechanics

#### Completed
- [timestamp] FEAT-001: ProposeAction fallback field - [description]

#### Issues Encountered
- [timestamp] ISSUE: [description]
  - Root cause: [what caused it]
  - Resolution: [how it was fixed]

#### Workarounds Applied
- [timestamp] WORKAROUND: [description]
  - Reason: [why needed]

---

### Phase 2: Integration & Polish

#### Completed

#### Issues Encountered

---

## Summary Statistics
| Metric | Count |
|--------|-------|
| Features completed | 0/9 |
| Issues encountered | 0 |
| Phases completed | 0/2 |
```

---

## Verification Commands

```bash
# Run all non-slow tests
uv run pytest -m "not slow" -q

# Run specific test files
uv run pytest tests/test_actions.py -v
uv run pytest tests/test_decisions.py -v
uv run pytest tests/test_simulation.py -v
uv run pytest tests/test_search.py -v

# Run with specific markers
uv run pytest -v -k fallback
uv run pytest -v -k opportunity
uv run pytest -v -k cooldown
```
