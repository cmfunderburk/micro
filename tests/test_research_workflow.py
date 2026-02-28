"""Integration test for research workflow script (A-250)."""

import json
import tempfile
from pathlib import Path

import pytest

import scripts.research_workflow as rw

# Save original values
_ORIG_N_AGENTS = rw.N_AGENTS
_ORIG_GRID_SIZE = rw.GRID_SIZE
_ORIG_TICKS = rw.TICKS
_ORIG_SEEDS = rw.SEEDS
_ORIG_OUTPUT_DIR = rw.OUTPUT_DIR


@pytest.fixture(autouse=True)
def _fast_config(tmp_path):
    """Override workflow constants for fast test execution."""
    rw.N_AGENTS = 4
    rw.GRID_SIZE = 5
    rw.TICKS = 5
    rw.SEEDS = [0]
    rw.OUTPUT_DIR = tmp_path
    yield tmp_path
    # Restore originals
    rw.N_AGENTS = _ORIG_N_AGENTS
    rw.GRID_SIZE = _ORIG_GRID_SIZE
    rw.TICKS = _ORIG_TICKS
    rw.SEEDS = _ORIG_SEEDS
    rw.OUTPUT_DIR = _ORIG_OUTPUT_DIR


pytestmark = pytest.mark.simulation


class TestResearchWorkflow:
    """Test the research workflow produces valid evidence artifacts."""

    def test_workflow_produces_evidence(self, _fast_config):
        """Run workflow with minimal params, verify output structure."""
        output_dir = _fast_config
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

    def test_evidence_metrics_have_expected_fields(self, _fast_config):
        """Each metric in comparison has required statistical fields."""
        output_dir = _fast_config
        rw.SEEDS = [0, 1]  # Need 2+ seeds for meaningful stats
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

    def test_per_run_summary_has_efficiency(self, _fast_config):
        """Each per-run summary includes efficiency_ratio."""
        output_dir = _fast_config
        rw.main()

        matching = json.loads((output_dir / "matching_comparison.json").read_text())
        for summary in matching["per_run_summaries"]:
            assert "efficiency_ratio" in summary
            assert isinstance(summary["efficiency_ratio"], float)
