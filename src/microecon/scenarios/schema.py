"""
Scenario schema dataclasses.

Minimal schema for v1:
- meta.title (required)
- meta.complexity (required for ordering)
- meta.description (optional)
- meta.tags (optional)
- config.grid_size (required)
- config.agents (required)
- config.perception_radius (optional, default 7.0)
- config.discount_factor (optional, default 0.9)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class ScenarioMeta:
    """Metadata about a scenario."""

    title: str
    complexity: int  # 1-4, for ordering in browser
    description: str = ""
    tags: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for a single agent."""

    id: str
    position: Tuple[int, int]
    alpha: float  # Cobb-Douglas preference parameter
    endowment: Tuple[float, float]  # (x, y)

    def __post_init__(self):
        if not 0 < self.alpha < 1:
            raise ValueError(f"alpha must be in (0, 1), got {self.alpha}")
        if self.endowment[0] < 0 or self.endowment[1] < 0:
            raise ValueError(f"endowment must be non-negative, got {self.endowment}")


@dataclass(frozen=True)
class ScenarioConfig:
    """Simulation configuration for a scenario."""

    grid_size: int
    agents: Tuple[AgentConfig, ...]
    perception_radius: float = 7.0
    discount_factor: float = 0.9

    def __post_init__(self):
        if self.grid_size < 2:
            raise ValueError(f"grid_size must be >= 2, got {self.grid_size}")
        if len(self.agents) < 2:
            raise ValueError(f"Need at least 2 agents, got {len(self.agents)}")


@dataclass(frozen=True)
class Scenario:
    """A complete scenario definition."""

    meta: ScenarioMeta
    config: ScenarioConfig
    path: Optional[str] = None  # File path, set by loader

    @property
    def title(self) -> str:
        return self.meta.title

    @property
    def complexity(self) -> int:
        return self.meta.complexity

    @property
    def description(self) -> str:
        return self.meta.description

    @property
    def tags(self) -> Tuple[str, ...]:
        return self.meta.tags
