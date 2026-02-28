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


class BilateralProposalMatching(MatchingProtocol):
    """Default bilateral proposal matching -- extracts current _execute_actions behavior.

    Resolution order:
    1. Detect mutual proposals (A->B and B->A) -- fast-track to trade
    2. Evaluate non-mutual proposals -- target accepts/rejects based on opportunity cost
    3. Handle conflicts -- first-responder advantage for same target

    This is a pure extraction of the matching logic from simulation.py into a protocol.
    """

    def resolve(
        self,
        propose_actions: dict[str, "ProposeAction"],
        agents: dict[str, "Agent"],
        positions: dict[str, "Position"],
        decision_procedure: "DecisionProcedure",
        bargaining_protocol: "BargainingProtocol",
    ) -> MatchResult:
        if not propose_actions:
            return MatchResult(trades=(), rejections=(), non_selections=())

        trades: list[TradeOutcome] = []
        rejections: list[Rejection] = []
        non_selections: list[str] = []
        traded_this_tick: set[str] = set()

        # Step 1: Detect and resolve mutual proposals
        mutual_proposals: set[frozenset[str]] = set()
        for proposer_id, action in propose_actions.items():
            target_action = propose_actions.get(action.target_id)
            if target_action and target_action.target_id == proposer_id:
                mutual_proposals.add(frozenset([proposer_id, action.target_id]))

        processed_mutual: set[str] = set()
        for pair in sorted(mutual_proposals, key=lambda p: sorted(p)):
            pair_list = sorted(pair)
            if pair_list[0] in processed_mutual or pair_list[1] in processed_mutual:
                continue

            a_id, b_id = pair_list
            if a_id not in agents or b_id not in agents:
                continue

            pos_a = positions.get(a_id)
            pos_b = positions.get(b_id)
            if pos_a is None or pos_b is None:
                continue
            if pos_a.chebyshev_distance_to(pos_b) > 1:
                continue

            # Mutual match: use sorted order for deterministic proposer assignment
            trades.append(TradeOutcome(proposer_id=a_id, target_id=b_id))
            processed_mutual.add(a_id)
            processed_mutual.add(b_id)
            traded_this_tick.add(a_id)
            traded_this_tick.add(b_id)

        # Step 2: Evaluate non-mutual proposals
        # Build decision context for proposal evaluation
        from microecon.actions import ActionContext
        from microecon.decisions import DecisionContext

        action_context = ActionContext(
            current_tick=0,
            agent_positions=positions,
            agent_interaction_states={},
            co_located_agents={},
            adjacent_agents={},
            pending_proposals={},
        )
        decision_context = DecisionContext(
            action_context=action_context,
            visible_agents=agents,  # Full visibility for evaluation (ADR-005)
            bargaining_protocol=bargaining_protocol,
            agent_positions=positions,
        )

        responded_targets: set[str] = set()

        for proposer_id, action in propose_actions.items():
            if proposer_id in processed_mutual:
                continue
            if proposer_id in traded_this_tick:
                continue

            target_id = action.target_id
            proposer = agents.get(proposer_id)
            target = agents.get(target_id)
            if proposer is None or target is None:
                continue

            # Target already responded to another proposal
            if target_id in responded_targets:
                non_selections.append(proposer_id)
                continue

            # Target already traded (from mutual proposal)
            if target_id in traded_this_tick:
                non_selections.append(proposer_id)
                continue

            # Check adjacency
            proposer_pos = positions.get(proposer_id)
            target_pos = positions.get(target_id)
            if proposer_pos is None or target_pos is None:
                continue
            if proposer_pos.chebyshev_distance_to(target_pos) > 1:
                continue

            # Target evaluates proposal
            accept = decision_procedure.evaluate_proposal(
                target, proposer, decision_context
            )
            responded_targets.add(target_id)

            if accept:
                trades.append(TradeOutcome(proposer_id=proposer_id, target_id=target_id))
                traded_this_tick.add(proposer_id)
                traded_this_tick.add(target_id)
            else:
                rejections.append(Rejection(
                    proposer_id=proposer_id,
                    target_id=target_id,
                    cooldown_ticks=3,
                ))

        return MatchResult(
            trades=tuple(trades),
            rejections=tuple(rejections),
            non_selections=tuple(non_selections),
        )


class CentralizedClearingMatching(MatchingProtocol):
    """Centralized welfare-maximizing matching.

    A centralized auctioneer collects all proposals, computes bilateral surplus
    for each adjacent proposer-target pair, and greedily assigns matches by
    descending surplus (each agent matched at most once).

    Key differences from BilateralProposalMatching:
    - No rejections (unmatched = non-selected, no cooldowns)
    - Welfare-maximizing (highest surplus pairs matched first)
    - Simultaneous resolution (no first-responder advantage)

    This is a stub demonstrating the MatchingProtocol interface.
    """

    def resolve(
        self,
        propose_actions: dict[str, "ProposeAction"],
        agents: dict[str, "Agent"],
        positions: dict[str, "Position"],
        decision_procedure: "DecisionProcedure",
        bargaining_protocol: "BargainingProtocol",
    ) -> MatchResult:
        if not propose_actions:
            return MatchResult(trades=(), rejections=(), non_selections=())

        # Compute surplus for each valid proposal (adjacent pairs only)
        scored_proposals: list[tuple[float, str, str]] = []
        for proposer_id, action in propose_actions.items():
            target_id = action.target_id
            proposer = agents.get(proposer_id)
            target = agents.get(target_id)
            if proposer is None or target is None:
                continue

            pos_p = positions.get(proposer_id)
            pos_t = positions.get(target_id)
            if pos_p is None or pos_t is None:
                continue
            if pos_p.chebyshev_distance_to(pos_t) > 1:
                continue

            surplus = bargaining_protocol.compute_expected_surplus(proposer, target)
            if surplus > 0:
                scored_proposals.append((surplus, proposer_id, target_id))

        # Sort by surplus descending, then by proposer_id for determinism
        scored_proposals.sort(key=lambda x: (-x[0], x[1]))

        # Greedy matching: assign highest surplus pairs first
        trades: list[TradeOutcome] = []
        matched: set[str] = set()

        for surplus, proposer_id, target_id in scored_proposals:
            if proposer_id in matched or target_id in matched:
                continue
            trades.append(TradeOutcome(proposer_id=proposer_id, target_id=target_id))
            matched.add(proposer_id)
            matched.add(target_id)

        # All unmatched proposers are non-selected (no rejections in centralized clearing)
        non_selections = tuple(
            pid for pid in propose_actions if pid not in matched
        )

        return MatchResult(
            trades=tuple(trades),
            rejections=(),  # Centralized clearing never rejects
            non_selections=non_selections,
        )
