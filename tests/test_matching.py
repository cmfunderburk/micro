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
