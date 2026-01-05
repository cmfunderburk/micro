"""Tests for bargaining solutions (Nash and Rubinstein)."""

import pytest
import math
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import create_agent, AgentType, AgentPrivateState, Agent
from microecon.bargaining import (
    # Nash bargaining
    nash_bargaining_solution,
    compute_nash_surplus,
    BargainingOutcome,
    # Rubinstein bargaining
    rubinstein_share,
    rubinstein_bargaining_solution,
    compute_rubinstein_surplus,
    # Protocol abstraction
    BargainingProtocol,
    NashBargainingProtocol,
    RubinsteinBargainingProtocol,
)


class TestNashBargainingSolution:
    """Test Nash bargaining solution computation."""

    def test_symmetric_agents_equal_endowments(self):
        """Symmetric agents with equal endowments should get symmetric outcomes."""
        prefs1 = CobbDouglas(0.5)
        prefs2 = CobbDouglas(0.5)
        endow1 = Bundle(5.0, 5.0)
        endow2 = Bundle(5.0, 5.0)

        outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        # Symmetric case: no gains from trade
        assert outcome.gains_1 == pytest.approx(0.0, abs=0.1)
        assert outcome.gains_2 == pytest.approx(0.0, abs=0.1)

    def test_complementary_endowments(self):
        """Agents with different endowments should trade."""
        prefs1 = CobbDouglas(0.5)
        prefs2 = CobbDouglas(0.5)
        endow1 = Bundle(10.0, 2.0)  # Has more x
        endow2 = Bundle(2.0, 10.0)  # Has more y

        outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        # Both should gain from trade
        assert outcome.trade_occurred
        assert outcome.gains_1 > 0
        assert outcome.gains_2 > 0
        assert outcome.total_gains > 0

    def test_different_preferences(self):
        """Agents with different preferences should benefit from trade."""
        prefs1 = CobbDouglas(0.3)  # Prefers y more
        prefs2 = CobbDouglas(0.7)  # Prefers x more
        endow1 = Bundle(6.0, 6.0)
        endow2 = Bundle(6.0, 6.0)

        outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        # Trade should occur: agent1 gets more y, agent2 gets more x
        assert outcome.trade_occurred
        assert outcome.allocation_1.y > endow1.y  # Agent 1 should get more y
        assert outcome.allocation_2.x > endow2.x  # Agent 2 should get more x

    def test_pareto_efficiency(self):
        """Outcome should be Pareto efficient (on contract curve)."""
        prefs1 = CobbDouglas(0.4)
        prefs2 = CobbDouglas(0.6)
        endow1 = Bundle(10.0, 2.0)
        endow2 = Bundle(2.0, 10.0)

        outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        # At Pareto efficient allocation, MRS should be equal
        mrs1 = prefs1.marginal_rate_of_substitution(outcome.allocation_1)
        mrs2 = prefs2.marginal_rate_of_substitution(outcome.allocation_2)

        assert mrs1 == pytest.approx(mrs2, rel=0.1)

    def test_individual_rationality(self):
        """Each agent should be at least as well off as at disagreement point."""
        prefs1 = CobbDouglas(0.5)
        prefs2 = CobbDouglas(0.5)
        endow1 = Bundle(8.0, 4.0)
        endow2 = Bundle(4.0, 8.0)

        d1 = prefs1.utility(endow1)
        d2 = prefs2.utility(endow2)

        outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        assert outcome.utility_1 >= d1 - 1e-6
        assert outcome.utility_2 >= d2 - 1e-6

    def test_feasibility(self):
        """Allocations should sum to total endowment."""
        prefs1 = CobbDouglas(0.4)
        prefs2 = CobbDouglas(0.6)
        endow1 = Bundle(7.0, 3.0)
        endow2 = Bundle(3.0, 7.0)

        total_x = endow1.x + endow2.x
        total_y = endow1.y + endow2.y

        outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        assert outcome.allocation_1.x + outcome.allocation_2.x == pytest.approx(total_x)
        assert outcome.allocation_1.y + outcome.allocation_2.y == pytest.approx(total_y)

    def test_no_trade_when_no_gains(self):
        """Should not trade when no gains available."""
        # Both have identical preferences and are on contract curve
        prefs1 = CobbDouglas(0.5)
        prefs2 = CobbDouglas(0.5)
        endow1 = Bundle(5.0, 5.0)
        endow2 = Bundle(5.0, 5.0)

        outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        # Very small or no gains
        assert outcome.total_gains < 0.1

    def test_degenerate_zero_endowment(self):
        """Handle zero total endowment gracefully."""
        prefs1 = CobbDouglas(0.5)
        prefs2 = CobbDouglas(0.5)
        endow1 = Bundle(0.0, 0.0)
        endow2 = Bundle(0.0, 0.0)

        outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        assert not outcome.trade_occurred


