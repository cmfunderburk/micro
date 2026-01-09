# Transaction Cost Model Design

**Date:** 2026-01-08
**Status:** Design approved, implementation pending

## Problem Statement

As agents converge toward Pareto efficiency, remaining gains from trade shrink toward zero. The last few trades may have utility gains like 1e-8, which:

1. Display as "+0.00" in the UI (misleading)
2. Are numerically fragile (floating point precision)
3. Don't reflect real-world behavior (transaction costs exist)

This was observed in the comparison trade history modal where all trades showed "+0.00" gains because agents had already reached near-efficient allocations.

## Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Approach** | Minimum surplus threshold | Theoretically grounded as implicit transaction costs (O&R) |
| **Location** | Institutional configuration | Alongside bargaining/matching protocols - it's another "rule of the game" |
| **Default ε** | `1e-4` | Filters clearly negligible trades while remaining permissive |
| **Search integration** | Yes | Filter targets where expected surplus < cost |
| **Extensibility** | ABC with simple default | Start with FixedTransactionCost, expand later |

## Architecture

```
┌─────────────────────────────────────┐
│       TransactionCostModel          │  ← ABC
│  ───────────────────────────────    │
│  + min_surplus(agent_a, agent_b)    │
│  + [future: cost(trade_details)]    │
└─────────────────────────────────────┘
              ▲
              │
    ┌─────────┴─────────────────────────────┐
    │                   │                   │
┌───┴───┐         ┌─────┴─────┐       ┌─────┴─────┐
│ Fixed │         │ Distance  │       │Relationship│
│  (ε)  │         │  Based    │       │   Based    │
└───────┘         └───────────┘       └────────────┘
 (Phase 1)            (Future)            (Future)
```

## Phase 1 Implementation

### New Module: `microecon/transaction_costs.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from microecon.agent import Agent

class TransactionCostModel(ABC):
    """
    Determines minimum viable surplus for trade execution.

    Transaction costs create a "wedge" that prevents trades with
    gains smaller than the cost. This is theoretically well-grounded
    (see O&R discussion of transaction costs in bargaining).

    Current implementation uses a simple fixed threshold. Future
    implementations may endogenize costs based on:
    - Distance between agents
    - Relationship history (first trade vs repeat)
    - Trade volume
    - Information asymmetry
    """

    @abstractmethod
    def min_surplus(self, agent_a: "Agent", agent_b: "Agent") -> float:
        """
        Return minimum total surplus required for trade to execute.

        If computed surplus < min_surplus, trade should not occur.
        """
        pass


@dataclass
class FixedTransactionCost(TransactionCostModel):
    """
    Constant minimum surplus threshold.

    Simple model where all trades face the same minimum viable
    surplus regardless of agents, distance, or history.

    Default epsilon of 1e-4 filters negligible trades while
    remaining permissive for meaningful exchanges.
    """
    epsilon: float = 1e-4

    def min_surplus(self, agent_a: "Agent", agent_b: "Agent") -> float:
        return self.epsilon


# Default for convenience
DEFAULT_TRANSACTION_COST_MODEL = FixedTransactionCost()
```

### Integration Points

**1. Simulation configuration:**
```python
# simulation.py
class Simulation:
    def __init__(
        self,
        ...,
        bargaining_protocol: BargainingProtocol,
        matching_protocol: MatchingProtocol,
        transaction_cost_model: TransactionCostModel | None = None,
    ):
        self.transaction_cost_model = transaction_cost_model or FixedTransactionCost()
```

**2. Bargaining protocol execution:**
```python
# bargaining.py - in execute() method
def execute(self, agent_a, agent_b, info_env, cost_model=None) -> TradeResult | None:
    # ... compute trade and surplus ...

    if cost_model is not None:
        min_surplus = cost_model.min_surplus(agent_a, agent_b)
        if total_surplus < min_surplus:
            return None  # Trade not viable

    # ... proceed with trade ...
```

**3. Search target evaluation:**
```python
# search.py - in target evaluation
def evaluate_target(self, agent, target, surplus_fn, cost_model=None) -> float:
    surplus = surplus_fn(agent, target)

    if cost_model is not None:
        min_surplus = cost_model.min_surplus(agent, target)
        if surplus < min_surplus:
            return 0.0  # Not worth pursuing

    return discount_by_distance(surplus, distance)
```

### Test Coverage

```python
# tests/test_transaction_costs.py

def test_fixed_cost_filters_small_surplus():
    """Trades with surplus < epsilon should not execute."""

def test_fixed_cost_allows_large_surplus():
    """Trades with surplus >= epsilon should execute normally."""

def test_search_respects_transaction_costs():
    """Targets with expected surplus < cost should be filtered."""

def test_default_epsilon_value():
    """Default epsilon should be 1e-4."""
```

## Future Extensions

### Distance-Based Costs
```python
@dataclass
class DistanceBasedCost(TransactionCostModel):
    """Cost increases with spatial distance between agents."""
    base: float = 1e-4
    per_unit_distance: float = 0.01

    def min_surplus(self, agent_a: Agent, agent_b: Agent) -> float:
        distance = compute_distance(agent_a.position, agent_b.position)
        return self.base + self.per_unit_distance * distance
```

### Relationship-Based Costs
```python
@dataclass
class RelationshipBasedCost(TransactionCostModel):
    """First trade with a partner is costly, repeat trades cheaper."""
    first_trade_cost: float = 0.1
    repeat_trade_cost: float = 1e-4

    def min_surplus(self, agent_a: Agent, agent_b: Agent) -> float:
        if have_traded_before(agent_a, agent_b):
            return self.repeat_trade_cost
        return self.first_trade_cost
```

### Search vs Exchange Costs

An important future consideration: search transaction costs and exchange transaction costs may differ.

- **Search costs**: Cost of evaluating/approaching a potential partner
- **Exchange costs**: Cost of executing the actual trade

For now, we use a single model for both. Future work may introduce:
```python
class DualCostModel:
    search_cost_model: TransactionCostModel
    exchange_cost_model: TransactionCostModel
```

## Open Questions

1. **Logging**: Should filtered trades (surplus < cost) be logged as events? Useful for analysis but adds noise.

2. **UI exposure**: Should transaction cost model be configurable in the frontend, or backend-only for now?

3. **Server integration**: The server's `SimulationConfig` will need a `transaction_cost_model` field or `min_surplus_threshold` parameter.

4. **Backward compatibility**: Existing simulations should continue to work with permissive defaults.

## Implementation Priority

This is a **medium priority** enhancement. The simulation works correctly without it, but the UI display issue ("+0.00" gains) creates confusion. Recommend implementing before the next major feature work.

## References

- O&R Ch 2-3: Discussion of transaction costs in bargaining theory
- Current codebase: `microecon/bargaining.py`, `microecon/search.py`, `microecon/simulation.py`
- Related: `docs/current/ROADMAP-DISCUSSION-2026-01-08.md` - tick model discussion
