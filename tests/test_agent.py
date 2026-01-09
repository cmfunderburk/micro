"""Tests for Agent and related classes."""

import pytest
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import Agent, AgentPrivateState, AgentType, create_agent

pytestmark = pytest.mark.core


class TestAgentPrivateState:
    """Test agent private state."""

    def test_create_private_state(self):
        prefs = CobbDouglas(0.5)
        endowment = Bundle(10.0, 5.0)
        state = AgentPrivateState(prefs, endowment)

        assert state.preferences.alpha == 0.5
        assert state.endowment == Bundle(10.0, 5.0)

    def test_utility_from_endowment(self):
        prefs = CobbDouglas(0.5)
        endowment = Bundle(4.0, 4.0)
        state = AgentPrivateState(prefs, endowment)

        assert state.utility() == pytest.approx(4.0)

    def test_utility_of_bundle(self):
        prefs = CobbDouglas(0.5)
        endowment = Bundle(4.0, 4.0)
        state = AgentPrivateState(prefs, endowment)

        other_bundle = Bundle(9.0, 1.0)
        # 9^0.5 * 1^0.5 = 3
        assert state.utility_of(other_bundle) == pytest.approx(3.0)


class TestAgentType:
    """Test observable agent type."""

    def test_from_private_state(self):
        prefs = CobbDouglas(0.5)
        endowment = Bundle(10.0, 5.0)
        state = AgentPrivateState(prefs, endowment)

        agent_type = AgentType.from_private_state(state)

        assert agent_type.preferences.alpha == 0.5
        assert agent_type.endowment == Bundle(10.0, 5.0)

    def test_type_is_immutable(self):
        prefs = CobbDouglas(0.5)
        agent_type = AgentType(prefs, Bundle(10.0, 5.0))

        with pytest.raises(AttributeError):
            agent_type.endowment = Bundle(1.0, 1.0)


class TestAgent:
    """Test Agent class."""

    def test_create_agent(self):
        agent = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=5.0,
        )

        assert agent.preferences.alpha == 0.5
        assert agent.endowment == Bundle(10.0, 5.0)
        assert agent.perception_radius == 3.0  # default
        assert agent.discount_factor == 0.95  # default

    def test_create_agent_with_params(self):
        agent = create_agent(
            alpha=0.3,
            endowment_x=5.0,
            endowment_y=15.0,
            perception_radius=5.0,
            discount_factor=0.9,
            movement_budget=2,
        )

        assert agent.perception_radius == 5.0
        assert agent.discount_factor == 0.9
        assert agent.movement_budget == 2

    def test_agent_utility(self):
        agent = create_agent(alpha=0.5, endowment_x=4.0, endowment_y=4.0)
        assert agent.utility() == pytest.approx(4.0)

    def test_agent_endowment_update(self):
        agent = create_agent(alpha=0.5, endowment_x=4.0, endowment_y=4.0)
        agent.endowment = Bundle(8.0, 8.0)
        assert agent.endowment == Bundle(8.0, 8.0)
        assert agent.utility() == pytest.approx(8.0)

    def test_would_gain_from(self):
        agent = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=9.0)
        # Current utility: 1^0.5 * 9^0.5 = 3

        better = Bundle(4.0, 4.0)  # utility 4
        worse = Bundle(1.0, 1.0)  # utility 1

        assert agent.would_gain_from(better)
        assert not agent.would_gain_from(worse)

    def test_agent_unique_ids(self):
        agent1 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        agent2 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        assert agent1.id != agent2.id

    def test_agent_equality_by_id(self):
        agent1 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        agent2 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        assert agent1 != agent2
        assert agent1 == agent1
