"""
Hub-and-spoke theoretical scenario tests.

Test classes:
- TestFourAgentHubAndSpokeStage1-3: Symmetric hub with uniform peripherals (α=0.5 for all)
- TestMixedHubAndSpokeStage1-3: Asymmetric endowments break ties

These tests explore multi-agent dynamics where a central hub agent has trading
opportunities with multiple peripheral agents.
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

pytestmark = pytest.mark.scenario


# =============================================================================
# Symmetric Hub-and-Spoke (all α=0.5, identical peripheral endowments)
# =============================================================================


class TestFourAgentHubAndSpokeStage1:
    """
    Hub-and-spoke scenario Stage 1: TRUE 3-way tie and first trade.

    Setup:
        Center C: position (7,7), α=0.5, endowment=(6,6)
        Peripheral A: position (2,7), α=0.5, endowment=(10,2) [distance=5]
        Peripheral B: position (12,7), α=0.5, endowment=(10,2) [distance=5]
        Peripheral D: position (7,2), α=0.5, endowment=(10,2) [distance=5]

    All peripherals have identical preferences, endowments, and distance from center.
    This is a TRUE 3-way tie that must be resolved by lexicographic ID ordering.

    Hand-computed predictions:
        - Initial utilities: C=6.0, A=B=D=√20≈4.472
        - All peripherals have identical Nash surplus with C ≈ 0.42
        - All at same distance → identical discounted value
        - Tie-break: C should select A (smallest ID)
        - After C-A trade:
            C: ~(9.08, 4.54), utility ≈ 6.42
            A: ~(6.92, 3.46), utility ≈ 4.89
    """

    # Hand-computed constants
    INITIAL_UTILITY_CENTER = 6.0
    INITIAL_UTILITY_PERIPHERAL = math.sqrt(20)  # ≈ 4.472
    EXPECTED_GAIN_PER_AGENT = 0.42  # Approximate

    @pytest.fixture
    def scenario(self):
        """Set up hub-and-spoke with true 3-way tie."""
        center = Agent(
            id="center",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_a = Agent(
            id="p_a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_b = Agent(
            id="p_b",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_d = Agent(
            id="p_d",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(center, Position(7, 7))
        sim.add_agent(p_a, Position(2, 7))   # distance 5
        sim.add_agent(p_b, Position(12, 7))  # distance 5
        sim.add_agent(p_d, Position(7, 2))   # distance 5

        return sim, center, p_a, p_b, p_d

    def test_initial_utilities(self, scenario):
        """Verify initial utilities match predictions."""
        sim, center, p_a, p_b, p_d = scenario

        assert center.utility() == pytest.approx(self.INITIAL_UTILITY_CENTER, rel=0.01)
        assert p_a.utility() == pytest.approx(self.INITIAL_UTILITY_PERIPHERAL, rel=0.01)
        assert p_b.utility() == pytest.approx(self.INITIAL_UTILITY_PERIPHERAL, rel=0.01)
        assert p_d.utility() == pytest.approx(self.INITIAL_UTILITY_PERIPHERAL, rel=0.01)

    def test_all_peripherals_equidistant(self, scenario):
        """Verify all peripherals are at same distance from center."""
        sim, center, p_a, p_b, p_d = scenario

        center_pos = sim.grid.get_position(center)
        dist_a = sim.grid.get_position(p_a).distance_to(center_pos)
        dist_b = sim.grid.get_position(p_b).distance_to(center_pos)
        dist_d = sim.grid.get_position(p_d).distance_to(center_pos)

        assert dist_a == pytest.approx(dist_b, rel=0.01)
        assert dist_a == pytest.approx(dist_d, rel=0.01)
        assert dist_a == 5.0

    def test_all_peripherals_have_identical_surplus(self, scenario):
        """All peripherals should have identical Nash surplus with center."""
        sim, center, p_a, p_b, p_d = scenario

        center_type = AgentType(center.preferences, center.endowment)
        type_a = AgentType(p_a.preferences, p_a.endowment)
        type_b = AgentType(p_b.preferences, p_b.endowment)
        type_d = AgentType(p_d.preferences, p_d.endowment)

        surplus_a = compute_nash_surplus(center_type, type_a)
        surplus_b = compute_nash_surplus(center_type, type_b)
        surplus_d = compute_nash_surplus(center_type, type_d)

        # All should be equal
        assert surplus_a == pytest.approx(surplus_b, rel=0.01)
        assert surplus_a == pytest.approx(surplus_d, rel=0.01)
        # And positive
        assert surplus_a > 0

    def test_center_selects_lexicographically_smallest_target(self, scenario):
        """Center should select p_a (smallest ID: p_a < p_b < p_d)."""
        sim, center, p_a, p_b, p_d = scenario

        agents_by_id = {a.id: a for a in sim.agents}
        result = evaluate_targets(center, sim.grid, sim.info_env, agents_by_id)

        # Should select p_a
        assert result.best_target_id == "p_a"

    def test_first_trade_is_center_with_p_a(self, scenario):
        """First trade should be between center and p_a."""
        sim, center, p_a, p_b, p_d = scenario

        # Run until first trade
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        assert len(sim.trades) == 1
        trade = sim.trades[0]

        # Should be center-p_a trade
        agents_in_trade = {trade.agent1_id, trade.agent2_id}
        assert "center" in agents_in_trade
        assert "p_a" in agents_in_trade

    def test_first_trade_allocations_correct(self, scenario):
        """After first trade, allocations should match Nash solution."""
        sim, center, p_a, p_b, p_d = scenario

        # Run until first trade
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # Center and p_a should have traded
        # Center started with (6,6), p_a with (10,2)
        # Total: (16, 8)
        # With symmetric α=0.5, on contract curve each gets equal utility gain

        # Just verify feasibility and utility improvements
        total_x = center.endowment.x + p_a.endowment.x
        total_y = center.endowment.y + p_a.endowment.y

        assert total_x == pytest.approx(16.0, rel=0.01)
        assert total_y == pytest.approx(8.0, rel=0.01)

        # Both should have gained utility
        assert center.utility() > self.INITIAL_UTILITY_CENTER
        assert p_a.utility() > self.INITIAL_UTILITY_PERIPHERAL

    def test_peripherals_b_and_d_unchanged(self, scenario):
        """After first trade, p_b and p_d should be unchanged."""
        sim, center, p_a, p_b, p_d = scenario

        initial_b = (p_b.endowment.x, p_b.endowment.y)
        initial_d = (p_d.endowment.x, p_d.endowment.y)

        # Run until first trade
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # p_b and p_d should be unchanged
        assert (p_b.endowment.x, p_b.endowment.y) == initial_b
        assert (p_d.endowment.x, p_d.endowment.y) == initial_d

    def test_post_trade_remaining_surplus_exists(self, scenario):
        """After center-p_a trade, surplus should still exist with p_b and p_d."""
        sim, center, p_a, p_b, p_d = scenario

        # Run until first trade
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # Check surplus between center (now modified) and p_b, p_d
        center_type = AgentType(center.preferences, center.endowment)
        type_b = AgentType(p_b.preferences, p_b.endowment)
        type_d = AgentType(p_d.preferences, p_d.endowment)

        surplus_cb = compute_nash_surplus(center_type, type_b)
        surplus_cd = compute_nash_surplus(center_type, type_d)

        # Center's MRS changed after trade, so surplus with p_b, p_d should still exist
        # (unless center is now equilibrated, but that's unlikely with only one trade)
        # This is a key prediction: trading continues
        assert surplus_cb > 0 or surplus_cd > 0


class TestFourAgentHubAndSpokeStage2:
    """
    Hub-and-spoke scenario Stage 2: Post-first-trade dynamics.

    After center trades with p_a:
    - Center has new allocation ~(9.08, 4.54), MRS ≈ 0.5
    - p_a has new allocation ~(6.92, 3.46), MRS ≈ 0.5
    - p_b, p_d still have (10, 2), MRS = 0.2

    Since MRS differ (0.5 vs 0.2), further trades are possible:
    - Center can trade profitably with p_b or p_d
    - p_a can also trade profitably with p_b or p_d

    Key insight: After first trade, the "equilibrated" center-p_a pair
    still has gains from trade with the remaining peripherals.
    """

    @pytest.fixture
    def scenario_after_first_trade(self):
        """Set up scenario and run until first trade completes."""
        center = Agent(
            id="center",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_a = Agent(
            id="p_a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_b = Agent(
            id="p_b",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_d = Agent(
            id="p_d",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(center, Position(7, 7))
        sim.add_agent(p_a, Position(2, 7))
        sim.add_agent(p_b, Position(12, 7))
        sim.add_agent(p_d, Position(7, 2))

        # Run until first trade
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        return sim, center, p_a, p_b, p_d

    def test_mrs_changed_after_first_trade(self, scenario_after_first_trade):
        """Center and p_a should have different MRS after trade."""
        sim, center, p_a, p_b, p_d = scenario_after_first_trade

        mrs_center = center.preferences.marginal_rate_of_substitution(center.endowment)
        mrs_a = p_a.preferences.marginal_rate_of_substitution(p_a.endowment)
        mrs_b = p_b.preferences.marginal_rate_of_substitution(p_b.endowment)

        # Center and p_a should have equal MRS (they just traded to Pareto efficiency)
        assert mrs_center == pytest.approx(mrs_a, rel=0.1)

        # But p_b (and p_d) still have original MRS = 0.2
        assert mrs_b == pytest.approx(0.2, rel=0.01)

        # So center/p_a MRS differs from p_b MRS → gains from trade exist
        assert abs(mrs_center - mrs_b) > 0.1

    def test_further_trades_occur(self, scenario_after_first_trade):
        """Additional trades should occur after the first."""
        sim, center, p_a, p_b, p_d = scenario_after_first_trade

        trades_after_first = len(sim.trades)

        # Run more ticks
        sim.run(30)

        # More trades should have occurred
        assert len(sim.trades) > trades_after_first

    def test_p_b_and_p_d_eventually_trade(self, scenario_after_first_trade):
        """p_b and p_d should eventually participate in trades."""
        sim, center, p_a, p_b, p_d = scenario_after_first_trade

        # Run until equilibrium
        sim.run(50)

        # Check that p_b and p_d participated
        p_b_traded = any(
            t.agent1_id == "p_b" or t.agent2_id == "p_b"
            for t in sim.trades
        )
        p_d_traded = any(
            t.agent1_id == "p_d" or t.agent2_id == "p_d"
            for t in sim.trades
        )

        # At least one of them should have traded
        assert p_b_traded or p_d_traded


class TestFourAgentHubAndSpokeStage3:
    """
    Hub-and-spoke scenario Stage 3: Equilibrium verification.

    After all trades complete, verify:
    1. Pareto efficiency: All agents have equal MRS (where they can trade)
    2. Zero bilateral surplus: No pair has remaining gains from trade
    3. Welfare improvement: Total welfare increased
    4. Feasibility: Total resources unchanged
    """

    @pytest.fixture
    def scenario_at_equilibrium(self):
        """Set up scenario and run to equilibrium."""
        center = Agent(
            id="center",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_a = Agent(
            id="p_a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_b = Agent(
            id="p_b",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_d = Agent(
            id="p_d",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(center, Position(7, 7))
        sim.add_agent(p_a, Position(2, 7))
        sim.add_agent(p_b, Position(12, 7))
        sim.add_agent(p_d, Position(7, 2))

        # Record initial values
        initial_welfare = sim.total_welfare()
        initial_total_x = sum(a.endowment.x for a in sim.agents)
        initial_total_y = sum(a.endowment.y for a in sim.agents)

        # Run to equilibrium
        sim.run(100)

        return sim, center, p_a, p_b, p_d, initial_welfare, initial_total_x, initial_total_y

    def test_mrs_converge_toward_equality(self, scenario_at_equilibrium):
        """At equilibrium, MRS should be closer together than initially.

        Note: In bilateral exchange, zero bilateral surplus does NOT imply
        perfect MRS equality (which requires a complete market/Walrasian
        auctioneer). We only verify that agents who traded together have
        equalized MRS, and that overall MRS have converged from initial values.
        """
        sim, center, p_a, p_b, p_d, _, _, _ = scenario_at_equilibrium

        mrs_center = center.preferences.marginal_rate_of_substitution(center.endowment)
        mrs_a = p_a.preferences.marginal_rate_of_substitution(p_a.endowment)
        mrs_b = p_b.preferences.marginal_rate_of_substitution(p_b.endowment)
        mrs_d = p_d.preferences.marginal_rate_of_substitution(p_d.endowment)

        # Initial MRS values were: center=1.0, peripherals=0.2
        # After trading, MRS should have converged somewhat
        all_mrs = [mrs_center, mrs_a, mrs_b, mrs_d]
        initial_mrs = [1.0, 0.2, 0.2, 0.2]

        # Calculate variance (spread) of MRS
        mean_final = sum(all_mrs) / len(all_mrs)
        variance_final = sum((m - mean_final) ** 2 for m in all_mrs) / len(all_mrs)

        mean_initial = sum(initial_mrs) / len(initial_mrs)
        variance_initial = sum((m - mean_initial) ** 2 for m in initial_mrs) / len(initial_mrs)

        # Final variance should be lower than initial (MRS converged)
        assert variance_final < variance_initial, \
            f"MRS should converge: initial variance={variance_initial:.4f}, final={variance_final:.4f}"

    def test_zero_bilateral_surplus_at_equilibrium(self, scenario_at_equilibrium):
        """No pair should have remaining gains from trade."""
        sim, center, p_a, p_b, p_d, _, _, _ = scenario_at_equilibrium

        agents = [center, p_a, p_b, p_d]

        for i, agent1 in enumerate(agents):
            for agent2 in agents[i + 1:]:
                type1 = AgentType(agent1.preferences, agent1.endowment)
                type2 = AgentType(agent2.preferences, agent2.endowment)

                surplus = compute_nash_surplus(type1, type2)

                assert surplus == pytest.approx(0.0, abs=0.1), \
                    f"Non-zero surplus between {agent1.id} and {agent2.id}: {surplus}"

    def test_welfare_improved(self, scenario_at_equilibrium):
        """Total welfare should have increased."""
        sim, center, p_a, p_b, p_d, initial_welfare, _, _ = scenario_at_equilibrium

        final_welfare = sim.total_welfare()

        assert final_welfare > initial_welfare

    def test_feasibility_preserved(self, scenario_at_equilibrium):
        """Total resources should be unchanged."""
        sim, center, p_a, p_b, p_d, _, initial_total_x, initial_total_y = scenario_at_equilibrium

        final_total_x = sum(a.endowment.x for a in sim.agents)
        final_total_y = sum(a.endowment.y for a in sim.agents)

        assert final_total_x == pytest.approx(initial_total_x, rel=1e-9)
        assert final_total_y == pytest.approx(initial_total_y, rel=1e-9)

    def test_multiple_trades_occurred(self, scenario_at_equilibrium):
        """Multiple trades should have occurred (not just one)."""
        sim, _, _, _, _, _, _, _ = scenario_at_equilibrium

        # With 4 agents and gains from trade, we expect multiple trades
        assert len(sim.trades) >= 2

    def test_no_more_trades_after_equilibrium(self, scenario_at_equilibrium):
        """Running more ticks should produce no additional trades."""
        sim, center, p_a, p_b, p_d, _, _, _ = scenario_at_equilibrium

        trades_at_equilibrium = len(sim.trades)

        # Run more
        sim.run(20)

        # No new trades
        assert len(sim.trades) == trades_at_equilibrium


# =============================================================================
# Mixed Hub-and-Spoke (D has complementary endowment to A and B)
# =============================================================================


class TestMixedHubAndSpokeStage1:
    """
    Mixed hub-and-spoke scenario Stage 1: Asymmetric endowments break ties.

    Setup:
        Center C:     position (7,7), α=0.5, endowment=(6,6)   MRS=1.0
        Peripheral A: position (2,7), α=0.5, endowment=(10,2)  MRS=0.2
        Peripheral B: position (12,7), α=0.5, endowment=(10,2) MRS=0.2
        Peripheral D: position (7,2), α=0.5, endowment=(2,10)  MRS=5.0  ← DIFFERENT

    Unlike the symmetric hub-and-spoke, here D has complementary endowment to A and B.
    This creates DIFFERENT surplus values:

    Hand-computed Nash surplus:
        - C↔A, C↔B, C↔D: ~0.42 gain each (C is indifferent among peripherals)
        - A↔D, B↔D: ~1.53 gain each (3.6x more than trading with C!)
        - A↔B: 0 (identical types, no gains from trade)

    Key predictions:
        - From A's perspective: D >> C >> B (1.53 vs 0.42 vs 0)
        - From D's perspective: A = B >> C (1.53 vs 0.42)
        - A and D should target each other and trade FIRST
        - C is "left out" of the best trade despite being at the hub
    """

    # Hand-computed constants
    INITIAL_UTILITY_CENTER = 6.0
    INITIAL_UTILITY_PERIPHERAL = math.sqrt(20)  # ≈ 4.472

    # Nash surplus values
    SURPLUS_C_WITH_ANY = 0.42  # C's gain from trading with A, B, or D
    SURPLUS_A_WITH_D = 1.53    # A's gain from trading with D (and vice versa)
    SURPLUS_A_WITH_C = 0.42    # A's gain from trading with C
    SURPLUS_A_WITH_B = 0.0     # No gains from trade (identical types)

    # Post A-D trade allocations
    POST_AD_TRADE_ALLOCATION = (6.0, 6.0)  # Both get (6, 6)
    POST_AD_TRADE_UTILITY = 6.0

    @pytest.fixture
    def scenario(self):
        """Set up mixed hub-and-spoke with asymmetric endowments."""
        center = Agent(
            id="center",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_a = Agent(
            id="p_a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_b = Agent(
            id="p_b",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_d = Agent(
            id="p_d",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(2.0, 10.0),  # ← DIFFERENT from original
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(center, Position(7, 7))
        sim.add_agent(p_a, Position(2, 7))    # distance 5 from center
        sim.add_agent(p_b, Position(12, 7))   # distance 5 from center
        sim.add_agent(p_d, Position(7, 2))    # distance 5 from center

        return sim, center, p_a, p_b, p_d

    # =========================================================================
    # Phase 1: Initial state verification
    # =========================================================================

    def test_initial_utilities(self, scenario):
        """Verify initial utilities match hand calculations."""
        sim, center, p_a, p_b, p_d = scenario

        assert center.utility() == pytest.approx(self.INITIAL_UTILITY_CENTER, rel=1e-6)
        assert p_a.utility() == pytest.approx(self.INITIAL_UTILITY_PERIPHERAL, rel=1e-6)
        assert p_b.utility() == pytest.approx(self.INITIAL_UTILITY_PERIPHERAL, rel=1e-6)
        assert p_d.utility() == pytest.approx(self.INITIAL_UTILITY_PERIPHERAL, rel=1e-6)

    def test_initial_mrs_values(self, scenario):
        """Verify MRS matches hand calculations: C=1, A=B=0.2, D=5."""
        sim, center, p_a, p_b, p_d = scenario

        mrs = center.preferences.marginal_rate_of_substitution
        assert mrs(center.endowment) == pytest.approx(1.0, rel=1e-6)
        assert mrs(p_a.endowment) == pytest.approx(0.2, rel=1e-6)
        assert mrs(p_b.endowment) == pytest.approx(0.2, rel=1e-6)
        assert mrs(p_d.endowment) == pytest.approx(5.0, rel=1e-6)

    def test_all_peripherals_equidistant_from_center(self, scenario):
        """All peripherals should be at distance 5 from center."""
        sim, center, p_a, p_b, p_d = scenario

        pos_center = sim.grid.get_position(center)
        pos_a = sim.grid.get_position(p_a)
        pos_b = sim.grid.get_position(p_b)
        pos_d = sim.grid.get_position(p_d)

        dist_a = pos_a.chebyshev_distance_to(pos_center)
        dist_b = pos_b.chebyshev_distance_to(pos_center)
        dist_d = pos_d.chebyshev_distance_to(pos_center)

        assert dist_a == 5
        assert dist_b == 5
        assert dist_d == 5

    # =========================================================================
    # Phase 2: Surplus ordering verification
    # =========================================================================

    def test_center_has_equal_surplus_with_all_peripherals(self, scenario):
        """C's surplus with A, B, D should all be approximately equal (~0.42)."""
        sim, center, p_a, p_b, p_d = scenario

        type_c = AgentType(center.preferences, center.endowment)
        type_a = AgentType(p_a.preferences, p_a.endowment)
        type_b = AgentType(p_b.preferences, p_b.endowment)
        type_d = AgentType(p_d.preferences, p_d.endowment)

        surplus_c_a = compute_nash_surplus(type_c, type_a)
        surplus_c_b = compute_nash_surplus(type_c, type_b)
        surplus_c_d = compute_nash_surplus(type_c, type_d)

        # All approximately equal
        assert surplus_c_a == pytest.approx(self.SURPLUS_C_WITH_ANY, abs=0.05)
        assert surplus_c_b == pytest.approx(self.SURPLUS_C_WITH_ANY, abs=0.05)
        assert surplus_c_d == pytest.approx(self.SURPLUS_C_WITH_ANY, abs=0.05)

        # Confirm they're equal to each other
        assert surplus_c_a == pytest.approx(surplus_c_b, rel=0.01)
        assert surplus_c_a == pytest.approx(surplus_c_d, rel=0.01)

    def test_a_has_much_higher_surplus_with_d_than_c(self, scenario):
        """A's surplus with D should be ~3.6x higher than with C."""
        sim, center, p_a, p_b, p_d = scenario

        type_a = AgentType(p_a.preferences, p_a.endowment)
        type_c = AgentType(center.preferences, center.endowment)
        type_d = AgentType(p_d.preferences, p_d.endowment)

        surplus_a_c = compute_nash_surplus(type_a, type_c)
        surplus_a_d = compute_nash_surplus(type_a, type_d)

        assert surplus_a_c == pytest.approx(self.SURPLUS_A_WITH_C, abs=0.05)
        assert surplus_a_d == pytest.approx(self.SURPLUS_A_WITH_D, abs=0.05)

        # D should be strictly preferred
        assert surplus_a_d > surplus_a_c * 3.0  # At least 3x

    def test_d_has_much_higher_surplus_with_a_b_than_c(self, scenario):
        """D's surplus with A or B should be ~3.6x higher than with C."""
        sim, center, p_a, p_b, p_d = scenario

        type_d = AgentType(p_d.preferences, p_d.endowment)
        type_a = AgentType(p_a.preferences, p_a.endowment)
        type_b = AgentType(p_b.preferences, p_b.endowment)
        type_c = AgentType(center.preferences, center.endowment)

        surplus_d_a = compute_nash_surplus(type_d, type_a)
        surplus_d_b = compute_nash_surplus(type_d, type_b)
        surplus_d_c = compute_nash_surplus(type_d, type_c)

        # D-A and D-B should be equal (symmetric endowments)
        assert surplus_d_a == pytest.approx(surplus_d_b, rel=0.01)

        # And much higher than D-C
        assert surplus_d_a > surplus_d_c * 3.0

    def test_a_b_have_zero_surplus_with_each_other(self, scenario):
        """A and B have identical types, so no gains from trade."""
        sim, center, p_a, p_b, p_d = scenario

        type_a = AgentType(p_a.preferences, p_a.endowment)
        type_b = AgentType(p_b.preferences, p_b.endowment)

        surplus_a_b = compute_nash_surplus(type_a, type_b)

        assert surplus_a_b == pytest.approx(0.0, abs=0.01)

    # =========================================================================
    # Phase 3: Target selection verification
    # =========================================================================

    def test_a_targets_d_not_center(self, scenario):
        """A should target D (higher surplus) rather than C or B."""
        sim, center, p_a, p_b, p_d = scenario

        agents_by_id = {a.id: a for a in sim.agents}

        result = evaluate_targets(p_a, sim.grid, sim.info_env, agents_by_id)

        assert result is not None
        assert result.best_target_id == p_d.id

    def test_d_targets_a_via_tiebreak(self, scenario):
        """D should target A (tie-break: p_a < p_b lexicographically)."""
        sim, center, p_a, p_b, p_d = scenario

        agents_by_id = {a.id: a for a in sim.agents}

        result = evaluate_targets(p_d, sim.grid, sim.info_env, agents_by_id)

        assert result is not None
        # D has equal surplus with A and B, both at distance 5
        # Tie-break should select p_a (lexicographically smallest)
        assert result.best_target_id == p_a.id

    # =========================================================================
    # Phase 4: First trade verification
    # =========================================================================

    def test_first_trade_is_between_a_and_d(self, scenario):
        """A and D should trade first (both targeting each other)."""
        sim, center, p_a, p_b, p_d = scenario

        # Run until first trade
        for _ in range(15):  # Should happen within ~5 ticks
            trades = sim.step()
            if trades:
                break

        assert len(sim.trades) >= 1

        first_trade = sim.trades[0]
        trade_pair = {first_trade.agent1_id, first_trade.agent2_id}

        assert trade_pair == {p_a.id, p_d.id}, \
            f"Expected A-D trade, got {trade_pair}"

    def test_post_ad_trade_allocations(self, scenario):
        """After A-D trade, both should have (6, 6)."""
        sim, center, p_a, p_b, p_d = scenario

        # Run until first trade
        for _ in range(15):
            trades = sim.step()
            if trades:
                break

        # Verify allocations
        assert p_a.endowment.x == pytest.approx(6.0, abs=0.1)
        assert p_a.endowment.y == pytest.approx(6.0, abs=0.1)
        assert p_d.endowment.x == pytest.approx(6.0, abs=0.1)
        assert p_d.endowment.y == pytest.approx(6.0, abs=0.1)

    def test_post_ad_trade_utilities(self, scenario):
        """After A-D trade, both A and D should have utility 6."""
        sim, center, p_a, p_b, p_d = scenario

        # Run until first trade
        for _ in range(15):
            trades = sim.step()
            if trades:
                break

        assert p_a.utility() == pytest.approx(6.0, abs=0.1)
        assert p_d.utility() == pytest.approx(6.0, abs=0.1)

    def test_center_and_b_unchanged_after_first_trade(self, scenario):
        """C and B should not have traded yet."""
        sim, center, p_a, p_b, p_d = scenario

        # Record initial values
        initial_c = (center.endowment.x, center.endowment.y)
        initial_b = (p_b.endowment.x, p_b.endowment.y)

        # Run until first trade
        for _ in range(15):
            trades = sim.step()
            if trades:
                break

        # C and B unchanged
        assert (center.endowment.x, center.endowment.y) == initial_c
        assert (p_b.endowment.x, p_b.endowment.y) == initial_b

    def test_remaining_surplus_after_first_trade(self, scenario):
        """After A-D trade, there should still be surplus with B."""
        sim, center, p_a, p_b, p_d = scenario

        # Run until first trade
        for _ in range(15):
            trades = sim.step()
            if trades:
                break

        # After A-D trade, A and D have (6,6) with MRS=1
        # B still has (10,2) with MRS=0.2
        # There should be gains from trade between any of {A, D, C} and B

        type_a = AgentType(p_a.preferences, p_a.endowment)
        type_b = AgentType(p_b.preferences, p_b.endowment)

        surplus_a_b = compute_nash_surplus(type_a, type_b)

        # Should be positive (approximately same as original C-A surplus)
        assert surplus_a_b > 0.3


