# B-E1: Manifest and Orchestrator Services — Design

**Status:** Draft
**Date:** 2026-03-02
**Epic:** B-E1 (Gate B)
**Issues:** B-101 through B-107
**Upstream:** `docs/VISION/VISION-WORKFLOW-EXECUTION-BOARD.md` §5

---

## 1. Purpose

This document defines the design for the Manifest and Orchestrator Services epic — the backend infrastructure that moves experiment execution from ad-hoc scripting to a product service with persistence, provenance, and queryable results.

After Gate A, experiments are runnable via `BatchRunner` and `scripts/research_workflow.py`, but there is no formal experiment definition, no execution management, and no structured catalog of results. B-E1 fills these gaps.

---

## 2. Architecture Overview

```
┌─ Manifest Service (/api/manifests) ───────────────────┐
│ Create, validate, persist experiment definitions       │
│ B-101: Schema  B-102: Validator  B-103: CRUD API      │
└───────────────────────┬───────────────────────────────┘
                        │ manifest_id
┌─ Orchestrator Service (/api/jobs) ────────────────────┐
│ Launch, monitor, cancel experiment execution           │
│ B-104: Async job model with background threads         │
│                                                        │
│ Expands manifest into individual runs                  │
│ Populates run_id, manifest_id, treatment_arm           │
│ Writes Parquet tick data on completion                  │
└───────────────────────┬───────────────────────────────┘
                        │ run_id, data_path
┌─ Catalog Service (/api/catalog) ──────────────────────┐
│ Query runs, load replay data, compute comparisons      │
│ B-105: Run catalog  B-106: Comparison reporting        │
└───────────────────────────────────────────────────────┘
                        │
┌─ Storage Layer ───────────────────────────────────────┐
│ SQLite (microecon.db): manifests, jobs, runs metadata  │
│ Parquet (data/{run_id}.parquet): tick-level data       │
└───────────────────────────────────────────────────────┘
```

All three services are FastAPI routers sharing one SQLite database. Tick data is stored in per-run Parquet files for efficient analytical queries.

---

## 3. Manifest Schema (B-101)

A manifest is a complete, self-contained experiment definition.

### Data Model

```python
@dataclass(frozen=True)
class ExperimentManifest:
    # Identity
    manifest_id: str                      # UUID4, assigned on creation
    name: str                             # Human-readable label
    created_at: str                       # ISO 8601 timestamp
    schema_version: str                   # Manifest schema version

    # Intent
    objective: str                        # What question does this answer?
    hypotheses: list[str]                 # Expected outcomes (can be empty)

    # Fixed controls (held constant across all treatments)
    base_config: BaseConfig               # n_agents, grid_size, etc.

    # Treatments (what varies)
    treatments: list[TreatmentArm]        # At least 2 arms for comparison

    # Execution policy
    seed_policy: SeedPolicy               # Explicit seed list
    run_budget: int                       # len(treatments) × len(seeds)


@dataclass(frozen=True)
class BaseConfig:
    n_agents: int
    grid_size: int
    ticks: int                            # Simulation duration
    perception_radius: float = 7.0
    discount_factor: float = 0.95
    use_beliefs: bool = False
    info_env_name: str = "full"
    info_env_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TreatmentArm:
    name: str                             # e.g. "nash_bilateral"
    description: str                      # What this arm tests
    overrides: dict[str, Any]             # Fields that override base_config
    # e.g. {"bargaining_protocol": "nash", "matching_protocol": "bilateral_proposal"}


@dataclass(frozen=True)
class SeedPolicy:
    seeds: list[int]                      # Explicit seed list
```

### Design Rationale

- `base_config` + `TreatmentArm.overrides` mirrors the existing `BatchRunner` pattern (base + variations cartesian product).
- Treatment arms are named — this name becomes the `treatment_arm` field in each run's logging `SimulationConfig`.
- `objective` and `hypotheses` are free text — the manifest captures experimental intent, not just configuration.
- `seed_policy` uses explicit seed lists, consistent with the determinism policy.
- `run_budget` is derived (`len(treatments) × len(seeds)`) but stored for validation.
- `ticks` in `BaseConfig` defines simulation duration — required by `Simulation.step()` loop and `BatchRunner.run(ticks=...)`.
- Treatment arm `overrides` can include `bargaining_protocol` and `matching_protocol` — the orchestrator builds logging `SimulationConfig` directly and calls `create_simple_economy()`, bypassing the server `SimulationConfig` which does not expose matching protocol selection.

