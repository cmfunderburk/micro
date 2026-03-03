"""Tests for manifest CRUD API (B-103, B-107 Level 1)."""

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.database import init_db
import server.database as db_mod


@pytest.fixture
def client(tmp_path):
    """Create test client with isolated database."""
    db_path = tmp_path / "test.db"
    original_db_path = db_mod.DB_PATH
    original_data_dir = db_mod.DATA_DIR
    db_mod.DB_PATH = db_path
    db_mod.DATA_DIR = tmp_path / "data"

    init_db(db_path)
    app = create_app()

    with TestClient(app) as c:
        yield c

    db_mod.DB_PATH = original_db_path
    db_mod.DATA_DIR = original_data_dir


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
        assert data["schema_version"] is not None

    def test_create_invalid_manifest(self, client):
        payload = _valid_manifest_payload()
        payload["treatments"] = [payload["treatments"][0]]  # Only 1 arm
        payload["run_budget"] = 3
        resp = client.post("/api/manifests", json=payload)
        assert resp.status_code == 422
        assert "errors" in resp.json()["detail"]

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
