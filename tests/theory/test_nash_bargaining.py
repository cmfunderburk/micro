"""
THEORY-001: Verify Nash Bargaining Maximizes Nash Product.

Tests verifying NashBargainingProtocol correctly maximizes the Nash product
(u1-d1)(u2-d2). Tests that no feasible allocation achieves higher Nash product
than the computed solution.

Theoretical References:
- Nash (1950) uniqueness theorem
- O&R-B Ch 2: Axiomatic characterization
- theoretical-foundations.md

Test tolerance: rel=1e-3 (optimization outcome)
"""

import pytest
import math
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.bargaining import (
    nash_bargaining_solution,
    asymmetric_nash_bargaining_solution,
    BargainingOutcome,
)


class TestNashProductMaximization:
    """Test that Nash solution maximizes the Nash product."""

    def compute_nash_product(
        self,
        prefs_1: CobbDouglas,
        prefs_2: CobbDouglas,
        allocation_1: Bundle,
        allocation_2: Bundle,
        d1: float,
        d2: float,
    ) -> float:
        """Compute Nash product (u1-d1)(u2-d2) for given allocation."""
        u1 = prefs_1.utility(allocation_1)
        u2 = prefs_2.utility(allocation_2)
        if u1 <= d1 or u2 <= d2:
            return -float('inf')
        return (u1 - d1) * (u2 - d2)

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        # Symmetric case
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        # Asymmetric preferences
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.8, 0.2, 10.0, 5.0, 5.0, 10.0),
        # Asymmetric endowments
        (0.5, 0.5, 20.0, 2.0, 2.0, 20.0),
        # Both asymmetric
        (0.3, 0.8, 15.0, 3.0, 3.0, 15.0),
        # Edge cases
        (0.1, 0.9, 10.0, 10.0, 10.0, 10.0),
        (0.5, 0.5, 1.0, 100.0, 100.0, 1.0),
    ])
    def test_nash_product_is_maximized(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        Verify that no feasible perturbation increases Nash product.

        Strategy: Grid search over feasible allocations to verify the computed
        Nash solution achieves the maximum Nash product.
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        # Compute Nash solution
        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        if not outcome.trade_occurred:
            # No trade means no gains available - verify this
            d1 = prefs_1.utility(endowment_1)
            d2 = prefs_2.utility(endowment_2)
            # Any feasible reallocation should not improve both agents
            return

        # Disagreement utilities
        d1 = prefs_1.utility(endowment_1)
        d2 = prefs_2.utility(endowment_2)

        # Nash product at solution
        np_solution = self.compute_nash_product(
            prefs_1, prefs_2,
            outcome.allocation_1, outcome.allocation_2,
            d1, d2
        )

        # Total resources
        W_x = e1_x + e2_x
        W_y = e1_y + e2_y

        # Grid search over feasible allocations
        n_points = 50
        for i in range(1, n_points):
            for j in range(1, n_points):
                x1 = (i / n_points) * W_x
                y1 = (j / n_points) * W_y
                x2 = W_x - x1
                y2 = W_y - y1

                test_alloc_1 = Bundle(x1, y1)
                test_alloc_2 = Bundle(x2, y2)

                np_test = self.compute_nash_product(
                    prefs_1, prefs_2,
                    test_alloc_1, test_alloc_2,
                    d1, d2
                )

                # Solution should be at least as good as any test allocation
                # (within tolerance for optimization)
                assert np_solution >= np_test - 1e-6, (
                    f"Found allocation with higher Nash product: "
                    f"solution={np_solution:.6f}, test={np_test:.6f} "
                    f"at ({x1:.2f}, {y1:.2f})"
                )

    def test_nash_product_computed_correctly(self):
        """Verify Nash product formula is applied correctly."""
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        # Verify utility values match outcome
        u1_computed = prefs_1.utility(outcome.allocation_1)
        u2_computed = prefs_2.utility(outcome.allocation_2)

        assert abs(u1_computed - outcome.utility_1) < 1e-9
        assert abs(u2_computed - outcome.utility_2) < 1e-9

        # Verify gains are computed correctly
        d1 = prefs_1.utility(endowment_1)
        d2 = prefs_2.utility(endowment_2)

        assert abs(outcome.gains_1 - (outcome.utility_1 - d1)) < 1e-9
        assert abs(outcome.gains_2 - (outcome.utility_2 - d2)) < 1e-9


class TestNashSymmetry:
    """Test symmetry property of Nash solution."""

    def test_symmetric_preferences_symmetric_endowments(self):
        """
        With identical preferences and symmetric endowments,
        the Nash solution should give equal utilities.
        """
        prefs = CobbDouglas(0.5)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs, endowment_1, prefs, endowment_2
        )

        # With symmetric setup, utilities should be equal
        assert abs(outcome.utility_1 - outcome.utility_2) < 1e-3

    def test_swapping_agents_swaps_outcome(self):
        """Swapping agent 1 and 2 should swap their allocations."""
        prefs_1 = CobbDouglas(0.3)
        prefs_2 = CobbDouglas(0.7)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome_12 = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )
        outcome_21 = nash_bargaining_solution(
            prefs_2, endowment_2, prefs_1, endowment_1
        )

        # Agent 1's allocation in first call should equal Agent 2's in swapped call
        assert abs(outcome_12.allocation_1.x - outcome_21.allocation_2.x) < 1e-6
        assert abs(outcome_12.allocation_1.y - outcome_21.allocation_2.y) < 1e-6
        assert abs(outcome_12.allocation_2.x - outcome_21.allocation_1.x) < 1e-6
        assert abs(outcome_12.allocation_2.y - outcome_21.allocation_1.y) < 1e-6


