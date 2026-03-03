# B-E1: Manifest and Orchestrator Services Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the manifest, orchestrator, and catalog service layer — the backend that turns ad-hoc experiments into a product service with persistence, provenance, and queryable results.

**Architecture:** SQLite catalog (manifests, jobs, runs metadata) + per-run Parquet files (lossless tick data). Three FastAPI routers: manifest service, orchestrator service, catalog service. Async job execution with background threads.

**Tech Stack:** Python 3.12, FastAPI, SQLite (stdlib), pyarrow (Parquet), existing microecon simulation core.

**Design Doc:** `docs/plans/2026-03-02-b-e1-manifest-orchestrator-design.md`

---

## Task 1: Add pyarrow dependency and orchestrator test marker

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

**Step 1: Add pyarrow to project dependencies**

In `pyproject.toml`, add `pyarrow` to the `dependencies` list (after `websockets`):

```toml
dependencies = [
    "pyyaml>=6.0.3",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "websockets>=14.0",
    "pyarrow>=14.0",
]
```

**Step 2: Add orchestrator test marker**

In `pyproject.toml` under `[tool.pytest.ini_options]` markers, add:

```
orchestrator = "Manifest, orchestrator, and catalog service tests"
```

**Step 3: Add data directory and database to .gitignore**

Append to `.gitignore`:

```
# B-E1: Orchestrator data
microecon.db
microecon.db-wal
microecon.db-shm
data/
```

**Step 4: Install dependencies**

Run: `uv sync`
Expected: pyarrow installs successfully

**Step 5: Verify pyarrow works**

Run: `uv run python -c "import pyarrow; print(pyarrow.__version__)"`
Expected: Version >= 14.0

**Step 6: Commit**

```bash
git add pyproject.toml .gitignore uv.lock
git commit -m "feat(deps): add pyarrow dependency and orchestrator test marker"
```

---

## Task 2: Manifest data model and serialization (B-101)

**Files:**
- Create: `microecon/manifest.py`
- Create: `tests/test_manifest.py`

**Step 1: Write failing tests for manifest data model**

Create `tests/test_manifest.py`:

```python
"""Tests for experiment manifest data model (B-101)."""

import pytest

from microecon.manifest import (
    ExperimentManifest,
    BaseConfig,
    TreatmentArm,
    SeedPolicy,
    MANIFEST_SCHEMA_VERSION,
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'microecon.manifest'`

**Step 3: Implement manifest data model**

Create `microecon/manifest.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add microecon/manifest.py tests/test_manifest.py
git commit -m "feat(manifest): add experiment manifest data model (B-101)"
```

---

## Task 3: Manifest validation (B-102)

**Files:**
- Modify: `microecon/manifest.py`
- Modify: `tests/test_manifest.py`

**Step 1: Write failing tests for validation**

Append to `tests/test_manifest.py`:

```python
from microecon.manifest import validate_manifest


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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_manifest.py::TestManifestValidation -v`
Expected: FAIL — `cannot import name 'validate_manifest'`

**Step 3: Implement validate_manifest**

Add to `microecon/manifest.py`:

```python
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
    if bc.perception_radius <= 0:
        errors.append(f"perception_radius must be > 0, got {bc.perception_radius}")

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

    return errors
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add microecon/manifest.py tests/test_manifest.py
git commit -m "feat(manifest): add manifest validation (B-102)"
```

---

## Task 4: Database module

**Files:**
- Create: `server/database.py`
- Create: `tests/test_database.py`

**Step 1: Write failing tests for database init**

Create `tests/test_database.py`:

