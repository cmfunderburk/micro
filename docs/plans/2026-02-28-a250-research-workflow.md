# A-250: Scripted Research Workflow — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a Python script that runs matching and bargaining protocol comparisons and writes JSON evidence artifacts for Gate B.

**Architecture:** Extend BatchRunner to support `matching_protocol` variations, then write a flat sequential script (`scripts/research_workflow.py`) that configures two experiments, runs 12 simulations via BatchRunner, computes comparison metrics, and writes structured JSON evidence to `output/evidence/`.

**Tech Stack:** Python, existing BatchRunner, analysis.distributions, analysis.emergence modules.

**Design doc:** `docs/plans/2026-02-28-a250-research-workflow-design.md`

---

### Task 1: Extend BatchRunner to support matching_protocol

**Files:**
- Modify: `microecon/batch.py:1-30` (imports), `microecon/batch.py:118-165` (_create_simulation, _config_to_simulation_config)
- Test: `tests/test_batch.py`

**Step 1: Write the failing test**

Add to `tests/test_batch.py`:

```python
from microecon.matching import BilateralProposalMatching, CentralizedClearingMatching

class TestBatchRunnerMatchingProtocol:
    """Test BatchRunner matching_protocol support."""

    def test_matching_protocol_passed_to_simulation(self):
        """matching_protocol in config is used by the simulation."""
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
            variations={"matching_protocol": [
                BilateralProposalMatching(),
                CentralizedClearingMatching(),
            ]},
            keep_in_memory=True,
        )
        results = runner.run(ticks=5)
        assert len(results) == 2
        assert results[0].config.matching_protocol_name == "bilateral_proposal"
        assert results[1].config.matching_protocol_name == "centralized_clearing"

    def test_matching_protocol_in_run_name(self):
        """Run name includes matching protocol name."""
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
            variations={"matching_protocol": [
                CentralizedClearingMatching(),
            ]},
            keep_in_memory=True,
            output_dir=None,
        )
        run_name = runner._generate_run_name(
            {"seed": 42, "matching_protocol": CentralizedClearingMatching(),
             "protocol": NashBargainingProtocol()},
            0,
        )
        assert "centralized_clearing" in run_name
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_batch.py::TestBatchRunnerMatchingProtocol -v`
Expected: FAIL — matching_protocol not extracted in _create_simulation, matching_protocol_name defaults to "bilateral_proposal" for both runs.

**Step 3: Write minimal implementation**

In `microecon/batch.py`, add import at top (after existing imports):

```python
from microecon.matching import (
    MatchingProtocol,
    BilateralProposalMatching,
    CentralizedClearingMatching,
)
```

Add helper function after `_get_info_env_params()` (after line 73):

```python
def _get_matching_protocol_name(protocol: MatchingProtocol) -> str:
    """Get a string name for a matching protocol."""
    if isinstance(protocol, BilateralProposalMatching):
        return "bilateral_proposal"
    elif isinstance(protocol, CentralizedClearingMatching):
        return "centralized_clearing"
    else:
        return protocol.__class__.__name__.lower()
```

Modify `_create_simulation()` to extract and pass matching_protocol. Replace lines 118-145:

```python
    def _create_simulation(
        self, config: dict[str, Any], logger: SimulationLogger | None
    ) -> Simulation:
        """Create a simulation from config dict."""
        # Extract parameters with defaults
        n_agents = config.get("n_agents", 10)
        grid_size = config.get("grid_size", 10)
        perception_radius = config.get("perception_radius", 7.0)
        discount_factor = config.get("discount_factor", 0.95)
        seed = config.get("seed")
        bargaining_protocol = config.get("protocol", NashBargainingProtocol())
        info_env = config.get("info_env")
        matching_protocol = config.get("matching_protocol")

        # Create simulation using factory function but inject logger
        sim = create_simple_economy(
            n_agents=n_agents,
            grid_size=grid_size,
            perception_radius=perception_radius,
            discount_factor=discount_factor,
            seed=seed,
            bargaining_protocol=bargaining_protocol,
            info_env=info_env,
            matching_protocol=matching_protocol,
        )

        # Inject logger
        sim.logger = logger

        return sim
```

Modify `_config_to_simulation_config()` to set matching_protocol_name. Replace lines 147-165:

