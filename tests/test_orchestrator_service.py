"""Tests for orchestrator service (B-104, B-107 Level 2)."""

import time
import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.database import init_db
import server.database as db_mod


@pytest.fixture
def client(tmp_path):
    """Create test client with isolated database and data directory."""
    db_path = tmp_path / "test.db"
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    original_db_path = db_mod.DB_PATH
    original_data_dir = db_mod.DATA_DIR
    db_mod.DB_PATH = db_path
    db_mod.DATA_DIR = data_dir

    init_db(db_path)
    app = create_app()

    with TestClient(app) as c:
        yield c

    db_mod.DB_PATH = original_db_path
    db_mod.DATA_DIR = original_data_dir


def _create_manifest(client):
    """Create a small manifest and return its ID."""
    payload = {
        "name": "Small Test",
        "objective": "Test orchestrator",
        "hypotheses": [],
        "base_config": {"n_agents": 2, "grid_size": 5, "ticks": 5},
        "treatments": [
            {"name": "nash", "description": "Nash", "overrides": {"bargaining_protocol": "nash"}},
            {"name": "rubinstein", "description": "Rubinstein", "overrides": {"bargaining_protocol": "rubinstein"}},
        ],
        "seed_policy": {"seeds": [0, 1]},
        "run_budget": 4,
    }
    resp = client.post("/api/manifests", json=payload)
    assert resp.status_code == 201
    return resp.json()["manifest_id"]


def _wait_for_job(client, job_id, timeout=60):
    """Poll job status until completed/failed/cancelled."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/jobs/{job_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed", "cancelled"):
            return resp.json()
        time.sleep(0.5)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


@pytest.mark.orchestrator
class TestOrchestratorService:
    def test_create_job(self, client):
        manifest_id = _create_manifest(client)
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        assert resp.status_code == 201
        assert "job_id" in resp.json()

    def test_job_completes(self, client):
        manifest_id = _create_manifest(client)
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        job_id = resp.json()["job_id"]

        job = _wait_for_job(client, job_id)
        assert job["status"] == "completed"

    def test_all_runs_completed(self, client):
        manifest_id = _create_manifest(client)
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        job_id = resp.json()["job_id"]

        _wait_for_job(client, job_id)

        # Check all runs via direct DB query
        conn = db_mod.get_connection(db_mod.DB_PATH)
        runs = conn.execute(
            "SELECT status, summary, data_path FROM runs WHERE job_id = ?",
            (job_id,),
        ).fetchall()
        conn.close()

        assert len(runs) == 4  # 2 treatments x 2 seeds
        for run in runs:
            assert run["status"] == "completed"
            assert run["summary"] is not None
            assert run["data_path"] is not None

    def test_job_progress(self, client):
        manifest_id = _create_manifest(client)
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        job_id = resp.json()["job_id"]

        _wait_for_job(client, job_id)

        resp = client.get(f"/api/jobs/{job_id}")
        job = resp.json()
        assert job["progress"]["total"] == 4
        assert job["progress"]["completed"] == 4

    def test_list_jobs(self, client):
        manifest_id = _create_manifest(client)
        client.post("/api/jobs", json={"manifest_id": manifest_id})

        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_jobs_filter_by_manifest(self, client):
        manifest_id = _create_manifest(client)
        client.post("/api/jobs", json={"manifest_id": manifest_id})

        # Filter by this manifest
        resp = client.get(f"/api/jobs?manifest_id={manifest_id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Filter by nonexistent manifest
        resp = client.get("/api/jobs?manifest_id=nonexistent")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_list_jobs_filter_by_status(self, client):
        manifest_id = _create_manifest(client)
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        job_id = resp.json()["job_id"]
        _wait_for_job(client, job_id)

        resp = client.get("/api/jobs?status=completed")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        resp = client.get("/api/jobs?status=pending")
        assert resp.status_code == 200
        # The completed job should not appear in pending filter
        job_ids = [j["job_id"] for j in resp.json()]
        assert job_id not in job_ids

    def test_invalid_manifest_id(self, client):
        resp = client.post("/api/jobs", json={"manifest_id": "nonexistent"})
        assert resp.status_code == 404

    def test_get_nonexistent_job(self, client):
        resp = client.get("/api/jobs/nonexistent")
        assert resp.status_code == 404

    def test_cancel_job(self, client):
        """Test cancelling a job — use a manifest with enough runs to have pending ones."""
        # Create a manifest with more runs so cancellation has a chance
        payload = {
            "name": "Cancel Test",
            "objective": "Test cancellation",
            "hypotheses": [],
            "base_config": {"n_agents": 2, "grid_size": 5, "ticks": 5},
            "treatments": [
                {"name": "nash", "description": "Nash", "overrides": {"bargaining_protocol": "nash"}},
                {"name": "rubinstein", "description": "Rubinstein", "overrides": {"bargaining_protocol": "rubinstein"}},
            ],
            "seed_policy": {"seeds": [0, 1, 2, 3]},
            "run_budget": 8,
        }
        resp = client.post("/api/manifests", json=payload)
        manifest_id = resp.json()["manifest_id"]

        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        job_id = resp.json()["job_id"]

        # Request cancellation immediately
        resp = client.post(f"/api/jobs/{job_id}/cancel")
        assert resp.status_code == 200

        # Wait for the job to finish (completed or cancelled)
        job = _wait_for_job(client, job_id)
        # Job could be cancelled or completed depending on timing
        assert job["status"] in ("cancelled", "completed")

    def test_cancel_nonexistent_job(self, client):
        resp = client.post("/api/jobs/nonexistent/cancel")
        assert resp.status_code == 404

    def test_parquet_files_written(self, client):
        """Verify that Parquet files are written for completed runs."""
        import pathlib

        manifest_id = _create_manifest(client)
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        job_id = resp.json()["job_id"]

        _wait_for_job(client, job_id)

        conn = db_mod.get_connection(db_mod.DB_PATH)
        runs = conn.execute(
            "SELECT data_path FROM runs WHERE job_id = ?",
            (job_id,),
        ).fetchall()
        conn.close()

        for run in runs:
            path = pathlib.Path(run["data_path"])
            assert path.exists(), f"Parquet file not found: {path}"
            assert path.suffix == ".parquet"

    def test_run_configs_have_manifest_metadata(self, client):
        """Verify that run configs in DB have manifest_id and treatment_arm."""
        import json

        manifest_id = _create_manifest(client)
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        job_id = resp.json()["job_id"]

        _wait_for_job(client, job_id)

        conn = db_mod.get_connection(db_mod.DB_PATH)
        runs = conn.execute(
            "SELECT config, treatment_arm, manifest_id FROM runs WHERE job_id = ?",
            (job_id,),
        ).fetchall()
        conn.close()

        for run in runs:
            config = json.loads(run["config"])
            assert config["manifest_id"] == manifest_id
            assert config["treatment_arm"] in ("nash", "rubinstein")
            assert run["manifest_id"] == manifest_id
            assert run["treatment_arm"] in ("nash", "rubinstein")
