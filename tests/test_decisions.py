"""
Tests for the decision procedure system.

Tests RationalDecisionProcedure behavior, particularly fallback computation
and opportunity cost handling.
"""

import pytest

from microecon.actions import (
    ProposeAction,
    MoveAction,
    WaitAction,
    ActionContext,
)
from microecon.agent import create_agent
from microecon.decisions import RationalDecisionProcedure, DecisionContext
from microecon.grid import Grid, Position
from microecon.bargaining import NashBargainingProtocol


def create_test_context(agents, grid, protocol=None):
    """Helper to create a DecisionContext for testing."""
    if protocol is None:
        protocol = NashBargainingProtocol()

    agent_positions = {}
    for agent in agents:
        pos = grid.get_position(agent)
        if pos is not None:
            agent_positions[agent.id] = pos

    # Compute co-located and adjacent agents
    co_located_agents = {a.id: set() for a in agents}
    adjacent_agents = {a.id: set() for a in agents}

    for i, agent_a in enumerate(agents):
        pos_a = agent_positions.get(agent_a.id)
        if pos_a is None:
            continue
        for agent_b in agents[i+1:]:
            pos_b = agent_positions.get(agent_b.id)
            if pos_b is None:
                continue
            distance = pos_a.chebyshev_distance_to(pos_b)
            if distance == 0:
                co_located_agents[agent_a.id].add(agent_b.id)
                co_located_agents[agent_b.id].add(agent_a.id)
                adjacent_agents[agent_a.id].add(agent_b.id)
                adjacent_agents[agent_b.id].add(agent_a.id)
            elif distance == 1:
                adjacent_agents[agent_a.id].add(agent_b.id)
                adjacent_agents[agent_b.id].add(agent_a.id)

    # Get interaction states
    agent_interaction_states = {a.id: a.interaction_state for a in agents}

    action_context = ActionContext(
        current_tick=0,
        agent_positions=agent_positions,
        agent_interaction_states=agent_interaction_states,
        co_located_agents=co_located_agents,
        adjacent_agents=adjacent_agents,
        pending_proposals={},
    )

    visible_agents = {a.id: a for a in agents}

    return DecisionContext(
        action_context=action_context,
        visible_agents=visible_agents,
        bargaining_protocol=protocol,
        agent_positions=agent_positions,
    )


