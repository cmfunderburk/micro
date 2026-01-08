"""Data loading utilities for analysis.

Provides functions to load logged runs and batch results for analysis.
"""

from pathlib import Path

from microecon.logging import RunData, load_run as _load_run, load_batch as _load_batch


def load_run(path: Path | str) -> RunData:
    """Load a single run from disk.

    Args:
        path: Directory containing the run data (config.json, ticks.jsonl)

    Returns:
        RunData with config, ticks, and summary
    """
    if isinstance(path, str):
        path = Path(path)
    return _load_run(path)


def load_batch(path: Path | str) -> list[RunData]:
    """Load all runs from a batch directory.

    Args:
        path: Directory containing run subdirectories

    Returns:
        List of RunData objects
    """
    if isinstance(path, str):
        path = Path(path)
    return _load_batch(path)


def group_by_protocol(runs: list[RunData]) -> dict[str, list[RunData]]:
    """Group runs by bargaining protocol.

    Args:
        runs: List of RunData objects

    Returns:
        Dict mapping protocol name to list of runs
    """
    grouped: dict[str, list[RunData]] = {}
    for run in runs:
        protocol = run.config.protocol_name
        if protocol not in grouped:
            grouped[protocol] = []
        grouped[protocol].append(run)
    return grouped


def group_by_seed(runs: list[RunData]) -> dict[int, list[RunData]]:
    """Group runs by seed.

    Useful for paired comparisons where you want to compare
    different protocols with the same initial conditions.

    Args:
        runs: List of RunData objects

    Returns:
        Dict mapping seed to list of runs
    """
    grouped: dict[int, list[RunData]] = {}
    for run in runs:
        seed = run.config.seed
        if seed not in grouped:
            grouped[seed] = []
        grouped[seed].append(run)
    return grouped


def pair_runs_by_seed(
    runs: list[RunData], protocol_a: str, protocol_b: str
) -> list[tuple[RunData, RunData]]:
    """Pair runs with different protocols but same seed.

    Args:
        runs: List of RunData objects
        protocol_a: First protocol name (e.g., "nash")
        protocol_b: Second protocol name (e.g., "rubinstein")

    Returns:
        List of (run_a, run_b) pairs with matching seeds
    """
    by_seed = group_by_seed(runs)
    pairs = []

    for seed, seed_runs in by_seed.items():
        run_a = None
        run_b = None
        for run in seed_runs:
            if run.config.protocol_name == protocol_a:
                run_a = run
            elif run.config.protocol_name == protocol_b:
                run_b = run

        if run_a is not None and run_b is not None:
            pairs.append((run_a, run_b))

    return pairs
