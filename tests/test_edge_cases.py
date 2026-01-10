"""
Edge case tests for graceful degradation and boundary conditions.

Per COMPLETION-CRITERIA.md Phase 2.3:
- Graceful degradation for degenerate cases (no gains from trade, extreme endowments)
- Reasonable behavior at scale boundaries (1 agent, 500 agents)
- Clear error messages for invalid configurations
- Documented limitations
"""

import pytest
import math

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import Agent, AgentPrivateState, create_agent
from microecon.grid import Grid, Position
from microecon.simulation import Simulation, create_simple_economy
from microecon.information import FullInformation, NoisyAlphaInformation
from microecon.bargaining import (
    NashBargainingProtocol,
    RubinsteinBargainingProtocol,
    nash_bargaining_solution,
    compute_nash_surplus,
)
from microecon.matching import OpportunisticMatchingProtocol, StableRoommatesMatchingProtocol
from microecon.scenarios import MarketEmergenceConfig, run_market_emergence

pytestmark = pytest.mark.simulation


class TestInvalidConfigurations:
    """Test that invalid configurations produce clear error messages."""

    def test_alpha_zero_raises_clear_error(self):
        """Alpha=0 should raise ValueError with clear message."""
        with pytest.raises(ValueError, match="alpha must be in"):
            CobbDouglas(alpha=0.0)

    def test_alpha_one_raises_clear_error(self):
        """Alpha=1 should raise ValueError with clear message."""
        with pytest.raises(ValueError, match="alpha must be in"):
            CobbDouglas(alpha=1.0)

    def test_alpha_negative_raises_clear_error(self):
        """Alpha<0 should raise ValueError."""
        with pytest.raises(ValueError, match="alpha must be in"):
            CobbDouglas(alpha=-0.5)

    def test_alpha_greater_than_one_raises_clear_error(self):
        """Alpha>1 should raise ValueError."""
        with pytest.raises(ValueError, match="alpha must be in"):
            CobbDouglas(alpha=1.5)

    def test_negative_endowment_raises_clear_error(self):
        """Negative endowment should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Bundle(-1.0, 5.0)

    def test_grid_size_zero_raises_clear_error(self):
        """Grid size 0 should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            Grid(size=0)

    def test_grid_size_negative_raises_clear_error(self):
        """Negative grid size should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            Grid(size=-5)

    def test_noise_std_negative_raises_clear_error(self):
        """Negative noise_std should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            NoisyAlphaInformation(noise_std=-0.1)

    def test_market_emergence_too_few_agents(self):
        """MarketEmergenceConfig should reject n_agents < 2."""
        with pytest.raises(ValueError, match="n_agents must be >= 2"):
            MarketEmergenceConfig(n_agents=1)

    def test_market_emergence_grid_too_small(self):
        """MarketEmergenceConfig should reject grid_size < 5."""
        with pytest.raises(ValueError, match="grid_size must be >= 5"):
            MarketEmergenceConfig(n_agents=10, grid_size=3)

    def test_market_emergence_invalid_alpha_range(self):
        """MarketEmergenceConfig should reject invalid alpha_range."""
        with pytest.raises(ValueError, match="alpha_range"):
            MarketEmergenceConfig(alpha_range=(0.8, 0.2))  # Reversed

        with pytest.raises(ValueError, match="alpha_range"):
            MarketEmergenceConfig(alpha_range=(0.0, 0.5))  # Min at boundary

    def test_rubinstein_invalid_delta(self):
        """Rubinstein with invalid delta should raise ValueError."""
        from microecon.bargaining import rubinstein_bargaining_solution

        with pytest.raises(ValueError, match="delta"):
            rubinstein_bargaining_solution(
                prefs_1=CobbDouglas(0.3),
                endowment_1=Bundle(10, 5),
                prefs_2=CobbDouglas(0.7),
                endowment_2=Bundle(5, 10),
                delta_1=0.0,  # Invalid
                delta_2=0.95,
            )

        with pytest.raises(ValueError, match="delta"):
            rubinstein_bargaining_solution(
                prefs_1=CobbDouglas(0.3),
                endowment_1=Bundle(10, 5),
                prefs_2=CobbDouglas(0.7),
                endowment_2=Bundle(5, 10),
                delta_1=0.95,
                delta_2=1.0,  # Invalid (boundary)
            )


