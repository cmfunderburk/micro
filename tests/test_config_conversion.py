"""Tests for server -> logging SimulationConfig conversion."""

import pytest

from server.simulation_manager import SimulationConfig as ServerConfig
from microecon.logging import SimulationConfig as LoggingConfig


class TestServerToLoggingConfigConversion:
    """Test explicit config conversion between server and logging domains."""

    def test_basic_conversion(self):
        server_config = ServerConfig(
            n_agents=10, grid_size=15, perception_radius=7.0,
            discount_factor=0.95, seed=42, bargaining_protocol="nash",
        )
        logging_config = server_config.to_logging_config()

        assert isinstance(logging_config, LoggingConfig)
        assert logging_config.n_agents == 10
        assert logging_config.grid_size == 15
        assert logging_config.seed == 42
        assert logging_config.protocol_name == "nash"
        assert logging_config.perception_radius == 7.0
        assert logging_config.discount_factor == 0.95

    def test_protocol_name_mapping(self):
        """Server uses 'bargaining_protocol', logging uses 'protocol_name'."""
        for protocol in ["nash", "rubinstein", "tioli", "asymmetric_nash"]:
            server_config = ServerConfig(seed=42, bargaining_protocol=protocol)
            logging_config = server_config.to_logging_config()
            assert logging_config.protocol_name == protocol

    def test_info_env_mapping(self):
        server_config = ServerConfig(
            seed=42, info_env_name="noisy_alpha",
            info_env_params={"noise_std": 0.2},
        )
        logging_config = server_config.to_logging_config()
        assert logging_config.info_env_name == "noisy_alpha"
        assert logging_config.info_env_params == {"noise_std": 0.2}

    def test_schema_version_is_current(self):
        from microecon.logging.events import SCHEMA_VERSION
        server_config = ServerConfig(seed=42)
        logging_config = server_config.to_logging_config()
        assert logging_config.schema_version == SCHEMA_VERSION

    def test_seed_none_raises(self):
        """Logging config requires a seed; conversion should raise if missing."""
        server_config = ServerConfig(seed=None)
        with pytest.raises(ValueError, match="seed"):
            server_config.to_logging_config()
