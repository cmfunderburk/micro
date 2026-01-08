"""
Bargaining solutions for bilateral exchange.

This module implements bargaining solutions for two agents with Cobb-Douglas
preferences in a pure exchange economy:

1. Nash Bargaining Solution (symmetric) — O&R Ch 2
   - Axiomatic: Pareto efficiency, symmetry, IIA, scale invariance
   - Maximizes Nash product: (u1 - d1)(u2 - d2)
   - Power source: None (equal split)

2. Rubinstein / Nash (Patience) — O&R Ch 3, BRW (1986)
   - BRW limit of alternating-offers SPE
   - Power source: Patience (discount factors)
   - Higher δ → larger share; equal δ → symmetric Nash

3. Asymmetric Nash (Power) — O&R Ch 2.6
   - Weighted Nash product: (u1 - d1)^β × (u2 - d2)^(1-β)
   - Power source: Exogenous bargaining_power attribute
   - β = w1 / (w1 + w2)

4. Take-It-Or-Leave-It (TIOLI) — O&R Ch 3
   - Proposer extracts all surplus
   - Power source: Commitment / first-mover advantage
   - Responder at indifference (utility == disagreement)

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

    The feasible region for y1 is constrained by individual rationality:
    - u1(x1, y1) >= d1  =>  y1 >= y1_min
    - u2(x2, W_y - y1) >= d2  =>  y1 <= y1_max

    We first find this feasible region, then use golden section search.

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

    # Find feasible bounds for y1 where IR constraints can be satisfied
    # For u1 = x1^a1 * y1^(1-a1) >= d1:
    #   y1 >= (d1 / x1^a1)^(1/(1-a1)) = y1_min
    # For u2 = x2^a2 * y2^(1-a2) >= d2, y2 = W_y - y1:
    #   y2 >= (d2 / x2^a2)^(1/(1-a2))
    #   y1 <= W_y - (d2 / x2^a2)^(1/(1-a2)) = y1_max

    if x1 <= 0 or x2 <= 0:
        return W_y / 2, -float('inf')

    # Compute y1_min from agent 1's IR constraint
    x1_term = x1 ** alpha1
    if x1_term <= 0 or d1 <= 0:
        y1_min = bound_eps
    else:
        ratio1 = d1 / x1_term
        if ratio1 <= 0:
            y1_min = bound_eps
        else:
            y1_min = ratio1 ** (1 / (1 - alpha1))

    # Compute y1_max from agent 2's IR constraint
    x2_term = x2 ** alpha2
    if x2_term <= 0 or d2 <= 0:
        y1_max = W_y - bound_eps
    else:
        ratio2 = d2 / x2_term
        if ratio2 <= 0:
            y2_min = bound_eps
        else:
            y2_min = ratio2 ** (1 / (1 - alpha2))
        y1_max = W_y - y2_min

    # Clamp to valid range
    y1_min = max(y1_min, bound_eps)
    y1_max = min(y1_max, W_y - bound_eps)

    # If no feasible region exists, return infeasible
    if y1_min >= y1_max:
        return W_y / 2, -float('inf')

    # Golden section search within the feasible region
    phi = (1 + math.sqrt(5)) / 2
    a, b = y1_min, y1_max

    c = b - (b - a) / phi
    d_pt = a + (b - a) / phi

    for _ in range(50):  # Sufficient iterations for convergence
        np_c = nash_product(c)
        np_d = nash_product(d_pt)

        if np_c > np_d:
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
# Take-It-Or-Leave-It (TIOLI) Bargaining
# =============================================================================


def tioli_bargaining_solution(
    prefs_1: CobbDouglas,
    endowment_1: Bundle,
    prefs_2: CobbDouglas,
    endowment_2: Bundle,
    proposer: int = 1,
) -> BargainingOutcome:
    """
    Compute the Take-It-Or-Leave-It (TIOLI) bargaining solution.

    In TIOLI bargaining, the proposer makes a single offer that the responder
    must accept or reject. The optimal strategy for the proposer is to offer
    the responder exactly their disagreement utility (outside option), extracting
    all remaining surplus.

    This is a closed-form solution (not asymmetric Nash with extreme β), which:
    - Ensures responder utility exactly equals disagreement utility
    - Avoids numerical edge cases with β→1
    - Is semantically cleaner and more interpretable

    Properties (O&R Ch 3):
    - Proposer extracts all surplus: No feasible allocation gives proposer more
      while responder ≥ disagreement
    - Responder at indifference: responder_utility == disagreement_utility (within 1e-6)
    - Pareto efficient: Allocation on contract curve
    - Proposer identity matters: Swapping proposer swaps surplus recipient

    For Cobb-Douglas preferences, we find the point on the responder's disagreement
    indifference curve that maximizes proposer utility subject to feasibility.

    Reference: Osborne & Rubinstein, Bargaining and Markets, Chapter 3

    Args:
        prefs_1: Agent 1's Cobb-Douglas preferences
        endowment_1: Agent 1's initial endowment
        prefs_2: Agent 2's Cobb-Douglas preferences
        endowment_2: Agent 2's initial endowment
        proposer: Which agent proposes (1 or 2). Default is 1.

    Returns:
        BargainingOutcome with the TIOLI solution

    Raises:
        ValueError: If proposer not in {1, 2}
    """
    if proposer not in (1, 2):
        raise ValueError(f"proposer must be 1 or 2, got {proposer}")

    # Total endowment (feasibility constraint)
    W_x = endowment_1.x + endowment_2.x
    W_y = endowment_1.y + endowment_2.y

    # Disagreement utilities
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

    # Assign proposer and responder
    if proposer == 1:
        alpha_p, alpha_r = prefs_1.alpha, prefs_2.alpha
        d_r = d2  # Responder's disagreement utility
    else:
        alpha_p, alpha_r = prefs_2.alpha, prefs_1.alpha
        d_r = d1  # Responder's disagreement utility

    # Find optimal allocation using golden section search
    allocation_p, allocation_r = _solve_tioli(alpha_p, alpha_r, W_x, W_y, d_r)

    # Map back to agent 1 and agent 2
    if proposer == 1:
        allocation_1, allocation_2 = allocation_p, allocation_r
    else:
        allocation_1, allocation_2 = allocation_r, allocation_p

    u1 = prefs_1.utility(allocation_1)
    u2 = prefs_2.utility(allocation_2)

    # Verify trade is individually rational for BOTH agents
    # Proposer should gain, responder should be at least at disagreement
    # This catches edge cases where _solve_tioli returns infeasible fallback
    if u1 < d1 - 1e-9 or u2 < d2 - 1e-9:
        # Individual rationality violated - no beneficial trade exists
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


def _solve_tioli(
    alpha_p: float,
    alpha_r: float,
    W_x: float,
    W_y: float,
    d_r: float,
) -> tuple[Bundle, Bundle]:
    """
    Solve for TIOLI allocation where responder gets exactly disagreement utility.

    The responder's bundle (x_r, y_r) must satisfy:
        x_r^alpha_r * y_r^(1-alpha_r) = d_r

    The proposer maximizes:
        (W_x - x_r)^alpha_p * (W_y - y_r)^(1-alpha_p)

    We parameterize by x_r and derive y_r from the indifference curve constraint.

    Args:
        alpha_p: Proposer's Cobb-Douglas alpha
        alpha_r: Responder's Cobb-Douglas alpha
        W_x, W_y: Total endowments
        d_r: Responder's disagreement utility

    Returns:
        (proposer_bundle, responder_bundle)
    """
    eps = min(1e-9, W_x * 1e-9, W_y * 1e-9)

    def responder_y_from_x(x_r: float) -> float:
        """Compute y_r from indifference curve: x_r^alpha_r * y_r^(1-alpha_r) = d_r"""
        if x_r <= 0:
            return float('inf')
        # y_r = (d_r / x_r^alpha_r)^(1/(1-alpha_r))
        ratio = d_r / (x_r ** alpha_r)
        if ratio <= 0:
            return float('inf')
        return ratio ** (1 / (1 - alpha_r))

    def proposer_utility(x_r: float) -> float:
        """Proposer utility given responder gets x_r (and y_r from indifference curve)."""
        y_r = responder_y_from_x(x_r)
        x_p = W_x - x_r
        y_p = W_y - y_r

        # Check feasibility
        if x_p <= 0 or y_p <= 0:
            return -float('inf')

        return (x_p ** alpha_p) * (y_p ** (1 - alpha_p))

    # Find bounds for x_r where a feasible allocation exists
    #
    # The responder's indifference curve has y_r decreasing as x_r increases
    # (downward-sloping). Therefore:
    # - Small x_r → large y_r → small y_p (may violate y_p > 0)
    # - Large x_r → small y_r → large y_p but small x_p (may violate x_p > 0)
    #
    # Lower bound: y_p = W_y - y_r > 0 => y_r < W_y
    #   Find x_r where y_r = W_y: x_r_min = (d_r / W_y^(1-alpha_r))^(1/alpha_r)
    #   For x_r > x_r_min, we have y_r < W_y, so y_p > 0
    #
    # Upper bound: x_p = W_x - x_r > 0 => x_r < W_x

    if d_r <= 0:
        # Responder has zero disagreement utility - they accept anything
        # Give responder minimal allocation
        return (Bundle(W_x - eps, W_y - eps), Bundle(eps, eps))

    # x_r where y_r = W_y (lower limit - below this, y_p would be negative)
    x_r_at_y_limit = (d_r / (W_y ** (1 - alpha_r))) ** (1 / alpha_r) if W_y > 0 else eps

    # Search bounds: x_r from just above y_limit to just below W_x
    x_lower = max(x_r_at_y_limit + eps, eps)
    x_upper = W_x - eps

    if x_upper <= x_lower:
        # No feasible region - return endowment split (no trade beneficial)
        return (Bundle(W_x / 2, W_y / 2), Bundle(W_x / 2, W_y / 2))

    # Golden section search to maximize proposer utility
    phi = (1 + math.sqrt(5)) / 2
    a, b = x_lower, x_upper

    c = b - (b - a) / phi
    d_pt = a + (b - a) / phi

    for _ in range(60):
        if proposer_utility(c) > proposer_utility(d_pt):
            b = d_pt
        else:
            a = c
        c = b - (b - a) / phi
        d_pt = a + (b - a) / phi

    best_x_r = (a + b) / 2
    best_y_r = responder_y_from_x(best_x_r)

    x_p = W_x - best_x_r
    y_p = W_y - best_y_r

    # Clamp to non-negative (numerical precision)
    x_p = max(0.0, x_p)
    y_p = max(0.0, y_p)
    best_x_r = max(0.0, best_x_r)
    best_y_r = max(0.0, best_y_r)

    return (Bundle(x_p, y_p), Bundle(best_x_r, best_y_r))


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


# =============================================================================
# Bargaining Protocol Abstraction
# =============================================================================


class BargainingProtocol(ABC):
    """
    Abstract base class for bargaining protocols.

    Different protocols implement different approaches to bilateral bargaining:
    - Nash: Axiomatic solution maximizing Nash product (symmetric)
    - Rubinstein (BRW): Alternating-offers SPE in the limit, where patience
      (discount factors) determines bargaining power, not proposer identity

    This abstraction enables the platform's core value proposition:
    comparing outcomes under different institutional rules.

    Note: The current Rubinstein implementation uses the Binmore-Rubinstein-
    Wolinsky (1986) limit result. A future extension may add classic finite-δ
    Rubinstein with explicit first-mover advantage.

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
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> BargainingOutcome:
        """
        Compute bargaining outcome between two agents.

        Args:
            agent1: First agent
            agent2: Second agent
            proposer: Which agent proposes first (relevant for asymmetric protocols)
            effective_type_1: Override type for agent1 (for belief-based bargaining)
            effective_type_2: Override type for agent2 (for belief-based bargaining)

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
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> float:
        """
        Compute expected surplus for agent1 from potential trade.

        Used for search evaluation: agents assess potential partners by
        their expected gains from trade.

        Args:
            agent1: Evaluating agent
            agent2: Potential trade partner
            proposer: Which agent would propose first
            effective_type_1: Override type for agent1 (for belief-based evaluation)
            effective_type_2: Override type for agent2 (for belief-based evaluation)

        Returns:
            Expected surplus for agent1
        """
        pass

    def execute(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> BargainingOutcome:
        """
        Execute bargaining and update agent endowments.

        This is a convenience method that calls solve() and applies the
        outcome to the agents' endowments.

        Args:
            agent1: First agent
            agent2: Second agent
            proposer: Which agent proposes first
            effective_type_1: Override type for agent1 (for belief-based bargaining)
            effective_type_2: Override type for agent2 (for belief-based bargaining)

        Returns:
            BargainingOutcome describing what happened
        """
        outcome = self.solve(agent1, agent2, proposer, effective_type_1, effective_type_2)

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
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> BargainingOutcome:
        """Compute Nash bargaining solution. Proposer is ignored (symmetric)."""
        # Use effective types if provided, otherwise use agent's true type
        prefs_1 = effective_type_1.preferences if effective_type_1 else agent1.preferences
        endow_1 = effective_type_1.endowment if effective_type_1 else agent1.endowment
        prefs_2 = effective_type_2.preferences if effective_type_2 else agent2.preferences
        endow_2 = effective_type_2.endowment if effective_type_2 else agent2.endowment

        return nash_bargaining_solution(prefs_1, endow_1, prefs_2, endow_2)

    def compute_expected_surplus(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> float:
        """Compute expected surplus for agent1. Proposer is ignored."""
        # Use effective types if provided, otherwise construct from agent
        type1 = effective_type_1 or AgentType(agent1.preferences, agent1.endowment)
        type2 = effective_type_2 or AgentType(agent2.preferences, agent2.endowment)
        return compute_nash_surplus(type1, type2)


class RubinsteinBargainingProtocol(BargainingProtocol):
    """
    Rubinstein Alternating Offers - strategic approach (BRW limit).

    For exchange economies with Cobb-Douglas preferences, Binmore, Rubinstein,
    and Wolinsky (1986) showed that the alternating-offers SPE converges to
    the ASYMMETRIC Nash bargaining solution with patience-derived weights:

        w1 = ln(δ2) / (ln(δ1) + ln(δ2))
        w2 = ln(δ1) / (ln(δ1) + ln(δ2))

    Properties:
    - Patience = power: Higher discount factor → larger share
    - Equal δ → symmetric Nash (equal bargaining power)
    - Proposer identity no longer affects outcome (in the BRW limit)

    The proposer parameter is retained for API compatibility and logging
    but does not affect outcomes under the BRW formulation.

    Future extension: A ClassicRubinsteinProtocol could implement finite-round
    alternating offers where proposer identity confers first-mover advantage.
    This would enable studying proposer-advantage effects distinct from patience.

    Reference: O&R-B Chapter 4, Section 4.4; BRW (1986) RAND Journal
    """

    def solve(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> BargainingOutcome:
        """
        Compute Rubinstein bargaining solution using BRW asymmetric Nash.

        Args:
            agent1: First agent
            agent2: Second agent
            proposer: Retained for API compatibility (no longer affects outcome)
            effective_type_1: Override type for agent1 (for belief-based bargaining)
            effective_type_2: Override type for agent2 (for belief-based bargaining)

        Returns:
            BargainingOutcome with asymmetric Nash allocation based on patience
        """
        # Use effective types if provided, otherwise use agent's true type
        prefs_1 = effective_type_1.preferences if effective_type_1 else agent1.preferences
        endow_1 = effective_type_1.endowment if effective_type_1 else agent1.endowment
        prefs_2 = effective_type_2.preferences if effective_type_2 else agent2.preferences
        endow_2 = effective_type_2.endowment if effective_type_2 else agent2.endowment

        return rubinstein_bargaining_solution(
            prefs_1, endow_1, prefs_2, endow_2,
            agent1.discount_factor,
            agent2.discount_factor,
        )

    def compute_expected_surplus(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> float:
        """
        Compute expected surplus for agent1 under Rubinstein/BRW.

        With asymmetric Nash, the surplus depends on the ratio of patience
        (discount factors), not on proposer identity.

        Args:
            agent1: Evaluating agent
            agent2: Potential trade partner
            proposer: Retained for API compatibility (no longer affects outcome)
            effective_type_1: Override type for agent1 (for belief-based evaluation)
            effective_type_2: Override type for agent2 (for belief-based evaluation)

        Returns:
            Expected surplus for agent1
        """
        # Use effective types if provided, otherwise construct from agent
        type1 = effective_type_1 or AgentType(agent1.preferences, agent1.endowment)
        type2 = effective_type_2 or AgentType(agent2.preferences, agent2.endowment)

        return compute_rubinstein_surplus(
            type1,
            type2,
            agent1.discount_factor,
            agent2.discount_factor,
        )


class TIOLIBargainingProtocol(BargainingProtocol):
    """
    Take-It-Or-Leave-It Bargaining Protocol.

    In TIOLI, one agent (the proposer) makes a single offer that the other
    (the responder) must accept or reject. The optimal strategy is for the
    proposer to offer the responder exactly their disagreement utility,
    extracting all remaining surplus.

    **Power source**: Commitment / first-mover advantage. The proposer's ability
    to commit to a take-it-or-leave-it offer gives them all the bargaining power.
    Unlike Nash (symmetric) or Rubinstein (patience-based), TIOLI represents
    extreme proposer advantage.

    **Proposer selection**: By default, the agent with the lexicographically
    smaller ID proposes. This is deterministic and reproducible. The proposer
    can be explicitly specified via the `proposer` parameter in solve().

    Future extensions may add:
    - Random proposer selection
    - Endogenous proposer selection (e.g., based on outside options)
    - Alternating proposer across multiple interactions

    Properties (O&R Ch 3):
    - Proposer extracts full surplus
    - Responder at indifference (utility == disagreement utility)
    - Pareto efficient allocation
    - Proposer identity matters (unlike symmetric Nash)

    Reference: Osborne & Rubinstein, Bargaining and Markets, Chapter 3
    """

    def solve(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> BargainingOutcome:
        """
        Compute TIOLI bargaining solution.

        Args:
            agent1: First agent
            agent2: Second agent
            proposer: Which agent proposes. If None, uses lexicographic ID comparison
                (smaller ID proposes). Must be either agent1 or agent2 if specified.
            effective_type_1: Override type for agent1 (for belief-based bargaining)
            effective_type_2: Override type for agent2 (for belief-based bargaining)

        Returns:
            BargainingOutcome with the TIOLI solution
        """
        # Determine proposer
        if proposer is None:
            # Default: lexicographically smaller ID proposes
            proposer_is_1 = agent1.id < agent2.id
        elif proposer is agent1:
            proposer_is_1 = True
        elif proposer is agent2:
            proposer_is_1 = False
        else:
            raise ValueError("proposer must be agent1 or agent2")

        proposer_int = 1 if proposer_is_1 else 2

        # Use effective types if provided, otherwise use agent's true type
        prefs_1 = effective_type_1.preferences if effective_type_1 else agent1.preferences
        endow_1 = effective_type_1.endowment if effective_type_1 else agent1.endowment
        prefs_2 = effective_type_2.preferences if effective_type_2 else agent2.preferences
        endow_2 = effective_type_2.endowment if effective_type_2 else agent2.endowment

        return tioli_bargaining_solution(prefs_1, endow_1, prefs_2, endow_2, proposer_int)

    def compute_expected_surplus(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> float:
        """
        Compute expected surplus for agent1 under TIOLI.

        The surplus depends critically on who proposes:
        - If agent1 proposes: agent1 gets all surplus
        - If agent2 proposes: agent1 gets zero surplus (at disagreement)

        Args:
            agent1: Evaluating agent
            agent2: Potential trade partner
            proposer: Which agent would propose. If None, uses lexicographic ID.
            effective_type_1: Override type for agent1 (for belief-based evaluation)
            effective_type_2: Override type for agent2 (for belief-based evaluation)

        Returns:
            Expected surplus for agent1
        """
        outcome = self.solve(agent1, agent2, proposer, effective_type_1, effective_type_2)
        return outcome.gains_1


class AsymmetricNashBargainingProtocol(BargainingProtocol):
    """
    Asymmetric Nash Bargaining Protocol using institutional bargaining power.

    This protocol implements the asymmetric Nash bargaining solution where
    bargaining power comes from the agent's `bargaining_power` attribute
    (an exogenous institutional parameter), NOT from patience/discount factors.

    **Power source**: Institutional / exogenous bargaining power (w_i attribute).
    The bargaining weights are computed as:
        β = w1 / (w1 + w2)

    This maximizes the weighted Nash product:
        (u1 - d1)^β × (u2 - d2)^(1-β)

    **Contrast with other protocols**:
    - Nash (Symmetric): Equal bargaining power (β = 0.5)
    - Rubinstein/Nash (Patience): Power from discount factors via BRW formula
    - Nash (Power): Power from explicit bargaining_power attribute (THIS PROTOCOL)
    - TIOLI: Extreme asymmetry where proposer has all power

    This enables studying how different sources of bargaining power
    (patience vs institutional endowment) affect outcomes, a key goal
    of the platform's institutional visibility methodology.

    Properties (O&R Ch 2):
    - When w1 == w2: Reduces to symmetric Nash
    - Higher bargaining_power → higher utility share
    - Maximizes weighted Nash product
    - Individual rationality (both ≥ disagreement)

    Reference: Osborne & Rubinstein, Bargaining and Markets, Chapter 2
    """

    def solve(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> BargainingOutcome:
        """
        Compute asymmetric Nash solution using agents' bargaining_power attributes.

        Args:
            agent1: First agent (with bargaining_power attribute)
            agent2: Second agent (with bargaining_power attribute)
            proposer: Ignored (asymmetric Nash is proposer-independent)
            effective_type_1: Override type for agent1 (for belief-based bargaining)
            effective_type_2: Override type for agent2 (for belief-based bargaining)

        Returns:
            BargainingOutcome with the asymmetric Nash allocation
        """
        # Use effective types if provided, otherwise use agent's true type
        prefs_1 = effective_type_1.preferences if effective_type_1 else agent1.preferences
        endow_1 = effective_type_1.endowment if effective_type_1 else agent1.endowment
        prefs_2 = effective_type_2.preferences if effective_type_2 else agent2.preferences
        endow_2 = effective_type_2.endowment if effective_type_2 else agent2.endowment

        # Compute weights from bargaining_power attributes
        w1 = agent1.bargaining_power
        w2 = agent2.bargaining_power

        # Validate individual weights are positive (Nash axioms require positive weights)
        if w1 <= 0 or w2 <= 0:
            raise ValueError(
                f"bargaining_power must be positive for both agents, got w1={w1}, w2={w2}"
            )

        total_power = w1 + w2

        weight_1 = w1 / total_power
        weight_2 = w2 / total_power

        return asymmetric_nash_bargaining_solution(
            prefs_1, endow_1, prefs_2, endow_2, weight_1, weight_2
        )

    def compute_expected_surplus(
        self,
        agent1: Agent,
        agent2: Agent,
        proposer: Agent | None = None,
        effective_type_1: AgentType | None = None,
        effective_type_2: AgentType | None = None,
    ) -> float:
        """
        Compute expected surplus for agent1 under asymmetric Nash with bargaining_power.

        Args:
            agent1: Evaluating agent
            agent2: Potential trade partner
            proposer: Ignored (asymmetric Nash is proposer-independent)
            effective_type_1: Override type for agent1 (for belief-based evaluation)
            effective_type_2: Override type for agent2 (for belief-based evaluation)

        Returns:
            Expected surplus for agent1
        """
        outcome = self.solve(agent1, agent2, proposer, effective_type_1, effective_type_2)
        return outcome.gains_1
