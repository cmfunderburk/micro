"""
Tests for matching protocols.

Tests cover:
1. OpportunisticMatchingProtocol behavior
"""

import pytest
from microecon.matching import (
    MatchingProtocol,
    OpportunisticMatchingProtocol,
)
from microecon.agent import Agent, AgentPrivateState
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas

pytestmark = pytest.mark.matching


def make_agent(agent_id: str, alpha: float, endowment_x: float, endowment_y: float) -> Agent:
    """Helper to create agents with explicit IDs for testing."""
    return Agent(
        id=agent_id,
        private_state=AgentPrivateState(
            preferences=CobbDouglas(alpha),
            endowment=Bundle(endowment_x, endowment_y),
        ),
        perception_radius=10.0,
        discount_factor=0.95,
    )


class TestOpportunisticMatchingProtocol:
    """Tests for opportunistic matching (no explicit commitment)."""

    def test_requires_commitment_false(self):
        """Opportunistic matching doesn't require commitment."""
        protocol = OpportunisticMatchingProtocol()
        assert protocol.requires_commitment is False

    def test_compute_matches_returns_empty(self):
        """Opportunistic matching returns no committed pairs."""
        protocol = OpportunisticMatchingProtocol()

        agents = [
            make_agent("a", alpha=0.3, endowment_x=10, endowment_y=2),
            make_agent("b", alpha=0.7, endowment_x=2, endowment_y=10),
        ]

        visibility = {
            agents[0].id: {agents[1].id},
            agents[1].id: {agents[0].id},
        }

        def surplus_fn(a, b):
            return 1.0  # Positive surplus

        matches = protocol.compute_matches(agents, visibility, surplus_fn)

        assert matches == []

    def test_is_matching_protocol_subclass(self):
        """OpportunisticMatchingProtocol is a MatchingProtocol."""
        protocol = OpportunisticMatchingProtocol()
        assert isinstance(protocol, MatchingProtocol)
