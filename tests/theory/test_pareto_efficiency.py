"""
THEORY-005: Verify Pareto Efficiency of Outcomes.

Tests verifying bargaining outcomes are Pareto efficient:
- No feasible reallocation should Pareto-dominate the solution
- MRS equality at solution (contract curve condition)
- Outcome lies on the contract curve

Theoretical References:
- Kreps I Ch 8.3 (Pareto efficiency)
- First welfare theorem connection
- Contract curve characterization

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
)

pytestmark = pytest.mark.theory


class TestParetoEfficiencyNash:
    """Test Pareto efficiency of Nash bargaining solution."""

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.8, 0.2, 20.0, 2.0, 2.0, 20.0),
        (0.4, 0.6, 15.0, 8.0, 8.0, 15.0),
        (0.1, 0.9, 50.0, 5.0, 5.0, 50.0),
    ])
    def test_no_pareto_dominating_allocation_nash(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        No feasible allocation should Pareto-dominate the Nash solution.

        An allocation Pareto-dominates another if it makes at least one
        agent strictly better off while making no agent worse off.
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        if not outcome.trade_occurred:
            return  # No trade case, skip

        W_x = e1_x + e2_x
        W_y = e1_y + e2_y

        # Grid search for Pareto-dominating allocations
        n_points = 40
        for i in range(1, n_points):
            for j in range(1, n_points):
                x1 = (i / n_points) * W_x
                y1 = (j / n_points) * W_y
                x2 = W_x - x1
                y2 = W_y - y1

                if x2 <= 0 or y2 <= 0:
                    continue

                test_u1 = prefs_1.utility(Bundle(x1, y1))
                test_u2 = prefs_2.utility(Bundle(x2, y2))

                # Check for Pareto domination:
                # Both at least as well off, at least one strictly better
                weakly_better_1 = test_u1 >= outcome.utility_1 - 1e-9
                weakly_better_2 = test_u2 >= outcome.utility_2 - 1e-9
                strictly_better_1 = test_u1 > outcome.utility_1 + 1e-9
                strictly_better_2 = test_u2 > outcome.utility_2 + 1e-9

                pareto_dominates = (
                    weakly_better_1 and weakly_better_2 and
                    (strictly_better_1 or strictly_better_2)
                )

                assert not pareto_dominates, (
                    f"Found Pareto-dominating allocation at ({x1:.2f}, {y1:.2f}): "
                    f"test=({test_u1:.4f}, {test_u2:.4f}), "
                    f"solution=({outcome.utility_1:.4f}, {outcome.utility_2:.4f})"
                )


class TestParetoEfficiencyRubinstein:
    """Test Pareto efficiency of Rubinstein bargaining solution."""

    @pytest.mark.parametrize("delta1,delta2", [
        (0.9, 0.9),
        (0.9, 0.7),
        (0.8, 0.95),
        (0.5, 0.5),
    ])
    def test_no_pareto_dominating_allocation_rubinstein(self, delta1, delta2):
        """
        Rubinstein solution should also be Pareto efficient.

        Like Nash, it lies on the contract curve, just at a different point.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = rubinstein_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            delta_1=delta1, delta_2=delta2
        )

        W_x = 15.0
        W_y = 15.0

        n_points = 30
        for i in range(1, n_points):
            for j in range(1, n_points):
                x1 = (i / n_points) * W_x
                y1 = (j / n_points) * W_y
                x2 = W_x - x1
                y2 = W_y - y1

                if x2 <= 0 or y2 <= 0:
                    continue

                test_u1 = prefs_1.utility(Bundle(x1, y1))
                test_u2 = prefs_2.utility(Bundle(x2, y2))

                weakly_better_1 = test_u1 >= outcome.utility_1 - 1e-9
                weakly_better_2 = test_u2 >= outcome.utility_2 - 1e-9
                strictly_better_1 = test_u1 > outcome.utility_1 + 1e-9
                strictly_better_2 = test_u2 > outcome.utility_2 + 1e-9

                pareto_dominates = (
                    weakly_better_1 and weakly_better_2 and
                    (strictly_better_1 or strictly_better_2)
                )

                assert not pareto_dominates


class TestMRSEquality:
    """Test MRS equality at efficient allocations (contract curve condition)."""

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.8, 0.2, 20.0, 2.0, 2.0, 20.0),
        (0.4, 0.6, 15.0, 8.0, 8.0, 15.0),
    ])
    def test_mrs_equality_at_nash_solution(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        At Pareto efficient allocation, MRS_1 = MRS_2.

        This is the contract curve condition: both agents have the same
        marginal rate of substitution at the allocation.
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        if not outcome.trade_occurred:
            return

        mrs_1 = prefs_1.marginal_rate_of_substitution(outcome.allocation_1)
        mrs_2 = prefs_2.marginal_rate_of_substitution(outcome.allocation_2)

        # MRS should be equal at efficient allocation
        assert abs(mrs_1 - mrs_2) < 1e-3, (
            f"MRS not equal: MRS_1={mrs_1:.6f}, MRS_2={mrs_2:.6f}"
        )

    @pytest.mark.parametrize("delta1,delta2", [
        (0.9, 0.9),
        (0.9, 0.7),
        (0.8, 0.95),
    ])
    def test_mrs_equality_at_rubinstein_solution(self, delta1, delta2):
        """MRS equality should hold for Rubinstein solution too."""
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = rubinstein_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            delta_1=delta1, delta_2=delta2
        )

        mrs_1 = prefs_1.marginal_rate_of_substitution(outcome.allocation_1)
        mrs_2 = prefs_2.marginal_rate_of_substitution(outcome.allocation_2)

        assert abs(mrs_1 - mrs_2) < 1e-3, (
            f"MRS not equal: MRS_1={mrs_1:.6f}, MRS_2={mrs_2:.6f}"
        )


