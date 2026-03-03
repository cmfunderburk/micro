"""Tests for analysis module."""

import pytest

from microecon.batch import BatchRunner, run_comparison
from microecon.bargaining import NashBargainingProtocol, RubinsteinBargainingProtocol
from microecon.analysis import (
    # Loader
    group_by_protocol,
    group_by_seed,
    pair_runs_by_seed,
    # Time series
    welfare_over_time,
    trades_over_time,
    trades_per_tick,
    agent_utility_over_time,
    welfare_gains_over_time,
    average_utility_over_time,
    compare_welfare_trajectories,
    mrs_over_time,
    mrs_dispersion_over_time,
    # Distributions
    compare_final_welfare,
    compare_total_trades,
    compare_protocols,
    compare_values,
    final_welfare,
    total_trades,
    # Tracking
    agent_outcomes,
    gains_by_alpha,
    compare_agent_outcomes,
    winners_and_losers,
    search_efficiency,
)
from microecon.logging import SimulationLogger, SimulationConfig
from microecon.simulation import create_simple_economy

pytestmark = pytest.mark.analysis


def _create_test_run(seed=42, protocol="nash", ticks=10):
    """Helper to create a test run."""
    proto = (
        NashBargainingProtocol()
        if protocol == "nash"
        else RubinsteinBargainingProtocol()
    )
    config = SimulationConfig(
        n_agents=4, grid_size=5, seed=seed, protocol_name=protocol
    )
    logger = SimulationLogger(config)
    sim = create_simple_economy(
        n_agents=4, grid_size=5, seed=seed, bargaining_protocol=proto
    )
    sim.logger = logger
    sim.run(ticks)
    return logger.finalize()


class TestLoader:
    """Test loader utilities."""

    def test_group_by_protocol(self):
        runs = [
            _create_test_run(seed=1, protocol="nash"),
            _create_test_run(seed=2, protocol="nash"),
            _create_test_run(seed=1, protocol="rubinstein"),
        ]

        grouped = group_by_protocol(runs)

        assert "nash" in grouped
        assert "rubinstein" in grouped
        assert len(grouped["nash"]) == 2
        assert len(grouped["rubinstein"]) == 1

    def test_group_by_seed(self):
        runs = [
            _create_test_run(seed=1, protocol="nash"),
            _create_test_run(seed=1, protocol="rubinstein"),
            _create_test_run(seed=2, protocol="nash"),
        ]

        grouped = group_by_seed(runs)

        assert 1 in grouped
        assert 2 in grouped
        assert len(grouped[1]) == 2
        assert len(grouped[2]) == 1

    def test_pair_runs_by_seed(self):
        runs = [
            _create_test_run(seed=1, protocol="nash"),
            _create_test_run(seed=1, protocol="rubinstein"),
            _create_test_run(seed=2, protocol="nash"),
            _create_test_run(seed=2, protocol="rubinstein"),
        ]

        pairs = pair_runs_by_seed(runs, "nash", "rubinstein")

        assert len(pairs) == 2
        for run_a, run_b in pairs:
            assert run_a.config.protocol_name == "nash"
            assert run_b.config.protocol_name == "rubinstein"
            assert run_a.config.seed == run_b.config.seed


class TestTimeSeries:
    """Test time series analysis functions."""

    def test_welfare_over_time(self):
        run = _create_test_run(ticks=10)
        welfare = welfare_over_time(run)

        assert len(welfare) == 10
        assert all(w > 0 for w in welfare)
        # Welfare should generally not decrease (trades create value)
        # But it can stay flat if no trades occur

    def test_trades_over_time(self):
        run = _create_test_run(ticks=10)
        trades = trades_over_time(run)

        assert len(trades) == 10
        assert all(t >= 0 for t in trades)
        # Cumulative trades should be non-decreasing
        for i in range(1, len(trades)):
            assert trades[i] >= trades[i - 1]

    def test_trades_per_tick(self):
        run = _create_test_run(ticks=10)
        per_tick = trades_per_tick(run)

        assert len(per_tick) == 10
        assert all(t >= 0 for t in per_tick)

    def test_agent_utility_over_time(self):
        run = _create_test_run(ticks=10)
        agent_id = run.agent_ids[0]
        utilities = agent_utility_over_time(run, agent_id)

        assert len(utilities) == 10
        assert all(u > 0 for u in utilities)

    def test_welfare_gains_over_time(self):
        run = _create_test_run(ticks=10)
        gains = welfare_gains_over_time(run)

        assert len(gains) == 10
        assert gains[0] == 0  # No gain at start
        # Gains should be non-negative
        assert all(g >= -1e-9 for g in gains)

    def test_average_utility_over_time(self):
        run = _create_test_run(ticks=10)
        averages = average_utility_over_time(run)

        assert len(averages) == 10
        assert all(a > 0 for a in averages)

    def test_compare_welfare_trajectories(self):
        run_a = _create_test_run(seed=1, protocol="nash")
        run_b = _create_test_run(seed=1, protocol="rubinstein")

        diff = compare_welfare_trajectories(run_a, run_b)

        assert len(diff) == 10

    def test_mrs_over_time(self):
        run = _create_test_run(ticks=10)
        mrs = mrs_over_time(run)

        assert len(mrs) == 10
        # Each tick should have MRS for each agent
        for tick_mrs in mrs:
            assert isinstance(tick_mrs, dict)
            # MRS values should be positive (for sensible endowments)
            assert all(m > 0 for m in tick_mrs.values() if m != float("inf"))

    def test_mrs_dispersion_over_time(self):
        run = _create_test_run(ticks=10)
        dispersion = mrs_dispersion_over_time(run)

        assert len(dispersion) == 10
        # Dispersion (CV) should be non-negative
        import math
        for d in dispersion:
            if math.isfinite(d):
                assert d >= 0


