"""
Simulation engine for grid-based search and exchange.

The simulation runs in discrete ticks. Each tick:
1. Agents evaluate visible targets
2. Agents move toward best targets
3. Agents at same position may trade (Nash bargaining)

Reference: CLAUDE.md (First Milestone)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable
import random

from microecon.agent import Agent, create_agent
from microecon.grid import Grid, Position
from microecon.information import InformationEnvironment, FullInformation
from microecon.bargaining import execute_trade, BargainingOutcome
from microecon.search import compute_move_target, should_trade


@dataclass
class TradeEvent:
    """Record of a trade that occurred."""
    tick: int
    agent1_id: str
    agent2_id: str
    outcome: BargainingOutcome


@dataclass
class SimulationState:
    """
    Snapshot of simulation state at a point in time.

    Attributes:
        tick: Current tick number
        agents: List of agents
        positions: Map of agent ID to position
        trades: Trades that have occurred
    """
    tick: int
    agent_utilities: dict[str, float]
    agent_positions: dict[str, Position]
    total_trades: int


@dataclass
class Simulation:
    """
    Main simulation engine.

    Coordinates agent search, movement, and exchange on the grid.

    Attributes:
        grid: The spatial grid
        agents: All agents in the simulation
        info_env: Information environment
        tick: Current tick number
        trades: History of trades
    """
    grid: Grid
    info_env: InformationEnvironment = field(default_factory=FullInformation)
    agents: list[Agent] = field(default_factory=list)
    tick: int = 0
    trades: list[TradeEvent] = field(default_factory=list)
    _agents_by_id: dict[str, Agent] = field(default_factory=dict, repr=False)

    def add_agent(self, agent: Agent, position: Position) -> None:
        """Add an agent to the simulation at the given position."""
        self.agents.append(agent)
        self._agents_by_id[agent.id] = agent
        self.grid.place_agent(agent, position)

    def add_agent_random(self, agent: Agent) -> Position:
        """Add an agent at a random position on the grid."""
        pos = Position(
            random.randint(0, self.grid.size - 1),
            random.randint(0, self.grid.size - 1),
        )
        self.add_agent(agent, pos)
        return pos

    def remove_agent(self, agent: Agent) -> None:
        """Remove an agent from the simulation."""
        self.agents.remove(agent)
        del self._agents_by_id[agent.id]
        self.grid.remove_agent(agent)

    def step(self) -> list[TradeEvent]:
        """
        Execute one simulation tick.

        Returns:
            List of trades that occurred this tick
        """
        self.tick += 1
        tick_trades = []

        # Phase 1: Determine movement for all agents and store old positions
        move_targets: dict[str, Optional[Position]] = {}
        old_positions: dict[str, Position] = {}
        for agent in self.agents:
            old_positions[agent.id] = self.grid.get_position(agent)
            target = compute_move_target(
                agent, self.grid, self.info_env, self._agents_by_id
            )
            move_targets[agent.id] = target

        # Phase 2: Execute movement (simultaneous)
        for agent in self.agents:
            target = move_targets.get(agent.id)
            if target is not None:
                self.grid.move_toward(agent, target, steps=agent.movement_budget)

        # Phase 2.5: Detect crossing paths - if two agents swapped positions or
        # crossed through each other, place them at the same position (meeting)
        new_positions: dict[str, Position] = {
            a.id: self.grid.get_position(a) for a in self.agents
        }
        for i, agent1 in enumerate(self.agents):
            for agent2 in self.agents[i+1:]:
                old1, old2 = old_positions.get(agent1.id), old_positions.get(agent2.id)
                new1, new2 = new_positions.get(agent1.id), new_positions.get(agent2.id)

                if old1 is None or old2 is None or new1 is None or new2 is None:
                    continue

                # Check if they crossed paths (swapped positions or crossed through)
                crossed = (old1 == new2 and old2 == new1)
                # Also check if they're now adjacent but were moving toward each other
                adjacent = new1.chebyshev_distance_to(new2) == 1
                moving_toward = (
                    move_targets.get(agent1.id) == old2 and
                    move_targets.get(agent2.id) == old1
                )

                if crossed or (adjacent and moving_toward):
                    # Place both at the midpoint (agent1's new position)
                    self.grid.move_agent(agent2, new1)
                    new_positions[agent2.id] = new1

        # Phase 3: Execute trades for agents at same position
        # Track which agents have traded this tick to avoid double-trading
        traded_this_tick: set[str] = set()

        for agent in self.agents:
            if agent.id in traded_this_tick:
                continue

            # Find other agents at same position
            others = self.grid.agents_at_same_position(agent)
            others = {oid for oid in others if oid not in traded_this_tick}

            if not others:
                continue

            # Trade with first available partner
            for other_id in others:
                other = self._agents_by_id.get(other_id)
                if other is None:
                    continue

                if should_trade(agent, other, self.info_env):
                    outcome = execute_trade(agent, other)
                    if outcome.trade_occurred:
                        event = TradeEvent(
                            tick=self.tick,
                            agent1_id=agent.id,
                            agent2_id=other.id,
                            outcome=outcome,
                        )
                        tick_trades.append(event)
                        self.trades.append(event)
                        traded_this_tick.add(agent.id)
                        traded_this_tick.add(other.id)
                        break  # Agent can only trade once per tick

        return tick_trades

    def run(self, ticks: int, callback: Optional[Callable[[int, list[TradeEvent]], None]] = None) -> None:
        """
        Run the simulation for a number of ticks.

        Args:
            ticks: Number of ticks to run
            callback: Optional function called after each tick with (tick_number, trades)
        """
        for _ in range(ticks):
            tick_trades = self.step()
            if callback:
                callback(self.tick, tick_trades)

    def get_state(self) -> SimulationState:
        """Get a snapshot of current simulation state."""
        return SimulationState(
            tick=self.tick,
            agent_utilities={a.id: a.utility() for a in self.agents},
            agent_positions={
                a.id: pos
                for a in self.agents
                if (pos := self.grid.get_position(a)) is not None
            },
            total_trades=len(self.trades),
        )

    def total_welfare(self) -> float:
        """Compute sum of all agent utilities."""
        return sum(agent.utility() for agent in self.agents)

    def welfare_gains(self) -> float:
        """Compute total gains from trade (sum of all trade surpluses)."""
        return sum(
            trade.outcome.gains_1 + trade.outcome.gains_2
            for trade in self.trades
        )


def create_simple_economy(
    n_agents: int,
    grid_size: int = 10,
    perception_radius: float = 7.0,
    discount_factor: float = 0.95,
    seed: Optional[int] = None,
) -> Simulation:
    """
    Create a simple economy with heterogeneous agents.

    Creates agents with:
    - Varied preference parameters (alpha uniformly distributed)
    - Complementary endowments (half have more x, half have more y)

    This setup guarantees gains from trade between agents with
    different preferences.

    Args:
        n_agents: Number of agents
        grid_size: Size of the grid
        perception_radius: How far agents can see
        discount_factor: Time preference
        seed: Random seed for reproducibility

    Returns:
        Configured Simulation ready to run
    """
    if seed is not None:
        random.seed(seed)

    sim = Simulation(
        grid=Grid(grid_size),
        info_env=FullInformation(),
    )

    for i in range(n_agents):
        # Vary preference parameter
        alpha = 0.2 + 0.6 * (i / max(1, n_agents - 1))

        # Complementary endowments: some have more x, some have more y
        if i % 2 == 0:
            endowment_x, endowment_y = 10.0, 2.0
        else:
            endowment_x, endowment_y = 2.0, 10.0

        agent = create_agent(
            alpha=alpha,
            endowment_x=endowment_x,
            endowment_y=endowment_y,
            perception_radius=perception_radius,
            discount_factor=discount_factor,
        )

        sim.add_agent_random(agent)

    return sim
