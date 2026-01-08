# Ralph Loop Startup: PRD-PHASES-0-1

Copy and paste the command below to start the ralph-loop for Phases 0-1.

---

```
/ralph-loop:ralph-loop "Execute PRD-PHASES-0-1.json systematically.

PHASE 0 (Theoretical Alignment):
1. Create tests/theory/ directory
2. Implement THEORY-001 through THEORY-005 test files verifying Nash bargaining, Rubinstein SPE, preferences, gains from trade, and Pareto efficiency
3. Run tests, document any divergences in docs/current/THEORY-DIVERGENCES.md
4. Fix divergences or document as acceptable with rationale
5. When Phase 0 complete: use AskUserQuestion to request approval before proceeding

PHASE 1 (Agent Belief Architecture):
1. First create ADR-BELIEF-ARCHITECTURE.md - review against Kreps I Ch 5-7
2. Use AskUserQuestion to get ADR approval before implementation
3. Implement BELIEF-002 through BELIEF-006 per PRD specifications
4. Ensure all 450+ existing tests still pass

CONSTRAINTS:
- Phase 0 must fully complete before Phase 1 begins
- Use AskUserQuestion for: any divergence found, phase transitions, ADR approval, design ambiguities
- Test tolerances: strict (rel=1e-6) for formulas, moderate (rel=1e-3) for optimization
- Commit with conventional format: test(theory): ..., feat(beliefs): ..., docs: ...

Track progress via git commits, update PRD status fields as features complete." --max-iterations 20 --completion-promise "MICROECON PRD-PHASES-0-1 COMPLETE"
```

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `uv run pytest`
- [ ] On correct branch: `git branch`
- [ ] Working directory clean: `git status`

## Key Files

| File | Purpose |
|------|---------|
| `PRD-PHASES-0-1.json` | Full PRD specification |
| `VISION.md` | Authoritative project vision |
| `docs/current/DEVELOPMENT-PLAN.md` | Narrative context |
| `docs/current/WORK-ITEMS.md` | Issue tracker breakdown |
| `theoretical-foundations.md` | Theory reference mappings |

## Expected Outputs

**Phase 0:**
- `tests/theory/test_nash_bargaining.py`
- `tests/theory/test_rubinstein_bargaining.py`
- `tests/theory/test_preferences.py`
- `tests/theory/test_gains_from_trade.py`
- `tests/theory/test_pareto_efficiency.py`
- `docs/current/THEORY-DIVERGENCES.md`

**Phase 1:**
- `docs/current/ADR-BELIEF-ARCHITECTURE.md`
- `src/microecon/beliefs.py`
- `tests/test_beliefs.py`
- Updates to `agent.py`, `search.py`, `bargaining.py`