```python
    def _config_to_simulation_config(
        self, config: dict[str, Any]
    ) -> SimulationConfig:
        """Convert config dict to SimulationConfig dataclass."""
        protocol = config.get("protocol", NashBargainingProtocol())
        info_env = config.get("info_env", FullInformation())
        matching = config.get("matching_protocol", BilateralProposalMatching())
        return SimulationConfig(
            n_agents=config.get("n_agents", 10),
            grid_size=config.get("grid_size", 10),
            seed=config["seed"],  # Required - validated in run()
            protocol_name=_get_protocol_name(protocol),
            protocol_params=_get_protocol_params(protocol),
            perception_radius=config.get("perception_radius", 7.0),
            discount_factor=config.get("discount_factor", 0.95),
            movement_budget=config.get("movement_budget", 1),
            matching_protocol_name=_get_matching_protocol_name(matching),
            info_env_name=_get_info_env_name(info_env),
            info_env_params=_get_info_env_params(info_env),
        )
```

Modify `_generate_run_name()` to include matching protocol. Replace lines 167-176:

```python
    def _generate_run_name(self, config: dict[str, Any], index: int) -> str:
        """Generate a unique name for a run directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        seed = config.get("seed", index)

        # Include bargaining protocol
        bargaining = config.get("protocol", NashBargainingProtocol())
        bargaining_name = _get_protocol_name(bargaining)

        # Include matching protocol
        matching = config.get("matching_protocol", BilateralProposalMatching())
        matching_name = _get_matching_protocol_name(matching)

        return f"run_{timestamp}_seed{seed}_{bargaining_name}_{matching_name}_{index:04d}"
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_batch.py -v`
Expected: ALL PASS (new tests + existing tests)

**Step 5: Commit**

```bash
git add microecon/batch.py tests/test_batch.py
git commit -m "feat(batch): add matching_protocol support to BatchRunner (A-250)"
```

---

### Task 2: Write the research workflow script

**Files:**
- Create: `scripts/research_workflow.py`

**Step 1: Write the script**

```python
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
import sys
from dataclasses import asdict
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
```

**Step 2: Verify the script runs**

Run: `python scripts/research_workflow.py`
Expected: Prints progress, writes 3 JSON files to `output/evidence/`. Takes ~12 minutes.

**Step 3: Verify evidence artifacts**

Run: `python -c "import json; d=json.load(open('output/evidence/manifest.json')); print(d['seeds']); print(d['git_commit'][:8])"`
Expected: `[0, 1, 2]` and 8-char git hash.

Run: `python -c "import json; d=json.load(open('output/evidence/matching_comparison.json')); print(list(d['metrics'].keys())); print(d['config']['varying'])"`
Expected: `['final_welfare', 'total_trades', 'welfare_gain']` and `matching_protocol_name`.

**Step 4: Add output/evidence/ to .gitignore if not already present**

Check `.gitignore` for `output/` — if missing, add it. Evidence artifacts are generated, not committed.

**Step 5: Commit**

```bash
git add scripts/research_workflow.py
git commit -m "feat(scripts): add research workflow for protocol comparisons (A-250)"
```

---

### Task 3: Write integration test for the workflow

**Files:**
- Test: `tests/test_research_workflow.py`

**Step 1: Write the test**

A lightweight integration test that runs the workflow with minimal params (2 agents, 5 ticks, 1 seed) and verifies evidence structure.

