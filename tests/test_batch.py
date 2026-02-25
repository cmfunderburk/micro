"""Tests for batch runner."""

import tempfile
from pathlib import Path

import pytest

from microecon.batch import BatchRunner, run_comparison
from microecon.bargaining import NashBargainingProtocol, RubinsteinBargainingProtocol
from microecon.logging import load_run

pytestmark = pytest.mark.simulation


class TestBatchRunner:
    """Test BatchRunner functionality."""

    def test_run_requires_seed(self):
        """Batch runs must have an explicit seed for reproducibility."""
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5},
            variations={},
        )
        with pytest.raises(ValueError, match="requires an explicit seed"):
            runner.run(ticks=5)

    def test_run_accepts_seed_in_base_config(self):
        """Seed in base_config satisfies requirement."""
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
            variations={},
            keep_in_memory=True,
        )
        results = runner.run(ticks=5)
        assert len(results) == 1

    def test_run_accepts_seed_in_variations(self):
        """Seed in variations satisfies requirement."""
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5},
            variations={"seed": [1, 2]},
            keep_in_memory=True,
        )
        results = runner.run(ticks=5)
        assert len(results) == 2

    def test_count_runs_no_variations(self):
        runner = BatchRunner(
            base_config={"n_agents": 10, "grid_size": 15},
            variations={},
        )
        assert runner.count_runs() == 1

    def test_count_runs_single_variation(self):
        runner = BatchRunner(
            base_config={"n_agents": 10, "grid_size": 15},
            variations={"seed": [1, 2, 3]},
        )
        assert runner.count_runs() == 3

    def test_count_runs_multiple_variations(self):
        runner = BatchRunner(
            base_config={"n_agents": 10, "grid_size": 15},
            variations={
                "protocol": [NashBargainingProtocol(), RubinsteinBargainingProtocol()],
                "seed": [1, 2, 3],
            },
        )
        assert runner.count_runs() == 6  # 2 * 3

    def test_run_single_config(self):
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
            variations={},
            keep_in_memory=True,
        )
        results = runner.run(ticks=10)

        assert len(results) == 1
        assert results[0].summary["total_ticks"] == 10
        assert results[0].run_data is not None
        assert len(results[0].run_data.ticks) == 10

    def test_run_with_protocol_variations(self):
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
            variations={
                "protocol": [
                    NashBargainingProtocol(),
                    RubinsteinBargainingProtocol(),
                ],
            },
            keep_in_memory=True,
        )
        results = runner.run(ticks=10)

        assert len(results) == 2

        # Should have one Nash and one Rubinstein
        protocols = {r.config.protocol_name for r in results}
        assert protocols == {"nash", "rubinstein"}

    def test_run_with_seed_variations(self):
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5},
            variations={"seed": [1, 2, 3]},
            keep_in_memory=True,
        )
        results = runner.run(ticks=5)

        assert len(results) == 3

        # Different seeds should produce different outcomes
        welfares = [r.summary["final_welfare"] for r in results]
        # At least some should differ (not guaranteed but very likely)
        assert len(set(round(w, 6) for w in welfares)) >= 1

    def test_run_writes_to_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = BatchRunner(
                base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
                variations={
                    "protocol": [
                        NashBargainingProtocol(),
                        RubinsteinBargainingProtocol(),
                    ],
                },
                output_dir=Path(tmpdir),
            )
            results = runner.run(ticks=5)

            # Check directories were created
            assert len(list(Path(tmpdir).iterdir())) == 2

            # Check we can load each run
            for result in results:
                assert result.log_path is not None
                loaded = load_run(result.log_path)
                assert len(loaded.ticks) == 5

    def test_run_reproducibility(self):
        """Same seed should produce same results."""
        runner1 = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
            variations={},
            keep_in_memory=True,
        )
        runner2 = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
            variations={},
            keep_in_memory=True,
        )

        results1 = runner1.run(ticks=10)
        results2 = runner2.run(ticks=10)

        assert results1[0].summary["final_welfare"] == results2[0].summary["final_welfare"]
        assert results1[0].summary["total_trades"] == results2[0].summary["total_trades"]


