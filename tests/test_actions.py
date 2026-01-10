"""
Tests for the action system.

Tests the Action classes, particularly ProposeAction with fallback.
"""

import pytest

from microecon.actions import (
    ProposeAction,
    MoveAction,
    WaitAction,
    ActionType,
)
from microecon.grid import Position


class TestProposeActionFallback:
    """Tests for ProposeAction.fallback field (FEAT-001)."""

    def test_propose_action_accepts_fallback_parameter(self):
        """ProposeAction accepts fallback parameter."""
        fallback = MoveAction(Position(0, 0))
        action = ProposeAction(target_id="agent_b", fallback=fallback)

        assert action.fallback is fallback
        assert action.target_id == "agent_b"

    def test_propose_action_fallback_defaults_to_none(self):
        """Fallback defaults to None (backward compatible)."""
        action = ProposeAction(target_id="agent_b")

        assert action.fallback is None

    def test_propose_action_fallback_accepts_move_action(self):
        """Fallback can be a MoveAction."""
        fallback = MoveAction(Position(5, 5))
        action = ProposeAction(target_id="agent_b", fallback=fallback)

        assert isinstance(action.fallback, MoveAction)
        assert action.fallback.target_position == Position(5, 5)

    def test_propose_action_fallback_accepts_wait_action(self):
        """Fallback can be a WaitAction."""
        fallback = WaitAction()
        action = ProposeAction(target_id="agent_b", fallback=fallback)

        assert isinstance(action.fallback, WaitAction)

    def test_propose_action_fallback_rejects_propose_action(self):
        """Fallback must be MoveAction or WaitAction, never ProposeAction."""
        nested_propose = ProposeAction(target_id="agent_c")

        with pytest.raises(ValueError, match="cannot be another ProposeAction"):
            ProposeAction(target_id="agent_b", fallback=nested_propose)

    def test_propose_action_properties_unchanged(self):
        """Adding fallback doesn't affect other ProposeAction properties."""
        action = ProposeAction(
            target_id="agent_b",
            exchange_id="test123",
            fallback=WaitAction()
        )

        assert action.target_id == "agent_b"
        assert action.exchange_id == "test123"
        assert action.action_type == ActionType.PROPOSE
        assert action.cost() == 1


class TestProposeActionBackwardCompatibility:
    """Ensure ProposeAction changes don't break existing code."""

    def test_propose_action_without_fallback(self):
        """ProposeAction works without fallback (existing code pattern)."""
        action = ProposeAction("agent_b")

        assert action.target_id == "agent_b"
        assert action.fallback is None
        assert action.exchange_id is not None

    def test_propose_action_with_exchange_id_only(self):
        """ProposeAction works with only exchange_id (existing code pattern)."""
        action = ProposeAction("agent_b", "exch123")

        assert action.target_id == "agent_b"
        assert action.exchange_id == "exch123"
        assert action.fallback is None