class TestFallbackComputation:
    """Tests for FEAT-002: Compute fallback in choose()."""

    def test_propose_action_has_fallback_when_chosen(self):
        """When best action is ProposeAction, fallback is computed."""
        grid = Grid(10)
        # Create two agents with complementary endowments at adjacent positions
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))  # Adjacent

        context = create_test_context([agent_a, agent_b], grid)
        # Update co_located for precondition check
        context.action_context.co_located_agents = {"agent_a": ["agent_b"], "agent_b": ["agent_a"]}

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        # Should choose ProposeAction because they can trade
        assert isinstance(action, ProposeAction)
        # Fallback should be set
        assert action.fallback is not None

    def test_fallback_is_move_action_when_not_same_position(self):
        """Fallback is MoveAction toward target when not at same position."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))  # Adjacent but not same position

        context = create_test_context([agent_a, agent_b], grid)
        context.action_context.co_located_agents = {"agent_a": ["agent_b"], "agent_b": ["agent_a"]}

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        assert isinstance(action, ProposeAction)
        assert isinstance(action.fallback, MoveAction)
        assert action.fallback.target_position == Position(1, 0)  # B's position

    def test_fallback_is_wait_action_when_same_position(self):
        """Fallback is WaitAction when agent and target at same position."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        # Both at same position
        grid.place_agent(agent_a, Position(5, 5))
        grid.place_agent(agent_b, Position(5, 5))

        context = create_test_context([agent_a, agent_b], grid)
        context.action_context.co_located_agents = {"agent_a": ["agent_b"], "agent_b": ["agent_a"]}

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        assert isinstance(action, ProposeAction)
        assert isinstance(action.fallback, WaitAction)

    def test_fallback_always_set_for_propose_action(self):
        """ProposeAction always has fallback when returned from choose()."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(0, 1))

        context = create_test_context([agent_a, agent_b], grid)
        context.action_context.co_located_agents = {"agent_a": ["agent_b"], "agent_b": ["agent_a"]}

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        if isinstance(action, ProposeAction):
            assert action.fallback is not None, "ProposeAction from choose() must have fallback"

    def test_non_propose_actions_unchanged(self):
        """MoveAction and WaitAction are returned as-is without modification."""
        grid = Grid(10)
        # Agent alone - no one to trade with
        agent_a = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0, agent_id="agent_a")

        grid.place_agent(agent_a, Position(0, 0))

        context = create_test_context([agent_a], grid)
        context.action_context.co_located_agents = {"agent_a": []}

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        # Should be WaitAction since no one to trade with
        assert isinstance(action, WaitAction)


class TestFallbackPreservesProposeProperties:
    """Ensure fallback computation doesn't alter other ProposeAction properties."""

    def test_target_id_preserved(self):
        """target_id is preserved when attaching fallback."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)
        context.action_context.co_located_agents = {"agent_a": ["agent_b"], "agent_b": ["agent_a"]}

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        assert isinstance(action, ProposeAction)
        assert action.target_id == "agent_b"

    def test_exchange_id_preserved(self):
        """exchange_id is preserved when attaching fallback."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)
        context.action_context.co_located_agents = {"agent_a": ["agent_b"], "agent_b": ["agent_a"]}

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        assert isinstance(action, ProposeAction)
        assert action.exchange_id is not None
        assert len(action.exchange_id) == 8  # UUID format


class TestOpportunityCostStorage:
    """Tests for FEAT-003: Store opportunity cost in agent state."""

    def test_opportunity_cost_set_during_choose(self):
        """Agent._opportunity_cost is set when choose() is called."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)

        # Check initial value
        assert agent_a.opportunity_cost == 0.0

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        # After choose, opportunity cost should be set
        # Since agent chose ProposeAction (beneficial), opportunity cost > 0
        assert isinstance(action, ProposeAction)
        assert agent_a.opportunity_cost > 0.0

    def test_opportunity_cost_equals_best_action_value(self):
        """Opportunity cost equals the value of the chosen action."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)
        protocol = NashBargainingProtocol()

        # Compute expected surplus directly
        expected_surplus = protocol.compute_expected_surplus(agent_a, agent_b)

        procedure = RationalDecisionProcedure()
        procedure.choose(agent_a, context)

        # Opportunity cost should equal the expected surplus from trading with B
        assert abs(agent_a.opportunity_cost - expected_surplus) < 1e-10

    def test_opportunity_cost_zero_when_wait_chosen(self):
        """Opportunity cost is 0 when agent chooses WaitAction."""
        grid = Grid(10)
        # Agent alone - no one to trade with
        agent_a = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0, agent_id="agent_a")

        grid.place_agent(agent_a, Position(0, 0))

        context = create_test_context([agent_a], grid)

        procedure = RationalDecisionProcedure()
        action = procedure.choose(agent_a, context)

        # Should wait (no trade partners)
        assert isinstance(action, WaitAction)
        # Opportunity cost should be 0
        assert agent_a.opportunity_cost == 0.0

    def test_opportunity_cost_nonnegative(self):
        """Opportunity cost is always >= 0."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)

        procedure = RationalDecisionProcedure()
        procedure.choose(agent_a, context)

        assert agent_a.opportunity_cost >= 0.0

    def test_opportunity_cost_accessible_via_property(self):
        """Opportunity cost is accessible via agent.opportunity_cost property."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)

        procedure = RationalDecisionProcedure()
        procedure.choose(agent_a, context)

        # Verify property accessor works
        opp_cost = agent_a.opportunity_cost
        assert isinstance(opp_cost, float)
        assert opp_cost > 0.0


