"""
THEORY-002: Verify Rubinstein SPE and BRW Weights.

Tests verifying RubinsteinBargainingProtocol computes correct SPE allocation
per BRW (1986). Verify bargaining weights match formula:
    w1 = ln(d2)/(ln(d1)+ln(d2))

Theoretical References:
- Rubinstein (1982) SPE uniqueness
- BRW (1986) asymmetric Nash convergence
- O&R-B Ch 3-4

Test tolerance: rel=1e-6 (formula verification)
"""

import pytest
import math
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.bargaining import (
    compute_brw_weights,
    rubinstein_share,
    rubinstein_bargaining_solution,
    nash_bargaining_solution,
    asymmetric_nash_bargaining_solution,
)


class TestBRWWeightFormula:
    """Test BRW weight formula: w1 = ln(d2)/(ln(d1)+ln(d2))."""

    @pytest.mark.parametrize("delta1,delta2", [
        (0.9, 0.9),   # Equal patience
        (0.9, 0.8),   # Agent 1 more patient
        (0.8, 0.9),   # Agent 2 more patient
        (0.5, 0.5),   # Equal, low patience
        (0.99, 0.99), # Equal, high patience
        (0.95, 0.85), # Moderate asymmetry
        (0.7, 0.3),   # Large asymmetry
    ])
    def test_brw_weight_formula_direct(self, delta1, delta2):
        """
        Verify BRW formula: w1 = ln(delta2) / (ln(delta1) + ln(delta2))

        Note: ln(delta) < 0 for delta in (0,1), so both numerator and
        denominator are negative, giving positive weights.
        """
        w1, w2 = compute_brw_weights(delta1, delta2)

        # Direct formula computation
        ln_d1 = math.log(delta1)
        ln_d2 = math.log(delta2)
        expected_w1 = ln_d2 / (ln_d1 + ln_d2)
        expected_w2 = ln_d1 / (ln_d1 + ln_d2)

        assert abs(w1 - expected_w1) < 1e-10, (
            f"w1={w1} != expected {expected_w1}"
        )
        assert abs(w2 - expected_w2) < 1e-10, (
            f"w2={w2} != expected {expected_w2}"
        )

    @pytest.mark.parametrize("delta1,delta2", [
        (0.9, 0.9),
        (0.9, 0.8),
        (0.5, 0.5),
        (0.99, 0.01),
    ])
    def test_weights_sum_to_one(self, delta1, delta2):
        """BRW weights must sum to 1."""
        w1, w2 = compute_brw_weights(delta1, delta2)
        assert abs(w1 + w2 - 1.0) < 1e-10

    @pytest.mark.parametrize("delta1,delta2", [
        (0.9, 0.8),
        (0.95, 0.85),
        (0.7, 0.5),
        (0.99, 0.9),
    ])
    def test_more_patient_gets_larger_weight(self, delta1, delta2):
        """
        The MORE patient player (higher delta) gets GREATER bargaining power.

        This is the key insight of BRW: patience = power.
        """
        w1, w2 = compute_brw_weights(delta1, delta2)

        if delta1 > delta2:
            assert w1 > w2, f"More patient agent 1 should get more: w1={w1}, w2={w2}"
        elif delta2 > delta1:
            assert w2 > w1, f"More patient agent 2 should get more: w1={w1}, w2={w2}"
        else:
            assert abs(w1 - w2) < 1e-10, f"Equal patience should give equal weights"

    def test_equal_patience_gives_equal_weights(self):
        """Equal discount factors should give equal bargaining weights."""
        for delta in [0.5, 0.7, 0.9, 0.99]:
            w1, w2 = compute_brw_weights(delta, delta)
            assert abs(w1 - 0.5) < 1e-10
            assert abs(w2 - 0.5) < 1e-10


