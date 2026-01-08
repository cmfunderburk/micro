"""
Scenario loading and management for the microecon platform.

Scenarios are YAML files that define reproducible simulation configurations
for demonstration, comparison, and research purposes.

The market_emergence module provides programmatic scenarios for large-scale
(50-100 agent) demonstrations of market emergence from bilateral exchange.
"""

from .schema import ScenarioMeta, AgentConfig, ScenarioConfig, Scenario
from .loader import load_scenario, load_all_scenarios, ScenarioLoadError
from .market_emergence import (
    MarketEmergenceConfig,
    MarketEmergenceResult,
    run_market_emergence,
    compare_protocols,
    run_demonstration,
    print_emergence_summary,
)

__all__ = [
    # YAML scenarios
    "ScenarioMeta",
    "AgentConfig",
    "ScenarioConfig",
    "Scenario",
    "load_scenario",
    "load_all_scenarios",
    "ScenarioLoadError",
    # Market emergence demonstration
    "MarketEmergenceConfig",
    "MarketEmergenceResult",
    "run_market_emergence",
    "compare_protocols",
    "run_demonstration",
    "print_emergence_summary",
]