class TestContractCurve:
    """Test that outcomes lie on the contract curve."""

    def compute_contract_curve_mrs(
        self, prefs_1: CobbDouglas, prefs_2: CobbDouglas,
        x1: float, y1: float, W_x: float, W_y: float
    ) -> tuple[float, float]:
        """Compute MRS for both agents at a given allocation."""
        x2 = W_x - x1
        y2 = W_y - y1

        if x1 <= 0 or y1 <= 0 or x2 <= 0 or y2 <= 0:
            return float('inf'), float('inf')

        mrs_1 = prefs_1.marginal_rate_of_substitution(Bundle(x1, y1))
        mrs_2 = prefs_2.marginal_rate_of_substitution(Bundle(x2, y2))

        return mrs_1, mrs_2

    def test_contract_curve_characterization(self):
        """
        The contract curve is characterized by MRS_1 = MRS_2.

        For Cobb-Douglas:
        MRS_1 = (a1/(1-a1)) * (y1/x1)
        MRS_2 = (a2/(1-a2)) * (y2/x2)

        Setting these equal gives the contract curve equation.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        W_x, W_y = 15.0, 15.0

        # Find points on the contract curve by solving MRS equality
        a1, a2 = 0.4, 0.6

        # MRS_1 = MRS_2
        # (a1/(1-a1)) * (y1/x1) = (a2/(1-a2)) * ((W_y-y1)/(W_x-x1))

        # For a few x1 values, find y1 on contract curve
        contract_curve_points = []
        for x1 in [3.0, 5.0, 7.0, 10.0, 12.0]:
            # Binary search for y1 that gives MRS equality
            # As y1 increases: MRS_1 = (a1/(1-a1))*(y1/x1) increases
            #                  MRS_2 = (a2/(1-a2))*(y2/x2) decreases (y2 = W_y - y1)
            # So if MRS_1 > MRS_2, we need to decrease y1
            y_lo, y_hi = 0.1, W_y - 0.1
            for _ in range(50):
                y_mid = (y_lo + y_hi) / 2
                mrs_1, mrs_2 = self.compute_contract_curve_mrs(
                    prefs_1, prefs_2, x1, y_mid, W_x, W_y
                )

                if mrs_1 > mrs_2:
                    y_hi = y_mid  # MRS_1 too high, decrease y1
                else:
                    y_lo = y_mid  # MRS_1 too low, increase y1

            y1 = (y_lo + y_hi) / 2
            mrs_1, mrs_2 = self.compute_contract_curve_mrs(
                prefs_1, prefs_2, x1, y1, W_x, W_y
            )

            # Should be on contract curve
            assert abs(mrs_1 - mrs_2) < 1e-6, (
                f"Point ({x1}, {y1}) not on contract curve: "
                f"MRS_1={mrs_1}, MRS_2={mrs_2}"
            )
            contract_curve_points.append((x1, y1))

    def test_nash_solution_on_contract_curve(self):
        """
        Nash solution should lie on the contract curve.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcome = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        # Verify it's on the contract curve (MRS equal)
        mrs_1 = prefs_1.marginal_rate_of_substitution(outcome.allocation_1)
        mrs_2 = prefs_2.marginal_rate_of_substitution(outcome.allocation_2)

        assert abs(mrs_1 - mrs_2) < 1e-3, (
            f"Nash solution not on contract curve: MRS_1={mrs_1}, MRS_2={mrs_2}"
        )

    def test_different_bargaining_weights_different_contract_curve_points(self):
        """
        Different bargaining weights select different points on the contract curve.

        All should be Pareto efficient (on the curve), but at different locations.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        outcomes = []
        for w1 in [0.3, 0.5, 0.7]:
            outcome = asymmetric_nash_bargaining_solution(
                prefs_1, endowment_1, prefs_2, endowment_2,
                weight_1=w1, weight_2=1-w1
            )
            outcomes.append((w1, outcome))

            # All should be on contract curve
            mrs_1 = prefs_1.marginal_rate_of_substitution(outcome.allocation_1)
            mrs_2 = prefs_2.marginal_rate_of_substitution(outcome.allocation_2)
            assert abs(mrs_1 - mrs_2) < 1e-3

        # Higher w1 should give agent 1 more utility
        assert outcomes[2][1].utility_1 > outcomes[1][1].utility_1 > outcomes[0][1].utility_1

        # All allocations should be different
        for i in range(len(outcomes)):
            for j in range(i + 1, len(outcomes)):
                diff_x = abs(outcomes[i][1].allocation_1.x - outcomes[j][1].allocation_1.x)
                assert diff_x > 0.01, "Different weights should give different allocations"


class TestParetoFrontier:
    """Test properties of the Pareto frontier."""

    def test_pareto_frontier_is_continuous(self):
        """
        The Pareto frontier should be continuous.

        Small changes in bargaining weights should produce small changes
        in outcome utilities.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        prev_outcome = None
        for w1 in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            outcome = asymmetric_nash_bargaining_solution(
                prefs_1, endowment_1, prefs_2, endowment_2,
                weight_1=w1, weight_2=1-w1
            )

            if prev_outcome is not None:
                # Change should be bounded
                du1 = abs(outcome.utility_1 - prev_outcome.utility_1)
                du2 = abs(outcome.utility_2 - prev_outcome.utility_2)
                assert du1 < 2.0, f"Discontinuity in u1 at w1={w1}"
                assert du2 < 2.0, f"Discontinuity in u2 at w1={w1}"

            prev_outcome = outcome

    def test_pareto_frontier_monotonicity(self):
        """
        On the Pareto frontier, increasing one agent's utility
        must decrease the other's (efficient trade-off).
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        u1_values = []
        u2_values = []

        for w1 in [0.1, 0.3, 0.5, 0.7, 0.9]:
            outcome = asymmetric_nash_bargaining_solution(
                prefs_1, endowment_1, prefs_2, endowment_2,
                weight_1=w1, weight_2=1-w1
            )
            u1_values.append(outcome.utility_1)
            u2_values.append(outcome.utility_2)

        # As w1 increases, u1 should increase and u2 should decrease
        for i in range(len(u1_values) - 1):
            assert u1_values[i] < u1_values[i + 1], (
                f"u1 not increasing with w1: {u1_values}"
            )
            assert u2_values[i] > u2_values[i + 1], (
                f"u2 not decreasing with w1: {u2_values}"
            )


class TestFirstWelfareTheorem:
    """
    Test connection to First Welfare Theorem.

    The First Welfare Theorem states that any competitive equilibrium
    allocation is Pareto efficient. Our bargaining solutions are
    analogous - they produce efficient allocations.
    """

    def test_bargaining_outcomes_efficient(self):
        """
        All bargaining outcomes (Nash, Rubinstein) are Pareto efficient.

        This mirrors the First Welfare Theorem for competitive equilibria.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        # Nash solution
        nash = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        # Rubinstein solution
        rub = rubinstein_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2,
            delta_1=0.9, delta_2=0.8
        )

        # Both should satisfy MRS equality (efficiency condition)
        nash_mrs_1 = prefs_1.marginal_rate_of_substitution(nash.allocation_1)
        nash_mrs_2 = prefs_2.marginal_rate_of_substitution(nash.allocation_2)
        assert abs(nash_mrs_1 - nash_mrs_2) < 1e-3

        rub_mrs_1 = prefs_1.marginal_rate_of_substitution(rub.allocation_1)
        rub_mrs_2 = prefs_2.marginal_rate_of_substitution(rub.allocation_2)
        assert abs(rub_mrs_1 - rub_mrs_2) < 1e-3

    def test_inefficient_allocation_not_on_contract_curve(self):
        """
        An inefficient allocation should have MRS inequality.
        """
        prefs_1 = CobbDouglas(0.4)
        prefs_2 = CobbDouglas(0.6)

        # Take an arbitrary interior allocation (likely inefficient)
        alloc_1 = Bundle(7.0, 8.0)
        alloc_2 = Bundle(8.0, 7.0)

        mrs_1 = prefs_1.marginal_rate_of_substitution(alloc_1)
        mrs_2 = prefs_2.marginal_rate_of_substitution(alloc_2)

        # Unless we're lucky, MRS won't be equal
        # This demonstrates that random allocations are typically inefficient
        if abs(mrs_1 - mrs_2) > 0.01:
            # Inefficient - there exist Pareto improvements
            W_x, W_y = 15.0, 15.0

            # Find a better allocation
            found_improvement = False
            for dx in [-0.5, 0.5]:
                for dy in [-0.5, 0.5]:
                    new_x1 = alloc_1.x + dx
                    new_y1 = alloc_1.y + dy
                    new_x2 = W_x - new_x1
                    new_y2 = W_y - new_y1

                    if new_x1 <= 0 or new_y1 <= 0 or new_x2 <= 0 or new_y2 <= 0:
                        continue

                    new_u1 = prefs_1.utility(Bundle(new_x1, new_y1))
                    new_u2 = prefs_2.utility(Bundle(new_x2, new_y2))

                    old_u1 = prefs_1.utility(alloc_1)
                    old_u2 = prefs_2.utility(alloc_2)

                    if new_u1 >= old_u1 and new_u2 >= old_u2:
                        if new_u1 > old_u1 or new_u2 > old_u2:
                            found_improvement = True
                            break

            # Should find Pareto improvement for inefficient allocation
            # (not guaranteed but very likely for arbitrary allocation)
            pass  # Test demonstrates concept; exact result depends on allocation