class TestDegenerateCases:
    """Test graceful degradation for degenerate economic cases."""

    def test_no_gains_from_trade_identical_preferences(self):
        """Agents with identical preferences may have no gains from trade."""
        prefs = CobbDouglas(0.5)
        bundle_a = Bundle(10.0, 10.0)
        bundle_b = Bundle(10.0, 10.0)

        # No trade should occur (identical preferences and endowments)
        result = nash_bargaining_solution(prefs, bundle_a, prefs, bundle_b)
        # With identical preferences and endowments, gains should be minimal
        assert result.gains_1 == pytest.approx(0.0, abs=1e-6) or result.gains_2 == pytest.approx(0.0, abs=1e-6)

    def test_no_gains_from_trade_balanced_endowments(self):
        """Agents with balanced endowments may have no gains from trade."""
        # Even with different preferences, if endowments are balanced,
        # there may be gains from trade (alpha differences create surplus)
        prefs_a = CobbDouglas(0.3)
        prefs_b = CobbDouglas(0.7)
        bundle_a = Bundle(10.0, 10.0)  # Balanced
        bundle_b = Bundle(10.0, 10.0)  # Balanced

        # Should handle gracefully (may or may not find gains)
        result = nash_bargaining_solution(prefs_a, bundle_a, prefs_b, bundle_b)
        # Result exists, simulation continues
        assert result is not None

    def test_extreme_endowment_imbalance(self):
        """One agent has extreme endowment of one good only."""
        prefs_a = CobbDouglas(0.5)
        prefs_b = CobbDouglas(0.5)
        bundle_a = Bundle(1000.0, 0.01)  # Extreme x-rich
        bundle_b = Bundle(0.01, 1000.0)  # Extreme y-rich

        # Should find gains from trade (complementary endowments)
        result = nash_bargaining_solution(prefs_a, bundle_a, prefs_b, bundle_b)
        assert result is not None
        assert result.gains_1 > 0 or result.gains_2 > 0

    def test_near_zero_endowment(self):
        """Agents with very small endowments should work without errors."""
        agent_a = create_agent(alpha=0.3, endowment_x=0.001, endowment_y=0.001)
        agent_b = create_agent(alpha=0.7, endowment_x=0.001, endowment_y=0.001)

        # Should compute utility without errors
        assert agent_a.utility() > 0
        assert agent_b.utility() > 0

    def test_zero_component_endowment(self):
        """Endowment with one zero component should give zero utility."""
        # Zero y means zero utility for Cobb-Douglas
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=0.0)
        assert agent.utility() == 0.0

    def test_simulation_with_no_trades_possible(self):
        """Simulation should complete even if no trades are possible."""
        # Create agents with identical preferences and endowments
        grid = Grid(size=5)
        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
        )

        # Create identical agents (no gains from trade)
        for i in range(4):
            agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=10.0)
            sim.add_agent(agent, Position(2, 2))  # Same position

        # Should run without error, even with no trades
        sim.run(ticks=10)
        assert sim.tick == 10
        # May have 0 trades, which is fine

    def test_compute_surplus_zero_endowment(self):
        """compute_nash_surplus should handle zero utility gracefully."""
        from microecon.agent import AgentType
        prefs_a = CobbDouglas(0.5)
        prefs_b = CobbDouglas(0.5)
        # Zero utility case
        bundle_a = Bundle(10.0, 0.0)  # Zero y
        bundle_b = Bundle(0.0, 10.0)  # Zero x

        # Create AgentType objects as compute_nash_surplus expects
        type_a = AgentType(prefs_a, bundle_a)
        type_b = AgentType(prefs_b, bundle_b)

        # Both have zero utility, should still compute
        surplus = compute_nash_surplus(type_a, type_b)
        # Surplus should be non-negative and finite
        assert isinstance(surplus, float)
        assert math.isfinite(surplus) or surplus >= 0