class TestDistributions:
    """Test distribution comparison functions."""

    def test_final_welfare(self):
        run = _create_test_run(ticks=10)
        welfare = final_welfare(run)
        assert welfare > 0

    def test_total_trades(self):
        run = _create_test_run(ticks=20)
        trades = total_trades(run)
        assert trades >= 0

    def test_compare_final_welfare(self):
        runs_a = [_create_test_run(seed=i, protocol="nash") for i in range(3)]
        runs_b = [_create_test_run(seed=i, protocol="rubinstein") for i in range(3)]

        result = compare_final_welfare(runs_a, runs_b, "Nash", "Rubinstein")

        assert result.metric == "Final Welfare"
        assert result.group_a_name == "Nash"
        assert result.group_b_name == "Rubinstein"
        assert len(result.group_a_values) == 3
        assert len(result.group_b_values) == 3

    def test_compare_total_trades(self):
        runs_a = [_create_test_run(seed=i, protocol="nash", ticks=20) for i in range(3)]
        runs_b = [_create_test_run(seed=i, protocol="rubinstein", ticks=20) for i in range(3)]

        result = compare_total_trades(runs_a, runs_b, "Nash", "Rubinstein")

        assert result.metric == "Total Trades"
        assert len(result.group_a_values) == 3

    def test_compare_values(self):
        result = compare_values(
            values_a=[10.0, 12.0, 11.0],
            values_b=[15.0, 14.0, 16.0],
            metric_name="welfare",
            group_a_name="control",
            group_b_name="treatment",
        )
        assert result.metric == "welfare"
        assert result.group_a_name == "control"
        assert result.group_b_name == "treatment"
        assert result.group_a_mean == pytest.approx(11.0)
        assert result.group_b_mean == pytest.approx(15.0)
        assert result.difference == pytest.approx(4.0)
        assert result.effect_size > 0
        assert result.group_a_values == [10.0, 12.0, 11.0]
        assert result.group_b_values == [15.0, 14.0, 16.0]

    def test_compare_protocols(self):
        runs = [
            _create_test_run(seed=i, protocol="nash", ticks=15)
            for i in range(3)
        ] + [
            _create_test_run(seed=i, protocol="rubinstein", ticks=15)
            for i in range(3)
        ]

        results = compare_protocols(runs, "nash", "rubinstein")

        assert "final_welfare" in results
        assert "total_trades" in results
        assert "welfare_gain" in results


class TestTracking:
    """Test agent-level tracking functions."""

    def test_agent_outcomes(self):
        run = _create_test_run(ticks=20)
        outcomes = agent_outcomes(run)

        assert len(outcomes) == 4  # 4 agents

        for outcome in outcomes:
            assert outcome.agent_id
            assert 0 < outcome.alpha < 1
            assert outcome.initial_utility > 0
            assert outcome.final_utility > 0

    def test_gains_by_alpha(self):
        run = _create_test_run(ticks=20)
        gains = gains_by_alpha(run)

        assert len(gains) == 4
        for alpha, gain in gains:
            assert 0 < alpha < 1

    def test_compare_agent_outcomes(self):
        # Note: compare_agent_outcomes matches by agent_id, which only works
        # when comparing the same simulation run (e.g., replay vs live).
        # Different runs have different agent IDs even with same seed.
        run = _create_test_run(seed=42, protocol="nash", ticks=20)

        # Compare run with itself should match all agents
        comparisons = compare_agent_outcomes(run, run)

        assert len(comparisons) == 4  # All agents match

        for agent_id, alpha, gain_a, gain_b in comparisons:
            assert agent_id
            assert 0 < alpha < 1
            assert gain_a == gain_b  # Same run, same gains

    def test_winners_and_losers(self):
        # Same note: this function only works for runs with matching agent IDs
        run = _create_test_run(seed=42, protocol="nash", ticks=20)

        # Compare run with itself - all should be ties
        winners, losers, ties = winners_and_losers(run, run)

        assert len(winners) == 0
        assert len(losers) == 0
        assert len(ties) == 4

    def test_search_efficiency(self):
        run = _create_test_run(ticks=10)
        stats = search_efficiency(run)

        assert len(stats) == 4  # 4 agents

        for s in stats:
            assert s.agent_id
            assert s.total_evaluations >= 0
            assert s.total_movements >= 0
            assert s.average_visible >= 0
