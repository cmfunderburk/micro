"""Tests for database module."""

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