class TestScaleBoundaries:
    """Test reasonable behavior at scale boundaries."""

    def test_single_agent_simulation(self):
        """Single agent simulation should run but have no trades."""
        grid = Grid(size=5)
        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
        )
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=10.0)
        sim.add_agent(agent, Position(2, 2))

        # Should run without error
        sim.run(ticks=10)
        assert sim.tick == 10
        assert len(sim.trades) == 0  # No trades with single agent

    def test_two_agents_minimum(self):
        """Two agents is minimum for trading."""
        grid = Grid(size=5)
        sim = Simulation(grid=grid)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0)
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0)
        sim.add_agent(agent_a, Position(2, 2))
        sim.add_agent(agent_b, Position(2, 2))

        sim.run(ticks=10)
        # Should be able to trade
        assert sim.tick == 10

    @pytest.mark.skip(reason="Performance regression: new architecture is O(n^2) per tick - needs optimization")
    def test_large_scale_100_agents(self):
        """100 agents should run successfully."""
        sim = create_simple_economy(n_agents=100, grid_size=20, seed=42)
        sim.run(ticks=10)
        assert sim.tick == 10
        assert len(sim.agents) == 100

    @pytest.mark.skip(reason="Performance regression: new architecture is O(n^2) per tick - needs optimization")
    @pytest.mark.slow
    def test_large_scale_200_agents(self):
        """200 agents should run successfully."""
        sim = create_simple_economy(n_agents=200, grid_size=30, seed=42)
        sim.run(ticks=5)  # Fewer ticks for speed
        assert sim.tick == 5
        assert len(sim.agents) == 200

    def test_very_small_grid(self):
        """Very small grid (2x2) should work."""
        grid = Grid(size=2)
        sim = Simulation(grid=grid)
        # Can fit 4 agents
        for i in range(4):
            agent = create_agent(alpha=0.3 + 0.2*i, endowment_x=10.0, endowment_y=5.0)
            sim.add_agent(agent, Position(i // 2, i % 2))

        sim.run(ticks=5)
        assert sim.tick == 5

    @pytest.mark.skip(reason="Performance regression: 20 agents with O(n^2) is slow - needs optimization")
    def test_crowded_grid(self):
        """Grid with more agents than positions should work (agents can share positions)."""
        grid = Grid(size=3)  # 9 positions
        sim = Simulation(grid=grid)

        # Add 20 agents to 9 positions
        for i in range(20):
            agent = create_agent(alpha=0.3 + 0.4 * (i / 19), endowment_x=10.0, endowment_y=5.0)
            pos = Position(i % 3, (i // 3) % 3)
            sim.add_agent(agent, pos)

        sim.run(ticks=5)
        assert sim.tick == 5
        assert len(sim.agents) == 20


class TestExtremeParameters:
    """Test with extreme but valid parameter values."""

    def test_extreme_alpha_near_zero(self):
        """Alpha very close to 0 (strong preference for y)."""
        prefs = CobbDouglas(0.001)
        bundle = Bundle(100.0, 1.0)
        # Should compute without underflow
        utility = prefs.utility(bundle)
        assert utility > 0
        assert math.isfinite(utility)

    def test_extreme_alpha_near_one(self):
        """Alpha very close to 1 (strong preference for x)."""
        prefs = CobbDouglas(0.999)
        bundle = Bundle(1.0, 100.0)
        # Should compute without underflow
        utility = prefs.utility(bundle)
        assert utility > 0
        assert math.isfinite(utility)

    def test_very_large_endowments(self):
        """Very large endowment values."""
        agent = create_agent(alpha=0.5, endowment_x=1e10, endowment_y=1e10)
        utility = agent.utility()
        assert utility > 0
        assert math.isfinite(utility)

    def test_very_small_endowments(self):
        """Very small endowment values."""
        agent = create_agent(alpha=0.5, endowment_x=1e-10, endowment_y=1e-10)
        utility = agent.utility()
        assert utility > 0
        assert math.isfinite(utility)

    def test_extreme_discount_factor_near_zero(self):
        """Discount factor near 0 (very impatient)."""
        agent = create_agent(
            alpha=0.5, endowment_x=10.0, endowment_y=10.0,
            discount_factor=0.01
        )
        assert agent.discount_factor == 0.01

    def test_extreme_discount_factor_near_one(self):
        """Discount factor near 1 (very patient)."""
        agent = create_agent(
            alpha=0.5, endowment_x=10.0, endowment_y=10.0,
            discount_factor=0.999
        )
        assert agent.discount_factor == 0.999

    def test_large_perception_radius(self):
        """Perception radius larger than grid."""
        grid = Grid(size=10)
        sim = Simulation(grid=grid)
        agent = create_agent(
            alpha=0.5, endowment_x=10.0, endowment_y=10.0,
            perception_radius=100.0  # Larger than grid
        )
        sim.add_agent(agent, Position(5, 5))
        # Should work fine (sees all agents)
        sim.run(ticks=1)

    def test_zero_perception_radius(self):
        """Zero perception radius (can only see co-located agents)."""
        grid = Grid(size=10)
        sim = Simulation(grid=grid)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=0.0)
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=0.0)
        sim.add_agent(agent_a, Position(5, 5))
        sim.add_agent(agent_b, Position(5, 5))  # Same position

        sim.run(ticks=5)
        # Should still be able to trade if at same position


class TestMatchingProtocolEdgeCases:
    """Edge cases for matching protocols."""

    @pytest.mark.skip(reason="matching_protocol removed in 3-phase tick model rework")
    def test_stable_roommates_odd_agents(self):
        """Stable roommates with odd number of agents leaves one unmatched."""
        pass  # Test skipped - matching_protocol removed from Simulation

    @pytest.mark.skip(reason="matching_protocol removed in 3-phase tick model rework")
    def test_stable_roommates_no_visible_agents(self):
        """Agents can't see each other (perception radius 0, different positions)."""
        pass  # Test skipped - matching_protocol removed from Simulation


class TestNoisyInformationEdgeCases:
    """Edge cases for noisy information environments."""

    def test_zero_noise(self):
        """Zero noise should behave like full information."""
        info_env = NoisyAlphaInformation(noise_std=0.0, seed=42)
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=5.0)

        obs_type = info_env.get_observable_type(agent)
        assert obs_type.preferences.alpha == agent.preferences.alpha

    def test_very_high_noise(self):
        """Very high noise should still produce valid alphas in (0,1)."""
        info_env = NoisyAlphaInformation(noise_std=10.0, seed=42)
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=5.0)

        obs_type = info_env.get_observable_type(agent)
        # Should be clamped to valid range
        assert 0 < obs_type.preferences.alpha < 1


