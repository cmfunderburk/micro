"""Tests for logging infrastructure."""

import json
import tempfile
from pathlib import Path

import pytest

from microecon.logging import (
    AgentSnapshot,
    MovementEvent,
    RunSummary,
    SearchDecision,
    SimulationConfig,
    TargetEvaluation,
    TickRecord,
    TradeEvent,
    SimulationLogger,
    RunData,
    JSONLinesFormat,
    load_run,
)
from microecon.simulation import create_simple_economy

pytestmark = pytest.mark.analysis


class TestEventSerialization:
    """Test event dataclass serialization roundtrip."""

    def test_simulation_config_roundtrip(self):
        config = SimulationConfig(
            n_agents=10,
            grid_size=15,
            seed=42,
            protocol_name="nash",
            protocol_params={"foo": "bar"},
            perception_radius=5.0,
            discount_factor=0.9,
        )
        d = config.to_dict()
        restored = SimulationConfig.from_dict(d)
        assert restored == config

    def test_agent_snapshot_roundtrip(self):
        snapshot = AgentSnapshot(
            agent_id="abc123",
            position=(5, 7),
            endowment=(10.5, 3.2),
            alpha=0.6,
            utility=8.5,
        )
        d = snapshot.to_dict()
        restored = AgentSnapshot.from_dict(d)
        assert restored == snapshot

    def test_target_evaluation_roundtrip(self):
        eval = TargetEvaluation(
            target_id="target1",
            target_position=(3, 4),
            distance=5.0,
            ticks_to_reach=5,
            expected_surplus=2.5,
            discounted_value=1.8,
            observed_alpha=0.65,
        )
        d = eval.to_dict()
        restored = TargetEvaluation.from_dict(d)
        assert restored == eval

    def test_search_decision_roundtrip(self):
        decision = SearchDecision(
            agent_id="agent1",
            position=(5, 5),
            visible_agents=3,
            evaluations=(
                TargetEvaluation("t1", (1, 1), 2.0, 2, 1.0, 0.9, 0.6),
                TargetEvaluation("t2", (2, 2), 3.0, 3, 0.8, 0.7, 0.4),
            ),
            chosen_target_id="t1",
            chosen_value=0.9,
        )
        d = decision.to_dict()
        restored = SearchDecision.from_dict(d)
        assert restored == decision

    def test_movement_event_roundtrip(self):
        event = MovementEvent(
            agent_id="agent1",
            from_pos=(5, 5),
            to_pos=(6, 5),
            target_id="target1",
            reason="toward_target",
        )
        d = event.to_dict()
        restored = MovementEvent.from_dict(d)
        assert restored == event

    def test_trade_event_roundtrip(self):
        event = TradeEvent(
            agent1_id="a1",
            agent2_id="a2",
            proposer_id="a1",
            pre_holdings=((10.0, 2.0), (2.0, 10.0)),
            post_allocations=((6.0, 6.0), (6.0, 6.0)),
            utilities=(6.0, 6.0),
            gains=(1.5, 1.5),
            trade_occurred=True,
        )
        d = event.to_dict()
        restored = TradeEvent.from_dict(d)
        assert restored == event

    def test_tick_record_roundtrip(self):
        record = TickRecord(
            tick=5,
            agent_snapshots=(
                AgentSnapshot("a1", (0, 0), (10.0, 2.0), 0.5, 4.5),
            ),
            search_decisions=(),
            movements=(),
            trades=(),
            total_welfare=10.0,
            cumulative_trades=3,
        )
        d = record.to_dict()
        restored = TickRecord.from_dict(d)
        assert restored == record


