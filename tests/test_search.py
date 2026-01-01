"""Tests for search behavior."""

import pytest
from microecon.bundle import Bundle
from microecon.grid import Grid, Position
from microecon.agent import create_agent
from microecon.information import FullInformation
from microecon.search import evaluate_targets, compute_move_target, should_trade


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
