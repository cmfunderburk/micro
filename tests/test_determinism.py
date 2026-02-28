"""Determinism gate tests (A-105).

Proves that seeded simulations produce identical outputs across reruns.
See docs/contracts/determinism-policy.md for tolerance rules.

Tolerance policy:
- Integer fields (tick, position, trade count): exact match
- Floating-point fields (welfare, utility, surplus): abs(a - b) < 1e-10
- Sequence ordering: exact (deterministic tie-breaking is contract)
"""

import pytest

from microecon.simulation import create_simple_economy
from microecon.logging import SimulationLogger, SimulationConfig, TickRecord

pytestmark = pytest.mark.determinism

FLOAT_TOL = 1e-10


def _run_simulation(seed: int, protocol: str = "nash", n_agents: int = 6,
                     grid_size: int = 8, n_ticks: int = 20,
                     use_beliefs: bool = False,
                     info_env: str = "full",
                     info_env_params: dict | None = None) -> list[TickRecord]:
    """Run a simulation and collect tick records."""
    from microecon.information import FullInformation, NoisyAlphaInformation
    from microecon.bargaining import (
        NashBargainingProtocol, RubinsteinBargainingProtocol,
        TIOLIBargainingProtocol, AsymmetricNashBargainingProtocol,
    )

    protocols = {
        "nash": NashBargainingProtocol,
        "rubinstein": RubinsteinBargainingProtocol,
        "tioli": TIOLIBargainingProtocol,
        "asymmetric_nash": AsymmetricNashBargainingProtocol,
    }
    bargaining = protocols[protocol]()

    if info_env == "noisy_alpha":
        ie = NoisyAlphaInformation(
            noise_std=(info_env_params or {}).get("noise_std", 0.1),
            seed=seed,
        )
    else:
        ie = FullInformation()

    config = SimulationConfig(
        n_agents=n_agents, grid_size=grid_size, seed=seed,
        protocol_name=protocol,
    )
    logger = SimulationLogger(config)

    sim = create_simple_economy(
        n_agents=n_agents, grid_size=grid_size, seed=seed,
        bargaining_protocol=bargaining, use_beliefs=use_beliefs,
        info_env=ie,
    )
    sim.logger = logger
    sim.run(n_ticks)
    logger.finalize()

    return logger.ticks