---

## 4. Manifest Validation (B-102)

Validation runs on creation before persistence. Rejects invalid manifests with actionable error messages.

### Validation Rules

| Rule | Check |
|------|-------|
| Required fields | All fields present and non-empty |
| Treatment count | `len(treatments) >= 2` |
| Seed policy | `len(seed_policy.seeds) >= 1`, all seeds are integers |
| Run budget | `run_budget == len(treatments) * len(seed_policy.seeds)` |
| Base config bounds | `n_agents > 0`, `grid_size > 0`, `perception_radius > 0` |
| Override keys | All keys in `overrides` are recognized config fields |
| Protocol names | Bargaining protocol in `{nash, rubinstein, tioli, asymmetric_nash}` |
| Matching protocol names | Matching protocol in `{bilateral_proposal, centralized_clearing}` |
| Info env names | Info env in `{full, full_information, noisy_alpha}` |
| Treatment arm names | Unique across all arms |
| Seed uniqueness | No duplicate seeds in seed_policy |

Validation returns a list of errors, not just the first one.

---

## 5. SQLite Schema

### Tables

```sql
CREATE TABLE manifests (
    manifest_id    TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    objective      TEXT NOT NULL,
    hypotheses     TEXT NOT NULL,           -- JSON array of strings
    base_config    TEXT NOT NULL,           -- JSON blob
    treatments     TEXT NOT NULL,           -- JSON array of TreatmentArm
    seed_policy    TEXT NOT NULL,           -- JSON blob
    run_budget     INTEGER NOT NULL
);

CREATE TABLE jobs (
    job_id         TEXT PRIMARY KEY,
    manifest_id    TEXT NOT NULL REFERENCES manifests(manifest_id),
    status         TEXT NOT NULL DEFAULT 'pending',
                   -- pending | running | completed | failed | cancelled
    created_at     TEXT NOT NULL,
    started_at     TEXT,
    completed_at   TEXT,
    error_message  TEXT,
    progress       TEXT                     -- JSON: {"completed": 4, "total": 12}
);

CREATE TABLE runs (
    run_id         TEXT PRIMARY KEY,
    job_id         TEXT NOT NULL REFERENCES jobs(job_id),
    manifest_id    TEXT NOT NULL REFERENCES manifests(manifest_id),
    treatment_arm  TEXT NOT NULL,
    seed           INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
                   -- pending | running | completed | failed | cancelled
    config         TEXT NOT NULL,           -- JSON blob (full SimulationConfig)
    summary        TEXT,                    -- JSON blob (RunSummary, on completion)
    data_path      TEXT,                    -- path to Parquet file
    created_at     TEXT NOT NULL,
    completed_at   TEXT
);
```

### Indexes

```sql
CREATE INDEX idx_jobs_manifest ON jobs(manifest_id);
CREATE INDEX idx_runs_job ON runs(job_id);
CREATE INDEX idx_runs_manifest ON runs(manifest_id);
CREATE INDEX idx_runs_treatment ON runs(manifest_id, treatment_arm);
```

### Connection Configuration

- WAL mode enabled for concurrent read/write (orchestrator writes while catalog reads)
- Foreign keys enabled per connection (`PRAGMA foreign_keys = ON`)
- One connection per thread (SQLite connections are not thread-safe, but separate connections to a WAL-mode database support concurrency)

---

## 6. Parquet Data Layout

Each completed run produces one Parquet file at `data/{run_id}.parquet`, written as a single batch on run completion.

### Column Schema

The Parquet schema is lossless — every field in `TickRecord` is preserved for full `RunData` round-trip equivalence.