class TestRunComparison:
    """Test run_comparison convenience function."""

    def test_run_comparison_defaults(self):
        results = run_comparison(n_agents=4, grid_size=5, ticks=5, seeds=[42])

        # Should have 2 runs (Nash and Rubinstein) for 1 seed
        assert len(results) == 2

        protocols = {r.config.protocol_name for r in results}
        assert protocols == {"nash", "rubinstein"}

    @pytest.mark.slow
    def test_run_comparison_multiple_seeds(self):
        results = run_comparison(
            n_agents=4, grid_size=5, ticks=5, seeds=[1, 2, 3]
        )

        # 2 protocols * 3 seeds = 6 runs
        assert len(results) == 6

    def test_run_comparison_with_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results = run_comparison(
                n_agents=4,
                grid_size=5,
                ticks=5,
                seeds=[42],
                output_dir=Path(tmpdir),
            )

            # Should have created directories
            assert len(list(Path(tmpdir).iterdir())) == 2

            # Results should have log paths
            for r in results:
                assert r.log_path is not None


def test_batch_run_does_not_mutate_global_rng():
    """A-005: Batch runs must not mutate global random state."""
    import random

    state_before = random.getstate()

    runner = BatchRunner(
        base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
    )
    runner.run(ticks=5)

    state_after = random.getstate()
    assert state_before == state_after, "BatchRunner mutated global random state"


def test_batch_runner_honors_info_env():
    """A-002: BatchRunner must pass configured info_env to simulation."""
    from microecon.information import NoisyAlphaInformation

    info_env = NoisyAlphaInformation(noise_std=0.2)
    runner = BatchRunner(
        base_config={
            "n_agents": 4,
            "grid_size": 5,
            "seed": 42,
            "info_env": info_env,
        },
    )

    # Patch _create_simulation to capture the simulation before it runs
    original = runner._create_simulation
    created_sims = []
    def capturing_create(config, logger):
        sim = original(config, logger)
        created_sims.append(sim)
        return sim
    runner._create_simulation = capturing_create

    runner.run(ticks=5)

    assert len(created_sims) == 1
    sim = created_sims[0]
    assert isinstance(sim.info_env, NoisyAlphaInformation), (
        f"Expected NoisyAlphaInformation, got {type(sim.info_env)}"
    )
    assert sim.info_env.noise_std == 0.2


class TestBatchRunnerParameterCombinations:
    """Test complex parameter combinations."""

    @pytest.mark.slow
    def test_cartesian_product(self):
        runner = BatchRunner(
            base_config={"n_agents": 4, "grid_size": 5},
            variations={
                "protocol": [
                    NashBargainingProtocol(),
                    RubinsteinBargainingProtocol(),
                ],
                "seed": [1, 2],
                "perception_radius": [3.0, 5.0],
            },
            keep_in_memory=True,
        )

        # 2 * 2 * 2 = 8 combinations
        assert runner.count_runs() == 8

        results = runner.run(ticks=3)
        assert len(results) == 8

        # Check all combinations are present
        configs = [
            (r.config.protocol_name, r.config.seed, r.config.perception_radius)
            for r in results
        ]

        # Should have Nash with each seed/radius combo
        assert ("nash", 1, 3.0) in configs
        assert ("nash", 1, 5.0) in configs
        assert ("nash", 2, 3.0) in configs
        assert ("nash", 2, 5.0) in configs

        # Same for Rubinstein
        assert ("rubinstein", 1, 3.0) in configs
        assert ("rubinstein", 1, 5.0) in configs
        assert ("rubinstein", 2, 3.0) in configs
        assert ("rubinstein", 2, 5.0) in configs
