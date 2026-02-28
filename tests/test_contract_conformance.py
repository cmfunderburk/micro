"""Contract conformance tests (A-103).

Validates that all data paths conform to the canonical schema
defined in microecon/logging/events.py.

Four levels:
1. Canonical round-trip: to_dict() -> from_dict() == original
2. Persist/load: logger -> disk -> load_run() is lossless
3. Replay API: persisted data -> replay adapter -> expected shape
4. Live WS: SimulationManager tick data -> expected shape
"""

import json
import tempfile
from pathlib import Path

import pytest

from microecon.logging import (
    AgentSnapshot,
    BeliefSnapshot,
    CommitmentBrokenEvent,
    CommitmentFormedEvent,
    JSONLinesFormat,
    MovementEvent,
    PriceBeliefSnapshot,
    RunData,
    SearchDecision,
    SimulationConfig,
    SimulationLogger,
    TargetEvaluation,
    TickRecord,
    TradeEvent,
    TypeBeliefSnapshot,
    load_run,
)
from microecon.simulation import create_simple_economy

pytestmark = pytest.mark.contract


# =========================================================================
# Level 1: Canonical round-trip
# =========================================================================

class TestCanonicalRoundTrip:
    """Every canonical dataclass must survive to_dict() -> from_dict()."""

    def test_simulation_config(self):
        original = SimulationConfig(
            n_agents=10, grid_size=15, seed=42, protocol_name="nash",
            protocol_params={"key": "val"}, perception_radius=5.0,
            discount_factor=0.9, movement_budget=2,
            info_env_name="noisy_alpha", info_env_params={"noise_std": 0.1},
            run_id="test-run-id",
        )
        assert SimulationConfig.from_dict(original.to_dict()) == original

    def test_agent_snapshot(self):
        original = AgentSnapshot(
            agent_id="a1", position=(3, 4), endowment=(10.0, 5.0),
            alpha=0.6, utility=7.5, has_beliefs=True,
            n_trades_in_memory=3, n_type_beliefs=2,
        )
        assert AgentSnapshot.from_dict(original.to_dict()) == original

    def test_target_evaluation(self):
        original = TargetEvaluation(
            target_id="t1", target_position=(1, 2), distance=3.0,
            ticks_to_reach=3, expected_surplus=1.5, discounted_value=1.2,
            observed_alpha=0.7, used_belief=True, believed_alpha=0.65,
        )
        assert TargetEvaluation.from_dict(original.to_dict()) == original

    def test_search_decision(self):
        evals = (
            TargetEvaluation("t1", (1, 1), 2.0, 2, 1.0, 0.9, 0.6),
            TargetEvaluation("t2", (2, 2), 3.0, 3, 0.8, 0.7, 0.4),
        )
        original = SearchDecision(
            agent_id="a1", position=(5, 5), visible_agents=3,
            evaluations=evals, chosen_target_id="t1", chosen_value=0.9,
        )
        assert SearchDecision.from_dict(original.to_dict()) == original

    def test_movement_event(self):
        original = MovementEvent(
            agent_id="a1", from_pos=(0, 0), to_pos=(1, 1),
            target_id="t1", reason="toward_target",
        )
        assert MovementEvent.from_dict(original.to_dict()) == original

    def test_trade_event(self):
        original = TradeEvent(
            agent1_id="a1", agent2_id="a2", proposer_id="a1",
            pre_holdings=((10.0, 5.0), (5.0, 10.0)),
            post_allocations=((8.0, 7.0), (7.0, 8.0)),
            utilities=(6.5, 7.2), gains=(0.5, 0.3), trade_occurred=True,
        )
        assert TradeEvent.from_dict(original.to_dict()) == original

    def test_commitment_formed_event(self):
        original = CommitmentFormedEvent(agent_a="a1", agent_b="a2")
        assert CommitmentFormedEvent.from_dict(original.to_dict()) == original

    def test_commitment_broken_event(self):
        original = CommitmentBrokenEvent(
            agent_a="a1", agent_b="a2", reason="trade_completed",
        )
        assert CommitmentBrokenEvent.from_dict(original.to_dict()) == original

    def test_type_belief_snapshot(self):
        original = TypeBeliefSnapshot(
            target_agent_id="a2", believed_alpha=0.6,
            confidence=0.8, n_interactions=5,
        )
        assert TypeBeliefSnapshot.from_dict(original.to_dict()) == original

    def test_price_belief_snapshot(self):
        original = PriceBeliefSnapshot(
            mean=1.5, variance=0.3, n_observations=10,
        )
        assert PriceBeliefSnapshot.from_dict(original.to_dict()) == original

    def test_belief_snapshot(self):
        original = BeliefSnapshot(
            agent_id="a1",
            type_beliefs=(
                TypeBeliefSnapshot("a2", 0.6, 0.8, 5),
            ),
            price_belief=PriceBeliefSnapshot(1.5, 0.3, 10),
            n_trades_in_memory=3,
        )
        assert BeliefSnapshot.from_dict(original.to_dict()) == original

    def test_tick_record(self):
        original = TickRecord(
            tick=5,
            agent_snapshots=(
                AgentSnapshot("a1", (0, 0), (10.0, 5.0), 0.6, 7.5),
            ),
            search_decisions=(),
            movements=(),
            trades=(),
            total_welfare=7.5,
            cumulative_trades=0,
        )
        assert TickRecord.from_dict(original.to_dict()) == original

    def test_tick_record_with_all_optional_fields(self):
        original = TickRecord(
            tick=5,
            agent_snapshots=(
                AgentSnapshot("a1", (0, 0), (10.0, 5.0), 0.6, 7.5),
            ),
            search_decisions=(),
            movements=(),
            trades=(
                TradeEvent("a1", "a2", "a1",
                           ((10.0, 5.0), (5.0, 10.0)),
                           ((8.0, 7.0), (7.0, 8.0)),
                           (6.5, 7.2), (0.5, 0.3), True),
            ),
            total_welfare=13.7,
            cumulative_trades=1,
            commitments_formed=(CommitmentFormedEvent("a1", "a2"),),
            commitments_broken=(CommitmentBrokenEvent("a1", "a2", "trade_completed"),),
            belief_snapshots=(
                BeliefSnapshot("a1",
                    (TypeBeliefSnapshot("a2", 0.6, 0.8, 5),),
                    PriceBeliefSnapshot(1.5, 0.3, 10), 3),
            ),
        )
        assert TickRecord.from_dict(original.to_dict()) == original
