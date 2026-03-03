"""Tests for catalog service (B-105)."""

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


def _create_and_run_experiment(client):
    """Create a manifest, launch a job, wait for completion. Returns (manifest_id, job_id)."""
    payload = {
        "name": "Catalog Test",
        "objective": "Test catalog queries",
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
    manifest_id = resp.json()["manifest_id"]

    resp = client.post("/api/jobs", json={"manifest_id": manifest_id})
    job_id = resp.json()["job_id"]

    # Wait for completion
    deadline = time.time() + 60
    while time.time() < deadline:
        resp = client.get(f"/api/jobs/{job_id}")
        if resp.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)

    return manifest_id, job_id


@pytest.mark.orchestrator
class TestCatalogService:
    def test_list_runs(self, client):
        manifest_id, _ = _create_and_run_experiment(client)
        resp = client.get("/api/catalog/runs")
        assert resp.status_code == 200
        assert len(resp.json()) == 4  # 2 treatments x 2 seeds

    def test_filter_by_manifest(self, client):
        manifest_id, _ = _create_and_run_experiment(client)
        resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 4

    def test_filter_by_treatment_arm(self, client):
        manifest_id, _ = _create_and_run_experiment(client)
        resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}&treatment_arm=nash")
        assert resp.status_code == 200
        runs = resp.json()
        assert len(runs) == 2
        assert all(r["treatment_arm"] == "nash" for r in runs)

    def test_get_run_metadata(self, client):
        manifest_id, _ = _create_and_run_experiment(client)
        runs_resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}")
        run_id = runs_resp.json()[0]["run_id"]

        resp = client.get(f"/api/catalog/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert "config" in data
        assert "summary" in data

    def test_get_nonexistent_run(self, client):
        resp = client.get("/api/catalog/runs/nonexistent")
        assert resp.status_code == 404

    def test_get_ticks(self, client):
        manifest_id, _ = _create_and_run_experiment(client)
        runs_resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}")
        run_id = runs_resp.json()[0]["run_id"]

        resp = client.get(f"/api/catalog/runs/{run_id}/ticks")
        assert resp.status_code == 200
        ticks = resp.json()
        assert len(ticks) == 5  # 5 ticks
        assert ticks[0]["tick"] == 1  # Simulation ticks start at 1

    def test_get_single_tick(self, client):
        manifest_id, _ = _create_and_run_experiment(client)
        runs_resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}")
        run_id = runs_resp.json()[0]["run_id"]

        resp = client.get(f"/api/catalog/runs/{run_id}/ticks?tick=2")
        assert resp.status_code == 200
        ticks = resp.json()
        assert len(ticks) == 1
        assert ticks[0]["tick"] == 2

    def test_replay_endpoint(self, client):
        manifest_id, _ = _create_and_run_experiment(client)
        runs_resp = client.get(f"/api/catalog/runs?manifest_id={manifest_id}")
        run_id = runs_resp.json()[0]["run_id"]

        resp = client.get(f"/api/catalog/runs/{run_id}/replay")
        assert resp.status_code == 200
        data = resp.json()

        # Must match existing replay format
        assert "name" in data
        assert "config" in data
        assert "schema_version" in data
        assert "ticks" in data
        assert "n_ticks" in data
        assert data["n_ticks"] == 5

        # Check tick structure
        tick = data["ticks"][0]
        assert "agents" in tick
        assert "trades" in tick
        assert "metrics" in tick
        assert "beliefs" in tick
        assert "total_welfare" in tick["metrics"]
        assert "welfare_gains" in tick["metrics"]
        assert "cumulative_trades" in tick["metrics"]

        # Check agent structure
        agent = tick["agents"][0]
        assert "id" in agent
        assert "x" in agent
        assert "y" in agent
        assert "utility" in agent
        assert "alpha" in agent

    def test_comparison_report(self, client):
        manifest_id, _ = _create_and_run_experiment(client)
        resp = client.get(f"/api/catalog/compare/{manifest_id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["manifest_id"] == manifest_id
        assert len(data["treatments"]) == 2
        assert len(data["pairwise_comparisons"]) == 1  # 2 arms = 1 pair

        comparison = data["pairwise_comparisons"][0]
        assert "arm_a" in comparison
        assert "arm_b" in comparison
        assert "final_welfare" in comparison["metrics"]
        assert "total_trades" in comparison["metrics"]
        assert "welfare_gain" in comparison["metrics"]

        # Check metric structure
        fw = comparison["metrics"]["final_welfare"]
        assert "arm_a_mean" in fw
        assert "arm_b_mean" in fw
        assert "difference" in fw
        assert "effect_size" in fw
        assert "arm_a_values" in fw
        assert "arm_b_values" in fw

    def test_comparison_report_not_found(self, client):
        resp = client.get("/api/catalog/compare/nonexistent")
        assert resp.status_code == 404
