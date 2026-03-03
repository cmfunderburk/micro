"""Integration tests for information-regime product surface (A-007)."""

from server.simulation_manager import SimulationConfig, _create_simulation_from_config
from microecon.information import NoisyAlphaInformation, FullInformation


def test_config_with_noisy_alpha_creates_noisy_simulation():
    """Server config with info_env_name='noisy_alpha' must create NoisyAlphaInformation."""
    config = SimulationConfig(
        n_agents=4,
        grid_size=5,
        seed=42,
        bargaining_protocol="nash",
        info_env_name="noisy_alpha",
        info_env_params={"noise_std": 0.2},
    )
    sim = _create_simulation_from_config(config)
    assert isinstance(sim.info_env, NoisyAlphaInformation)
    assert sim.info_env.noise_std == 0.2


def test_config_default_creates_full_information():
    """Default config must still create FullInformation."""
    config = SimulationConfig(
        n_agents=4,
        grid_size=5,
        seed=42,
        bargaining_protocol="nash",
    )
    sim = _create_simulation_from_config(config)
    assert isinstance(sim.info_env, FullInformation)


def test_config_roundtrip_preserves_info_env():
    """SimulationConfig to_dict/from_dict must preserve info_env fields."""
    config = SimulationConfig(
        n_agents=4,
        grid_size=5,
        seed=42,
        bargaining_protocol="nash",
        info_env_name="noisy_alpha",
        info_env_params={"noise_std": 0.3},
    )
    d = config.to_dict()
    restored = SimulationConfig.from_dict(d)
    assert restored.info_env_name == "noisy_alpha"
    assert restored.info_env_params == {"noise_std": 0.3}
