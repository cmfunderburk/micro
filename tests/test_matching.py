"""Tests for matching protocol types, interface (A-201), and BilateralProposalMatching (A-202, A-203)."""

import pytest

from microecon.matching import (
    BilateralProposalMatching,
    MatchingProtocol,
    MatchResult,
    TradeOutcome,
    Rejection,
)
from microecon.actions import ProposeAction
from microecon.agent import create_agent
from microecon.grid import Grid, Position
from microecon.bargaining import NashBargainingProtocol
from microecon.decisions import RationalDecisionProcedure, DecisionContext


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


# =============================================================================
# BilateralProposalMatching Tests (A-202, A-203)
# =============================================================================


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

    def test_is_matching_protocol_subclass(self):
        """BilateralProposalMatching implements MatchingProtocol."""
        protocol = BilateralProposalMatching()
        assert isinstance(protocol, MatchingProtocol)
