# Ralph Loop Startup: Agent Architecture Rework

Copy and paste the command below to start the ralph-loop.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest`
- [ ] On correct branch: `git branch` (should be `fundamentals` or new feature branch)
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed: `docs/prd/PRD-AGENT-ARCHITECTURE.json`
- [ ] ADRs reviewed and approved:
  - [ ] `docs/adr/ADR-001-TICK-MODEL.md`
  - [ ] `docs/adr/ADR-002-INTERACTION-STATE.md`
  - [ ] `docs/adr/ADR-003-EXCHANGE-SEQUENCE.md`
  - [ ] `docs/adr/ADR-004-EVENT-CORRELATION.md`

---

## Startup Prompt

```
/ralph-loop:ralph-loop "Execute docs/prd/PRD-AGENT-ARCHITECTURE.json systematically.

This is a foundational architecture rework. Execute phases in order:

PHASE 1 - Agent Foundation:
- Add Holdings attribute to Agent (mutable, initialized from endowment)
- Make Endowment immutable after construction
- Update bargaining to mutate holdings not endowment
- Define InteractionState dataclass with Available/ProposalPending/Negotiating
- Add interaction_state attribute to Agent

PHASE 2 - Action System:
- Define Action ABC with type, cost(), preconditions(), transform(), tags
- Implement Move, Propose, Accept, Reject, Wait action classes
- Define DecisionProcedure interface
- Implement RationalDecisionProcedure baseline

PHASE 3 - Tick Restructure:
- Replace 4-phase tick loop with 3-phase (Perceive, Decide, Execute)
- Implement conflict resolution (multiple proposals, mutual proposals)
- Remove CommitmentState from matching.py
- Update simulation.py to use new tick structure

PHASE 4 - Exchange Sequence:
- Implement multi-tick exchange: Propose -> Accept/Reject -> Negotiate -> Execute
- Implement state transitions per ADR-002
- Add co-location validation throughout
- Implement cooldown mechanics

PHASE 5 - Event System:
- Add ProposalEvent, ProposalResponseEvent, NegotiationEvent, CooldownEvent
- Add exchange_id to all exchange events
- Update TickRecord with interaction_states snapshot
- Implement analysis query functions

PHASE 6 - Test Restoration:
- Fix broken simulation tests
- Remove CommitmentState tests, add InteractionState tests
- Add property tests for invariants (state machine, conservation)
- Verify all theory tests pass

CONSTRAINTS:
- Accept temporary test breakage during refactoring
- Phases are sequential (dependencies in PRD)
- Theory tests (bargaining outcomes) must pass at completion
- Conservation law (sum holdings = sum endowments) must hold

Track progress via git commits and progress.txt. Update PRD feature passes as they complete." --max-iterations 60 --completion-promise "AGENT-ARCHITECTURE-COMPLETE"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume docs/prd/PRD-AGENT-ARCHITECTURE.json execution.

Check current state:
1. Read progress.txt for last known state
2. Check PRD for feature passes values
3. Review recent git commits
4. Run tests to see current state: uv run pytest --tb=no -q

Continue from where execution stopped. This is HOTL mode - proceed automatically between phases." --max-iterations 60 --completion-promise "AGENT-ARCHITECTURE-COMPLETE"
```

---

## Phase-Specific Prompts (if needed)

### Phase 1 Only
```
/ralph-loop:ralph-loop "Execute Phase 1 of docs/prd/PRD-AGENT-ARCHITECTURE.json.

Focus on Agent Foundation:
- FEAT-001: Holdings attribute
- FEAT-002: Trade updates holdings not endowment
- FEAT-003: InteractionState dataclass

Stop after Phase 1 gate verification passes." --max-iterations 15 --completion-promise "AGENT-ARCHITECTURE-PHASE-1-COMPLETE"
```

### Phase 2 Only
```
/ralph-loop:ralph-loop "Execute Phase 2 of docs/prd/PRD-AGENT-ARCHITECTURE.json.

Phase 1 verified complete. Focus on Action System:
- FEAT-004: Action ABC
- FEAT-005: Concrete action types
- FEAT-006: DecisionProcedure interface
- FEAT-007: RationalDecisionProcedure

Stop after Phase 2 gate verification passes." --max-iterations 15 --completion-promise "AGENT-ARCHITECTURE-PHASE-2-COMPLETE"
```

### Phase 3 Only
```
/ralph-loop:ralph-loop "Execute Phase 3 of docs/prd/PRD-AGENT-ARCHITECTURE.json.

Phases 1-2 verified complete. Focus on Tick Restructure:
- FEAT-008: Perceive phase
- FEAT-009: Decide phase
- FEAT-010: Execute phase
- FEAT-011: Conflict resolution

Stop after Phase 3 gate verification passes." --max-iterations 15 --completion-promise "AGENT-ARCHITECTURE-PHASE-3-COMPLETE"
```

### Phase 4 Only
```
/ralph-loop:ralph-loop "Execute Phase 4 of docs/prd/PRD-AGENT-ARCHITECTURE.json.

Phases 1-3 verified complete. Focus on Exchange Sequence:
- FEAT-012: Proposal state transition
- FEAT-013: Acceptance state transition
- FEAT-014: Negotiation and trade execution
- FEAT-015: Co-location validation
- FEAT-016: Cooldown mechanics

