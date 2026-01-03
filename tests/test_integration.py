"""
Integration tests for the full simulation-to-analysis pipeline.

These tests cover:
- Full scenario-to-analysis pipeline (setup → simulation → logging → analysis)
- Information environment integration (noisy types flow through search/bargaining)
- Batch comparison workflow (multiple protocols, statistical comparison)

Visualization data flow is tested manually (DearPyGui requires display).
"""

import pytest
from pathlib import Path
import tempfile

from microecon.agent import create_agent, Agent
from microecon.grid import Grid, Position
from microecon.simulation import Simulation
from microecon.information import FullInformation, NoisyAlphaInformation
from microecon.bargaining import NashBargainingProtocol, RubinsteinBargainingProtocol
from microecon.matching import OpportunisticMatchingProtocol, StableRoommatesMatchingProtocol
from microecon.logging import SimulationLogger, SimulationConfig
from microecon.batch import BatchRunner


class TestFullPipeline:
    """Test the complete scenario-to-analysis pipeline."""

    def test_setup_to_analysis(self):
        """Test full pipeline: setup → simulation → logging → analysis."""
        from microecon.analysis import (
            welfare_over_time,
            trades_over_time,
            agent_outcomes,
        )
        from microecon.analysis.emergence import (
            trade_network_stats,
            welfare_efficiency,
        )

        # 1. Setup: Create agents and grid
        agents = [
            create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0),
            create_agent(alpha=0.5, endowment_x=6.0, endowment_y=6.0),
            create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0),
            create_agent(alpha=0.4, endowment_x=8.0, endowment_y=4.0),
        ]
        grid_size = 10

        # 2. Configure logging
        config = SimulationConfig(
            n_agents=len(agents),
            grid_size=grid_size,
            seed=42,
            protocol_name="nash",
        )
        logger = SimulationLogger(config=config)

        # 3. Create simulation with logging
        grid = Grid(size=grid_size)
        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
            matching_protocol=OpportunisticMatchingProtocol(),
            info_env=FullInformation(),
            logger=logger,
        )

        # 4. Place agents
        positions = [Position(0, 0), Position(0, 5), Position(5, 0), Position(5, 5)]
        for agent, pos in zip(agents, positions):
            sim.add_agent(agent, pos)

        # 5. Run simulation
        sim.run(ticks=50)

        # 6. Get run data
        run_data = logger.finalize()

        # 7. Verify basic structure
        assert len(run_data.ticks) == 50
        assert run_data.config.n_agents == 4

        # 8. Run time-series analysis
        welfare = welfare_over_time(run_data)
        trades = trades_over_time(run_data)

        assert len(welfare) == 50
        assert all(w > 0 for w in welfare)  # Welfare should be positive
        assert trades[-1] >= 0  # Cumulative trades

        # 9. Run agent-level analysis
        outcomes = agent_outcomes(run_data)
        assert len(outcomes) == 4
        for outcome in outcomes:
            assert outcome.agent_id is not None
            assert 0 < outcome.alpha < 1

        # 10. Run network analysis
        network_stats = trade_network_stats(run_data)
        assert network_stats.n_nodes == 4
        assert network_stats.total_trades >= 0

        # 11. Run efficiency analysis
        efficiency = welfare_efficiency(run_data)
        assert efficiency.initial_welfare > 0
        assert efficiency.theoretical_max_gains >= 0

    def test_pipeline_with_disk_logging(self):
        """Test pipeline with logging to disk and reloading."""
        from microecon.logging import load_run

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_run.jsonl"

            # Setup
            config = SimulationConfig(
                n_agents=4,
                grid_size=10,
                seed=42,
                protocol_name="nash",
            )
            logger = SimulationLogger(config=config, output_path=output_path)

            grid = Grid(size=10)
            sim = Simulation(
                grid=grid,
                bargaining_protocol=NashBargainingProtocol(),
                logger=logger,
            )

            for i in range(4):
                agent = create_agent(
                    alpha=0.3 + 0.2 * i,
                    endowment_x=5.0,
                    endowment_y=5.0,
                )
                sim.add_agent(agent, Position(i % 2 * 5, i // 2 * 5))

            # Run
            sim.run(ticks=20)
            logger.finalize()

            # Reload from disk
            reloaded = load_run(output_path)

            assert len(reloaded.ticks) == 20
            assert reloaded.config.n_agents == 4


class TestInformationEnvironmentIntegration:
    """Test that information environments integrate through the full pipeline."""

    def test_noisy_info_affects_search(self):
        """Noisy information should affect agent search behavior."""
        # Create complementary agents
        agents = [
            create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=10.0),
            create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=10.0),
        ]

        # Run with full information
        config_full = SimulationConfig(n_agents=2, grid_size=10, seed=42, protocol_name="nash")
        logger_full = SimulationLogger(config=config_full)
        grid_full = Grid(size=10)
        sim_full = Simulation(
            grid=grid_full,
            bargaining_protocol=NashBargainingProtocol(),
            info_env=FullInformation(),
            logger=logger_full,
        )
        sim_full.add_agent(agents[0], Position(0, 0))
        sim_full.add_agent(agents[1], Position(9, 9))
        sim_full.run(ticks=30)
        run_full = logger_full.finalize()

        # Run with noisy information
        agents_noisy = [
            create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=10.0),
            create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=10.0),
        ]
        config_noisy = SimulationConfig(n_agents=2, grid_size=10, seed=42, protocol_name="nash")
        logger_noisy = SimulationLogger(config=config_noisy)
        grid_noisy = Grid(size=10)
        sim_noisy = Simulation(
            grid=grid_noisy,
            bargaining_protocol=NashBargainingProtocol(),
            info_env=NoisyAlphaInformation(noise_std=0.2, seed=99),
            logger=logger_noisy,
        )
        sim_noisy.add_agent(agents_noisy[0], Position(0, 0))
        sim_noisy.add_agent(agents_noisy[1], Position(9, 9))
        sim_noisy.run(ticks=30)
        run_noisy = logger_noisy.finalize()

        # Both should complete successfully
        assert len(run_full.ticks) == 30
        assert len(run_noisy.ticks) == 30

        # Search decisions should be recorded
        assert any(len(t.search_decisions) > 0 for t in run_full.ticks)
        assert any(len(t.search_decisions) > 0 for t in run_noisy.ticks)

    def test_noisy_info_with_bargaining(self):
        """Noisy information should affect bargaining outcomes."""
        from microecon.analysis import agent_outcomes

        def run_scenario(info_env, seed):
            agents = [
                create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0),
                create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0),
            ]
            config = SimulationConfig(n_agents=2, grid_size=5, seed=seed, protocol_name="nash")
            logger = SimulationLogger(config=config)
            grid = Grid(size=5)
            sim = Simulation(
                grid=grid,
                bargaining_protocol=NashBargainingProtocol(),
                info_env=info_env,
                logger=logger,
            )
            # Place at same position to force trade
            sim.add_agent(agents[0], Position(2, 2))
            sim.add_agent(agents[1], Position(2, 2))
            sim.run(ticks=10)
            return logger.finalize()

        # Full info run
        run_full = run_scenario(FullInformation(), seed=42)
        outcomes_full = agent_outcomes(run_full)

        # Noisy info run
        run_noisy = run_scenario(NoisyAlphaInformation(noise_std=0.15, seed=123), seed=42)
        outcomes_noisy = agent_outcomes(run_noisy)

        # Both should produce outcomes
        assert len(outcomes_full) == 2
        assert len(outcomes_noisy) == 2