```python
"""Tests for database module."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from server.database import init_db, get_connection


@pytest.mark.orchestrator
class TestDatabase:
    def test_init_creates_tables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            init_db(db_path)

            conn = get_connection(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            assert "manifests" in tables
            assert "jobs" in tables
            assert "runs" in tables
            conn.close()

    def test_init_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            init_db(db_path)
            init_db(db_path)  # Should not raise

    def test_connection_has_foreign_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            init_db(db_path)
            conn = get_connection(db_path)
            result = conn.execute("PRAGMA foreign_keys").fetchone()
            assert result[0] == 1
            conn.close()

    def test_connection_has_wal_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            init_db(db_path)
            conn = get_connection(db_path)
            result = conn.execute("PRAGMA journal_mode").fetchone()
            assert result[0] == "wal"
            conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement database module**

Create `server/database.py`:

```python
"""SQLite database module for manifest, job, and run persistence.

Design doc: docs/plans/2026-03-02-b-e1-manifest-orchestrator-design.md §5, §10
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("microecon.db")
DATA_DIR = Path("data")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS manifests (
    manifest_id    TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    objective      TEXT NOT NULL,
    hypotheses     TEXT NOT NULL,
    base_config    TEXT NOT NULL,
    treatments     TEXT NOT NULL,
    seed_policy    TEXT NOT NULL,
    run_budget     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id         TEXT PRIMARY KEY,
    manifest_id    TEXT NOT NULL REFERENCES manifests(manifest_id),
    status         TEXT NOT NULL DEFAULT 'pending',
    created_at     TEXT NOT NULL,
    started_at     TEXT,
    completed_at   TEXT,
    error_message  TEXT,
    progress       TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id         TEXT PRIMARY KEY,
    job_id         TEXT NOT NULL REFERENCES jobs(job_id),
    manifest_id    TEXT NOT NULL REFERENCES manifests(manifest_id),
    treatment_arm  TEXT NOT NULL,
    seed           INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    config         TEXT NOT NULL,
    summary        TEXT,
    data_path      TEXT,
    created_at     TEXT NOT NULL,
    completed_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_manifest ON jobs(manifest_id);
CREATE INDEX IF NOT EXISTS idx_runs_job ON runs(job_id);
CREATE INDEX IF NOT EXISTS idx_runs_manifest ON runs(manifest_id);
CREATE INDEX IF NOT EXISTS idx_runs_treatment ON runs(manifest_id, treatment_arm);
"""


def init_db(path: Path = DB_PATH) -> None:
    """Create tables and indexes if they don't exist."""
    conn = get_connection(path)
    conn.executescript(_SCHEMA_SQL)
    conn.close()


