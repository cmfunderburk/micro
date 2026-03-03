# A-E3: Matching/Clearing Runtime Modularity — Design

**Date:** 2026-02-27
**Status:** Approved
**Scope:** A-200 through A-206 (7 items)
**Depends on:** A-E1 (complete), A-E2 (complete)

---

## Context

The simulation's `_execute_actions()` method (simulation.py:316-549) is a monolith handling four concerns: mutual proposal detection, non-mutual evaluation, fallback execution, and movement execution. AGENT-ARCHITECTURE.md §6.4 identifies this as the major modularity gap — matching/clearing logic is embedded, preventing institutional comparison.

This epic extracts matching into a swappable `MatchingProtocol` interface, preserves current behavior as the default implementation, and adds a centralized clearing stub to prove the interface works.

---

## Protocol Interface

```python
class MatchingProtocol(Protocol):
    def resolve(
        self,
        propose_actions: dict[str, ProposeAction],
        agents: dict[str, Agent],
        positions: dict[str, Position],
        decision_procedure: DecisionProcedure,
        bargaining_protocol: BargainingProtocol,
    ) -> MatchResult:
        """Resolve all proposals for this tick.

        Returns which proposals become trades, which are rejected,
        and which are implicitly non-selected.
        """
        ...
```

```python
@dataclass(frozen=True)
class TradeOutcome:
    proposer_id: str
    target_id: str

@dataclass(frozen=True)
class Rejection:
    proposer_id: str
    target_id: str
    cooldown_ticks: int

@dataclass(frozen=True)
class MatchResult:
    trades: tuple[TradeOutcome, ...]
    rejections: tuple[Rejection, ...]
    non_selections: tuple[str, ...]  # proposer_ids with implicit failure
```

---

## Extraction Boundary

| Current _execute_actions Step | Destination | Rationale |
|---|---|---|
| Step 1: Mutual proposal detection (353-410) | `MatchingProtocol.resolve()` | Matching concern |
| Step 2: Non-mutual evaluation (412-496) | `MatchingProtocol.resolve()` | Matching concern |
| Step 3: Fallback execution (498-525) | Stays in `Simulation` | Movement concern |
| Step 4: Movement execution (527-549) | Stays in `Simulation` | Movement concern |

Trade execution (`_execute_trade()`) stays in `Simulation` — the protocol decides *who* trades, the simulation handles *executing* the trade.

Interaction state management:
- Cooldown *creation*: returned by `MatchResult.rejections` (protocol decides)
- Cooldown *application*: stays in `Simulation` (state mutation)
- State transitions (AVAILABLE/NEGOTIATING): stays in `Simulation`

---

## Implementations

### BilateralProposalMatching (default)

Extracts current behavior exactly:
1. Detect mutual proposals (frozenset pairs)
2. Validate adjacency (Chebyshev distance <= 1) for mutual pairs
3. Non-mutual: group by target, evaluate acceptance via `decision_procedure.evaluate_proposal()`
4. Track responded targets to prevent double-selection
5. Return `MatchResult` with trades, explicit rejections, implicit non-selections

Zero behavioral change. Existing tests stay green.

### CentralizedClearingMatching (stub alternative)

Demonstrates interface swappability:
1. Collect all proposals
2. For each potential pair, compute bilateral surplus via `bargaining_protocol.compute_expected_surplus()`
3. Greedily assign matches by descending surplus (each agent matched at most once)
4. All unmatched proposers are non-selections (no cooldowns — centralized clearing doesn't reject)

Intentionally simple — welfare-maximizing greedy matcher, not full Gale-Shapley complexity.

---

## File Layout

```
microecon/matching.py                — MatchingProtocol, MatchResult, BilateralProposalMatching, CentralizedClearingMatching
microecon/simulation.py              — _execute_actions() calls protocol.resolve()
docs/adr/ADR-006-MATCHING.md         — Design rationale and interface contract
tests/test_matching.py               — Unit tests for both protocols
tests/test_matching_conformance.py   — Protocol conformance tests (parametrized over all implementations)
```

---

## Testing Strategy

Three layers:

1. **Conformance tests** (`test_matching_conformance.py`): Protocol-agnostic properties any `MatchingProtocol` must satisfy — no agent matched twice, only adjacent pairs matched (for spatial protocols), valid `MatchResult` structure. Parametrized over all registered protocols.

2. **Behavioral tests** (`test_matching.py`): Protocol-specific. `BilateralProposalMatching` produces identical outcomes to current monolith. `CentralizedClearingMatching` maximizes welfare among available pairs.

3. **Regression**: Full existing test suite passes unchanged after extraction (default protocol preserves behavior exactly).

Performance baseline: benchmark recording tick execution time for 20-agent/20x20/100-tick simulation, stored as a reference number (documented, not a hard gate).

---

## Sequencing

```
A-200: Design ADR
  → A-201: Interface extraction (MatchingProtocol, MatchResult types)
    → A-202: Interaction state-transition extraction (proposal lifecycle behind protocol)
      → A-203: Default bilateral adapter (extract current behavior into BilateralProposalMatching)
        → A-204: Simulation loop refactor (wire protocol into _execute_actions)
          → A-205: Conformance tests and benchmark baseline
            → A-206: Centralized clearing stub
```

Linear dependency chain. Each step is independently testable and committable.
