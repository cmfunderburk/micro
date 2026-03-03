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


# ---------------------------------------------------------------------------
# Manifest validation (B-102)
# ---------------------------------------------------------------------------

_VALID_BARGAINING_PROTOCOLS = {"nash", "rubinstein", "tioli", "asymmetric_nash"}
_VALID_MATCHING_PROTOCOLS = {"bilateral_proposal", "centralized_clearing"}
_VALID_INFO_ENVS = {"full", "full_information", "noisy_alpha"}
_VALID_OVERRIDE_KEYS = {
    "bargaining_protocol", "matching_protocol",
    "info_env_name", "info_env_params",
    "perception_radius", "discount_factor", "use_beliefs",
    "n_agents", "grid_size", "ticks",
    "bargaining_power_distribution",
}


def validate_manifest(manifest: ExperimentManifest) -> list[str]:
    """Validate a manifest and return a list of error messages.

    Returns an empty list if the manifest is valid.
    """
    errors: list[str] = []

    # Treatment count
    if len(manifest.treatments) < 2:
        errors.append(
            f"Manifest must have at least 2 treatment arms, got {len(manifest.treatments)}"
        )

    # Seed policy
    if len(manifest.seed_policy.seeds) < 1:
        errors.append("seed_policy must contain at least 1 seed")

    if len(manifest.seed_policy.seeds) != len(set(manifest.seed_policy.seeds)):
        errors.append("seed_policy contains duplicate seeds")

    # Run budget
    expected_budget = len(manifest.treatments) * len(manifest.seed_policy.seeds)
    if manifest.run_budget != expected_budget:
        errors.append(
            f"run_budget ({manifest.run_budget}) does not match "
            f"treatments ({len(manifest.treatments)}) x seeds ({len(manifest.seed_policy.seeds)}) "
            f"= {expected_budget}"
        )

    # Base config bounds
    bc = manifest.base_config
    if bc.n_agents <= 0:
        errors.append(f"n_agents must be > 0, got {bc.n_agents}")
    if bc.grid_size <= 0:
        errors.append(f"grid_size must be > 0, got {bc.grid_size}")
    if bc.ticks <= 0:
        errors.append(f"ticks must be > 0, got {bc.ticks}")

    # Treatment arm names
    arm_names = [t.name for t in manifest.treatments]
    if len(arm_names) != len(set(arm_names)):
        errors.append("Treatment arm names must be unique")

    # Override validation
    for arm in manifest.treatments:
        for key, value in arm.overrides.items():
            if key not in _VALID_OVERRIDE_KEYS:
                errors.append(
                    f"Treatment '{arm.name}': unknown override key '{key}'"
                )
            if key == "bargaining_protocol" and value not in _VALID_BARGAINING_PROTOCOLS:
                errors.append(
                    f"Treatment '{arm.name}': invalid bargaining_protocol '{value}'. "
                    f"Valid: {sorted(_VALID_BARGAINING_PROTOCOLS)}"
                )
            if key == "matching_protocol" and value not in _VALID_MATCHING_PROTOCOLS:
                errors.append(
                    f"Treatment '{arm.name}': invalid matching_protocol '{value}'. "
                    f"Valid: {sorted(_VALID_MATCHING_PROTOCOLS)}"
                )
            if key == "info_env_name" and value not in _VALID_INFO_ENVS:
                errors.append(
                    f"Treatment '{arm.name}': invalid info_env_name '{value}'. "
                    f"Valid: {sorted(_VALID_INFO_ENVS)}"
                )
            # Numeric bounds on overridable config fields
            if key in ("n_agents", "grid_size", "ticks") and isinstance(value, (int, float)):
                if value <= 0:
                    errors.append(
                        f"Treatment '{arm.name}': {key} must be > 0, got {value}"
                    )
            if key == "perception_radius" and isinstance(value, (int, float)):
                if value <= 0:
                    errors.append(
                        f"Treatment '{arm.name}': perception_radius must be > 0, got {value}"
                    )

    return errors