```
-- Flat metric columns (fast analytical queries)
tick                    INT32
total_welfare           FLOAT64
cumulative_trades       INT32
trade_count             INT32               -- derived: len(trades)
welfare_gains           FLOAT64             -- derived: total_welfare - initial_welfare

-- Agent state (per-tick snapshot of all agents)
agent_snapshots         LIST<STRUCT>
  agent_id              STRING
  position              LIST<INT32>         -- [row, col]
  endowment             LIST<FLOAT64>       -- [x, y]
  alpha                 FLOAT64
  utility               FLOAT64
  has_beliefs           BOOL
  n_trades_in_memory    INT32
  n_type_beliefs        INT32

-- Search decisions (per-agent target evaluation)
search_decisions        LIST<STRUCT>
  agent_id              STRING
  position              LIST<INT32>
  visible_agents        INT32
  evaluations           STRING              -- JSON (variable-length nested TargetEvaluation list)
  chosen_target_id      STRING              -- nullable
  chosen_value          FLOAT64

-- Movement events
movements               LIST<STRUCT>
  agent_id              STRING
  from_pos              LIST<INT32>
  to_pos                LIST<INT32>
  target_id             STRING              -- nullable
  reason                STRING

-- Trade events
trades                  LIST<STRUCT>
  agent1_id             STRING
  agent2_id             STRING
  proposer_id           STRING
  pre_holdings          LIST<LIST<FLOAT64>>
  post_allocations      LIST<LIST<FLOAT64>>
  gains                 LIST<FLOAT64>
  trade_occurred        BOOL

-- Commitment events (for future committed matching protocols)
commitments_formed      LIST<STRUCT>
  agent_a               STRING
  agent_b               STRING

commitments_broken      LIST<STRUCT>
  agent_a               STRING
  agent_b               STRING
  reason                STRING

-- Belief snapshots
belief_snapshots        LIST<STRUCT>
  agent_id              STRING
  type_beliefs          STRING              -- JSON (variable structure)
  price_beliefs         STRING              -- JSON (variable structure)
  n_trades_in_memory    INT32
```

### Design Rationale

- **Lossless**: Every `TickRecord` field is represented. `write_run_parquet` → `read_run_parquet` produces identical `RunData`.
- **Flat metric columns** (`total_welfare`, `cumulative_trades`, etc.) are top-level for fast analytical queries without deserialization.
- **Nested structs** for agent snapshots, trades, movements — Arrow handles these natively; only read for replay or agent-level analysis.
- **JSON strings** for variable-structure data (search evaluations list, belief internals) — avoids deep schema rigidity for data whose shape varies by agent count and config.
- **One row per tick** — a 100-tick run is 100 rows regardless of agent count (agents are nested).
- **Default Snappy compression** — good balance of speed and size.

### Query Patterns

| Use case | Read pattern |
|----------|-------------|
| Welfare timeseries | `total_welfare` column only |
| Cross-run comparison | `total_welfare` from N files via Arrow dataset API |
| Replay tick N | Row N, all columns |
| Agent trajectory | `agent_snapshots` column, filter by agent_id |
| Trade inspection | `trades` column at specific tick |

### Parquet Module

New file: `microecon/logging/parquet.py`

```python
def write_run_parquet(run_data: RunData, path: Path) -> None:
    """Convert RunData to Arrow table and write Parquet file."""

def read_run_parquet(path: Path) -> RunData:
    """Read Parquet file back into RunData for replay."""

def read_ticks_parquet(path: Path, tick: int | None = None) -> list[TickRecord]:
    """Read specific tick(s) from Parquet."""

def read_column_parquet(path: Path, column: str) -> pa.Array:
    """Read a single column for fast analytical queries."""
```

This module sits alongside the existing `formats.py` (JSON lines) as an alternative storage backend.

---

## 7. Service Endpoints

### Manifest Service (`server/manifest_service.py`)

```
POST   /api/manifests              Create manifest (validate, assign ID, persist)
GET    /api/manifests              List all manifests (summary view)
GET    /api/manifests/{id}         Get full manifest by ID
DELETE /api/manifests/{id}         Delete manifest (only if no jobs reference it)
```

### Orchestrator Service (`server/orchestrator_service.py`)

