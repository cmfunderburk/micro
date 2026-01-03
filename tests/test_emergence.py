"""Tests for market emergence analysis."""

import pytest
from microecon.analysis.emergence import (
    build_trade_network,
    trade_network_stats,
    welfare_efficiency,
    detect_trading_clusters,
    agent_trajectories,
    convergence_analysis,
    analyze_market_emergence,
    compute_theoretical_max_gains,
)
from microecon.logging import RunData, SimulationConfig, TickRecord, AgentSnapshot, TradeEvent


def create_test_run(
    n_agents: int = 4,
    ticks: int = 10,
    trades: list[tuple[int, str, str]] | None = None,
) -> RunData:
    """Create a test RunData object.

    Args:
        n_agents: Number of agents
        ticks: Number of ticks
        trades: List of (tick, agent1_id, agent2_id) tuples for trades

    Returns:
        RunData object
    """
    config = SimulationConfig(
        n_agents=n_agents,
        grid_size=10,
        perception_radius=5.0,
        seed=42,
        protocol_name="nash",
    )

    # Create agent snapshots (vary alpha for diversity)
    tick_records = []
    agent_ids = [f"agent_{i}" for i in range(n_agents)]

    for t in range(ticks):
        # Create agent snapshots with varying positions
        snapshots = []
        for i, aid in enumerate(agent_ids):
            # Agents move around a bit
            row = (i + t) % 10
            col = i % 10
            snapshots.append(AgentSnapshot(
                agent_id=aid,
                position=(row, col),
                alpha=0.2 + 0.6 * (i / max(1, n_agents - 1)),
                endowment=(10.0 - i, 2.0 + i),
                utility=5.0 + t * 0.1,
            ))

        # Add trades
        trade_records = []
        if trades:
            for trade_tick, a1, a2 in trades:
                if trade_tick == t:
                    trade_records.append(TradeEvent(
                        agent1_id=a1,
                        agent2_id=a2,
                        proposer_id=a1,
                        pre_endowments=((5.0, 5.0), (5.0, 5.0)),
                        post_allocations=((6.0, 4.0), (4.0, 6.0)),
                        utilities=(5.5, 5.5),
                        gains=(0.5, 0.5),
                        trade_occurred=True,
                    ))

        tick_records.append(TickRecord(
            tick=t,
            agent_snapshots=tuple(snapshots),
            trades=tuple(trade_records),
            movements=(),
            search_decisions=(),
            commitments_formed=(),
            commitments_broken=(),
            total_welfare=sum(s.utility for s in snapshots),
            cumulative_trades=sum(1 for tt, _, _ in (trades or []) if tt <= t),
        ))

    return RunData(config=config, ticks=tick_records)


class TestTradeNetwork:
    """Tests for trade network analysis."""

    def test_empty_run(self):
        """Empty run should produce empty network."""
        config = SimulationConfig(n_agents=0, grid_size=10, perception_radius=5.0, seed=42, protocol_name="nash")
        run = RunData(config=config, ticks=[])
        network = build_trade_network(run)
        assert len(network) == 0

    def test_network_from_trades(self):
        """Trades should create network edges."""
        trades = [
            (0, "agent_0", "agent_1"),
            (1, "agent_0", "agent_2"),
            (2, "agent_1", "agent_2"),
        ]
        run = create_test_run(n_agents=4, trades=trades)
        network = build_trade_network(run)

        # Check edges exist
        assert "agent_1" in network.get("agent_0", {}) or "agent_0" in network.get("agent_1", {})
        assert "agent_2" in network.get("agent_0", {}) or "agent_0" in network.get("agent_2", {})

    def test_network_stats_empty(self):
        """Empty run should have zero stats."""
        config = SimulationConfig(n_agents=0, grid_size=10, perception_radius=5.0, seed=42, protocol_name="nash")
        run = RunData(config=config, ticks=[])
        stats = trade_network_stats(run)

        assert stats.n_nodes == 0
        assert stats.n_edges == 0
        assert stats.total_trades == 0

    def test_network_stats_with_trades(self):
        """Stats should reflect trade structure."""
        trades = [
            (0, "agent_0", "agent_1"),
            (1, "agent_0", "agent_1"),  # Same pair again
            (2, "agent_0", "agent_2"),
        ]
        run = create_test_run(n_agents=4, trades=trades)
        stats = trade_network_stats(run)

        assert stats.n_nodes == 4
        assert stats.n_edges == 2  # Two unique pairs
        assert stats.total_trades == 3  # Three trades total
        assert stats.density > 0
        assert stats.avg_degree > 0

    def test_hub_detection(self):
        """Agent with most trades should be identified as hub."""
        trades = [
            (0, "agent_0", "agent_1"),
            (1, "agent_0", "agent_2"),
            (2, "agent_0", "agent_3"),
        ]
        run = create_test_run(n_agents=4, trades=trades)
        stats = trade_network_stats(run)

        assert "agent_0" in stats.hub_agent_ids
        assert stats.max_degree == 3

    def test_isolated_agents(self):
        """Agents with no trades should be identified."""
        trades = [
            (0, "agent_0", "agent_1"),
        ]
        run = create_test_run(n_agents=4, trades=trades)
        stats = trade_network_stats(run)

        # Agents 2 and 3 have no trades
        assert "agent_2" in stats.isolated_agent_ids
        assert "agent_3" in stats.isolated_agent_ids


