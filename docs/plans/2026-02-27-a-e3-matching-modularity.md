# A-E3: Matching/Clearing Runtime Modularity — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract matching/clearing logic from the monolithic `_execute_actions()` into a swappable `MatchingProtocol` interface, preserving current behavior as the default implementation and adding a centralized clearing stub.

**Architecture:** A `MatchingProtocol` receives all proposals for a tick and returns a `MatchResult` (who trades, who is rejected, who is non-selected). The simulation loop calls the protocol for matching decisions, then handles trade execution, fallbacks, and movement itself. Two implementations: `BilateralProposalMatching` (extracts current behavior exactly) and `CentralizedClearingMatching` (greedy welfare-maximizing stub).

**Tech Stack:** Python dataclasses (protocol types), ABC (protocol interface), pytest (conformance/behavioral tests)

**Decisions (locked):**
1. MatchingProtocol returns match decisions, does NOT execute trades or mutate state
2. Trade execution, fallbacks, movement stay in Simulation
3. Cooldown creation is returned in MatchResult; application stays in Simulation
4. BilateralProposalMatching preserves current behavior exactly (zero behavioral change)
5. CentralizedClearingMatching is a greedy welfare-maximizer (not Gale-Shapley)

---

### Task 1: Write ADR-006-MATCHING design document (A-200)

**Files:**
- Create: `docs/adr/ADR-006-MATCHING.md`

**Step 1: Write the ADR**

```markdown
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
```

**Step 2: Commit**

```bash
git add docs/adr/ADR-006-MATCHING.md
git commit -m "docs(adr): add ADR-006 matching protocol abstraction (A-200)"
```

---

### Task 2: Create MatchingProtocol interface and result types (A-201)

**Files:**
- Create: `microecon/matching.py`
- Test: `tests/test_matching.py`

**Step 1: Write the failing tests**

Create `tests/test_matching.py`:

```python
"""Tests for matching protocol types and interface (A-201)."""

import pytest

from microecon.matching import (
    MatchingProtocol,
    MatchResult,
    TradeOutcome,
    Rejection,
)


class TestMatchResultTypes:
    """Test MatchResult and its component types."""

    def test_trade_outcome_is_frozen(self):
        outcome = TradeOutcome(proposer_id="a1", target_id="a2")
        with pytest.raises(AttributeError):
            outcome.proposer_id = "changed"

    def test_rejection_is_frozen(self):
        rejection = Rejection(proposer_id="a1", target_id="a2", cooldown_ticks=3)
        with pytest.raises(AttributeError):
            rejection.proposer_id = "changed"

    def test_match_result_is_frozen(self):
        result = MatchResult(
            trades=(TradeOutcome("a1", "a2"),),
            rejections=(),
            non_selections=(),
        )
        with pytest.raises(AttributeError):
            result.trades = ()

    def test_match_result_empty(self):
        result = MatchResult(trades=(), rejections=(), non_selections=())
        assert len(result.trades) == 0
        assert len(result.rejections) == 0
        assert len(result.non_selections) == 0

    def test_match_result_with_all_outcomes(self):
        result = MatchResult(
            trades=(TradeOutcome("a1", "a2"),),
            rejections=(Rejection("a3", "a4", 3),),
            non_selections=("a5",),
        )
        assert len(result.trades) == 1
        assert result.trades[0].proposer_id == "a1"
        assert result.rejections[0].cooldown_ticks == 3
        assert result.non_selections[0] == "a5"

    def test_matching_protocol_is_abstract(self):
        with pytest.raises(TypeError):
            MatchingProtocol()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_matching.py -v`
