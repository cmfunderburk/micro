"""Research workflow: run matching and bargaining protocol comparisons.

Produces structured JSON evidence artifacts for Gate B.
Requires no manual code edits — configure via constants below.

Usage:
    python scripts/research_workflow.py

Output:
    output/evidence/manifest.json
    output/evidence/matching_comparison.json
    output/evidence/bargaining_comparison.json

Reference: docs/plans/2026-02-28-a250-research-workflow-design.md
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from microecon.batch import BatchRunner
from microecon.bargaining import NashBargainingProtocol, RubinsteinBargainingProtocol
from microecon.matching import BilateralProposalMatching, CentralizedClearingMatching
from microecon.analysis.distributions import (
    compare_groups,
    final_welfare,
    total_trades,
    welfare_gain,
)
from microecon.analysis.emergence import welfare_efficiency

# ── Configuration ────────────────────────────────────────────────────
N_AGENTS = 10
GRID_SIZE = 15
TICKS = 100
SEEDS = [0, 1, 2]
OUTPUT_DIR = Path("output/evidence")
# ─────────────────────────────────────────────────────────────────────


def _git_commit_hash() -> str:
    """Get current git commit hash, or 'unknown' if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _run_batch(variations: dict, label: str) -> list:
    """Run a BatchRunner experiment and return results."""
    print(f"  Running {label}...", flush=True)
    runner = BatchRunner(
        base_config={"n_agents": N_AGENTS, "grid_size": GRID_SIZE},
        variations=variations,
        keep_in_memory=True,
    )
    print(f"    {runner.count_runs()} runs", flush=True)
    results = runner.run(ticks=TICKS)
    print(f"    Done.", flush=True)
    return results


def _split_by_config_field(results, field: str) -> dict[str, list]:
    """Split RunResults into groups by a SimulationConfig field."""
    groups: dict[str, list] = {}
    for r in results:
        key = getattr(r.config, field)
        groups.setdefault(key, []).append(r)
    return groups


def _compute_comparison(results, group_field: str, group_a_name: str, group_b_name: str) -> dict:
    """Compute comparison metrics between two protocol groups."""
    groups = _split_by_config_field(results, group_field)
    runs_a = [r.run_data for r in groups[group_a_name]]
    runs_b = [r.run_data for r in groups[group_b_name]]

    metrics = {}
    for metric_name, extractor in [
        ("final_welfare", final_welfare),
        ("total_trades", lambda r: float(total_trades(r))),
        ("welfare_gain", welfare_gain),
    ]:
        cr = compare_groups(runs_a, runs_b, metric_name, extractor, group_a_name, group_b_name)
        metrics[metric_name] = {
            "group_a_mean": cr.group_a_mean,
            "group_b_mean": cr.group_b_mean,
            "difference": cr.difference,
            "effect_size": cr.effect_size,
            "group_a_values": cr.group_a_values,
            "group_b_values": cr.group_b_values,
        }

    # Per-run summaries with efficiency
    per_run = []
    for r in results:
        eff = welfare_efficiency(r.run_data)
        per_run.append({
            "seed": r.config.seed,
            group_field: getattr(r.config, group_field),
            "final_welfare": r.summary["final_welfare"],
            "total_trades": r.summary["total_trades"],
            "welfare_gain": r.summary["welfare_gains"],
            "efficiency_ratio": eff.efficiency_ratio,
        })

    return {
        "config": {
            "varying": group_field,
            "group_a": group_a_name,
            "group_b": group_b_name,
            "n_agents": N_AGENTS,
            "grid_size": GRID_SIZE,
            "ticks": TICKS,
            "seeds": SEEDS,
        },
        "metrics": metrics,
        "per_run_summaries": per_run,
    }


def main():
    print("A-250 Research Workflow", flush=True)
    print(f"  {N_AGENTS} agents, {GRID_SIZE}x{GRID_SIZE} grid, {TICKS} ticks, seeds={SEEDS}", flush=True)

    # ── Matching comparison ──────────────────────────────────────────
    print("\n[1/2] Matching protocol comparison", flush=True)
    matching_results = _run_batch(
        variations={
            "matching_protocol": [
                BilateralProposalMatching(),
                CentralizedClearingMatching(),
            ],
            "seed": SEEDS,
        },
        label="bilateral vs centralized",
    )
    matching_comparison = _compute_comparison(
        matching_results,
        group_field="matching_protocol_name",
        group_a_name="bilateral_proposal",
        group_b_name="centralized_clearing",
    )

    # ── Bargaining comparison ────────────────────────────────────────
    print("\n[2/2] Bargaining protocol comparison", flush=True)
    bargaining_results = _run_batch(
        variations={
            "protocol": [
                NashBargainingProtocol(),
                RubinsteinBargainingProtocol(),
            ],
            "seed": SEEDS,
        },
        label="Nash vs Rubinstein",
    )
    bargaining_comparison = _compute_comparison(
        bargaining_results,
        group_field="protocol_name",
        group_a_name="nash",
        group_b_name="rubinstein",
    )

    # ── Write evidence ───────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit_hash(),
        "seeds": SEEDS,
        "n_agents": N_AGENTS,
        "grid_size": GRID_SIZE,
        "ticks": TICKS,
    }

    for name, data in [
        ("manifest.json", manifest),
        ("matching_comparison.json", matching_comparison),
        ("bargaining_comparison.json", bargaining_comparison),
    ]:
        path = OUTPUT_DIR / name
        path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"  Wrote {path}", flush=True)

    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()
