"""Logging infrastructure for simulation replay and analysis.

This module provides:
- Event dataclasses for capturing simulation state
- SimulationLogger for recording runs
- Log formats for persistence (JSON lines default)
"""

from .events import (
    AgentSnapshot,
    CommitmentBrokenEvent,
    CommitmentFormedEvent,
    MovementEvent,
    RunSummary,
    SearchDecision,
    SimulationConfig,
    TargetEvaluation,
    TickRecord,
    TradeEvent,
)
from .formats import JSONLinesFormat, LogFormat, load_batch, load_run
from .logger import (
    RunData,
    SimulationLogger,
    create_agent_snapshot,
    create_commitment_broken_event,
    create_commitment_formed_event,
    create_movement_event,
    create_search_decision,
    create_target_evaluation,
    create_tick_record,
    create_trade_event,
)

__all__ = [
    # Events
    "AgentSnapshot",
    "CommitmentBrokenEvent",
    "CommitmentFormedEvent",
    "MovementEvent",
    "RunSummary",
    "SearchDecision",
    "SimulationConfig",
    "TargetEvaluation",
    "TickRecord",
    "TradeEvent",
    # Logger
    "RunData",
    "SimulationLogger",
    # Helpers
    "create_agent_snapshot",
    "create_commitment_broken_event",
    "create_commitment_formed_event",
    "create_movement_event",
    "create_search_decision",
    "create_target_evaluation",
    "create_tick_record",
    "create_trade_event",
    # Formats
    "JSONLinesFormat",
    "LogFormat",
    "load_batch",
    "load_run",
]