class TestComputeNashSurplus:
    """Test surplus computation for search evaluation."""

    def test_surplus_symmetric(self):
        """Compute surplus for symmetric case."""
        type1 = AgentType(CobbDouglas(0.5), Bundle(10.0, 2.0))
        type2 = AgentType(CobbDouglas(0.5), Bundle(2.0, 10.0))

        surplus1 = compute_nash_surplus(type1, type2)
        surplus2 = compute_nash_surplus(type2, type1)

        # Symmetric preferences should give equal surplus
        assert surplus1 == pytest.approx(surplus2, rel=0.1)
        assert surplus1 > 0


# =============================================================================
# Rubinstein Alternating Offers Tests
# =============================================================================


class TestRubinsteinShare:
    """Test Rubinstein SPE surplus share formula."""

    def test_equal_delta_proposer_advantage(self):
        """With equal delta, proposer gets 1/(1+δ), responder gets δ/(1+δ)."""
        delta = 0.9
        share1, share2 = rubinstein_share(delta, delta, proposer=1)

        expected_proposer = 1 / (1 + delta)
        expected_responder = delta / (1 + delta)

        assert share1 == pytest.approx(expected_proposer, rel=1e-6)
        assert share2 == pytest.approx(expected_responder, rel=1e-6)

    def test_shares_sum_to_one(self):
        """Surplus shares should sum to 1."""
        for delta1 in [0.5, 0.8, 0.95]:
            for delta2 in [0.5, 0.8, 0.95]:
                share1, share2 = rubinstein_share(delta1, delta2)
                assert share1 + share2 == pytest.approx(1.0, rel=1e-10)

    def test_proposer_advantage(self):
        """Proposer should get larger share (first-mover advantage)."""
        delta = 0.9
        share1_p1, share2_p1 = rubinstein_share(delta, delta, proposer=1)
        share1_p2, share2_p2 = rubinstein_share(delta, delta, proposer=2)

        # When player 1 proposes, player 1 gets more
        assert share1_p1 > share2_p1
        # When player 2 proposes, player 2 gets more
        assert share2_p2 > share1_p2

    def test_patience_equals_power(self):
        """More patient player (higher δ) should get larger share."""
        # Player 1 is more patient
        share1, share2 = rubinstein_share(0.99, 0.5, proposer=1)
        assert share1 > share2

        # Player 2 is more patient
        share1, share2 = rubinstein_share(0.5, 0.99, proposer=1)
        assert share2 > share1

    def test_convergence_to_50_50(self):
        """As δ → 1, shares should converge to 50-50 (Nash limit)."""
        for delta in [0.99, 0.999, 0.9999]:
            share1, share2 = rubinstein_share(delta, delta, proposer=1)
            # Should approach 0.5 as delta approaches 1
            assert abs(share1 - 0.5) < (1 - delta) * 2

    def test_invalid_delta_raises(self):
        """Invalid discount factors should raise ValueError."""
        with pytest.raises(ValueError):
            rubinstein_share(0.0, 0.5)
        with pytest.raises(ValueError):
            rubinstein_share(1.0, 0.5)
        with pytest.raises(ValueError):
            rubinstein_share(0.5, 1.5)

    def test_invalid_proposer_raises(self):
        """Invalid proposer should raise ValueError."""
        with pytest.raises(ValueError):
            rubinstein_share(0.9, 0.9, proposer=0)
        with pytest.raises(ValueError):
            rubinstein_share(0.9, 0.9, proposer=3)


