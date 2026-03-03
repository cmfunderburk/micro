"""
Three-agent theoretical scenario tests.

Test classes:
- TestThreeAgentSequentialTrading: Heterogeneous preferences, multi-stage trading
"""

import pytest
import math

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.grid import Grid, Position
from microecon.agent import create_agent, AgentType
from microecon.information import FullInformation
from microecon.simulation import Simulation
from microecon.bargaining import (
    nash_bargaining_solution,
    compute_nash_surplus,
    NashBargainingProtocol,
)
from microecon.search import evaluate_targets, SearchResult

pytestmark = pytest.mark.scenario


class TestThreeAgentSequentialTrading:
    """
    Scenario: Three agents with heterogeneous preferences, multi-stage trading.

    Setup:
        A (α=0.5):  endowment=(10,2) - balanced preference, x-rich
        B (α=0.5):  endowment=(2,10) - balanced preference, y-rich
        C (α=0.25): endowment=(8,4)  - y-preferring

    Trading sequence (determined by spatial positioning):
        Stage 1: A-B trade → both get (6, 6)
        Stage 2: A-C trade → A: (9.78, 4.36), C: (4.22, 5.64)
        Stage 3: B-C trade → B: (8.10, 4.50), C: (2.13, 7.14)

    Key insights:
        - After A-B trade, A and B are equilibrated with each other
        - But A and B both have surplus with C (different preferences)
        - After A-C trade, B still has surplus with C's new allocation
        - Total of 3 trades, significant welfare improvement
    """

    INITIAL_TOTAL_WELFARE = 4.472 + 4.472 + 4.757  # ≈ 13.70
    FINAL_TOTAL_WELFARE = 6.527 + 6.035 + 5.277    # ≈ 17.84

    @pytest.fixture
    def scenario(self):
        """Set up 3-agent scenario with spatial positioning for sequential trading."""
        from microecon.bargaining import NashBargainingProtocol

        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=15.0,  # Can see entire grid
            discount_factor=0.95,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=15.0,
            discount_factor=0.95,
        )
        agent_c = create_agent(
            alpha=0.25,  # Prefers y
            endowment_x=8.0,
            endowment_y=4.0,
            perception_radius=15.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(20),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        # Position A and B close together, C farther away
        # This ensures A-B trade first, then winner races to C
        sim.add_agent(agent_a, Position(5, 5))
        sim.add_agent(agent_b, Position(5, 6))  # Adjacent to A
        sim.add_agent(agent_c, Position(15, 15))  # Far from A and B

        return sim, agent_a, agent_b, agent_c

    def test_initial_state(self, scenario):
        """Verify initial utilities and total welfare."""
        sim, agent_a, agent_b, agent_c = scenario

        assert agent_a.utility() == pytest.approx(4.472, rel=0.01)
        assert agent_b.utility() == pytest.approx(4.472, rel=0.01)
        assert agent_c.utility() == pytest.approx(4.757, rel=0.01)

    def test_first_trade_occurs_between_ab(self, scenario):
        """A and B should trade first (closest together)."""
        sim, agent_a, agent_b, agent_c = scenario

        # Run until first trade
        for _ in range(5):
            trades = sim.step()
            if trades:
                break

        assert len(sim.trades) == 1

        # First trade should be between A and B
        trade = sim.trades[0]
        agents_in_trade = {trade.agent1_id, trade.agent2_id}
        assert agent_a.id in agents_in_trade
        assert agent_b.id in agents_in_trade

        # Both A and B should now have (6, 6)
        assert agent_a.holdings.x == pytest.approx(6.0, rel=0.01)
        assert agent_a.holdings.y == pytest.approx(6.0, rel=0.01)
        assert agent_b.holdings.x == pytest.approx(6.0, rel=0.01)
        assert agent_b.holdings.y == pytest.approx(6.0, rel=0.01)

    def test_subsequent_trades_with_c(self, scenario):
        """After A-B trade, trades should occur with C."""
        sim, agent_a, agent_b, agent_c = scenario

        # Run for enough ticks for all trades
        sim.run(50)

        # Should have at least 2 trades (A-B, and one with C)
        # Could have 3 trades total (A-B, A-C, B-C)
        assert len(sim.trades) >= 2

        # C should have participated in at least one trade
        c_traded = any(
            t.agent1_id == agent_c.id or t.agent2_id == agent_c.id
            for t in sim.trades
        )
        assert c_traded

    def test_welfare_improvement(self, scenario):
        """Total welfare should increase significantly."""
        sim, agent_a, agent_b, agent_c = scenario

        initial_welfare = sim.total_welfare()

        sim.run(50)

        final_welfare = sim.total_welfare()

        # Welfare should increase
        assert final_welfare > initial_welfare
        # Gains should be substantial (at least 3 utility units total)
        assert final_welfare - initial_welfare > 3.0

    def test_c_gets_more_y(self, scenario):
        """C (who prefers y) should end up with more y after trading."""
        sim, agent_a, agent_b, agent_c = scenario

        initial_c_y = agent_c.holdings.y

        sim.run(50)

        # C should have gained y
        assert agent_c.holdings.y > initial_c_y

    def test_equilibrium_reached(self, scenario):
        """After all trades, no more beneficial opportunities should exist."""
        sim, agent_a, agent_b, agent_c = scenario

        sim.run(50)

        # Check all pairwise surpluses
        type_a = AgentType(agent_a.preferences, agent_a.holdings)
        type_b = AgentType(agent_b.preferences, agent_b.holdings)
        type_c = AgentType(agent_c.preferences, agent_c.holdings)

        surplus_ab = compute_nash_surplus(type_a, type_b)
        surplus_ac = compute_nash_surplus(type_a, type_c)
        surplus_bc = compute_nash_surplus(type_b, type_c)

        # All surpluses should be essentially zero
        assert surplus_ab == pytest.approx(0.0, abs=0.1)
        assert surplus_ac == pytest.approx(0.0, abs=0.1)
        assert surplus_bc == pytest.approx(0.0, abs=0.1)
