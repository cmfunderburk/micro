"""
Preference representations and utility functions.

This module implements utility functions that represent agent preferences.
For the MVP, we focus on Cobb-Douglas preferences, which are:
- Monotonic (more is better)
- Strictly convex (preference for variety)
- Homothetic (indifference curves are radial expansions)

Reference: Kreps I, Ch 2; theoretical-foundations.md
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import math

from microecon.bundle import Bundle


class Preferences(ABC):
    """
    Abstract base class for preference representations.

    Preferences can be represented by a utility function u: R^2_+ -> R
    such that bundle a is preferred to bundle b iff u(a) > u(b).
    """

    @abstractmethod
    def utility(self, bundle: Bundle) -> float:
        """Compute utility of a bundle."""
        pass

    @abstractmethod
    def marginal_rate_of_substitution(self, bundle: Bundle) -> float:
        """
        Compute MRS at a bundle: -dy/dx along indifference curve.

        MRS = MU_x / MU_y = rate at which agent trades y for x at margin.
        """
        pass

    def prefers(self, a: Bundle, b: Bundle) -> bool:
        """Check if bundle a is strictly preferred to bundle b."""
        return self.utility(a) > self.utility(b)

    def indifferent(self, a: Bundle, b: Bundle, tol: float = 1e-9) -> bool:
        """Check if agent is indifferent between bundles a and b."""
        return abs(self.utility(a) - self.utility(b)) < tol


@dataclass(frozen=True)
class CobbDouglas(Preferences):
    """
    Cobb-Douglas preferences: u(x, y) = x^alpha * y^(1-alpha)

    Properties:
    - alpha in (0, 1) determines relative preference for good x vs y
    - Monotonic: more of either good increases utility
    - Strictly convex: MRS is strictly decreasing along indifference curve
    - Homothetic: optimal expenditure shares are constant (alpha on x, 1-alpha on y)

    The parameter alpha can be interpreted as:
    - Budget share spent on good x at any price ratio
    - Relative importance of good x in consumption

    Reference: Kreps I, Ch 2, Ch 3 (demand functions)
    """
    alpha: float

    def __post_init__(self) -> None:
        if not 0 < self.alpha < 1:
            raise ValueError(f"alpha must be in (0, 1), got {self.alpha}")

    def utility(self, bundle: Bundle) -> float:
        """
        Compute Cobb-Douglas utility: u(x, y) = x^alpha * y^(1-alpha)

        Note: Returns 0 if either component is 0 (boundary of commodity space).
        """
        if bundle.x <= 0 or bundle.y <= 0:
            return 0.0
        return (bundle.x ** self.alpha) * (bundle.y ** (1 - self.alpha))

    def log_utility(self, bundle: Bundle) -> float:
        """
        Compute log utility: ln(u) = alpha * ln(x) + (1-alpha) * ln(y)

        This monotonic transformation is often more convenient for optimization.
        Returns -inf if either component is non-positive.
        """
        if bundle.x <= 0 or bundle.y <= 0:
            return float('-inf')
        return self.alpha * math.log(bundle.x) + (1 - self.alpha) * math.log(bundle.y)

    def marginal_rate_of_substitution(self, bundle: Bundle) -> float:
        """
        Compute MRS for Cobb-Douglas: MRS = (alpha / (1-alpha)) * (y / x)

        At the optimum, MRS = price ratio p_x / p_y.
        """
        if bundle.x <= 0:
            return float('inf')
        if bundle.y <= 0:
            return 0.0
        return (self.alpha / (1 - self.alpha)) * (bundle.y / bundle.x)

    def marshallian_demand(self, income: float, p_x: float, p_y: float) -> Bundle:
        """
        Compute optimal consumption bundle given income and prices.

        For Cobb-Douglas, demand functions are:
        - x* = alpha * income / p_x
        - y* = (1 - alpha) * income / p_y

        Reference: Kreps I, Ch 3.4 (Lagrangian solution)
        """
        if income < 0 or p_x <= 0 or p_y <= 0:
            raise ValueError("Income must be non-negative, prices must be positive")

        x_star = self.alpha * income / p_x
        y_star = (1 - self.alpha) * income / p_y
        return Bundle(x_star, y_star)

    def indirect_utility(self, income: float, p_x: float, p_y: float) -> float:
        """
        Compute indirect utility: maximum utility achievable at given income and prices.

        V(p, m) = u(x*(p, m), y*(p, m))
        """
        optimal_bundle = self.marshallian_demand(income, p_x, p_y)
        return self.utility(optimal_bundle)
