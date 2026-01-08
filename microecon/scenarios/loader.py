"""
YAML scenario loader.

Loads scenario files from the scenarios/ directory at repo root.
"""

from pathlib import Path
from typing import List, Optional

import yaml

from .schema import Scenario, ScenarioMeta, ScenarioConfig, AgentConfig


class ScenarioLoadError(Exception):
    """Raised when a scenario file cannot be loaded."""

    pass


def _get_scenarios_dir() -> Path:
    """Get the scenarios directory path (the one with YAML files, not the Python package)."""
    # First, find the repo root by looking for pyproject.toml or .git
    current = Path(__file__).resolve()
    repo_root = None
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            repo_root = parent
            break

    if repo_root is not None:
        scenarios_dir = repo_root / "scenarios"
        if scenarios_dir.is_dir():
            return scenarios_dir

    # Fallback: relative to cwd
    return Path.cwd() / "scenarios"


def load_scenario(path: Path) -> Scenario:
    """
    Load a single scenario from a YAML file.

    Args:
        path: Path to the YAML file

    Returns:
        Parsed Scenario object

    Raises:
        ScenarioLoadError: If the file cannot be loaded or parsed
    """
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise ScenarioLoadError(f"Scenario file not found: {path}")
    except yaml.YAMLError as e:
        raise ScenarioLoadError(f"Invalid YAML in {path}: {e}")

    if not isinstance(data, dict):
        raise ScenarioLoadError(f"Scenario must be a YAML mapping, got {type(data)}")

    # Parse meta section
    meta_data = data.get("meta", {})
    if "title" not in meta_data:
        raise ScenarioLoadError(f"Missing required field: meta.title in {path}")
    if "complexity" not in meta_data:
        raise ScenarioLoadError(f"Missing required field: meta.complexity in {path}")

    tags = meta_data.get("tags", [])
    if isinstance(tags, list):
        tags = tuple(tags)

    meta = ScenarioMeta(
        title=meta_data["title"],
        complexity=int(meta_data["complexity"]),
        description=meta_data.get("description", ""),
        tags=tags,
    )

    # Parse config section
    config_data = data.get("config", {})
    if "grid_size" not in config_data:
        raise ScenarioLoadError(f"Missing required field: config.grid_size in {path}")
    if "agents" not in config_data:
        raise ScenarioLoadError(f"Missing required field: config.agents in {path}")

    agents = []
    for i, agent_data in enumerate(config_data["agents"]):
        try:
            agent = AgentConfig(
                id=agent_data["id"],
                position=tuple(agent_data["position"]),
                alpha=float(agent_data["alpha"]),
                endowment=tuple(float(x) for x in agent_data["endowment"]),
            )
            agents.append(agent)
        except KeyError as e:
            raise ScenarioLoadError(
                f"Missing field {e} in agent {i} of {path}"
            )
        except (ValueError, TypeError) as e:
            raise ScenarioLoadError(
                f"Invalid value in agent {i} of {path}: {e}"
            )

    try:
        config = ScenarioConfig(
            grid_size=int(config_data["grid_size"]),
            agents=tuple(agents),
            perception_radius=float(config_data.get("perception_radius", 7.0)),
            discount_factor=float(config_data.get("discount_factor", 0.9)),
        )
    except ValueError as e:
        raise ScenarioLoadError(f"Invalid config in {path}: {e}")

    return Scenario(meta=meta, config=config, path=str(path))


def load_all_scenarios(directory: Optional[Path] = None) -> List[Scenario]:
    """
    Load all scenarios from a directory.

    Args:
        directory: Path to scenarios directory. If None, uses default location.

    Returns:
        List of Scenario objects, sorted by complexity then title
    """
    if directory is None:
        directory = _get_scenarios_dir()

    if not directory.is_dir():
        return []

    scenarios = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            scenario = load_scenario(path)
            scenarios.append(scenario)
        except ScenarioLoadError:
            # Skip invalid scenarios, but could log warning
            continue

    # Sort by complexity, then by title
    scenarios.sort(key=lambda s: (s.complexity, s.title))
    return scenarios
