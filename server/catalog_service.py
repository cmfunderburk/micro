"""Catalog service for querying runs and loading replay data (B-105).

Provides REST endpoints for browsing completed experiment runs,
reading tick-level Parquet data, and producing frontend-compatible
replay payloads.

Design doc: docs/plans/2026-03-02-b-e1-manifest-orchestrator-design.md
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from microecon.logging.parquet import read_run_parquet
from server.database import get_connection

catalog_router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_run_row(run_id: str) -> dict[str, Any]:
    """Fetch a single run row from SQLite. Raises HTTPException(404) if missing."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return dict(row)


def _run_row_to_list_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a run row to a list-response dict (excludes config and data_path)."""
    return {
        "run_id": row["run_id"],
        "job_id": row["job_id"],
        "manifest_id": row["manifest_id"],
        "treatment_arm": row["treatment_arm"],
        "seed": row["seed"],
        "status": row["status"],
        "summary": json.loads(row["summary"]) if row["summary"] else None,
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


def _run_row_to_detail_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a run row to a full detail-response dict (includes config and summary)."""
    return {
        "run_id": row["run_id"],
        "job_id": row["job_id"],
        "manifest_id": row["manifest_id"],
        "treatment_arm": row["treatment_arm"],
        "seed": row["seed"],
        "status": row["status"],
        "config": json.loads(row["config"]) if row["config"] else None,
        "summary": json.loads(row["summary"]) if row["summary"] else None,
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


def _read_parquet_for_run(row: dict[str, Any]):
    """Read the Parquet file for a run. Raises HTTPException if missing."""
    data_path = row.get("data_path")
    if not data_path:
        raise HTTPException(status_code=404, detail="Run has no data file")

    parquet_path = Path(data_path)
    if not parquet_path.exists():
        raise HTTPException(status_code=404, detail="Parquet file not found")

    return read_run_parquet(parquet_path)


def _tick_to_replay_format(
    tick_record,
    initial_welfare: float,
) -> dict[str, Any]:
    """Transform a TickRecord into the frontend replay format.

    Matches the shape produced by server/routes.py load_run() for
    frontend compatibility.
    """
    # Build agent alpha lookup for trade enrichment
    alpha_by_id = {
        agent.agent_id: agent.alpha
        for agent in tick_record.agent_snapshots
    }

    # Build belief map from belief_snapshots
    beliefs: dict[str, Any] = {}
    for bs in tick_record.belief_snapshots:
        beliefs[bs.agent_id] = {
            "type_beliefs": [
                {
                    "target_id": tb.target_agent_id,
                    "believed_alpha": tb.believed_alpha,
                    "confidence": tb.confidence,
                    "n_interactions": tb.n_interactions,
                }
                for tb in bs.type_beliefs
            ],
            "price_belief": {
                "mean": bs.price_belief.mean,
                "variance": bs.price_belief.variance,
                "n_observations": bs.price_belief.n_observations,
            } if bs.price_belief else None,
            "n_trades_in_memory": bs.n_trades_in_memory,
        }

    total_welfare = tick_record.total_welfare

    return {
        "tick": tick_record.tick,
        "agents": [
            {
                "id": agent.agent_id,
                "x": agent.position[0],
                "y": agent.position[1],
                "position": list(agent.position),
                "endowment": list(agent.endowment),
                "alpha": agent.alpha,
                "utility": agent.utility,
                "perception_radius": 7.0,
                "discount_factor": 0.95,
                "has_beliefs": agent.has_beliefs,
                "n_trades_in_memory": agent.n_trades_in_memory,
                "n_type_beliefs": agent.n_type_beliefs,
            }
            for agent in tick_record.agent_snapshots
        ],
        "trades": [
            {
                "tick": tick_record.tick,
                "agent1_id": trade.agent1_id,
                "agent2_id": trade.agent2_id,
                "proposer_id": trade.proposer_id,
                "alpha1": alpha_by_id.get(trade.agent1_id, 0.5),
                "alpha2": alpha_by_id.get(trade.agent2_id, 0.5),
                "pre_holdings_1": list(trade.pre_holdings[0]),
                "pre_holdings_2": list(trade.pre_holdings[1]),
                "post_allocation_1": list(trade.post_allocations[0]),
                "post_allocation_2": list(trade.post_allocations[1]),
                "gains": list(trade.gains),
            }
            for trade in tick_record.trades
        ],
        "metrics": {
            "total_welfare": total_welfare,
            "welfare_gains": total_welfare - initial_welfare,
            "cumulative_trades": tick_record.cumulative_trades,
        },
        "beliefs": beliefs,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@catalog_router.get("/catalog/runs")
async def list_runs(
    manifest_id: str | None = Query(default=None),
    treatment_arm: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    """List runs with optional filtering."""
    conn = get_connection()
    try:
        query = "SELECT * FROM runs WHERE 1=1"
        params: list[Any] = []

        if manifest_id is not None:
            query += " AND manifest_id = ?"
            params.append(manifest_id)

        if treatment_arm is not None:
            query += " AND treatment_arm = ?"
            params.append(treatment_arm)

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [_run_row_to_list_dict(dict(row)) for row in rows]
    finally:
        conn.close()


@catalog_router.get("/catalog/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    """Get full run metadata including config and summary."""
    row = _get_run_row(run_id)
    return _run_row_to_detail_dict(row)


@catalog_router.get("/catalog/runs/{run_id}/ticks")
async def get_ticks(
    run_id: str,
    tick: int | None = Query(default=None),
) -> list[dict[str, Any]]:
    """Read tick data from Parquet file.

    If tick query param is provided, return just that one tick.
    Otherwise return all ticks.
    """
    row = _get_run_row(run_id)
    run_data = _read_parquet_for_run(row)

    ticks = run_data.ticks
    if tick is not None:
        ticks = [t for t in ticks if t.tick == tick]

    return [t.to_dict() for t in ticks]


@catalog_router.get("/catalog/runs/{run_id}/replay")
async def get_replay(run_id: str) -> dict[str, Any]:
    """Produce a replay payload compatible with the frontend replay mode.

    Matches the shape of GET /api/runs/{run_name} in server/routes.py so
    the frontend can consume it without changes.
    """
    row = _get_run_row(run_id)
    run_data = _read_parquet_for_run(row)

    config_dict = run_data.config.to_dict()

    # Determine initial welfare from first tick
    initial_welfare = 0.0
    if run_data.ticks:
        initial_welfare = run_data.ticks[0].total_welfare

    replay_ticks = [
        _tick_to_replay_format(t, initial_welfare)
        for t in run_data.ticks
    ]

    return {
        "name": run_id,
        "config": config_dict,
        "schema_version": config_dict.get("schema_version", "1.0"),
        "ticks": replay_ticks,
        "n_ticks": len(replay_ticks),
    }