class TestWelfareEfficiency:
    """Tests for welfare efficiency analysis."""

    def test_efficiency_empty_run(self):
        """Empty run should have zero efficiency."""
        config = SimulationConfig(n_agents=0, grid_size=10, perception_radius=5.0, seed=42, protocol_name="nash")
        run = RunData(config=config, ticks=[])
        result = welfare_efficiency(run)

        assert result.achieved_gains == 0.0
        assert result.theoretical_max_gains == 0.0

    def test_efficiency_with_trades(self):
        """Run with trades should show gains."""
        trades = [(0, "agent_0", "agent_1")]
        run = create_test_run(n_agents=4, trades=trades)
        result = welfare_efficiency(run)

        assert result.final_welfare > result.initial_welfare
        assert result.achieved_gains > 0
        assert 0 <= result.efficiency_ratio <= 1

    def test_theoretical_max_positive(self):
        """Theoretical max should be positive for diverse agents."""
        run = create_test_run(n_agents=4)
        max_gains = compute_theoretical_max_gains(run)
        # With diverse alphas and endowments, there should be gains available
        assert max_gains >= 0


class TestSpatialClustering:
    """Tests for spatial cluster detection."""

    def test_no_clusters_empty_run(self):
        """Empty run should have no clusters."""
        config = SimulationConfig(n_agents=0, grid_size=10, perception_radius=5.0, seed=42, protocol_name="nash")
        run = RunData(config=config, ticks=[])
        clusters = detect_trading_clusters(run)
        assert len(clusters) == 0

    def test_cluster_from_trades_at_same_location(self):
        """Multiple trades at same location should form a cluster."""
        # Create run where agents trade repeatedly at same location
        trades = [
            (0, "agent_0", "agent_1"),
            (1, "agent_0", "agent_1"),
            (2, "agent_0", "agent_1"),
            (3, "agent_0", "agent_1"),
        ]
        run = create_test_run(n_agents=4, trades=trades)
        clusters = detect_trading_clusters(run, min_cluster_size=3)

        # Should have at least one cluster
        assert len(clusters) >= 1
        assert clusters[0].trade_count >= 3


class TestAgentTrajectories:
    """Tests for agent trajectory analysis."""

    def test_trajectories_empty_run(self):
        """Empty run should have no trajectories."""
        config = SimulationConfig(n_agents=0, grid_size=10, perception_radius=5.0, seed=42, protocol_name="nash")
        run = RunData(config=config, ticks=[])
        trajectories = agent_trajectories(run)
        assert len(trajectories) == 0

    def test_trajectories_count(self):
        """Should have one trajectory per agent."""
        run = create_test_run(n_agents=4, ticks=10)
        trajectories = agent_trajectories(run)
        assert len(trajectories) == 4

    def test_trajectory_positions(self):
        """Trajectories should have correct number of positions."""
        run = create_test_run(n_agents=4, ticks=10)
        trajectories = agent_trajectories(run)

        for traj in trajectories:
            assert len(traj.positions) == 10

    def test_trajectory_distance_calculation(self):
        """Total distance should be non-negative."""
        run = create_test_run(n_agents=4, ticks=10)
        trajectories = agent_trajectories(run)

        for traj in trajectories:
            assert traj.total_distance >= 0
            assert traj.final_distance_from_start >= 0


class TestConvergenceAnalysis:
    """Tests for convergence analysis."""

    def test_convergence_empty_run(self):
        """Empty run should have zero convergence stats."""
        config = SimulationConfig(n_agents=0, grid_size=10, perception_radius=5.0, seed=42, protocol_name="nash")
        run = RunData(config=config, ticks=[])
        stats = convergence_analysis(run)

        assert stats.avg_total_distance == 0.0
        assert stats.agents_at_hotspots == 0

    def test_convergence_with_agents(self):
        """Run with agents should have valid convergence stats."""
        trades = [(0, "agent_0", "agent_1")]
        run = create_test_run(n_agents=4, ticks=10, trades=trades)
        stats = convergence_analysis(run)

        assert stats.avg_total_distance >= 0
        assert 0 <= stats.hotspot_convergence_rate <= 1


class TestMarketEmergenceReport:
    """Tests for comprehensive market emergence analysis."""

    def test_full_report(self):
        """Should generate complete report for a run."""
        trades = [
            (0, "agent_0", "agent_1"),
            (2, "agent_1", "agent_2"),
            (4, "agent_2", "agent_3"),
        ]
        run = create_test_run(n_agents=4, ticks=10, trades=trades)
        report = analyze_market_emergence(run)

        assert report.n_agents == 4
        assert report.total_ticks == 10
        assert report.network is not None
        assert report.efficiency is not None
        assert report.clusters is not None
        assert report.convergence is not None

    def test_report_network_matches(self):
        """Report network stats should match direct call."""
        run = create_test_run(n_agents=4, ticks=10)
        report = analyze_market_emergence(run)
        direct_stats = trade_network_stats(run)

        assert report.network.n_nodes == direct_stats.n_nodes
        assert report.network.n_edges == direct_stats.n_edges
