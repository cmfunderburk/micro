"""
THEORY: Verify AsymmetricNashBargainingProtocol Properties.

Tests verifying AsymmetricNashBargainingProtocol correctly implements
asymmetric Nash bargaining using agent.bargaining_power attributes:

1. Equal bargaining_power reduces to symmetric Nash
2. Higher bargaining_power gives higher utility share (power monotonicity)
3. Maximizes weighted Nash product (u1-d1)^β × (u2-d2)^(1-β)
4. Individual rationality (both agents ≥ disagreement utility)

The key distinction from RubinsteinBargainingProtocol:
- Rubinstein derives weights from patience (discount_factor) via BRW formula
- AsymmetricNash uses explicit bargaining_power attribute

Theoretical References:
- Osborne & Rubinstein, Bargaining and Markets, Chapter 2
- theoretical-foundations.md

Test tolerance: 1e-6 for closed-form solutions
"""

import pytest
import math
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import create_agent, Agent
from microecon.bargaining import (
    nash_bargaining_solution,
    asymmetric_nash_bargaining_solution,
    NashBargainingProtocol,
    AsymmetricNashBargainingProtocol,
)

pytestmark = pytest.mark.theory


class TestAsymmetricNashReducesToSymmetric:
    """
    Test that AsymmetricNashBargainingProtocol with equal bargaining_power
    produces the same result as NashBargainingProtocol.
    """

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.8, 0.2, 5.0, 15.0, 15.0, 5.0),
        (0.4, 0.6, 8.0, 12.0, 12.0, 8.0),
    ])
    def test_equal_power_equals_symmetric_nash(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        When both agents have equal bargaining_power, AsymmetricNashProtocol
        should produce identical results to NashBargainingProtocol.
        """
        # Create agents with equal bargaining power
        a1 = create_agent(
            alpha=alpha1, endowment_x=e1_x, endowment_y=e1_y,
            bargaining_power=1.0, agent_id='a1'
        )
        a2 = create_agent(
            alpha=alpha2, endowment_x=e2_x, endowment_y=e2_y,
            bargaining_power=1.0, agent_id='a2'
        )

        nash_protocol = NashBargainingProtocol()
        asym_protocol = AsymmetricNashBargainingProtocol()

        outcome_nash = nash_protocol.solve(a1, a2)
        outcome_asym = asym_protocol.solve(a1, a2)

        # Utilities should match within tolerance
        assert abs(outcome_nash.utility_1 - outcome_asym.utility_1) < 1e-6, (
            f"Utility 1 differs: Nash={outcome_nash.utility_1}, "
            f"Asym={outcome_asym.utility_1}"
        )
        assert abs(outcome_nash.utility_2 - outcome_asym.utility_2) < 1e-6, (
            f"Utility 2 differs: Nash={outcome_nash.utility_2}, "
            f"Asym={outcome_asym.utility_2}"
        )

        # Allocations should match
        assert abs(outcome_nash.allocation_1.x - outcome_asym.allocation_1.x) < 1e-6
        assert abs(outcome_nash.allocation_1.y - outcome_asym.allocation_1.y) < 1e-6

    def test_equal_power_different_values(self):
        """Equal ratios of bargaining_power should give same result."""
        a1_v1 = create_agent(alpha=0.6, endowment_x=5, endowment_y=15,
                             bargaining_power=1.0, agent_id='a1')
        a2_v1 = create_agent(alpha=0.4, endowment_x=15, endowment_y=5,
                             bargaining_power=1.0, agent_id='a2')

        # Same ratio (1:1) but different absolute values
        a1_v2 = create_agent(alpha=0.6, endowment_x=5, endowment_y=15,
                             bargaining_power=5.0, agent_id='a1')
        a2_v2 = create_agent(alpha=0.4, endowment_x=15, endowment_y=5,
                             bargaining_power=5.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()

        outcome_v1 = protocol.solve(a1_v1, a2_v1)
        outcome_v2 = protocol.solve(a1_v2, a2_v2)

        # Same ratios should give same result
        assert abs(outcome_v1.utility_1 - outcome_v2.utility_1) < 1e-6
        assert abs(outcome_v1.utility_2 - outcome_v2.utility_2) < 1e-6


class TestAsymmetricNashPowerMonotonicity:
    """
    Test that higher bargaining_power gives higher utility share.
    O&R Ch 2: Power monotonicity property.
    """

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.5, 0.5, 10.0, 5.0, 5.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.8, 0.2, 5.0, 15.0, 15.0, 5.0),
    ])
    def test_higher_power_gives_higher_utility(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """Agent with higher bargaining_power should get higher utility."""
        # Low power for agent 1
        a1_low = create_agent(alpha=alpha1, endowment_x=e1_x, endowment_y=e1_y,
                              bargaining_power=0.5, agent_id='a1')
        a2_low = create_agent(alpha=alpha2, endowment_x=e2_x, endowment_y=e2_y,
                              bargaining_power=1.5, agent_id='a2')

        # Equal power
        a1_eq = create_agent(alpha=alpha1, endowment_x=e1_x, endowment_y=e1_y,
                             bargaining_power=1.0, agent_id='a1')
        a2_eq = create_agent(alpha=alpha2, endowment_x=e2_x, endowment_y=e2_y,
                             bargaining_power=1.0, agent_id='a2')

        # High power for agent 1
        a1_high = create_agent(alpha=alpha1, endowment_x=e1_x, endowment_y=e1_y,
                               bargaining_power=1.5, agent_id='a1')
        a2_high = create_agent(alpha=alpha2, endowment_x=e2_x, endowment_y=e2_y,
                               bargaining_power=0.5, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()

        outcome_low = protocol.solve(a1_low, a2_low)
        outcome_eq = protocol.solve(a1_eq, a2_eq)
        outcome_high = protocol.solve(a1_high, a2_high)

        if outcome_low.trade_occurred and outcome_eq.trade_occurred and outcome_high.trade_occurred:
            # Agent 1's utility should increase with their bargaining power
            assert outcome_high.utility_1 > outcome_eq.utility_1 - 1e-6, (
                f"A1 high power ({outcome_high.utility_1}) should exceed "
                f"equal power ({outcome_eq.utility_1})"
            )
            assert outcome_eq.utility_1 > outcome_low.utility_1 - 1e-6, (
                f"A1 equal power ({outcome_eq.utility_1}) should exceed "
                f"low power ({outcome_low.utility_1})"
            )

            # Agent 2's utility should decrease as Agent 1's power increases
            assert outcome_low.utility_2 > outcome_eq.utility_2 - 1e-6, (
                f"A2 utility when A1 has low power ({outcome_low.utility_2}) "
                f"should exceed equal power ({outcome_eq.utility_2})"
            )

    def test_extreme_power_approaches_tioli(self):
        """Very high power ratio should approach TIOLI-like outcomes."""
        a1 = create_agent(alpha=0.6, endowment_x=5, endowment_y=15,
                          bargaining_power=100.0, agent_id='a1')
        a2 = create_agent(alpha=0.4, endowment_x=15, endowment_y=5,
                          bargaining_power=1.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        outcome = protocol.solve(a1, a2)

        # Agent 2 should get close to (but not exactly at) disagreement
        d2 = a2.preferences.utility(a2.endowment)

        if outcome.trade_occurred:
            # With 100:1 power ratio, A2 should get very little surplus
            # (β = 100/101 ≈ 0.99, so A1 gets ~99% of surplus)
            assert outcome.gains_2 < outcome.gains_1, (
                f"Agent with low power should get less surplus: "
                f"A1={outcome.gains_1}, A2={outcome.gains_2}"
            )


class TestAsymmetricNashWeightedProductMaximization:
    """
    Test that AsymmetricNashProtocol maximizes the weighted Nash product
    (u1-d1)^β × (u2-d2)^(1-β) where β = w1/(w1+w2).
    """

    @pytest.mark.parametrize("power1,power2", [
        (1.0, 1.0),  # Equal (β = 0.5)
        (2.0, 1.0),  # β = 2/3
        (1.0, 3.0),  # β = 1/4
        (3.0, 2.0),  # β = 3/5
    ])
    def test_weighted_product_is_maximized(self, power1, power2):
        """
        Verify via grid search that no feasible allocation achieves
        higher weighted Nash product.
        """
        a1 = create_agent(alpha=0.4, endowment_x=10, endowment_y=5,
                          bargaining_power=power1, agent_id='a1')
        a2 = create_agent(alpha=0.6, endowment_x=5, endowment_y=10,
                          bargaining_power=power2, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        outcome = protocol.solve(a1, a2)

        if not outcome.trade_occurred:
            return

        # Compute weights
        beta = power1 / (power1 + power2)

        # Disagreement utilities
        d1 = a1.preferences.utility(a1.endowment)
        d2 = a2.preferences.utility(a2.endowment)

        def weighted_nash_product(alloc1: Bundle, alloc2: Bundle) -> float:
            u1 = a1.preferences.utility(alloc1)
            u2 = a2.preferences.utility(alloc2)
            if u1 <= d1 or u2 <= d2:
                return -float('inf')
            return ((u1 - d1) ** beta) * ((u2 - d2) ** (1 - beta))

        wnp_solution = weighted_nash_product(
            outcome.allocation_1, outcome.allocation_2
        )

        # Grid search
        W_x = a1.endowment.x + a2.endowment.x
        W_y = a1.endowment.y + a2.endowment.y
        n_points = 50

        for i in range(1, n_points):
            for j in range(1, n_points):
                x1 = (i / n_points) * W_x
                y1 = (j / n_points) * W_y

                wnp_test = weighted_nash_product(
                    Bundle(x1, y1), Bundle(W_x - x1, W_y - y1)
                )

                assert wnp_solution >= wnp_test - 1e-6, (
                    f"Found higher weighted Nash product: "
                    f"solution={wnp_solution:.6f}, test={wnp_test:.6f} "
                    f"with β={beta:.2f}"
                )


class TestAsymmetricNashIndividualRationality:
    """Test that AsymmetricNash satisfies individual rationality."""

    @pytest.mark.parametrize("power1,power2", [
        (1.0, 1.0),
        (2.0, 1.0),
        (1.0, 3.0),
        (0.5, 1.5),
    ])
    def test_both_agents_at_least_disagreement(self, power1, power2):
        """Both agents should get at least their disagreement utility."""
        a1 = create_agent(alpha=0.4, endowment_x=10, endowment_y=5,
                          bargaining_power=power1, agent_id='a1')
        a2 = create_agent(alpha=0.6, endowment_x=5, endowment_y=10,
                          bargaining_power=power2, agent_id='a2')

        d1 = a1.preferences.utility(a1.endowment)
        d2 = a2.preferences.utility(a2.endowment)

        protocol = AsymmetricNashBargainingProtocol()
        outcome = protocol.solve(a1, a2)

        assert outcome.utility_1 >= d1 - 1e-9, (
            f"Agent 1 utility {outcome.utility_1} < disagreement {d1}"
        )
        assert outcome.utility_2 >= d2 - 1e-9, (
            f"Agent 2 utility {outcome.utility_2} < disagreement {d2}"
        )
        assert outcome.gains_1 >= -1e-9, "Agent 1 gains should be non-negative"
        assert outcome.gains_2 >= -1e-9, "Agent 2 gains should be non-negative"


class TestAsymmetricNashDistinctFromRubinstein:
    """
    Test that AsymmetricNash (using bargaining_power) differs from
    Rubinstein (using discount_factor) when the two attributes differ.
    """

    def test_power_independent_of_patience(self):
        """
        Agents with same discount_factor but different bargaining_power
        should have different outcomes under AsymmetricNash.
        """
        # Same discount_factor, different bargaining_power
        a1 = create_agent(alpha=0.5, endowment_x=10, endowment_y=5,
                          discount_factor=0.9, bargaining_power=2.0, agent_id='a1')
        a2 = create_agent(alpha=0.5, endowment_x=5, endowment_y=10,
                          discount_factor=0.9, bargaining_power=1.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        outcome = protocol.solve(a1, a2)

        # With 2:1 power ratio, A1 should get more
        if outcome.trade_occurred:
            assert outcome.gains_1 > outcome.gains_2 + 1e-6, (
                f"Higher bargaining_power should give higher gains: "
                f"A1={outcome.gains_1}, A2={outcome.gains_2}"
            )

    def test_bargaining_power_attribute_used_not_discount(self):
        """
        Verify that bargaining_power attribute determines weights,
        not discount_factor.
        """
        # Different discount_factors but equal bargaining_power
        a1 = create_agent(alpha=0.5, endowment_x=10, endowment_y=5,
                          discount_factor=0.99, bargaining_power=1.0, agent_id='a1')
        a2 = create_agent(alpha=0.5, endowment_x=5, endowment_y=10,
                          discount_factor=0.5, bargaining_power=1.0, agent_id='a2')

        asym_protocol = AsymmetricNashBargainingProtocol()
        nash_protocol = NashBargainingProtocol()

        outcome_asym = asym_protocol.solve(a1, a2)
        outcome_nash = nash_protocol.solve(a1, a2)

        # AsymmetricNash with equal bargaining_power should equal symmetric Nash
        # (discount_factor should NOT affect the result)
        if outcome_asym.trade_occurred and outcome_nash.trade_occurred:
            assert abs(outcome_asym.utility_1 - outcome_nash.utility_1) < 1e-6, (
                f"AsymmetricNash should ignore discount_factor and match Nash: "
                f"Asym={outcome_asym.utility_1}, Nash={outcome_nash.utility_1}"
            )


class TestAsymmetricNashProtocolAPI:
    """Test AsymmetricNashBargainingProtocol class interface."""

    def test_compute_expected_surplus(self):
        """Test compute_expected_surplus method returns gains_1."""
        a1 = create_agent(alpha=0.6, endowment_x=5, endowment_y=15,
                          bargaining_power=2.0, agent_id='a1')
        a2 = create_agent(alpha=0.4, endowment_x=15, endowment_y=5,
                          bargaining_power=1.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        surplus = protocol.compute_expected_surplus(a1, a2)
        outcome = protocol.solve(a1, a2)

        assert abs(surplus - outcome.gains_1) < 1e-9

    def test_proposer_parameter_ignored(self):
        """Proposer parameter should be ignored (asymmetric Nash is symmetric in roles)."""
        a1 = create_agent(alpha=0.6, endowment_x=5, endowment_y=15,
                          bargaining_power=2.0, agent_id='a1')
        a2 = create_agent(alpha=0.4, endowment_x=15, endowment_y=5,
                          bargaining_power=1.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()

        outcome_no_prop = protocol.solve(a1, a2)
        outcome_a1_prop = protocol.solve(a1, a2, proposer=a1)
        outcome_a2_prop = protocol.solve(a1, a2, proposer=a2)

        # All should be identical
        assert abs(outcome_no_prop.utility_1 - outcome_a1_prop.utility_1) < 1e-9
        assert abs(outcome_no_prop.utility_1 - outcome_a2_prop.utility_1) < 1e-9

    def test_execute_updates_holdings(self):
        """Test that execute() method updates agent holdings (not endowment)."""
        a1 = create_agent(alpha=0.6, endowment_x=5, endowment_y=15,
                          bargaining_power=1.5, agent_id='a1')
        a2 = create_agent(alpha=0.4, endowment_x=15, endowment_y=5,
                          bargaining_power=1.0, agent_id='a2')

        original_h1 = Bundle(a1.holdings.x, a1.holdings.y)
        original_e1 = Bundle(a1.endowment.x, a1.endowment.y)

        protocol = AsymmetricNashBargainingProtocol()
        outcome = protocol.execute(a1, a2)

        if outcome.trade_occurred:
            # Holdings should be updated to allocations
            assert abs(a1.holdings.x - outcome.allocation_1.x) < 1e-9
            assert abs(a1.holdings.y - outcome.allocation_1.y) < 1e-9
            assert abs(a2.holdings.x - outcome.allocation_2.x) < 1e-9
            assert abs(a2.holdings.y - outcome.allocation_2.y) < 1e-9

            # Holdings should differ from original
            assert (abs(a1.holdings.x - original_h1.x) > 1e-6 or
                    abs(a1.holdings.y - original_h1.y) > 1e-6)

            # Endowment should remain unchanged
            assert abs(a1.endowment.x - original_e1.x) < 1e-9
            assert abs(a1.endowment.y - original_e1.y) < 1e-9


class TestAsymmetricNashFeasibility:
    """Test that AsymmetricNash allocations are feasible."""

    @pytest.mark.parametrize("power1,power2", [
        (1.0, 1.0),
        (2.0, 1.0),
        (1.0, 3.0),
    ])
    def test_allocation_exhausts_resources(self, power1, power2):
        """Allocation should sum to total endowment."""
        a1 = create_agent(alpha=0.4, endowment_x=10, endowment_y=5,
                          bargaining_power=power1, agent_id='a1')
        a2 = create_agent(alpha=0.6, endowment_x=5, endowment_y=10,
                          bargaining_power=power2, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        outcome = protocol.solve(a1, a2)

        W_x = a1.endowment.x + a2.endowment.x
        W_y = a1.endowment.y + a2.endowment.y

        total_x = outcome.allocation_1.x + outcome.allocation_2.x
        total_y = outcome.allocation_1.y + outcome.allocation_2.y

        assert abs(total_x - W_x) < 1e-6, f"X: {total_x} != {W_x}"
        assert abs(total_y - W_y) < 1e-6, f"Y: {total_y} != {W_y}"

    def test_allocations_non_negative(self):
        """All allocations should be non-negative."""
        a1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5,
                          bargaining_power=3.0, agent_id='a1')
        a2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10,
                          bargaining_power=1.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        outcome = protocol.solve(a1, a2)

        assert outcome.allocation_1.x >= -1e-9
        assert outcome.allocation_1.y >= -1e-9
        assert outcome.allocation_2.x >= -1e-9
        assert outcome.allocation_2.y >= -1e-9


class TestAsymmetricNashValidation:
    """Test that AsymmetricNash validates bargaining_power inputs."""

    def test_negative_power_raises_error(self):
        """Negative bargaining_power should raise ValueError."""
        a1 = create_agent(alpha=0.5, endowment_x=10, endowment_y=5,
                          bargaining_power=-0.5, agent_id='a1')
        a2 = create_agent(alpha=0.5, endowment_x=5, endowment_y=10,
                          bargaining_power=2.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        with pytest.raises(ValueError, match="bargaining_power must be positive"):
            protocol.solve(a1, a2)

    def test_zero_power_raises_error(self):
        """Zero bargaining_power should raise ValueError."""
        a1 = create_agent(alpha=0.5, endowment_x=10, endowment_y=5,
                          bargaining_power=0.0, agent_id='a1')
        a2 = create_agent(alpha=0.5, endowment_x=5, endowment_y=10,
                          bargaining_power=1.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        with pytest.raises(ValueError, match="bargaining_power must be positive"):
            protocol.solve(a1, a2)

    def test_both_negative_raises_error(self):
        """Both negative bargaining_power should raise ValueError."""
        a1 = create_agent(alpha=0.5, endowment_x=10, endowment_y=5,
                          bargaining_power=-1.0, agent_id='a1')
        a2 = create_agent(alpha=0.5, endowment_x=5, endowment_y=10,
                          bargaining_power=-1.0, agent_id='a2')

        protocol = AsymmetricNashBargainingProtocol()
        with pytest.raises(ValueError, match="bargaining_power must be positive"):
            protocol.solve(a1, a2)