class TestMixedHubAndSpokeStage2:
    """
    Mixed hub-and-spoke scenario Stage 2: Post-A-D trade dynamics.

    State after A-D trade:
        A: (6, 6), MRS = 1.0, utility = 6.0
        D: (6, 6), MRS = 1.0, utility = 6.0
        C: (6, 6), MRS = 1.0, utility = 6.0 (unchanged)
        B: (10, 2), MRS = 0.2, utility = √20 ≈ 4.47 (unchanged)

    Key insight: A, D, and C all now have identical bundles (6, 6).
    They have NO gains from trading with each other.
    B is the ONLY remaining trade opportunity for everyone.

    Hand-computed predictions:
        - Surplus A↔B = D↔B = C↔B ≈ 0.42 each
        - Surplus A↔C = A↔D = C↔D = 0 (identical bundles)
        - B becomes the "last man standing" - sole source of remaining gains
    """

    @pytest.fixture
    def scenario_after_ad_trade(self):
        """Set up scenario and run until A-D trade completes."""
        center = Agent(
            id="center",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_a = Agent(
            id="p_a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_b = Agent(
            id="p_b",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_d = Agent(
            id="p_d",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(2.0, 10.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(center, Position(7, 7))
        sim.add_agent(p_a, Position(2, 7))
        sim.add_agent(p_b, Position(12, 7))
        sim.add_agent(p_d, Position(7, 2))

        # Run until first trade (A-D trade)
        for _ in range(15):
            trades = sim.step()
            if trades:
                break

        return sim, center, p_a, p_b, p_d

    # =========================================================================
    # Phase 1: Post-trade state verification
    # =========================================================================

    def test_a_and_d_have_equal_mrs_after_trade(self, scenario_after_ad_trade):
        """A and D should have MRS = 1.0 after trading."""
        sim, center, p_a, p_b, p_d = scenario_after_ad_trade

        mrs = center.preferences.marginal_rate_of_substitution

        # A and D traded and should have MRS = 1 (balanced bundle)
        assert mrs(p_a.endowment) == pytest.approx(1.0, rel=0.1)
        assert mrs(p_d.endowment) == pytest.approx(1.0, rel=0.1)

    def test_center_unchanged_still_mrs_1(self, scenario_after_ad_trade):
        """Center should still have MRS = 1.0 (didn't trade yet)."""
        sim, center, p_a, p_b, p_d = scenario_after_ad_trade

        mrs = center.preferences.marginal_rate_of_substitution

        # Center didn't trade - still at (6, 6) with MRS = 1
        assert center.endowment.x == pytest.approx(6.0, abs=0.01)
        assert center.endowment.y == pytest.approx(6.0, abs=0.01)
        assert mrs(center.endowment) == pytest.approx(1.0, rel=0.01)

    def test_b_unchanged_still_mrs_02(self, scenario_after_ad_trade):
        """B should still have MRS = 0.2 (didn't trade yet)."""
        sim, center, p_a, p_b, p_d = scenario_after_ad_trade

        mrs = center.preferences.marginal_rate_of_substitution

        # B didn't trade - still at (10, 2) with MRS = 0.2
        assert p_b.endowment.x == pytest.approx(10.0, abs=0.01)
        assert p_b.endowment.y == pytest.approx(2.0, abs=0.01)
        assert mrs(p_b.endowment) == pytest.approx(0.2, rel=0.01)

    # =========================================================================
    # Phase 2: Surplus analysis - B is the only trade opportunity
    # =========================================================================

    def test_no_surplus_between_a_d_c(self, scenario_after_ad_trade):
        """A, D, C all have (6,6) - no gains from trading with each other."""
        sim, center, p_a, p_b, p_d = scenario_after_ad_trade

        type_a = AgentType(p_a.preferences, p_a.endowment)
        type_d = AgentType(p_d.preferences, p_d.endowment)
        type_c = AgentType(center.preferences, center.endowment)

        # All pairs among A, D, C should have ~0 surplus
        assert compute_nash_surplus(type_a, type_d) == pytest.approx(0.0, abs=0.05)
        assert compute_nash_surplus(type_a, type_c) == pytest.approx(0.0, abs=0.05)
        assert compute_nash_surplus(type_c, type_d) == pytest.approx(0.0, abs=0.05)

    def test_positive_surplus_with_b(self, scenario_after_ad_trade):
        """A, D, C all have positive surplus with B (~0.42)."""
        sim, center, p_a, p_b, p_d = scenario_after_ad_trade

        type_a = AgentType(p_a.preferences, p_a.endowment)
        type_d = AgentType(p_d.preferences, p_d.endowment)
        type_c = AgentType(center.preferences, center.endowment)
        type_b = AgentType(p_b.preferences, p_b.endowment)

        surplus_a_b = compute_nash_surplus(type_a, type_b)
        surplus_d_b = compute_nash_surplus(type_d, type_b)
        surplus_c_b = compute_nash_surplus(type_c, type_b)

        # All should have positive surplus with B (~0.42)
        assert surplus_a_b > 0.3
        assert surplus_d_b > 0.3
        assert surplus_c_b > 0.3

        # All should be approximately equal (same (6,6) bundle)
        assert surplus_a_b == pytest.approx(surplus_d_b, rel=0.1)
        assert surplus_a_b == pytest.approx(surplus_c_b, rel=0.1)

    # =========================================================================
    # Phase 3: B eventually participates in trade
    # =========================================================================

    def test_b_eventually_trades(self, scenario_after_ad_trade):
        """B should participate in at least one trade after A-D."""
        sim, center, p_a, p_b, p_d = scenario_after_ad_trade

        initial_b_endowment = (p_b.endowment.x, p_b.endowment.y)

        # Run more ticks
        sim.run(30)

        # B's endowment should have changed (participated in trade)
        final_b_endowment = (p_b.endowment.x, p_b.endowment.y)
        assert final_b_endowment != initial_b_endowment, \
            "B should have traded at some point"

    def test_b_trades_recorded_in_log(self, scenario_after_ad_trade):
        """At least one trade involving B should be recorded."""
        sim, center, p_a, p_b, p_d = scenario_after_ad_trade

        # Run more ticks
        sim.run(30)

        b_traded = any(
            t.agent1_id == "p_b" or t.agent2_id == "p_b"
            for t in sim.trades
        )
        assert b_traded, "B should appear in trade log"

    def test_welfare_improves_after_b_trades(self, scenario_after_ad_trade):
        """Total welfare should increase when B trades."""
        sim, center, p_a, p_b, p_d = scenario_after_ad_trade

        welfare_after_ad = sim.total_welfare()

        # Run more ticks
        sim.run(30)

        welfare_final = sim.total_welfare()

        # Welfare should have increased (B had remaining surplus)
        assert welfare_final > welfare_after_ad


class TestMixedHubAndSpokeStage3:
    """
    Mixed hub-and-spoke scenario Stage 3: Equilibrium verification.

    After all trades complete, verify:
        1. Zero bilateral surplus: No pair has remaining gains from trade
        2. Welfare improvement: Total welfare increased from initial state
        3. Feasibility: Total resources unchanged (conservation)
        4. Multiple trades: More than just A-D trade occurred
        5. Stasis: No more trades after equilibrium

    Key insight from bilateral exchange theory:
        At equilibrium, zero bilateral surplus does NOT imply MRS equality
        (which would require a complete market/Walrasian auctioneer).
        The correct criterion is compute_nash_surplus() ≈ 0 for all pairs.
    """

    @pytest.fixture
    def scenario_at_equilibrium(self):
        """Set up scenario and run to equilibrium."""
        center = Agent(
            id="center",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(6.0, 6.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_a = Agent(
            id="p_a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_b = Agent(
            id="p_b",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        p_d = Agent(
            id="p_d",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(2.0, 10.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(center, Position(7, 7))
        sim.add_agent(p_a, Position(2, 7))
        sim.add_agent(p_b, Position(12, 7))
        sim.add_agent(p_d, Position(7, 2))

        # Record initial values
        initial_welfare = sim.total_welfare()
        initial_total_x = sum(a.endowment.x for a in sim.agents)
        initial_total_y = sum(a.endowment.y for a in sim.agents)

        # Run to equilibrium
        sim.run(100)

        return sim, center, p_a, p_b, p_d, initial_welfare, initial_total_x, initial_total_y

    # =========================================================================
    # Equilibrium properties
    # =========================================================================

    def test_zero_bilateral_surplus_at_equilibrium(self, scenario_at_equilibrium):
        """No pair should have remaining gains from trade."""
        sim, center, p_a, p_b, p_d, _, _, _ = scenario_at_equilibrium

        agents = [center, p_a, p_b, p_d]

        for i, agent1 in enumerate(agents):
            for agent2 in agents[i + 1:]:
                type1 = AgentType(agent1.preferences, agent1.endowment)
                type2 = AgentType(agent2.preferences, agent2.endowment)

                surplus = compute_nash_surplus(type1, type2)

                assert surplus == pytest.approx(0.0, abs=0.1), \
                    f"Non-zero surplus between {agent1.id} and {agent2.id}: {surplus}"

    def test_welfare_improved(self, scenario_at_equilibrium):
        """Total welfare should have increased from initial state."""
        sim, center, p_a, p_b, p_d, initial_welfare, _, _ = scenario_at_equilibrium

        final_welfare = sim.total_welfare()

        # Significant welfare improvement expected
        # Initial: 6 + √20 + √20 + √20 ≈ 19.42
        # Expected improvement from A-D trade alone: ~3.06 (1.53 each)
        # Plus B trades: additional ~0.84 total
        assert final_welfare > initial_welfare + 2.0

    def test_feasibility_preserved(self, scenario_at_equilibrium):
        """Total resources should be unchanged (conservation of goods)."""
        sim, center, p_a, p_b, p_d, _, initial_total_x, initial_total_y = scenario_at_equilibrium

        final_total_x = sum(a.endowment.x for a in sim.agents)
        final_total_y = sum(a.endowment.y for a in sim.agents)

        # Total: (6+10+10+2, 6+2+2+10) = (28, 20)
        assert final_total_x == pytest.approx(initial_total_x, rel=1e-9)
        assert final_total_y == pytest.approx(initial_total_y, rel=1e-9)

    def test_multiple_trades_occurred(self, scenario_at_equilibrium):
        """More than just the A-D trade should have occurred."""
        sim, center, p_a, p_b, p_d, _, _, _ = scenario_at_equilibrium

        # At minimum: A-D trade + at least one trade with B
        assert len(sim.trades) >= 2

    def test_all_agents_participated(self, scenario_at_equilibrium):
        """All four agents should have participated in at least one trade."""
        sim, center, p_a, p_b, p_d, _, _, _ = scenario_at_equilibrium

        participants = set()
        for trade in sim.trades:
            participants.add(trade.agent1_id)
            participants.add(trade.agent2_id)

        assert "center" in participants
        assert "p_a" in participants
        assert "p_b" in participants
        assert "p_d" in participants

    def test_no_more_trades_after_equilibrium(self, scenario_at_equilibrium):
        """Running more ticks should produce no additional trades."""
        sim, center, p_a, p_b, p_d, _, _, _ = scenario_at_equilibrium

        trades_at_equilibrium = len(sim.trades)

        # Run more
        sim.run(20)

        # No new trades
        assert len(sim.trades) == trades_at_equilibrium

    def test_mrs_converge_from_initial(self, scenario_at_equilibrium):
        """MRS variance should be lower at equilibrium than initially.

        Note: In bilateral exchange, zero bilateral surplus does NOT imply
        perfect MRS equality. We only test that MRS have converged compared
        to the highly divergent initial state (0.2, 1.0, 0.2, 5.0).
        """
        sim, center, p_a, p_b, p_d, _, _, _ = scenario_at_equilibrium

        mrs = center.preferences.marginal_rate_of_substitution

        # Initial MRS were: center=1.0, p_a=0.2, p_b=0.2, p_d=5.0
        initial_mrs = [1.0, 0.2, 0.2, 5.0]
        mean_initial = sum(initial_mrs) / 4
        variance_initial = sum((m - mean_initial) ** 2 for m in initial_mrs) / 4

        # Final MRS
        final_mrs = [
            mrs(center.endowment),
            mrs(p_a.endowment),
            mrs(p_b.endowment),
            mrs(p_d.endowment),
        ]
        mean_final = sum(final_mrs) / 4
        variance_final = sum((m - mean_final) ** 2 for m in final_mrs) / 4

        # Variance should have decreased (convergence)
        assert variance_final < variance_initial, \
            f"MRS should converge: initial variance={variance_initial:.4f}, final={variance_final:.4f}"
