"""End-to-end integration tests (B-107 Level 4)."""

import time
import json

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


def _wait_for_job(client, job_id, timeout=120):
    """Poll job status until terminal state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/jobs/{job_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed", "cancelled"):
            return resp.json()
        time.sleep(0.5)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


@pytest.mark.orchestrator
@pytest.mark.integration
class TestEndToEndPipeline:
    """Full manifest -> run -> catalog -> compare -> replay pipeline."""

    def test_full_pipeline(self, client):
        # 1. Create manifest (2 arms, 3 seeds = 6 runs)
        manifest_payload = {
            "name": "Integration Test Experiment",
            "objective": "Verify full B-E1 pipeline end-to-end",
            "hypotheses": ["Nash and Rubinstein produce different welfare outcomes"],
            "base_config": {
                "n_agents": 2,
                "grid_size": 5,
                "ticks": 5,
            },
            "treatments": [
                {
                    "name": "nash",
                    "description": "Nash bargaining protocol",
                    "overrides": {"bargaining_protocol": "nash"},
                },
                {
                    "name": "rubinstein",
                    "description": "Rubinstein bargaining protocol",
                    "overrides": {"bargaining_protocol": "rubinstein"},
                },
            ],
            "seed_policy": {"seeds": [0, 1, 2]},
            "run_budget": 6,
        }
        resp = client.post("/api/manifests", json=manifest_payload)
        assert resp.status_code == 201, f"Create manifest failed: {resp.text}"
        manifest_id = resp.json()["manifest_id"]

        # Verify manifest is readable
        resp = client.get(f"/api/manifests/{manifest_id}")
        assert resp.status_code == 200
        manifest = resp.json()
        assert manifest["run_budget"] == 6

        # 2. Launch job
        resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
        assert resp.status_code == 201
        job_id = resp.json()["job_id"]

        # 3. Wait for completion
        job = _wait_for_job(client, job_id)
        assert job["status"] == "completed", f"Job failed: {job.get('error_message')}"

        # 4. Verify 6 runs total
        resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}")
        assert resp.status_code == 200
        runs = resp.json()
        assert len(runs) == 6, f"Expected 6 runs, got {len(runs)}"

        # 5. Verify 3 runs per treatment arm
        resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}&treatment_arm=nash")
        assert resp.status_code == 200
        nash_runs = resp.json()
        assert len(nash_runs) == 3

        resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}&treatment_arm=rubinstein")
        assert resp.status_code == 200
        rubinstein_runs = resp.json()
        assert len(rubinstein_runs) == 3

        # 6. Verify all runs are completed with summaries
        for run in runs:
            assert run["status"] == "completed"

        # 7. Get comparison report
        resp = client.get(f"/api/catalog/compare/{manifest_id}")
        assert resp.status_code == 200
        comparison = resp.json()

        assert comparison["manifest_id"] == manifest_id
        assert len(comparison["treatments"]) == 2
        assert len(comparison["pairwise_comparisons"]) == 1  # 2 arms = 1 pair

        pair = comparison["pairwise_comparisons"][0]
        assert "final_welfare" in pair["metrics"]
        assert "total_trades" in pair["metrics"]
        assert "welfare_gain" in pair["metrics"]

        # Each metric should have 3 values per arm (3 seeds)
        fw = pair["metrics"]["final_welfare"]
        assert len(fw["arm_a_values"]) == 3
        assert len(fw["arm_b_values"]) == 3
        assert isinstance(fw["effect_size"], float)

        # 8. Load replay for one run
        run_id = runs[0]["run_id"]
        resp = client.get(f"/api/catalog/runs/{run_id}/replay")
        assert resp.status_code == 200
        replay = resp.json()

        assert "name" in replay
        assert "config" in replay
        assert "schema_version" in replay
        assert "ticks" in replay
        assert "n_ticks" in replay
        assert replay["n_ticks"] == 5

        # Verify tick structure matches frontend format
        tick = replay["ticks"][0]
        assert "agents" in tick
        assert "trades" in tick
        assert "metrics" in tick
        assert "beliefs" in tick

        # Verify config has provenance fields
        assert replay["config"]["manifest_id"] == manifest_id
        assert replay["config"]["treatment_arm"] is not None
