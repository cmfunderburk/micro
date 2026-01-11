"""
Trading chain theoretical scenario tests.

Test classes:
- TestTradingChainOpportunisticStage1: Initial state and target selection
- TestTradingChainOpportunisticStage2: First trade via path crossing (skipped - adjacency changes)

OPPORTUNISTIC (OpportunisticMatchingProtocol - default):
- No commitments; any adjacent pair can trade
- First trade is B-C via path crossing

Historical note: COMMITTED mode tests (using StableRoommatesMatchingProtocol) were
removed when that matching protocol was deprecated and removed from the codebase.
"""

import pytest

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.grid import Grid, Position
from microecon.agent import Agent, AgentPrivateState
from microecon.information import FullInformation
from microecon.simulation import Simulation
from microecon.bargaining import NashBargainingProtocol
from microecon.search import evaluate_targets

pytestmark = pytest.mark.scenario


# =============================================================================
# OPPORTUNISTIC MODE TESTS
# =============================================================================


class TestTradingChainOpportunisticStage1:
    """
    Trading chain scenario Stage 1: Initial state and target selection.

    Uses OPPORTUNISTIC matching mode (OpportunisticMatchingProtocol - default).

    Setup:
        Position:   (0,0)    (5,0)    (10,0)   (15,0)
        Agent:        A        B        C        D
        α:          0.2      0.4      0.6      0.8
        Endowment: (6,6)    (6,6)    (6,6)    (6,6)

    Key behavior:
        - No explicit matching phase
        - Any adjacent pair can trade
        - Agents pursue targets independently

    Target selection:
        - A targets D, D targets A (highest surplus pair)
        - B targets D, C targets A (pursuing extremes)
        - B and C will cross paths while pursuing different targets
    """

    INITIAL_UTILITY = 6.0
    DISCOUNT_FACTOR = 0.9
    MRS_A = 0.25
    MRS_B = 0.6667
    MRS_C = 1.5
    MRS_D = 4.0

    @pytest.fixture
    def scenario(self):
        """Set up 4 agents in a line with uniform endowments (opportunistic mode)."""
        agent_a = Agent(
            id="a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.2),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,
            discount_factor=self.DISCOUNT_FACTOR,
        )
        agent_b = Agent(
            id="b",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.4),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,
            discount_factor=self.DISCOUNT_FACTOR,
        )
        agent_c = Agent(
            id="c",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.6),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,
            discount_factor=self.DISCOUNT_FACTOR,
        )
        agent_d = Agent(
            id="d",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.8),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,
            discount_factor=self.DISCOUNT_FACTOR,
        )

        sim = Simulation(
            grid=Grid(20),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 0))
        sim.add_agent(agent_c, Position(10, 0))
        sim.add_agent(agent_d, Position(15, 0))

        return sim, agent_a, agent_b, agent_c, agent_d

    def test_decision_procedure_configured(self, scenario):
        """Verify rational decision procedure is in use."""
        from microecon.decisions import RationalDecisionProcedure
        sim, a, b, c, d = scenario

        assert isinstance(sim.decision_procedure, RationalDecisionProcedure)

    def test_initial_utilities_all_equal(self, scenario):
        """All agents have utility 6.0 with uniform (6,6) endowment."""
        sim, a, b, c, d = scenario

        for agent in [a, b, c, d]:
            assert agent.utility() == pytest.approx(self.INITIAL_UTILITY, rel=1e-6)

    def test_target_selection(self, scenario):
        """Agents target highest-surplus partners."""
        sim, a, b, c, d = scenario

        agents_by_id = {ag.id: ag for ag in sim.agents}

        # A targets D
        result_a = evaluate_targets(a, sim.grid, sim.info_env, agents_by_id)
        assert result_a.best_target_id == d.id

        # D targets A
        result_d = evaluate_targets(d, sim.grid, sim.info_env, agents_by_id)
        assert result_d.best_target_id == a.id

        # B targets D (extreme)
        result_b = evaluate_targets(b, sim.grid, sim.info_env, agents_by_id)
        assert result_b.best_target_id == d.id

        # C targets A (extreme)
        result_c = evaluate_targets(c, sim.grid, sim.info_env, agents_by_id)
        assert result_c.best_target_id == a.id


