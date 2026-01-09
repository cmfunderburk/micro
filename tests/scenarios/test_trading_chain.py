"""
Trading chain theoretical scenario tests.

Test classes:
- TestTradingChainCommittedStage1-3: Tests for COMMITTED matching mode
- TestTradingChainOpportunisticStage1-2: Tests for OPPORTUNISTIC matching mode (initial state and first trade)

NOTE: TestTradingChainOpportunisticStage3 and TestMatchingProtocolComparison were
removed after the Nash optimizer fix (2026-01-07) because they were testing
specific numeric expectations calibrated against a buggy optimizer. The improved
optimizer finds true Nash product maxima, which changed simulation outcomes.
The removed tests should be redesigned to test conceptual properties rather
than specific numeric values if matching protocol comparison is needed.

Both matching modes demonstrate the simulation infrastructure works correctly:

COMMITTED (StableRoommatesMatchingProtocol):
- Irving's algorithm forms optimal pairs: (A,D) and (B,C)
- Trades execute when pairs meet
- Result: Competitive equilibrium (all MRS=1.0)

OPPORTUNISTIC (OpportunisticMatchingProtocol - default):
- No commitments; any co-located pair can trade
- First trade is B-C via path crossing

See docs/DESIGN_matching_protocol.md for the matching protocol abstraction.
"""

import pytest
import math

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.grid import Grid, Position
from microecon.agent import create_agent, AgentType, Agent, AgentPrivateState
from microecon.information import FullInformation
from microecon.simulation import Simulation
from microecon.bargaining import (
    nash_bargaining_solution,
    compute_nash_surplus,
    NashBargainingProtocol,
)
from microecon.search import evaluate_targets, SearchResult
from microecon.matching import (
    StableRoommatesMatchingProtocol,
    OpportunisticMatchingProtocol,
)

pytestmark = pytest.mark.scenario


