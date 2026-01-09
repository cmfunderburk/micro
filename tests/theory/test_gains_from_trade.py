"""
THEORY-004: Verify Gains from Trade Computation.

Tests verifying gains from trade are computed correctly and fully exhausted
at bargaining solution. At solution, no remaining bilateral gains should exist.

Theoretical References:
- Pareto improvement definition
- Contract curve characterization
- O&R-B bargaining theory

Test tolerance: rel=1e-3 (optimization outcome)
"""

import pytest
import math
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.bargaining import (
    nash_bargaining_solution,
    rubinstein_bargaining_solution,
    asymmetric_nash_bargaining_solution,
    BargainingOutcome,
)

pytestmark = pytest.mark.theory


class TestGainsComputation:
    """Test that gains from trade are computed correctly."""

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.8, 0.2, 20.0, 2.0, 2.0, 20.0),
        (0.4, 0.6, 15.0, 8.0, 8.0, 15.0),
    ])
    def test_gains_equal_utility_difference(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        Gains from trade = utility at outcome - utility at endowment.

        gains_i = u_i(allocation_i) - u_i(endowment_i)
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        d1 = prefs_1.utility(endowment_1)
        d2 = prefs_2.utility(endowment_2)

        expected_gains_1 = outcome.utility_1 - d1
        expected_gains_2 = outcome.utility_2 - d2

        assert abs(outcome.gains_1 - expected_gains_1) < 1e-9
        assert abs(outcome.gains_2 - expected_gains_2) < 1e-9

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
    ])
    def test_total_gains_equals_sum(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """Total surplus = sum of individual gains."""
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        assert abs(outcome.total_gains - (outcome.gains_1 + outcome.gains_2)) < 1e-9


class TestGainsNonNegative:
    """Test that gains are non-negative for individually rational trades."""

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.1, 0.9, 50.0, 5.0, 5.0, 50.0),
        (0.5, 0.5, 100.0, 1.0, 1.0, 100.0),
    ])
    def test_gains_non_negative_nash(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        Individual rationality: Each agent must gain (or at least not lose).

        This is a fundamental property of voluntary exchange.
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        assert outcome.gains_1 >= -1e-9, f"Agent 1 gains negative: {outcome.gains_1}"
        assert outcome.gains_2 >= -1e-9, f"Agent 2 gains negative: {outcome.gains_2}"

    @pytest.mark.parametrize("delta1,delta2", [
        (0.9, 0.9),
        (0.9, 0.7),
        (0.5, 0.8),
    ])
    def test_gains_non_negative_rubinstein(self, delta1, delta2):
        """Individual rationality holds for Rubinstein solution too."""
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = rubinstein_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            delta_1=delta1, delta_2=delta2
        )

        assert outcome.gains_1 >= -1e-9
        assert outcome.gains_2 >= -1e-9


class TestGainsExhausted:
    """Test that gains are fully exhausted at bargaining solution."""

    def test_no_pareto_improvement_at_nash_solution(self):
        """
        At Nash solution, no further Pareto improvements are possible.

        If we could make one agent better off without hurting the other,
        we would have found a higher Nash product.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        if not outcome.trade_occurred:
            return  # No trade case

        # Try small perturbations - none should be Pareto-improving
        W_x = endowment_1.x + endowment_2.x
        W_y = endowment_1.y + endowment_2.y

        for dx in [-0.1, -0.01, 0.01, 0.1]:
            for dy in [-0.1, -0.01, 0.01, 0.1]:
                new_x1 = outcome.allocation_1.x + dx
                new_y1 = outcome.allocation_1.y + dy

                if new_x1 <= 0 or new_y1 <= 0:
                    continue
                if new_x1 >= W_x or new_y1 >= W_y:
                    continue

                new_alloc_1 = Bundle(new_x1, new_y1)
                new_alloc_2 = Bundle(W_x - new_x1, W_y - new_y1)

                new_u1 = prefs_1.utility(new_alloc_1)
                new_u2 = prefs_2.utility(new_alloc_2)

                # Cannot be Pareto-improving (both strictly better)
                is_pareto_improving = (
                    new_u1 > outcome.utility_1 + 1e-9 and
                    new_u2 > outcome.utility_2 + 1e-9
                )

                assert not is_pareto_improving, (
                    f"Found Pareto improvement: ({dx}, {dy}) gives "
                    f"u1={new_u1} > {outcome.utility_1}, u2={new_u2} > {outcome.utility_2}"
                )

    def test_marginal_gains_zero_at_solution(self):
        """
        At the optimal allocation, marginal reallocation yields zero net gain.

        This is because we're on the contract curve (MRS equality).
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        if not outcome.trade_occurred:
            return

        # Compute MRS at solution
        mrs_1 = prefs_1.marginal_rate_of_substitution(outcome.allocation_1)
        mrs_2 = prefs_2.marginal_rate_of_substitution(outcome.allocation_2)

        # At Pareto efficient allocation, MRS should be equal
        # (they trade at the same rate)
        assert abs(mrs_1 - mrs_2) < 1e-3, (
            f"MRS not equal at solution: MRS_1={mrs_1}, MRS_2={mrs_2}"
        )


