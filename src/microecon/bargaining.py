"""
Bargaining solutions for bilateral exchange.

This module implements bargaining solutions for two agents with Cobb-Douglas
preferences in a pure exchange economy:

1. Nash Bargaining Solution (axiomatic approach)
   - Characterized by Pareto efficiency, symmetry, IIA, scale invariance
   - Maximizes Nash product: (u1 - d1)(u2 - d2)
   - Reference: O&R-B Ch 2, Kreps II Ch 23

2. Rubinstein Alternating Offers (strategic approach)
   - Unique Subgame Perfect Equilibrium with immediate agreement
   - Proposer advantage: first-mover gets larger share
   - Patience = bargaining power: higher δ → larger share
   - Converges to Nash as δ → 1
   - Reference: O&R-B Ch 3

The disagreement point is each agent's utility from their endowment
(no trade = consume own endowment).

Reference: theoretical-foundations.md
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
import math

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import Agent, AgentType

if TYPE_CHECKING:
    pass


@dataclass
class BargainingOutcome:
    """
    Result of a bargaining process.

    Attributes:
        allocation_1: Final bundle for agent 1
        allocation_2: Final bundle for agent 2
        utility_1: Agent 1's utility at outcome
        utility_2: Agent 2's utility at outcome
        gains_1: Agent 1's utility gain over disagreement point
        gains_2: Agent 2's utility gain over disagreement point
        trade_occurred: Whether any trade happened
    """
    allocation_1: Bundle
    allocation_2: Bundle
    utility_1: float
    utility_2: float
    gains_1: float
    gains_2: float
    trade_occurred: bool

    @property
    def total_gains(self) -> float:
        """Total gains from trade."""
        return self.gains_1 + self.gains_2


def nash_bargaining_solution(
    prefs_1: CobbDouglas,
    endowment_1: Bundle,
    prefs_2: CobbDouglas,
    endowment_2: Bundle,
) -> BargainingOutcome:
    """
    Compute the Nash bargaining solution for two-agent exchange.

    For Cobb-Douglas preferences, the NBS has a closed-form solution.
    The key insight is that we can work in log-utility space where the
    problem becomes separable.

    The aggregate endowment is W = e1 + e2. The NBS allocation (x1, y1), (x2, y2)
    maximizes:
        [u1(x1, y1) - u1(e1)] * [u2(x2, y2) - u2(e2)]
    subject to:
        (x1, y1) + (x2, y2) = W
        u1(x1, y1) >= u1(e1), u2(x2, y2) >= u2(e2)  (individual rationality)

    For Cobb-Douglas with u_i = x^{alpha_i} * y^{1-alpha_i}, the solution is:

    First, compute disagreement utilities:
        d1 = u1(e1), d2 = u2(e2)

    The efficient frontier (Pareto set) for Cobb-Douglas is characterized by
    equal MRS: (alpha1/(1-alpha1))*(y1/x1) = (alpha2/(1-alpha2))*(y2/x2)

    The NBS picks the point on this frontier maximizing the Nash product.

    Args:
        prefs_1: Agent 1's Cobb-Douglas preferences
        endowment_1: Agent 1's initial endowment
        prefs_2: Agent 2's Cobb-Douglas preferences
        endowment_2: Agent 2's initial endowment

    Returns:
        BargainingOutcome with the Nash bargaining solution
    """
    # Total endowment (feasibility constraint)
    W_x = endowment_1.x + endowment_2.x
    W_y = endowment_1.y + endowment_2.y

    # Disagreement point: utility from consuming own endowment
    d1 = prefs_1.utility(endowment_1)
    d2 = prefs_2.utility(endowment_2)

    # Check for degenerate cases
    if W_x <= 0 or W_y <= 0:
        # No goods to trade
        return BargainingOutcome(
            allocation_1=endowment_1,
            allocation_2=endowment_2,
            utility_1=d1,
            utility_2=d2,
            gains_1=0.0,
            gains_2=0.0,
            trade_occurred=False,
        )

    # For Cobb-Douglas, the NBS allocation can be computed using the
    # characterization that at the solution, each agent receives a share
    # of each good that reflects their bargaining power and preferences.
    #
    # With equal bargaining power (symmetric NBS), we can use the result
    # that the solution equates the product of marginal utilities weighted
    # by the disagreement utilities.
    #
    # For the symmetric NBS with Cobb-Douglas, we use numerical optimization
    # on the log Nash product.

    allocation_1, allocation_2 = _solve_nash_cobb_douglas(
        prefs_1.alpha, prefs_2.alpha, W_x, W_y, d1, d2
    )

    u1 = prefs_1.utility(allocation_1)
    u2 = prefs_2.utility(allocation_2)

    # Verify individual rationality
    if u1 < d1 - 1e-9 or u2 < d2 - 1e-9:
        # No mutually beneficial trade exists
        return BargainingOutcome(
            allocation_1=endowment_1,
            allocation_2=endowment_2,
            utility_1=d1,
            utility_2=d2,
            gains_1=0.0,
            gains_2=0.0,
            trade_occurred=False,
        )

    return BargainingOutcome(
        allocation_1=allocation_1,
        allocation_2=allocation_2,
        utility_1=u1,
        utility_2=u2,
        gains_1=u1 - d1,
        gains_2=u2 - d2,
        trade_occurred=True,
    )


def asymmetric_nash_bargaining_solution(
    prefs_1: CobbDouglas,
    endowment_1: Bundle,
    prefs_2: CobbDouglas,
    endowment_2: Bundle,
    weight_1: float = 0.5,
    weight_2: float = 0.5,
) -> BargainingOutcome:
    """
    Compute the asymmetric Nash bargaining solution for two-agent exchange.

    The asymmetric Nash solution generalizes the symmetric Nash solution by
    allowing different bargaining power weights for each player. It maximizes:

        (u1 - d1)^w1 * (u2 - d2)^w2

    subject to Pareto efficiency and individual rationality.

    When w1 = w2, this reduces to the symmetric Nash solution.

    This is the solution to which Rubinstein alternating-offers converges
    for general preferences, with weights derived from patience parameters.
    See Binmore, Rubinstein, Wolinsky (1986).

    Reference: O&R-B Chapter 4, Section 4.4

    Args:
        prefs_1: Agent 1's Cobb-Douglas preferences
        endowment_1: Agent 1's initial endowment
        prefs_2: Agent 2's Cobb-Douglas preferences
        endowment_2: Agent 2's initial endowment
        weight_1: Agent 1's bargaining power weight (default 0.5)
        weight_2: Agent 2's bargaining power weight (default 0.5)

    Returns:
        BargainingOutcome with the asymmetric Nash bargaining solution
    """
    # Total endowment (feasibility constraint)
    W_x = endowment_1.x + endowment_2.x
    W_y = endowment_1.y + endowment_2.y

    # Disagreement point: utility from consuming own endowment
    d1 = prefs_1.utility(endowment_1)
    d2 = prefs_2.utility(endowment_2)

    # Check for degenerate cases
    if W_x <= 0 or W_y <= 0:
        return BargainingOutcome(
            allocation_1=endowment_1,
            allocation_2=endowment_2,
            utility_1=d1,
            utility_2=d2,
            gains_1=0.0,
            gains_2=0.0,
            trade_occurred=False,
        )

    # Solve for asymmetric Nash allocation
    allocation_1, allocation_2 = _solve_nash_cobb_douglas(
        prefs_1.alpha, prefs_2.alpha, W_x, W_y, d1, d2, weight_1, weight_2
    )

    u1 = prefs_1.utility(allocation_1)
    u2 = prefs_2.utility(allocation_2)

    # Verify individual rationality
    if u1 < d1 - 1e-9 or u2 < d2 - 1e-9:
        return BargainingOutcome(
            allocation_1=endowment_1,
            allocation_2=endowment_2,
            utility_1=d1,
            utility_2=d2,
            gains_1=0.0,
            gains_2=0.0,
            trade_occurred=False,
        )

    return BargainingOutcome(
        allocation_1=allocation_1,
        allocation_2=allocation_2,
        utility_1=u1,
        utility_2=u2,
        gains_1=u1 - d1,
        gains_2=u2 - d2,
        trade_occurred=True,
    )


def compute_brw_weights(delta_1: float, delta_2: float) -> tuple[float, float]:
    """
    Compute asymmetric Nash bargaining weights from discount factors.

    Binmore, Rubinstein, and Wolinsky (1986) showed that the Rubinstein
    alternating-offers SPE converges to the asymmetric Nash solution with
    weights derived from patience:

        w1 = ln(δ2) / (ln(δ1) + ln(δ2))
        w2 = ln(δ1) / (ln(δ1) + ln(δ2))

    Note the counterintuitive formula: w1 uses δ2 in the numerator!
    This means the MORE patient player (higher δ) gets GREATER bargaining power.

    Reference: O&R-B Chapter 4, Section 4.4.4

    Args:
        delta_1: Agent 1's discount factor (0 < δ1 < 1)
        delta_2: Agent 2's discount factor (0 < δ2 < 1)

    Returns:
        (weight_1, weight_2) tuple of bargaining power weights

    Raises:
        ValueError: If discount factors not in (0, 1)
    """
    if not (0 < delta_1 < 1):
        raise ValueError(f"delta_1 must be in (0, 1), got {delta_1}")
    if not (0 < delta_2 < 1):
        raise ValueError(f"delta_2 must be in (0, 1), got {delta_2}")

    # Both ln(δ) values are negative since 0 < δ < 1
    ln_d1 = math.log(delta_1)
    ln_d2 = math.log(delta_2)

    # BRW formula: w1 = ln(δ2) / (ln(δ1) + ln(δ2))
    denom = ln_d1 + ln_d2
    weight_1 = ln_d2 / denom
    weight_2 = ln_d1 / denom

    return weight_1, weight_2


def _solve_nash_cobb_douglas(
    alpha1: float,
    alpha2: float,
    W_x: float,
    W_y: float,
    d1: float,
    d2: float,
    weight1: float = 0.5,
    weight2: float = 0.5,
) -> tuple[Bundle, Bundle]:
    """
    Solve for (asymmetric) Nash bargaining allocation with Cobb-Douglas preferences.

    Uses golden section search for efficient unimodal optimization.
    The Nash product with Cobb-Douglas utilities is quasiconcave,
    so golden section search converges to the global optimum.

    Strategy:
    1. Define objective: for given x1, find optimal y1, return Nash product
    2. Find feasible bounds where IR constraints can be satisfied
    3. Use golden section search over x1 to find the optimum

    Args:
        alpha1, alpha2: Cobb-Douglas preference parameters
        W_x, W_y: Total endowments of goods x and y
        d1, d2: Disagreement utilities
        weight1, weight2: Bargaining power weights (default 0.5, 0.5 for symmetric Nash)
    """
    # Small epsilon for numerical stability
    eps = min(1e-6, W_x * 1e-6, W_y * 1e-6)

    def objective(x1: float) -> float:
        """(Asymmetric) Nash product maximized over y1 for given x1."""
        if x1 <= eps or x1 >= W_x - eps:
            return -float('inf')
        x2 = W_x - x1
        _, np_val = _optimize_y1(alpha1, alpha2, x1, x2, W_y, d1, d2, eps, weight1, weight2)
        return np_val

    # Find feasible bounds for x1 where a valid allocation exists.
    # The issue is that golden section search can fail if it starts in
    # an infeasible region. We first find any feasible point, then expand.

    # Step 1: Find any feasible point by sampling across the range
    feasible_point = None
    for i in range(1, 20):
        test_x = i * W_x / 20
        if objective(test_x) > -float('inf'):
            feasible_point = test_x
            break

    if feasible_point is None:
        # No feasible region found - return equal split as fallback
        return (Bundle(W_x / 2, W_y / 2), Bundle(W_x / 2, W_y / 2))

    # Step 2: Binary search for lower bound of feasible region
    lo, hi = eps, feasible_point
    for _ in range(30):
        mid = (lo + hi) / 2
        if objective(mid) > -float('inf'):
            hi = mid
        else:
            lo = mid
    feasible_lower = hi

    # Step 3: Binary search for upper bound of feasible region
    lo, hi = feasible_point, W_x - eps
    for _ in range(30):
        mid = (lo + hi) / 2
        if objective(mid) > -float('inf'):
            lo = mid
        else:
            hi = mid
    feasible_upper = lo

    # Golden section search over x1 within feasible bounds
    phi = (1 + math.sqrt(5)) / 2
    a, b = feasible_lower, feasible_upper

    c = b - (b - a) / phi
    d_pt = a + (b - a) / phi

    # 60 iterations gives ~1e-13 relative precision
    for _ in range(60):
        if objective(c) > objective(d_pt):
            b = d_pt
        else:
            a = c
        c = b - (b - a) / phi
        d_pt = a + (b - a) / phi

    best_x1 = (a + b) / 2
    x2 = W_x - best_x1
    best_y1, _ = _optimize_y1(alpha1, alpha2, best_x1, x2, W_y, d1, d2, eps, weight1, weight2)

    return (Bundle(best_x1, best_y1), Bundle(x2, W_y - best_y1))


def _optimize_y1(
    alpha1: float,
    alpha2: float,
    x1: float,
    x2: float,
    W_y: float,
    d1: float,
    d2: float,
    eps: float = 1e-6,
    weight1: float = 0.5,
    weight2: float = 0.5,
) -> tuple[float, float]:
    """
    Optimize y1 given x1, x2 to maximize (asymmetric) Nash product.

    For fixed x1, x2, the asymmetric Nash product as a function of y1 is:
    ANP(y1) = (u1 - d1)^w1 * (u2 - d2)^w2

    where u1 = x1^a1 * y1^(1-a1), u2 = x2^a2 * (W_y - y1)^(1-a2)

    We use golden section search for unimodal optimization.

    Args:
        alpha1, alpha2: Cobb-Douglas preference parameters
        x1, x2: Good x allocations (fixed)
        W_y: Total good y to allocate
        d1, d2: Disagreement utilities
        eps: Small value for numerical bounds. Adapts to small endowments.
        weight1, weight2: Bargaining power weights (default 0.5, 0.5 for symmetric Nash)
    """
    # Ensure valid search interval even for small W_y
    bound_eps = min(eps, W_y * 0.01)
    if bound_eps * 2 >= W_y:
        # W_y too small for meaningful optimization
        return W_y / 2, -float('inf')

    def nash_product(y1: float) -> float:
        if y1 <= 0 or y1 >= W_y:
            return -float('inf')
        y2 = W_y - y1

        u1 = (x1 ** alpha1) * (y1 ** (1 - alpha1))
        u2 = (x2 ** alpha2) * (y2 ** (1 - alpha2))

        if u1 <= d1 or u2 <= d2:
            return -float('inf')

        # Asymmetric Nash product: (u1 - d1)^w1 * (u2 - d2)^w2
        return ((u1 - d1) ** weight1) * ((u2 - d2) ** weight2)

    # Golden section search
    phi = (1 + math.sqrt(5)) / 2
    a, b = bound_eps, W_y - bound_eps

    c = b - (b - a) / phi
    d_pt = a + (b - a) / phi

    for _ in range(50):  # Sufficient iterations for convergence
        if nash_product(c) > nash_product(d_pt):
            b = d_pt
        else:
            a = c

        c = b - (b - a) / phi
        d_pt = a + (b - a) / phi

    y1_opt = (a + b) / 2
    return y1_opt, nash_product(y1_opt)


def compute_nash_surplus(
    observer_type: AgentType,
    target_type: AgentType,
) -> float:
    """
    Compute expected surplus from Nash bargaining between two agents.

    This is used for search evaluation: agents evaluate potential trade
    partners by computing the expected gains from trade.

    Args:
        observer_type: Observable type of the evaluating agent
        target_type: Observable type of the potential partner

    Returns:
        Expected surplus for the observer from Nash bargaining
    """
    outcome = nash_bargaining_solution(
        observer_type.preferences,
        observer_type.endowment,
        target_type.preferences,
        target_type.endowment,
    )
    return outcome.gains_1


def compute_mutual_surplus(
    type_1: AgentType,
    type_2: AgentType,
) -> tuple[float, float]:
    """
    Compute surplus for both agents from Nash bargaining.

    Returns:
        Tuple of (agent_1_surplus, agent_2_surplus)
    """
    outcome = nash_bargaining_solution(
        type_1.preferences,
        type_1.endowment,
        type_2.preferences,
        type_2.endowment,
    )
    return outcome.gains_1, outcome.gains_2


# =============================================================================
# Rubinstein Alternating Offers
# =============================================================================


def rubinstein_share(
    delta1: float,
    delta2: float,
    proposer: int = 1,
) -> tuple[float, float]:
    """
    Compute Rubinstein SPE surplus shares.

    In Rubinstein's alternating-offers bargaining game, players make offers
    alternately until one accepts. With discount factors δ₁ and δ₂, there
    is a unique Subgame Perfect Equilibrium with immediate agreement.

    The SPE shares of the surplus are:
    - If player 1 proposes first:
        share_1 = (1 - δ₂) / (1 - δ₁δ₂)
        share_2 = δ₂(1 - δ₁) / (1 - δ₁δ₂)

    - If player 2 proposes first:
        share_1 = δ₁(1 - δ₂) / (1 - δ₁δ₂)
        share_2 = (1 - δ₁) / (1 - δ₁δ₂)

    Properties:
    - Proposer advantage: first-mover gets more
    - Patience = power: higher δ → larger share
    - As δ → 1: converges to 50-50 (Nash limit)
    - Equal δ: proposer gets 1/(1+δ), responder gets δ/(1+δ)

    Reference: O&R-B Chapter 3, Theorem 3.4

    Args:
        delta1: Player 1's discount factor (0 < δ₁ < 1)
        delta2: Player 2's discount factor (0 < δ₂ < 1)
        proposer: Which player proposes first (1 or 2)

    Returns:
        (share_1, share_2) where shares sum to 1

    Raises:
        ValueError: If discount factors not in (0, 1) or proposer not 1 or 2
    """
    if not (0 < delta1 < 1):
        raise ValueError(f"delta1 must be in (0, 1), got {delta1}")
    if not (0 < delta2 < 1):
        raise ValueError(f"delta2 must be in (0, 1), got {delta2}")
    if proposer not in (1, 2):
        raise ValueError(f"proposer must be 1 or 2, got {proposer}")

    denom = 1 - delta1 * delta2

    if proposer == 1:
        # Player 1 proposes first
        share_1 = (1 - delta2) / denom
        share_2 = delta2 * (1 - delta1) / denom
    else:
        # Player 2 proposes first
        share_1 = delta1 * (1 - delta2) / denom
        share_2 = (1 - delta1) / denom

    return share_1, share_2


def rubinstein_bargaining_solution(
    prefs_1: CobbDouglas,
    endowment_1: Bundle,
    prefs_2: CobbDouglas,
    endowment_2: Bundle,
    delta_1: float,
    delta_2: float,
    proposer: int = 1,
) -> BargainingOutcome:
    """
    Compute the Rubinstein bargaining solution for two-agent exchange.

    For exchange economies with non-linear utility (like Cobb-Douglas),
    Binmore, Rubinstein, and Wolinsky (1986) showed that the alternating-offers
    SPE converges to the ASYMMETRIC Nash bargaining solution with weights
    derived from patience:

        w1 = ln(δ2) / (ln(δ1) + ln(δ2))
        w2 = ln(δ1) / (ln(δ1) + ln(δ2))

    The MORE patient player (higher δ) gets GREATER bargaining power.

    Note: The proposer parameter is retained for API compatibility and logging,
    but with asymmetric Nash, the proposer identity's effect vanishes as δ → 1.
    The key determinant of bargaining power is patience, not first-mover status.

    Reference: O&R-B Chapter 4, Section 4.4; BRW (1986) RAND Journal

    Args:
        prefs_1: Agent 1's Cobb-Douglas preferences
        endowment_1: Agent 1's initial endowment
        prefs_2: Agent 2's Cobb-Douglas preferences
        endowment_2: Agent 2's initial endowment
        delta_1: Agent 1's discount factor (0 < δ₁ < 1)
        delta_2: Agent 2's discount factor (0 < δ₂ < 1)
        proposer: Which agent proposes first (retained for compatibility/logging)

    Returns:
        BargainingOutcome with the Rubinstein bargaining solution
    """
    # Compute BRW weights from discount factors
    weight_1, weight_2 = compute_brw_weights(delta_1, delta_2)

    # Use asymmetric Nash solution with patience-derived weights
    return asymmetric_nash_bargaining_solution(
        prefs_1, endowment_1, prefs_2, endowment_2, weight_1, weight_2
    )


def _solve_rubinstein_allocation(
    alpha1: float,
    alpha2: float,
    W_x: float,
    W_y: float,
    d1: float,
    d2: float,
    target_share_1: float,
    target_share_2: float,
) -> tuple[Bundle, Bundle]:
    """
    Find Pareto-efficient allocation achieving target surplus shares.

    We parameterize the Pareto frontier and search for the point where
    the ratio of surplus gains matches the Rubinstein shares.

    For Cobb-Douglas, we search over x1 (agent 1's allocation of good x),
    finding the Pareto-efficient y1 for each x1, and selecting the (x1, y1)
    where gains_1 / gains_2 ≈ target_share_1 / target_share_2.
    """
    eps = min(1e-6, W_x * 1e-6, W_y * 1e-6)

    def surplus_ratio_error(x1: float) -> float:
        """Error in achieving target surplus ratio."""
        if x1 <= eps or x1 >= W_x - eps:
            return float('inf')

        x2 = W_x - x1

        # Find Pareto-efficient y1 using MRS equality
        # For Cobb-Douglas: MRS = (α/(1-α)) * (y/x)
        # At Pareto optimum: MRS_1 = MRS_2
        # => (α1/(1-α1)) * (y1/x1) = (α2/(1-α2)) * (y2/x2)

        # Solve for y1 given x1, x2, and W_y = y1 + y2
        # Let a = α1/(1-α1), b = α2/(1-α2)
        # a * y1 / x1 = b * (W_y - y1) / x2
        # a * y1 * x2 = b * (W_y - y1) * x1
        # a * y1 * x2 = b * W_y * x1 - b * y1 * x1
        # y1 * (a * x2 + b * x1) = b * W_y * x1
        # y1 = (b * W_y * x1) / (a * x2 + b * x1)

        a = alpha1 / (1 - alpha1) if alpha1 < 1 else 1e10
        b = alpha2 / (1 - alpha2) if alpha2 < 1 else 1e10

        denom = a * x2 + b * x1
        if denom <= 0:
            return float('inf')

        y1 = (b * W_y * x1) / denom
        y2 = W_y - y1

        if y1 <= 0 or y2 <= 0:
            return float('inf')

        # Compute utilities and gains
        u1 = (x1 ** alpha1) * (y1 ** (1 - alpha1))
        u2 = (x2 ** alpha2) * (y2 ** (1 - alpha2))

        gain1 = u1 - d1
        gain2 = u2 - d2

        if gain1 <= 0 or gain2 <= 0:
            return float('inf')

        # We want gain1/gain2 = target_share_1/target_share_2
        # Error = (gain1/total - target_share_1)^2
        total_gain = gain1 + gain2
        actual_share_1 = gain1 / total_gain

        return (actual_share_1 - target_share_1) ** 2

    # Golden section search to minimize surplus ratio error
    phi = (1 + math.sqrt(5)) / 2
    a, b = eps, W_x - eps

    c = b - (b - a) / phi
    d_pt = a + (b - a) / phi

    for _ in range(60):
        if surplus_ratio_error(c) < surplus_ratio_error(d_pt):
            b = d_pt
        else:
            a = c
        c = b - (b - a) / phi
        d_pt = a + (b - a) / phi

    best_x1 = (a + b) / 2
    x2 = W_x - best_x1

    # Compute Pareto-efficient y1
    a_coef = alpha1 / (1 - alpha1) if alpha1 < 1 else 1e10
    b_coef = alpha2 / (1 - alpha2) if alpha2 < 1 else 1e10
    y1 = (b_coef * W_y * best_x1) / (a_coef * x2 + b_coef * best_x1)

    return Bundle(best_x1, y1), Bundle(x2, W_y - y1)


def compute_rubinstein_surplus(
    observer_type: AgentType,
    target_type: AgentType,
    observer_delta: float,
    target_delta: float,
    observer_is_proposer: bool = True,
) -> float:
    """
    Compute expected surplus from Rubinstein bargaining between two agents.

    With the BRW (1986) formulation, the Rubinstein solution for exchange economies
    converges to asymmetric Nash with patience-derived weights. The proposer
    identity parameter is retained for API compatibility but no longer affects
    the outcome - bargaining power is determined by patience (discount factors).

    Args:
        observer_type: Observable type of the evaluating agent
        target_type: Observable type of the potential partner
        observer_delta: Observer's discount factor
        target_delta: Target's discount factor
        observer_is_proposer: Retained for API compatibility (no longer affects outcome)

    Returns:
        Expected surplus for the observer from Rubinstein bargaining
    """
    # Note: proposer parameter retained for compatibility but no longer used
    outcome = rubinstein_bargaining_solution(
        observer_type.preferences,
        observer_type.endowment,
        target_type.preferences,
        target_type.endowment,
        observer_delta,
        target_delta,
    )
    return outcome.gains_1


def execute_trade(agent1: Agent, agent2: Agent) -> BargainingOutcome:
    """
    Execute Nash bargaining between two agents, updating their endowments.

    This modifies the agents' endowments to reflect the bargaining outcome.

    Note: This legacy function always uses Nash bargaining. For protocol-aware
    trading, use BargainingProtocol.execute() instead.

    Args:
        agent1: First agent
        agent2: Second agent

    Returns:
        BargainingOutcome describing what happened
    """
    outcome = nash_bargaining_solution(
        agent1.preferences,
        agent1.endowment,
        agent2.preferences,
        agent2.endowment,
    )

    if outcome.trade_occurred:
        agent1.endowment = outcome.allocation_1
        agent2.endowment = outcome.allocation_2

    return outcome


# =============================================================================
# Bargaining Protocol Abstraction
# =============================================================================


class BargainingProtocol(ABC):
    """
    Abstract base class for bargaining protocols.

    Different protocols implement different approaches to bilateral bargaining:
    - Nash: Axiomatic solution maximizing Nash product (symmetric)
    - Rubinstein: Strategic alternating-offers with first-mover advantage

    This abstraction enables the platform's core value proposition:
    comparing outcomes under different institutional rules.

    Usage:
        protocol = NashBargainingProtocol()
        # or
        protocol = RubinsteinBargainingProtocol()

        outcome = protocol.solve(agent1, agent2)
        surplus = protocol.compute_expected_surplus(agent1, agent2)
    """

    @abstractmethod
    def solve(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
    ) -> BargainingOutcome:
        """
        Compute bargaining outcome between two agents.

        Args:
            agent1: First agent
            agent2: Second agent
            proposer: Which agent proposes first (relevant for asymmetric protocols)

        Returns:
            BargainingOutcome with allocations and gains
        """
        pass

    @abstractmethod
    def compute_expected_surplus(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
    ) -> float:
        """
        Compute expected surplus for agent1 from potential trade.

        Used for search evaluation: agents assess potential partners by
        their expected gains from trade.

        Args:
            agent1: Evaluating agent
            agent2: Potential trade partner
            proposer: Which agent would propose first

        Returns:
            Expected surplus for agent1
        """
        pass

    def execute(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
    ) -> BargainingOutcome:
        """
        Execute bargaining and update agent endowments.

        This is a convenience method that calls solve() and applies the
        outcome to the agents' endowments.

        Args:
            agent1: First agent
            agent2: Second agent
            proposer: Which agent proposes first

        Returns:
            BargainingOutcome describing what happened
        """
        outcome = self.solve(agent1, agent2, proposer)

        if outcome.trade_occurred:
            agent1.endowment = outcome.allocation_1
            agent2.endowment = outcome.allocation_2

        return outcome


class NashBargainingProtocol(BargainingProtocol):
    """
    Nash Bargaining Solution - axiomatic approach.

    Implements the symmetric Nash bargaining solution that maximizes
    the Nash product (u1 - d1)(u2 - d2) subject to Pareto efficiency.

    Properties:
    - Symmetric: Outcome depends only on preferences and endowments
    - No first-mover advantage: proposer parameter is ignored
    - Pareto efficient allocation on contract curve

    Reference: O&R-B Chapter 2, theoretical-foundations.md
    """

    def solve(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
    ) -> BargainingOutcome:
        """Compute Nash bargaining solution. Proposer is ignored (symmetric)."""
        return nash_bargaining_solution(
            agent1.preferences,
            agent1.endowment,
            agent2.preferences,
            agent2.endowment,
        )

    def compute_expected_surplus(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
    ) -> float:
        """Compute expected surplus for agent1. Proposer is ignored."""
        # Create observable types from agents (full information case)
        type1 = AgentType(agent1.preferences, agent1.endowment)
        type2 = AgentType(agent2.preferences, agent2.endowment)
        return compute_nash_surplus(type1, type2)


class RubinsteinBargainingProtocol(BargainingProtocol):
    """
    Rubinstein Alternating Offers - strategic approach.

    For exchange economies with Cobb-Douglas preferences, Binmore, Rubinstein,
    and Wolinsky (1986) showed that the alternating-offers SPE converges to
    the ASYMMETRIC Nash bargaining solution with patience-derived weights:

        w1 = ln(δ2) / (ln(δ1) + ln(δ2))
        w2 = ln(δ1) / (ln(δ1) + ln(δ2))

    Properties:
    - Patience = power: Higher discount factor → larger share
    - Equal δ → symmetric Nash (equal bargaining power)
    - Proposer identity no longer affects outcome (with asymmetric Nash)

    The proposer parameter is retained for API compatibility and logging
    but does not affect outcomes under the BRW formulation.

    Reference: O&R-B Chapter 4, Section 4.4; BRW (1986) RAND Journal
    """

    def solve(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
    ) -> BargainingOutcome:
        """
        Compute Rubinstein bargaining solution using BRW asymmetric Nash.

        Args:
            agent1: First agent
            agent2: Second agent
            proposer: Retained for API compatibility (no longer affects outcome)

        Returns:
            BargainingOutcome with asymmetric Nash allocation based on patience
        """
        return rubinstein_bargaining_solution(
            agent1.preferences,
            agent1.endowment,
            agent2.preferences,
            agent2.endowment,
            agent1.discount_factor,
            agent2.discount_factor,
        )

    def compute_expected_surplus(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
    ) -> float:
        """
        Compute expected surplus for agent1 under Rubinstein/BRW.

        With asymmetric Nash, the surplus depends on the ratio of patience
        (discount factors), not on proposer identity.

        Args:
            agent1: Evaluating agent
            agent2: Potential trade partner
            proposer: Retained for API compatibility (no longer affects outcome)

        Returns:
            Expected surplus for agent1
        """
        # Create observable types from agents (full information case)
        type1 = AgentType(agent1.preferences, agent1.endowment)
        type2 = AgentType(agent2.preferences, agent2.endowment)

        return compute_rubinstein_surplus(
            type1,
            type2,
            agent1.discount_factor,
            agent2.discount_factor,
        )
