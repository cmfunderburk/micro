"""Manifest CRUD API (B-103).

Provides REST endpoints for creating, listing, fetching, and deleting
experiment manifests.

Design doc: docs/plans/2026-03-02-b-e1-manifest-orchestrator-design.md
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from microecon.manifest import (
    MANIFEST_SCHEMA_VERSION,
    BaseConfig,
    ExperimentManifest,
    SeedPolicy,
    TreatmentArm,
    validate_manifest,
)
from server.database import get_connection

manifest_router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TreatmentArmRequest(BaseModel):
    name: str
    description: str
    overrides: dict[str, Any] = {}


class SeedPolicyRequest(BaseModel):
    seeds: list[int]


class CreateManifestRequest(BaseModel):
    name: str
    objective: str
    hypotheses: list[str]
    base_config: dict[str, Any]
    treatments: list[TreatmentArmRequest]
    seed_policy: SeedPolicyRequest
    run_budget: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _manifest_row_to_dict(row) -> dict[str, Any]:
    """Convert a SQLite Row from the manifests table to a dict."""
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@manifest_router.post("/manifests", status_code=201)
async def create_manifest(request: CreateManifestRequest) -> dict[str, Any]:
    """Create a new experiment manifest.

    Validates the manifest, assigns an ID and timestamp, persists to SQLite,
    and returns the full manifest dict.
    """
    manifest_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # Build domain objects for validation
    try:
        base_config = BaseConfig.from_dict(request.base_config)
    except (KeyError, TypeError) as e:
        raise HTTPException(
            status_code=422,
            detail={"errors": [f"Invalid base_config: {e}"]},
        )
    treatments = [
        TreatmentArm(name=t.name, description=t.description, overrides=t.overrides)
        for t in request.treatments
    ]
    seed_policy = SeedPolicy(seeds=request.seed_policy.seeds)

    manifest = ExperimentManifest(
        manifest_id=manifest_id,
        name=request.name,
        created_at=created_at,
        schema_version=MANIFEST_SCHEMA_VERSION,
        objective=request.objective,
        hypotheses=request.hypotheses,
        base_config=base_config,
        treatments=treatments,
        seed_policy=seed_policy,
        run_budget=request.run_budget,
    )

    # Validate
    errors = validate_manifest(manifest)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    # Persist
    manifest_dict = manifest.to_dict()
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO manifests
               (manifest_id, name, created_at, schema_version,
                objective, hypotheses, base_config, treatments,
                seed_policy, run_budget)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                manifest_dict["manifest_id"],
                manifest_dict["name"],
                manifest_dict["created_at"],
                manifest_dict["schema_version"],
                manifest_dict["objective"],
                json.dumps(manifest_dict["hypotheses"]),
                json.dumps(manifest_dict["base_config"]),
                json.dumps(manifest_dict["treatments"]),
                json.dumps(manifest_dict["seed_policy"]),
                manifest_dict["run_budget"],
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return manifest_dict


@manifest_router.get("/manifests")
async def list_manifests() -> list[dict[str, Any]]:
    """List all experiment manifests."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM manifests ORDER BY created_at DESC").fetchall()
        return [_manifest_row_to_dict(row) for row in rows]
    finally:
        conn.close()


@manifest_router.get("/manifests/{manifest_id}")
async def get_manifest(manifest_id: str) -> dict[str, Any]:
    """Get a single manifest by ID."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM manifests WHERE manifest_id = ?", (manifest_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Manifest not found")

    return _manifest_row_to_dict(row)


@manifest_router.delete("/manifests/{manifest_id}")
async def delete_manifest(manifest_id: str) -> dict[str, str]:
    """Delete a manifest if no jobs reference it."""
    conn = get_connection()
    try:
        # Check manifest exists
        row = conn.execute(
            "SELECT manifest_id FROM manifests WHERE manifest_id = ?",
            (manifest_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Manifest not found")

        # Check no jobs reference this manifest
        job_count = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE manifest_id = ?",
            (manifest_id,),
        ).fetchone()[0]
        if job_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete manifest: {job_count} job(s) reference it",
            )

        conn.execute(
            "DELETE FROM manifests WHERE manifest_id = ?", (manifest_id,)
        )
        conn.commit()
    finally:
        conn.close()

    return {"status": "deleted", "manifest_id": manifest_id}
