"""Tests for experiment manifest data model (B-101) and validation (B-102)."""

import pytest

from microecon.manifest import (
    ExperimentManifest,
    BaseConfig,
    TreatmentArm,
    SeedPolicy,
    MANIFEST_SCHEMA_VERSION,
    validate_manifest,
)


def _make_manifest(**overrides):
    """Helper to create a valid manifest with optional overrides."""
    defaults = {
        "manifest_id": "test-id-123",
        "name": "Test Experiment",
        "created_at": "2026-03-03T00:00:00Z",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "objective": "Compare Nash vs Rubinstein bargaining",
        "hypotheses": ["Rubinstein yields higher welfare"],
        "base_config": BaseConfig(n_agents=10, grid_size=15, ticks=100),
        "treatments": [
            TreatmentArm(
                name="nash_baseline",
                description="Nash bargaining with bilateral matching",
                overrides={"bargaining_protocol": "nash"},
            ),
            TreatmentArm(
                name="rubinstein_treatment",
                description="Rubinstein bargaining with bilateral matching",
                overrides={"bargaining_protocol": "rubinstein"},
            ),
        ],
        "seed_policy": SeedPolicy(seeds=[0, 1, 2]),
        "run_budget": 6,
    }
    defaults.update(overrides)
    return ExperimentManifest(**defaults)


@pytest.mark.orchestrator
class TestManifestDataModel:
    """Test manifest creation and field access."""

    def test_create_manifest(self):
        m = _make_manifest()
        assert m.manifest_id == "test-id-123"
        assert m.name == "Test Experiment"
        assert m.base_config.n_agents == 10
        assert m.base_config.ticks == 100
        assert len(m.treatments) == 2
        assert m.treatments[0].name == "nash_baseline"
        assert m.seed_policy.seeds == [0, 1, 2]
        assert m.run_budget == 6

    def test_manifest_is_frozen(self):
        m = _make_manifest()
        with pytest.raises(AttributeError):
            m.name = "changed"

    def test_base_config_defaults(self):
        bc = BaseConfig(n_agents=10, grid_size=15, ticks=100)
        assert bc.perception_radius == 7.0
        assert bc.discount_factor == 0.95
        assert bc.use_beliefs is False
        assert bc.info_env_name == "full"
        assert bc.info_env_params == {}


@pytest.mark.orchestrator
class TestManifestSerialization:
    """Test manifest to_dict/from_dict round-trip."""

    def test_manifest_roundtrip(self):
        original = _make_manifest()
        d = original.to_dict()
        restored = ExperimentManifest.from_dict(d)
        assert restored == original

    def test_to_dict_structure(self):
        m = _make_manifest()
        d = m.to_dict()
        assert d["manifest_id"] == "test-id-123"
        assert d["base_config"]["n_agents"] == 10
        assert d["base_config"]["ticks"] == 100
        assert len(d["treatments"]) == 2
        assert d["treatments"][0]["name"] == "nash_baseline"
        assert d["seed_policy"]["seeds"] == [0, 1, 2]

    def test_base_config_roundtrip(self):
        bc = BaseConfig(n_agents=20, grid_size=25, ticks=200, use_beliefs=True)
        d = bc.to_dict()
        restored = BaseConfig.from_dict(d)
        assert restored == bc

    def test_treatment_arm_roundtrip(self):
        arm = TreatmentArm(
            name="test_arm",
            description="A test",
            overrides={"bargaining_protocol": "tioli", "matching_protocol": "centralized_clearing"},
        )
        d = arm.to_dict()
        restored = TreatmentArm.from_dict(d)
        assert restored == arm


@pytest.mark.orchestrator
class TestManifestValidation:
    """Test manifest validation rules (B-102)."""

    def test_valid_manifest_passes(self):
        m = _make_manifest()
        errors = validate_manifest(m)
        assert errors == []

    def test_too_few_treatments(self):
        m = _make_manifest(treatments=[
            TreatmentArm(name="only_one", description="solo", overrides={}),
        ], run_budget=3)
        errors = validate_manifest(m)
        assert any("at least 2" in e for e in errors)

    def test_empty_seeds(self):
        m = _make_manifest(seed_policy=SeedPolicy(seeds=[]), run_budget=0)
        errors = validate_manifest(m)
        assert any("seed" in e.lower() for e in errors)

    def test_wrong_run_budget(self):
        m = _make_manifest(run_budget=999)
        errors = validate_manifest(m)
        assert any("run_budget" in e for e in errors)

    def test_invalid_n_agents(self):
        m = _make_manifest(base_config=BaseConfig(n_agents=0, grid_size=15, ticks=100))
        errors = validate_manifest(m)
        assert any("n_agents" in e for e in errors)

    def test_invalid_grid_size(self):
        m = _make_manifest(base_config=BaseConfig(n_agents=10, grid_size=-1, ticks=100))
        errors = validate_manifest(m)
        assert any("grid_size" in e for e in errors)

    def test_invalid_ticks(self):
        m = _make_manifest(base_config=BaseConfig(n_agents=10, grid_size=15, ticks=0))
        errors = validate_manifest(m)
        assert any("ticks" in e for e in errors)

    def test_unknown_bargaining_protocol(self):
        m = _make_manifest(treatments=[
            TreatmentArm(name="a", description="a", overrides={"bargaining_protocol": "unknown"}),
            TreatmentArm(name="b", description="b", overrides={"bargaining_protocol": "nash"}),
        ])
        errors = validate_manifest(m)
        assert any("bargaining_protocol" in e for e in errors)

    def test_unknown_matching_protocol(self):
        m = _make_manifest(treatments=[
            TreatmentArm(name="a", description="a", overrides={"matching_protocol": "invalid"}),
            TreatmentArm(name="b", description="b", overrides={}),
        ])
        errors = validate_manifest(m)
        assert any("matching_protocol" in e for e in errors)

    def test_duplicate_treatment_names(self):
        m = _make_manifest(treatments=[
            TreatmentArm(name="same", description="a", overrides={"bargaining_protocol": "nash"}),
            TreatmentArm(name="same", description="b", overrides={"bargaining_protocol": "rubinstein"}),
        ])
        errors = validate_manifest(m)
        assert any("unique" in e.lower() or "duplicate" in e.lower() for e in errors)

    def test_duplicate_seeds(self):
        m = _make_manifest(seed_policy=SeedPolicy(seeds=[1, 1, 2]), run_budget=6)
        errors = validate_manifest(m)
        assert any("duplicate" in e.lower() or "unique" in e.lower() for e in errors)

    def test_unknown_override_key(self):
        m = _make_manifest(treatments=[
            TreatmentArm(name="a", description="a", overrides={"nonexistent_field": 42}),
            TreatmentArm(name="b", description="b", overrides={}),
        ])
        errors = validate_manifest(m)
        assert any("nonexistent_field" in e for e in errors)

    def test_multiple_errors_returned(self):
        """Validation should return ALL errors, not just the first."""
        m = _make_manifest(
            base_config=BaseConfig(n_agents=0, grid_size=-1, ticks=0),
            treatments=[TreatmentArm(name="only", description="solo", overrides={})],
            seed_policy=SeedPolicy(seeds=[]),
            run_budget=999,
        )
        errors = validate_manifest(m)
        assert len(errors) >= 4
