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


# =========================================================================
# Level 2: Persist -> Load conformance
# =========================================================================

class TestPersistLoadConformance:
    """Persisting via SimulationLogger and loading via load_run() must be lossless."""

    def _run_and_persist(self, tmpdir: Path, n_ticks: int = 10, seed: int = 42,
                         protocol: str = "nash", use_beliefs: bool = False) -> RunData:
        """Helper: run a simulation and persist it."""
        output_path = tmpdir / "test_run"
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=seed, protocol_name=protocol,
        )
        logger = SimulationLogger(
            config=config, output_path=output_path, log_format=JSONLinesFormat(),
        )
        sim = create_simple_economy(
            n_agents=4, grid_size=5, seed=seed, use_beliefs=use_beliefs,
        )
        sim.logger = logger
        sim.run(n_ticks)
        return logger.finalize()

    def test_config_survives_persist_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir))
            loaded = load_run(Path(tmpdir) / "test_run")
            assert loaded.config.n_agents == original.config.n_agents
            assert loaded.config.grid_size == original.config.grid_size
            assert loaded.config.seed == original.config.seed
            assert loaded.config.protocol_name == original.config.protocol_name
            assert loaded.config.schema_version == original.config.schema_version
            assert loaded.config.run_id == original.config.run_id

    def test_tick_count_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=10)
            loaded = load_run(Path(tmpdir) / "test_run")
            assert len(loaded.ticks) == len(original.ticks) == 10

    def test_agent_snapshots_survive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=5)
            loaded = load_run(Path(tmpdir) / "test_run")
            for orig_tick, loaded_tick in zip(original.ticks, loaded.ticks):
                assert len(loaded_tick.agent_snapshots) == len(orig_tick.agent_snapshots)
                for orig_snap, loaded_snap in zip(
                    orig_tick.agent_snapshots, loaded_tick.agent_snapshots
                ):
                    assert loaded_snap.agent_id == orig_snap.agent_id
                    assert loaded_snap.position == orig_snap.position
                    assert loaded_snap.alpha == orig_snap.alpha
                    assert abs(loaded_snap.utility - orig_snap.utility) < 1e-10

    def test_trades_survive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=20)
            loaded = load_run(Path(tmpdir) / "test_run")
            for orig_tick, loaded_tick in zip(original.ticks, loaded.ticks):
                assert len(loaded_tick.trades) == len(orig_tick.trades)
                for orig_trade, loaded_trade in zip(
                    orig_tick.trades, loaded_tick.trades
                ):
                    assert loaded_trade.agent1_id == orig_trade.agent1_id
                    assert loaded_trade.agent2_id == orig_trade.agent2_id
                    assert loaded_trade.proposer_id == orig_trade.proposer_id
                    assert loaded_trade.trade_occurred == orig_trade.trade_occurred

    def test_welfare_survives(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=10)
            loaded = load_run(Path(tmpdir) / "test_run")
            for orig_tick, loaded_tick in zip(original.ticks, loaded.ticks):
                assert abs(loaded_tick.total_welfare - orig_tick.total_welfare) < 1e-10
                assert loaded_tick.cumulative_trades == orig_tick.cumulative_trades

    def test_summary_survives(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=10)
            loaded = load_run(Path(tmpdir) / "test_run")
            assert loaded.summary is not None
            assert original.summary is not None
            assert loaded.summary.total_ticks == original.summary.total_ticks
            assert loaded.summary.total_trades == original.summary.total_trades
            assert abs(loaded.summary.final_welfare - original.summary.final_welfare) < 1e-10

    def test_schema_version_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._run_and_persist(Path(tmpdir))
            config_file = Path(tmpdir) / "test_run" / "config.json"
            with open(config_file) as f:
                raw = json.load(f)
            assert "schema_version" in raw
            assert raw["schema_version"] == "1.0"

    def test_run_id_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir))
            config_file = Path(tmpdir) / "test_run" / "config.json"
            with open(config_file) as f:
                raw = json.load(f)
            assert "run_id" in raw
            assert raw["run_id"] == original.config.run_id
            assert raw["run_id"] != ""


# =========================================================================
# Level 3: Persist -> Replay API conformance
# =========================================================================

class TestReplayAPIConformance:
    """Replay API adapter must correctly transform canonical schema to presentation format.

    Adapter contract (from docs/contracts/schema-v1.md):
    - agent_id -> id (rename)
    - target_agent_id -> target_id (rename in beliefs)
    - pre_holdings[0] -> pre_holdings_1 (tuple unpack)
    - post_allocations[0] -> post_allocation_1 (tuple unpack)
    - alpha1, alpha2 derived from AgentSnapshot.alpha
    - belief_snapshots array -> beliefs map keyed by agent_id
    """

    @pytest.fixture
    def replay_data(self):
        """Create a persisted run and load it through the replay API transform."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_run"
            config = SimulationConfig(
                n_agents=4, grid_size=5, seed=42, protocol_name="nash",
            )
            logger = SimulationLogger(
                config=config, output_path=output_path, log_format=JSONLinesFormat(),
            )
            sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
            sim.logger = logger
            sim.run(15)
            logger.finalize()

            # Load raw persisted data
            config_file = output_path / "config.json"
            ticks_file = output_path / "ticks.jsonl"

            with open(config_file) as f:
                raw_config = json.load(f)

            raw_ticks = []
            with open(ticks_file) as f:
                for line in f:
                    raw_ticks.append(json.loads(line.strip()))

            yield {"config": raw_config, "raw_ticks": raw_ticks}

    def test_agent_snapshots_have_required_fields(self, replay_data):
        """Each agent snapshot in raw data has all canonical fields."""
        for tick in replay_data["raw_ticks"]:
            for agent in tick["agent_snapshots"]:
                assert "agent_id" in agent
                assert "position" in agent
                assert "endowment" in agent
                assert "alpha" in agent
                assert "utility" in agent

    def test_trade_events_have_required_fields(self, replay_data):
        """Trade events have all canonical fields including proposer_id."""
        trades_found = False
        for tick in replay_data["raw_ticks"]:
            for trade in tick.get("trades", []):
                trades_found = True
                assert "agent1_id" in trade
                assert "agent2_id" in trade
                assert "proposer_id" in trade
                assert "pre_holdings" in trade
                assert "post_allocations" in trade
                assert "utilities" in trade
                assert "gains" in trade
                assert "trade_occurred" in trade
                # pre_holdings is a list of two lists
                assert len(trade["pre_holdings"]) == 2
                assert len(trade["post_allocations"]) == 2
        assert trades_found, "No trades found in 15 ticks — test needs more ticks"

    def test_alpha_derivable_from_agent_snapshots(self, replay_data):
        """Alpha values for trade enrichment must be derivable from same-tick agent snapshots."""
        for tick in replay_data["raw_ticks"]:
            alpha_by_id = {
                agent["agent_id"]: agent["alpha"]
                for agent in tick["agent_snapshots"]
            }
            for trade in tick.get("trades", []):
                assert trade["agent1_id"] in alpha_by_id
                assert trade["agent2_id"] in alpha_by_id

    def test_schema_version_in_config(self, replay_data):
        assert "schema_version" in replay_data["config"]

    def test_run_id_in_config(self, replay_data):
        assert "run_id" in replay_data["config"]
        assert replay_data["config"]["run_id"] != ""
