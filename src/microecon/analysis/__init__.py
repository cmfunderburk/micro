"""Analysis module for simulation data.

Provides tools for:
- Loading logged runs
- Time series analysis
- Distribution comparison
- Agent-level tracking
"""

from .loader import (
    load_run,
    load_batch,
    group_by_protocol,
    group_by_seed,
    pair_runs_by_seed,
)
from .timeseries import (
    welfare_over_time,
    trades_over_time,
    trades_per_tick,
    agent_utility_over_time,
    agent_position_over_time,
    agent_endowment_over_time,
    welfare_gains_over_time,
    average_utility_over_time,
    utility_variance_over_time,
    compare_welfare_trajectories,
    metric_over_time,
)
from .distributions import (
    ComparisonResult,
    compare_groups,
    compare_final_welfare,
    compare_total_trades,
    compare_welfare_gain,
    compare_protocols,
    extract_metric,
    final_welfare,
    total_trades,
    welfare_gain,
)
from .tracking import (
    AgentOutcome,
    SearchEfficiencyStats,
    agent_outcomes,
    gains_by_alpha,
    compare_agent_outcomes,
    winners_and_losers,
    search_efficiency,
    trade_partners,
    unique_trade_partners,
)

__all__ = [
    # Loader
    "load_run",
    "load_batch",
    "group_by_protocol",
    "group_by_seed",
    "pair_runs_by_seed",
    # Time series
    "welfare_over_time",
    "trades_over_time",
    "trades_per_tick",
    "agent_utility_over_time",
    "agent_position_over_time",
    "agent_endowment_over_time",
    "welfare_gains_over_time",
    "average_utility_over_time",
    "utility_variance_over_time",
    "compare_welfare_trajectories",
    "metric_over_time",
    # Distributions
    "ComparisonResult",
    "compare_groups",
    "compare_final_welfare",
    "compare_total_trades",
    "compare_welfare_gain",
    "compare_protocols",
    "extract_metric",
    "final_welfare",
    "total_trades",
    "welfare_gain",
    # Tracking
    "AgentOutcome",
    "SearchEfficiencyStats",
    "agent_outcomes",
    "gains_by_alpha",
    "compare_agent_outcomes",
    "winners_and_losers",
    "search_efficiency",
    "trade_partners",
    "unique_trade_partners",
]