class TestRubinsteinShareFormula:
    """Test Rubinstein SPE share formula for surplus division."""

    @pytest.mark.parametrize("delta1,delta2,proposer", [
        (0.9, 0.9, 1),
        (0.9, 0.9, 2),
        (0.9, 0.8, 1),
        (0.9, 0.8, 2),
        (0.5, 0.5, 1),
    ])
    def test_rubinstein_share_formula(self, delta1, delta2, proposer):
        """
        Verify Rubinstein share formula matches theory.

        If player 1 proposes first:
            share_1 = (1 - delta2) / (1 - delta1*delta2)
            share_2 = delta2*(1 - delta1) / (1 - delta1*delta2)

        If player 2 proposes first:
            share_1 = delta1*(1 - delta2) / (1 - delta1*delta2)
            share_2 = (1 - delta1) / (1 - delta1*delta2)
        """
        s1, s2 = rubinstein_share(delta1, delta2, proposer)

        denom = 1 - delta1 * delta2

        if proposer == 1:
            expected_s1 = (1 - delta2) / denom
            expected_s2 = delta2 * (1 - delta1) / denom
        else:
            expected_s1 = delta1 * (1 - delta2) / denom
            expected_s2 = (1 - delta1) / denom

        assert abs(s1 - expected_s1) < 1e-10
        assert abs(s2 - expected_s2) < 1e-10

    @pytest.mark.parametrize("delta1,delta2,proposer", [
        (0.9, 0.9, 1),
        (0.8, 0.8, 2),
        (0.7, 0.5, 1),
    ])
    def test_shares_sum_to_one(self, delta1, delta2, proposer):
        """Rubinstein shares must sum to 1."""
        s1, s2 = rubinstein_share(delta1, delta2, proposer)
        assert abs(s1 + s2 - 1.0) < 1e-10

    def test_proposer_advantage(self):
        """
        First mover gets larger share (proposer advantage).

        With equal discount factors, proposer gets 1/(1+delta),
        responder gets delta/(1+delta).
        """
        delta = 0.9
        s1_prop1, s2_prop1 = rubinstein_share(delta, delta, proposer=1)
        s1_prop2, s2_prop2 = rubinstein_share(delta, delta, proposer=2)

        # When 1 proposes, 1 should get more
        assert s1_prop1 > s2_prop1
        # When 2 proposes, 2 should get more
        assert s2_prop2 > s1_prop2

        # Verify exact formula for equal delta
        expected_proposer = 1 / (1 + delta)
        expected_responder = delta / (1 + delta)

        assert abs(s1_prop1 - expected_proposer) < 1e-10
        assert abs(s2_prop1 - expected_responder) < 1e-10

    def test_patience_is_power(self):
        """More patient player gets larger share regardless of proposer."""
        delta1, delta2 = 0.9, 0.7  # Agent 1 more patient

        # Even when agent 2 proposes, agent 1's patience helps
        s1_prop2, s2_prop2 = rubinstein_share(delta1, delta2, proposer=2)

        # The more patient player's share increases with their patience
        delta1_higher, delta2_same = 0.95, 0.7
        s1_higher, s2_higher = rubinstein_share(delta1_higher, delta2_same, proposer=2)

        # Higher patience for agent 1 should increase agent 1's share
        assert s1_higher > s1_prop2


