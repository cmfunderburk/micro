"""Experiment manifest data model (B-101).

An ExperimentManifest is a complete, self-contained experiment definition:
objective, assumptions, treatment arms, seed policy, and run budget.

Design doc: docs/plans/2026-03-02-b-e1-manifest-orchestrator-design.md §3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MANIFEST_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class BaseConfig:
    """Fixed simulation parameters held constant across all treatment arms."""

    n_agents: int
    grid_size: int
    ticks: int
    perception_radius: float = 7.0
    discount_factor: float = 0.95
    use_beliefs: bool = False
    info_env_name: str = "full"
    info_env_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_agents": self.n_agents,
            "grid_size": self.grid_size,
            "ticks": self.ticks,
            "perception_radius": self.perception_radius,
            "discount_factor": self.discount_factor,
            "use_beliefs": self.use_beliefs,
            "info_env_name": self.info_env_name,
            "info_env_params": self.info_env_params,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BaseConfig:
        return cls(
            n_agents=d["n_agents"],
            grid_size=d["grid_size"],
            ticks=d["ticks"],
            perception_radius=d.get("perception_radius", 7.0),
            discount_factor=d.get("discount_factor", 0.95),
            use_beliefs=d.get("use_beliefs", False),
            info_env_name=d.get("info_env_name", "full"),
            info_env_params=d.get("info_env_params", {}),
        )


@dataclass(frozen=True)
class TreatmentArm:
    """One experimental condition — overrides base_config fields."""

    name: str
    description: str
    overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "overrides": self.overrides,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TreatmentArm:
        return cls(
            name=d["name"],
            description=d["description"],
            overrides=d.get("overrides", {}),
        )


@dataclass(frozen=True)
class SeedPolicy:
    """Seed policy for deterministic reproducibility."""

    seeds: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"seeds": self.seeds}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SeedPolicy:
        return cls(seeds=d["seeds"])


@dataclass(frozen=True)
class ExperimentManifest:
    """Complete, self-contained experiment definition.

    A manifest captures enough information that anyone can understand
    what was intended, reproduce it, and interpret the results.
    """

    # Identity
    manifest_id: str
    name: str
    created_at: str
    schema_version: str

    # Intent
    objective: str
    hypotheses: list[str]

    # Fixed controls
    base_config: BaseConfig

    # Treatments
    treatments: list[TreatmentArm]

    # Execution policy
    seed_policy: SeedPolicy
    run_budget: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "name": self.name,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "objective": self.objective,
            "hypotheses": self.hypotheses,
            "base_config": self.base_config.to_dict(),
            "treatments": [t.to_dict() for t in self.treatments],
            "seed_policy": self.seed_policy.to_dict(),
            "run_budget": self.run_budget,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExperimentManifest:
        return cls(
            manifest_id=d["manifest_id"],
            name=d["name"],
            created_at=d["created_at"],
            schema_version=d["schema_version"],
            objective=d["objective"],
            hypotheses=d.get("hypotheses", []),
            base_config=BaseConfig.from_dict(d["base_config"]),
            treatments=[TreatmentArm.from_dict(t) for t in d["treatments"]],
            seed_policy=SeedPolicy.from_dict(d["seed_policy"]),
            run_budget=d["run_budget"],
        )
