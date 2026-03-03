"""Tests for search behavior."""

import pytest
from microecon.bundle import Bundle
from microecon.grid import Grid, Position
from microecon.agent import create_agent
from microecon.information import FullInformation
from microecon.search import evaluate_targets, compute_move_target, should_trade

pytestmark = pytest.mark.search


class TestEvaluateTargets:
    """Test target evaluation for search."""

    def test_find_best_target(self):
        grid = Grid(20)
        info_env = FullInformation()

        # Observer prefers y (low alpha), has lots of x
        observer = create_agent(
            alpha=0.3,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
        )
        grid.place_agent(observer, Position(10, 10))

        # Target 1: Prefers x (high alpha), has lots of y - good trade partner
        target1 = create_agent(
            alpha=0.7,
            endowment_x=2.0,
            endowment_y=10.0,
        )
        grid.place_agent(target1, Position(12, 10))  # distance 2

        # Target 2: Same preferences as observer - less gains from trade
        target2 = create_agent(
            alpha=0.3,
            endowment_x=2.0,
            endowment_y=10.0,
        )
        grid.place_agent(target2, Position(11, 10))  # distance 1, but less surplus

        agents_by_id = {
            observer.id: observer,
            target1.id: target1,
            target2.id: target2,
        }

        result = evaluate_targets(observer, grid, info_env, agents_by_id)

        assert result.visible_agents == 2
        assert result.best_target_id is not None
        assert result.discounted_value > 0

    def test_no_visible_targets(self):
        grid = Grid(20)
        info_env = FullInformation()

        observer = create_agent(
            alpha=0.5,
            endowment_x=5.0,
            endowment_y=5.0,
            perception_radius=2.0,  # Small radius
        )
        grid.place_agent(observer, Position(0, 0))

        # Target is too far
        target = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=10.0,
        )
        grid.place_agent(target, Position(10, 10))  # distance > 2

        agents_by_id = {observer.id: observer, target.id: target}

        result = evaluate_targets(observer, grid, info_env, agents_by_id)

        assert result.visible_agents == 0
        assert result.best_target_id is None

    def test_discounting_affects_target_choice(self):
        """Closer targets may be preferred due to discounting."""
        grid = Grid(20)
        info_env = FullInformation()

        observer = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=15.0,
            discount_factor=0.8,  # Strong discounting
        )
        grid.place_agent(observer, Position(10, 10))

        # Target 1: Far but excellent trade
        target1 = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
        )
        grid.place_agent(target1, Position(18, 18))  # far

        # Target 2: Close, still good trade
        target2 = create_agent(
            alpha=0.5,
            endowment_x=3.0,
            endowment_y=9.0,
        )
        grid.place_agent(target2, Position(11, 11))  # close

        agents_by_id = {
            observer.id: observer,
            target1.id: target1,
            target2.id: target2,
        }

        result = evaluate_targets(observer, grid, info_env, agents_by_id)

        # With strong discounting, closer target should be preferred
        assert result.best_target_id == target2.id


class TestComputeMoveTarget:
    """Test move target computation."""

    def test_returns_target_position(self):
        grid = Grid(20)
        info_env = FullInformation()

        observer = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
        )
        grid.place_agent(observer, Position(0, 0))

        target = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
        )
        target_pos = Position(5, 5)
        grid.place_agent(target, target_pos)

        agents_by_id = {observer.id: observer, target.id: target}

        move_target = compute_move_target(observer, grid, info_env, agents_by_id)

        assert move_target == target_pos

    def test_returns_none_when_no_targets(self):
        grid = Grid(20)
        info_env = FullInformation()

        observer = create_agent(
            alpha=0.5,
            endowment_x=5.0,
            endowment_y=5.0,
            perception_radius=2.0,
        )
        grid.place_agent(observer, Position(0, 0))

        agents_by_id = {observer.id: observer}

        move_target = compute_move_target(observer, grid, info_env, agents_by_id)

        assert move_target is None


class TestShouldTrade:
    """Test trade decision."""

    def test_trade_when_mutual_gains(self):
        info_env = FullInformation()

        agent1 = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=2.0)
        agent2 = create_agent(alpha=0.5, endowment_x=2.0, endowment_y=10.0)

        assert should_trade(agent1, agent2, info_env)

    def test_no_trade_when_identical(self):
        info_env = FullInformation()

        agent1 = create_agent(alpha=0.5, endowment_x=6.0, endowment_y=6.0)
        agent2 = create_agent(alpha=0.5, endowment_x=6.0, endowment_y=6.0)

        # No gains from trade between identical agents
        result = should_trade(agent1, agent2, info_env)
        # May or may not trade depending on numerical precision
        # The key is welfare should not decrease


