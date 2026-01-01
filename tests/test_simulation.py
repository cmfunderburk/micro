"""Tests for simulation engine."""

import pytest
from microecon.bundle import Bundle
from microecon.grid import Grid, Position
from microecon.agent import create_agent
from microecon.information import FullInformation
from microecon.simulation import Simulation, create_simple_economy


class TestSimulationSetup:
    """Test simulation setup."""

    def test_create_simulation(self):
        sim = Simulation(grid=Grid(10))
        assert sim.tick == 0
        assert len(sim.agents) == 0

    def test_add_agent(self):
        sim = Simulation(grid=Grid(10))
        agent = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0)

        sim.add_agent(agent, Position(3, 3))

        assert len(sim.agents) == 1
        assert sim.grid.get_position(agent) == Position(3, 3)

    def test_add_agent_random(self):
        sim = Simulation(grid=Grid(10))
        agent = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0)

        pos = sim.add_agent_random(agent)

        assert len(sim.agents) == 1
        assert 0 <= pos.row < 10
        assert 0 <= pos.col < 10


class TestSimulationStep:
    """Test simulation step mechanics."""

    def test_step_increments_tick(self):
        sim = Simulation(grid=Grid(10))
        assert sim.tick == 0

        sim.step()
        assert sim.tick == 1

        sim.step()
        assert sim.tick == 2

    def test_agents_at_same_position_trade(self):
        """Agents placed at same position should trade."""
        sim = Simulation(grid=Grid(10), info_env=FullInformation())

        # Create agents with complementary endowments
        agent1 = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=2.0)
        agent2 = create_agent(alpha=0.5, endowment_x=2.0, endowment_y=10.0)

        pos = Position(5, 5)
        sim.add_agent(agent1, pos)
        sim.add_agent(agent2, pos)

        initial_u1 = agent1.utility()
        initial_u2 = agent2.utility()

        trades = sim.step()

        assert len(trades) == 1
        assert agent1.utility() >= initial_u1
        assert agent2.utility() >= initial_u2

    def test_agents_at_different_positions_dont_trade(self):
        """Agents at different positions shouldn't trade immediately."""
        sim = Simulation(grid=Grid(10), info_env=FullInformation())

        agent1 = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=2.0)
        agent2 = create_agent(alpha=0.5, endowment_x=2.0, endowment_y=10.0)

        sim.add_agent(agent1, Position(0, 0))
        sim.add_agent(agent2, Position(9, 9))

        trades = sim.step()

        assert len(trades) == 0


class TestSimulationRun:
    """Test running simulation for multiple ticks."""

    def test_run_multiple_ticks(self):
        sim = create_simple_economy(n_agents=4, grid_size=10, seed=42)

        sim.run(10)

        assert sim.tick == 10

    def test_run_with_callback(self):
        sim = create_simple_economy(n_agents=4, grid_size=10, seed=42)

        ticks_recorded = []

        def callback(tick: int, trades):
            ticks_recorded.append(tick)

        sim.run(5, callback=callback)

        assert ticks_recorded == [1, 2, 3, 4, 5]


class TestSimulationState:
    """Test simulation state snapshots."""

    def test_get_state(self):
        sim = create_simple_economy(n_agents=4, grid_size=10, seed=42)
        sim.run(5)

        state = sim.get_state()

        assert state.tick == 5
        assert len(state.agent_utilities) == 4
        assert len(state.agent_positions) == 4

    def test_total_welfare(self):
        sim = create_simple_economy(n_agents=4, grid_size=10, seed=42)

        initial_welfare = sim.total_welfare()
        sim.run(20)
        final_welfare = sim.total_welfare()

        # Welfare should not decrease (trades are voluntary)
        assert final_welfare >= initial_welfare - 1e-6


class TestCreateSimpleEconomy:
    """Test economy creation helper."""

    def test_creates_correct_number_of_agents(self):
        sim = create_simple_economy(n_agents=8, grid_size=10)
        assert len(sim.agents) == 8

    def test_agents_have_varied_preferences(self):
        sim = create_simple_economy(n_agents=10, seed=42)

        alphas = [a.preferences.alpha for a in sim.agents]

        # Should have variety
        assert min(alphas) < 0.4
        assert max(alphas) > 0.6

    def test_agents_have_complementary_endowments(self):
        sim = create_simple_economy(n_agents=4, seed=42)

        # Some agents should have more x, others more y
        x_rich = sum(1 for a in sim.agents if a.endowment.x > a.endowment.y)
        y_rich = sum(1 for a in sim.agents if a.endowment.y > a.endowment.x)

        assert x_rich >= 1
        assert y_rich >= 1

    def test_seed_reproducibility(self):
        sim1 = create_simple_economy(n_agents=4, grid_size=10, seed=42)
        sim2 = create_simple_economy(n_agents=4, grid_size=10, seed=42)

        # Same seed should give same positions
        for a1, a2 in zip(sim1.agents, sim2.agents):
            pos1 = sim1.grid.get_position(a1)
            pos2 = sim2.grid.get_position(a2)
            assert pos1 == pos2