class TestOpportunityCostAcceptance:
    """Tests for FEAT-004: Opportunity cost acceptance check."""

    def test_accept_when_surplus_exceeds_opportunity_cost(self):
        """Agent accepts proposal when surplus >= opportunity_cost."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)
        protocol = NashBargainingProtocol()

        # Set opportunity cost to 0 - should accept any positive surplus
        agent_b.opportunity_cost = 0.0

        procedure = RationalDecisionProcedure()
        result = procedure.evaluate_proposal(agent_b, agent_a, context)

        # Surplus should be positive, so accept
        surplus = protocol.compute_expected_surplus(agent_b, agent_a)
        assert surplus > 0
        assert result is True

    def test_reject_when_surplus_below_opportunity_cost(self):
        """Agent rejects proposal when surplus < opportunity_cost."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)
        protocol = NashBargainingProtocol()

        # Compute actual surplus
        surplus = protocol.compute_expected_surplus(agent_b, agent_a)

        # Set opportunity cost higher than surplus - should reject
        agent_b.opportunity_cost = surplus + 1.0

        procedure = RationalDecisionProcedure()
        result = procedure.evaluate_proposal(agent_b, agent_a, context)

        assert result is False

    def test_accept_when_surplus_equals_opportunity_cost(self):
        """Agent accepts when surplus exactly equals opportunity_cost (>=)."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)
        protocol = NashBargainingProtocol()

        # Set opportunity cost exactly equal to surplus
        surplus = protocol.compute_expected_surplus(agent_b, agent_a)
        agent_b.opportunity_cost = surplus

        procedure = RationalDecisionProcedure()
        result = procedure.evaluate_proposal(agent_b, agent_a, context)

        # Should accept (>= not just >)
        assert result is True

    def test_agent_with_better_alternative_rejects_mediocre_proposal(self):
        """Agent with high opportunity cost rejects lower-value proposal."""
        grid = Grid(10)
        # Create 3 agents with different trade values
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.5, endowment_x=6.0, endowment_y=6.0, agent_id="agent_b")
        agent_c = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_c")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))
        grid.place_agent(agent_c, Position(2, 0))

        context = create_test_context([agent_a, agent_b, agent_c], grid)
        protocol = NashBargainingProtocol()

        # B's surplus trading with A vs C
        surplus_b_with_a = protocol.compute_expected_surplus(agent_b, agent_a)
        surplus_b_with_c = protocol.compute_expected_surplus(agent_b, agent_c)

        # If B's opportunity cost is from trading with C
        agent_b.opportunity_cost = surplus_b_with_c

        procedure = RationalDecisionProcedure()

        # B should accept A's proposal only if surplus_with_A >= surplus_with_C
        result = procedure.evaluate_proposal(agent_b, agent_a, context)

        if surplus_b_with_a >= surplus_b_with_c:
            assert result is True
        else:
            assert result is False

    def test_acceptance_uses_stored_opportunity_cost(self):
        """evaluate_proposal uses the stored opportunity_cost, not recomputed."""
        grid = Grid(10)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="agent_a")
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="agent_b")

        grid.place_agent(agent_a, Position(0, 0))
        grid.place_agent(agent_b, Position(1, 0))

        context = create_test_context([agent_a, agent_b], grid)
        protocol = NashBargainingProtocol()

        surplus = protocol.compute_expected_surplus(agent_b, agent_a)

        procedure = RationalDecisionProcedure()

        # Set low opportunity cost - should accept
        agent_b.opportunity_cost = 0.0
        assert procedure.evaluate_proposal(agent_b, agent_a, context) is True

        # Set high opportunity cost - should reject
        agent_b.opportunity_cost = surplus + 10.0
        assert procedure.evaluate_proposal(agent_b, agent_a, context) is False
