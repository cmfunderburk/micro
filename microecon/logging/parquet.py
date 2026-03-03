"""Parquet read/write for simulation tick data.

Provides lossless round-trip serialization of RunData to Parquet files.
Each run produces one Parquet file with one row per tick.

Design doc: docs/plans/2026-03-02-b-e1-manifest-orchestrator-design.md S6
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .events import (
    AgentSnapshot,
    BeliefSnapshot,
    CommitmentBrokenEvent,
    CommitmentFormedEvent,
    MovementEvent,
    RunSummary,
    SearchDecision,
    SimulationConfig,
    TickRecord,
    TradeEvent,
)
from .logger import RunData


def write_run_parquet(run_data: RunData, path: Path) -> None:
    """Convert RunData to Arrow table and write Parquet file.

    Writes config as Parquet file metadata so the file is self-contained.
    """
    rows: list[dict[str, Any]] = []
    for tick in run_data.ticks:
        rows.append(_tick_to_row(tick))

    table = pa.Table.from_pylist(rows)

    # Store config and summary as file metadata
    metadata: dict[bytes, bytes] = {
        b"config": json.dumps(run_data.config.to_dict()).encode(),
    }
    if run_data.summary is not None:
        metadata[b"summary"] = json.dumps(run_data.summary.to_dict()).encode()

    table = table.replace_schema_metadata({
        **metadata,
        **(table.schema.metadata or {}),
    })

    pq.write_table(table, str(path))


def read_run_parquet(path: Path) -> RunData:
    """Read Parquet file back into RunData."""
    table = pq.read_table(str(path))
    metadata = table.schema.metadata or {}

    config = SimulationConfig.from_dict(
        json.loads(metadata[b"config"].decode())
    )

    summary = None
    if b"summary" in metadata:
        summary = RunSummary.from_dict(
            json.loads(metadata[b"summary"].decode())
        )

    ticks = []
    for i in range(len(table)):
        row = {col: table.column(col)[i].as_py() for col in table.column_names}
        ticks.append(_row_to_tick(row))

    return RunData(config=config, ticks=ticks, summary=summary)


def read_column_parquet(path: Path, column: str) -> pa.Array:
    """Read a single column for fast analytical queries."""
    table = pq.read_table(str(path), columns=[column])
    return table.column(column)


def _tick_to_row(tick: TickRecord) -> dict[str, Any]:
    """Convert a TickRecord to a flat dict for Arrow."""
    return {
        "tick": tick.tick,
        "total_welfare": tick.total_welfare,
        "cumulative_trades": tick.cumulative_trades,
        "trade_count": len(tick.trades),
        "agent_snapshots": [s.to_dict() for s in tick.agent_snapshots],
        "search_decisions": [s.to_dict() for s in tick.search_decisions],
        "movements": [m.to_dict() for m in tick.movements],
        "trades": [t.to_dict() for t in tick.trades],
        "commitments_formed": [c.to_dict() for c in tick.commitments_formed],
        "commitments_broken": [c.to_dict() for c in tick.commitments_broken],
        "belief_snapshots": [b.to_dict() for b in tick.belief_snapshots],
    }


def _row_to_tick(row: dict[str, Any]) -> TickRecord:
    """Convert a Parquet row back to a TickRecord."""
    return TickRecord(
        tick=row["tick"],
        total_welfare=row["total_welfare"],
        cumulative_trades=row["cumulative_trades"],
        agent_snapshots=tuple(
            AgentSnapshot.from_dict(s) for s in (row.get("agent_snapshots") or [])
        ),
        search_decisions=tuple(
            SearchDecision.from_dict(s) for s in (row.get("search_decisions") or [])
        ),
        movements=tuple(
            MovementEvent.from_dict(m) for m in (row.get("movements") or [])
        ),
        trades=tuple(
            TradeEvent.from_dict(t) for t in (row.get("trades") or [])
        ),
        commitments_formed=tuple(
            CommitmentFormedEvent.from_dict(c)
            for c in (row.get("commitments_formed") or [])
        ),
        commitments_broken=tuple(
            CommitmentBrokenEvent.from_dict(c)
            for c in (row.get("commitments_broken") or [])
        ),
        belief_snapshots=tuple(
            BeliefSnapshot.from_dict(b) for b in (row.get("belief_snapshots") or [])
        ),
    )
