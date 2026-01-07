"""
THEORY-003: Verify Utility and Preference Calculations.

Tests verifying CobbDouglas preferences match textbook formulas:
- MRS = (alpha/(1-alpha)) * (y/x)
- Marshallian demand: x* = alpha*M/px, y* = (1-alpha)*M/py
- Indirect utility computation

Theoretical References:
- Kreps I Ch 2-3
- MRS = MUx/MUy
- Lagrangian first-order conditions

Test tolerance: rel=1e-6 (formula verification)
"""

import pytest
import math
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas


class TestMRSFormula:
    """Test MRS formula: MRS = (alpha/(1-alpha)) * (y/x)."""

    @pytest.mark.parametrize("alpha,x,y", [
        (0.5, 10.0, 10.0),
        (0.5, 10.0, 20.0),
        (0.3, 10.0, 10.0),
        (0.7, 10.0, 10.0),
        (0.5, 1.0, 100.0),
        (0.5, 100.0, 1.0),
        (0.1, 5.0, 50.0),
        (0.9, 50.0, 5.0),
    ])
    def test_mrs_formula_direct(self, alpha, x, y):
        """
        Verify MRS = (alpha/(1-alpha)) * (y/x) directly.

        MRS is the rate at which the consumer is willing to trade
        good y for good x while maintaining utility.
        """
        prefs = CobbDouglas(alpha)
        bundle = Bundle(x, y)

        computed_mrs = prefs.marginal_rate_of_substitution(bundle)
        expected_mrs = (alpha / (1 - alpha)) * (y / x)

        assert abs(computed_mrs - expected_mrs) < 1e-10, (
            f"MRS mismatch: computed={computed_mrs}, expected={expected_mrs}"
        )

    def test_mrs_equals_ratio_of_marginal_utilities(self):
        """
        Verify MRS = MU_x / MU_y.

        For Cobb-Douglas u = x^a * y^(1-a):
            MU_x = a * x^(a-1) * y^(1-a)
            MU_y = (1-a) * x^a * y^(-a)
            MRS = MU_x / MU_y = (a/(1-a)) * (y/x)
        """
        alpha = 0.4
        prefs = CobbDouglas(alpha)
        x, y = 10.0, 15.0
        bundle = Bundle(x, y)

        # Compute marginal utilities via partial derivatives
        # For small h, MU_x ≈ (u(x+h,y) - u(x,y)) / h
        h = 1e-7
        mu_x = (prefs.utility(Bundle(x + h, y)) - prefs.utility(bundle)) / h
        mu_y = (prefs.utility(Bundle(x, y + h)) - prefs.utility(bundle)) / h

        mrs_from_mu = mu_x / mu_y
        mrs_formula = prefs.marginal_rate_of_substitution(bundle)

        assert abs(mrs_from_mu - mrs_formula) < 1e-4, (
            f"MRS from MU ratio {mrs_from_mu} != formula {mrs_formula}"
        )

    @pytest.mark.parametrize("alpha", [0.2, 0.4, 0.5, 0.6, 0.8])
    def test_mrs_decreasing_along_indifference_curve(self, alpha):
        """
        MRS should be strictly decreasing along an indifference curve.

        This is the diminishing MRS property that makes preferences convex.
        """
        prefs = CobbDouglas(alpha)
        target_utility = 10.0

        # Find points on the indifference curve u(x,y) = target_utility
        # For Cobb-Douglas: y = (target_utility / x^alpha)^(1/(1-alpha))
        mrs_values = []
        x_values = [2.0, 5.0, 10.0, 20.0, 50.0]

        for x in x_values:
            y = (target_utility / (x ** alpha)) ** (1 / (1 - alpha))
            bundle = Bundle(x, y)

            # Verify we're on the indifference curve
            assert abs(prefs.utility(bundle) - target_utility) < 1e-6

            mrs = prefs.marginal_rate_of_substitution(bundle)
            mrs_values.append(mrs)

        # MRS should be strictly decreasing
        for i in range(len(mrs_values) - 1):
            assert mrs_values[i] > mrs_values[i + 1], (
                f"MRS not decreasing: {mrs_values[i]} <= {mrs_values[i+1]} "
                f"at x={x_values[i]}, {x_values[i+1]}"
            )