```
POST   /api/jobs                   Launch job from manifest_id (returns job_id)
GET    /api/jobs                   List jobs (filterable by manifest_id, status)
GET    /api/jobs/{id}              Get job status and progress
POST   /api/jobs/{id}/cancel       Request cancellation
```

### Catalog Service (`server/catalog_service.py`)

```
GET    /api/catalog/runs                    List runs (filter by manifest_id, treatment_arm, status)
GET    /api/catalog/runs/{run_id}           Run metadata and summary
GET    /api/catalog/runs/{run_id}/ticks     Tick data from Parquet (?tick=N for single tick)
GET    /api/catalog/runs/{run_id}/replay    Full replay payload (same shape as /api/runs/{name})
GET    /api/catalog/compare/{manifest_id}   Comparison report across treatment arms
```

The `/replay` endpoint produces the same payload shape as the existing `/api/runs/{run_name}` endpoint. The frontend replay mode works without changes.

---

## 8. Orchestrator Execution Flow

### Job Launch (B-104)

1. Client sends `POST /api/jobs` with `{"manifest_id": "..."}`
2. Service validates manifest exists
3. Creates job row (status=pending)
4. Expands manifest into individual runs: for each treatment arm × each seed, creates a run row (status=pending) with fully-populated `SimulationConfig` including `manifest_id` and `treatment_arm`
5. Returns `{"job_id": "..."}` immediately
6. Launches background thread for execution

### Background Execution

```
For each run in job (ordered by treatment_arm, then seed):
    1. Set run status = running
    2. Build SimulationConfig from base_config + treatment overrides + seed
       - Set manifest_id, treatment_arm, run_id
    3. Create simulation via create_simple_economy()
    4. Attach SimulationLogger (in-memory, output_path=None)
    5. Run simulation for base_config.ticks steps
    6. Finalize logger → RunData
    7. Write Parquet: data/{run_id}.parquet
    8. Update run row: status=completed, summary, data_path
    9. Update job progress: {"completed": N, "total": M}
```

### Cancellation

- `POST /api/jobs/{id}/cancel` sets a `threading.Event`
- Background thread checks the event between runs
- All remaining unstarted runs are set to status=cancelled
- Job status set to cancelled
- The currently running run (if any) completes — cancellation is between-run, not mid-run

### Failure Handling

- If a single run fails, its status is set to failed with the error
- The job continues executing remaining runs
- Job status is failed only after all runs have been attempted, if any failed

---

## 9. Comparison Reporting (B-106)

The `/api/catalog/compare/{manifest_id}` endpoint:

1. Queries all completed runs for the manifest, grouped by `treatment_arm`
2. Extracts summary metric values from SQLite `runs.summary` JSON (no Parquet read needed)
3. Generates **pairwise comparisons** for all treatment arm pairs — a manifest with N arms produces N×(N-1)/2 pairs
4. For each pair and each metric (`final_welfare`, `total_trades`, `welfare_gain`), computes means, difference, and Cohen's d effect size

The comparison operates on pre-extracted summary values from SQLite, not full `RunData` objects. A new `compare_values()` function accepts `list[float]` directly, complementing the existing `compare_groups()` which requires `RunData` + extractor.

Response shape:

```json
{
    "manifest_id": "...",
    "treatments": ["nash_bilateral", "rubinstein_centralized", "tioli_bilateral"],
    "runs_per_arm": {"nash_bilateral": 5, "rubinstein_centralized": 5, "tioli_bilateral": 5},
    "pairwise_comparisons": [
        {
            "arm_a": "nash_bilateral",
            "arm_b": "rubinstein_centralized",
            "metrics": {
                "final_welfare": {
                    "arm_a_mean": 45.2,
                    "arm_b_mean": 48.1,
                    "difference": 2.9,
                    "effect_size": 0.45,
                    "arm_a_values": [44.1, 45.8, ...],
                    "arm_b_values": [47.2, 49.0, ...]
                },
                "total_trades": { ... },
                "welfare_gain": { ... }
            }
        },
        {
            "arm_a": "nash_bilateral",
            "arm_b": "tioli_bilateral",
            "metrics": { ... }
        },
        {
            "arm_a": "rubinstein_centralized",
            "arm_b": "tioli_bilateral",
            "metrics": { ... }
        }
    ]
}
```

