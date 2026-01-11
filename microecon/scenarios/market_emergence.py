"""Market emergence demonstration scenario.

Creates a 50-100 agent scenario demonstrating:
- Emergence of trading patterns from bilateral exchange
- Spatial clustering around trading opportunities
- Welfare improvement through trade
- Comparison across different institutional rules (protocols)

This scenario is the key demonstration of the platform's core value proposition:
making institutions visible through comparative simulation.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional

from microecon.agent import create_agent, Agent
from microecon.grid import Grid, Position
from microecon.simulation import Simulation
from microecon.information import FullInformation, NoisyAlphaInformation, InformationEnvironment
from microecon.bargaining import (
    NashBargainingProtocol,
    RubinsteinBargainingProtocol,
    BargainingProtocol,
)
from microecon.matching import (
    OpportunisticMatchingProtocol,
    MatchingProtocol,
)
from microecon.logging import SimulationLogger, SimulationConfig
from microecon.analysis.emergence import analyze_market_emergence, MarketEmergenceReport


@dataclass
class MarketEmergenceConfig:
    """Configuration for market emergence scenario.

    Attributes:
        n_agents: Number of agents (50-100 recommended)
        grid_size: Size of the NxN grid (suggested: n_agents // 2 to n_agents)
        perception_radius: How far agents can see (affects search)
        seed: Random seed for reproducibility
        ticks: Number of simulation ticks to run
        alpha_range: Range of preference parameters (min, max)
        endowment_types: List of endowment profiles ('x_rich', 'y_rich', 'balanced')
    """
    n_agents: int = 64
    grid_size: int = 32
    perception_radius: float = 5.0
    seed: int = 42
    ticks: int = 200
    alpha_range: tuple[float, float] = (0.2, 0.8)
    endowment_types: tuple[str, ...] = ('x_rich', 'y_rich')

    # Valid endowment type names
    VALID_ENDOWMENT_TYPES = frozenset({'x_rich', 'y_rich', 'balanced'})

    def __post_init__(self) -> None:
        if self.n_agents < 2:
            raise ValueError(f"n_agents must be >= 2, got {self.n_agents}")
        if self.grid_size < 5:
            raise ValueError(f"grid_size must be >= 5, got {self.grid_size}")
        if not (0 < self.alpha_range[0] < self.alpha_range[1] < 1):
            raise ValueError(f"alpha_range must be (a, b) with 0 < a < b < 1")
        # Validate endowment types (LA-4)
        if not self.endowment_types:
            raise ValueError("endowment_types cannot be empty")
        invalid = set(self.endowment_types) - self.VALID_ENDOWMENT_TYPES
        if invalid:
            raise ValueError(
                f"Unknown endowment_types: {invalid}. "
                f"Valid types: {sorted(self.VALID_ENDOWMENT_TYPES)}"
            )


@dataclass
class MarketEmergenceResult:
    """Result of a market emergence simulation run.

    Contains the logged run data and analysis report.
    """
    config: MarketEmergenceConfig
    protocol_name: str
    matching_name: str
    run_data: any  # RunData from logging
    analysis: MarketEmergenceReport


def create_heterogeneous_agents(
    config: MarketEmergenceConfig,
    rng: random.Random,
) -> list[Agent]:
    """Create agents with heterogeneous preferences and endowments.

    Design principles:
    - Preferences (alpha) uniformly distributed in specified range
    - Endowments create complementarity: some agents x-rich, others y-rich
    - Total endowment roughly equal per agent (different composition)

    Returns:
        List of agents with varied preferences and endowments
    """
    agents = []
    alpha_min, alpha_max = config.alpha_range
    endowment_types = config.endowment_types

    # Endowment profiles (total value roughly equal)
    profiles = {
        'x_rich': (12.0, 4.0),
        'y_rich': (4.0, 12.0),
        'balanced': (8.0, 8.0),
    }

    for i in range(config.n_agents):
        # Spread alpha uniformly across range
        alpha = alpha_min + (alpha_max - alpha_min) * (i / max(1, config.n_agents - 1))
        # Add small noise to avoid exact uniformity
        alpha += rng.gauss(0, 0.02)
        alpha = max(0.05, min(0.95, alpha))

        # Assign endowment type cyclically
        endow_type = endowment_types[i % len(endowment_types)]
        endow_x, endow_y = profiles[endow_type]
        # Add small variation
        endow_x *= (1 + rng.gauss(0, 0.05))
        endow_y *= (1 + rng.gauss(0, 0.05))

        agent = create_agent(
            alpha=alpha,
            endowment_x=max(0.1, endow_x),
            endowment_y=max(0.1, endow_y),
            perception_radius=config.perception_radius,
        )
        agents.append(agent)

    return agents


def place_agents_randomly(
    agents: list[Agent],
    grid: Grid,
    rng: random.Random,
) -> None:
    """Place agents at random positions on the grid.

    Uses scatter placement to avoid clustering at start.
    """
    positions_used: set[tuple[int, int]] = set()

    for agent in agents:
        # Find an unused position
        attempts = 0
        while attempts < 1000:
            row = rng.randint(0, grid.size - 1)
            col = rng.randint(0, grid.size - 1)
            if (row, col) not in positions_used:
                positions_used.add((row, col))
                grid.place_agent(agent, Position(row, col))
                break
            attempts += 1
        else:
            # Fallback: place even if occupied (simulation handles this)
            row = rng.randint(0, grid.size - 1)
            col = rng.randint(0, grid.size - 1)
            grid.place_agent(agent, Position(row, col))


def run_market_emergence(
    config: MarketEmergenceConfig,
    bargaining_protocol: Optional[BargainingProtocol] = None,
    matching_protocol: Optional[MatchingProtocol] = None,
    info_env: Optional[InformationEnvironment] = None,
) -> MarketEmergenceResult:
    """Run a market emergence simulation with specified protocols.

    This is the main entry point for the demonstration scenario.

    Args:
        config: Scenario configuration
        bargaining_protocol: Protocol for bargaining (default: Nash)
        matching_protocol: Protocol for matching (default: Opportunistic)
        info_env: Information environment (default: FullInformation)

    Returns:
        MarketEmergenceResult with run data and analysis
    """
    # Defaults
    if bargaining_protocol is None:
        bargaining_protocol = NashBargainingProtocol()
    if matching_protocol is None:
        matching_protocol = OpportunisticMatchingProtocol()
    if info_env is None:
        info_env = FullInformation()

    # Create RNG
    rng = random.Random(config.seed)

    # Create agents
    agents = create_heterogeneous_agents(config, rng)

    # Determine protocol names for logging
    protocol_name = type(bargaining_protocol).__name__.replace("Protocol", "").lower()
    matching_name = type(matching_protocol).__name__.replace("Protocol", "").lower()
    info_env_name = type(info_env).__name__.lower()

    # Get info_env params
    info_env_params: dict = {}
    if isinstance(info_env, NoisyAlphaInformation):
        info_env_params = {"noise_std": info_env.noise_std}

    # Create SimulationConfig for logging (LA-1: include institutional metadata)
    sim_config = SimulationConfig(
        n_agents=config.n_agents,
        grid_size=config.grid_size,
        seed=config.seed,
        protocol_name=protocol_name,
        perception_radius=config.perception_radius,
        matching_protocol_name=matching_name,
        info_env_name=info_env_name,
        info_env_params=info_env_params,
    )

    # Create logger
    logger = SimulationLogger(config=sim_config)

    # Create grid and simulation
    grid = Grid(size=config.grid_size)
    sim = Simulation(
        grid=grid,
        bargaining_protocol=bargaining_protocol,
        info_env=info_env,
        logger=logger,
    )

    # Place agents
    for agent in agents:
        # Get random position
        row = rng.randint(0, grid.size - 1)
        col = rng.randint(0, grid.size - 1)
        sim.add_agent(agent, Position(row, col))

    # Run simulation (logger captures ticks automatically)
    sim.run(ticks=config.ticks)

    # Get run data
    run_data = logger.finalize()

    # Analyze emergence
    analysis = analyze_market_emergence(run_data)

    return MarketEmergenceResult(
        config=config,
        protocol_name=protocol_name,
        matching_name=matching_name,
        run_data=run_data,
        analysis=analysis,
    )


def compare_protocols(
    config: MarketEmergenceConfig,
) -> dict[str, MarketEmergenceResult]:
    """Run market emergence under different institutional rules.

    This demonstrates the core value proposition: same initial conditions,
    different protocols, observe how institutions shape outcomes.

    Returns:
        Dict mapping protocol name to result
    """
    results = {}

    # Nash bargaining with opportunistic matching (baseline)
    results['nash_opportunistic'] = run_market_emergence(
        config,
        bargaining_protocol=NashBargainingProtocol(),
        matching_protocol=OpportunisticMatchingProtocol(),
    )

    # Rubinstein bargaining with opportunistic matching
    results['rubinstein_opportunistic'] = run_market_emergence(
        config,
        bargaining_protocol=RubinsteinBargainingProtocol(),
        matching_protocol=OpportunisticMatchingProtocol(),
    )

    return results


def print_emergence_summary(result: MarketEmergenceResult) -> None:
    """Print a summary of market emergence results."""
    a = result.analysis
    print(f"\n=== {result.protocol_name} + {result.matching_name} ===")
    print(f"Configuration: {a.n_agents} agents, {a.total_ticks} ticks")
    print()
    print("Trade Network:")
    print(f"  Total trades: {a.network.total_trades}")
    print(f"  Unique trading pairs: {a.network.n_edges}")
    print(f"  Network density: {a.network.density:.3f}")
    print(f"  Average degree: {a.network.avg_degree:.2f}")
    print(f"  Isolated agents: {len(a.network.isolated_agent_ids)}")
    print()
    print("Welfare Efficiency:")
    print(f"  Initial welfare: {a.efficiency.initial_welfare:.2f}")
    print(f"  Final welfare: {a.efficiency.final_welfare:.2f}")
    print(f"  Achieved gains: {a.efficiency.achieved_gains:.2f}")
    print(f"  Theoretical max: {a.efficiency.theoretical_max_gains:.2f}")
    print(f"  Efficiency ratio: {a.efficiency.efficiency_ratio:.1%}")
    print()
    print("Spatial Patterns:")
    print(f"  Trading clusters: {len(a.clusters)}")
    print(f"  Convergence rate: {a.convergence.hotspot_convergence_rate:.1%}")
    print(f"  Avg distance traveled: {a.convergence.avg_total_distance:.2f}")


def run_demonstration(
    n_agents: int = 64,
    ticks: int = 200,
    seed: int = 42,
    verbose: bool = True,
) -> dict[str, MarketEmergenceResult]:
    """Run the full market emergence demonstration.

    This is the top-level function for demonstrating institutional comparison.

    Args:
        n_agents: Number of agents (default 64 for reasonable runtime)
        ticks: Simulation length (default 200)
        seed: Random seed for reproducibility
        verbose: Whether to print progress and summaries

    Returns:
        Dict of results by protocol configuration
    """
    config = MarketEmergenceConfig(
        n_agents=n_agents,
        grid_size=max(16, n_agents // 4),
        perception_radius=5.0,
        seed=seed,
        ticks=ticks,
    )

    if verbose:
        print(f"Running market emergence demonstration...")
        print(f"  Agents: {n_agents}")
        print(f"  Grid: {config.grid_size}x{config.grid_size}")
        print(f"  Ticks: {ticks}")
        print(f"  Seed: {seed}")

    results = compare_protocols(config)

    if verbose:
        for result in results.values():
            print_emergence_summary(result)

        # Print comparison
        print("\n=== Protocol Comparison ===")
        for name, r in results.items():
            print(f"{name}: efficiency={r.analysis.efficiency.efficiency_ratio:.1%}, "
                  f"trades={r.analysis.network.total_trades}")

    return results


if __name__ == "__main__":
    # Run with moderate settings for quick demonstration
    results = run_demonstration(n_agents=50, ticks=150, seed=42)
