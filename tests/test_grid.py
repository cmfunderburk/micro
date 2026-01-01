"""Tests for Grid and Position classes."""

import pytest
import math
from microecon.grid import Grid, Position
from microecon.agent import create_agent


class TestPosition:
    """Test Position class."""

    def test_create_position(self):
        pos = Position(3, 5)
        assert pos.row == 3
        assert pos.col == 5

    def test_euclidean_distance(self):
        p1 = Position(0, 0)
        p2 = Position(3, 4)
        assert p1.distance_to(p2) == pytest.approx(5.0)

    def test_manhattan_distance(self):
        p1 = Position(0, 0)
        p2 = Position(3, 4)
        assert p1.manhattan_distance_to(p2) == 7

    def test_chebyshev_distance(self):
        p1 = Position(0, 0)
        p2 = Position(3, 4)
        assert p1.chebyshev_distance_to(p2) == 4

    def test_neighbors_with_diagonal(self):
        pos = Position(5, 5)
        neighbors = pos.neighbors(include_diagonal=True)
        assert len(neighbors) == 8

    def test_neighbors_without_diagonal(self):
        pos = Position(5, 5)
        neighbors = pos.neighbors(include_diagonal=False)
        assert len(neighbors) == 4

    def test_step_toward(self):
        start = Position(0, 0)
        target = Position(3, 4)

        step1 = start.step_toward(target)
        assert step1 == Position(1, 1)  # Diagonal step

    def test_step_toward_same_position(self):
        pos = Position(5, 5)
        assert pos.step_toward(pos) == pos


class TestGrid:
    """Test Grid class."""

    def test_create_grid(self):
        grid = Grid(10)
        assert grid.size == 10
        assert not grid.wrap

    def test_reject_invalid_size(self):
        with pytest.raises(ValueError):
            Grid(0)

    def test_place_agent(self):
        grid = Grid(10)
        agent = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        pos = Position(3, 5)

        grid.place_agent(agent, pos)

        assert grid.get_position(agent) == pos

    def test_place_agent_out_of_bounds(self):
        grid = Grid(10, wrap=False)
        agent = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        with pytest.raises(ValueError, match="out of bounds"):
            grid.place_agent(agent, Position(10, 5))

    def test_place_agent_wrapping(self):
        grid = Grid(10, wrap=True)
        agent = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        grid.place_agent(agent, Position(15, 5))

        assert grid.get_position(agent) == Position(5, 5)

    def test_move_agent(self):
        grid = Grid(10)
        agent = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        grid.place_agent(agent, Position(0, 0))
        grid.move_agent(agent, Position(5, 5))

        assert grid.get_position(agent) == Position(5, 5)

    def test_remove_agent(self):
        grid = Grid(10)
        agent = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        grid.place_agent(agent, Position(3, 3))
        grid.remove_agent(agent)

        assert grid.get_position(agent) is None

    def test_agents_at_position(self):
        grid = Grid(10)
        agent1 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        agent2 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        pos = Position(5, 5)

        grid.place_agent(agent1, pos)
        grid.place_agent(agent2, pos)

        agents = grid.agents_at(pos)
        assert agent1.id in agents
        assert agent2.id in agents

    def test_move_toward(self):
        grid = Grid(10)
        agent = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        grid.place_agent(agent, Position(0, 0))
        new_pos = grid.move_toward(agent, Position(5, 5), steps=2)

        assert new_pos == Position(2, 2)
        assert grid.get_position(agent) == Position(2, 2)

    def test_agents_within_radius(self):
        grid = Grid(10)
        center = Position(5, 5)

        agent1 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        agent2 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        agent3 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        grid.place_agent(agent1, Position(5, 6))  # distance 1
        grid.place_agent(agent2, Position(3, 3))  # distance ~2.83
        grid.place_agent(agent3, Position(0, 0))  # distance ~7.07

        nearby = list(grid.agents_within_radius(center, 3.0))

        assert len(nearby) == 2
        ids = {item[0] for item in nearby}
        assert agent1.id in ids
        assert agent2.id in ids
        assert agent3.id not in ids

    def test_agents_at_same_position(self):
        grid = Grid(10)
        agent1 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        agent2 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        pos = Position(5, 5)

        grid.place_agent(agent1, pos)
        grid.place_agent(agent2, pos)

        others = grid.agents_at_same_position(agent1)
        assert agent2.id in others
        assert agent1.id not in others

    def test_wrapped_distance(self):
        grid = Grid(10, wrap=True)

        p1 = Position(0, 0)
        p2 = Position(9, 0)

        # Direct distance would be 9, wrapped distance is 1
        dist = grid.distance(p1, p2)
        assert dist == pytest.approx(1.0)