class TestMarshallianDemand:
    """Test Marshallian demand: x* = alpha*M/px, y* = (1-alpha)*M/py."""

    @pytest.mark.parametrize("alpha,income,p_x,p_y", [
        (0.5, 100.0, 1.0, 1.0),
        (0.5, 100.0, 2.0, 1.0),
        (0.5, 100.0, 1.0, 2.0),
        (0.3, 150.0, 3.0, 2.0),
        (0.7, 200.0, 4.0, 5.0),
        (0.1, 1000.0, 10.0, 10.0),
        (0.9, 50.0, 0.5, 2.0),
    ])
    def test_marshallian_demand_formula(self, alpha, income, p_x, p_y):
        """
        Verify Marshallian demand: x* = alpha*M/p_x, y* = (1-alpha)*M/p_y.

        This is derived from the Lagrangian first-order conditions:
            MU_x / p_x = MU_y / p_y (= lambda)
            p_x * x + p_y * y = M (budget constraint)
        """
        prefs = CobbDouglas(alpha)
        optimal = prefs.marshallian_demand(income, p_x, p_y)

        expected_x = alpha * income / p_x
        expected_y = (1 - alpha) * income / p_y

        assert abs(optimal.x - expected_x) < 1e-10, (
            f"x* mismatch: computed={optimal.x}, expected={expected_x}"
        )
        assert abs(optimal.y - expected_y) < 1e-10, (
            f"y* mismatch: computed={optimal.y}, expected={expected_y}"
        )

    @pytest.mark.parametrize("alpha,income,p_x,p_y", [
        (0.5, 100.0, 1.0, 1.0),
        (0.3, 150.0, 3.0, 2.0),
        (0.7, 200.0, 4.0, 5.0),
    ])
    def test_demand_exhausts_budget(self, alpha, income, p_x, p_y):
        """
        Optimal bundle should exactly exhaust the budget.

        p_x * x* + p_y * y* = M
        """
        prefs = CobbDouglas(alpha)
        optimal = prefs.marshallian_demand(income, p_x, p_y)

        expenditure = p_x * optimal.x + p_y * optimal.y
        assert abs(expenditure - income) < 1e-10, (
            f"Budget not exhausted: {expenditure} != {income}"
        )

    @pytest.mark.parametrize("alpha", [0.2, 0.4, 0.5, 0.6, 0.8])
    def test_budget_shares_constant(self, alpha):
        """
        Homothetic property: Budget shares are constant across income levels.

        For Cobb-Douglas, share spent on x is always alpha,
        share spent on y is always (1-alpha).
        """
        prefs = CobbDouglas(alpha)
        p_x, p_y = 2.0, 3.0

        for income in [50.0, 100.0, 200.0, 500.0]:
            optimal = prefs.marshallian_demand(income, p_x, p_y)

            share_x = (p_x * optimal.x) / income
            share_y = (p_y * optimal.y) / income

            assert abs(share_x - alpha) < 1e-10, (
                f"x share {share_x} != alpha {alpha} at income {income}"
            )
            assert abs(share_y - (1 - alpha)) < 1e-10, (
                f"y share {share_y} != (1-alpha) {1-alpha} at income {income}"
            )

    def test_mrs_equals_price_ratio_at_optimum(self):
        """
        At the optimum, MRS = p_x / p_y (tangency condition).

        This is the first-order condition from utility maximization.
        """
        alpha = 0.4
        prefs = CobbDouglas(alpha)
        income, p_x, p_y = 100.0, 2.0, 3.0

        optimal = prefs.marshallian_demand(income, p_x, p_y)
        mrs_at_optimum = prefs.marginal_rate_of_substitution(optimal)
        price_ratio = p_x / p_y

        assert abs(mrs_at_optimum - price_ratio) < 1e-10, (
            f"MRS {mrs_at_optimum} != price ratio {price_ratio} at optimum"
        )


class TestIndirectUtility:
    """Test indirect utility computation."""

    @pytest.mark.parametrize("alpha,income,p_x,p_y", [
        (0.5, 100.0, 1.0, 1.0),
        (0.3, 150.0, 3.0, 2.0),
        (0.7, 200.0, 4.0, 5.0),
    ])
    def test_indirect_utility_equals_utility_at_optimum(
        self, alpha, income, p_x, p_y
    ):
        """
        Indirect utility V(p,M) = u(x*(p,M), y*(p,M)).
        """
        prefs = CobbDouglas(alpha)

        optimal = prefs.marshallian_demand(income, p_x, p_y)
        direct_utility = prefs.utility(optimal)
        indirect_utility = prefs.indirect_utility(income, p_x, p_y)

        assert abs(direct_utility - indirect_utility) < 1e-10

    def test_indirect_utility_formula(self):
        """
        For Cobb-Douglas, indirect utility has a closed form:
        V(p,M) = (alpha/p_x)^alpha * ((1-alpha)/p_y)^(1-alpha) * M

        This can be derived by substituting optimal demands into utility.
        """
        alpha = 0.4
        prefs = CobbDouglas(alpha)
        income, p_x, p_y = 100.0, 2.0, 3.0

        # Closed-form formula
        expected_v = (
            ((alpha / p_x) ** alpha) *
            (((1 - alpha) / p_y) ** (1 - alpha)) *
            income
        )

        computed_v = prefs.indirect_utility(income, p_x, p_y)

        assert abs(computed_v - expected_v) < 1e-10, (
            f"Indirect utility {computed_v} != formula {expected_v}"
        )