Expected: FAIL (ImportError — module doesn't exist yet)

**Step 3: Write minimal implementation**

Create `microecon/matching.py`:

```python
"""
Matching/clearing protocol abstraction.

Defines the interface for how agents are matched for trade each tick.
The protocol receives proposals and returns match decisions — it does NOT
execute trades or mutate agent state.

Implementations:
- BilateralProposalMatching: Current behavior (mutual detection + sequential evaluation)
- CentralizedClearingMatching: Welfare-maximizing greedy clearing

Reference: ADR-006-MATCHING.md
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from microecon.actions import ProposeAction
    from microecon.agent import Agent
    from microecon.bargaining import BargainingProtocol
    from microecon.decisions import DecisionProcedure
    from microecon.grid import Position


@dataclass(frozen=True)
class TradeOutcome:
    """A matched pair that should trade."""
    proposer_id: str
    target_id: str


@dataclass(frozen=True)
class Rejection:
    """An explicit rejection (triggers cooldown for proposer)."""
    proposer_id: str
    target_id: str
    cooldown_ticks: int


@dataclass(frozen=True)
class MatchResult:
    """Result of matching protocol resolution for one tick.

    Contains three disjoint sets covering all proposers:
    - trades: matched pairs that should execute trades
    - rejections: explicit rejections (proposer gets cooldown)
    - non_selections: implicit failures (no cooldown, e.g. target chose someone else)
    """
    trades: tuple[TradeOutcome, ...]
    rejections: tuple[Rejection, ...]
    non_selections: tuple[str, ...]  # proposer_ids


class MatchingProtocol(ABC):
    """Abstract base for matching/clearing protocols.

    A matching protocol determines which proposals become trades each tick.
    It receives all proposals and agent state, and returns a pure-data
    MatchResult. It does NOT execute trades or mutate state.

    Implementations must be deterministic given the same inputs.
    Tie-breaking uses sorted agent IDs (lexicographic).
    """

    @abstractmethod
    def resolve(
        self,
        propose_actions: dict[str, "ProposeAction"],
        agents: dict[str, "Agent"],
        positions: dict[str, "Position"],
        decision_procedure: "DecisionProcedure",
        bargaining_protocol: "BargainingProtocol",
    ) -> MatchResult:
        """Resolve all proposals for this tick.

        Args:
            propose_actions: Map of proposer_id -> ProposeAction
            agents: Map of agent_id -> Agent (all agents, not just proposers)
            positions: Map of agent_id -> Position (current positions)
            decision_procedure: For evaluating proposal acceptance
            bargaining_protocol: For computing surplus

        Returns:
            MatchResult with trades, rejections, and non-selections
        """
        ...
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_matching.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add microecon/matching.py tests/test_matching.py
git commit -m "feat(matching): add MatchingProtocol interface and result types (A-201)"
```

---

### Task 3: Implement BilateralProposalMatching (A-202, A-203)

This task extracts Steps 1-2 of `_execute_actions()` into `BilateralProposalMatching.resolve()`.

**Files:**
- Modify: `microecon/matching.py`
- Modify: `tests/test_matching.py`

**Step 1: Write the failing tests**

Add to `tests/test_matching.py`:

```python
from microecon.matching import BilateralProposalMatching
from microecon.actions import ProposeAction
from microecon.agent import create_agent
from microecon.grid import Grid, Position
from microecon.bargaining import NashBargainingProtocol
from microecon.decisions import RationalDecisionProcedure, DecisionContext
from microecon.actions import ActionContext


def _make_agent(agent_id, alpha=0.5, endowment_x=10.0, endowment_y=2.0):
    """Create a test agent."""
    return create_agent(
        agent_id=agent_id,
        alpha=alpha,
        endowment_x=endowment_x,
        endowment_y=endowment_y,
    )


def _setup_pair(grid, agent_a, agent_b, pos_a, pos_b):
    """Place two agents on a grid and return positions dict."""
    grid.place_agent(agent_a, pos_a)
    grid.place_agent(agent_b, pos_b)
    return {agent_a.id: pos_a, agent_b.id: pos_b}


class TestBilateralProposalMatching:
    """Tests for default bilateral proposal matching protocol."""

    def test_mutual_proposal_creates_trade(self):
        """Two agents proposing to each other -> trade."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.3)
        a2 = _make_agent("a2", alpha=0.7)
        pos = _setup_pair(grid, a1, a2, Position(0, 0), Position(0, 1))

        proposals = {
            "a1": ProposeAction(target_id="a2"),
            "a2": ProposeAction(target_id="a1"),
        }
        agents = {"a1": a1, "a2": a2}

        protocol = BilateralProposalMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )

        assert len(result.trades) == 1
        pair = {result.trades[0].proposer_id, result.trades[0].target_id}
        assert pair == {"a1", "a2"}
        assert len(result.rejections) == 0
        assert len(result.non_selections) == 0

    def test_mutual_proposal_not_adjacent_no_trade(self):
        """Mutual proposals but agents too far apart -> no trade."""
        grid = Grid(10)
        a1 = _make_agent("a1", alpha=0.3)
        a2 = _make_agent("a2", alpha=0.7)
        pos = _setup_pair(grid, a1, a2, Position(0, 0), Position(5, 5))

        proposals = {
            "a1": ProposeAction(target_id="a2"),
            "a2": ProposeAction(target_id="a1"),
        }
        agents = {"a1": a1, "a2": a2}

        protocol = BilateralProposalMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        assert len(result.trades) == 0

    def test_accepted_proposal(self):
        """Non-mutual proposal where target accepts -> trade."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.2)
        a2 = _make_agent("a2", alpha=0.8)
        pos = _setup_pair(grid, a1, a2, Position(0, 0), Position(0, 1))

        # Set opportunity cost low so acceptance is likely
        a2.opportunity_cost = 0.0

        proposals = {"a1": ProposeAction(target_id="a2")}
        agents = {"a1": a1, "a2": a2}

        protocol = BilateralProposalMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        assert len(result.trades) == 1
        assert result.trades[0].proposer_id == "a1"
        assert result.trades[0].target_id == "a2"

    def test_rejected_proposal_creates_rejection(self):
        """Non-mutual proposal where target rejects -> rejection with cooldown."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.45)
        a2 = _make_agent("a2", alpha=0.55)
        pos = _setup_pair(grid, a1, a2, Position(0, 0), Position(0, 1))

        # Set opportunity cost very high so target rejects
        a2.opportunity_cost = 999.0

        proposals = {"a1": ProposeAction(target_id="a2")}
        agents = {"a1": a1, "a2": a2}

        protocol = BilateralProposalMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        assert len(result.trades) == 0
        assert len(result.rejections) == 1
        assert result.rejections[0].proposer_id == "a1"
        assert result.rejections[0].target_id == "a2"
        assert result.rejections[0].cooldown_ticks == 3

    def test_multiple_proposals_to_same_target(self):
        """Two proposers to same target -> one trade, one non-selection."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.2)
        a2 = _make_agent("a2", alpha=0.8)
        a3 = _make_agent("a3", alpha=0.3)
        grid.place_agent(a1, Position(0, 0))
        grid.place_agent(a2, Position(0, 1))
        grid.place_agent(a3, Position(1, 1))
        pos = {"a1": Position(0, 0), "a2": Position(0, 1), "a3": Position(1, 1)}

        a2.opportunity_cost = 0.0

        proposals = {
            "a1": ProposeAction(target_id="a2"),
            "a3": ProposeAction(target_id="a2"),
        }
        agents = {"a1": a1, "a2": a2, "a3": a3}

        protocol = BilateralProposalMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        # One should trade, the other should be non-selected
        assert len(result.trades) == 1
        assert len(result.non_selections) == 1

    def test_no_agent_matched_twice(self):
        """An agent that already traded cannot be matched again."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.2)
        a2 = _make_agent("a2", alpha=0.8)
        a3 = _make_agent("a3", alpha=0.3)
        grid.place_agent(a1, Position(0, 0))
        grid.place_agent(a2, Position(0, 1))
        grid.place_agent(a3, Position(1, 0))
        pos = {"a1": Position(0, 0), "a2": Position(0, 1), "a3": Position(1, 0)}

        a2.opportunity_cost = 0.0
        a1.opportunity_cost = 0.0

        # a1 and a2 mutual, a3 proposes to a1
        proposals = {
            "a1": ProposeAction(target_id="a2"),
            "a2": ProposeAction(target_id="a1"),
            "a3": ProposeAction(target_id="a1"),
        }
        agents = {"a1": a1, "a2": a2, "a3": a3}

        protocol = BilateralProposalMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        # a1-a2 trade (mutual), a3 non-selected (a1 already traded)
        assert len(result.trades) == 1
        traded_ids = {result.trades[0].proposer_id, result.trades[0].target_id}
        assert traded_ids == {"a1", "a2"}
        assert "a3" in result.non_selections

    def test_empty_proposals(self):
        """No proposals -> empty result."""
        protocol = BilateralProposalMatching()
        result = protocol.resolve({}, {}, {}, RationalDecisionProcedure(), NashBargainingProtocol())
        assert result == MatchResult(trades=(), rejections=(), non_selections=())
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_matching.py::TestBilateralProposalMatching -v`
Expected: FAIL (ImportError — BilateralProposalMatching doesn't exist)

**Step 3: Write the implementation**

Add to `microecon/matching.py`:

```python
class BilateralProposalMatching(MatchingProtocol):
    """Default bilateral proposal matching — extracts current _execute_actions behavior.

    Resolution order:
    1. Detect mutual proposals (A→B and B→A) — fast-track to trade
    2. Evaluate non-mutual proposals — target accepts/rejects based on opportunity cost
    3. Handle conflicts — first-responder advantage for same target

    This is a pure extraction of simulation.py:353-496 into a protocol.
    """

    def resolve(
        self,
        propose_actions: dict[str, "ProposeAction"],
        agents: dict[str, "Agent"],
        positions: dict[str, "Position"],
        decision_procedure: "DecisionProcedure",
        bargaining_protocol: "BargainingProtocol",
    ) -> MatchResult:
        if not propose_actions:
            return MatchResult(trades=(), rejections=(), non_selections=())

        trades: list[TradeOutcome] = []
        rejections: list[Rejection] = []
        non_selections: list[str] = []
        traded_this_tick: set[str] = set()

        # Step 1: Detect and resolve mutual proposals
        mutual_proposals: set[frozenset[str]] = set()
        for proposer_id, action in propose_actions.items():
            target_action = propose_actions.get(action.target_id)
            if target_action and target_action.target_id == proposer_id:
                mutual_proposals.add(frozenset([proposer_id, action.target_id]))

        processed_mutual: set[str] = set()
        for pair in mutual_proposals:
            pair_list = sorted(pair)
            if pair_list[0] in processed_mutual or pair_list[1] in processed_mutual:
                continue

            a_id, b_id = pair_list
            if a_id not in agents or b_id not in agents:
                continue

            pos_a = positions.get(a_id)
            pos_b = positions.get(b_id)
            if pos_a is None or pos_b is None:
                continue
            if pos_a.chebyshev_distance_to(pos_b) > 1:
                continue

            # Mutual match: use sorted order for deterministic proposer assignment
            trades.append(TradeOutcome(proposer_id=a_id, target_id=b_id))
            processed_mutual.add(a_id)
            processed_mutual.add(b_id)
            traded_this_tick.add(a_id)
            traded_this_tick.add(b_id)

        # Step 2: Evaluate non-mutual proposals
        # Build decision context for proposal evaluation
        from microecon.actions import ActionContext
        from microecon.decisions import DecisionContext

        action_context = ActionContext(
            current_tick=0,
            agent_positions=positions,
            adjacent_agents={},
            co_located_agents={},
        )
        decision_context = DecisionContext(
            action_context=action_context,
            visible_agents=agents,  # Full visibility for evaluation (ADR-005)
            bargaining_protocol=bargaining_protocol,
            agent_positions=positions,
        )

        responded_targets: set[str] = set()

        for proposer_id, action in propose_actions.items():
            if proposer_id in processed_mutual:
                continue
            if proposer_id in traded_this_tick:
                continue

            target_id = action.target_id
            proposer = agents.get(proposer_id)
            target = agents.get(target_id)
            if proposer is None or target is None:
                continue

            # Target already responded to another proposal
            if target_id in responded_targets:
                non_selections.append(proposer_id)
                continue

            # Target already traded (from mutual proposal)
            if target_id in traded_this_tick:
                non_selections.append(proposer_id)
                continue

            # Check adjacency
            proposer_pos = positions.get(proposer_id)
            target_pos = positions.get(target_id)
            if proposer_pos is None or target_pos is None:
                continue
            if proposer_pos.chebyshev_distance_to(target_pos) > 1:
                continue

            # Target evaluates proposal
            accept = decision_procedure.evaluate_proposal(
                target, proposer, decision_context
            )
            responded_targets.add(target_id)

            if accept:
                trades.append(TradeOutcome(proposer_id=proposer_id, target_id=target_id))
                traded_this_tick.add(proposer_id)
                traded_this_tick.add(target_id)
            else:
                rejections.append(Rejection(
                    proposer_id=proposer_id,
                    target_id=target_id,
                    cooldown_ticks=3,
                ))

        return MatchResult(
            trades=tuple(trades),
            rejections=tuple(rejections),
            non_selections=tuple(non_selections),
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_matching.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add microecon/matching.py tests/test_matching.py
git commit -m "feat(matching): implement BilateralProposalMatching (A-202, A-203)"
```

---

### Task 4: Wire MatchingProtocol into Simulation (A-204)

This is the critical refactor — replace the monolithic steps 1-2 in `_execute_actions()` with a call to `matching_protocol.resolve()`.

**Files:**
- Modify: `microecon/simulation.py`
- Modify: `microecon/matching.py` (import in simulation)

**Step 1: Run the full test suite before refactoring**

Run: `uv run pytest -q`
Record the baseline: note test count and pass rate.

**Step 2: Add `matching_protocol` to Simulation**

In `microecon/simulation.py`, add to imports (after existing imports):

```python
from microecon.matching import (
    BilateralProposalMatching,
    MatchingProtocol,
    MatchResult,
)
```

Add to the `Simulation` dataclass fields (after `decision_procedure`):

```python
    matching_protocol: MatchingProtocol = field(default_factory=BilateralProposalMatching)
```

**Step 3: Refactor `_execute_actions()` to use the protocol**

Replace the body of `_execute_actions()` (lines 335-549) with:

```python
        tick_trades: list[TradeEvent] = []

        # Separate actions by type
        move_actions: dict[str, MoveAction] = {}
        propose_actions: dict[str, ProposeAction] = {}

        for agent_id, action in agent_actions.items():
            if isinstance(action, MoveAction):
                move_actions[agent_id] = action
            elif isinstance(action, ProposeAction):
                propose_actions[agent_id] = action

        # Track agents that traded this tick
        traded_this_tick: set[str] = set()

        # =====================================================================
        # Step 1-2: Matching protocol resolves proposals
        # =====================================================================
        match_result = self.matching_protocol.resolve(
            propose_actions=propose_actions,
            agents=self._agents_by_id,
            positions={a.id: self.grid.get_position(a) for a in self.agents
                       if self.grid.get_position(a) is not None},
            decision_procedure=self.decision_procedure,
            bargaining_protocol=self.bargaining_protocol,
        )

        # Execute matched trades
        for trade_outcome in match_result.trades:
            proposer = self._agents_by_id.get(trade_outcome.proposer_id)
            target = self._agents_by_id.get(trade_outcome.target_id)
            if proposer is None or target is None:
                continue

            exchange_id = propose_actions.get(trade_outcome.proposer_id)
            if exchange_id is not None:
                exchange_id = exchange_id.exchange_id
            else:
                exchange_id = propose_actions.get(trade_outcome.target_id, ProposeAction(target_id="")).exchange_id

            proposer.interaction_state.enter_negotiating(trade_outcome.target_id, self.tick)
            target.interaction_state.enter_negotiating(trade_outcome.proposer_id, self.tick)

            trade_event = self._execute_trade(proposer, target, exchange_id)
            if trade_event:
                tick_trades.append(trade_event)

            proposer.interaction_state.enter_available()
            target.interaction_state.enter_available()

            traded_this_tick.add(trade_outcome.proposer_id)
            traded_this_tick.add(trade_outcome.target_id)

        # Apply cooldowns from rejections
        for rejection in match_result.rejections:
            proposer = self._agents_by_id.get(rejection.proposer_id)
            if proposer is not None:
                proposer.interaction_state.enter_available(
                    add_cooldown_for=rejection.target_id,
                    cooldown_duration=rejection.cooldown_ticks,
                )

        # Build set of all failed proposers for fallback execution
        rejected_proposers = {r.proposer_id for r in match_result.rejections}
        non_selected_proposers = set(match_result.non_selections)
        all_failed_proposers = rejected_proposers | non_selected_proposers

        # =====================================================================
        # Step 3: Execute fallback actions for failed proposals
        # =====================================================================
        for proposer_id in all_failed_proposers:
            proposer = self._agents_by_id.get(proposer_id)
            if proposer is None:
                continue

            action = propose_actions.get(proposer_id)
            if action is None:
                continue

            fallback = action.fallback
            if fallback is None:
                continue

            if isinstance(fallback, MoveAction):
                if proposer.interaction_state.is_available():
                    self.grid.move_toward(
                        proposer,
                        fallback.target_position,
                        steps=proposer.movement_budget
                    )

        # =====================================================================
        # Step 4: Execute movement actions
        # =====================================================================
        for agent_id, action in move_actions.items():
            if agent_id in traded_this_tick:
                continue
            if agent_id in all_failed_proposers:
                continue

            agent = self._agents_by_id.get(agent_id)
            if agent is None:
                continue
            if not agent.interaction_state.is_available():
                continue

            self.grid.move_toward(agent, action.target_position, steps=agent.movement_budget)

        return tick_trades
```

**Step 4: Run the full test suite**

Run: `uv run pytest -q`
Expected: Same pass count as baseline. Zero regressions.

**Step 5: Run determinism tests specifically**

Run: `uv run pytest -m determinism -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add microecon/simulation.py
git commit -m "refactor(simulation): wire MatchingProtocol into _execute_actions (A-204)"
```

---

### Task 5: Thread `matching_protocol` through `create_simple_economy` and server

**Files:**
- Modify: `microecon/simulation.py` (create_simple_economy signature)
- Modify: `server/simulation_manager.py` (pass matching_protocol to Simulation)

**Step 1: Add `matching_protocol` parameter to `create_simple_economy`**

In `microecon/simulation.py`, modify `create_simple_economy` signature to add `matching_protocol` parameter:

```python
def create_simple_economy(
    n_agents: int,
    grid_size: int = 10,
    perception_radius: float = 7.0,
    discount_factor: float = 0.95,
    seed: Optional[int] = None,
    bargaining_protocol: Optional[BargainingProtocol] = None,
    decision_procedure: Optional[DecisionProcedure] = None,
    matching_protocol: Optional[MatchingProtocol] = None,
    use_beliefs: bool = False,
    info_env: Optional[InformationEnvironment] = None,
) -> Simulation:
```

And in the `Simulation()` construction inside this function, add:

```python
    sim = Simulation(
        grid=Grid(grid_size),
        info_env=info_env or FullInformation(),
        bargaining_protocol=bargaining_protocol or NashBargainingProtocol(),
        decision_procedure=decision_procedure or RationalDecisionProcedure(),
        matching_protocol=matching_protocol or BilateralProposalMatching(),
        _rng=rng,
    )
```

**Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: ALL PASS (matching_protocol has default, so no callers break)

**Step 3: Commit**

```bash
git add microecon/simulation.py
git commit -m "feat(simulation): thread matching_protocol through create_simple_economy (A-204)"
```

---

### Task 6: Add matching conformance tests (A-205)

**Files:**
- Create: `tests/test_matching_conformance.py`

**Step 1: Write the conformance tests**

Create `tests/test_matching_conformance.py`:

```python
"""Matching protocol conformance tests (A-205).

Any MatchingProtocol implementation must pass these tests.
Tests are parametrized over all registered protocol implementations.
"""

import pytest

from microecon.matching import (
    BilateralProposalMatching,
    MatchingProtocol,
    MatchResult,
)
from microecon.actions import ProposeAction
from microecon.agent import create_agent
from microecon.grid import Grid, Position
from microecon.bargaining import NashBargainingProtocol
from microecon.decisions import RationalDecisionProcedure

pytestmark = pytest.mark.contract

ALL_PROTOCOLS = [
    BilateralProposalMatching(),
]


def _make_agent(agent_id, alpha=0.5, endowment_x=10.0, endowment_y=2.0):
    return create_agent(
        agent_id=agent_id,
        alpha=alpha,
        endowment_x=endowment_x,
        endowment_y=endowment_y,
    )


class TestMatchingConformance:
    """Protocol-agnostic conformance tests."""

    @pytest.fixture(params=ALL_PROTOCOLS, ids=lambda p: type(p).__name__)
    def protocol(self, request):
        return request.param

    def test_empty_proposals_returns_empty_result(self, protocol):
        result = protocol.resolve({}, {}, {}, RationalDecisionProcedure(), NashBargainingProtocol())
        assert result.trades == ()
        assert result.rejections == ()
        assert result.non_selections == ()

    def test_no_agent_matched_twice(self, protocol):
        """An agent must not appear in more than one trade."""
        grid = Grid(10)
        agents = {}
        positions = {}
        for i in range(6):
            a = _make_agent(f"a{i}", alpha=0.1 + 0.15 * i)
            grid.place_agent(a, Position(i, 0))
            agents[a.id] = a
            positions[a.id] = Position(i, 0)
            a.opportunity_cost = 0.0

        # Everyone proposes to a0 (adjacent to a1 only)
        proposals = {f"a{i}": ProposeAction(target_id="a0") for i in range(1, 6)}

        result = protocol.resolve(
            proposals, agents, positions,
            RationalDecisionProcedure(), NashBargainingProtocol(),
        )

        # Collect all agent IDs that appear in trades
        traded_ids = []
        for t in result.trades:
            traded_ids.append(t.proposer_id)
            traded_ids.append(t.target_id)
        # No duplicates
        assert len(traded_ids) == len(set(traded_ids)), \
            f"Agent matched twice: {traded_ids}"

    def test_match_result_covers_all_proposers(self, protocol):
        """Every proposer must appear in exactly one of: trades, rejections, non_selections,
        or be part of a mutual proposal (also in trades)."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.2)
        a2 = _make_agent("a2", alpha=0.8)
        a3 = _make_agent("a3", alpha=0.5)
        for a, p in [(a1, Position(0, 0)), (a2, Position(0, 1)), (a3, Position(0, 2))]:
            grid.place_agent(a, p)
        agents = {"a1": a1, "a2": a2, "a3": a3}
        positions = {"a1": Position(0, 0), "a2": Position(0, 1), "a3": Position(0, 2)}
        a2.opportunity_cost = 0.0

        proposals = {
            "a1": ProposeAction(target_id="a2"),
            "a3": ProposeAction(target_id="a2"),
        }

        result = protocol.resolve(
            proposals, agents, positions,
            RationalDecisionProcedure(), NashBargainingProtocol(),
        )

        # All proposer_ids should be accounted for
        accounted = set()
        for t in result.trades:
            accounted.add(t.proposer_id)
            # For mutual proposals, target is also a proposer
            if t.target_id in proposals:
                accounted.add(t.target_id)
        for r in result.rejections:
            accounted.add(r.proposer_id)
        accounted.update(result.non_selections)

        assert accounted == set(proposals.keys()), \
            f"Proposers not accounted for: {set(proposals.keys()) - accounted}"

    def test_result_is_frozen(self, protocol):
        """MatchResult must be immutable."""
        result = protocol.resolve({}, {}, {}, RationalDecisionProcedure(), NashBargainingProtocol())
        with pytest.raises(AttributeError):
            result.trades = ()

    def test_deterministic_resolution(self, protocol):
        """Same inputs must produce same outputs."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.2)
        a2 = _make_agent("a2", alpha=0.8)
        for a, p in [(a1, Position(0, 0)), (a2, Position(0, 1))]:
            grid.place_agent(a, p)
        agents = {"a1": a1, "a2": a2}
        positions = {"a1": Position(0, 0), "a2": Position(0, 1)}
        a2.opportunity_cost = 0.0

        proposals = {"a1": ProposeAction(target_id="a2")}

        result1 = protocol.resolve(
            proposals, agents, positions,
            RationalDecisionProcedure(), NashBargainingProtocol(),
        )
        result2 = protocol.resolve(
            proposals, agents, positions,
            RationalDecisionProcedure(), NashBargainingProtocol(),
        )
        assert result1 == result2
```

**Step 2: Run the conformance tests**

Run: `uv run pytest tests/test_matching_conformance.py -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/test_matching_conformance.py
git commit -m "test(matching): add protocol conformance tests (A-205)"
```

---

### Task 7: Add performance benchmark baseline (A-205)

**Files:**
- Modify: `tests/test_matching_conformance.py`

**Step 1: Add benchmark test**

Add to `tests/test_matching_conformance.py`:

```python
import time

from microecon.simulation import create_simple_economy
from microecon.matching import BilateralProposalMatching


class TestMatchingPerformance:
    """Performance baseline for matching protocols.

    Not a hard gate — records reference numbers for regression monitoring.
    """

    def test_bilateral_20_agents_100_ticks(self):
        """Baseline: 20 agents, 20x20 grid, 100 ticks."""
        sim = create_simple_economy(
            n_agents=20, grid_size=20, seed=42,
            matching_protocol=BilateralProposalMatching(),
        )

        start = time.perf_counter()
        sim.run(100)
        elapsed = time.perf_counter() - start

        # Record baseline — not a hard gate, just documented
        # On typical hardware: ~2-5 seconds
        assert elapsed < 30, f"Performance regression: {elapsed:.2f}s for 100 ticks"
        print(f"\nPerformance baseline: 20 agents, 100 ticks = {elapsed:.2f}s")
```

**Step 2: Run it**

Run: `uv run pytest tests/test_matching_conformance.py::TestMatchingPerformance -v -s`
Expected: PASS with printed baseline

**Step 3: Commit**

```bash
git add tests/test_matching_conformance.py
git commit -m "test(matching): add performance benchmark baseline (A-205)"
```

---

### Task 8: Implement CentralizedClearingMatching (A-206)

**Files:**
- Modify: `microecon/matching.py`
- Modify: `tests/test_matching.py`
- Modify: `tests/test_matching_conformance.py` (add to ALL_PROTOCOLS)

**Step 1: Write the failing tests**

Add to `tests/test_matching.py`:

```python
from microecon.matching import CentralizedClearingMatching


class TestCentralizedClearingMatching:
    """Tests for centralized clearing matching protocol."""

    def test_single_pair_matched(self):
        """Single proposal with surplus -> trade."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.2)
        a2 = _make_agent("a2", alpha=0.8)
        pos = _setup_pair(grid, a1, a2, Position(0, 0), Position(0, 1))

        proposals = {"a1": ProposeAction(target_id="a2")}
        agents = {"a1": a1, "a2": a2}

        protocol = CentralizedClearingMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        assert len(result.trades) == 1
        assert len(result.rejections) == 0  # Centralized clearing doesn't reject

    def test_welfare_maximizing_match(self):
        """When multiple matches possible, picks highest surplus."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.1)   # Very different alpha
        a2 = _make_agent("a2", alpha=0.9)   # Very different alpha -> high surplus
        a3 = _make_agent("a3", alpha=0.45)  # Similar alpha -> low surplus
        grid.place_agent(a1, Position(0, 0))
        grid.place_agent(a2, Position(0, 1))
        grid.place_agent(a3, Position(1, 0))
        pos = {"a1": Position(0, 0), "a2": Position(0, 1), "a3": Position(1, 0)}

        # Both a1 and a3 propose to a2, a2 is adjacent to both
        proposals = {
            "a1": ProposeAction(target_id="a2"),
            "a3": ProposeAction(target_id="a2"),
        }
        agents = {"a1": a1, "a2": a2, "a3": a3}

        protocol = CentralizedClearingMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        # Should pick a1-a2 (higher surplus) over a3-a2
        assert len(result.trades) == 1
        assert result.trades[0].proposer_id == "a1"
        assert result.trades[0].target_id == "a2"
        assert "a3" in result.non_selections

    def test_no_rejections_only_non_selections(self):
        """Centralized clearing never rejects — unmatched are non-selected."""
        grid = Grid(5)
        a1 = _make_agent("a1", alpha=0.45)
        a2 = _make_agent("a2", alpha=0.55)
        pos = _setup_pair(grid, a1, a2, Position(0, 0), Position(0, 1))

        proposals = {"a1": ProposeAction(target_id="a2")}
        agents = {"a1": a1, "a2": a2}

        protocol = CentralizedClearingMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        # Either trades or non-selects, never rejects
        assert len(result.rejections) == 0

    def test_non_adjacent_not_matched(self):
        """Only adjacent pairs can be matched."""
        grid = Grid(10)
        a1 = _make_agent("a1", alpha=0.2)
        a2 = _make_agent("a2", alpha=0.8)
        pos = _setup_pair(grid, a1, a2, Position(0, 0), Position(5, 5))

        proposals = {"a1": ProposeAction(target_id="a2")}
        agents = {"a1": a1, "a2": a2}

        protocol = CentralizedClearingMatching()
        result = protocol.resolve(
            proposals, agents, pos,
            RationalDecisionProcedure(),
            NashBargainingProtocol(),
        )
        assert len(result.trades) == 0
        assert "a1" in result.non_selections
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_matching.py::TestCentralizedClearingMatching -v`
Expected: FAIL (ImportError — CentralizedClearingMatching doesn't exist)

**Step 3: Write the implementation**

Add to `microecon/matching.py`:

```python
class CentralizedClearingMatching(MatchingProtocol):
    """Centralized welfare-maximizing matching.

    A centralized auctioneer collects all proposals, computes bilateral surplus
    for each adjacent proposer-target pair, and greedily assigns matches by
    descending surplus (each agent matched at most once).

    Key differences from BilateralProposalMatching:
    - No rejections (unmatched = non-selected, no cooldowns)
    - Welfare-maximizing (highest surplus pairs matched first)
    - Simultaneous resolution (no first-responder advantage)

    This is a stub demonstrating the MatchingProtocol interface.
    """

    def resolve(
        self,
        propose_actions: dict[str, "ProposeAction"],
        agents: dict[str, "Agent"],
        positions: dict[str, "Position"],
        decision_procedure: "DecisionProcedure",
        bargaining_protocol: "BargainingProtocol",
    ) -> MatchResult:
        if not propose_actions:
            return MatchResult(trades=(), rejections=(), non_selections=())

        # Compute surplus for each valid proposal (adjacent pairs only)
        scored_proposals: list[tuple[float, str, str]] = []
        for proposer_id, action in propose_actions.items():
            target_id = action.target_id
            proposer = agents.get(proposer_id)
            target = agents.get(target_id)
            if proposer is None or target is None:
                continue

            pos_p = positions.get(proposer_id)
            pos_t = positions.get(target_id)
            if pos_p is None or pos_t is None:
                continue
            if pos_p.chebyshev_distance_to(pos_t) > 1:
                continue

            surplus = bargaining_protocol.compute_expected_surplus(proposer, target)
            if surplus > 0:
                scored_proposals.append((surplus, proposer_id, target_id))

        # Sort by surplus descending, then by proposer_id for determinism
        scored_proposals.sort(key=lambda x: (-x[0], x[1]))

        # Greedy matching: assign highest surplus pairs first
        trades: list[TradeOutcome] = []
        matched: set[str] = set()

        for surplus, proposer_id, target_id in scored_proposals:
            if proposer_id in matched or target_id in matched:
                continue
            trades.append(TradeOutcome(proposer_id=proposer_id, target_id=target_id))
            matched.add(proposer_id)
            matched.add(target_id)

        # All unmatched proposers are non-selected (no rejections in centralized clearing)
        non_selections = tuple(
            pid for pid in propose_actions if pid not in matched
        )

        return MatchResult(
            trades=tuple(trades),
            rejections=(),  # Centralized clearing never rejects
            non_selections=non_selections,
        )
```

**Step 4: Add CentralizedClearingMatching to ALL_PROTOCOLS in conformance tests**

In `tests/test_matching_conformance.py`, update the imports and ALL_PROTOCOLS:

```python
from microecon.matching import (
    BilateralProposalMatching,
    CentralizedClearingMatching,
    MatchingProtocol,
    MatchResult,
)

ALL_PROTOCOLS = [
    BilateralProposalMatching(),
    CentralizedClearingMatching(),
]
```

**Step 5: Run all matching tests**

Run: `uv run pytest tests/test_matching.py tests/test_matching_conformance.py -v`
Expected: ALL PASS

**Step 6: Run full test suite to verify no regressions**

Run: `uv run pytest -q`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add microecon/matching.py tests/test_matching.py tests/test_matching_conformance.py
git commit -m "feat(matching): add CentralizedClearingMatching stub (A-206)"
```

---

### Task 9: Full test suite verification and integration smoke test

**Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: ALL PASS (810+ tests)

**Step 2: Run contract conformance tests**

Run: `uv run pytest -m contract -v`
Expected: ALL PASS (34+ including new matching conformance)

**Step 3: Run determinism tests**

Run: `uv run pytest -m determinism -v`
Expected: ALL PASS (8 tests)

**Step 4: Run frontend checks**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: Clean

**Step 5: Integration smoke test — run simulation with each matching protocol**

Run in Python:

```python
uv run python -c "
from microecon.simulation import create_simple_economy
from microecon.matching import BilateralProposalMatching, CentralizedClearingMatching

# Bilateral (default)
sim1 = create_simple_economy(n_agents=6, grid_size=8, seed=42, matching_protocol=BilateralProposalMatching())
sim1.run(20)
print(f'Bilateral: {len(sim1.trades)} trades, welfare={sum(a.utility for a in sim1.agents):.2f}')

# Centralized
sim2 = create_simple_economy(n_agents=6, grid_size=8, seed=42, matching_protocol=CentralizedClearingMatching())
sim2.run(20)
print(f'Centralized: {len(sim2.trades)} trades, welfare={sum(a.utility for a in sim2.agents):.2f}')
"
```

Expected: Both run without errors. Trade counts and welfare may differ (different matching algorithms).

---

## Summary of All Files Changed

| File | Action | Task |
|---|---|---|
| `docs/adr/ADR-006-MATCHING.md` | Create | 1 |
| `microecon/matching.py` | Create | 2, 3, 8 |
| `tests/test_matching.py` | Create | 2, 3, 8 |
| `microecon/simulation.py` | Modify | 4, 5 |
| `tests/test_matching_conformance.py` | Create | 6, 7, 8 |