class TestSimulationLogger:
    """Test SimulationLogger functionality."""

    def test_logger_collects_ticks(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash"
        )
        logger = SimulationLogger(config)

        # Create a simulation with the logger
        sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
        sim.logger = logger

        # Run some ticks
        sim.run(10)

        # Verify ticks were collected
        assert len(logger.ticks) == 10

        # Each tick should have agent snapshots
        for tick in logger.ticks:
            assert len(tick.agent_snapshots) == 4

    def test_logger_writes_to_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_run"

            config = SimulationConfig(
                n_agents=4, grid_size=5, seed=42, protocol_name="nash"
            )
            logger = SimulationLogger(config, output_path=output_path)

            sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
            sim.logger = logger
            sim.run(5)

            run_data = logger.finalize()

            # Check files exist
            assert (output_path / "config.json").exists()
            assert (output_path / "ticks.jsonl").exists()
            assert (output_path / "summary.json").exists()

            # Verify we can load the run back
            loaded = load_run(output_path)
            assert len(loaded.ticks) == 5
            assert loaded.config.n_agents == 4

    def test_logger_captures_search_decisions(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash"
        )
        logger = SimulationLogger(config)

        sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
        sim.logger = logger
        sim.run(5)

        # Should have search decisions for each agent each tick
        for tick in logger.ticks:
            assert len(tick.search_decisions) == 4

    def test_logger_captures_movements(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash"
        )
        logger = SimulationLogger(config)

        sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
        sim.logger = logger
        sim.run(5)

        # Should have movement events for each agent each tick
        for tick in logger.ticks:
            assert len(tick.movements) == 4

    def test_logger_captures_trades(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash"
        )
        logger = SimulationLogger(config)

        sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
        sim.logger = logger
        sim.run(20)  # Run longer to ensure some trades

        run_data = logger.finalize()

        # Should have captured some trades
        total_trades = sum(len(tick.trades) for tick in run_data.ticks)
        assert total_trades > 0

        # Summary should reflect trades
        assert run_data.summary is not None
        assert run_data.summary.total_trades == total_trades


class TestJSONLinesFormat:
    """Test JSON lines format reading and writing."""

    def test_write_and_read_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            fmt = JSONLinesFormat()

            config = SimulationConfig(
                n_agents=10, grid_size=15, seed=42, protocol_name="nash"
            )
            fmt.write_config(config, path)

            # Read back
            with open(path / "config.json") as f:
                d = json.load(f)
            restored = SimulationConfig.from_dict(d)
            assert restored == config

    def test_write_and_read_ticks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            fmt = JSONLinesFormat()

            config = SimulationConfig(
                n_agents=2, grid_size=5, seed=42, protocol_name="nash"
            )
            fmt.write_config(config, path)

            # Write some ticks
            for i in range(3):
                tick = TickRecord(
                    tick=i + 1,
                    agent_snapshots=(),
                    search_decisions=(),
                    movements=(),
                    trades=(),
                    total_welfare=10.0 + i,
                    cumulative_trades=i,
                )
                fmt.write_tick(tick, path)

            fmt.write_summary(
                RunSummary(
                    total_ticks=3,
                    final_welfare=12.0,
                    total_trades=2,
                    welfare_gain=2.0,
                ),
                path,
            )

            # Read back
            run_data = fmt.read_run(path)
            assert len(run_data.ticks) == 3
            assert run_data.ticks[0].tick == 1
            assert run_data.ticks[2].tick == 3
            assert run_data.summary.total_ticks == 3


class TestRunData:
    """Test RunData convenience methods."""

    def test_welfare_at(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash"
        )
        logger = SimulationLogger(config)

        sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
        sim.logger = logger
        sim.run(5)

        run_data = logger.finalize()

        # Should be able to query welfare at each tick
        for i in range(5):
            welfare = run_data.welfare_at(i)
            assert welfare > 0

    def test_agent_trajectory(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash"
        )
        logger = SimulationLogger(config)

        sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
        sim.logger = logger
        sim.run(5)

        run_data = logger.finalize()

        # Get trajectory for first agent
        agent_id = run_data.agent_ids[0]
        trajectory = run_data.agent_trajectory(agent_id)

        assert len(trajectory) == 5
        assert all(s.agent_id == agent_id for s in trajectory)
