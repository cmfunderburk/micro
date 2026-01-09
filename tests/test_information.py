"""
Tests for information environments.

Tests cover:
- FullInformation environment (type = private state)
- NoisyAlphaInformation environment (noisy alpha observation)
"""

import pytest
from microecon.agent import Agent, AgentPrivateState, AgentType, create_agent
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.information import FullInformation, NoisyAlphaInformation

pytestmark = pytest.mark.core


class TestFullInformation:
    """Tests for the FullInformation environment."""

    def test_get_observable_type_returns_private_state(self):
        """Observable type should match private state."""
        agent = create_agent(alpha=0.6, endowment_x=10.0, endowment_y=5.0)
        env = FullInformation()

        observed = env.get_observable_type(agent)

        assert observed.preferences.alpha == 0.6
        assert observed.endowment.x == 10.0
        assert observed.endowment.y == 5.0

    def test_can_observe_within_radius(self):
        """Should be able to observe targets within perception radius."""
        observer = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0, perception_radius=3.0)
        target = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0)
        env = FullInformation()

        assert env.can_observe(observer, target, distance=2.5)
        assert env.can_observe(observer, target, distance=3.0)

    def test_cannot_observe_beyond_radius(self):
        """Should not be able to observe targets beyond perception radius."""
        observer = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0, perception_radius=3.0)
        target = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0)
        env = FullInformation()

        assert not env.can_observe(observer, target, distance=3.1)
        assert not env.can_observe(observer, target, distance=10.0)


