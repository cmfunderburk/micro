# Phase 1 Code Review: Decision Log

**Date:** 2026-01-07
**Scope:** PRD-PHASES-0-1 (commits 5029e8a..49a9ee5)
**Source Reviews:** CODE_REVIEW_PRD_PHASES_0_1.md, CODE_REVIEW_PHASE_1_FINAL.md (archived to .archived/)

---

## Executive Summary

Phase 0 (Theory Verification) succeeded - theory tests exist and pass, Nash optimizer is correct, and the codebase has stronger theoretical grounding.

Phase 1 (Belief Architecture) produced complete components but incomplete integration. The belief system exists as a horizontal layer (all primitives implemented), but vertical wiring is missing: beliefs don't update during simulation, bargaining ignores beliefs, and logging doesn't capture belief state.

**Root cause:** The PRD and ralph-loop prompt were file-focused rather than behavior-focused. Expected outputs listed artifacts to create, not observable behaviors to produce.

---

## Lessons Learned: Ralph Loop Process

### LL-01: Behavior-Focused Over File-Focused Specifications

**Problem:** The START-RALPH-LOOP.md prompt specified:
- "Implement BELIEF-002 through BELIEF-006 per PRD specifications"
- Expected outputs: `src/microecon/beliefs.py`, `tests/test_beliefs.py`, "Updates to agent.py, search.py, bargaining.py"

This is file-focused. The loop created the files. But "updates to bargaining.py" didn't specify *what behavior should change*.

**Lesson:** PRD features and ralph-loop prompts should specify observable behavior changes, not just artifacts:

```
## Expected Behaviors (not just files)

After Phase 1:
- When agents trade, their belief state updates
  Verify: simulation log shows belief changes after trades
- Bargaining outcomes differ under belief-enabled vs belief-disabled
  Verify: comparison test shows different allocations
- Logging captures belief state
  Verify: TickRecord contains believed_alpha field
```

**Ralph Interview Improvement:** Add to Phase 3 (Verification Design):
> "For each feature, what observable behavior change does it produce in the running system? If the answer is 'none yet,' integration features are missing from the PRD."

### LL-02: ADR Divergence Should Trigger Escalation

**Problem:** The ADR specified `AgentType` in memory interfaces; implementation used `observed_alpha: float`. This divergence happened silently - no AskUserQuestion was triggered.

**Lesson:** The prompt included "Use AskUserQuestion for: any divergence found, phase transitions, ADR approval, design ambiguities" - but "divergence" was interpreted as theory divergence, not ADR divergence.

**Ralph Interview Improvement:** Add explicit escalation trigger:
> "Implementation interface diverges from approved ADR"

### LL-03: Placeholder Tests Mask Incomplete Work

**Problem:** Some tests compute results but assert nothing (`test_should_trade_uses_beliefs` computes `result_with_beliefs` but has no assertions). These pass, creating false confidence.

**Lesson:** This is a difficult problem. The loop created test shapes as scaffolding but didn't complete them. Options:
1. Escalation trigger: "Test created without meaningful assertions"
2. Verification command that checks assertion density
3. Require AskUserQuestion for tests where expected behavior is ambiguous

**Ralph Interview Improvement:** Add to escalation triggers:
> "Test file created with placeholder or assertion-free test methods"

### LL-04: Horizontal-First Was Correct, But Wiring Features Were Missing

**Problem:** The belief system was built as a complete horizontal layer before vertical integration. This is appropriate for theory-grounded research software - the conceptual foundation should be sound before wiring.

**Lesson:** The issue wasn't the horizontal-first approach. The issue was that "wiring" features weren't in the PRD at all. Integration wasn't deferred - it was omitted.

**Ralph Interview Improvement:** During gap analysis (Phase 1), explicitly ask:
> "For each new subsystem, what existing systems must it connect to? Are those connection points represented as PRD features?"

---

## Findings & Decisions

### FIND-01: Belief Updates Not Wired to Simulation Loop

**Context:** The exchange phase in `simulation.py:357-384` executes trades but never calls `record_trade_observation`, `record_encounter`, or `record_observed_trade` from `beliefs.py`.

**Impact:** Agents have memory infrastructure but never form memories. Belief-enabled agents do not learn. BELIEF-005/006 behavior is not realized.

**VISION Alignment:** Fails "Agent Sophistication as Experimental Variable" - agents remain static despite having belief capacity.

**Decision:** See RESOLUTION-01 in PHASE1-RESOLUTIONS.md

**Status:** Pending resolution review

---

### FIND-02: Bargaining Protocols Ignore Beliefs

