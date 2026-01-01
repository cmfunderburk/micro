"""
Bundle representation for a 2-good economy.

In standard microeconomic theory, a bundle is a vector in the commodity space.
For our 2-good economy, this is a point in R^2_+.

Reference: Kreps I, Ch 1-2
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Bundle:
    """
    A bundle of goods in a 2-good economy.

    Represents a consumption bundle (x, y) where both goods are non-negative.
    Immutable to ensure bundles can be safely shared and compared.

    Attributes:
        x: Quantity of good 1 (non-negative)
        y: Quantity of good 2 (non-negative)
    """
    x: float
    y: float

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError(f"Bundle quantities must be non-negative: ({self.x}, {self.y})")

    def __add__(self, other: Bundle) -> Bundle:
        """Add two bundles component-wise."""
        if not isinstance(other, Bundle):
            return NotImplemented
        return Bundle(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Bundle) -> Bundle:
        """Subtract bundles component-wise. Result may have negative components."""
        if not isinstance(other, Bundle):
            return NotImplemented
        # Allow negative for transfer calculations; caller validates if needed
        return Bundle.__new__(Bundle)._unsafe_init(self.x - other.x, self.y - other.y)

    def _unsafe_init(self, x: float, y: float) -> Bundle:
        """Internal: create bundle without non-negativity check."""
        object.__setattr__(self, 'x', x)
        object.__setattr__(self, 'y', y)
        return self

    def __mul__(self, scalar: float) -> Bundle:
        """Scalar multiplication."""
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Bundle(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Bundle:
        """Right scalar multiplication."""
        return self.__mul__(scalar)

    def is_weakly_positive(self) -> bool:
        """Check if bundle is in R^2_+ (both components non-negative)."""
        return self.x >= 0 and self.y >= 0

    def is_strictly_positive(self) -> bool:
        """Check if bundle is in R^2_++ (both components strictly positive)."""
        return self.x > 0 and self.y > 0

    def dominates(self, other: Bundle) -> bool:
        """
        Check if this bundle weakly dominates another (at least as much of everything).

        Formally: self >= other iff self.x >= other.x and self.y >= other.y
        """
        return self.x >= other.x and self.y >= other.y

    def strictly_dominates(self, other: Bundle) -> bool:
        """
        Check if this bundle strictly dominates another (more of everything).

        Formally: self > other iff self.x > other.x and self.y > other.y
        """
        return self.x > other.x and self.y > other.y

    @staticmethod
    def zero() -> Bundle:
        """Return the zero bundle (origin)."""
        return Bundle(0.0, 0.0)
