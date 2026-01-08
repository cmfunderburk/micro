"""Simulation manager for the backend.

Manages simulation instances per backend process.
Supports multiple simulations for comparison mode.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable
import uuid

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
class SimulationInstance:
    """A single simulation instance with its own config and state."""

    sim_id: str
    label: str
    simulation: Simulation
    config: SimulationConfig
    _initial_welfare: float = 0.0

    def get_tick_data(self) -> dict[str, Any]:
        """Get current tick data for this simulation."""
        sim = self.simulation
        agents = []
        beliefs: dict[str, Any] = {}

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

        trades = []
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
            "sim_id": self.sim_id,
            "label": self.label,
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


def _create_simulation_from_config(config: SimulationConfig) -> Simulation:
    """Create a Simulation from a SimulationConfig."""
    if config.bargaining_protocol == "rubinstein":
        bargaining = RubinsteinBargainingProtocol()
    else:
        bargaining = NashBargainingProtocol()

    if config.matching_protocol == "stable_roommates":
        matching = StableRoommatesMatchingProtocol()
    else:
        matching = OpportunisticMatchingProtocol()

    return create_simple_economy(
        n_agents=config.n_agents,
        grid_size=config.grid_size,
        perception_radius=config.perception_radius,
        discount_factor=config.discount_factor,
        seed=config.seed,
        bargaining_protocol=bargaining,
        matching_protocol=matching,
        use_beliefs=config.use_beliefs,
    )


@dataclass
class SimulationManager:
    """Manages simulation instances.

    Supports both single simulation mode (backward compatible) and
    comparison mode with multiple named simulations.
    """

    simulation: Simulation | None = None
    config: SimulationConfig = field(default_factory=SimulationConfig)
    running: bool = False
    speed: float = 1.0  # Ticks per second
    tick_callbacks: list[Callable[[dict[str, Any]], None]] = field(default_factory=list)
    _run_task: asyncio.Task | None = field(default=None, repr=False)
    _initial_welfare: float = 0.0

    # Multi-simulation support for comparison mode
    _simulations: dict[str, SimulationInstance] = field(default_factory=dict)
    comparison_mode: bool = False

    def create_simulation(self, config: SimulationConfig | None = None) -> None:
        """Create a new simulation with the given configuration."""
        if config is not None:
            self.config = config

        self.simulation = _create_simulation_from_config(self.config)
        self._initial_welfare = self.simulation.total_welfare()
        self.running = False

    def create_comparison(
        self,
        config1: SimulationConfig,
        config2: SimulationConfig,
        label1: str = "A",
        label2: str = "B",
    ) -> tuple[str, str]:
        """Create two simulations for comparison mode.

        Both simulations should use the same seed for fair comparison.
        Returns the sim_ids for the two simulations.
        """
        self.comparison_mode = True
        self._simulations.clear()

        sim_id1 = str(uuid.uuid4())[:8]
        sim1 = _create_simulation_from_config(config1)
        self._simulations[sim_id1] = SimulationInstance(
            sim_id=sim_id1,
            label=label1,
            simulation=sim1,
            config=config1,
            _initial_welfare=sim1.total_welfare(),
        )

        sim_id2 = str(uuid.uuid4())[:8]
        sim2 = _create_simulation_from_config(config2)
        self._simulations[sim_id2] = SimulationInstance(
            sim_id=sim_id2,
            label=label2,
            simulation=sim2,
            config=config2,
            _initial_welfare=sim2.total_welfare(),
        )

        return sim_id1, sim_id2

    def exit_comparison(self) -> None:
        """Exit comparison mode and return to single simulation."""
        self.comparison_mode = False
        self._simulations.clear()

    def get_comparison_simulations(self) -> list[SimulationInstance]:
        """Get all simulations in comparison mode."""
        return list(self._simulations.values())

    def reset(self) -> None:
        """Reset the simulation to initial state with same config."""
        self.stop()
        if self.comparison_mode:
            # Reset all comparison simulations
            for inst in self._simulations.values():
                inst.simulation = _create_simulation_from_config(inst.config)
                inst._initial_welfare = inst.simulation.total_welfare()
        else:
            self.create_simulation()

    def step(self) -> list[TradeEvent]:
        """Execute a single simulation tick."""
        if self.comparison_mode:
            all_trades = []
            for inst in self._simulations.values():
                trades = inst.simulation.step()
                all_trades.extend(trades)
            return all_trades
        else:
            if self.simulation is None:
                self.create_simulation()
            return self.simulation.step()

    def start(self) -> None:
        """Start continuous simulation."""
        if not self.comparison_mode and self.simulation is None:
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

    def get_comparison_tick_data(self) -> dict[str, Any]:
        """Get tick data for all simulations in comparison mode."""
        if not self.comparison_mode:
            return {"comparison_mode": False, "simulations": []}

        return {
            "comparison_mode": True,
            "simulations": [inst.get_tick_data() for inst in self._simulations.values()],
        }

    def get_state(self) -> dict[str, Any]:
        """Get full simulation state."""
        if self.comparison_mode:
            return {
                "running": self.running,
                "speed": self.speed,
                "comparison_mode": True,
                "simulations": [
                    {
                        "sim_id": inst.sim_id,
                        "label": inst.label,
                        "config": inst.config.to_dict(),
                        "tick_data": inst.get_tick_data(),
                    }
                    for inst in self._simulations.values()
                ],
            }
        return {
            "running": self.running,
            "speed": self.speed,
            "comparison_mode": False,
            "config": self.config.to_dict(),
            "tick_data": self.get_tick_data(),
        }


# Global simulation manager instance
manager = SimulationManager()