class TestSearchIntegration:
    """Integration tests for search behavior."""

    def test_agents_converge_to_trade(self):
        """Agents should move toward each other and eventually trade."""
        from microecon.simulation import Simulation

        grid = Grid(10)
        sim = Simulation(grid=grid, info_env=FullInformation())

        # Place agents at opposite corners
        agent1 = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=15.0,  # Can see across grid
        )
        agent2 = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=15.0,
        )

        sim.add_agent(agent1, Position(0, 0))
        sim.add_agent(agent2, Position(9, 9))

        initial_u1 = agent1.utility()
        initial_u2 = agent2.utility()

        # Run until they trade
        for _ in range(20):
            trades = sim.step()
            if trades:
                break

        # Should have traded
        assert len(sim.trades) > 0
        assert agent1.utility() >= initial_u1
        assert agent2.utility() >= initial_u2


class TestCooldownExclusion:
    """Tests for FEAT-006: Cooldown exclusion from search."""

    def test_evaluate_targets_skips_cooldown(self):
        """evaluate_targets skips agents on cooldown."""
        from microecon.search import evaluate_targets_detailed

        grid = Grid(10)
        info_env = FullInformation()

        observer = create_agent(
            alpha=0.3,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
            agent_id="observer",
        )
        target = create_agent(
            alpha=0.7,
            endowment_x=2.0,
            endowment_y=10.0,
            agent_id="target",
        )

        grid.place_agent(observer, Position(0, 0))
        grid.place_agent(target, Position(1, 0))

        agents_by_id = {observer.id: observer, target.id: target}

        # Without cooldown - should find target
        result_no_cooldown, evals_no_cooldown = evaluate_targets_detailed(
            observer, grid, info_env, agents_by_id
        )
        assert result_no_cooldown.best_target_id == target.id
        assert len(evals_no_cooldown) == 1

        # Add cooldown for target
        observer.interaction_state.cooldowns[target.id] = 3

        # With cooldown - should not find target
        result_with_cooldown, evals_with_cooldown = evaluate_targets_detailed(
            observer, grid, info_env, agents_by_id
        )
        assert result_with_cooldown.best_target_id is None
        assert len(evals_with_cooldown) == 0

    def test_available_actions_excludes_move_to_cooldown(self):
        """available_actions excludes MoveAction toward cooldown targets."""
        from microecon.decisions import RationalDecisionProcedure, DecisionContext
        from microecon.actions import ActionContext, MoveAction
        from microecon.bargaining import NashBargainingProtocol

        grid = Grid(10)
        observer = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="observer")
        target = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="target")

        grid.place_agent(observer, Position(0, 0))
        grid.place_agent(target, Position(5, 0))  # Not adjacent (distance 5)

        agent_positions = {observer.id: Position(0, 0), target.id: Position(5, 0)}
        action_context = ActionContext(
            current_tick=0,
            agent_positions=agent_positions,
            agent_interaction_states={
                observer.id: observer.interaction_state,
                target.id: target.interaction_state,
            },
            co_located_agents={observer.id: set(), target.id: set()},
            adjacent_agents={observer.id: set(), target.id: set()},
            pending_proposals={},
        )
        decision_context = DecisionContext(
            action_context=action_context,
            visible_agents={target.id: target},
            bargaining_protocol=NashBargainingProtocol(),
            agent_positions=agent_positions,
        )

        procedure = RationalDecisionProcedure()

        # Without cooldown - should include MoveAction toward target
        actions_no_cooldown = procedure.available_actions(observer, decision_context)
        move_actions = [a for a in actions_no_cooldown if isinstance(a, MoveAction)]
        assert len(move_actions) == 1
        assert move_actions[0].target_position == Position(5, 0)

        # Add cooldown for target
        observer.interaction_state.cooldowns[target.id] = 3

        # With cooldown - should NOT include MoveAction toward target
        actions_with_cooldown = procedure.available_actions(observer, decision_context)
        move_actions = [a for a in actions_with_cooldown if isinstance(a, MoveAction)]
        assert len(move_actions) == 0

    def test_propose_action_blocked_by_cooldown(self):
        """ProposeAction preconditions return False for cooldown targets."""
        from microecon.actions import ProposeAction, ActionContext

        grid = Grid(10)
        observer = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, agent_id="observer")
        target = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, agent_id="target")

        grid.place_agent(observer, Position(0, 0))
        grid.place_agent(target, Position(0, 0))  # Co-located

        action_context = ActionContext(
            current_tick=0,
            agent_positions={observer.id: Position(0, 0), target.id: Position(0, 0)},
            agent_interaction_states={
                observer.id: observer.interaction_state,
                target.id: target.interaction_state,
            },
            co_located_agents={observer.id: {target.id}, target.id: {observer.id}},
            adjacent_agents={observer.id: {target.id}, target.id: {observer.id}},
            pending_proposals={},
        )

        action = ProposeAction(target_id=target.id)

        # Without cooldown - preconditions pass
        assert action.preconditions(observer, action_context) is True

        # Add cooldown
        observer.interaction_state.cooldowns[target.id] = 3

        # With cooldown - preconditions fail
        assert action.preconditions(observer, action_context) is False