def get_connection(path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_database.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add server/database.py tests/test_database.py
git commit -m "feat(db): add SQLite database module with schema init"
```

---

## Task 5: Parquet read/write module (B-105 partial)

**Files:**
- Create: `microecon/logging/parquet.py`
- Create: `tests/test_parquet.py`

**Step 1: Write failing tests for Parquet round-trip**

Create `tests/test_parquet.py`:

```python
"""Tests for Parquet read/write (B-107 Level 3)."""

import tempfile
from pathlib import Path

import pytest

from microecon.simulation import create_simple_economy
from microecon.logging.logger import SimulationLogger, RunData
from microecon.logging.events import SimulationConfig
from microecon.logging.parquet import write_run_parquet, read_run_parquet, read_column_parquet


def _run_simulation(seed: int = 42, n_agents: int = 4, ticks: int = 10) -> RunData:
    """Run a small simulation and return RunData."""
    config = SimulationConfig(
        n_agents=n_agents, grid_size=10, seed=seed, protocol_name="nash",
    )
    logger = SimulationLogger(config=config, output_path=None)
    sim = create_simple_economy(
        n_agents=n_agents, grid_size=10, seed=seed,
    )
    sim.logger = logger
    for _ in range(ticks):
        sim.step()
    return logger.finalize()


@pytest.mark.orchestrator
class TestParquetRoundTrip:
    """Level 3: Parquet round-trip tests."""

    def test_write_and_read_produces_equivalent_run_data(self):
        original = _run_simulation()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.parquet"
            write_run_parquet(original, path)
            restored = read_run_parquet(path)

            assert restored.config == original.config
            assert len(restored.ticks) == len(original.ticks)
            for orig_tick, rest_tick in zip(original.ticks, restored.ticks):
                assert rest_tick.tick == orig_tick.tick
                assert abs(rest_tick.total_welfare - orig_tick.total_welfare) < 1e-10
                assert rest_tick.cumulative_trades == orig_tick.cumulative_trades
                assert len(rest_tick.agent_snapshots) == len(orig_tick.agent_snapshots)
                assert len(rest_tick.trades) == len(orig_tick.trades)
                assert len(rest_tick.search_decisions) == len(orig_tick.search_decisions)
                assert len(rest_tick.movements) == len(orig_tick.movements)

    def test_read_single_column(self):
        run_data = _run_simulation()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.parquet"
            write_run_parquet(run_data, path)

            welfare_col = read_column_parquet(path, "total_welfare")
            assert len(welfare_col) == len(run_data.ticks)
            for i, tick in enumerate(run_data.ticks):
                assert abs(welfare_col[i].as_py() - tick.total_welfare) < 1e-10

    def test_parquet_file_exists_after_write(self):
        run_data = _run_simulation()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.parquet"
            write_run_parquet(run_data, path)
            assert path.exists()
            assert path.stat().st_size > 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_parquet.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement Parquet module**

Create `microecon/logging/parquet.py`. This is the largest single implementation — it converts between `RunData`/`TickRecord` and Arrow tables.

```python
"""Parquet read/write for simulation tick data.

Provides lossless round-trip serialization of RunData to Parquet files.
Each run produces one Parquet file with one row per tick.

Design doc: docs/plans/2026-03-02-b-e1-manifest-orchestrator-design.md §6
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .events import (
    AgentSnapshot,
    BeliefSnapshot,
    CommitmentBrokenEvent,
    CommitmentFormedEvent,
    MovementEvent,
    SearchDecision,
    SimulationConfig,
    TargetEvaluation,
    TickRecord,
    TradeEvent,
    RunSummary,
)
from .logger import RunData


def write_run_parquet(run_data: RunData, path: Path) -> None:
    """Convert RunData to Arrow table and write Parquet file.

    Writes config as Parquet file metadata so the file is self-contained.
    """
    rows: list[dict[str, Any]] = []
    for tick in run_data.ticks:
        rows.append(_tick_to_row(tick))

    table = pa.Table.from_pylist(rows)

    # Store config and summary as file metadata
    metadata = {
        b"config": json.dumps(run_data.config.to_dict()).encode(),
    }
    if run_data.summary is not None:
        metadata[b"summary"] = json.dumps(run_data.summary.to_dict()).encode()

    table = table.replace_schema_metadata({
        **metadata,
        **(table.schema.metadata or {}),
    })

    pq.write_table(table, str(path))


def read_run_parquet(path: Path) -> RunData:
    """Read Parquet file back into RunData."""
    table = pq.read_table(str(path))
    metadata = table.schema.metadata or {}

    config = SimulationConfig.from_dict(
        json.loads(metadata[b"config"].decode())
    )

    summary = None
    if b"summary" in metadata:
        summary = RunSummary.from_dict(
            json.loads(metadata[b"summary"].decode())
        )

    ticks = []
    for i in range(len(table)):
        row = {col: table.column(col)[i].as_py() for col in table.column_names}
        ticks.append(_row_to_tick(row))

    return RunData(config=config, ticks=ticks, summary=summary)


def read_column_parquet(path: Path, column: str) -> pa.Array:
    """Read a single column for fast analytical queries."""
    table = pq.read_table(str(path), columns=[column])
    return table.column(column)


def _tick_to_row(tick: TickRecord) -> dict[str, Any]:
    """Convert a TickRecord to a flat dict for Arrow."""
    return {
        "tick": tick.tick,
        "total_welfare": tick.total_welfare,
        "cumulative_trades": tick.cumulative_trades,
        "trade_count": len(tick.trades),
        "welfare_gains": 0.0,  # Populated by caller if needed

        "agent_snapshots": [s.to_dict() for s in tick.agent_snapshots],
        "search_decisions": [s.to_dict() for s in tick.search_decisions],
        "movements": [m.to_dict() for m in tick.movements],
        "trades": [t.to_dict() for t in tick.trades],
        "commitments_formed": [c.to_dict() for c in tick.commitments_formed],
        "commitments_broken": [c.to_dict() for c in tick.commitments_broken],
        "belief_snapshots": [b.to_dict() for b in tick.belief_snapshots],
    }


def _row_to_tick(row: dict[str, Any]) -> TickRecord:
    """Convert a Parquet row back to a TickRecord."""
    return TickRecord(
        tick=row["tick"],
        total_welfare=row["total_welfare"],
        cumulative_trades=row["cumulative_trades"],
        agent_snapshots=tuple(
            AgentSnapshot.from_dict(s) for s in (row.get("agent_snapshots") or [])
        ),
        search_decisions=tuple(
            SearchDecision.from_dict(s) for s in (row.get("search_decisions") or [])
        ),
        movements=tuple(
            MovementEvent.from_dict(m) for m in (row.get("movements") or [])
        ),
        trades=tuple(
            TradeEvent.from_dict(t) for t in (row.get("trades") or [])
        ),
        commitments_formed=tuple(
            CommitmentFormedEvent.from_dict(c) for c in (row.get("commitments_formed") or [])
        ),
        commitments_broken=tuple(
            CommitmentBrokenEvent.from_dict(c) for c in (row.get("commitments_broken") or [])
        ),
        belief_snapshots=tuple(
            BeliefSnapshot.from_dict(b) for b in (row.get("belief_snapshots") or [])
        ),
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_parquet.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add microecon/logging/parquet.py tests/test_parquet.py
git commit -m "feat(parquet): add Parquet read/write for tick data (B-105)"
```

---

## Task 6: Manifest service — CRUD API (B-103)

**Files:**
- Create: `server/manifest_service.py`
- Create: `tests/test_manifest_service.py`
- Modify: `server/app.py`

**Step 1: Write failing tests for manifest service**

Create `tests/test_manifest_service.py`:

```python
"""Tests for manifest CRUD API (B-103, B-107 Level 1)."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.database import init_db, DB_PATH


@pytest.fixture
def client(tmp_path):
    """Create test client with isolated database."""
    db_path = tmp_path / "test.db"
    import server.database as db_mod
    original_path = db_mod.DB_PATH
    db_mod.DB_PATH = db_path

    app = create_app()
    init_db(db_path)

    with TestClient(app) as c:
        yield c

    db_mod.DB_PATH = original_path


def _valid_manifest_payload():
    return {
        "name": "Test Experiment",
        "objective": "Compare Nash vs Rubinstein",
        "hypotheses": ["Rubinstein yields higher welfare"],
        "base_config": {
            "n_agents": 10,
            "grid_size": 15,
            "ticks": 50,
        },
        "treatments": [
            {"name": "nash", "description": "Nash bargaining", "overrides": {"bargaining_protocol": "nash"}},
            {"name": "rubinstein", "description": "Rubinstein bargaining", "overrides": {"bargaining_protocol": "rubinstein"}},
        ],
        "seed_policy": {"seeds": [0, 1, 2]},
        "run_budget": 6,
    }


@pytest.mark.orchestrator
class TestManifestService:
    def test_create_manifest(self, client):
        resp = client.post("/api/manifests", json=_valid_manifest_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert "manifest_id" in data
        assert data["name"] == "Test Experiment"

    def test_create_invalid_manifest(self, client):
        payload = _valid_manifest_payload()
        payload["treatments"] = [payload["treatments"][0]]  # Only 1 arm
        payload["run_budget"] = 3
        resp = client.post("/api/manifests", json=payload)
        assert resp.status_code == 422
        assert "errors" in resp.json()

    def test_get_manifest(self, client):
        create_resp = client.post("/api/manifests", json=_valid_manifest_payload())
        manifest_id = create_resp.json()["manifest_id"]

        resp = client.get(f"/api/manifests/{manifest_id}")
        assert resp.status_code == 200
        assert resp.json()["manifest_id"] == manifest_id

    def test_get_nonexistent_manifest(self, client):
        resp = client.get("/api/manifests/nonexistent")
        assert resp.status_code == 404

    def test_list_manifests(self, client):
        client.post("/api/manifests", json=_valid_manifest_payload())
        resp = client.get("/api/manifests")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_delete_manifest(self, client):
        create_resp = client.post("/api/manifests", json=_valid_manifest_payload())
        manifest_id = create_resp.json()["manifest_id"]

        resp = client.delete(f"/api/manifests/{manifest_id}")
        assert resp.status_code == 200

        resp = client.get(f"/api/manifests/{manifest_id}")
        assert resp.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_manifest_service.py -v`
Expected: FAIL

**Step 3: Implement manifest service**

Create `server/manifest_service.py` — the full CRUD router with validation.

The service should:
- Accept POST with manifest payload (without manifest_id, created_at, schema_version — assigned by service)
- Validate using `validate_manifest()`
- Persist to SQLite via `database.get_connection()`
- Return manifest data on GET endpoints
- Delete only if no jobs reference the manifest

**Step 4: Mount router in app.py**

Add to `server/app.py`:
```python
from server.manifest_service import manifest_router
app.include_router(manifest_router, prefix="/api")
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_manifest_service.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add server/manifest_service.py server/app.py tests/test_manifest_service.py
git commit -m "feat(manifest): add manifest CRUD API (B-103)"
```

---

## Task 7: Orchestrator service — job lifecycle (B-104)

**Files:**
- Create: `server/orchestrator_service.py`
- Create: `tests/test_orchestrator_service.py`
- Modify: `server/app.py`

**Step 1: Write failing tests for orchestrator lifecycle**

Create `tests/test_orchestrator_service.py` with tests for:
- `POST /api/jobs` creates job and returns job_id
- `GET /api/jobs/{id}` shows status and progress
- Job reaches `completed` status after all runs finish
- All runs have `completed` status with summary and data_path
- `POST /api/jobs/{id}/cancel` cancels remaining runs

Key: Use small experiments (2 agents, 5 grid, 10 ticks, 2 treatments, 2 seeds = 4 runs) to keep tests fast.

**Step 2: Run tests to verify they fail**

**Step 3: Implement orchestrator service**

Create `server/orchestrator_service.py`. The orchestrator should:
- Accept `POST /api/jobs` with `{"manifest_id": "..."}`
- Load manifest from SQLite
- Expand manifest into runs (treatment arms x seeds)
- Build `SimulationConfig` for each run using `base_config` + `overrides` + seed
- Map protocol names to instances using patterns from `batch.py` (`_get_protocol_name`, etc.)
- Launch background thread that executes runs sequentially
- Write Parquet via `write_run_parquet()` on each run completion
- Update SQLite run/job status throughout

For the config build, follow the pattern in `batch.py:_config_to_simulation_config()` and `_run_single()`. The orchestrator builds the logging `SimulationConfig` directly (not the server config) and populates `manifest_id` and `treatment_arm`.

**Step 4: Mount router in app.py**

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestrator_service.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add server/orchestrator_service.py server/app.py tests/test_orchestrator_service.py
git commit -m "feat(orchestrator): add async job execution service (B-104)"
```

---

## Task 8: Catalog service — run queries and replay (B-105)

**Files:**
- Create: `server/catalog_service.py`
- Create: `tests/test_catalog_service.py`
- Modify: `server/app.py`

**Step 1: Write failing tests for catalog service**

Tests should cover:
- `GET /api/catalog/runs` lists runs (empty initially)
- `GET /api/catalog/runs?manifest_id=X` filters by manifest
- `GET /api/catalog/runs?treatment_arm=Y` filters by treatment arm
- `GET /api/catalog/runs/{run_id}` returns run metadata + summary
- `GET /api/catalog/runs/{run_id}/replay` returns frontend-compatible replay payload
- Replay payload has same shape as existing `/api/runs/{name}` endpoint

For replay tests, create a manifest, run a job to completion, then verify the replay payload. Compare structure against the existing replay endpoint in `server/routes.py:179-310`.

**Step 2: Run tests to verify they fail**

**Step 3: Implement catalog service**

Create `server/catalog_service.py`. The catalog reads from SQLite for metadata queries and from Parquet for tick data. The replay endpoint transforms Parquet data into the same JSON shape as the existing `/api/runs/{name}` endpoint (see `server/routes.py:260-297` for the transformation pattern).

**Step 4: Mount router in app.py**

**Step 5: Run tests to verify they pass**

**Step 6: Commit**

```bash
git add server/catalog_service.py server/app.py tests/test_catalog_service.py
git commit -m "feat(catalog): add run catalog and replay service (B-105)"
```

---

## Task 9: Comparison reporting (B-106)

**Files:**
- Modify: `microecon/analysis/distributions.py`
- Modify: `server/catalog_service.py`
- Modify: `tests/test_catalog_service.py`

**Step 1: Write failing test for compare_values**

Add to the distributions test file or create a new test:

```python
def test_compare_values():
    from microecon.analysis.distributions import compare_values
    result = compare_values(
        values_a=[10.0, 12.0, 11.0],
        values_b=[15.0, 14.0, 16.0],
        metric_name="welfare",
        group_a_name="control",
        group_b_name="treatment",
    )
    assert result.group_a_mean == pytest.approx(11.0)
    assert result.group_b_mean == pytest.approx(15.0)
    assert result.difference == pytest.approx(4.0)
    assert result.effect_size > 0  # Treatment has higher values
```

**Step 2: Implement compare_values**

Add to `microecon/analysis/distributions.py`:

```python
def compare_values(
    values_a: list[float],
    values_b: list[float],
    metric_name: str,
    group_a_name: str = "Group A",
    group_b_name: str = "Group B",
) -> ComparisonResult:
    """Compare pre-extracted metric values between two groups.

    Like compare_groups() but operates on raw values instead of RunData.
    """
    # Same computation as compare_groups but without the extraction step
```

**Step 3: Write failing test for comparison endpoint**

Add to `tests/test_catalog_service.py`:

```python
def test_comparison_report(self, client):
    # Create manifest, run job, wait for completion
    # GET /api/catalog/compare/{manifest_id}
    # Assert pairwise comparisons structure
```

**Step 4: Implement comparison endpoint**

Add `GET /api/catalog/compare/{manifest_id}` to `server/catalog_service.py`. It queries completed runs from SQLite, extracts summary values, calls `compare_values()` for each pair of treatment arms and each metric.

**Step 5: Run all tests**

Run: `uv run pytest tests/test_catalog_service.py tests/test_parquet.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add microecon/analysis/distributions.py server/catalog_service.py tests/
git commit -m "feat(catalog): add pairwise comparison reporting (B-106)"
```

---

## Task 10: End-to-end integration tests (B-107)

**Files:**
- Create: `tests/test_orchestrator_integration.py`

**Step 1: Write end-to-end pipeline test**

```python
"""End-to-end integration tests (B-107 Level 4)."""

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.database import init_db


@pytest.mark.orchestrator
@pytest.mark.integration
class TestEndToEndPipeline:
    """Full manifest → run → catalog → compare pipeline."""

    def test_full_pipeline(self, client):
        # 1. Create manifest (2 arms, 3 seeds = 6 runs)
        resp = client.post("/api/manifests", json={...})
        manifest_id = resp.json()["manifest_id"]

        # 2. Launch job
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        job_id = resp.json()["job_id"]

        # 3. Poll until complete
        # (use a loop with timeout)

        # 4. Verify 6 runs
        resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}")
        assert len(resp.json()) == 6

        # 5. Verify 3 per arm
        resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}&treatment_arm=nash")
        assert len(resp.json()) == 3

        # 6. Get comparison report
        resp = client.get(f"/api/catalog/compare/{manifest_id}")
        data = resp.json()
        assert len(data["pairwise_comparisons"]) == 1  # 2 arms = 1 pair
        assert "final_welfare" in data["pairwise_comparisons"][0]["metrics"]

        # 7. Load replay
        run_id = client.get(f"/api/catalog/runs?manifest_id={manifest_id}").json()[0]["run_id"]
        resp = client.get(f"/api/catalog/runs/{run_id}/replay")
        assert resp.status_code == 200
        assert "ticks" in resp.json()
        assert "config" in resp.json()
