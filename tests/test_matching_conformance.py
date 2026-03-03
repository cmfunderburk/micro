"""Matching protocol conformance tests (A-205).

Any MatchingProtocol implementation must pass these tests.
Tests are parametrized over all registered protocol implementations.
"""

import time

import pytest

from microecon.matching import (
    BilateralProposalMatching,
    CentralizedClearingMatching,
    MatchingProtocol,
    MatchResult,
)
from microecon.actions import ProposeAction
from microecon.agent import create_agent
from microecon.grid import Grid, Position
from microecon.bargaining import NashBargainingProtocol
from microecon.decisions import RationalDecisionProcedure
from microecon.simulation import create_simple_economy

pytestmark = pytest.mark.contract

ALL_PROTOCOLS = [
    BilateralProposalMatching(),
    CentralizedClearingMatching(),
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


class TestMatchingPerformance:
    """Performance baseline for matching protocols.

    Not a hard gate -- records reference numbers for regression monitoring.
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

        # Record baseline -- not a hard gate, just documented
        # Observed range: ~30-60s depending on hardware
        assert elapsed < 120, f"Performance regression: {elapsed:.2f}s for 100 ticks"
        print(f"\nPerformance baseline: 20 agents, 100 ticks = {elapsed:.2f}s")