This generalizes to any number of treatment arms (>= 2). Confidence intervals and sensitivity analysis are deferred to a later iteration.

---

## 10. Database Module

New file: `server/database.py`

```python
DB_PATH = Path("microecon.db")
DATA_DIR = Path("data")

def init_db(path: Path = DB_PATH) -> None:
    """Create tables and indexes if they don't exist."""

def get_connection(path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a connection with WAL mode and foreign keys enabled."""
```

- `init_db()` called once in `create_app()` (FastAPI factory)
- Services create their own connections as needed
- Background threads get their own connections

Both `microecon.db` and `data/` are added to `.gitignore`.

---

## 11. File Layout

### New Files

```
server/
├── database.py                  # SQLite connection, schema init
├── manifest_service.py          # Manifest CRUD + validation router
├── orchestrator_service.py      # Job lifecycle router + background execution
├── catalog_service.py           # Run catalog + comparison reporting router

microecon/logging/
├── parquet.py                   # Parquet read/write for tick data
```

### Modified Files

```
server/app.py                    # Mount new routers
pyproject.toml                   # Add pyarrow dependency
.gitignore                       # Add microecon.db, data/
```

---

## 12. Migration Strategy

Clean break from the JSON lines format. The orchestrator writes to SQLite + Parquet only.

- Existing `runs/` directory is legacy and untouched
- Existing `/api/runs` and `/api/runs/{name}` endpoints continue to work for legacy runs
- New orchestrated runs use `/api/catalog/*` endpoints
- No dual-path maintenance — two separate systems that coexist
- A one-time import tool (legacy JSON lines → SQLite + Parquet) can be built later if needed

---

## 13. Testing Strategy (B-107)

Four levels, mirroring the Gate A contract conformance approach.

### Level 1: Manifest Round-Trip
- Create manifest → serialize to SQLite → deserialize → assert equality
- Validator rejects invalid manifests (missing fields, bad bounds, unknown protocols)
- Validator accepts valid manifests and returns no errors

### Level 2: Orchestrator Lifecycle
- Create manifest → launch job → poll status → verify completed
- All runs have status=completed, summary populated, data_path set
- Cancel mid-execution → remaining runs skipped, job status=cancelled
- Failed run → run status=failed, job continues, job status=failed at end

### Level 3: Parquet Round-Trip
- Run simulation → write Parquet → read back → assert tick data matches original RunData
- Single-column read (`total_welfare`) returns correct values
- Single-tick read returns correct row with all nested data

### Level 4: End-to-End Pipeline
- Create manifest (2 treatment arms, 3 seeds = 6 runs)
- Launch job, wait for completion
- Query catalog by manifest_id → 6 runs returned
- Query catalog by treatment_arm → 3 runs per arm
- Get comparison report → ComparisonResult with effect size for each metric
- Load replay for one run → payload matches expected shape for frontend consumption

Test marker: `orchestrator` added to `pyproject.toml`.

---

## 14. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `pyarrow` | >= 14.0 | Parquet read/write, Arrow table operations |

No other new dependencies. SQLite is in the Python standard library.

---

## 15. Acceptance Criteria Summary

| Issue | Criterion |
|-------|-----------|
| B-101 | Manifest schema can describe baseline + treatment experiments with objective, assumptions, treatments, sweep seeds, tick count, and run budget |
| B-102 | Invalid manifests rejected pre-run with actionable error list |
| B-103 | Manifests created, read, listed, deleted via REST API; addressable by ID |
| B-104 | Jobs launched asynchronously, status polled, cancellation supported; runs populate manifest_id and treatment_arm in SimulationConfig |
| B-105 | Runs queryable by manifest_id and treatment_arm; replay endpoint produces frontend-compatible payload from Parquet data |
| B-106 | Comparison report computes pairwise per-metric effect size (Cohen's d) across all treatment arm pairs for a manifest, using summary values from SQLite |
| B-107 | Four-level test suite passes: manifest round-trip, orchestrator lifecycle, Parquet round-trip, end-to-end pipeline |
