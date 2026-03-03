"""Orchestrator service for async experiment execution (B-104).

Provides REST endpoints for launching, monitoring, and cancelling
experiment jobs that execute manifest-defined simulation runs.

Design doc: docs/plans/2026-03-02-b-e1-manifest-orchestrator-design.md
"""

import json
import threading
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from microecon.bargaining import (
    AsymmetricNashBargainingProtocol,
    NashBargainingProtocol,
    RubinsteinBargainingProtocol,
    TIOLIBargainingProtocol,
)
from microecon.information import FullInformation, NoisyAlphaInformation
from microecon.logging.events import SimulationConfig as LoggingSimulationConfig
from microecon.logging.logger import SimulationLogger
from microecon.logging.parquet import write_run_parquet
from microecon.manifest import BaseConfig, ExperimentManifest, SeedPolicy, TreatmentArm
from microecon.matching import BilateralProposalMatching, CentralizedClearingMatching
from microecon.simulation import create_simple_economy
import server.database as db_mod
from server.database import get_connection

orchestrator_router = APIRouter()

# Track cancel events by job_id
_cancel_events: dict[str, threading.Event] = {}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateJobRequest(BaseModel):
    manifest_id: str


# ---------------------------------------------------------------------------
# Protocol factories
# ---------------------------------------------------------------------------

_BARGAINING_PROTOCOLS = {
    "nash": lambda: NashBargainingProtocol(),
    "rubinstein": lambda: RubinsteinBargainingProtocol(),
    "tioli": lambda: TIOLIBargainingProtocol(),
    "asymmetric_nash": lambda: AsymmetricNashBargainingProtocol(),
}

_MATCHING_PROTOCOLS = {
    "bilateral_proposal": lambda: BilateralProposalMatching(),
    "centralized_clearing": lambda: CentralizedClearingMatching(),
}