**Context:** `BargainingProtocol.solve` and `compute_expected_surplus` access `agent.preferences` and `agent.endowment` directly. No path exists for believed types or observed types.

**Impact:** Bargaining always uses true private types (effectively full information), regardless of what agents believe or observe. Information asymmetry is irrelevant to exchange outcomes.

**VISION Alignment:** Fails "Institutional Visibility" - the information environment has no effect on bargaining.

**Decision:** See RESOLUTION-02 in PHASE1-RESOLUTIONS.md

**Status:** Pending resolution review

---

### FIND-03: Logging Blind to Beliefs

**Context:**
- `AgentSnapshot` logs `alpha` (true) but not `believed_alpha` or price beliefs
- `TargetEvaluation` logs `observed_alpha` (what InfoEnv reveals) but not `believed_alpha` (what agent thinks)
- No UI exists to show agent beliefs about other agents

**Impact:** Researchers cannot observe learning dynamics or belief convergence - a core Phase 1 goal.

**VISION Alignment:** Fails "Visualization Focus" - belief states are invisible.

**Decision:** See RESOLUTION-03 in PHASE1-RESOLUTIONS.md

**Status:** Pending resolution review

---

### FIND-04: Price Beliefs Unused

**Context:** `PriceBelief` is implemented and tested in `beliefs.py`, but `search.py` relies exclusively on `compute_nash_surplus` for target evaluation. No code path uses price beliefs.

**Impact:** BELIEF-004 requirement ("price expectations influence surplus calculation") is not met. Price belief is dead data.

**Decision:** See RESOLUTION-04 in PHASE1-RESOLUTIONS.md

**Status:** Pending resolution review

---

### FIND-05: `evaluate_targets` Ignores `bargaining_protocol` Parameter

**Context:** `search.py:105-204` computes expected surplus via `compute_nash_surplus` regardless of the `bargaining_protocol` parameter passed to the function.

**Impact:** Search behavior is not institution-specific. The parameter is misleading - it has no effect.

**VISION Alignment:** Reduces "Institutional Visibility" - protocol differences don't propagate to search decisions.

**Decision:** See RESOLUTION-05 in PHASE1-RESOLUTIONS.md

**Status:** Pending resolution review

---

### FIND-06: ADR and Code Diverge on Interfaces

**Context:** ADR-BELIEF-ARCHITECTURE.md (lines 92-156) expects `AgentType` in memory and update interfaces. Code stores `observed_alpha` only; `update_type_belief` takes a `float`.

**Impact:** Documentation and implementation disagree. Future work risks implementing against the wrong contract.

**Decision:** See RESOLUTION-06 in PHASE1-RESOLUTIONS.md

**Status:** Pending resolution review

---

### FIND-07: Integration Tests Incomplete

**Context:**
- `test_should_trade_uses_beliefs` (lines 743-773) computes `result_with_beliefs` but asserts nothing
- `test_beliefs_integration` (lines 1193-1197) is a no-op placeholder

**Impact:** Coverage gaps allow regressions in belief-driven behavior. Tests pass but verify nothing.

**Decision:** See RESOLUTION-07 in PHASE1-RESOLUTIONS.md

**Status:** Pending resolution review

---

### FIND-08: Factory Doesn't Enable Beliefs

**Context:** `create_simple_economy` creates agents using `create_agent` but never calls `enable_beliefs()`.

**Impact:** Even if wiring existed, the default simulation setup produces agents without belief capability.

**Decision:** See RESOLUTION-08 in PHASE1-RESOLUTIONS.md

**Status:** Pending resolution review

---

### FIND-09: PriceObservation Docstring Inconsistent

**Context:** `beliefs.py:68-73` states "units of y per unit of x" while the formula returns `x / y`.

**Impact:** Minor documentation confusion about price interpretation.

**Decision:** Fix docstring to match formula (or vice versa). Low priority.

**Status:** Pending

---

## Verification Plan

After resolutions are implemented:

1. **Integration Test:** Run simulation with belief-enabled agents starting from noisy priors. Verify logs show `believed_alpha` converging toward `true_alpha` over time.

2. **Bargaining Test:** Execute trade between agents with incorrect beliefs. Verify offer/negotiation reflects beliefs, even if actual utility uses true types.

3. **Visualization:** Run `visualization/app.py` in replay mode. Confirm belief metrics are visible and inspectable.

---

## Next Steps

1. Review PHASE1-RESOLUTIONS.md for resolution options
2. Make decisions on each resolution
3. Update this document with chosen approaches
4. Create PRD for Phase 1.5 (Integration Wiring) or incorporate into Phase 2
