"""Tests for Grid and Position classes."""

import pytest
import math
from microecon.grid import Grid, Position
from microecon.agent import create_agent

pytestmark = pytest.mark.core


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

    def test_chebyshev_distance(self):
        """Grid.chebyshev_distance should compute Chebyshev metric."""
        grid = Grid(10)

        p1 = Position(0, 0)
        p2 = Position(3, 5)

        # Chebyshev = max(|3-0|, |5-0|) = 5
        assert grid.chebyshev_distance(p1, p2) == 5

    def test_wrapped_chebyshev_distance(self):
        """Chebyshev distance should account for wrapping on torus grid."""
        grid = Grid(10, wrap=True)

        p1 = Position(0, 0)
        p2 = Position(9, 9)

        # Without wrapping: max(9, 9) = 9
        # With wrapping: max(1, 1) = 1 (going the short way around)
        assert grid.chebyshev_distance(p1, p2) == 1

        # Another example: (0,0) to (8,2)
        p3 = Position(8, 2)
        # Without wrapping: max(8, 2) = 8
        # With wrapping: max(2, 2) = 2 (row wraps: 10-8=2)
        assert grid.chebyshev_distance(p1, p3) == 2

    def test_agents_within_radius_uses_chebyshev(self):
        """
        agents_within_radius should use Chebyshev distance for consistency
        with movement mechanics.

        This is a regression test for CE-4: previously used Euclidean distance,
        which created inconsistency with the Chebyshev-based movement model.
        """
        grid = Grid(10)
        center = Position(5, 5)

        agent1 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
        agent2 = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)

        # Place agent1 at (5,8): Chebyshev=3, Euclidean=3.0
        grid.place_agent(agent1, Position(5, 8))
        # Place agent2 at (8,8): Chebyshev=3, Euclidean≈4.24
        grid.place_agent(agent2, Position(8, 8))

        # With radius 3.0, both should be visible if using Chebyshev
        # With Euclidean, agent2 would be excluded (4.24 > 3.0)
        nearby = list(grid.agents_within_radius(center, 3.0))

        assert len(nearby) == 2, (
            "Both agents at Chebyshev distance 3 should be visible. "
            "If only 1 visible, distance metric may still be Euclidean."
        )

    def test_perception_movement_consistency(self):
        """
        An agent should be able to reach any visible target in at most
        perception_radius steps (using diagonal moves).

        This verifies that perception uses the same distance metric as movement.
        """
        grid = Grid(15)
        center = Position(7, 7)

        # Place agents at various positions
        positions = [
            Position(10, 10),  # Chebyshev=3
            Position(7, 12),   # Chebyshev=5
            Position(2, 4),    # Chebyshev=5
        ]

        agents = []
        for i, pos in enumerate(positions):
            agent = create_agent(alpha=0.5, endowment_x=1.0, endowment_y=1.0)
            grid.place_agent(agent, pos)
            agents.append(agent)

        # With radius 5, all should be visible
        nearby = list(grid.agents_within_radius(center, 5.0))
        assert len(nearby) == 3

        # The returned distance should equal Chebyshev distance
        for agent_id, pos, dist in nearby:
            expected_chebyshev = grid.chebyshev_distance(center, pos)
            assert dist == expected_chebyshev, (
                f"Returned distance {dist} != Chebyshev {expected_chebyshev}"
            )