```python
"""Integration test for research workflow script (A-250)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.simulation
class TestResearchWorkflow:
    """Test the research workflow produces valid evidence artifacts."""

    def test_workflow_produces_evidence(self):
        """Run workflow with minimal params, verify output structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Patch constants for fast execution
            with patch("scripts.research_workflow.N_AGENTS", 4), \
                 patch("scripts.research_workflow.GRID_SIZE", 5), \
                 patch("scripts.research_workflow.TICKS", 5), \
                 patch("scripts.research_workflow.SEEDS", [0]), \
                 patch("scripts.research_workflow.OUTPUT_DIR", output_dir):

                # Import after patching isn't reliable for module-level constants.
                # Instead, just call main() with the patches active.
                import scripts.research_workflow as rw
                rw.N_AGENTS = 4
                rw.GRID_SIZE = 5
                rw.TICKS = 5
                rw.SEEDS = [0]
                rw.OUTPUT_DIR = output_dir
                rw.main()

            # Verify manifest
            manifest = json.loads((output_dir / "manifest.json").read_text())
            assert manifest["seeds"] == [0]
            assert manifest["n_agents"] == 4
            assert "git_commit" in manifest
            assert "timestamp" in manifest

            # Verify matching comparison
            matching = json.loads((output_dir / "matching_comparison.json").read_text())
            assert matching["config"]["varying"] == "matching_protocol_name"
            assert "final_welfare" in matching["metrics"]
            assert "total_trades" in matching["metrics"]
            assert "welfare_gain" in matching["metrics"]
            assert len(matching["per_run_summaries"]) == 2  # 2 protocols x 1 seed

            # Verify bargaining comparison
            bargaining = json.loads((output_dir / "bargaining_comparison.json").read_text())
            assert bargaining["config"]["varying"] == "protocol_name"
            assert len(bargaining["per_run_summaries"]) == 2

    def test_evidence_metrics_have_expected_fields(self):
        """Each metric in comparison has required statistical fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            import scripts.research_workflow as rw
            rw.N_AGENTS = 4
            rw.GRID_SIZE = 5
            rw.TICKS = 5
            rw.SEEDS = [0, 1]
            rw.OUTPUT_DIR = output_dir
            rw.main()

            matching = json.loads((output_dir / "matching_comparison.json").read_text())
            for metric_name, metric_data in matching["metrics"].items():
                assert "group_a_mean" in metric_data, f"{metric_name} missing group_a_mean"
                assert "group_b_mean" in metric_data, f"{metric_name} missing group_b_mean"
                assert "difference" in metric_data, f"{metric_name} missing difference"
                assert "effect_size" in metric_data, f"{metric_name} missing effect_size"
                assert "group_a_values" in metric_data, f"{metric_name} missing group_a_values"
                assert "group_b_values" in metric_data, f"{metric_name} missing group_b_values"
                assert len(metric_data["group_a_values"]) == 2  # 2 seeds
                assert len(metric_data["group_b_values"]) == 2

    def test_per_run_summary_has_efficiency(self):
        """Each per-run summary includes efficiency_ratio from emergence analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            import scripts.research_workflow as rw
            rw.N_AGENTS = 4
            rw.GRID_SIZE = 5
            rw.TICKS = 5
            rw.SEEDS = [0]
            rw.OUTPUT_DIR = output_dir
            rw.main()

            matching = json.loads((output_dir / "matching_comparison.json").read_text())
            for summary in matching["per_run_summaries"]:
                assert "efficiency_ratio" in summary
                assert 0.0 <= summary["efficiency_ratio"] <= 1.0 or summary["efficiency_ratio"] == 1.0
```

Note: The test imports `scripts.research_workflow` as a module. For this to work, either `scripts/` needs an `__init__.py` or the test uses `importlib`. The simpler approach is to directly mutate module-level constants after import.

**Step 2: Ensure scripts/ is importable**

Create `scripts/__init__.py` (empty) if it doesn't exist.

**Step 3: Run tests to verify they pass**

Run: `pytest tests/test_research_workflow.py -v`
Expected: ALL PASS (3 tests, each fast with minimal params)

**Step 4: Commit**

```bash
git add tests/test_research_workflow.py scripts/__init__.py
git commit -m "test(scripts): add integration tests for research workflow (A-250)"
```

---

### Task 4: Verify full workflow and update execution board

**Step 1: Run the full workflow**

Run: `python scripts/research_workflow.py`
Expected: Completes in ~12 minutes, writes 3 files to `output/evidence/`.

**Step 2: Validate evidence**

Run: `python -c "import json, pathlib; [print(f'{f.name}: {len(json.loads(f.read_text()))} keys') for f in sorted(pathlib.Path('output/evidence').glob('*.json'))]"`
Expected: Shows 3 JSON files with reasonable key counts.

**Step 3: Run full test suite**

Run: `pytest --tb=short -q`
Expected: All tests pass, no regressions.

**Step 4: Commit evidence .gitignore update if needed**

Check if `output/` is in `.gitignore`. If not:

```bash
echo "output/" >> .gitignore
git add .gitignore
git commit -m "chore: add output/ to .gitignore"
```

**Step 5: Final commit**

```bash
git add docs/VISION/VISION-WORKFLOW-EXECUTION-BOARD.md  # if marking A-250 done
git commit -m "feat(a250): complete research workflow proof (A-250)"
```
