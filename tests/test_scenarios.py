"""Tests for scenario loading and schema."""

import pytest
from pathlib import Path

from microecon.scenarios import (
    Scenario,
    ScenarioMeta,
    ScenarioConfig,
    AgentConfig,
    load_scenario,
    load_all_scenarios,
    ScenarioLoadError,
)


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_valid_agent_config(self):
        """Valid agent config should be created."""
        config = AgentConfig(
            id="A",
            position=(0, 0),
            alpha=0.3,
            endowment=(5.0, 5.0),
        )
        assert config.id == "A"
        assert config.alpha == 0.3

    def test_alpha_must_be_in_zero_one(self):
        """Alpha must be strictly between 0 and 1."""
        with pytest.raises(ValueError, match="alpha must be in"):
            AgentConfig(id="A", position=(0, 0), alpha=0.0, endowment=(1.0, 1.0))

        with pytest.raises(ValueError, match="alpha must be in"):
            AgentConfig(id="A", position=(0, 0), alpha=1.0, endowment=(1.0, 1.0))

    def test_endowment_must_be_non_negative(self):
        """Endowment must be non-negative."""
        with pytest.raises(ValueError, match="endowment must be non-negative"):
            AgentConfig(id="A", position=(0, 0), alpha=0.5, endowment=(-1.0, 1.0))


class TestScenarioConfig:
    """Tests for ScenarioConfig dataclass."""

    def test_valid_scenario_config(self):
        """Valid scenario config should be created."""
        agents = (
            AgentConfig(id="A", position=(0, 0), alpha=0.3, endowment=(5.0, 5.0)),
            AgentConfig(id="B", position=(5, 0), alpha=0.7, endowment=(5.0, 5.0)),
        )
        config = ScenarioConfig(grid_size=10, agents=agents)
        assert config.grid_size == 10
        assert len(config.agents) == 2

    def test_grid_size_must_be_at_least_2(self):
        """Grid size must be at least 2."""
        agents = (
            AgentConfig(id="A", position=(0, 0), alpha=0.3, endowment=(5.0, 5.0)),
            AgentConfig(id="B", position=(0, 0), alpha=0.7, endowment=(5.0, 5.0)),
        )
        with pytest.raises(ValueError, match="grid_size must be >= 2"):
            ScenarioConfig(grid_size=1, agents=agents)

    def test_must_have_at_least_2_agents(self):
        """Must have at least 2 agents."""
        agents = (
            AgentConfig(id="A", position=(0, 0), alpha=0.3, endowment=(5.0, 5.0)),
        )
        with pytest.raises(ValueError, match="at least 2 agents"):
            ScenarioConfig(grid_size=10, agents=agents)


class TestScenarioLoader:
    """Tests for scenario loading."""

    def test_load_trading_chain_scenario(self):
        """Should load the trading chain scenario."""
        path = Path("scenarios/trading_chain.yaml")
        if not path.exists():
            pytest.skip("Scenario file not found")

        scenario = load_scenario(path)
        assert scenario.title == "Trading Chain (4 Agents)"
        assert scenario.complexity == 2
        assert len(scenario.config.agents) == 4

    def test_load_all_scenarios(self):
        """Should load all scenarios from directory."""
        scenarios = load_all_scenarios(Path("scenarios"))

        # Should have at least the 3 we created
        assert len(scenarios) >= 3

        # Should be sorted by complexity then title
        for i in range(len(scenarios) - 1):
            assert (scenarios[i].complexity, scenarios[i].title) <= \
                   (scenarios[i+1].complexity, scenarios[i+1].title)

    def test_load_nonexistent_file(self):
        """Should raise error for nonexistent file."""
        with pytest.raises(ScenarioLoadError, match="not found"):
            load_scenario(Path("scenarios/nonexistent.yaml"))

    def test_scenarios_have_required_fields(self):
        """All loaded scenarios should have required fields."""
        scenarios = load_all_scenarios(Path("scenarios"))

        for scenario in scenarios:
            assert scenario.title
            assert scenario.complexity >= 1
            assert scenario.config.grid_size >= 2
            assert len(scenario.config.agents) >= 2


class TestMarketEmergenceScenario:
    """Tests for programmatic market emergence scenarios."""

    def test_market_emergence_config(self):
        """Config should validate parameters."""
        from microecon.scenarios import MarketEmergenceConfig

        config = MarketEmergenceConfig(n_agents=50, grid_size=20)
        assert config.n_agents == 50
        assert config.grid_size == 20

    def test_market_emergence_config_validation(self):
        """Config should reject invalid parameters."""
        from microecon.scenarios import MarketEmergenceConfig

        with pytest.raises(ValueError):
            MarketEmergenceConfig(n_agents=1)  # Too few agents

        with pytest.raises(ValueError):
            MarketEmergenceConfig(n_agents=10, grid_size=3)  # Grid too small

    def test_run_small_market_emergence(self):
        """Should run a small scenario successfully."""
        from microecon.scenarios import MarketEmergenceConfig, run_market_emergence

        config = MarketEmergenceConfig(
            n_agents=10,
            grid_size=8,
            ticks=20,
            seed=42,
        )
        result = run_market_emergence(config)

        assert result.analysis.n_agents == 10
        assert result.analysis.total_ticks == 20
        assert result.protocol_name == "nashbargaining"
        assert result.matching_name == "opportunisticmatching"
