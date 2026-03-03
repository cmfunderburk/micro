"""Simulation manager for the backend.

Manages simulation instances per backend process.
Supports multiple simulations for comparison mode.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from microecon.logging.events import SimulationConfig as LoggingSimulationConfig
import uuid

from microecon.simulation import Simulation, create_simple_economy, TradeEvent
from microecon.bargaining import (
    NashBargainingProtocol,
    RubinsteinBargainingProtocol,
    TIOLIBargainingProtocol,
    AsymmetricNashBargainingProtocol,
)
# matching_protocol removed in 3-phase tick model rework - agents now use DecisionProcedure
from microecon.logging import SimulationLogger
from microecon.logging.events import TickRecord, AgentSnapshot


@dataclass
class AgentSpec:
    """Specification for a single agent in a scenario."""

    id: str
    position: tuple[int, int]
    alpha: float
    endowment: tuple[float, float]


@dataclass
class SimulationConfig:
    """Configuration for creating a simulation."""

    n_agents: int = 10
    grid_size: int = 15
    perception_radius: float = 7.0
    discount_factor: float = 0.95
    seed: int | None = None
    bargaining_protocol: str = "nash"  # "nash", "rubinstein", "tioli", "asymmetric_nash"
    # matching_protocol removed - agents now use DecisionProcedure in 3-phase tick model
    use_beliefs: bool = False
    # Bargaining power distribution (only used with asymmetric_nash)
    # Options: "uniform", "gaussian", "bimodal"
    bargaining_power_distribution: str = "uniform"
    # Information environment configuration
    info_env_name: str = "full"  # "full" or "noisy_alpha"
    info_env_params: dict[str, Any] = field(default_factory=dict)
    # Optional: specific agents for scenario mode (overrides n_agents if provided)
    agents: list[AgentSpec] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "n_agents": self.n_agents,
            "grid_size": self.grid_size,
            "perception_radius": self.perception_radius,
            "discount_factor": self.discount_factor,
            "seed": self.seed,
            "bargaining_protocol": self.bargaining_protocol,
            "use_beliefs": self.use_beliefs,
            "bargaining_power_distribution": self.bargaining_power_distribution,
            "info_env_name": self.info_env_name,
            "info_env_params": self.info_env_params,
        }
        if self.agents is not None:
            result["agents"] = [
                {
                    "id": a.id,
                    "position": list(a.position),
                    "alpha": a.alpha,
                    "endowment": list(a.endowment),
                }
                for a in self.agents
            ]
        return result

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SimulationConfig:
        agents = None
        if "agents" in d and d["agents"]:
            agents = [
                AgentSpec(
                    id=a["id"],
                    position=tuple(a["position"]),
                    alpha=a["alpha"],
                    endowment=tuple(a["endowment"]),
                )
                for a in d["agents"]
            ]
        return cls(
            n_agents=d.get("n_agents", 10),
            grid_size=d.get("grid_size", 15),
            perception_radius=d.get("perception_radius", 7.0),
            discount_factor=d.get("discount_factor", 0.95),
            seed=d.get("seed"),
            bargaining_protocol=d.get("bargaining_protocol", "nash"),
            use_beliefs=d.get("use_beliefs", False),
            bargaining_power_distribution=d.get("bargaining_power_distribution", "uniform"),
            info_env_name=d.get("info_env_name", "full"),
            info_env_params=d.get("info_env_params", {}),
            agents=agents,
        )

    def to_logging_config(self) -> "LoggingSimulationConfig":
        """Convert server config to logging config for run persistence.

        The server config captures user intent (what to create).
        The logging config captures what was created (for reproducibility).
        """
        from microecon.logging.events import SimulationConfig as LoggingSimulationConfig

        if self.seed is None:
            raise ValueError(
                "Cannot convert to logging config without a seed. "
                "Assign a seed before persisting."
            )

        return LoggingSimulationConfig(
            n_agents=self.n_agents,
            grid_size=self.grid_size,
            seed=self.seed,
            protocol_name=self.bargaining_protocol,
            perception_radius=self.perception_radius,
            discount_factor=self.discount_factor,
            info_env_name=self.info_env_name,
            info_env_params=self.info_env_params,
        )


@dataclass
class SimulationInstance:
    """A single simulation instance with its own config and state."""

    sim_id: str
    label: str
    simulation: Simulation
    config: SimulationConfig
    _initial_welfare: float = 0.0
    _prev_trade_count: int = 0

    def get_tick_data(self) -> dict[str, Any]:
        """Get current tick data for this simulation."""
        sim = self.simulation
        agents = []
        beliefs: dict[str, Any] = {}

        for agent in sim.agents:
            pos = sim.grid.get_position(agent)
            if pos is not None:
                # Get interaction state info for visualization
                interaction_state = agent.interaction_state
                state_info = {
                    "state": interaction_state.state.value,
                    "proposal_target": interaction_state.proposal_target,
                    "negotiation_partner": interaction_state.negotiation_partner,
                }
                agent_data = {
                    "id": agent.id,
                    "position": [pos.row, pos.col],
                    "endowment": [agent.holdings.x, agent.holdings.y],  # Use holdings for current state
                    "alpha": agent.preferences.alpha,
                    "utility": agent.utility(),
                    "perception_radius": agent.perception_radius,
                    "discount_factor": agent.discount_factor,
                    "bargaining_power": agent.bargaining_power,
                    "has_beliefs": agent.has_beliefs,
                    "interaction_state": state_info,  # New: expose agent state
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
        for trade in sim.trades[self._prev_trade_count:]:
            agent1 = agent_by_id.get(trade.agent1_id)
            agent2 = agent_by_id.get(trade.agent2_id)
            alpha1 = agent1.preferences.alpha if agent1 else 0.5
            alpha2 = agent2.preferences.alpha if agent2 else 0.5
            trades.append({
                "tick": sim.tick,
                "agent1_id": trade.agent1_id,
                "agent2_id": trade.agent2_id,
                "proposer_id": trade.proposer_id,
                "alpha1": alpha1,
                "alpha2": alpha2,
                "pre_holdings_1": list(trade.pre_holdings[0]),
                "pre_holdings_2": list(trade.pre_holdings[1]),
                "post_allocation_1": list(trade.post_allocations[0]),
                "post_allocation_2": list(trade.post_allocations[1]),
                "gains": list(trade.gains),
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


def _generate_bargaining_powers(
    n_agents: int,
    distribution: str,
    seed: int | None = None,
) -> list[float]:
    """Generate bargaining power values according to distribution.

    Args:
        n_agents: Number of agents
        distribution: One of "uniform", "gaussian", "bimodal"
        seed: Random seed for reproducibility

    Returns:
        List of bargaining power values (all positive)
    """
    import random

    rng = random.Random(seed)

    if distribution == "gaussian":
        # Gaussian: μ=1, σ=0.3, clipped to positive
        powers = [max(0.1, min(3.0, rng.gauss(1.0, 0.3))) for _ in range(n_agents)]
    elif distribution == "bimodal":
        # Bimodal: half at 0.5, half at 1.5
        powers = [0.5 if i < n_agents // 2 else 1.5 for i in range(n_agents)]
        rng.shuffle(powers)
    else:  # uniform (default)
        # Uniform: [0.5, 1.5]
        powers = [rng.uniform(0.5, 1.5) for _ in range(n_agents)]

    return powers


def _create_info_env(name: str, params: dict[str, Any]) -> "InformationEnvironment":
    """Create an InformationEnvironment from name and params."""
    from microecon.information import FullInformation, NoisyAlphaInformation

    if name == "noisy_alpha":
        return NoisyAlphaInformation(noise_std=params.get("noise_std", 0.1))
    return FullInformation()


def _create_simulation_from_config(config: SimulationConfig) -> Simulation:
    """Create a Simulation from a SimulationConfig."""
    from microecon.grid import Grid, Position
    from microecon.agent import Agent, AgentPrivateState
    from microecon.preferences import CobbDouglas
    from microecon.bundle import Bundle

    # Select bargaining protocol
    if config.bargaining_protocol == "rubinstein":
        bargaining = RubinsteinBargainingProtocol()
    elif config.bargaining_protocol == "tioli":
        bargaining = TIOLIBargainingProtocol()
    elif config.bargaining_protocol == "asymmetric_nash":
        bargaining = AsymmetricNashBargainingProtocol()
    else:  # "nash" or default
        bargaining = NashBargainingProtocol()

    # matching_protocol removed - agents now use DecisionProcedure in 3-phase tick model

    # Generate bargaining powers if using asymmetric_nash
    bargaining_powers = None
    if config.bargaining_protocol == "asymmetric_nash":
        bargaining_powers = _generate_bargaining_powers(
            config.n_agents,
            config.bargaining_power_distribution,
            config.seed,
        )

    # Create the configured information environment
    info_env = _create_info_env(config.info_env_name, config.info_env_params)

    # If agents are specified (scenario mode), use them directly
    if config.agents is not None:
        grid = Grid(config.grid_size)
        sim = Simulation(
            grid=grid,
            info_env=info_env,
            bargaining_protocol=bargaining,
        )

        for i, agent_spec in enumerate(config.agents):
            private_state = AgentPrivateState(
                preferences=CobbDouglas(agent_spec.alpha),
                endowment=Bundle(agent_spec.endowment[0], agent_spec.endowment[1]),
            )
            # Assign bargaining power if available
            bp = bargaining_powers[i] if bargaining_powers and i < len(bargaining_powers) else 1.0
            agent = Agent(
                id=agent_spec.id,
                private_state=private_state,
                perception_radius=config.perception_radius,
                discount_factor=config.discount_factor,
                bargaining_power=bp,
            )
            if config.use_beliefs:
                agent.enable_beliefs()
            pos = Position(agent_spec.position[0], agent_spec.position[1])
            sim.add_agent(agent, pos)

        return sim

    # Otherwise use create_simple_economy for random agents
    sim = create_simple_economy(
        n_agents=config.n_agents,
        grid_size=config.grid_size,
        perception_radius=config.perception_radius,
        discount_factor=config.discount_factor,
        seed=config.seed,
        bargaining_protocol=bargaining,
        use_beliefs=config.use_beliefs,
        info_env=info_env,
    )

    # Assign bargaining powers if using asymmetric_nash
    if bargaining_powers:
        for i, agent in enumerate(sim.agents):
            if i < len(bargaining_powers):
                agent.bargaining_power = bargaining_powers[i]

    return sim


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
    _prev_trade_count: int = 0

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
                inst._prev_trade_count = len(inst.simulation.trades)
                trades = inst.simulation.step()
                all_trades.extend(trades)
            return all_trades
        else:
            if self.simulation is None:
                self.create_simulation()
            self._prev_trade_count = len(self.simulation.trades)
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
                # Get interaction state info for visualization
                interaction_state = agent.interaction_state
                state_info = {
                    "state": interaction_state.state.value,
                    "proposal_target": interaction_state.proposal_target,
                    "negotiation_partner": interaction_state.negotiation_partner,
                }
                agent_data = {
                    "id": agent.id,
                    "position": [pos.row, pos.col],
                    "endowment": [agent.holdings.x, agent.holdings.y],  # Use holdings for current state
                    "alpha": agent.preferences.alpha,
                    "utility": agent.utility(),
                    "perception_radius": agent.perception_radius,
                    "discount_factor": agent.discount_factor,
                    "bargaining_power": agent.bargaining_power,
                    "has_beliefs": agent.has_beliefs,
                    "interaction_state": state_info,  # New: expose agent state
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
        for trade in sim.trades[self._prev_trade_count:]:
            agent1 = agent_by_id.get(trade.agent1_id)
            agent2 = agent_by_id.get(trade.agent2_id)
            alpha1 = agent1.preferences.alpha if agent1 else 0.5
            alpha2 = agent2.preferences.alpha if agent2 else 0.5
            trades.append({
                "tick": sim.tick,
                "agent1_id": trade.agent1_id,
                "agent2_id": trade.agent2_id,
                "proposer_id": trade.proposer_id,
                "alpha1": alpha1,
                "alpha2": alpha2,
                "pre_holdings_1": list(trade.pre_holdings[0]),
                "pre_holdings_2": list(trade.pre_holdings[1]),
                "post_allocation_1": list(trade.post_allocations[0]),
                "post_allocation_2": list(trade.post_allocations[1]),
                "gains": list(trade.gains),
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