_INFO_ENVS = {
    "full": lambda params: FullInformation(),
    "full_information": lambda params: FullInformation(),
    "noisy_alpha": lambda params: NoisyAlphaInformation(
        noise_std=params.get("noise_std", 0.1)
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_manifest(manifest_id: str) -> dict[str, Any]:
    """Load manifest from SQLite, return raw dict. Raises HTTPException(404) if missing."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM manifests WHERE manifest_id = ?", (manifest_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Manifest not found")

    return {
        "manifest_id": row["manifest_id"],
        "name": row["name"],
        "created_at": row["created_at"],
        "schema_version": row["schema_version"],
        "objective": row["objective"],
        "hypotheses": json.loads(row["hypotheses"]),
        "base_config": json.loads(row["base_config"]),
        "treatments": json.loads(row["treatments"]),
        "seed_policy": json.loads(row["seed_policy"]),
        "run_budget": row["run_budget"],
    }


def _build_logging_config(
    base_config: BaseConfig,
    treatment: TreatmentArm,
    seed: int,
    run_id: str,
    manifest_id: str,
) -> LoggingSimulationConfig:
    """Build a LoggingSimulationConfig from base_config + treatment overrides."""
    overrides = treatment.overrides

    # Apply overrides to base config values
    n_agents = overrides.get("n_agents", base_config.n_agents)
    grid_size = overrides.get("grid_size", base_config.grid_size)
    perception_radius = overrides.get("perception_radius", base_config.perception_radius)
    discount_factor = overrides.get("discount_factor", base_config.discount_factor)
    info_env_name = overrides.get("info_env_name", base_config.info_env_name)
    info_env_params = overrides.get("info_env_params", base_config.info_env_params)

    # Bargaining protocol: treatment override or default "nash"
    protocol_name = overrides.get("bargaining_protocol", "nash")

    # Matching protocol: treatment override or default "bilateral_proposal"
    matching_protocol_name = overrides.get("matching_protocol", "bilateral_proposal")

    return LoggingSimulationConfig(
        n_agents=n_agents,
        grid_size=grid_size,
        seed=seed,
        protocol_name=protocol_name,
        protocol_params={},
        perception_radius=perception_radius,
        discount_factor=discount_factor,
        movement_budget=1,
        matching_protocol_name=matching_protocol_name,
        info_env_name=info_env_name,
        info_env_params=info_env_params,
        run_id=run_id,
        manifest_id=manifest_id,
        treatment_arm=treatment.name,
    )


def _update_job_progress(job_id: str, completed: int, total: int) -> None:
    """Update the progress JSON on a job row."""
    progress = json.dumps({"completed": completed, "total": total})
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE jobs SET progress = ? WHERE job_id = ?",
            (progress, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def _update_job_status(job_id: str, status: str, error_message: str | None = None) -> None:
    """Update job status and optionally set completed_at / error_message."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        if status in ("completed", "failed", "cancelled"):
            conn.execute(
                "UPDATE jobs SET status = ?, completed_at = ?, error_message = ? WHERE job_id = ?",
                (status, now, error_message, job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, started_at = ? WHERE job_id = ?",
                (status, now, job_id),
            )
        conn.commit()
    finally:
        conn.close()


def _update_run_status(
    run_id: str,
    status: str,
    summary: dict[str, Any] | None = None,
    data_path: str | None = None,
) -> None:
    """Update a run's status, summary, and data_path."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE runs SET status = ?, summary = ?, data_path = ?, completed_at = ? WHERE run_id = ?",
            (
                status,
                json.dumps(summary) if summary is not None else None,
                data_path,
                now if status in ("completed", "failed", "cancelled") else None,
                run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Background execution
# ---------------------------------------------------------------------------


def _execute_job(job_id: str, manifest_dict: dict[str, Any]) -> None:
    """Background thread: execute all runs for a job."""
    cancel_event = _cancel_events.get(job_id)

    # Parse manifest
    manifest = ExperimentManifest.from_dict(manifest_dict)
    base_config = manifest.base_config
    ticks = base_config.ticks

    # Gather run rows from DB
    conn = get_connection()
    try:
        run_rows = conn.execute(
            "SELECT run_id, treatment_arm, seed FROM runs WHERE job_id = ? ORDER BY treatment_arm, seed",
            (job_id,),
        ).fetchall()
    finally:
        conn.close()

    total = len(run_rows)
    completed_count = 0
    failed_count = 0

    _update_job_status(job_id, "running")

    for run_row in run_rows:
        # Check cancellation
        if cancel_event is not None and cancel_event.is_set():
            # Cancel remaining runs
            for remaining in run_rows:
                r_id = remaining["run_id"]
                conn = get_connection()
                try:
                    row = conn.execute(
                        "SELECT status FROM runs WHERE run_id = ?", (r_id,)
                    ).fetchone()
                    if row and row["status"] == "pending":
                        _update_run_status(r_id, "cancelled")
                finally:
                    conn.close()
            _update_job_status(job_id, "cancelled")
            _cancel_events.pop(job_id, None)
            return

        run_id = run_row["run_id"]
        treatment_arm_name = run_row["treatment_arm"]
        seed = run_row["seed"]

        # Find the treatment
        treatment = None
        for t in manifest.treatments:
            if t.name == treatment_arm_name:
                treatment = t
                break
        if treatment is None:
            _update_run_status(run_id, "failed")
            failed_count += 1
            completed_count += 1
            _update_job_progress(job_id, completed_count, total)
            continue

        try:
            # Set run status to running
            _update_run_status(run_id, "running")

            # Build logging config
            logging_config = _build_logging_config(
                base_config=base_config,
                treatment=treatment,
                seed=seed,
                run_id=run_id,
                manifest_id=manifest.manifest_id,
            )

            # Build protocol instances from names
            overrides = treatment.overrides
            protocol_name = overrides.get("bargaining_protocol", "nash")
            matching_name = overrides.get("matching_protocol", "bilateral_proposal")
            info_env_name = overrides.get("info_env_name", base_config.info_env_name)
            info_env_params = overrides.get("info_env_params", base_config.info_env_params)
            use_beliefs = overrides.get("use_beliefs", base_config.use_beliefs)
            n_agents = overrides.get("n_agents", base_config.n_agents)
            grid_size = overrides.get("grid_size", base_config.grid_size)
            perception_radius = overrides.get("perception_radius", base_config.perception_radius)
            discount_factor = overrides.get("discount_factor", base_config.discount_factor)

            bargaining_protocol = _BARGAINING_PROTOCOLS[protocol_name]()
            matching_protocol = _MATCHING_PROTOCOLS[matching_name]()
            info_env = _INFO_ENVS[info_env_name](info_env_params)

            # Create simulation
            sim = create_simple_economy(
                n_agents=n_agents,
                grid_size=grid_size,
                seed=seed,
                bargaining_protocol=bargaining_protocol,
                matching_protocol=matching_protocol,
                info_env=info_env,
                use_beliefs=use_beliefs,
                perception_radius=perception_radius,
                discount_factor=discount_factor,
            )

            # Create logger (in-memory only)
            logger = SimulationLogger(config=logging_config, output_path=None)
            sim.logger = logger

            # Run simulation
            for _ in range(ticks):
                sim.step()

            # Finalize
            run_data = logger.finalize()

            # Ensure data directory exists
            data_dir = db_mod.DATA_DIR
            data_dir.mkdir(parents=True, exist_ok=True)

            # Write Parquet
            parquet_path = data_dir / f"{run_id}.parquet"
            write_run_parquet(run_data, parquet_path)

            # Update run in SQLite
            summary_dict = run_data.summary.to_dict() if run_data.summary else None
            _update_run_status(
                run_id,
                "completed",
                summary=summary_dict,
                data_path=str(parquet_path),
            )

        except Exception:
            traceback.print_exc()
            _update_run_status(run_id, "failed")
            failed_count += 1

        completed_count += 1
        _update_job_progress(job_id, completed_count, total)

    # Final job status
    if failed_count > 0:
        _update_job_status(job_id, "failed", error_message=f"{failed_count} run(s) failed")
    else:
        _update_job_status(job_id, "completed")

    _cancel_events.pop(job_id, None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@orchestrator_router.post("/jobs", status_code=201)
async def create_job(request: CreateJobRequest) -> dict[str, Any]:
    """Launch a job from a manifest_id.

    Creates run rows for each treatment arm x seed combination,
    then launches a background thread to execute all runs.
    """
    # Load and verify manifest exists
    manifest_dict = _load_manifest(request.manifest_id)
    manifest = ExperimentManifest.from_dict(manifest_dict)

    # Create job
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    total_runs = len(manifest.treatments) * len(manifest.seed_policy.seeds)
    progress = json.dumps({"completed": 0, "total": total_runs})

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO jobs (job_id, manifest_id, status, created_at, progress)
               VALUES (?, ?, 'pending', ?, ?)""",
            (job_id, manifest.manifest_id, now, progress),
        )

        # Create run rows
        for treatment in manifest.treatments:
            for seed in manifest.seed_policy.seeds:
                run_id = str(uuid.uuid4())

                logging_config = _build_logging_config(
                    base_config=manifest.base_config,
                    treatment=treatment,
                    seed=seed,
                    run_id=run_id,
                    manifest_id=manifest.manifest_id,
                )

                conn.execute(
                    """INSERT INTO runs
                       (run_id, job_id, manifest_id, treatment_arm, seed,
                        status, config, created_at)
                       VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
                    (
                        run_id,
                        job_id,
                        manifest.manifest_id,
                        treatment.name,
                        seed,
                        json.dumps(logging_config.to_dict()),
                        now,
                    ),
                )

        conn.commit()
    finally:
        conn.close()

    # Set up cancel event and launch background thread
    cancel_event = threading.Event()
    _cancel_events[job_id] = cancel_event

    thread = threading.Thread(
        target=_execute_job,
        args=(job_id, manifest_dict),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


@orchestrator_router.get("/jobs")
async def list_jobs(
    manifest_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    """List jobs with optional filtering by manifest_id and status."""
    conn = get_connection()
    try:
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list[Any] = []

        if manifest_id is not None:
            query += " AND manifest_id = ?"
            params.append(manifest_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [_job_row_to_dict(row) for row in rows]
    finally:
        conn.close()


@orchestrator_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    """Get job details including progress."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return _job_row_to_dict(row)


@orchestrator_router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, str]:
    """Request cancellation of a running job."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT job_id, status FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    cancel_event = _cancel_events.get(job_id)
    if cancel_event is not None:
        cancel_event.set()

    return {"status": "cancel_requested", "job_id": job_id}


# ---------------------------------------------------------------------------
# Row conversion
# ---------------------------------------------------------------------------


def _job_row_to_dict(row) -> dict[str, Any]:
    """Convert a SQLite Row from the jobs table to a response dict."""
    progress = json.loads(row["progress"]) if row["progress"] else {"completed": 0, "total": 0}
    return {
        "job_id": row["job_id"],
        "manifest_id": row["manifest_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "error_message": row["error_message"],
        "progress": progress,
    }