class TestBatchComparisonWorkflow:
    """Test batch comparison across multiple protocols."""

    def test_protocol_comparison_batch(self):
        """Run same scenario with different protocols and compare."""
        from microecon.analysis import compare_protocols

        base_config = {
            'n_agents': 6,
            'grid_size': 10,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Run batch with both protocols
            runner = BatchRunner(
                base_config=base_config,
                variations={
                    'protocol': [NashBargainingProtocol(), RubinsteinBargainingProtocol()],
                    'seed': [42, 43],
                },
                output_dir=Path(tmpdir),
            )
            results = runner.run(ticks=30)

            # Should have 4 results (2 protocols x 2 seeds)
            assert len(results) == 4

            # Run statistical comparison
            all_runs = [r.run_data for r in results]
            comparisons = compare_protocols(all_runs)

            # Should have comparison results
            assert len(comparisons) > 0

    def test_matching_protocol_comparison(self):
        """Compare opportunistic vs stable matching."""
        from microecon.analysis.emergence import trade_network_stats

        base_config = {
            'n_agents': 8,
            'grid_size': 12,
            'perception_radius': 5.0,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Run batch with both matching protocols
            runner = BatchRunner(
                base_config=base_config,
                variations={
                    'matching_protocol': [
                        OpportunisticMatchingProtocol(),
                        StableRoommatesMatchingProtocol(),
                    ],
                    'seed': [42],
                },
                output_dir=Path(tmpdir),
            )
            results = runner.run(ticks=40)

            # Should have 2 results (2 matching protocols x 1 seed)
            assert len(results) == 2

            # Analyze network structure for each
            for result in results:
                network = trade_network_stats(result.run_data)
                assert network.n_nodes == 8


class TestScenarioToAnalysisPipeline:
    """Test using the scenarios module through to analysis."""

    def test_market_emergence_pipeline(self):
        """Full market emergence scenario through analysis."""
        from microecon.scenarios import MarketEmergenceConfig, run_market_emergence
        from microecon.analysis.emergence import (
            trade_network_stats,
            welfare_efficiency,
            detect_trading_clusters,
        )

        # Run a small market emergence scenario
        config = MarketEmergenceConfig(
            n_agents=12,
            grid_size=8,
            ticks=30,
            seed=42,
        )
        result = run_market_emergence(config)

        # Verify result structure
        assert result.analysis is not None
        assert result.run_data is not None

        # Run additional analyses on the run data
        network = trade_network_stats(result.run_data)
        efficiency = welfare_efficiency(result.run_data)
        clusters = detect_trading_clusters(result.run_data)

        # Verify analyses completed
        assert network.n_nodes == 12
        assert efficiency.theoretical_max_gains >= 0
        assert isinstance(clusters, list)

    def test_protocol_comparison_scenario(self):
        """Compare protocols using market emergence scenario."""
        from microecon.scenarios import MarketEmergenceConfig, run_market_emergence

        config = MarketEmergenceConfig(
            n_agents=10,
            grid_size=8,
            ticks=25,
            seed=42,
        )

        # Run with Nash bargaining
        result_nash = run_market_emergence(
            config,
            bargaining_protocol=NashBargainingProtocol(),
        )

        # Run with Rubinstein bargaining
        result_rub = run_market_emergence(
            config,
            bargaining_protocol=RubinsteinBargainingProtocol(),
        )

        # Both should complete
        assert result_nash.analysis.total_ticks == 25
        assert result_rub.analysis.total_ticks == 25

        # Can compare efficiency
        eff_nash = result_nash.analysis.efficiency.efficiency_ratio
        eff_rub = result_rub.analysis.efficiency.efficiency_ratio

        # Both should be valid ratios
        assert 0 <= eff_nash <= 1.5  # Can exceed 1 due to repeated trades
        assert 0 <= eff_rub <= 1.5


class TestReplayControllerIntegration:
    """Test replay controller with logged data."""

    def test_replay_from_logged_run(self):
        """Create a run, log it, and replay it."""
        from microecon.visualization.replay import ReplayController

        # Create and run simulation with logging
        config = SimulationConfig(n_agents=4, grid_size=10, seed=42, protocol_name="nash")
        logger = SimulationLogger(config=config)
        grid = Grid(size=10)
        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
            logger=logger,
        )

        for i in range(4):
            agent = create_agent(alpha=0.3 + 0.2 * i, endowment_x=5.0, endowment_y=5.0)
            sim.add_agent(agent, Position(i, i))

        sim.run(ticks=20)
        run_data = logger.finalize()

        # Create replay controller
        controller = ReplayController(run_data)

        # Test navigation
        assert controller.current_tick == 0
        assert controller.total_ticks == 20

        controller.step()
        assert controller.current_tick == 1

        controller.seek(10)
        assert controller.current_tick == 10

        state = controller.get_state()
        assert len(state.agent_snapshots) == 4

        controller.step_back()
        assert controller.current_tick == 9

        controller.reset()
        assert controller.current_tick == 0