```

**Step 2: Run test to verify it fails (services not yet wired)**

**Step 3: Fix any integration issues discovered**

**Step 4: Run full test suite**

Run: `uv run pytest -q`
Expected: All existing tests still pass, all new orchestrator tests pass

Run: `uv run pytest -m orchestrator -v`
Expected: All orchestrator tests pass

**Step 5: Commit**

```bash
git add tests/test_orchestrator_integration.py
git commit -m "test(orchestrator): add end-to-end integration tests (B-107)"
```

---

## Task 11: Final verification and cleanup

**Step 1: Run full test suite**

Run: `uv run pytest -q`
Expected: All tests pass (existing + new)

**Step 2: Run targeted suites**

Run: `uv run pytest -m orchestrator -v`
Expected: All orchestrator tests pass

Run: `uv run pytest -m contract -v`
Expected: Existing contract tests still pass (no regression)

Run: `uv run pytest -m determinism -v`
Expected: Existing determinism tests still pass

**Step 3: Frontend verification**

Run: `cd frontend && npm run lint && npm run build`
Expected: Clean lint, successful build (no frontend changes in this epic)

**Step 4: Update CLAUDE.md commands section**

Add orchestrator test command to the commands section in `CLAUDE.md`:
```
uv run pytest -m orchestrator            # Manifest/orchestrator service tests
```

**Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add orchestrator test command to CLAUDE.md"
```
