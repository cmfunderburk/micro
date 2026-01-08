"""Simulation manager for the backend.

Manages a single simulation instance per backend process.
Handles creation, stepping, and state retrieval.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

from microecon.simulation import Simulation, create_simple_economy, TradeEvent
from microecon.bargaining import NashBargainingProtocol, RubinsteinBargainingProtocol
from microecon.matching import OpportunisticMatchingProtocol, StableRoommatesMatchingProtocol
from microecon.logging import SimulationLogger
from microecon.logging.events import TickRecord, AgentSnapshot


@dataclass
class SimulationConfig:
    """Configuration for creating a simulation."""

    n_agents: int = 10
    grid_size: int = 15
    perception_radius: float = 7.0
    discount_factor: float = 0.95
    seed: int | None = None
    bargaining_protocol: str = "nash"  # "nash" or "rubinstein"
    matching_protocol: str = "opportunistic"  # "opportunistic" or "stable_roommates"
    use_beliefs: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_agents": self.n_agents,
            "grid_size": self.grid_size,
            "perception_radius": self.perception_radius,
            "discount_factor": self.discount_factor,
            "seed": self.seed,
            "bargaining_protocol": self.bargaining_protocol,
            "matching_protocol": self.matching_protocol,
            "use_beliefs": self.use_beliefs,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SimulationConfig:
        return cls(
            n_agents=d.get("n_agents", 10),
            grid_size=d.get("grid_size", 15),
            perception_radius=d.get("perception_radius", 7.0),
            discount_factor=d.get("discount_factor", 0.95),
            seed=d.get("seed"),
            bargaining_protocol=d.get("bargaining_protocol", "nash"),
            matching_protocol=d.get("matching_protocol", "opportunistic"),
            use_beliefs=d.get("use_beliefs", False),
        )


@dataclass
class SimulationManager:
    """Manages a single simulation instance.

    This is a singleton-like manager that holds the current simulation state.
    Only one simulation runs at a time per backend instance (ADR-WEB-005).
    """

    simulation: Simulation | None = None
    config: SimulationConfig = field(default_factory=SimulationConfig)
    running: bool = False
    speed: float = 1.0  # Ticks per second
    tick_callbacks: list[Callable[[dict[str, Any]], None]] = field(default_factory=list)
    _run_task: asyncio.Task | None = field(default=None, repr=False)
    _initial_welfare: float = 0.0

    def create_simulation(self, config: SimulationConfig | None = None) -> None:
        """Create a new simulation with the given configuration."""
        if config is not None:
            self.config = config

        # Select bargaining protocol
        if self.config.bargaining_protocol == "rubinstein":
            bargaining = RubinsteinBargainingProtocol()
        else:
            bargaining = NashBargainingProtocol()

        # Select matching protocol
        if self.config.matching_protocol == "stable_roommates":
            matching = StableRoommatesMatchingProtocol()
        else:
            matching = OpportunisticMatchingProtocol()

        self.simulation = create_simple_economy(
            n_agents=self.config.n_agents,
            grid_size=self.config.grid_size,
            perception_radius=self.config.perception_radius,
            discount_factor=self.config.discount_factor,
            seed=self.config.seed,
            bargaining_protocol=bargaining,
            matching_protocol=matching,
            use_beliefs=self.config.use_beliefs,
        )
        self._initial_welfare = self.simulation.total_welfare()
        self.running = False

    def reset(self) -> None:
        """Reset the simulation to initial state with same config."""
        self.stop()
        self.create_simulation()

    def step(self) -> list[TradeEvent]:
        """Execute a single simulation tick."""
        if self.simulation is None:
            self.create_simulation()
        return self.simulation.step()

    def start(self) -> None:
        """Start continuous simulation."""
        if self.simulation is None:
            self.create_simulation()
        self.running = True

    def stop(self) -> None:
        """Stop continuous simulation."""
        self.running = False
        if self._run_task is not None:
            self._run_task.cancel()
            self._run_task = None

    def set_speed(self, speed: float) -> None:
        """Set simulation speed (ticks per second)."""
        self.speed = max(0.1, min(speed, 60.0))  # Clamp to reasonable range

    def get_tick_data(self) -> dict[str, Any]:
        """Get current tick data for WebSocket streaming."""
        if self.simulation is None:
            return {"tick": 0, "agents": [], "trades": [], "metrics": {}, "beliefs": {}}

        sim = self.simulation
        agents = []
        beliefs: dict[str, Any] = {}  # agent_id -> belief data

        for agent in sim.agents:
            pos = sim.grid.get_position(agent)
            if pos is not None:
                agent_data = {
                    "id": agent.id,
                    "position": [pos.row, pos.col],
                    "endowment": [agent.endowment.x, agent.endowment.y],
                    "alpha": agent.preferences.alpha,
                    "utility": agent.utility(),
                    "perception_radius": agent.perception_radius,
                    "discount_factor": agent.discount_factor,
                    "has_beliefs": agent.has_beliefs,
                }
                agents.append(agent_data)

                # Include belief data if agent has beliefs
                if agent.has_beliefs and agent.type_beliefs is not None:
                    type_beliefs = []
                    for target_id, tb in agent.type_beliefs.items():
                        type_beliefs.append({
                            "target_id": target_id,
                            "believed_alpha": tb.believed_alpha,
                            "confidence": tb.confidence,
                            "n_interactions": tb.n_interactions,
                        })

                    price_belief = None
                    if agent.price_belief is not None:
                        price_belief = {
                            "mean": agent.price_belief.mean,
                            "variance": agent.price_belief.variance,
                            "n_observations": agent.price_belief.n_observations,
                        }

                    beliefs[agent.id] = {
                        "type_beliefs": type_beliefs,
                        "price_belief": price_belief,
                        "n_trades_in_memory": agent.memory.n_trades() if agent.memory else 0,
                    }

        # Get recent trades (this tick)
        trades = []
        # Build agent lookup for alpha values
        agent_by_id = {a.id: a for a in sim.agents}
        for trade in sim.trades:
            if trade.tick == sim.tick:
                agent1 = agent_by_id.get(trade.agent1_id)
                agent2 = agent_by_id.get(trade.agent2_id)
                alpha1 = agent1.preferences.alpha if agent1 else 0.5
                alpha2 = agent2.preferences.alpha if agent2 else 0.5
                trades.append({
                    "tick": trade.tick,
                    "agent1_id": trade.agent1_id,
                    "agent2_id": trade.agent2_id,
                    "alpha1": alpha1,
                    "alpha2": alpha2,
                    "pre_endowment_1": list(trade.pre_endowment_1),
                    "pre_endowment_2": list(trade.pre_endowment_2),
                    "post_allocation_1": [trade.outcome.allocation_1.x, trade.outcome.allocation_1.y],
                    "post_allocation_2": [trade.outcome.allocation_2.x, trade.outcome.allocation_2.y],
                    "gains": [trade.outcome.gains_1, trade.outcome.gains_2],
                })

        return {
            "tick": sim.tick,
            "agents": agents,
            "trades": trades,
            "metrics": {
                "total_welfare": sim.total_welfare(),
                "welfare_gains": sim.total_welfare() - self._initial_welfare,
                "cumulative_trades": len(sim.trades),
            },
            "config": {
                "grid_size": sim.grid.size,
            },
            "beliefs": beliefs,
        }

    def get_state(self) -> dict[str, Any]:
        """Get full simulation state."""
        return {
            "running": self.running,
            "speed": self.speed,
            "config": self.config.to_dict(),
            "tick_data": self.get_tick_data(),
        }


# Global simulation manager instance
manager = SimulationManager()