class TestRubinsteinBargainingSolution:
    """Test Rubinstein bargaining solution for exchange."""

    def test_trade_occurs(self):
        """Trade should occur when there are gains available."""
        prefs1 = CobbDouglas(0.3)
        prefs2 = CobbDouglas(0.7)
        endow1 = Bundle(8.0, 2.0)
        endow2 = Bundle(2.0, 8.0)

        outcome = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.9, 0.9, proposer=1
        )

        assert outcome.trade_occurred
        assert outcome.gains_1 > 0
        assert outcome.gains_2 > 0

    def test_patience_determines_bargaining_power(self):
        """More patient player should get larger share (BRW formulation).

        Under BRW (1986), the Rubinstein alternating-offers converges to
        asymmetric Nash with patience-derived weights. The MORE patient
        player (higher δ) gets GREATER bargaining power.

        Note: Proposer identity no longer affects outcomes.
        """
        prefs1 = CobbDouglas(0.3)
        prefs2 = CobbDouglas(0.7)
        endow1 = Bundle(8.0, 2.0)
        endow2 = Bundle(2.0, 8.0)

        # Agent 1 more patient (δ1 > δ2)
        outcome_patient1 = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.95, 0.5
        )

        # Agent 2 more patient (δ2 > δ1)
        outcome_patient2 = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.5, 0.95
        )

        # More patient player gets larger share
        assert outcome_patient1.gains_1 > outcome_patient2.gains_1
        assert outcome_patient2.gains_2 > outcome_patient1.gains_2

        # Also verify proposer identity no longer matters
        outcome_prop1 = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.9, 0.9, proposer=1
        )
        outcome_prop2 = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.9, 0.9, proposer=2
        )
        # Outcomes should be identical regardless of proposer
        assert outcome_prop1.gains_1 == pytest.approx(outcome_prop2.gains_1, rel=1e-6)
        assert outcome_prop1.gains_2 == pytest.approx(outcome_prop2.gains_2, rel=1e-6)

    def test_pareto_efficiency(self):
        """Outcome should be Pareto efficient."""
        prefs1 = CobbDouglas(0.4)
        prefs2 = CobbDouglas(0.6)
        endow1 = Bundle(10.0, 2.0)
        endow2 = Bundle(2.0, 10.0)

        outcome = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.9, 0.9, proposer=1
        )

        # At Pareto efficient allocation, MRS should be equal
        mrs1 = prefs1.marginal_rate_of_substitution(outcome.allocation_1)
        mrs2 = prefs2.marginal_rate_of_substitution(outcome.allocation_2)

        assert mrs1 == pytest.approx(mrs2, rel=0.1)

    def test_individual_rationality(self):
        """Each agent should be at least as well off as disagreement point."""
        prefs1 = CobbDouglas(0.5)
        prefs2 = CobbDouglas(0.5)
        endow1 = Bundle(8.0, 4.0)
        endow2 = Bundle(4.0, 8.0)

        d1 = prefs1.utility(endow1)
        d2 = prefs2.utility(endow2)

        outcome = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.9, 0.9, proposer=1
        )

        assert outcome.utility_1 >= d1 - 1e-6
        assert outcome.utility_2 >= d2 - 1e-6

    def test_feasibility(self):
        """Allocations should sum to total endowment."""
        prefs1 = CobbDouglas(0.4)
        prefs2 = CobbDouglas(0.6)
        endow1 = Bundle(7.0, 3.0)
        endow2 = Bundle(3.0, 7.0)

        total_x = endow1.x + endow2.x
        total_y = endow1.y + endow2.y

        outcome = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.9, 0.9, proposer=1
        )

        assert outcome.allocation_1.x + outcome.allocation_2.x == pytest.approx(total_x)
        assert outcome.allocation_1.y + outcome.allocation_2.y == pytest.approx(total_y)

    def test_equal_delta_gives_symmetric_nash(self):
        """Equal patience (δ1 = δ2) should give symmetric Nash solution.

        Under BRW, when discount factors are equal, the bargaining weights
        are equal (0.5, 0.5), which gives the symmetric Nash solution.
        """
        from microecon.bargaining import compute_brw_weights

        prefs1 = CobbDouglas(0.3)
        prefs2 = CobbDouglas(0.7)
        endow1 = Bundle(8.0, 2.0)
        endow2 = Bundle(2.0, 8.0)
        delta1, delta2 = 0.9, 0.9

        # Compute BRW weights - should be equal
        w1, w2 = compute_brw_weights(delta1, delta2)
        assert w1 == pytest.approx(0.5, rel=1e-6)
        assert w2 == pytest.approx(0.5, rel=1e-6)

        # Rubinstein outcome should match symmetric Nash
        rubinstein_outcome = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, delta1, delta2
        )
        nash_outcome = nash_bargaining_solution(
            prefs1, endow1, prefs2, endow2
        )

        # Should match symmetric Nash closely
        assert rubinstein_outcome.gains_1 == pytest.approx(nash_outcome.gains_1, rel=0.01)
        assert rubinstein_outcome.gains_2 == pytest.approx(nash_outcome.gains_2, rel=0.01)


class TestRubinsteinConvergesToNash:
    """Test that Rubinstein converges to Nash as δ → 1."""

    def test_high_delta_approaches_nash(self):
        """With δ near 1, Rubinstein should approximate Nash."""
        prefs1 = CobbDouglas(0.3)
        prefs2 = CobbDouglas(0.7)
        endow1 = Bundle(8.0, 2.0)
        endow2 = Bundle(2.0, 8.0)

        nash_outcome = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)

        # Rubinstein with very high delta
        rub_outcome = rubinstein_bargaining_solution(
            prefs1, endow1, prefs2, endow2, 0.999, 0.999, proposer=1
        )

        # Total gains should be similar
        assert nash_outcome.total_gains == pytest.approx(rub_outcome.total_gains, rel=0.01)

        # Share should be close to 50-50 (symmetric Nash)
        rub_share = rub_outcome.gains_1 / rub_outcome.total_gains
        nash_share = nash_outcome.gains_1 / nash_outcome.total_gains

        assert rub_share == pytest.approx(nash_share, abs=0.01)