class TestNoisyAlphaInformation:
    """Tests for the NoisyAlphaInformation environment."""

    def test_initialization(self):
        """Environment should initialize with valid noise_std."""
        env = NoisyAlphaInformation(noise_std=0.1)
        assert env.noise_std == 0.1
        assert env.seed is None

    def test_initialization_with_seed(self):
        """Environment should accept a seed for reproducibility."""
        env = NoisyAlphaInformation(noise_std=0.1, seed=42)
        assert env.noise_std == 0.1
        assert env.seed == 42

    def test_negative_noise_std_raises(self):
        """Negative noise_std should raise ValueError."""
        with pytest.raises(ValueError, match="noise_std must be non-negative"):
            NoisyAlphaInformation(noise_std=-0.1)

    def test_zero_noise_returns_true_alpha(self):
        """With zero noise, observed alpha should equal true alpha."""
        agent = create_agent(alpha=0.6, endowment_x=10.0, endowment_y=5.0)
        env = NoisyAlphaInformation(noise_std=0.0, seed=42)

        observed = env.get_observable_type(agent)

        assert observed.preferences.alpha == 0.6

    def test_noisy_alpha_differs_from_true(self):
        """With noise, observed alpha should differ from true alpha."""
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=5.0)
        env = NoisyAlphaInformation(noise_std=0.2, seed=42)

        observed = env.get_observable_type(agent)

        # With seed=42 and noise_std=0.2, the noise should produce a different alpha
        assert observed.preferences.alpha != 0.5

    def test_endowment_is_not_noisy(self):
        """Endowment should be observed exactly (no noise)."""
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=5.0)
        env = NoisyAlphaInformation(noise_std=0.2, seed=42)

        observed = env.get_observable_type(agent)

        assert observed.endowment.x == 10.0
        assert observed.endowment.y == 5.0

    def test_alpha_clipped_to_valid_range(self):
        """Observed alpha should be clipped to (0.01, 0.99)."""
        # Agent with alpha near 0
        agent_low = create_agent(alpha=0.05, endowment_x=10.0, endowment_y=5.0)
        # Agent with alpha near 1
        agent_high = create_agent(alpha=0.95, endowment_x=10.0, endowment_y=5.0)

        # High noise to test clipping
        env = NoisyAlphaInformation(noise_std=0.5, seed=123)

        # Run multiple observations to verify clipping
        for _ in range(100):
            obs_low = env.get_observable_type(agent_low)
            obs_high = env.get_observable_type(agent_high)

            assert 0.01 <= obs_low.preferences.alpha <= 0.99
            assert 0.01 <= obs_high.preferences.alpha <= 0.99

    def test_seed_reproducibility(self):
        """Same seed should produce same noisy observations."""
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=5.0)

        env1 = NoisyAlphaInformation(noise_std=0.2, seed=42)
        env2 = NoisyAlphaInformation(noise_std=0.2, seed=42)

        obs1 = env1.get_observable_type(agent)
        obs2 = env2.get_observable_type(agent)

        assert obs1.preferences.alpha == obs2.preferences.alpha

    def test_different_seeds_produce_different_observations(self):
        """Different seeds should produce different noisy observations."""
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=5.0)

        env1 = NoisyAlphaInformation(noise_std=0.2, seed=42)
        env2 = NoisyAlphaInformation(noise_std=0.2, seed=99)

        obs1 = env1.get_observable_type(agent)
        obs2 = env2.get_observable_type(agent)

        assert obs1.preferences.alpha != obs2.preferences.alpha

    def test_multiple_observations_vary(self):
        """Multiple observations of the same agent should vary."""
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=5.0)
        env = NoisyAlphaInformation(noise_std=0.2, seed=42)

        observations = [env.get_observable_type(agent).preferences.alpha for _ in range(10)]

        # Check that not all observations are the same
        assert len(set(observations)) > 1

    def test_can_observe_within_radius(self):
        """Should be able to observe targets within perception radius."""
        observer = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0, perception_radius=3.0)
        target = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0)
        env = NoisyAlphaInformation(noise_std=0.2, seed=42)

        assert env.can_observe(observer, target, distance=2.5)
        assert env.can_observe(observer, target, distance=3.0)

    def test_cannot_observe_beyond_radius(self):
        """Should not be able to observe targets beyond perception radius."""
        observer = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0, perception_radius=3.0)
        target = create_agent(alpha=0.5, endowment_x=5.0, endowment_y=5.0)
        env = NoisyAlphaInformation(noise_std=0.2, seed=42)

        assert not env.can_observe(observer, target, distance=3.1)
        assert not env.can_observe(observer, target, distance=10.0)

    def test_get_true_type(self):
        """get_true_type should return the actual type without noise."""
        agent = create_agent(alpha=0.6, endowment_x=10.0, endowment_y=5.0)
        env = NoisyAlphaInformation(noise_std=0.2, seed=42)

        true_type = env.get_true_type(agent)

        assert true_type.preferences.alpha == 0.6
        assert true_type.endowment.x == 10.0
        assert true_type.endowment.y == 5.0

    def test_noise_distribution(self):
        """With many observations, noise should be approximately Gaussian."""
        agent = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=5.0)
        env = NoisyAlphaInformation(noise_std=0.1, seed=42)

        # Collect many observations
        observations = [env.get_observable_type(agent).preferences.alpha for _ in range(1000)]

        # Compute mean - should be close to true alpha (0.5)
        mean_obs = sum(observations) / len(observations)
        assert abs(mean_obs - 0.5) < 0.02  # Allow some sampling error

        # Compute std - should be close to noise_std (0.1)
        variance = sum((x - mean_obs) ** 2 for x in observations) / len(observations)
        std_obs = variance ** 0.5
        # Std will be less than 0.1 due to clipping at boundaries
        assert std_obs < 0.12