@pytest.mark.skip(reason="Path-crossing predictions invalid with adjacency-based trading - agents may trade before crossing")
class TestTradingChainOpportunisticStage2:
    """
    Trading chain scenario Stage 2: First trade via path crossing.

    Uses OPPORTUNISTIC matching mode (OpportunisticMatchingProtocol).

    Key dynamic:
        - B moves RIGHT toward D (target)
        - C moves LEFT toward A (target)
        - They cross paths around x=7-8 after ~2-3 ticks
        - When adjacent, they trade opportunistically

    This is "opportunistic" because neither B nor C was targeting the other,
    but they trade when they happen to meet.

    Post B-C trade allocations:
        - B: (4.8, 7.2)
        - C: (7.2, 4.8)
    """

    B_POST_TRADE = Bundle(4.8, 7.2)
    C_POST_TRADE = Bundle(7.2, 4.8)
    POST_TRADE_MRS = 1.0
    DISCOUNT_FACTOR = 0.9

    @pytest.fixture
    def scenario(self):
        """Set up the trading chain scenario (opportunistic mode)."""
        agent_a = Agent(
            id="a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.2),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,
            discount_factor=self.DISCOUNT_FACTOR,
        )
        agent_b = Agent(
            id="b",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.4),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,
            discount_factor=self.DISCOUNT_FACTOR,
        )
        agent_c = Agent(
            id="c",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.6),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,
            discount_factor=self.DISCOUNT_FACTOR,
        )
        agent_d = Agent(
            id="d",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.8),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,
            discount_factor=self.DISCOUNT_FACTOR,
        )

        sim = Simulation(
            grid=Grid(20),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 0))
        sim.add_agent(agent_c, Position(10, 0))
        sim.add_agent(agent_d, Position(15, 0))

        return sim, agent_a, agent_b, agent_c, agent_d

    @pytest.fixture
    def scenario_after_first_trade(self, scenario):
        """Run simulation until first trade occurs."""
        sim, a, b, c, d = scenario

        trades = []
        for _ in range(20):
            tick_trades = sim.step()
            if tick_trades:
                trades.extend(tick_trades)
                break

        return sim, a, b, c, d, trades

    def test_first_trade_is_b_c_via_path_crossing(self, scenario_after_first_trade):
        """
        First trade is B-C via path crossing.

        B was targeting D, C was targeting A. They crossed paths and traded
        opportunistically.
        """
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert len(trades) >= 1, "At least one trade should have occurred"

        first_trade = trades[0]
        trade_ids = {first_trade.agent1_id, first_trade.agent2_id}

        assert trade_ids == {"b", "c"}, \
            f"First trade should be B-C (path crossing), got {trade_ids}"

    def test_b_allocation_after_first_trade(self, scenario_after_first_trade):
        """B should have (4.8, 7.2) after trading with C."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert b.holdings.x == pytest.approx(self.B_POST_TRADE.x, rel=0.01)
        assert b.holdings.y == pytest.approx(self.B_POST_TRADE.y, rel=0.01)

    def test_c_allocation_after_first_trade(self, scenario_after_first_trade):
        """C should have (7.2, 4.8) after trading with B."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert c.holdings.x == pytest.approx(self.C_POST_TRADE.x, rel=0.01)
        assert c.holdings.y == pytest.approx(self.C_POST_TRADE.y, rel=0.01)

    def test_b_c_reach_mrs_one(self, scenario_after_first_trade):
        """B and C should have MRS=1.0 after trading."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        mrs_b = b.preferences.marginal_rate_of_substitution(b.holdings)
        mrs_c = c.preferences.marginal_rate_of_substitution(c.holdings)

        assert mrs_b == pytest.approx(self.POST_TRADE_MRS, rel=0.01)
        assert mrs_c == pytest.approx(self.POST_TRADE_MRS, rel=0.01)

    def test_a_d_unchanged_after_first_trade(self, scenario_after_first_trade):
        """A and D should still have (6, 6) after B-C trade."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert a.holdings.x == pytest.approx(6.0, rel=1e-6)
        assert a.holdings.y == pytest.approx(6.0, rel=1e-6)
        assert d.holdings.x == pytest.approx(6.0, rel=1e-6)
        assert d.holdings.y == pytest.approx(6.0, rel=1e-6)