class TestTradingChainCommittedStage1:
    """
    Trading chain scenario Stage 1: Initial state and target selection.

    Uses COMMITTED matching mode (StableRoommatesMatchingProtocol).

    Setup:
        Position:   (0,0)    (5,0)    (10,0)   (15,0)
        Agent:        A        B        C        D
        α:          0.2      0.4      0.6      0.8
        Endowment: (6,6)    (6,6)    (6,6)    (6,6)

    All agents have uniform endowments (6,6), isolating preference heterogeneity
    as the sole driver of trade.

    Key theoretical predictions:
        - MRS spread: A=0.25, B=0.667, C=1.5, D=4.0
        - Extremes (A-D) have highest surplus: 2.55 total (12x more than neighbors)
        - Even with discounting (δ^15 ≈ 0.21), A→D and D→A remain best targets
        - Surplus ranking: A-D >> A-C = B-D >> C-D ≈ B-C ≈ A-B
    """

    # Hand-computed constants
    INITIAL_UTILITY = 6.0  # 6^α * 6^(1-α) = 6 for all α
    DISCOUNT_FACTOR = 0.9

    # MRS at (6,6): MRS = α/(1-α)
    MRS_A = 0.25      # 0.2/0.8
    MRS_B = 0.6667    # 0.4/0.6
    MRS_C = 1.5       # 0.6/0.4
    MRS_D = 4.0       # 0.8/0.2

    # Nash surplus values (computed with corrected optimizer)
    SURPLUS_A_D = 1.2754  # Each agent's gain from A-D trade
    SURPLUS_A_C = 0.5441  # A's gain from A-C
    SURPLUS_B_D = 0.5374  # B's gain from B-D
    SURPLUS_A_B = 0.1469  # A's gain from A-B (neighbors, similar prefs)
    SURPLUS_B_C = 0.1220  # B's gain from B-C

    # Distances
    DIST_NEIGHBOR = 5
    DIST_SKIP_ONE = 10
    DIST_EXTREME = 15

    @pytest.fixture
    def scenario(self):
        """Set up 4 agents in a line with uniform endowments (committed mode)."""
        agent_a = Agent(
            id="a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.2),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=20.0,  # Can see all agents
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
            matching_protocol=StableRoommatesMatchingProtocol(),  # Committed mode
        )

        # Position agents in a horizontal line
        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 0))
        sim.add_agent(agent_c, Position(10, 0))
        sim.add_agent(agent_d, Position(15, 0))

        return sim, agent_a, agent_b, agent_c, agent_d

    # =========================================================================
    # Initial state verification
    # =========================================================================

    def test_initial_utilities_all_equal(self, scenario):
        """All agents have utility 6.0 with uniform (6,6) endowment."""
        sim, a, b, c, d = scenario

        for agent in [a, b, c, d]:
            assert agent.utility() == pytest.approx(self.INITIAL_UTILITY, rel=1e-6)

    def test_initial_mrs_values(self, scenario):
        """Verify MRS spans from 0.25 (A) to 4.0 (D)."""
        sim, a, b, c, d = scenario

        # Each agent's MRS at their own endowment
        assert a.preferences.marginal_rate_of_substitution(a.endowment) == pytest.approx(self.MRS_A, rel=1e-3)
        assert b.preferences.marginal_rate_of_substitution(b.endowment) == pytest.approx(self.MRS_B, rel=1e-3)
        assert c.preferences.marginal_rate_of_substitution(c.endowment) == pytest.approx(self.MRS_C, rel=1e-3)
        assert d.preferences.marginal_rate_of_substitution(d.endowment) == pytest.approx(self.MRS_D, rel=1e-3)

    def test_linear_positions(self, scenario):
        """Verify agents are positioned in a horizontal line."""
        sim, a, b, c, d = scenario

        assert sim.grid.get_position(a) == Position(0, 0)
        assert sim.grid.get_position(b) == Position(5, 0)
        assert sim.grid.get_position(c) == Position(10, 0)
        assert sim.grid.get_position(d) == Position(15, 0)

    def test_distances_are_correct(self, scenario):
        """Verify Chebyshev distances between agents."""
        sim, a, b, c, d = scenario

        pos_a = sim.grid.get_position(a)
        pos_b = sim.grid.get_position(b)
        pos_c = sim.grid.get_position(c)
        pos_d = sim.grid.get_position(d)

        # Adjacent pairs: distance 5
        assert pos_a.chebyshev_distance_to(pos_b) == self.DIST_NEIGHBOR
        assert pos_b.chebyshev_distance_to(pos_c) == self.DIST_NEIGHBOR
        assert pos_c.chebyshev_distance_to(pos_d) == self.DIST_NEIGHBOR

        # Skip-one pairs: distance 10
        assert pos_a.chebyshev_distance_to(pos_c) == self.DIST_SKIP_ONE
        assert pos_b.chebyshev_distance_to(pos_d) == self.DIST_SKIP_ONE

        # Extremes: distance 15
        assert pos_a.chebyshev_distance_to(pos_d) == self.DIST_EXTREME

    # =========================================================================
    # Surplus ordering verification
    # =========================================================================

    def test_extremes_have_highest_surplus(self, scenario):
        """A-D pair has by far the highest Nash surplus."""
        sim, a, b, c, d = scenario

        type_a = AgentType(a.preferences, a.endowment)
        type_b = AgentType(b.preferences, b.endowment)
        type_c = AgentType(c.preferences, c.endowment)
        type_d = AgentType(d.preferences, d.endowment)

        surplus_ad = compute_nash_surplus(type_a, type_d)
        surplus_ac = compute_nash_surplus(type_a, type_c)
        surplus_ab = compute_nash_surplus(type_a, type_b)

        # A-D surplus should be much higher than other pairs
        # With equal endowments, alpha difference of 0.6 (A-D) vs 0.2 (A-B) gives ~8x ratio
        assert surplus_ad > surplus_ac * 2, "A-D should have >2x surplus vs A-C"
        assert surplus_ad > surplus_ab * 5, "A-D should have >5x surplus vs A-B"

    def test_neighbors_have_lowest_surplus(self, scenario):
        """Adjacent pairs have minimal surplus due to similar preferences."""
        sim, a, b, c, d = scenario

        type_a = AgentType(a.preferences, a.endowment)
        type_b = AgentType(b.preferences, b.endowment)
        type_c = AgentType(c.preferences, c.endowment)
        type_d = AgentType(d.preferences, d.endowment)

        surplus_ab = compute_nash_surplus(type_a, type_b)
        surplus_bc = compute_nash_surplus(type_b, type_c)
        surplus_cd = compute_nash_surplus(type_c, type_d)
        surplus_ad = compute_nash_surplus(type_a, type_d)

        # All neighbor surpluses should be much less than extremes
        for neighbor_surplus in [surplus_ab, surplus_bc, surplus_cd]:
            assert neighbor_surplus < surplus_ad / 5

    def test_surplus_symmetry_for_extreme_pair(self, scenario):
        """A and D get similar gains (approximately symmetric around α=0.5)."""
        sim, a, b, c, d = scenario

        type_a = AgentType(a.preferences, a.endowment)
        type_d = AgentType(d.preferences, d.endowment)

        surplus_a_from_d = compute_nash_surplus(type_a, type_d)
        surplus_d_from_a = compute_nash_surplus(type_d, type_a)

        # Should be approximately equal due to α symmetry (0.2 and 0.8)
        # Note: not perfectly symmetric due to numerical computation
        assert surplus_a_from_d == pytest.approx(surplus_d_from_a, rel=0.05)
        assert surplus_a_from_d == pytest.approx(self.SURPLUS_A_D, rel=0.05)

    # =========================================================================
    # Target selection with discounting
    # =========================================================================

    def test_a_targets_d_despite_distance(self, scenario):
        """A's best target is D, even with distance discounting."""
        sim, a, b, c, d = scenario

        agents_by_id = {ag.id: ag for ag in sim.agents}
        result = evaluate_targets(a, sim.grid, sim.info_env, agents_by_id)

        assert result.best_target_id == d.id, \
            f"A should target D, not {result.best_target_id}"

    def test_d_targets_a_despite_distance(self, scenario):
        """D's best target is A, even with distance discounting."""
        sim, a, b, c, d = scenario

        agents_by_id = {ag.id: ag for ag in sim.agents}
        result = evaluate_targets(d, sim.grid, sim.info_env, agents_by_id)

        assert result.best_target_id == a.id, \
            f"D should target A, not {result.best_target_id}"

    def test_b_targets_extreme_not_neighbor(self, scenario):
        """B should target an extreme (D), not neighbor C."""
        sim, a, b, c, d = scenario

        agents_by_id = {ag.id: ag for ag in sim.agents}
        result = evaluate_targets(b, sim.grid, sim.info_env, agents_by_id)

        # B should prefer D over C (higher discounted surplus)
        assert result.best_target_id == d.id, \
            f"B should target D, not {result.best_target_id}"

    def test_c_targets_extreme_not_neighbor(self, scenario):
        """C should target an extreme (A), not neighbor B."""
        sim, a, b, c, d = scenario

        agents_by_id = {ag.id: ag for ag in sim.agents}
        result = evaluate_targets(c, sim.grid, sim.info_env, agents_by_id)

        # C should prefer A over B (higher discounted surplus)
        assert result.best_target_id == a.id, \
            f"C should target A, not {result.best_target_id}"

    def test_discounted_surplus_still_favors_extremes(self, scenario):
        """Even with δ^15 discounting, A-D pair wins."""
        sim, a, b, c, d = scenario

        type_a = AgentType(a.preferences, a.endowment)
        type_b = AgentType(b.preferences, b.endowment)
        type_d = AgentType(d.preferences, d.endowment)

        # Raw surpluses
        raw_ad = compute_nash_surplus(type_a, type_d)
        raw_ab = compute_nash_surplus(type_a, type_b)

        # Discounted
        disc_ad = raw_ad * (self.DISCOUNT_FACTOR ** self.DIST_EXTREME)
        disc_ab = raw_ab * (self.DISCOUNT_FACTOR ** self.DIST_NEIGHBOR)

        # Even discounted, A-D should beat A-B
        assert disc_ad > disc_ab, \
            f"Discounted A-D ({disc_ad:.4f}) should beat A-B ({disc_ab:.4f})"