class TestBoundaryCases:
    """Test boundary cases for preferences."""

    def test_utility_zero_at_boundary(self):
        """Utility is 0 when either good is 0 (boundary of commodity space)."""
        prefs = CobbDouglas(0.5)

        assert prefs.utility(Bundle(0.0, 10.0)) == 0.0
        assert prefs.utility(Bundle(10.0, 0.0)) == 0.0
        assert prefs.utility(Bundle(0.0, 0.0)) == 0.0

    def test_mrs_at_boundary(self):
        """MRS behavior at boundaries."""
        prefs = CobbDouglas(0.5)

        # MRS = inf when x = 0 (willing to give up infinite y for marginal x)
        assert prefs.marginal_rate_of_substitution(Bundle(0.0, 10.0)) == float('inf')

        # MRS = 0 when y = 0 (not willing to give up any y for x)
        assert prefs.marginal_rate_of_substitution(Bundle(10.0, 0.0)) == 0.0

    def test_utility_positive_interior(self):
        """Utility is strictly positive for interior bundles."""
        prefs = CobbDouglas(0.5)

        for x in [0.1, 1.0, 10.0, 100.0]:
            for y in [0.1, 1.0, 10.0, 100.0]:
                assert prefs.utility(Bundle(x, y)) > 0


class TestLogUtility:
    """Test log utility transformation."""

    def test_log_utility_formula(self):
        """
        Log utility: ln(u) = alpha*ln(x) + (1-alpha)*ln(y).

        This monotonic transformation is often more convenient.
        """
        alpha = 0.4
        prefs = CobbDouglas(alpha)
        x, y = 10.0, 15.0
        bundle = Bundle(x, y)

        expected_log_u = alpha * math.log(x) + (1 - alpha) * math.log(y)
        computed_log_u = prefs.log_utility(bundle)

        assert abs(computed_log_u - expected_log_u) < 1e-10

    def test_log_utility_is_monotonic_transform(self):
        """Log utility is monotonic transform of utility."""
        prefs = CobbDouglas(0.5)

        bundles = [
            Bundle(5.0, 5.0),
            Bundle(10.0, 10.0),
            Bundle(7.0, 14.0),
            Bundle(20.0, 5.0),
        ]

        utilities = [prefs.utility(b) for b in bundles]
        log_utilities = [prefs.log_utility(b) for b in bundles]

        # Same ordering
        for i in range(len(bundles)):
            for j in range(len(bundles)):
                if utilities[i] > utilities[j]:
                    assert log_utilities[i] > log_utilities[j]
                elif utilities[i] < utilities[j]:
                    assert log_utilities[i] < log_utilities[j]

    def test_log_utility_negative_infinity_at_boundary(self):
        """Log utility is -inf at boundary (consistent with utility = 0)."""
        prefs = CobbDouglas(0.5)

        assert prefs.log_utility(Bundle(0.0, 10.0)) == float('-inf')
        assert prefs.log_utility(Bundle(10.0, 0.0)) == float('-inf')


class TestPreferenceOrdering:
    """Test preference ordering methods."""

    def test_prefers(self):
        """Test strict preference relation."""
        prefs = CobbDouglas(0.5)

        a = Bundle(10.0, 10.0)
        b = Bundle(5.0, 5.0)
        c = Bundle(10.0, 10.0)

        assert prefs.prefers(a, b)
        assert not prefs.prefers(b, a)
        assert not prefs.prefers(a, c)  # Equal utility, not strictly preferred

    def test_indifferent(self):
        """Test indifference relation."""
        prefs = CobbDouglas(0.5)

        a = Bundle(10.0, 10.0)

        # Find point on same indifference curve
        u_a = prefs.utility(a)
        # For y = 20, find x such that x^0.5 * 20^0.5 = u_a
        x_b = (u_a / (20.0 ** 0.5)) ** 2
        b = Bundle(x_b, 20.0)

        assert prefs.indifferent(a, b)

        c = Bundle(11.0, 11.0)
        assert not prefs.indifferent(a, c)


class TestAlphaValidation:
    """Test alpha parameter validation."""

    def test_alpha_must_be_in_open_interval(self):
        """Alpha must be in (0, 1)."""
        with pytest.raises(ValueError):
            CobbDouglas(0.0)

        with pytest.raises(ValueError):
            CobbDouglas(1.0)

        with pytest.raises(ValueError):
            CobbDouglas(-0.1)

        with pytest.raises(ValueError):
            CobbDouglas(1.5)

    def test_valid_alpha_values(self):
        """Valid alpha values should work."""
        for alpha in [0.01, 0.1, 0.5, 0.9, 0.99]:
            prefs = CobbDouglas(alpha)
            assert prefs.alpha == alpha
