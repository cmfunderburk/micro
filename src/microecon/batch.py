"""Batch runner for parameter sweeps and systematic comparisons.

Enables running multiple simulations with varying parameters,
collecting logs and summary statistics for analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any, Iterator
import random

from microecon.simulation import Simulation, create_simple_economy
from microecon.grid import Grid
from microecon.information import FullInformation
from microecon.bargaining import (
    BargainingProtocol,
    NashBargainingProtocol,
    RubinsteinBargainingProtocol,
)
from microecon.matching import (
    MatchingProtocol,
    OpportunisticMatchingProtocol,
    StableRoommatesMatchingProtocol,
)
from microecon.logging import (
    SimulationConfig,
    SimulationLogger,
    RunData,
    JSONLinesFormat,
)


@dataclass
class RunResult:
    """Result from a single simulation run."""

    config: SimulationConfig
    log_path: Path | None
    summary: dict[str, Any]
    run_data: RunData | None = None  # Populated if keep_in_memory=True


def _get_protocol_name(protocol: BargainingProtocol) -> str:
    """Get a string name for a bargaining protocol."""
    if isinstance(protocol, NashBargainingProtocol):
        return "nash"
    elif isinstance(protocol, RubinsteinBargainingProtocol):
        return "rubinstein"
    else:
        return protocol.__class__.__name__.lower()


def _get_matching_protocol_name(protocol: MatchingProtocol) -> str:
    """Get a string name for a matching protocol."""
    if isinstance(protocol, OpportunisticMatchingProtocol):
        return "opportunistic"
    elif isinstance(protocol, StableRoommatesMatchingProtocol):
        return "stable_roommates"
    else:
        return protocol.__class__.__name__.lower()


def _get_protocol_params(protocol: BargainingProtocol) -> dict[str, Any]:
    """Get parameters for a bargaining protocol."""
    # Rubinstein uses agent discount factors, not protocol-level delta
    return {}


@dataclass
class BatchRunner:
    """Run multiple simulations with parameter variations.

    Creates a cartesian product of all parameter variations and runs
    each configuration, collecting logs and summary statistics.

    Usage:
        runner = BatchRunner(
            base_config={
                "n_agents": 10,
                "grid_size": 15,
            },
            variations={
                "protocol": [NashBargainingProtocol(), RubinsteinBargainingProtocol()],
                "seed": list(range(5)),
            },
            output_dir=Path("./runs/experiment_001")
        )
        results = runner.run(ticks=100)
    """

    base_config: dict[str, Any]
    variations: dict[str, list[Any]] = field(default_factory=dict)
    output_dir: Path | None = None
    keep_in_memory: bool = True  # Keep RunData in memory for analysis

    def _expand_variations(self) -> Iterator[dict[str, Any]]:
        """Generate all parameter combinations."""
        if not self.variations:
            yield self.base_config.copy()
            return

        keys = list(self.variations.keys())
        value_lists = [self.variations[k] for k in keys]

        for values in product(*value_lists):
            config = self.base_config.copy()
            for key, value in zip(keys, values):
                config[key] = value
            yield config

    def _create_simulation(
        self, config: dict[str, Any], logger: SimulationLogger | None
    ) -> Simulation:
        """Create a simulation from config dict."""
        # Extract parameters with defaults
        n_agents = config.get("n_agents", 10)
        grid_size = config.get("grid_size", 10)
        perception_radius = config.get("perception_radius", 7.0)
        discount_factor = config.get("discount_factor", 0.95)
        seed = config.get("seed")
        bargaining_protocol = config.get("protocol", NashBargainingProtocol())
        matching_protocol = config.get("matching_protocol", OpportunisticMatchingProtocol())

        # Create simulation using factory function but inject logger
        if seed is not None:
            random.seed(seed)

        sim = create_simple_economy(
            n_agents=n_agents,
            grid_size=grid_size,
            perception_radius=perception_radius,
            discount_factor=discount_factor,
            seed=seed,
            bargaining_protocol=bargaining_protocol,
            matching_protocol=matching_protocol,
        )

        # Inject logger
        sim.logger = logger

        return sim

    def _config_to_simulation_config(
        self, config: dict[str, Any]
    ) -> SimulationConfig:
        """Convert config dict to SimulationConfig dataclass."""
        protocol = config.get("protocol", NashBargainingProtocol())
        return SimulationConfig(
            n_agents=config.get("n_agents", 10),
            grid_size=config.get("grid_size", 10),
            seed=config["seed"],  # Required - validated in run()
            protocol_name=_get_protocol_name(protocol),
            protocol_params=_get_protocol_params(protocol),
            perception_radius=config.get("perception_radius", 7.0),
            discount_factor=config.get("discount_factor", 0.95),
            movement_budget=config.get("movement_budget", 1),
        )

    def _generate_run_name(self, config: dict[str, Any], index: int) -> str:
        """Generate a unique name for a run directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        seed = config.get("seed", index)

        # Include bargaining protocol if varying
        bargaining = config.get("protocol", NashBargainingProtocol())
        bargaining_name = _get_protocol_name(bargaining)

        # Include matching protocol if varying
        matching = config.get("matching_protocol", OpportunisticMatchingProtocol())
        matching_name = _get_matching_protocol_name(matching)

        # Build name with both protocols if non-default matching
        if matching_name != "opportunistic":
            return f"run_{timestamp}_seed{seed}_{bargaining_name}_{matching_name}_{index:04d}"
        return f"run_{timestamp}_seed{seed}_{bargaining_name}_{index:04d}"

    def _run_single(
        self, config: dict[str, Any], ticks: int, index: int
    ) -> RunResult:
        """Run a single simulation configuration."""
        sim_config = self._config_to_simulation_config(config)

        # Set up output path if specified
        output_path = None
        if self.output_dir is not None:
            run_name = self._generate_run_name(config, index)
            output_path = self.output_dir / run_name

        # Create logger
        logger = SimulationLogger(
            config=sim_config,
            output_path=output_path,
            log_format=JSONLinesFormat() if output_path else None,
        )

        # Create and run simulation
        sim = self._create_simulation(config, logger)
        sim.run(ticks)

        # Finalize and get run data
        run_data = logger.finalize()

        # Build summary
        summary = {
            "total_ticks": ticks,
            "final_welfare": sim.total_welfare(),
            "total_trades": len(sim.trades),
            "welfare_gains": sim.welfare_gains(),
        }

        return RunResult(
            config=sim_config,
            log_path=output_path,
            summary=summary,
            run_data=run_data if self.keep_in_memory else None,
        )

    def _validate_seed_required(self) -> None:
        """Validate that all runs will have an explicit seed.

        Batch runs require explicit seeds for reproducibility. This catches
        the mistake early rather than after a long batch completes.
        """
        has_base_seed = "seed" in self.base_config
        has_seed_variation = "seed" in self.variations

        if not has_base_seed and not has_seed_variation:
            raise ValueError(
                "BatchRunner requires an explicit seed for reproducibility. "
                "Provide 'seed' in base_config or include 'seed' in variations."
            )

    def run(self, ticks: int = 100) -> list[RunResult]:
        """Run all parameter combinations.

        Args:
            ticks: Number of simulation ticks to run for each configuration

        Returns:
            List of RunResult objects with summary statistics and log paths

        Raises:
            ValueError: If no seed is provided in base_config or variations
        """
        # Validate seed requirement before starting any runs
        self._validate_seed_required()

        # Create output directory if specified
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for index, config in enumerate(self._expand_variations()):
            result = self._run_single(config, ticks, index)
            results.append(result)

        return results

    def count_runs(self) -> int:
        """Count how many runs will be executed."""
        if not self.variations:
            return 1
        count = 1
        for values in self.variations.values():
            count *= len(values)
        return count