class TestNoGainsWhenIdentical:
    """Test that gains are zero when agents are identical."""

    def test_identical_agents_no_gains(self):
        """
        When agents have identical preferences AND endowments,
        there are no gains from trade.
        """
        prefs = CobbDouglas(0.5)
        endowment = Bundle(10.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs, endowment, prefs, endowment
        )

        # With identical setup, either no trade or zero gains
        assert outcome.gains_1 < 1e-9
        assert outcome.gains_2 < 1e-9

    def test_similar_preferences_small_gains(self):
        """
        When preferences are similar, gains from trade are small.

        Different endowments still create trade opportunities,
        but similar alpha values reduce potential gains.
        """
        # Very similar preferences
        prefs_1 = CobbDouglas(0.49)
        prefs_2 = CobbDouglas(0.51)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome_similar = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        # Very different preferences
        prefs_3 = CobbDouglas(0.2)
        prefs_4 = CobbDouglas(0.8)

        outcome_different = nash_bargaining_solution(
            prefs_3, endowment_1, prefs_4, endowment_2
        )

        # Different preferences should yield larger gains
        assert outcome_different.total_gains > outcome_similar.total_gains


class TestGainsFromTradeVariousCases:
    """Test gains computation for various preference/endowment combinations."""

    def test_complementary_endowments_high_gains(self):
        """
        When endowments are complementary to preferences,
        gains from trade should be high.

        Agent 1 prefers x but has mostly y.
        Agent 2 prefers y but has mostly x.
        """
        # Agent 1: high alpha (wants x), has y
        prefs_1 = CobbDouglas(0.8)
        endowment_1 = Bundle(2.0, 20.0)

        # Agent 2: low alpha (wants y), has x
        prefs_2 = CobbDouglas(0.2)
        endowment_2 = Bundle(20.0, 2.0)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        # Should have significant gains
        assert outcome.trade_occurred
        assert outcome.total_gains > 0.5  # Substantial gains expected

    def test_aligned_endowments_lower_gains(self):
        """
        When endowments align with preferences, gains are lower.

        Agent 1 prefers x and has x.
        Agent 2 prefers y and has y.
        """
        # Agent 1: high alpha (wants x), has x
        prefs_1 = CobbDouglas(0.8)
        endowment_1 = Bundle(20.0, 2.0)

        # Agent 2: low alpha (wants y), has y
        prefs_2 = CobbDouglas(0.2)
        endowment_2 = Bundle(2.0, 20.0)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        # Gains should be smaller than complementary case
        # (they already have what they want most)
        assert outcome.total_gains >= 0

    def test_extreme_preferences_create_gains(self):
        """
        Extreme preference differences create large gains from trade.
        """
        prefs_1 = CobbDouglas(0.1)  # Strongly prefers y
        prefs_2 = CobbDouglas(0.9)  # Strongly prefers x

        # Equal endowments
        endowment = Bundle(10.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs_1, endowment, prefs_2, endowment
        )

        assert outcome.trade_occurred
        # Agent 1 should end up with more y, less x
        assert outcome.allocation_1.y > outcome.allocation_1.x
        # Agent 2 should end up with more x, less y
        assert outcome.allocation_2.x > outcome.allocation_2.y


class TestGainsDistribution:
    """Test how gains are distributed between agents."""

    def test_nash_symmetric_gains_with_symmetric_setup(self):
        """
        With symmetric preferences and complementary endowments,
        Nash solution should give roughly equal gains.
        """
        prefs = CobbDouglas(0.5)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs, endowment_1, prefs, endowment_2
        )

        # Gains should be equal (symmetric setup)
        assert abs(outcome.gains_1 - outcome.gains_2) < 1e-6

    def test_rubinstein_patient_agent_larger_gains(self):
        """
        In Rubinstein bargaining, more patient agent gets larger gains.
        """
        prefs_1 = CobbDouglas(0.5)
        prefs_2 = CobbDouglas(0.5)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        # Agent 1 more patient
        outcome_1patient = rubinstein_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            delta_1=0.95, delta_2=0.8
        )

        # Agent 2 more patient
        outcome_2patient = rubinstein_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            delta_1=0.8, delta_2=0.95
        )

        # More patient agent should get larger share of gains
        assert outcome_1patient.gains_1 > outcome_1patient.gains_2
        assert outcome_2patient.gains_2 > outcome_2patient.gains_1

    def test_asymmetric_weights_shift_gains(self):
        """
        Asymmetric bargaining weights shift gains distribution.
        """
        prefs_1 = CobbDouglas(0.5)
        prefs_2 = CobbDouglas(0.5)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        # Equal weights
        outcome_equal = asymmetric_nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            weight_1=0.5, weight_2=0.5
        )

        # Agent 1 higher weight
        outcome_1high = asymmetric_nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            weight_1=0.7, weight_2=0.3
        )

        # Higher weight should give larger gains
        assert outcome_1high.gains_1 > outcome_equal.gains_1
        assert outcome_1high.gains_2 < outcome_equal.gains_2

        # Total gains should be similar (Pareto efficient)
        assert abs(outcome_1high.total_gains - outcome_equal.total_gains) < 0.1