class TestRubinsteinConvergesToNash:
    """Test that Rubinstein converges to symmetric Nash as delta -> 1."""

    def test_convergence_to_symmetric_nash(self):
        """
        As both discount factors approach 1, Rubinstein outcome
        should converge to symmetric Nash bargaining solution.

        This is the BRW (1986) result: the strategic foundation
        for the axiomatic Nash solution.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        # Nash solution (symmetric)
        nash_outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        # Rubinstein with very high (near 1) discount factors
        # should approximate Nash
        for delta in [0.9, 0.95, 0.99, 0.999]:
            rub_outcome = rubinstein_bargaining_solution(
                prefs_1, endowment_1, prefs_2, endowment_2,
                delta_1=delta, delta_2=delta
            )

            # Difference should decrease as delta increases
            diff_u1 = abs(rub_outcome.utility_1 - nash_outcome.utility_1)
            diff_u2 = abs(rub_outcome.utility_2 - nash_outcome.utility_2)

            # With equal deltas -> equal weights -> symmetric Nash
            if delta >= 0.99:
                assert diff_u1 < 0.01, f"delta={delta}: u1 diff={diff_u1}"
                assert diff_u2 < 0.01, f"delta={delta}: u2 diff={diff_u2}"

    def test_rubinstein_uses_brw_weights(self):
        """
        Verify Rubinstein solution equals asymmetric Nash with BRW weights.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        delta_1, delta_2 = 0.9, 0.8

        # Rubinstein outcome
        rub_outcome = rubinstein_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            delta_1=delta_1, delta_2=delta_2
        )

        # Asymmetric Nash with BRW weights
        w1, w2 = compute_brw_weights(delta_1, delta_2)
        asym_nash_outcome = asymmetric_nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            weight_1=w1, weight_2=w2
        )

        # Should be identical
        assert abs(rub_outcome.utility_1 - asym_nash_outcome.utility_1) < 1e-6
        assert abs(rub_outcome.utility_2 - asym_nash_outcome.utility_2) < 1e-6
        assert abs(rub_outcome.allocation_1.x - asym_nash_outcome.allocation_1.x) < 1e-6
        assert abs(rub_outcome.allocation_1.y - asym_nash_outcome.allocation_1.y) < 1e-6


class TestRubinsteinFirstMoverAdvantage:
    """Test first-mover advantage magnitude matches theory."""

    def test_equal_delta_proposer_advantage_magnitude(self):
        """
        With equal discount factors delta, the proposer gets share 1/(1+delta).

        This is the classic Rubinstein result for surplus division.
        """
        for delta in [0.5, 0.7, 0.9, 0.95]:
            s1, s2 = rubinstein_share(delta, delta, proposer=1)

            expected_proposer = 1 / (1 + delta)
            expected_responder = delta / (1 + delta)

            assert abs(s1 - expected_proposer) < 1e-10, (
                f"delta={delta}: proposer share {s1} != {expected_proposer}"
            )
            assert abs(s2 - expected_responder) < 1e-10, (
                f"delta={delta}: responder share {s2} != {expected_responder}"
            )

    def test_advantage_decreases_with_patience(self):
        """
        As delta increases (more patient), first-mover advantage decreases.

        At delta=0, proposer gets everything.
        At delta->1, shares converge to 50-50.
        """
        advantages = []
        for delta in [0.3, 0.5, 0.7, 0.9, 0.95, 0.99]:
            s1, s2 = rubinstein_share(delta, delta, proposer=1)
            advantage = s1 - s2  # Proposer advantage
            advantages.append(advantage)

        # Advantage should be strictly decreasing
        for i in range(len(advantages) - 1):
            assert advantages[i] > advantages[i + 1], (
                f"Advantage should decrease: {advantages}"
            )

        # At high delta, advantage should be small
        assert advantages[-1] < 0.02  # Less than 2% at delta=0.99


class TestRubinsteinValidation:
    """Test input validation for Rubinstein functions."""

    def test_brw_weights_invalid_delta(self):
        """BRW weights should reject invalid discount factors."""
        with pytest.raises(ValueError):
            compute_brw_weights(0.0, 0.9)  # delta1 = 0

        with pytest.raises(ValueError):
            compute_brw_weights(0.9, 1.0)  # delta2 = 1

        with pytest.raises(ValueError):
            compute_brw_weights(-0.1, 0.9)  # negative

        with pytest.raises(ValueError):
            compute_brw_weights(1.5, 0.9)  # > 1

    def test_rubinstein_share_invalid_delta(self):
        """Rubinstein share should reject invalid discount factors."""
        with pytest.raises(ValueError):
            rubinstein_share(0.0, 0.9)

        with pytest.raises(ValueError):
            rubinstein_share(0.9, 1.0)

    def test_rubinstein_share_invalid_proposer(self):
        """Rubinstein share should reject invalid proposer."""
        with pytest.raises(ValueError):
            rubinstein_share(0.9, 0.9, proposer=0)

        with pytest.raises(ValueError):
            rubinstein_share(0.9, 0.9, proposer=3)