def _assert_ticks_equal(ticks_a: list[TickRecord], ticks_b: list[TickRecord]) -> None:
    """Assert two tick sequences are identical within tolerance."""
    assert len(ticks_a) == len(ticks_b), \
        f"Tick count mismatch: {len(ticks_a)} vs {len(ticks_b)}"

    for i, (ta, tb) in enumerate(zip(ticks_a, ticks_b)):
        # Tick number
        assert ta.tick == tb.tick, f"Tick {i}: tick number mismatch"

        # Welfare
        assert abs(ta.total_welfare - tb.total_welfare) < FLOAT_TOL, \
            f"Tick {i}: welfare mismatch {ta.total_welfare} vs {tb.total_welfare}"

        # Cumulative trades
        assert ta.cumulative_trades == tb.cumulative_trades, \
            f"Tick {i}: cumulative trades mismatch"

        # Agent snapshots
        assert len(ta.agent_snapshots) == len(tb.agent_snapshots), \
            f"Tick {i}: agent count mismatch"
        for sa, sb in zip(ta.agent_snapshots, tb.agent_snapshots):
            assert sa.agent_id == sb.agent_id, \
                f"Tick {i}: agent ID mismatch"
            assert sa.position == sb.position, \
                f"Tick {i}, agent {sa.agent_id}: position mismatch"
            for ea, eb in zip(sa.endowment, sb.endowment):
                assert abs(ea - eb) < FLOAT_TOL, \
                    f"Tick {i}, agent {sa.agent_id}: endowment mismatch"
            assert abs(sa.alpha - sb.alpha) < FLOAT_TOL, \
                f"Tick {i}, agent {sa.agent_id}: alpha mismatch"
            assert abs(sa.utility - sb.utility) < FLOAT_TOL, \
                f"Tick {i}, agent {sa.agent_id}: utility mismatch"
            assert sa.has_beliefs == sb.has_beliefs, \
                f"Tick {i}, agent {sa.agent_id}: has_beliefs mismatch"
            assert sa.n_trades_in_memory == sb.n_trades_in_memory, \
                f"Tick {i}, agent {sa.agent_id}: n_trades_in_memory mismatch"
            assert sa.n_type_beliefs == sb.n_type_beliefs, \
                f"Tick {i}, agent {sa.agent_id}: n_type_beliefs mismatch"

        # Trades
        assert len(ta.trades) == len(tb.trades), \
            f"Tick {i}: trade count mismatch"
        for tra, trb in zip(ta.trades, tb.trades):
            assert tra.agent1_id == trb.agent1_id
            assert tra.agent2_id == trb.agent2_id
            assert tra.proposer_id == trb.proposer_id
            assert tra.trade_occurred == trb.trade_occurred
            for ga, gb in zip(tra.gains, trb.gains):
                assert abs(ga - gb) < FLOAT_TOL

        # Movements
        assert len(ta.movements) == len(tb.movements), \
            f"Tick {i}: movement count mismatch"
        for ma, mb in zip(ta.movements, tb.movements):
            assert ma.agent_id == mb.agent_id
            assert ma.from_pos == mb.from_pos
            assert ma.to_pos == mb.to_pos

        # Search decisions
        assert len(ta.search_decisions) == len(tb.search_decisions), \
            f"Tick {i}: search decision count mismatch"
        for sda, sdb in zip(ta.search_decisions, tb.search_decisions):
            assert sda.agent_id == sdb.agent_id
            assert sda.position == sdb.position
            assert sda.visible_agents == sdb.visible_agents
            assert sda.chosen_target_id == sdb.chosen_target_id
            if sda.chosen_value is not None and sdb.chosen_value is not None:
                assert abs(sda.chosen_value - sdb.chosen_value) < FLOAT_TOL
            else:
                assert sda.chosen_value == sdb.chosen_value
            assert len(sda.evaluations) == len(sdb.evaluations)
            for eva, evb in zip(sda.evaluations, sdb.evaluations):
                assert eva.target_id == evb.target_id
                assert abs(eva.expected_surplus - evb.expected_surplus) < FLOAT_TOL
                assert abs(eva.discounted_value - evb.discounted_value) < FLOAT_TOL

        # Commitments
        assert len(ta.commitments_formed) == len(tb.commitments_formed), \
            f"Tick {i}: commitments_formed count mismatch"
        for ca, cb in zip(ta.commitments_formed, tb.commitments_formed):
            assert ca.agent_a == cb.agent_a
            assert ca.agent_b == cb.agent_b

        assert len(ta.commitments_broken) == len(tb.commitments_broken), \
            f"Tick {i}: commitments_broken count mismatch"
        for ca, cb in zip(ta.commitments_broken, tb.commitments_broken):
            assert ca.agent_a == cb.agent_a
            assert ca.agent_b == cb.agent_b
            assert ca.reason == cb.reason

        # Belief snapshots
        assert len(ta.belief_snapshots) == len(tb.belief_snapshots), \
            f"Tick {i}: belief_snapshots count mismatch"
        for bsa, bsb in zip(ta.belief_snapshots, tb.belief_snapshots):
            assert bsa.agent_id == bsb.agent_id
            assert len(bsa.type_beliefs) == len(bsb.type_beliefs)
            for tba, tbb in zip(bsa.type_beliefs, bsb.type_beliefs):
                assert tba.target_agent_id == tbb.target_agent_id
                assert abs(tba.believed_alpha - tbb.believed_alpha) < FLOAT_TOL
                assert abs(tba.confidence - tbb.confidence) < FLOAT_TOL
                assert tba.n_interactions == tbb.n_interactions
            if bsa.price_belief is not None and bsb.price_belief is not None:
                assert abs(bsa.price_belief.mean - bsb.price_belief.mean) < FLOAT_TOL
                assert abs(bsa.price_belief.variance - bsb.price_belief.variance) < FLOAT_TOL
                assert bsa.price_belief.n_observations == bsb.price_belief.n_observations
            else:
                assert bsa.price_belief == bsb.price_belief


class TestDeterminismGate:
    """Seeded reruns must produce identical outputs."""

    @pytest.mark.parametrize("protocol", [
        "nash", "rubinstein", "tioli", "asymmetric_nash",
    ])
    def test_protocol_determinism(self, protocol):
        """Same seed + same protocol -> identical ticks."""
        ticks_a = _run_simulation(seed=42, protocol=protocol)
        ticks_b = _run_simulation(seed=42, protocol=protocol)
        _assert_ticks_equal(ticks_a, ticks_b)

    def test_different_seeds_differ(self):
        """Different seeds should produce different outputs."""
        ticks_a = _run_simulation(seed=42)
        ticks_b = _run_simulation(seed=99)
        # At least one tick should differ in welfare or trades
        any_diff = False
        for ta, tb in zip(ticks_a, ticks_b):
            if abs(ta.total_welfare - tb.total_welfare) > FLOAT_TOL:
                any_diff = True
                break
            if ta.cumulative_trades != tb.cumulative_trades:
                any_diff = True
                break
        assert any_diff, "Different seeds produced identical results"

    def test_noisy_info_determinism(self):
        """NoisyAlphaInformation with same seed -> identical ticks."""
        ticks_a = _run_simulation(
            seed=42, info_env="noisy_alpha",
            info_env_params={"noise_std": 0.1},
        )
        ticks_b = _run_simulation(
            seed=42, info_env="noisy_alpha",
            info_env_params={"noise_std": 0.1},
        )
        _assert_ticks_equal(ticks_a, ticks_b)

    def test_beliefs_determinism(self):
        """Simulations with beliefs enabled are deterministic."""
        ticks_a = _run_simulation(seed=42, use_beliefs=True, n_ticks=30)
        ticks_b = _run_simulation(seed=42, use_beliefs=True, n_ticks=30)
        _assert_ticks_equal(ticks_a, ticks_b)

    def test_larger_simulation_determinism(self):
        """Larger grid with more agents remains deterministic."""
        ticks_a = _run_simulation(seed=42, n_agents=12, grid_size=15, n_ticks=30)
        ticks_b = _run_simulation(seed=42, n_agents=12, grid_size=15, n_ticks=30)
        _assert_ticks_equal(ticks_a, ticks_b)
