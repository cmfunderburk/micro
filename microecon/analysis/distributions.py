"""Distribution analysis and statistical comparisons.

Compare outcome distributions across runs and protocols.
"""

from dataclasses import dataclass
from typing import Callable
import math

from microecon.logging import RunData


@dataclass
class ComparisonResult:
    """Result of a statistical comparison between two groups."""

    metric: str
    group_a_name: str
    group_b_name: str
    group_a_values: list[float]
    group_b_values: list[float]
    group_a_mean: float
    group_b_mean: float
    group_a_std: float
    group_b_std: float
    difference: float  # group_b_mean - group_a_mean
    effect_size: float  # Cohen's d

    def summary(self) -> str:
        """Return a human-readable summary of the comparison."""
        direction = "higher" if self.difference > 0 else "lower"
        return (
            f"{self.metric}: {self.group_b_name} is {abs(self.difference):.4f} "
            f"{direction} than {self.group_a_name} "
            f"(effect size d={self.effect_size:.2f})"
        )


def _mean(values: list[float]) -> float:
    """Compute mean of a list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    """Compute standard deviation of a list."""
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _cohens_d(group_a: list[float], group_b: list[float]) -> float:
    """Compute Cohen's d effect size."""
    n1, n2 = len(group_a), len(group_b)
    if n1 < 2 or n2 < 2:
        return 0.0

    mean1, mean2 = _mean(group_a), _mean(group_b)
    var1 = sum((x - mean1) ** 2 for x in group_a) / (n1 - 1)
    var2 = sum((x - mean2) ** 2 for x in group_b) / (n2 - 1)

    # Pooled standard deviation
    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    if pooled_std == 0:
        return 0.0

    return (mean2 - mean1) / pooled_std


def final_welfare(run: RunData) -> float:
    """Extract final welfare from a run."""
    if not run.ticks:
        return 0.0
    return run.ticks[-1].total_welfare


def total_trades(run: RunData) -> int:
    """Extract total trades from a run."""
    if not run.ticks:
        return 0
    return run.ticks[-1].cumulative_trades


def welfare_gain(run: RunData) -> float:
    """Extract welfare gain (final - initial) from a run."""
    if len(run.ticks) < 2:
        return 0.0
    return run.ticks[-1].total_welfare - run.ticks[0].total_welfare


def extract_metric(
    runs: list[RunData], extractor: Callable[[RunData], float]
) -> list[float]:
    """Extract a metric from each run.

    Args:
        runs: List of RunData objects
        extractor: Function that takes a RunData and returns a metric value

    Returns:
        List of metric values
    """
    return [extractor(run) for run in runs]


def compare_groups(
    runs_a: list[RunData],
    runs_b: list[RunData],
    metric_name: str,
    extractor: Callable[[RunData], float],
    group_a_name: str = "Group A",
    group_b_name: str = "Group B",
) -> ComparisonResult:
    """Compare a metric between two groups of runs.

    Args:
        runs_a: First group of runs
        runs_b: Second group of runs
        metric_name: Name of the metric being compared
        extractor: Function to extract metric from RunData
        group_a_name: Label for first group
        group_b_name: Label for second group

    Returns:
        ComparisonResult with statistics
    """
    values_a = extract_metric(runs_a, extractor)
    values_b = extract_metric(runs_b, extractor)

    mean_a = _mean(values_a)
    mean_b = _mean(values_b)
    std_a = _std(values_a)
    std_b = _std(values_b)

    return ComparisonResult(
        metric=metric_name,
        group_a_name=group_a_name,
        group_b_name=group_b_name,
        group_a_values=values_a,
        group_b_values=values_b,
        group_a_mean=mean_a,
        group_b_mean=mean_b,
        group_a_std=std_a,
        group_b_std=std_b,
        difference=mean_b - mean_a,
        effect_size=_cohens_d(values_a, values_b),
    )


def compare_final_welfare(
    runs_a: list[RunData],
    runs_b: list[RunData],
    group_a_name: str = "Group A",
    group_b_name: str = "Group B",
) -> ComparisonResult:
    """Compare final welfare between two groups.

    Args:
        runs_a: First group of runs
        runs_b: Second group of runs
        group_a_name: Label for first group
        group_b_name: Label for second group

    Returns:
        ComparisonResult with statistics
    """
    return compare_groups(
        runs_a, runs_b, "Final Welfare", final_welfare, group_a_name, group_b_name
    )


def compare_total_trades(
    runs_a: list[RunData],
    runs_b: list[RunData],
    group_a_name: str = "Group A",
    group_b_name: str = "Group B",
) -> ComparisonResult:
    """Compare total trades between two groups.

    Args:
        runs_a: First group of runs
        runs_b: Second group of runs
        group_a_name: Label for first group
        group_b_name: Label for second group

    Returns:
        ComparisonResult with statistics
    """
    return compare_groups(
        runs_a,
        runs_b,
        "Total Trades",
        lambda r: float(total_trades(r)),
        group_a_name,
        group_b_name,
    )


def compare_welfare_gain(
    runs_a: list[RunData],
    runs_b: list[RunData],
    group_a_name: str = "Group A",
    group_b_name: str = "Group B",
) -> ComparisonResult:
    """Compare welfare gain between two groups.

    Args:
        runs_a: First group of runs
        runs_b: Second group of runs
        group_a_name: Label for first group
        group_b_name: Label for second group

    Returns:
        ComparisonResult with statistics
    """
    return compare_groups(
        runs_a, runs_b, "Welfare Gain", welfare_gain, group_a_name, group_b_name
    )


def compare_protocols(
    runs: list[RunData],
    protocol_a: str = "nash",
    protocol_b: str = "rubinstein",
) -> dict[str, ComparisonResult]:
    """Compare multiple metrics between two protocols.

    Args:
        runs: All runs (will be grouped by protocol)
        protocol_a: First protocol name
        protocol_b: Second protocol name

    Returns:
        Dict mapping metric name to ComparisonResult
    """
    from .loader import group_by_protocol

    grouped = group_by_protocol(runs)
    runs_a = grouped.get(protocol_a, [])
    runs_b = grouped.get(protocol_b, [])

    if not runs_a or not runs_b:
        return {}

    return {
        "final_welfare": compare_final_welfare(runs_a, runs_b, protocol_a, protocol_b),
        "total_trades": compare_total_trades(runs_a, runs_b, protocol_a, protocol_b),
        "welfare_gain": compare_welfare_gain(runs_a, runs_b, protocol_a, protocol_b),
    }