class TestNoisyAlphaWithSearch:
    """Tests for NoisyAlphaInformation integration with search behavior."""

    def test_search_uses_noisy_type(self):
        """Search should use noisy observations, not true types."""
        from microecon.grid import Grid, Position
        from microecon.search import evaluate_targets

        # Create grid with two agents
        grid = Grid(size=10)
        observer = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=5.0)
        target = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=5.0)

        grid.place_agent(observer, Position(0, 0))
        grid.place_agent(target, Position(2, 0))

        agents_by_id = {observer.id: observer, target.id: target}

        # With zero noise, should get consistent results
        env_no_noise = NoisyAlphaInformation(noise_std=0.0, seed=42)
        result1 = evaluate_targets(observer, grid, env_no_noise, agents_by_id)
        result2 = evaluate_targets(observer, grid, env_no_noise, agents_by_id)
        assert result1.discounted_value == result2.discounted_value

        # With high noise and different seeds, results may vary
        env_noisy1 = NoisyAlphaInformation(noise_std=0.3, seed=42)
        env_noisy2 = NoisyAlphaInformation(noise_std=0.3, seed=99)
        result_noisy1 = evaluate_targets(observer, grid, env_noisy1, agents_by_id)
        result_noisy2 = evaluate_targets(observer, grid, env_noisy2, agents_by_id)
        # Values may differ due to different noise realizations
        # (This is a statistical test - with high noise they should differ)
        # We don't assert inequality because occasionally they could be equal

    def test_noise_causes_different_target_valuations(self):
        """
        Verify that noisy information actually produces different valuations.

        This is a regression test for CE-1: before the fix, search used true types
        regardless of information environment, so noisy info had no effect.
        """
        from microecon.grid import Grid, Position
        from microecon.search import evaluate_targets

        grid = Grid(size=10)
        observer = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=5.0)
        target = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=5.0)

        grid.place_agent(observer, Position(0, 0))
        grid.place_agent(target, Position(2, 0))
        agents_by_id = {observer.id: observer, target.id: target}

        # Run with noise many times, collect valuations
        valuations = set()
        for seed in range(50):
            env = NoisyAlphaInformation(noise_std=0.2, seed=seed)
            result = evaluate_targets(observer, grid, env, agents_by_id)
            # Round to avoid floating point issues
            valuations.add(round(result.discounted_value, 6))

        # With noise affecting behavior, we should see variation in valuations
        # Without the fix, all valuations would be identical
        assert len(valuations) > 1, (
            "Expected noise to cause variation in target valuations, "
            "but all 50 runs produced identical results. "
            "This suggests information environment is not affecting search behavior."
        )

    def test_observer_knows_own_type(self):
        """
        Verify that observers use their true type (not noisy) for self.

        This is a regression test for CE-2: observers should not apply noise
        to their own alpha when evaluating potential trades.
        """
        from microecon.grid import Grid, Position
        from microecon.search import evaluate_targets
        from microecon.bargaining import compute_nash_surplus
        from microecon.agent import AgentType

        grid = Grid(size=10)
        observer = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=5.0)
        target = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=5.0)

        grid.place_agent(observer, Position(0, 0))
        grid.place_agent(target, Position(1, 0))  # Distance 1, no discounting effect
        agents_by_id = {observer.id: observer, target.id: target}

        # With zero noise, the valuation should match Nash surplus computed with true types
        env = NoisyAlphaInformation(noise_std=0.0, seed=42)
        result = evaluate_targets(observer, grid, env, agents_by_id)

        true_observer_type = AgentType.from_private_state(observer.private_state)
        true_target_type = AgentType.from_private_state(target.private_state)
        expected_surplus = compute_nash_surplus(true_observer_type, true_target_type)

        # Account for discounting (distance = 1 tick)
        expected_value = expected_surplus * (observer.discount_factor ** 1)

        assert abs(result.discounted_value - expected_value) < 1e-6, (
            f"Expected valuation {expected_value}, got {result.discounted_value}. "
            "Observer may be using noisy self-type instead of true type."
        )