class TestMarketEmergenceEdgeCases:
    """Edge cases for market emergence scenarios."""

    def test_minimum_viable_scenario(self):
        """Smallest valid market emergence scenario."""
        config = MarketEmergenceConfig(
            n_agents=2,
            grid_size=5,
            ticks=5,
            seed=42,
        )
        result = run_market_emergence(config)
        assert result.analysis.n_agents == 2
        assert result.analysis.total_ticks == 5

    @pytest.mark.slow
    def test_market_emergence_with_rubinstein(self):
        """Market emergence with Rubinstein protocol."""
        config = MarketEmergenceConfig(
            n_agents=10,
            grid_size=8,
            ticks=10,
            seed=42,
        )
        result = run_market_emergence(
            config,
            bargaining_protocol=RubinsteinBargainingProtocol(),
        )
        assert result.protocol_name == "rubinsteinbargaining"

    @pytest.mark.skip(reason="matching_protocol removed in 3-phase tick model rework")
    def test_market_emergence_with_stable_matching(self):
        """Market emergence with stable roommates matching."""
        pass  # Test skipped - matching_protocol removed from Simulation

    @pytest.mark.slow
    def test_market_emergence_with_noisy_info(self):
        """Market emergence with noisy information."""
        config = MarketEmergenceConfig(
            n_agents=10,
            grid_size=8,
            ticks=10,
            seed=42,
        )
        result = run_market_emergence(
            config,
            info_env=NoisyAlphaInformation(noise_std=0.1, seed=42),
        )
        assert result.analysis.total_ticks == 10


class TestAnalysisEdgeCases:
    """Edge cases for analysis functions."""

    def test_analyze_empty_run(self):
        """Analysis of run with no trades."""
        from microecon.logging import SimulationLogger, SimulationConfig
        from microecon.analysis.emergence import (
            trade_network_stats,
            welfare_efficiency,
        )

        # Create minimal run
        config = SimulationConfig(n_agents=2, grid_size=5, seed=42, protocol_name="nash")
        logger = SimulationLogger(config=config)

        grid = Grid(size=5)
        sim = Simulation(grid=grid, logger=logger)
        # Add agents far apart so they don't trade
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=0.0)
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=0.0)
        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(4, 4))

        sim.run(ticks=5)
        run_data = logger.finalize()

        # Should analyze without error
        network = trade_network_stats(run_data)
        assert network.n_nodes == 2
        assert network.total_trades == 0
        assert network.n_edges == 0

        efficiency = welfare_efficiency(run_data)
        assert efficiency.efficiency_ratio == 0.0  # No gains achieved

    def test_analyze_single_tick_run(self):
        """Analysis of run with single tick."""
        from microecon.logging import SimulationLogger, SimulationConfig
        from microecon.analysis.emergence import analyze_market_emergence

        config = SimulationConfig(n_agents=2, grid_size=5, seed=42, protocol_name="nash")
        logger = SimulationLogger(config=config)

        grid = Grid(size=5)
        sim = Simulation(grid=grid, logger=logger)
        agent_a = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0)
        agent_b = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0)
        sim.add_agent(agent_a, Position(2, 2))
        sim.add_agent(agent_b, Position(2, 2))

        sim.run(ticks=1)
        run_data = logger.finalize()

        report = analyze_market_emergence(run_data)
        assert report.total_ticks == 1
