"""
Nash bargaining solution for bilateral exchange.

This module implements the axiomatic Nash bargaining solution for two agents
with Cobb-Douglas preferences in a pure exchange economy.

The Nash Bargaining Solution (NBS) is characterized by four axioms:
1. Pareto efficiency: No feasible outcome Pareto-dominates the solution
2. Symmetry: If the game is symmetric, the solution gives equal gains
3. Independence of irrelevant alternatives (IIA): Adding/removing non-selected
   alternatives doesn't change the solution
4. Scale invariance: Affine transformations of utility don't change solution

The solution maximizes the Nash product: (u1 - d1)(u2 - d2)
where di is agent i's disagreement (threat) point utility.

In pure exchange with no outside options, the disagreement point is each agent's
utility from their endowment (no trade = consume own endowment).

Reference: O&R-B Ch 2, Kreps II Ch 23, theoretical-foundations.md
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import Agent, AgentType


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


def _solve_nash_cobb_douglas(
    alpha1: float,
    alpha2: float,
    W_x: float,
    W_y: float,
    d1: float,
    d2: float,
) -> tuple[Bundle, Bundle]:
    """
    Solve for Nash bargaining allocation with Cobb-Douglas preferences.

    Uses the first-order conditions for the Nash product maximization.

    The Lagrangian for maximizing ln(u1 - d1) + ln(u2 - d2) subject to
    feasibility gives FOCs that characterize the solution.

    For numerical stability, we use a grid search over agent 1's share
    of good x, then solve for optimal y1 given x1.
    """
    best_nash_product = -float('inf')
    best_allocation = (Bundle(W_x / 2, W_y / 2), Bundle(W_x / 2, W_y / 2))

    # Grid search over x1 share with refinement
    for resolution in [100, 1000]:
        best_x1 = W_x / 2
        local_best = best_nash_product

        for i in range(resolution + 1):
            x1 = (i / resolution) * W_x
            x2 = W_x - x1

            if x1 <= 0 or x2 <= 0:
                continue

            # For given x1, x2, find optimal y1 to maximize Nash product
            # This is a 1D optimization problem
            y1_opt, np_val = _optimize_y1(alpha1, alpha2, x1, x2, W_y, d1, d2)

            if np_val > local_best:
                local_best = np_val
                best_x1 = x1

        # Refine around best_x1
        if resolution == 100:
            # Narrow the search window
            delta = W_x / resolution
            search_min = max(0.001, best_x1 - delta)
            search_max = min(W_x - 0.001, best_x1 + delta)

            for i in range(resolution + 1):
                x1 = search_min + (i / resolution) * (search_max - search_min)
                x2 = W_x - x1

                if x1 <= 0 or x2 <= 0:
                    continue

                y1_opt, np_val = _optimize_y1(alpha1, alpha2, x1, x2, W_y, d1, d2)

                if np_val > best_nash_product:
                    best_nash_product = np_val
                    best_allocation = (Bundle(x1, y1_opt), Bundle(x2, W_y - y1_opt))

    return best_allocation


def _optimize_y1(
    alpha1: float,
    alpha2: float,
    x1: float,
    x2: float,
    W_y: float,
    d1: float,
    d2: float,
) -> tuple[float, float]:
    """
    Optimize y1 given x1, x2 to maximize Nash product.

    For fixed x1, x2, the Nash product as a function of y1 is:
    NP(y1) = (x1^a1 * y1^(1-a1) - d1) * (x2^a2 * (W_y - y1)^(1-a2) - d2)

    We use golden section search for unimodal optimization.
    """
    def nash_product(y1: float) -> float:
        if y1 <= 0 or y1 >= W_y:
            return -float('inf')
        y2 = W_y - y1

        u1 = (x1 ** alpha1) * (y1 ** (1 - alpha1))
        u2 = (x2 ** alpha2) * (y2 ** (1 - alpha2))

        if u1 <= d1 or u2 <= d2:
            return -float('inf')

        return (u1 - d1) * (u2 - d2)

    # Golden section search
    phi = (1 + math.sqrt(5)) / 2
    a, b = 0.001, W_y - 0.001

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


def execute_trade(agent1: Agent, agent2: Agent) -> BargainingOutcome:
    """
    Execute Nash bargaining between two agents, updating their endowments.

    This modifies the agents' endowments to reflect the bargaining outcome.

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
