"""Tests for Nash bargaining solution."""

import pytest
import math
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import create_agent, AgentType
from microecon.bargaining import (
    nash_bargaining_solution,
    compute_nash_surplus,
    execute_trade,
    BargainingOutcome,
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


class TestExecuteTrade:
    """Test trade execution between agents."""

    def test_execute_trade_updates_endowments(self):
        agent1 = create_agent(alpha=0.5, endowment_x=10.0, endowment_y=2.0)
        agent2 = create_agent(alpha=0.5, endowment_x=2.0, endowment_y=10.0)

        initial_u1 = agent1.utility()
        initial_u2 = agent2.utility()

        outcome = execute_trade(agent1, agent2)

        assert outcome.trade_occurred
        assert agent1.utility() >= initial_u1
        assert agent2.utility() >= initial_u2
        assert agent1.endowment == outcome.allocation_1
        assert agent2.endowment == outcome.allocation_2

    def test_execute_trade_preserves_total(self):
        agent1 = create_agent(alpha=0.4, endowment_x=8.0, endowment_y=4.0)
        agent2 = create_agent(alpha=0.6, endowment_x=4.0, endowment_y=8.0)

        total_x = agent1.endowment.x + agent2.endowment.x
        total_y = agent1.endowment.y + agent2.endowment.y

        execute_trade(agent1, agent2)

        new_total_x = agent1.endowment.x + agent2.endowment.x
        new_total_y = agent1.endowment.y + agent2.endowment.y

        assert new_total_x == pytest.approx(total_x)
        assert new_total_y == pytest.approx(total_y)