def run_comparison(
    n_agents: int = 10,
    grid_size: int = 15,
    ticks: int = 100,
    seeds: list[int] | None = None,
    output_dir: Path | None = None,
) -> list[RunResult]:
    """Quick comparison of Nash vs Rubinstein bargaining.

    Convenience function for the most common comparison case.

    Args:
        n_agents: Number of agents per run
        grid_size: Size of the grid
        ticks: Number of simulation ticks
        seeds: List of seeds to run (default: [0, 1, 2, 3, 4])
        output_dir: Optional directory to save logs

    Returns:
        List of RunResult objects (alternating Nash/Rubinstein for each seed)
    """
    if seeds is None:
        seeds = list(range(5))

    runner = BatchRunner(
        base_config={
            "n_agents": n_agents,
            "grid_size": grid_size,
        },
        variations={
            "protocol": [
                NashBargainingProtocol(),
                RubinsteinBargainingProtocol(),
            ],
            "seed": seeds,
        },
        output_dir=output_dir,
    )

    return runner.run(ticks=ticks)


def run_matching_comparison(
    n_agents: int = 10,
    grid_size: int = 15,
    ticks: int = 100,
    seeds: list[int] | None = None,
    output_dir: Path | None = None,
) -> list[RunResult]:
    """Quick comparison of Opportunistic vs StableRoommates matching.

    Convenience function for comparing matching protocols. Uses Nash
    bargaining as the default bargaining protocol.

    Args:
        n_agents: Number of agents per run
        grid_size: Size of the grid
        ticks: Number of simulation ticks
        seeds: List of seeds to run (default: [0, 1, 2, 3, 4])
        output_dir: Optional directory to save logs

    Returns:
        List of RunResult objects (alternating Opportunistic/StableRoommates for each seed)
    """
    if seeds is None:
        seeds = list(range(5))

    runner = BatchRunner(
        base_config={
            "n_agents": n_agents,
            "grid_size": grid_size,
        },
        variations={
            "matching_protocol": [
                OpportunisticMatchingProtocol(),
                StableRoommatesMatchingProtocol(),
            ],
            "seed": seeds,
        },
        output_dir=output_dir,
    )

    return runner.run(ticks=ticks)
