"""
Grid representation for spatial search and matching.

The NxN grid provides spatial grounding for:
- Search costs (distance = time to reach partner)
- Information structure (perception radius)
- Meeting mechanics (agents must be at same position to trade)

Reference: CLAUDE.md (First Milestone), VISION.md (The Grid and Spatial Grounding)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Iterator
import math

from microecon.agent import Agent


@dataclass(frozen=True)
class Position:
    """
    A position on the grid.

    Uses integer coordinates for discrete grid positions.
    Position (0, 0) is the top-left corner.
    """
    row: int
    col: int

    def distance_to(self, other: Position) -> float:
        """
        Compute Euclidean distance to another position.

        This is the relevant metric for search costs and perception.
        """
        return math.sqrt((self.row - other.row) ** 2 + (self.col - other.col) ** 2)

    def manhattan_distance_to(self, other: Position) -> int:
        """
        Compute Manhattan distance to another position.

        This is relevant for movement budget (if diagonal moves cost same as cardinal).
        """
        return abs(self.row - other.row) + abs(self.col - other.col)

    def chebyshev_distance_to(self, other: Position, grid_size: int | None = None) -> int:
        """
        Compute Chebyshev distance (max of absolute differences).

        This is the number of moves needed if diagonal moves are allowed.

        Args:
            other: Target position
            grid_size: If provided, compute wrapped distance on a torus of this size

        Returns:
            Number of diagonal moves needed to reach other position
        """
        dr = abs(self.row - other.row)
        dc = abs(self.col - other.col)

        if grid_size is not None:
            # Consider wraparound
            dr = min(dr, grid_size - dr)
            dc = min(dc, grid_size - dc)

        return max(dr, dc)

    def neighbors(self, include_diagonal: bool = True) -> list[Position]:
        """
        Get adjacent positions.

        Args:
            include_diagonal: If True, include 8-connected neighbors;
                            if False, only 4-connected (cardinal directions)

        Returns:
            List of neighboring positions (may be outside grid bounds)
        """
        cardinal = [
            Position(self.row - 1, self.col),  # up
            Position(self.row + 1, self.col),  # down
            Position(self.row, self.col - 1),  # left
            Position(self.row, self.col + 1),  # right
        ]
        if not include_diagonal:
            return cardinal

        diagonal = [
            Position(self.row - 1, self.col - 1),
            Position(self.row - 1, self.col + 1),
            Position(self.row + 1, self.col - 1),
            Position(self.row + 1, self.col + 1),
        ]
        return cardinal + diagonal

    def step_toward(self, target: Position) -> Position:
        """
        Take one step toward target position.

        Returns the adjacent position that minimizes distance to target.
        Allows diagonal movement (Chebyshev metric).
        """
        if self == target:
            return self

        dr = 0 if target.row == self.row else (1 if target.row > self.row else -1)
        dc = 0 if target.col == self.col else (1 if target.col > self.col else -1)

        return Position(self.row + dr, self.col + dc)


@dataclass
class Grid:
    """
    An NxN grid for agent positioning and movement.

    The grid maintains:
    - Agent positions
    - Boundary enforcement
    - Spatial queries (who is within radius)

    Attributes:
        size: Grid dimension (size x size)
        wrap: If True, grid wraps around (torus topology); if False, bounded
    """
    size: int
    wrap: bool = False
    _positions: dict[str, Position] = field(default_factory=dict)
    _occupancy: dict[Position, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError(f"Grid size must be positive, got {self.size}")

    def place_agent(self, agent: Agent, position: Position) -> None:
        """
        Place an agent at a position on the grid.

        Args:
            agent: Agent to place
            position: Where to place them

        Raises:
            ValueError: If position is out of bounds (and wrap=False)
        """
        position = self._normalize_position(position)
        self._validate_position(position)

        # Remove from old position if already placed
        if agent.id in self._positions:
            self.remove_agent(agent)

        self._positions[agent.id] = position
        if position not in self._occupancy:
            self._occupancy[position] = set()
        self._occupancy[position].add(agent.id)

    def remove_agent(self, agent: Agent) -> None:
        """Remove an agent from the grid."""
        if agent.id not in self._positions:
            return

        old_pos = self._positions[agent.id]
        del self._positions[agent.id]
        self._occupancy[old_pos].discard(agent.id)
        if not self._occupancy[old_pos]:
            del self._occupancy[old_pos]

    def get_position(self, agent: Agent) -> Optional[Position]:
        """Get an agent's current position, or None if not on grid."""
        return self._positions.get(agent.id)

    def agents_at(self, position: Position) -> set[str]:
        """Get IDs of agents at a position."""
        position = self._normalize_position(position)
        return self._occupancy.get(position, set()).copy()

    def move_agent(self, agent: Agent, new_position: Position) -> None:
        """
        Move an agent to a new position.

        Args:
            agent: Agent to move
            new_position: Target position
        """
        self.place_agent(agent, new_position)

    def move_toward(self, agent: Agent, target: Position, steps: int = 1) -> Position:
        """
        Move agent toward target position.

        Args:
            agent: Agent to move
            target: Position to move toward
            steps: Number of steps to take (up to agent's movement budget)

        Returns:
            The new position after moving
        """
        current = self.get_position(agent)
        if current is None:
            raise ValueError(f"Agent {agent.id} is not on the grid")

        target = self._normalize_position(target)
        new_pos = current
        for _ in range(steps):
            if new_pos == target:
                break
            new_pos = new_pos.step_toward(target)
            new_pos = self._normalize_position(new_pos)

        self.move_agent(agent, new_pos)
        return new_pos

    def agents_within_radius(
        self,
        center: Position,
        radius: float,
        exclude_center: bool = True,
    ) -> Iterator[tuple[str, Position, float]]:
        """
        Find all agents within radius of center position.

        Uses Chebyshev distance (diagonal moves allowed) for consistency with
        movement mechanics. This means perception area is square, not circular.

        Args:
            center: Center position for search
            radius: Maximum Chebyshev distance (number of diagonal moves)
            exclude_center: If True, exclude agents at the exact center position

        Yields:
            Tuples of (agent_id, position, chebyshev_distance)
        """
        # For efficiency on large grids, we could use spatial indexing.
        # For now, iterate all agents (fine for small simulations).
        for agent_id, pos in self._positions.items():
            if exclude_center and pos == center:
                continue

            dist = self.chebyshev_distance(center, pos)
            if dist <= radius:
                yield (agent_id, pos, float(dist))

    def agents_at_same_position(self, agent: Agent) -> set[str]:
        """
        Get IDs of other agents at the same position as agent.

        Returns:
            Set of agent IDs (excluding the querying agent)
        """
        pos = self.get_position(agent)
        if pos is None:
            return set()

        others = self.agents_at(pos)
        others.discard(agent.id)
        return others

    def agents_adjacent_to(self, agent: Agent, include_same_position: bool = True) -> set[str]:
        """
        Get IDs of agents adjacent to (or at same position as) agent.

        Uses Chebyshev distance <= 1, meaning 8-connected neighbors plus
        optionally the same position.

        Args:
            agent: The agent to find neighbors for
            include_same_position: If True, include agents at exact same position

        Returns:
            Set of agent IDs (excluding the querying agent)
        """
        pos = self.get_position(agent)
        if pos is None:
            return set()

        result: set[str] = set()

        # Check same position
        if include_same_position:
            result.update(self.agents_at(pos))

        # Check 8-connected neighbors
        for neighbor_pos in pos.neighbors(include_diagonal=True):
            # Normalize for wrapping grids
            neighbor_pos = self._normalize_position(neighbor_pos)
            # Skip out-of-bounds positions for non-wrapping grids
            if not self.wrap:
                if not (0 <= neighbor_pos.row < self.size and 0 <= neighbor_pos.col < self.size):
                    continue
            result.update(self.agents_at(neighbor_pos))

        result.discard(agent.id)
        return result

    def _normalize_position(self, position: Position) -> Position:
        """Normalize position for wrapping grid."""
        if not self.wrap:
            return position
        return Position(position.row % self.size, position.col % self.size)

    def _validate_position(self, position: Position) -> None:
        """Check position is in bounds (for non-wrapping grid)."""
        if self.wrap:
            return

        if not (0 <= position.row < self.size and 0 <= position.col < self.size):
            raise ValueError(
                f"Position {position} out of bounds for {self.size}x{self.size} grid"
            )

    def _wrapped_distance(self, p1: Position, p2: Position) -> float:
        """Compute Euclidean distance with wraparound (torus topology)."""
        dr = abs(p1.row - p2.row)
        dc = abs(p1.col - p2.col)

        # Consider wraparound
        dr = min(dr, self.size - dr)
        dc = min(dc, self.size - dc)

        return math.sqrt(dr ** 2 + dc ** 2)

    def chebyshev_distance(self, p1: Position, p2: Position) -> int:
        """Compute Chebyshev distance between two positions (respecting wrap setting)."""
        return p1.chebyshev_distance_to(p2, grid_size=self.size if self.wrap else None)

    def all_positions(self) -> Iterator[Position]:
        """Iterate over all grid positions."""
        for row in range(self.size):
            for col in range(self.size):
                yield Position(row, col)

    def distance(self, p1: Position, p2: Position) -> float:
        """Compute distance between two positions (respecting wrap setting)."""
        if self.wrap:
            return self._wrapped_distance(p1, p2)
        return p1.distance_to(p2)
