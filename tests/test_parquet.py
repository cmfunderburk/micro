"""Tests for Parquet read/write (B-107 Level 3)."""

import tempfile
from pathlib import Path

import pytest

from microecon.simulation import create_simple_economy
from microecon.logging.logger import SimulationLogger, RunData
from microecon.logging.events import SimulationConfig
from microecon.logging.parquet import write_run_parquet, read_run_parquet, read_column_parquet


def _run_simulation(seed: int = 42, n_agents: int = 4, ticks: int = 10) -> RunData:
    """Run a small simulation and return RunData."""
    config = SimulationConfig(
        n_agents=n_agents, grid_size=10, seed=seed, protocol_name="nash",
    )
    logger = SimulationLogger(config=config, output_path=None)
    sim = create_simple_economy(
        n_agents=n_agents, grid_size=10, seed=seed,
    )
    sim.logger = logger
    for _ in range(ticks):
        sim.step()
    return logger.finalize()


@pytest.mark.orchestrator
class TestParquetRoundTrip:
    """Level 3: Parquet round-trip tests."""

    def test_write_and_read_produces_equivalent_run_data(self):
        original = _run_simulation()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.parquet"
            write_run_parquet(original, path)
            restored = read_run_parquet(path)

            assert restored.config == original.config
            assert len(restored.ticks) == len(original.ticks)
            for orig_tick, rest_tick in zip(original.ticks, restored.ticks):
                assert rest_tick.tick == orig_tick.tick
                assert abs(rest_tick.total_welfare - orig_tick.total_welfare) < 1e-10
                assert rest_tick.cumulative_trades == orig_tick.cumulative_trades
                assert len(rest_tick.agent_snapshots) == len(orig_tick.agent_snapshots)
                assert len(rest_tick.trades) == len(orig_tick.trades)
                assert len(rest_tick.search_decisions) == len(orig_tick.search_decisions)
                assert len(rest_tick.movements) == len(orig_tick.movements)

    def test_read_single_column(self):
        run_data = _run_simulation()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.parquet"
            write_run_parquet(run_data, path)

            welfare_col = read_column_parquet(path, "total_welfare")
            assert len(welfare_col) == len(run_data.ticks)
            for i, tick in enumerate(run_data.ticks):
                assert abs(welfare_col[i].as_py() - tick.total_welfare) < 1e-10

    def test_parquet_file_exists_after_write(self):
        run_data = _run_simulation()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.parquet"
            write_run_parquet(run_data, path)
            assert path.exists()
            assert path.stat().st_size > 0