class TestTradingChainCommittedStage2:
    """
    Trading chain scenario Stage 2: First trade and subsequent dynamics.

    Uses COMMITTED matching mode (StableRoommatesMatchingProtocol).

    Under committed mode, Irving's algorithm forms both optimal pairs
    simultaneously on tick 1: (A,D) and (B,C). The closer pair (B,C)
    meets and trades first.

    Key predictions:
        - Irving's forms pairs: A-D and B-C (tick 1)
        - First trade: B-C (~tick 2, closer pair)
        - Second trade: A-D (~tick 7, farther pair)
        - Post B-C allocations: B=(4.8, 7.2), C=(7.2, 4.8)
        - Post A-D allocations: A=(2.4, 9.6), D=(9.6, 2.4)
        - All agents reach MRS=1.0 (competitive equilibrium)
    """

    # Post B-C trade allocations (first trade)
    B_POST_TRADE = Bundle(4.8, 7.2)
    C_POST_TRADE = Bundle(7.2, 4.8)
    # Post A-D trade allocations (second trade)
    A_POST_TRADE = Bundle(2.4, 9.6)
    D_POST_TRADE = Bundle(9.6, 2.4)
    POST_TRADE_MRS = 1.0
    DISCOUNT_FACTOR = 0.9

    @pytest.fixture
    def scenario(self):
        """Set up the trading chain scenario (committed mode)."""
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
            matching_protocol=StableRoommatesMatchingProtocol(),  # Committed mode
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 0))
        sim.add_agent(agent_c, Position(10, 0))
        sim.add_agent(agent_d, Position(15, 0))

        return sim, agent_a, agent_b, agent_c, agent_d

    @pytest.fixture
    def scenario_after_first_trade(self, scenario):
        """Run simulation until first trade occurs (committed mode)."""
        sim, a, b, c, d = scenario

        trades = []
        for _ in range(20):  # Should converge much faster
            tick_trades = sim.step()
            if tick_trades:
                trades.extend(tick_trades)
                break

        return sim, a, b, c, d, trades

    # =========================================================================
    # First trade verification (B-C trades first - closer pair)
    # =========================================================================

    def test_first_trade_is_b_c(self, scenario_after_first_trade):
        """First trade should be B-C (closer pair meets first)."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert len(trades) >= 1, "At least one trade should have occurred"

        first_trade = trades[0]
        trade_ids = {first_trade.agent1_id, first_trade.agent2_id}

        assert trade_ids == {"b", "c"}, \
            f"First trade should be B-C (closer pair), got {trade_ids}"

    def test_b_allocation_after_first_trade(self, scenario_after_first_trade):
        """B should have (4.8, 7.2) after trading with C."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert b.endowment.x == pytest.approx(self.B_POST_TRADE.x, rel=0.01)
        assert b.endowment.y == pytest.approx(self.B_POST_TRADE.y, rel=0.01)

    def test_c_allocation_after_first_trade(self, scenario_after_first_trade):
        """C should have (7.2, 4.8) after trading with B."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert c.endowment.x == pytest.approx(self.C_POST_TRADE.x, rel=0.01)
        assert c.endowment.y == pytest.approx(self.C_POST_TRADE.y, rel=0.01)

    def test_b_c_reach_mrs_one(self, scenario_after_first_trade):
        """B and C should have MRS=1.0 after trading with each other."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        mrs_b = b.preferences.marginal_rate_of_substitution(b.endowment)
        mrs_c = c.preferences.marginal_rate_of_substitution(c.endowment)

        assert mrs_b == pytest.approx(self.POST_TRADE_MRS, rel=0.01)
        assert mrs_c == pytest.approx(self.POST_TRADE_MRS, rel=0.01)

    def test_a_d_unchanged_after_first_trade(self, scenario_after_first_trade):
        """A and D should still have (6, 6) after B-C trade."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert a.endowment.x == pytest.approx(6.0, rel=1e-6)
        assert a.endowment.y == pytest.approx(6.0, rel=1e-6)
        assert d.endowment.x == pytest.approx(6.0, rel=1e-6)
        assert d.endowment.y == pytest.approx(6.0, rel=1e-6)

    # =========================================================================
    # Post-first-trade surplus analysis
    # =========================================================================

    def test_b_c_zero_surplus_after_trade(self, scenario_after_first_trade):
        """B and C should have zero remaining surplus with each other."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        type_b = AgentType(b.preferences, b.endowment)
        type_c = AgentType(c.preferences, c.endowment)

        surplus = compute_nash_surplus(type_b, type_c)
        assert surplus == pytest.approx(0.0, abs=1e-6)

    def test_a_d_still_have_surplus(self, scenario_after_first_trade):
        """A and D still have positive surplus with each other."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        type_a = AgentType(a.preferences, a.endowment)
        type_d = AgentType(d.preferences, d.endowment)

        surplus = compute_nash_surplus(type_a, type_d)
        assert surplus > 1.0, f"A-D should have positive surplus, got {surplus}"

    def test_a_d_still_committed(self, scenario_after_first_trade):
        """A and D should still be committed to each other."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert sim.commitments.get_partner(a.id) == d.id
        assert sim.commitments.get_partner(d.id) == a.id

    def test_b_c_no_longer_committed(self, scenario_after_first_trade):
        """B and C should no longer be committed (traded)."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert sim.commitments.get_partner(b.id) is None
        assert sim.commitments.get_partner(c.id) is None


class TestTradingChainCommittedStage3:
    """
    Trading chain scenario Stage 3: Equilibrium properties.

    Uses COMMITTED matching mode (StableRoommatesMatchingProtocol).

    Under committed mode, agents reach competitive equilibrium through
    exactly 2 trades: A-D and B-C.

    Expected final state:
        A: (2.4, 9.6), MRS=1.0, utility=7.28
        B: (4.8, 7.2), MRS=1.0, utility=6.12
        C: (7.2, 4.8), MRS=1.0, utility=6.12
        D: (9.6, 2.4), MRS=1.0, utility=7.28

    Key properties:
        - All MRS converge to 1.0 (competitive equilibrium!)
        - Exactly 2 trades total
        - Zero bilateral surplus for all pairs
        - Total welfare gain: 2.80
    """

    INITIAL_WELFARE = 24.0  # 4 * 6.0
    FINAL_WELFARE = 26.795  # Sum of final utilities
    WELFARE_GAIN = 2.795
    DISCOUNT_FACTOR = 0.9

    @pytest.fixture
    def scenario_at_equilibrium(self):
        """Run simulation to equilibrium (committed mode)."""
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
            matching_protocol=StableRoommatesMatchingProtocol(),  # Committed mode
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 0))
        sim.add_agent(agent_c, Position(10, 0))
        sim.add_agent(agent_d, Position(15, 0))

        # Run to equilibrium
        all_trades = []
        for _ in range(50):
            trades = sim.step()
            if trades:
                all_trades.extend(trades)

        return sim, agent_a, agent_b, agent_c, agent_d, all_trades

    # =========================================================================
    # Equilibrium properties
    # =========================================================================

    def test_exactly_two_trades(self, scenario_at_equilibrium):
        """Exactly 2 trades should occur: A-D then B-C."""
        sim, a, b, c, d, trades = scenario_at_equilibrium

        assert len(trades) == 2, f"Expected 2 trades, got {len(trades)}"

    def test_trade_participants(self, scenario_at_equilibrium):
        """Trades should be A-D and B-C."""
        sim, a, b, c, d, trades = scenario_at_equilibrium

        trade_pairs = [
            frozenset({t.agent1_id, t.agent2_id}) for t in trades
        ]

        assert frozenset({"a", "d"}) in trade_pairs
        assert frozenset({"b", "c"}) in trade_pairs

    def test_all_mrs_equal_one(self, scenario_at_equilibrium):
        """All agents should have MRS=1.0 at equilibrium."""
        sim, a, b, c, d, trades = scenario_at_equilibrium

        for agent in [a, b, c, d]:
            mrs = agent.preferences.marginal_rate_of_substitution(agent.endowment)
            assert mrs == pytest.approx(1.0, rel=0.01), \
                f"Agent {agent.id} MRS should be 1.0, got {mrs}"

    def test_zero_bilateral_surplus_all_pairs(self, scenario_at_equilibrium):
        """All pairs should have zero remaining surplus."""
        sim, a, b, c, d, trades = scenario_at_equilibrium

        agents = [a, b, c, d]
        for i, ag1 in enumerate(agents):
            for ag2 in agents[i + 1:]:
                type1 = AgentType(ag1.preferences, ag1.endowment)
                type2 = AgentType(ag2.preferences, ag2.endowment)
                surplus = compute_nash_surplus(type1, type2)
                assert surplus == pytest.approx(0.0, abs=1e-4), \
                    f"{ag1.id}-{ag2.id} should have zero surplus, got {surplus}"

    def test_welfare_improvement(self, scenario_at_equilibrium):
        """Total welfare should increase by ~2.80."""
        sim, a, b, c, d, trades = scenario_at_equilibrium

        final_welfare = sum(ag.utility() for ag in [a, b, c, d])

        assert final_welfare == pytest.approx(self.FINAL_WELFARE, rel=0.01)
        assert final_welfare - self.INITIAL_WELFARE == pytest.approx(
            self.WELFARE_GAIN, rel=0.01
        )

    def test_feasibility_preserved(self, scenario_at_equilibrium):
        """Total endowment should be unchanged: (24, 24)."""
        sim, a, b, c, d, trades = scenario_at_equilibrium

        total_x = sum(ag.endowment.x for ag in [a, b, c, d])
        total_y = sum(ag.endowment.y for ag in [a, b, c, d])

        assert total_x == pytest.approx(24.0, rel=1e-6)
        assert total_y == pytest.approx(24.0, rel=1e-6)

    def test_no_further_trades(self, scenario_at_equilibrium):
        """No trades should occur after equilibrium."""
        sim, a, b, c, d, trades = scenario_at_equilibrium

        # Run additional ticks
        for _ in range(10):
            new_trades = sim.step()
            assert len(new_trades) == 0, "No trades should occur at equilibrium"

    def test_mrs_equality_in_symmetric_case(self, scenario_at_equilibrium):
        """
        MRS equality achieved in this symmetric scenario.

        Bilateral Nash bargaining achieves MRS equality (competitive equilibrium)
        in this specific symmetric scenario. This is NOT a general property of
        bilateral exchange - it occurs here because initial endowments are uniform
        (6,6) and the effective price ratio is 1:1.

        Note: With asymmetric endowments or preferences, bilateral Nash does not
        generally achieve competitive equilibrium prices.
        """
        sim, a, b, c, d, trades = scenario_at_equilibrium

        # All MRS equal implies competitive equilibrium
        mrs_values = [
            ag.preferences.marginal_rate_of_substitution(ag.endowment)
            for ag in [a, b, c, d]
        ]

        # Variance should be essentially zero
        mean_mrs = sum(mrs_values) / 4
        variance = sum((m - mean_mrs) ** 2 for m in mrs_values) / 4

        assert variance < 1e-6, \
            f"MRS variance should be ~0 for competitive eq, got {variance}"


# =============================================================================
# OPPORTUNISTIC MODE TESTS
# =============================================================================


class TestTradingChainOpportunisticStage1:
    """
    Trading chain scenario Stage 1: Initial state and target selection.

    Uses OPPORTUNISTIC matching mode (OpportunisticMatchingProtocol - default).

    Setup is identical to committed mode:
        Position:   (0,0)    (5,0)    (10,0)   (15,0)
        Agent:        A        B        C        D
        α:          0.2      0.4      0.6      0.8
        Endowment: (6,6)    (6,6)    (6,6)    (6,6)

    Key difference from committed mode:
        - No explicit matching phase
        - Any co-located pair can trade
        - Agents pursue targets independently

    Target selection (same as committed):
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
            matching_protocol=OpportunisticMatchingProtocol(),  # Opportunistic mode
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 0))
        sim.add_agent(agent_c, Position(10, 0))
        sim.add_agent(agent_d, Position(15, 0))

        return sim, agent_a, agent_b, agent_c, agent_d

    def test_opportunistic_protocol_configured(self, scenario):
        """Verify opportunistic matching protocol is in use."""
        sim, a, b, c, d = scenario

        assert isinstance(sim.matching_protocol, OpportunisticMatchingProtocol)
        assert not sim.matching_protocol.requires_commitment

    def test_initial_utilities_all_equal(self, scenario):
        """All agents have utility 6.0 with uniform (6,6) endowment."""
        sim, a, b, c, d = scenario

        for agent in [a, b, c, d]:
            assert agent.utility() == pytest.approx(self.INITIAL_UTILITY, rel=1e-6)

    def test_target_selection_same_as_committed(self, scenario):
        """Target selection is identical to committed mode."""
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

    def test_no_initial_commitments(self, scenario):
        """Opportunistic mode has no commitments."""
        sim, a, b, c, d = scenario

        # No agents should be committed
        for agent in [a, b, c, d]:
            assert not sim.commitments.is_committed(agent.id)
            assert sim.commitments.get_partner(agent.id) is None


