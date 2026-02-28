"""
Matching/clearing protocol abstraction.

Defines the interface for how agents are matched for trade each tick.
The protocol receives proposals and returns match decisions — it does NOT
execute trades or mutate agent state.

Implementations:
- BilateralProposalMatching: Current behavior (mutual detection + sequential evaluation)
- CentralizedClearingMatching: Welfare-maximizing greedy clearing

Reference: ADR-006-MATCHING.md
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from microecon.actions import ProposeAction
    from microecon.agent import Agent
    from microecon.bargaining import BargainingProtocol
    from microecon.decisions import DecisionProcedure
    from microecon.grid import Position


@dataclass(frozen=True)
class TradeOutcome:
    """A matched pair that should trade."""
    proposer_id: str
    target_id: str


@dataclass(frozen=True)
class Rejection:
    """An explicit rejection (triggers cooldown for proposer)."""
    proposer_id: str
    target_id: str
    cooldown_ticks: int


@dataclass(frozen=True)
class MatchResult:
    """Result of matching protocol resolution for one tick.

    Contains three disjoint sets covering all proposers:
    - trades: matched pairs that should execute trades
    - rejections: explicit rejections (proposer gets cooldown)
    - non_selections: implicit failures (no cooldown, e.g. target chose someone else)
    """
    trades: tuple[TradeOutcome, ...]
    rejections: tuple[Rejection, ...]
    non_selections: tuple[str, ...]  # proposer_ids


class MatchingProtocol(ABC):
    """Abstract base for matching/clearing protocols.

    A matching protocol determines which proposals become trades each tick.
    It receives all proposals and agent state, and returns a pure-data
    MatchResult. It does NOT execute trades or mutate state.

    Implementations must be deterministic given the same inputs.
    Tie-breaking uses sorted agent IDs (lexicographic).
    """

    @abstractmethod
    def resolve(
        self,
        propose_actions: dict[str, "ProposeAction"],
        agents: dict[str, "Agent"],
        positions: dict[str, "Position"],
        decision_procedure: "DecisionProcedure",
        bargaining_protocol: "BargainingProtocol",
    ) -> MatchResult:
        """Resolve all proposals for this tick.

        Args:
            propose_actions: Map of proposer_id -> ProposeAction
            agents: Map of agent_id -> Agent (all agents, not just proposers)
            positions: Map of agent_id -> Position (current positions)
            decision_procedure: For evaluating proposal acceptance
            bargaining_protocol: For computing surplus

        Returns:
            MatchResult with trades, rejections, and non-selections
        """
        ...