# =============================================================================
# Protocol Abstraction Tests
# =============================================================================


class TestBargainingProtocol:
    """Test protocol abstraction and polymorphism."""

    @pytest.fixture
    def agents(self):
        """Create two test agents."""
        state1 = AgentPrivateState(CobbDouglas(0.3), Bundle(8.0, 2.0))
        state2 = AgentPrivateState(CobbDouglas(0.7), Bundle(2.0, 8.0))
        agent1 = Agent(private_state=state1, id="agent_1", discount_factor=0.9)
        agent2 = Agent(private_state=state2, id="agent_2", discount_factor=0.9)
        return agent1, agent2

    def test_nash_protocol_solve(self, agents):
        """NashBargainingProtocol should compute Nash solution."""
        agent1, agent2 = agents
        protocol = NashBargainingProtocol()

        outcome = protocol.solve(agent1, agent2)

        assert outcome.trade_occurred
        # Nash is symmetric
        assert outcome.gains_1 == pytest.approx(outcome.gains_2, rel=0.01)

    def test_rubinstein_protocol_solve(self, agents):
        """RubinsteinBargainingProtocol should compute Rubinstein solution."""
        agent1, agent2 = agents
        protocol = RubinsteinBargainingProtocol()

        # Agent 1 proposes
        outcome = protocol.solve(agent1, agent2, proposer=agent1)

        assert outcome.trade_occurred
        # Proposer gets more
        assert outcome.gains_1 > outcome.gains_2

    def test_protocol_execute_updates_endowments(self, agents):
        """Protocol.execute() should update agent endowments."""
        agent1, agent2 = agents
        protocol = RubinsteinBargainingProtocol()

        initial_endow1 = agent1.endowment
        initial_endow2 = agent2.endowment

        outcome = protocol.execute(agent1, agent2, proposer=agent1)

        assert outcome.trade_occurred
        assert agent1.endowment == outcome.allocation_1
        assert agent2.endowment == outcome.allocation_2
        assert agent1.endowment != initial_endow1
        assert agent2.endowment != initial_endow2

    def test_protocols_produce_different_outcomes(self, agents):
        """Nash and Rubinstein should produce different outcomes."""
        agent1, agent2 = agents

        nash = NashBargainingProtocol()
        rubinstein = RubinsteinBargainingProtocol()

        nash_outcome = nash.solve(agent1, agent2)

        # Reset endowments
        agent1.endowment = Bundle(8.0, 2.0)
        agent2.endowment = Bundle(2.0, 8.0)

        rub_outcome = rubinstein.solve(agent1, agent2, proposer=agent1)

        # Nash is symmetric, Rubinstein has proposer advantage
        nash_ratio = nash_outcome.gains_1 / nash_outcome.gains_2
        rub_ratio = rub_outcome.gains_1 / rub_outcome.gains_2

        assert nash_ratio == pytest.approx(1.0, rel=0.01)
        assert rub_ratio > 1.0  # Proposer gets more

    def test_compute_expected_surplus_nash(self, agents):
        """Nash protocol expected surplus should be symmetric."""
        agent1, agent2 = agents
        protocol = NashBargainingProtocol()

        surplus1 = protocol.compute_expected_surplus(agent1, agent2)
        surplus2 = protocol.compute_expected_surplus(agent2, agent1)

        # Nash is symmetric
        assert surplus1 == pytest.approx(surplus2, rel=0.01)

    def test_compute_expected_surplus_rubinstein(self, agents):
        """Rubinstein protocol expected surplus depends on patience (BRW).

        Under BRW (1986), the expected surplus depends on the ratio of
        discount factors, not on proposer identity.
        """
        agent1, agent2 = agents
        protocol = RubinsteinBargainingProtocol()

        # With equal discount factors, surplus should be similar
        surplus1 = protocol.compute_expected_surplus(agent1, agent2)
        surplus2 = protocol.compute_expected_surplus(agent2, agent1)

        # Both should be positive
        assert surplus1 > 0
        assert surplus2 > 0

        # Proposer parameter no longer affects outcome
        surplus_prop1 = protocol.compute_expected_surplus(agent1, agent2, proposer=agent1)
        surplus_prop2 = protocol.compute_expected_surplus(agent1, agent2, proposer=agent2)
        assert surplus_prop1 == pytest.approx(surplus_prop2, rel=1e-6)