class TestTradingChainOpportunisticStage2:
    """
    Trading chain scenario Stage 2: First trade via path crossing.

    Uses OPPORTUNISTIC matching mode (OpportunisticMatchingProtocol).

    Key dynamic difference from committed mode:
        - B moves RIGHT toward D (target)
        - C moves LEFT toward A (target)
        - They cross paths around x=7-8 after ~2-3 ticks
        - When co-located, they trade opportunistically

    This is "opportunistic" because neither B nor C was targeting the other,
    but they trade when they happen to meet.

    Post B-C trade allocations (same as committed):
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
            matching_protocol=OpportunisticMatchingProtocol(),  # Opportunistic mode
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 0))
        sim.add_agent(agent_c, Position(10, 0))
        sim.add_agent(agent_d, Position(15, 0))

        return sim, agent_a, agent_b, agent_c, agent_d

    @pytest.fixture
    def scenario_after_first_trade(self, scenario):
        """Run simulation until first trade occurs (opportunistic mode)."""
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
        opportunistically - different mechanism from committed mode where
        Irving's algorithm paired them.
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

        assert b.endowment.x == pytest.approx(self.B_POST_TRADE.x, rel=0.01)
        assert b.endowment.y == pytest.approx(self.B_POST_TRADE.y, rel=0.01)

    def test_c_allocation_after_first_trade(self, scenario_after_first_trade):
        """C should have (7.2, 4.8) after trading with B."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert c.endowment.x == pytest.approx(self.C_POST_TRADE.x, rel=0.01)
        assert c.endowment.y == pytest.approx(self.C_POST_TRADE.y, rel=0.01)

    def test_b_c_reach_mrs_one(self, scenario_after_first_trade):
        """B and C should have MRS=1.0 after trading."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        mrs_b = b.preferences.marginal_rate_of_substitution(b.endowment)
        mrs_c = c.preferences.marginal_rate_of_substitution(c.endowment)

        assert mrs_b == pytest.approx(self.POST_TRADE_MRS, rel=0.01)
        assert mrs_c == pytest.approx(self.POST_TRADE_MRS, rel=0.01)

    def test_a_d_unchanged_after_first_trade(self, scenario_after_first_trade):
        """A and D should still have (6, 6) after B-C trade."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert a.endowment.x == pytest.approx(6.0, rel=1e-6)
        assert a.endowment.y == pytest.approx(6.0, rel=1e-6)
        assert d.endowment.x == pytest.approx(6.0, rel=1e-6)
        assert d.endowment.y == pytest.approx(6.0, rel=1e-6)

    def test_no_commitments_after_trade(self, scenario_after_first_trade):
        """Opportunistic mode never forms commitments."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        for agent in [a, b, c, d]:
            assert not sim.commitments.is_committed(agent.id)