class TestNoisyAlphaWithSimulation:
    """Tests for NoisyAlphaInformation integration with simulation."""

    def test_simulation_with_noisy_information(self):
        """Simulation should run correctly with noisy information environment."""
        from microecon.simulation import Simulation
        from microecon.grid import Grid, Position
        from microecon.bargaining import NashBargainingProtocol
        from microecon.matching import OpportunisticMatchingProtocol

        # Create simulation with noisy information
        env = NoisyAlphaInformation(noise_std=0.1, seed=42)

        grid = Grid(size=10)
        sim = Simulation(
            grid=grid,
            info_env=env,
            bargaining_protocol=NashBargainingProtocol(),
            matching_protocol=OpportunisticMatchingProtocol(),
        )

        # Create and place agents
        for i in range(6):
            alpha = 0.2 + 0.6 * (i / 5)  # Vary from 0.2 to 0.8
            if i < 3:
                agent = create_agent(alpha=alpha, endowment_x=10.0, endowment_y=2.0)
            else:
                agent = create_agent(alpha=alpha, endowment_x=2.0, endowment_y=10.0)
            sim.add_agent(agent, Position(i % 3, i // 3))

        # Run for a few ticks
        sim.run(ticks=10)

        # Simulation should complete without error
        assert sim.tick == 10

    def test_observed_alpha_logged_in_search_decisions(self):
        """Logged search decisions should include observed_alpha for V-1 visualization."""
        from microecon.simulation import Simulation
        from microecon.grid import Grid, Position
        from microecon.bargaining import NashBargainingProtocol
        from microecon.matching import OpportunisticMatchingProtocol
        from microecon.logging import SimulationLogger, SimulationConfig

        # Create agents with known alphas
        observer = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=10.0)
        target = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=10.0)

        # With full info, observed_alpha should equal true alpha
        config = SimulationConfig(n_agents=2, grid_size=10, seed=42, protocol_name="nash")
        logger = SimulationLogger(config=config)
        grid = Grid(size=10)
        sim = Simulation(
            grid=grid,
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
            matching_protocol=OpportunisticMatchingProtocol(),
            logger=logger,
        )
        sim.add_agent(observer, Position(0, 0))
        sim.add_agent(target, Position(2, 0))
        sim.run(ticks=1)
        run_data = logger.finalize()

        # Find search decision from observer
        search_decisions = run_data.ticks[0].search_decisions
        observer_decision = next(d for d in search_decisions if d.agent_id == observer.id)
        target_eval = next(e for e in observer_decision.evaluations if e.target_id == target.id)

        # With full info, observed_alpha should match true alpha
        assert target_eval.observed_alpha == 0.7

        # Now test with noisy info
        noisy_env = NoisyAlphaInformation(noise_std=0.2, seed=99)
        config2 = SimulationConfig(n_agents=2, grid_size=10, seed=42, protocol_name="nash")
        logger2 = SimulationLogger(config=config2)
        grid2 = Grid(size=10)
        observer2 = create_agent(alpha=0.3, endowment_x=10.0, endowment_y=2.0, perception_radius=10.0)
        target2 = create_agent(alpha=0.7, endowment_x=2.0, endowment_y=10.0, perception_radius=10.0)
        sim2 = Simulation(
            grid=grid2,
            info_env=noisy_env,
            bargaining_protocol=NashBargainingProtocol(),
            matching_protocol=OpportunisticMatchingProtocol(),
            logger=logger2,
        )
        sim2.add_agent(observer2, Position(0, 0))
        sim2.add_agent(target2, Position(2, 0))
        sim2.run(ticks=1)
        run_data2 = logger2.finalize()

        search_decisions2 = run_data2.ticks[0].search_decisions
        observer_decision2 = next(d for d in search_decisions2 if d.agent_id == observer2.id)
        target_eval2 = next(e for e in observer_decision2.evaluations if e.target_id == target2.id)

        # With noisy info, observed_alpha should differ from true alpha
        assert target_eval2.observed_alpha != 0.7
        # But should still be valid (clipped to 0.01-0.99)
        assert 0.01 <= target_eval2.observed_alpha <= 0.99