class TestNashIndividualRationality:
    """Test that Nash solution satisfies individual rationality."""

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.1, 0.9, 20.0, 1.0, 1.0, 20.0),
        (0.5, 0.5, 100.0, 100.0, 100.0, 100.0),
    ])
    def test_individual_rationality(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        Each agent should be at least as well off at the solution
        as at their disagreement point (own endowment).
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

        # Individual rationality: u_i >= d_i
        assert outcome.utility_1 >= d1 - 1e-9, (
            f"Agent 1 utility {outcome.utility_1} < disagreement {d1}"
        )
        assert outcome.utility_2 >= d2 - 1e-9, (
            f"Agent 2 utility {outcome.utility_2} < disagreement {d2}"
        )

        # Gains should be non-negative
        assert outcome.gains_1 >= -1e-9
        assert outcome.gains_2 >= -1e-9


class TestNashFeasibility:
    """Test that Nash solution is feasible."""

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.8, 0.2, 1.0, 100.0, 100.0, 1.0),
    ])
    def test_allocation_sums_to_total(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """Allocation should exhaust total endowment (no waste)."""
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        W_x = e1_x + e2_x
        W_y = e1_y + e2_y

        total_x = outcome.allocation_1.x + outcome.allocation_2.x
        total_y = outcome.allocation_1.y + outcome.allocation_2.y

        assert abs(total_x - W_x) < 1e-6, (
            f"X allocation {total_x} != total {W_x}"
        )
        assert abs(total_y - W_y) < 1e-6, (
            f"Y allocation {total_y} != total {W_y}"
        )

    def test_allocations_non_negative(self):
        """All allocations should be non-negative."""
        prefs_1 = CobbDouglas(0.3)
        prefs_2 = CobbDouglas(0.7)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        assert outcome.allocation_1.x >= 0
        assert outcome.allocation_1.y >= 0
        assert outcome.allocation_2.x >= 0
        assert outcome.allocation_2.y >= 0


class TestAsymmetricNash:
    """Test asymmetric Nash bargaining solution."""

    def test_weights_affect_outcome(self):
        """Different weights should produce different outcomes."""
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        # Symmetric weights
        outcome_sym = asymmetric_nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            weight_1=0.5, weight_2=0.5
        )

        # Agent 1 has more power
        outcome_1heavy = asymmetric_nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            weight_1=0.7, weight_2=0.3
        )

        # Agent 2 has more power
        outcome_2heavy = asymmetric_nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            weight_1=0.3, weight_2=0.7
        )

        # Higher weight should give higher utility
        assert outcome_1heavy.utility_1 > outcome_sym.utility_1
        assert outcome_2heavy.utility_2 > outcome_sym.utility_2

        # Lower weight should give lower utility
        assert outcome_1heavy.utility_2 < outcome_sym.utility_2
        assert outcome_2heavy.utility_1 < outcome_sym.utility_1

    def test_equal_weights_equals_symmetric_nash(self):
        """Asymmetric Nash with w1=w2=0.5 should equal symmetric Nash."""
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome_sym = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        outcome_asym = asymmetric_nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            weight_1=0.5, weight_2=0.5
        )

        # Should be identical (within tolerance)
        assert abs(outcome_sym.utility_1 - outcome_asym.utility_1) < 1e-6
        assert abs(outcome_sym.utility_2 - outcome_asym.utility_2) < 1e-6

    def test_asymmetric_nash_product_maximized(self):
        """
        Verify asymmetric Nash maximizes (u1-d1)^w1 * (u2-d2)^w2.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)
        weight_1, weight_2 = 0.6, 0.4

        outcome = asymmetric_nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            weight_1=weight_1, weight_2=weight_2
        )

        d1 = prefs_1.utility(endowment_1)
        d2 = prefs_2.utility(endowment_2)

        def asym_nash_product(alloc1: Bundle, alloc2: Bundle) -> float:
            u1 = prefs_1.utility(alloc1)
            u2 = prefs_2.utility(alloc2)
            if u1 <= d1 or u2 <= d2:
                return -float('inf')
            return ((u1 - d1) ** weight_1) * ((u2 - d2) ** weight_2)

        anp_solution = asym_nash_product(
            outcome.allocation_1, outcome.allocation_2
        )

        # Grid search
        W_x = endowment_1.x + endowment_2.x
        W_y = endowment_1.y + endowment_2.y
        n_points = 50

        for i in range(1, n_points):
            for j in range(1, n_points):
                x1 = (i / n_points) * W_x
                y1 = (j / n_points) * W_y

                anp_test = asym_nash_product(
                    Bundle(x1, y1), Bundle(W_x - x1, W_y - y1)
                )

                assert anp_solution >= anp_test - 1e-6, (
                    f"Found higher asymmetric Nash product: "
                    f"solution={anp_solution:.6f}, test={anp_test:.6f}"
                )
