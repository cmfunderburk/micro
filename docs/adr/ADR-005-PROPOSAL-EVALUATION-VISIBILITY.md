# ADR-005: Proposal Evaluation Visibility

**Status:** Accepted
**Date:** 2026-02-27
**Context:** A-107 (Proposal-evaluation visibility semantics decision)

## Decision

Execute-phase proposal evaluation uses **full visibility**: the target agent evaluates proposals using the proposer's true preferences, regardless of the configured `InformationEnvironment`.

## Context

During the Execute phase, when a non-mutual proposal arrives, the target agent must immediately decide whether to accept or reject. This decision is made in `simulation.py:_execute_actions()` via `decision_procedure.evaluate_proposal()`.

The `DecisionContext` is built with full agent visibility:

```python
visible_agents={a.id: a for a in self.agents}  # Full visibility for evaluation
```

The `evaluate_proposal` implementation (`decisions.py:459`) computes surplus using the proposer's true preferences via `compute_expected_surplus(agent, proposer)`.

## Rationale

1. **Institutional constraint, not agent perception**: Proposal evaluation is an institutional constraint (AGENT-ARCHITECTURE.md 7.9), not a perceptual act. The institution determines whether a trade is feasible and beneficial, using true parameters.

2. **Information environment governs search, not settlement**: The `InformationEnvironment` affects what agents *observe* during the Perceive phase (search target selection). Once two agents are adjacent and negotiating, the bargaining protocol operates on true preferences to compute the actual allocation.

3. **Consistency with bargaining**: The bargaining protocols (Nash, Rubinstein, etc.) already use true preferences to compute allocations. Having proposal *acceptance* use noisy preferences while *settlement* uses true preferences would create an inconsistency.

## Consequences

- Under noisy information, agents may search for suboptimal partners (based on noisy alpha), but once adjacent, they correctly evaluate whether trade is beneficial.
- This means information asymmetry affects *who* agents seek out, not *whether* they trade once matched.
- A future mechanism that uses local visibility for proposal evaluation would need to be added as a separate `DecisionProcedure` implementation, not by modifying the current one.

## Regression Test

`tests/test_simulation.py::TestProposalEvaluationVisibility` locks in this behavior.
