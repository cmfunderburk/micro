"""Tests for Bundle class."""

import pytest
from microecon.bundle import Bundle


class TestBundleCreation:
    """Test bundle creation and validation."""

    def test_create_valid_bundle(self):
        b = Bundle(3.0, 5.0)
        assert b.x == 3.0
        assert b.y == 5.0

    def test_create_zero_bundle(self):
        b = Bundle.zero()
        assert b.x == 0.0
        assert b.y == 0.0

    def test_reject_negative_x(self):
        with pytest.raises(ValueError, match="non-negative"):
            Bundle(-1.0, 5.0)

    def test_reject_negative_y(self):
        with pytest.raises(ValueError, match="non-negative"):
            Bundle(3.0, -2.0)

    def test_bundle_is_immutable(self):
        b = Bundle(3.0, 5.0)
        with pytest.raises(AttributeError):
            b.x = 10.0


class TestBundleArithmetic:
    """Test bundle arithmetic operations."""

    def test_addition(self):
        a = Bundle(3.0, 5.0)
        b = Bundle(2.0, 1.0)
        result = a + b
        assert result == Bundle(5.0, 6.0)

    def test_scalar_multiplication(self):
        b = Bundle(3.0, 4.0)
        result = b * 2.0
        assert result == Bundle(6.0, 8.0)

    def test_right_scalar_multiplication(self):
        b = Bundle(3.0, 4.0)
        result = 0.5 * b
        assert result == Bundle(1.5, 2.0)


class TestBundleComparison:
    """Test bundle dominance relations."""

    def test_dominates(self):
        a = Bundle(5.0, 5.0)
        b = Bundle(3.0, 4.0)
        assert a.dominates(b)
        assert not b.dominates(a)

    def test_strictly_dominates(self):
        a = Bundle(5.0, 5.0)
        b = Bundle(3.0, 4.0)
        c = Bundle(5.0, 4.0)  # Equal x

        assert a.strictly_dominates(b)
        assert not a.strictly_dominates(c)  # Not strictly greater in x

    def test_is_strictly_positive(self):
        assert Bundle(1.0, 2.0).is_strictly_positive()
        assert not Bundle(0.0, 2.0).is_strictly_positive()
        assert not Bundle(1.0, 0.0).is_strictly_positive()