Stop after Phase 4 gate verification passes." --max-iterations 15 --completion-promise "AGENT-ARCHITECTURE-PHASE-4-COMPLETE"
```

### Phase 5 Only
```
/ralph-loop:ralph-loop "Execute Phase 5 of docs/prd/PRD-AGENT-ARCHITECTURE.json.

Phase 4 verified complete. Focus on Event System:
- FEAT-017: New event types
- FEAT-018: exchange_id generation and propagation
- FEAT-019: TickRecord updates
- FEAT-020: Analysis query functions

Stop after Phase 5 gate verification passes." --max-iterations 10 --completion-promise "AGENT-ARCHITECTURE-PHASE-5-COMPLETE"
```

### Phase 6 Only
```
/ralph-loop:ralph-loop "Execute Phase 6 of docs/prd/PRD-AGENT-ARCHITECTURE.json.

Phases 1-5 verified complete. Focus on Test Restoration:
- FEAT-021: Fix simulation tests
- FEAT-022: Fix matching tests
- FEAT-023: Property tests for invariants
- FEAT-024: Theory test preservation

All tests must pass. Run: uv run pytest" --max-iterations 20 --completion-promise "AGENT-ARCHITECTURE-COMPLETE"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/prd/PRD-AGENT-ARCHITECTURE.json` | Full PRD specification |
| `VISION.md` | Authoritative project vision |
| `docs/current/AGENT-ARCHITECTURE.md` | Target architecture specification |
| `docs/current/ROADMAP.md` | Development roadmap context |
| `docs/adr/ADR-001-TICK-MODEL.md` | Three-phase tick decision |
| `docs/adr/ADR-002-INTERACTION-STATE.md` | Interaction state machine decision |
| `docs/adr/ADR-003-EXCHANGE-SEQUENCE.md` | Multi-tick exchange decision |
| `docs/adr/ADR-004-EVENT-CORRELATION.md` | Event correlation decision |

---

## Expected Outputs

### Phase 1: Agent Foundation
- Modified `microecon/agent.py` with holdings attribute and InteractionState
- Modified `microecon/bargaining.py` to update holdings
- New tests for holdings/endowment separation

### Phase 2: Action System
- New `microecon/actions.py` with Action ABC and concrete types
- New `microecon/decisions.py` with DecisionProcedure interface
- New `tests/test_actions.py` and `tests/test_decisions.py`

### Phase 3: Tick Restructure
- Modified `microecon/simulation.py` with 3-phase tick loop
- Modified `microecon/matching.py` (CommitmentState removed)
- Conflict resolution logic added

### Phase 4: Exchange Sequence
- New `microecon/exchange.py` or integrated into simulation
- State transition logic
- New `tests/test_exchange.py`

### Phase 5: Event System
- Modified `microecon/logging/events.py` with new event types
- Modified logging throughout for exchange_id
- New analysis functions in `microecon/analysis/`

### Phase 6: Test Restoration
- All tests in `tests/` passing
- New `tests/test_properties.py` with hypothesis tests

---

## Progress Tracking Template

Create `progress.txt` with this structure:

```markdown
# Progress Log: Agent Architecture Rework

## Format
Each entry follows: [timestamp] [phase] [status] [description]

---

## Log

### Phase 1: Agent Foundation

#### Completed
- [timestamp] FEAT-001: Holdings attribute - Added to Agent class
- [timestamp] FEAT-002: Trade updates holdings - Bargaining updated
- [timestamp] FEAT-003: InteractionState - Dataclass defined

#### Issues Encountered
- [timestamp] ISSUE: [description]
  - Root cause: [what caused it]
  - Resolution: [how it was fixed]

#### Workarounds Applied
- [timestamp] WORKAROUND: [what was done differently]
  - Reason: [why needed]

---

### Phase 2: Action System
[same structure]

---

### Phase 3: Tick Restructure
[same structure]

---

### Phase 4: Exchange Sequence
[same structure]

---

### Phase 5: Event System
[same structure]

---

### Phase 6: Test Restoration
[same structure]

---

## Summary Statistics
| Metric | Count |
|--------|-------|
| Features completed | 0/24 |
| Features skipped | 0 |
| Issues encountered | 0 |
| Workarounds applied | 0 |
| Phases completed | 0/6 |
| Tests passing | 667/667 |
```

---

## Verification Commands

```bash
# Check current test status
uv run pytest --tb=no -q

# Run specific test categories
uv run pytest -m core -v          # Core data structures
uv run pytest -m theory -v        # Theory verification
uv run pytest -m simulation -v    # Simulation tests
uv run pytest -m bargaining -v    # Bargaining tests

# Check for conservation law (after Phase 1+)
uv run pytest -k "conservation" -v

# Full test suite
uv run pytest

# With coverage
uv run pytest --cov=microecon
```

---

## Escalation Triggers

Stop and ask if:
- Theory tests fail (bargaining outcomes wrong)
- More than 50% of tests failing unexpectedly
- Conservation law violated (holdings sum != endowments sum)
- Architectural question not covered by ADRs
