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


def init_db(path: Path | None = None) -> None:
    """Create tables and indexes if they don't exist."""
    conn = get_connection(path)
    conn.executescript(_SCHEMA_SQL)
    conn.close()


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    """Return a connection with WAL mode and foreign keys enabled."""
    if path is None:
        path = DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn
