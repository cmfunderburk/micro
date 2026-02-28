# ADR-006: Matching/Clearing Protocol Abstraction

**Status:** Accepted
**Date:** 2026-02-27
**Context:** A-200 (Matching/clearing runtime modularity)

## Decision

Extract matching/clearing logic from `Simulation._execute_actions()` into a swappable `MatchingProtocol` interface. The protocol receives proposals and returns match decisions. Trade execution and state mutation remain in the simulation.

## Context

`_execute_actions()` (simulation.py:316-549) is a monolith handling four concerns:
1. Mutual proposal detection (lines 353-410)
2. Non-mutual proposal evaluation (lines 412-496)
3. Fallback execution (lines 498-525)
4. Movement execution (lines 527-549)

Concerns 1-2 are matching logic. Concerns 3-4 are post-matching execution. The matching logic is tightly coupled to the simulation, preventing institutional comparison (e.g., bilateral vs centralized clearing).

## Interface

```python
class MatchingProtocol(ABC):
    @abstractmethod
    def resolve(
        self,
        propose_actions: dict[str, ProposeAction],
        agents: dict[str, Agent],
        positions: dict[str, Position],
        decision_procedure: DecisionProcedure,
        bargaining_protocol: BargainingProtocol,
    ) -> MatchResult: ...

@dataclass(frozen=True)
class MatchResult:
    trades: tuple[TradeOutcome, ...]
    rejections: tuple[Rejection, ...]
    non_selections: tuple[str, ...]
```

## Extraction Boundary

| Concern | Location |
|---|---|
| Who matches with whom | `MatchingProtocol.resolve()` |
| Trade settlement | `Simulation._execute_trade()` |
| Cooldown application | `Simulation._execute_actions()` |
| Fallback execution | `Simulation._execute_actions()` |
| Movement | `Simulation._execute_actions()` |

## Implementations

1. **BilateralProposalMatching** (default): Extracts current behavior. Mutual detection, sequential evaluation, first-responder conflict resolution. Zero behavioral change.

2. **CentralizedClearingMatching** (stub): Collects proposals, computes bilateral surplus, greedily assigns welfare-maximizing matches. No rejections (unmatched = non-selected).

## Invariants

- No agent matched twice per tick
- Only adjacent pairs matched (for spatial protocols)
- MatchResult is pure data — no side effects
- Protocol does not mutate agents or grid state

## Determinism

Protocol resolution must be deterministic given the same inputs. Tie-breaking uses sorted agent IDs (lexicographic).

## Consequences

- Matching is swappable without rewriting the simulation loop
- Current behavior preserved under default protocol
- New protocols can implement alternative matching algorithms
- Performance: one additional function call per tick (negligible)
