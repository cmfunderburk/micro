"""Tests for preference representations."""

import pytest
import math
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas

pytestmark = pytest.mark.core


class TestCobbDouglasCreation:
    """Test Cobb-Douglas preference creation."""

    def test_valid_alpha(self):
        prefs = CobbDouglas(0.5)
        assert prefs.alpha == 0.5

    def test_reject_alpha_zero(self):
        with pytest.raises(ValueError, match="alpha must be in"):
            CobbDouglas(0.0)

    def test_reject_alpha_one(self):
        with pytest.raises(ValueError, match="alpha must be in"):
            CobbDouglas(1.0)

    def test_reject_negative_alpha(self):
        with pytest.raises(ValueError, match="alpha must be in"):
            CobbDouglas(-0.5)


class TestCobbDouglasUtility:
    """Test utility computation."""

    def test_utility_basic(self):
        prefs = CobbDouglas(0.5)
        bundle = Bundle(4.0, 4.0)
        # u = 4^0.5 * 4^0.5 = 2 * 2 = 4
        assert prefs.utility(bundle) == pytest.approx(4.0)

    def test_utility_asymmetric(self):
        prefs = CobbDouglas(0.25)
        bundle = Bundle(16.0, 16.0)
        # u = 16^0.25 * 16^0.75 = 2 * 8 = 16
        assert prefs.utility(bundle) == pytest.approx(16.0)

    def test_utility_zero_x(self):
        prefs = CobbDouglas(0.5)
        bundle = Bundle(0.0, 5.0)
        assert prefs.utility(bundle) == 0.0

    def test_utility_zero_y(self):
        prefs = CobbDouglas(0.5)
        bundle = Bundle(5.0, 0.0)
        assert prefs.utility(bundle) == 0.0

    def test_log_utility(self):
        prefs = CobbDouglas(0.5)
        bundle = Bundle(4.0, 4.0)
        # ln(4) = 1.386...
        expected = 0.5 * math.log(4.0) + 0.5 * math.log(4.0)
        assert prefs.log_utility(bundle) == pytest.approx(expected)


class TestCobbDouglasMRS:
    """Test marginal rate of substitution."""

    def test_mrs_symmetric(self):
        prefs = CobbDouglas(0.5)
        bundle = Bundle(4.0, 4.0)
        # MRS = (0.5/0.5) * (4/4) = 1
        assert prefs.marginal_rate_of_substitution(bundle) == pytest.approx(1.0)

    def test_mrs_asymmetric_preferences(self):
        prefs = CobbDouglas(0.25)
        bundle = Bundle(1.0, 3.0)
        # MRS = (0.25/0.75) * (3/1) = 1
        assert prefs.marginal_rate_of_substitution(bundle) == pytest.approx(1.0)


class TestCobbDouglasPreference:
    """Test preference relations."""

    def test_prefers_more(self):
        prefs = CobbDouglas(0.5)
        a = Bundle(5.0, 5.0)
        b = Bundle(4.0, 4.0)
        assert prefs.prefers(a, b)
        assert not prefs.prefers(b, a)

    def test_indifferent(self):
        prefs = CobbDouglas(0.5)
        a = Bundle(4.0, 4.0)
        b = Bundle(2.0, 8.0)  # 2^0.5 * 8^0.5 = sqrt(16) = 4
        assert prefs.indifferent(a, b, tol=1e-6)


class TestCobbDouglasDemand:
    """Test demand functions."""

    def test_marshallian_demand_symmetric(self):
        prefs = CobbDouglas(0.5)
        demand = prefs.marshallian_demand(income=100.0, p_x=1.0, p_y=1.0)
        # x* = 0.5 * 100 / 1 = 50
        # y* = 0.5 * 100 / 1 = 50
        assert demand.x == pytest.approx(50.0)
        assert demand.y == pytest.approx(50.0)

    def test_marshallian_demand_different_prices(self):
        prefs = CobbDouglas(0.25)
        demand = prefs.marshallian_demand(income=100.0, p_x=2.0, p_y=1.0)
        # x* = 0.25 * 100 / 2 = 12.5
        # y* = 0.75 * 100 / 1 = 75
        assert demand.x == pytest.approx(12.5)
        assert demand.y == pytest.approx(75.0)

    def test_demand_exhausts_budget(self):
        prefs = CobbDouglas(0.5)
        demand = prefs.marshallian_demand(income=100.0, p_x=2.0, p_y=3.0)
        expenditure = 2.0 * demand.x + 3.0 * demand.y
        assert expenditure == pytest.approx(100.0)
