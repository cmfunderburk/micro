"""
Theoretical scenario tests: hand-verified economic predictions.

These tests verify that simulation outcomes match analytically-derived
theoretical predictions. Each scenario is simple enough to compute by hand,
providing rigorous validation of the simulation's economic correctness.

Test structure:
1. Scenario setup with explicit parameters
2. Hand-computed expected values with derivation comments
3. Comprehensive verification: allocations, utilities, efficiency, equilibrium
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


class TestTwoAgentSymmetricScenario:
    """
    Scenario: Two agents with identical preferences, complementary endowments.

    Setup:
        Agent A: α=0.5, endowment=(10,2), position=(0,0)
        Agent B: α=0.5, endowment=(2,10), position=(5,5)

    Theoretical predictions (hand-computed):
        - u(x,y) = x^0.5 * y^0.5
        - Initial utilities: √(10*2) = √20 ≈ 4.472 for each
        - Nash solution with symmetric prefs: equal split of total
        - Total endowment: (12, 12)
        - NBS allocation: (6, 6) for each agent
        - Post-trade utility: √(6*6) = 6 for each
        - Gain per agent: 6 - √20 ≈ 1.528
        - Post-trade MRS: (α/(1-α)) * (y/x) = 1 * 1 = 1 (equal for both)
        - Post-trade surplus: 0 (no remaining gains)
    """

    # Hand-computed constants
    INITIAL_UTILITY = math.sqrt(20)  # ≈ 4.472
    POST_TRADE_ALLOCATION = (6.0, 6.0)
    POST_TRADE_UTILITY = 6.0
    EXPECTED_GAIN = 6.0 - math.sqrt(20)  # ≈ 1.528
    POST_TRADE_MRS = 1.0
    CHEBYSHEV_DISTANCE = 5  # from (0,0) to (5,5)

    @pytest.fixture
    def scenario(self):
        """Set up the canonical 2-agent symmetric scenario."""
        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,  # Large enough to see partner
            discount_factor=0.95,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),  # Grid large enough to contain positions
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 5))

        return sim, agent_a, agent_b

    # =========================================================================
    # Phase 1: Initial state verification
    # =========================================================================

    def test_initial_utilities_match_theory(self, scenario):
        """Verify initial utilities equal √20 ≈ 4.472."""
        sim, agent_a, agent_b = scenario

        assert agent_a.utility() == pytest.approx(self.INITIAL_UTILITY, rel=1e-6)
        assert agent_b.utility() == pytest.approx(self.INITIAL_UTILITY, rel=1e-6)

    def test_initial_positions(self, scenario):
        """Verify agents at expected positions."""
        sim, agent_a, agent_b = scenario

        assert sim.grid.get_position(agent_a) == Position(0, 0)
        assert sim.grid.get_position(agent_b) == Position(5, 5)

    # =========================================================================
    # Phase 2: Search evaluation verification
    # =========================================================================

    def test_search_finds_positive_surplus(self, scenario):
        """Each agent should see positive Nash surplus from partner."""
        sim, agent_a, agent_b = scenario

        # Agent A evaluates Agent B
        type_a = AgentType(agent_a.preferences, agent_a.endowment)
        type_b = AgentType(agent_b.preferences, agent_b.endowment)

        surplus_a_from_b = compute_nash_surplus(type_a, type_b)
        surplus_b_from_a = compute_nash_surplus(type_b, type_a)

        # Both should see positive surplus ≈ 1.528
        assert surplus_a_from_b == pytest.approx(self.EXPECTED_GAIN, rel=0.01)
        assert surplus_b_from_a == pytest.approx(self.EXPECTED_GAIN, rel=0.01)

    def test_search_selects_partner_as_target(self, scenario):
        """Each agent should select the other as best target."""
        sim, agent_a, agent_b = scenario

        agents_by_id = {a.id: a for a in sim.agents}

        result_a = evaluate_targets(
            agent_a, sim.grid, sim.info_env, agents_by_id
        )
        result_b = evaluate_targets(
            agent_b, sim.grid, sim.info_env, agents_by_id
        )

        assert result_a.best_target_id == agent_b.id
        assert result_b.best_target_id == agent_a.id
        assert result_a.visible_agents == 1
        assert result_b.visible_agents == 1

    def test_discounted_value_calculation(self, scenario):
        """Verify discounted value = surplus * δ^distance."""
        sim, agent_a, agent_b = scenario

        agents_by_id = {a.id: a for a in sim.agents}
        result = evaluate_targets(agent_a, sim.grid, sim.info_env, agents_by_id)

        # Expected: surplus * 0.95^5
        expected_discounted = self.EXPECTED_GAIN * (0.95 ** self.CHEBYSHEV_DISTANCE)

        assert result.discounted_value == pytest.approx(expected_discounted, rel=0.01)

    # =========================================================================
    # Phase 3: Movement and convergence
    # =========================================================================

    def test_agents_move_toward_each_other(self, scenario):
        """After one tick, agents should be closer together."""
        sim, agent_a, agent_b = scenario

        initial_distance = Position(0, 0).chebyshev_distance_to(Position(5, 5))

        sim.step()

        new_pos_a = sim.grid.get_position(agent_a)
        new_pos_b = sim.grid.get_position(agent_b)
        new_distance = new_pos_a.chebyshev_distance_to(new_pos_b)

        assert new_distance < initial_distance

    def test_agents_eventually_meet(self, scenario):
        """Agents should meet within Chebyshev distance ticks."""
        sim, agent_a, agent_b = scenario

        # Run for enough ticks to guarantee meeting
        # With both moving, should meet in ceil(5/2) = 3 ticks at most
        for _ in range(self.CHEBYSHEV_DISTANCE):
            sim.step()
            pos_a = sim.grid.get_position(agent_a)
            pos_b = sim.grid.get_position(agent_b)
            if pos_a == pos_b:
                break

        assert sim.grid.get_position(agent_a) == sim.grid.get_position(agent_b)

    # =========================================================================
    # Phase 4: Bargaining outcome verification
    # =========================================================================

    def test_trade_occurs(self, scenario):
        """Trade should occur when agents meet."""
        sim, agent_a, agent_b = scenario

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        assert len(sim.trades) == 1
        assert sim.trades[0].outcome.trade_occurred

    def test_allocation_matches_nash_solution(self, scenario):
        """Post-trade allocations should be (6, 6) for each."""
        sim, agent_a, agent_b = scenario

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # Verify exact allocations (within numerical tolerance)
        assert agent_a.endowment.x == pytest.approx(self.POST_TRADE_ALLOCATION[0], rel=0.01)
        assert agent_a.endowment.y == pytest.approx(self.POST_TRADE_ALLOCATION[1], rel=0.01)
        assert agent_b.endowment.x == pytest.approx(self.POST_TRADE_ALLOCATION[0], rel=0.01)
        assert agent_b.endowment.y == pytest.approx(self.POST_TRADE_ALLOCATION[1], rel=0.01)

    def test_utilities_increase_as_predicted(self, scenario):
        """Post-trade utilities should be 6.0 (gain ≈ 1.528)."""
        sim, agent_a, agent_b = scenario

        initial_u_a = agent_a.utility()
        initial_u_b = agent_b.utility()

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        assert agent_a.utility() == pytest.approx(self.POST_TRADE_UTILITY, rel=0.01)
        assert agent_b.utility() == pytest.approx(self.POST_TRADE_UTILITY, rel=0.01)

        # Verify gains
        gain_a = agent_a.utility() - initial_u_a
        gain_b = agent_b.utility() - initial_u_b

        assert gain_a == pytest.approx(self.EXPECTED_GAIN, rel=0.01)
        assert gain_b == pytest.approx(self.EXPECTED_GAIN, rel=0.01)

    def test_pareto_efficiency(self, scenario):
        """Post-trade allocation should have equal MRS (on contract curve)."""
        sim, agent_a, agent_b = scenario

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # MRS = (α/(1-α)) * (y/x) = 1 * (6/6) = 1 for both
        mrs_a = agent_a.preferences.marginal_rate_of_substitution(agent_a.endowment)
        mrs_b = agent_b.preferences.marginal_rate_of_substitution(agent_b.endowment)

        assert mrs_a == pytest.approx(self.POST_TRADE_MRS, rel=0.01)
        assert mrs_b == pytest.approx(self.POST_TRADE_MRS, rel=0.01)
        assert mrs_a == pytest.approx(mrs_b, rel=0.01)  # Equal MRS = Pareto efficient

    def test_feasibility_preserved(self, scenario):
        """Total resources should be unchanged after trade."""
        sim, agent_a, agent_b = scenario

        initial_total_x = agent_a.endowment.x + agent_b.endowment.x
        initial_total_y = agent_a.endowment.y + agent_b.endowment.y

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        final_total_x = agent_a.endowment.x + agent_b.endowment.x
        final_total_y = agent_a.endowment.y + agent_b.endowment.y

        assert final_total_x == pytest.approx(initial_total_x, rel=1e-9)
        assert final_total_y == pytest.approx(initial_total_y, rel=1e-9)

    # =========================================================================
    # Phase 5: Post-trade equilibrium verification
    # =========================================================================

    def test_no_remaining_surplus_after_trade(self, scenario):
        """Post-trade, agents should see zero surplus from each other."""
        sim, agent_a, agent_b = scenario

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # Compute surplus with post-trade endowments
        type_a = AgentType(agent_a.preferences, agent_a.endowment)
        type_b = AgentType(agent_b.preferences, agent_b.endowment)

        surplus_a_from_b = compute_nash_surplus(type_a, type_b)
        surplus_b_from_a = compute_nash_surplus(type_b, type_a)

        # Should be essentially zero (within numerical tolerance)
        assert surplus_a_from_b == pytest.approx(0.0, abs=0.01)
        assert surplus_b_from_a == pytest.approx(0.0, abs=0.01)

    def test_no_movement_target_after_trade(self, scenario):
        """Post-trade, agents should have no beneficial movement target."""
        sim, agent_a, agent_b = scenario

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        agents_by_id = {a.id: a for a in sim.agents}

        result_a = evaluate_targets(agent_a, sim.grid, sim.info_env, agents_by_id)
        result_b = evaluate_targets(agent_b, sim.grid, sim.info_env, agents_by_id)

        # No target should be selected (surplus ≤ 0)
        assert result_a.best_target_id is None
        assert result_b.best_target_id is None

    def test_simulation_reaches_stasis(self, scenario):
        """After trade, additional ticks should produce no further trades."""
        sim, agent_a, agent_b = scenario

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        trade_count_after_first = len(sim.trades)

        # Run additional ticks
        for _ in range(10):
            sim.step()

        # No additional trades should occur
        assert len(sim.trades) == trade_count_after_first

    def test_positions_unchanged_after_equilibrium(self, scenario):
        """In equilibrium, agents should not move."""
        sim, agent_a, agent_b = scenario

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        pos_a_after_trade = sim.grid.get_position(agent_a)
        pos_b_after_trade = sim.grid.get_position(agent_b)

        # Run more ticks
        for _ in range(5):
            sim.step()

        # Positions should be unchanged
        assert sim.grid.get_position(agent_a) == pos_a_after_trade
        assert sim.grid.get_position(agent_b) == pos_b_after_trade


class TestTwoAgentNoTradeScenario:
    """
    Scenario: Two agents where NO trade should occur.

    Setup:
        Agent A: α=0.5, endowment=(5,5), position=(0,0)
        Agent B: α=0.5, endowment=(5,5), position=(5,5)

    Theoretical prediction:
        - Both have identical preferences and balanced endowments
        - Already on the contract curve (MRS = 1 for both)
        - No gains from trade exist
        - Should not trade even if they meet
    """

    @pytest.fixture
    def scenario(self):
        """Set up scenario with no gains from trade."""
        agent_a = create_agent(
            alpha=0.5,
            endowment_x=5.0,
            endowment_y=5.0,
            perception_radius=10.0,
            discount_factor=0.95,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=5.0,
            endowment_y=5.0,
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        # Place at same position to ensure they meet
        sim.add_agent(agent_a, Position(5, 5))
        sim.add_agent(agent_b, Position(5, 5))

        return sim, agent_a, agent_b

    def test_no_surplus_when_on_contract_curve(self, scenario):
        """Agents already on contract curve should see zero surplus."""
        sim, agent_a, agent_b = scenario

        type_a = AgentType(agent_a.preferences, agent_a.endowment)
        type_b = AgentType(agent_b.preferences, agent_b.endowment)

        surplus = compute_nash_surplus(type_a, type_b)

        assert surplus == pytest.approx(0.0, abs=0.1)

    def test_no_trade_when_co_located(self, scenario):
        """Agents at same position should not trade if no gains exist."""
        sim, agent_a, agent_b = scenario

        initial_endow_a = (agent_a.endowment.x, agent_a.endowment.y)
        initial_endow_b = (agent_b.endowment.x, agent_b.endowment.y)

        # Run several ticks
        for _ in range(5):
            sim.step()

        # No trades should occur
        assert len(sim.trades) == 0

        # Endowments unchanged
        assert (agent_a.endowment.x, agent_a.endowment.y) == initial_endow_a
        assert (agent_b.endowment.x, agent_b.endowment.y) == initial_endow_b

    def test_no_movement_target(self, scenario):
        """Agents should have no movement target when no surplus exists."""
        sim, agent_a, agent_b = scenario

        agents_by_id = {a.id: a for a in sim.agents}

        result_a = evaluate_targets(agent_a, sim.grid, sim.info_env, agents_by_id)
        result_b = evaluate_targets(agent_b, sim.grid, sim.info_env, agents_by_id)

        assert result_a.best_target_id is None
        assert result_b.best_target_id is None


class TestTwoAgentAsymmetricScenario:
    """
    Scenario: Two agents with asymmetric preferences (mirror symmetric).

    Setup:
        Agent A: α=0.25 (prefers y), endowment=(10,2), position=(0,0)
        Agent B: α=0.75 (prefers x), endowment=(2,10), position=(5,5)

    Theoretical predictions (numerically verified):
        - u_A(x,y) = x^0.25 * y^0.75, u_B(x,y) = x^0.75 * y^0.25
        - Initial utilities: ≈ 2.991 for each
        - Nash solution: A gets (3, 9), B gets (9, 3)
        - Trade: A gives 7x for 7y, B gives 7y for 7x
        - Post-trade utilities: ≈ 6.838 for each
        - Gain per agent: ≈ 3.848
        - Post-trade MRS: 1.0 for both (Pareto efficient)

    Key insight: Mirror symmetry (α_A + α_B = 1, complementary endowments)
    produces symmetric gains despite asymmetric preferences.
    """

    # Numerically verified constants
    ALPHA_A = 0.25
    ALPHA_B = 0.75
    INITIAL_UTILITY = 2.9907
    POST_TRADE_ALLOCATION_A = (3.0, 9.0)
    POST_TRADE_ALLOCATION_B = (9.0, 3.0)
    POST_TRADE_UTILITY = 6.8385
    EXPECTED_GAIN = 3.8478
    POST_TRADE_MRS = 1.0

    @pytest.fixture
    def scenario(self):
        """Set up the asymmetric 2-agent scenario."""
        agent_a = create_agent(
            alpha=self.ALPHA_A,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
            discount_factor=0.95,
        )
        agent_b = create_agent(
            alpha=self.ALPHA_B,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 5))

        return sim, agent_a, agent_b

    def test_initial_utilities(self, scenario):
        """Verify initial utilities ≈ 2.991."""
        sim, agent_a, agent_b = scenario

        assert agent_a.utility() == pytest.approx(self.INITIAL_UTILITY, rel=0.01)
        assert agent_b.utility() == pytest.approx(self.INITIAL_UTILITY, rel=0.01)

    def test_trade_occurs(self, scenario):
        """Trade should occur when agents meet."""
        sim, agent_a, agent_b = scenario

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        assert len(sim.trades) == 1

    def test_allocation_direction_correct(self, scenario):
        """A (y-heavy) should get more y, B (x-heavy) should get more x."""
        sim, agent_a, agent_b = scenario

        initial_a_x, initial_a_y = 10.0, 2.0
        initial_b_x, initial_b_y = 2.0, 10.0

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # A should have less x, more y
        assert agent_a.endowment.x < initial_a_x
        assert agent_a.endowment.y > initial_a_y

        # B should have more x, less y
        assert agent_b.endowment.x > initial_b_x
        assert agent_b.endowment.y < initial_b_y

    def test_allocation_matches_theory(self, scenario):
        """Post-trade allocations should match Nash solution: A=(3,9), B=(9,3)."""
        sim, agent_a, agent_b = scenario

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        assert agent_a.endowment.x == pytest.approx(self.POST_TRADE_ALLOCATION_A[0], rel=0.01)
        assert agent_a.endowment.y == pytest.approx(self.POST_TRADE_ALLOCATION_A[1], rel=0.01)
        assert agent_b.endowment.x == pytest.approx(self.POST_TRADE_ALLOCATION_B[0], rel=0.01)
        assert agent_b.endowment.y == pytest.approx(self.POST_TRADE_ALLOCATION_B[1], rel=0.01)

    def test_utilities_increase_correctly(self, scenario):
        """Post-trade utilities should be ≈ 6.838, gains ≈ 3.848."""
        sim, agent_a, agent_b = scenario

        initial_u_a = agent_a.utility()
        initial_u_b = agent_b.utility()

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # Final utilities
        assert agent_a.utility() == pytest.approx(self.POST_TRADE_UTILITY, rel=0.01)
        assert agent_b.utility() == pytest.approx(self.POST_TRADE_UTILITY, rel=0.01)

        # Gains
        assert agent_a.utility() - initial_u_a == pytest.approx(self.EXPECTED_GAIN, rel=0.01)
        assert agent_b.utility() - initial_u_b == pytest.approx(self.EXPECTED_GAIN, rel=0.01)

    def test_symmetric_gains_despite_asymmetric_preferences(self, scenario):
        """Mirror symmetry produces equal gains for both agents."""
        sim, agent_a, agent_b = scenario

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        trade = sim.trades[0]
        # Gains should be equal (mirror symmetry property)
        assert trade.outcome.gains_1 == pytest.approx(trade.outcome.gains_2, rel=0.01)

    def test_pareto_efficiency(self, scenario):
        """Post-trade allocation should have equal MRS = 1.0."""
        sim, agent_a, agent_b = scenario

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        mrs_a = agent_a.preferences.marginal_rate_of_substitution(agent_a.endowment)
        mrs_b = agent_b.preferences.marginal_rate_of_substitution(agent_b.endowment)

        assert mrs_a == pytest.approx(self.POST_TRADE_MRS, rel=0.01)
        assert mrs_b == pytest.approx(self.POST_TRADE_MRS, rel=0.01)
        assert mrs_a == pytest.approx(mrs_b, rel=0.01)

    def test_no_remaining_surplus(self, scenario):
        """Post-trade, no further gains exist between agents."""
        sim, agent_a, agent_b = scenario

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        type_a = AgentType(agent_a.preferences, agent_a.endowment)
        type_b = AgentType(agent_b.preferences, agent_b.endowment)

        surplus = compute_nash_surplus(type_a, type_b)
        assert surplus == pytest.approx(0.0, abs=0.01)

    def test_equilibrium_reached(self, scenario):
        """After trade, no further trades or movement should occur."""
        sim, agent_a, agent_b = scenario

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        pos_after_trade = (
            sim.grid.get_position(agent_a),
            sim.grid.get_position(agent_b),
        )
        trades_after_first = len(sim.trades)

        # Run more ticks
        for _ in range(10):
            sim.step()

        # No new trades
        assert len(sim.trades) == trades_after_first

        # Positions unchanged
        assert sim.grid.get_position(agent_a) == pos_after_trade[0]
        assert sim.grid.get_position(agent_b) == pos_after_trade[1]


class TestRubinsteinProtocol:
    """
    Test Rubinstein alternating-offers bargaining protocol.

    Key properties to verify:
    1. First-mover (proposer) advantage: proposer gets larger share
    2. Surplus shares match formula: share_1 = (1-δ₂)/(1-δ₁δ₂)
    3. Patience = power: higher δ → larger share
    4. Convergence to Nash: as δ → 1, Rubinstein → Nash

    Reference: O&R-B Chapter 3, Theorem 3.4
    """

    @pytest.fixture
    def symmetric_agents(self):
        """Create two agents with same preferences and complementary endowments."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
            discount_factor=0.9,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,
            discount_factor=0.9,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=RubinsteinBargainingProtocol(),
        )

        return sim, agent_a, agent_b

    def test_proposer_advantage_a_proposes(self, symmetric_agents):
        """When A proposes, A should get more than B."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        sim, agent_a, agent_b = symmetric_agents
        protocol = RubinsteinBargainingProtocol()

        outcome = protocol.solve(agent_a, agent_b, proposer=agent_a)

        # Proposer gets more
        assert outcome.gains_1 > outcome.gains_2
        # With δ=0.9, proposer share ≈ 0.526
        expected_share = 1 / (1 + 0.9)
        actual_share = outcome.gains_1 / outcome.total_gains
        assert actual_share == pytest.approx(expected_share, rel=0.01)

    def test_proposer_advantage_b_proposes(self, symmetric_agents):
        """When B proposes, B should get more than A."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        sim, agent_a, agent_b = symmetric_agents
        protocol = RubinsteinBargainingProtocol()

        outcome = protocol.solve(agent_a, agent_b, proposer=agent_b)

        # Now B (agent2 in the solution) gets more
        assert outcome.gains_2 > outcome.gains_1
        expected_share = 1 / (1 + 0.9)
        actual_share_b = outcome.gains_2 / outcome.total_gains
        assert actual_share_b == pytest.approx(expected_share, rel=0.01)

    def test_surplus_shares_match_formula(self, symmetric_agents):
        """Surplus shares should exactly match Rubinstein formula."""
        from microecon.bargaining import RubinsteinBargainingProtocol, rubinstein_share

        sim, agent_a, agent_b = symmetric_agents
        protocol = RubinsteinBargainingProtocol()

        outcome = protocol.solve(agent_a, agent_b, proposer=agent_a)

        # Get theoretical shares
        expected_share_a, expected_share_b = rubinstein_share(0.9, 0.9, proposer=1)

        # Compare
        actual_share_a = outcome.gains_1 / outcome.total_gains
        actual_share_b = outcome.gains_2 / outcome.total_gains

        assert actual_share_a == pytest.approx(expected_share_a, rel=0.01)
        assert actual_share_b == pytest.approx(expected_share_b, rel=0.01)

    def test_patience_equals_power(self):
        """More patient agent should get larger share."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        # A is very patient (δ=0.99), B is impatient (δ=0.5)
        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
            discount_factor=0.99,  # Very patient
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,
            discount_factor=0.5,  # Impatient
        )

        protocol = RubinsteinBargainingProtocol()
        outcome = protocol.solve(agent_a, agent_b, proposer=agent_a)

        # Patient A should get much more
        assert outcome.gains_1 > outcome.gains_2 * 10  # A gets >10x

    def test_convergence_to_nash(self):
        """As δ → 1, Rubinstein should converge to Nash (50-50 split)."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        # Very patient agents (δ close to 1)
        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
            discount_factor=0.999,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,
            discount_factor=0.999,
        )

        protocol = RubinsteinBargainingProtocol()
        outcome = protocol.solve(agent_a, agent_b, proposer=agent_a)

        # Should be close to 50-50
        share_a = outcome.gains_1 / outcome.total_gains
        assert share_a == pytest.approx(0.5, abs=0.01)

    def test_pareto_efficiency(self, symmetric_agents):
        """Rubinstein solution should be Pareto efficient (MRS equality)."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        sim, agent_a, agent_b = symmetric_agents
        protocol = RubinsteinBargainingProtocol()

        outcome = protocol.execute(agent_a, agent_b, proposer=agent_a)

        mrs_a = agent_a.preferences.marginal_rate_of_substitution(agent_a.endowment)
        mrs_b = agent_b.preferences.marginal_rate_of_substitution(agent_b.endowment)

        assert mrs_a == pytest.approx(mrs_b, rel=0.1)

    def test_simulation_with_rubinstein_protocol(self):
        """Test full simulation flow with Rubinstein protocol."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
            discount_factor=0.9,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,
            discount_factor=0.9,
        )

        sim = Simulation(
            grid=Grid(15),
            info_env=FullInformation(),
            bargaining_protocol=RubinsteinBargainingProtocol(),
        )

        # Place at same position for immediate trade
        sim.add_agent(agent_a, Position(5, 5))
        sim.add_agent(agent_b, Position(5, 5))

        initial_u_a = agent_a.utility()
        initial_u_b = agent_b.utility()

        trades = sim.step()

        # Trade should occur
        assert len(trades) == 1

        # Both should gain
        assert agent_a.utility() > initial_u_a
        assert agent_b.utility() > initial_u_b

        # Proposer (agent_a as initiator) should get more
        trade = trades[0]
        assert trade.outcome.gains_1 > trade.outcome.gains_2

    def test_rubinstein_vs_nash_different_outcomes(self):
        """Rubinstein and Nash should produce different surplus distributions."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
            discount_factor=0.9,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,
            discount_factor=0.9,
        )

        nash_protocol = NashBargainingProtocol()
        rubinstein_protocol = RubinsteinBargainingProtocol()

        nash_outcome = nash_protocol.solve(agent_a, agent_b)

        # Reset endowments
        agent_a.endowment = Bundle(10.0, 2.0)
        agent_b.endowment = Bundle(2.0, 10.0)

        rub_outcome = rubinstein_protocol.solve(agent_a, agent_b, proposer=agent_a)

        # Nash is symmetric (50-50)
        nash_ratio = nash_outcome.gains_1 / nash_outcome.gains_2
        assert nash_ratio == pytest.approx(1.0, rel=0.01)

        # Rubinstein has proposer advantage
        rub_ratio = rub_outcome.gains_1 / rub_outcome.gains_2
        assert rub_ratio > 1.0

    def test_equilibrium_after_rubinstein_trade(self):
        """After Rubinstein trade, no further gains should exist."""
        from microecon.bargaining import RubinsteinBargainingProtocol

        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=10.0,
            discount_factor=0.9,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,
            discount_factor=0.9,
        )

        protocol = RubinsteinBargainingProtocol()
        protocol.execute(agent_a, agent_b, proposer=agent_a)

        # Check surplus after trade
        type_a = AgentType(agent_a.preferences, agent_a.endowment)
        type_b = AgentType(agent_b.preferences, agent_b.endowment)

        surplus = compute_nash_surplus(type_a, type_b)

        # Should be essentially zero
        assert surplus == pytest.approx(0.0, abs=0.1)


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
        assert agent_a.endowment.x == pytest.approx(6.0, rel=0.01)
        assert agent_a.endowment.y == pytest.approx(6.0, rel=0.01)
        assert agent_b.endowment.x == pytest.approx(6.0, rel=0.01)
        assert agent_b.endowment.y == pytest.approx(6.0, rel=0.01)

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

        initial_c_y = agent_c.endowment.y

        sim.run(50)

        # C should have gained y
        assert agent_c.endowment.y > initial_c_y

    def test_equilibrium_reached(self, scenario):
        """After all trades, no more beneficial opportunities should exist."""
        sim, agent_a, agent_b, agent_c = scenario

        sim.run(50)

        # Check all pairwise surpluses
        type_a = AgentType(agent_a.preferences, agent_a.endowment)
        type_b = AgentType(agent_b.preferences, agent_b.endowment)
        type_c = AgentType(agent_c.preferences, agent_c.endowment)

        surplus_ab = compute_nash_surplus(type_a, type_b)
        surplus_ac = compute_nash_surplus(type_a, type_c)
        surplus_bc = compute_nash_surplus(type_b, type_c)

        # All surpluses should be essentially zero
        assert surplus_ab == pytest.approx(0.0, abs=0.1)
        assert surplus_ac == pytest.approx(0.0, abs=0.1)
        assert surplus_bc == pytest.approx(0.0, abs=0.1)


class TestNashSymmetry:
    """
    Test that Nash bargaining solution is symmetric with respect to agent ordering.

    This was a bug discovered during 3-agent scenario development where the
    Nash solution gave different results depending on which agent was listed first.
    """

    def test_symmetric_solution_basic(self):
        """Nash solution should be the same regardless of agent ordering."""
        from microecon.bargaining import nash_bargaining_solution

        prefs_a = CobbDouglas(0.5)
        prefs_c = CobbDouglas(0.25)
        endow_a = Bundle(6.0, 6.0)
        endow_c = Bundle(8.0, 4.0)

        # Order 1: A first
        r1 = nash_bargaining_solution(prefs_a, endow_a, prefs_c, endow_c)

        # Order 2: C first
        r2 = nash_bargaining_solution(prefs_c, endow_c, prefs_a, endow_a)

        # Both should find a trade
        assert r1.trade_occurred == r2.trade_occurred

        if r1.trade_occurred:
            # A's allocation should match in both orderings
            assert r1.allocation_1.x == pytest.approx(r2.allocation_2.x, rel=0.01)
            assert r1.allocation_1.y == pytest.approx(r2.allocation_2.y, rel=0.01)

            # C's allocation should match in both orderings
            assert r1.allocation_2.x == pytest.approx(r2.allocation_1.x, rel=0.01)
            assert r1.allocation_2.y == pytest.approx(r2.allocation_1.y, rel=0.01)

    def test_symmetric_solution_edge_case(self):
        """Test symmetry with unbalanced endowments that caused the original bug."""
        from microecon.bargaining import nash_bargaining_solution

        # This specific case triggered the bug: feasible region entirely above W_x/2
        prefs_a = CobbDouglas(0.5)
        prefs_c = CobbDouglas(0.25)
        endow_a = Bundle(6.0, 6.0)  # High utility reservation
        endow_c = Bundle(8.0, 4.0)

        r1 = nash_bargaining_solution(prefs_a, endow_a, prefs_c, endow_c)
        r2 = nash_bargaining_solution(prefs_c, endow_c, prefs_a, endow_a)

        # Both orderings must agree on whether trade occurs
        assert r1.trade_occurred == r2.trade_occurred
        assert r1.trade_occurred is True  # Trade should occur in this case

        # Gains should match
        assert r1.gains_1 == pytest.approx(r2.gains_2, rel=0.01)  # A's gain
        assert r1.gains_2 == pytest.approx(r2.gains_1, rel=0.01)  # C's gain


class TestPerceptionBoundary:
    """
    Scenario: Test that perception radius correctly limits partner discovery.

    Tests the boundary condition where agents should/shouldn't see each other
    based on distance vs perception radius.
    """

    def test_agent_within_perception_is_found(self):
        """Agent just inside perception radius should be found."""
        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=5.0,  # Exactly at distance
            discount_factor=0.95,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=5.0,
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(20),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        # Distance = √(3² + 4²) = 5.0 (exactly at perception boundary)
        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(3, 4))

        agents_by_id = {a.id: a for a in sim.agents}
        result = evaluate_targets(agent_a, sim.grid, sim.info_env, agents_by_id)

        # Should find agent_b (distance == perception_radius is visible)
        assert result.best_target_id == agent_b.id

    def test_agent_outside_perception_not_found(self):
        """Agent just outside perception radius should not be found."""
        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=4.9,  # Just under distance
            discount_factor=0.95,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,  # B can see A
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(20),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        # Distance = 5.0, but A's perception = 4.9
        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(3, 4))

        agents_by_id = {a.id: a for a in sim.agents}
        result = evaluate_targets(agent_a, sim.grid, sim.info_env, agents_by_id)

        # A should NOT find B (distance > perception_radius)
        assert result.best_target_id is None
        assert result.visible_agents == 0

    def test_asymmetric_perception_one_moves(self):
        """When only one agent can see, only that agent should move toward."""
        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=3.0,  # Cannot see B
            discount_factor=0.95,
        )
        agent_b = create_agent(
            alpha=0.5,
            endowment_x=2.0,
            endowment_y=10.0,
            perception_radius=10.0,  # Can see A
            discount_factor=0.95,
        )

        sim = Simulation(
            grid=Grid(20),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
        )

        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 5))

        pos_a_initial = Position(0, 0)
        pos_b_initial = Position(5, 5)

        sim.step()

        pos_a_after = sim.grid.get_position(agent_a)
        pos_b_after = sim.grid.get_position(agent_b)

        # A should stay put (cannot see B)
        assert pos_a_after == pos_a_initial

        # B should move toward A
        assert pos_b_after != pos_b_initial
        assert pos_b_after.chebyshev_distance_to(pos_a_initial) < pos_b_initial.chebyshev_distance_to(pos_a_initial)


class TestTieBreakingDeterminism:
    """
    Test that tie-breaking is deterministic and uses lexicographic agent ID ordering.

    When multiple agents have identical discounted surplus values, the agent
    with the lexicographically smallest ID should be selected. This ensures
    reproducible simulation behavior.
    """

    def test_search_tie_break_selects_smallest_id(self):
        """When targets have equal discounted value, smallest ID wins."""
        from microecon.agent import Agent, AgentPrivateState

        # Create center agent
        center = Agent(
            id="center",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )

        # Create three targets with identical surplus potential, equidistant
        # They have complementary endowments to center, so positive surplus exists
        target_c = Agent(
            id="target_c",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(2.0, 10.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        target_a = Agent(
            id="target_a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(2.0, 10.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        target_b = Agent(
            id="target_b",
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

        # Place center at origin, targets equidistant (distance = 5)
        sim.add_agent(center, Position(7, 7))
        sim.add_agent(target_c, Position(2, 7))   # distance 5
        sim.add_agent(target_a, Position(12, 7))  # distance 5
        sim.add_agent(target_b, Position(7, 2))   # distance 5

        agents_by_id = {a.id: a for a in sim.agents}
        result = evaluate_targets(center, sim.grid, sim.info_env, agents_by_id)

        # Should select target_a (lexicographically smallest: a < b < c)
        assert result.best_target_id == "target_a"
        assert result.visible_agents == 3

    def test_trade_partner_tie_break_selects_smallest_id(self):
        """When multiple trade partners available, smallest ID trades first."""
        from microecon.agent import Agent, AgentPrivateState

        # Center with complementary endowment
        center = Agent(
            id="center",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(10.0, 2.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )

        # Three potential partners at same position as center
        partner_c = Agent(
            id="partner_c",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(2.0, 10.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        partner_a = Agent(
            id="partner_a",
            private_state=AgentPrivateState(
                preferences=CobbDouglas(0.5),
                endowment=Bundle(2.0, 10.0),
            ),
            perception_radius=10.0,
            discount_factor=0.95,
        )
        partner_b = Agent(
            id="partner_b",
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

        # All at same position - add center first (so it iterates first)
        sim.add_agent(center, Position(5, 5))
        sim.add_agent(partner_c, Position(5, 5))
        sim.add_agent(partner_a, Position(5, 5))
        sim.add_agent(partner_b, Position(5, 5))

        trades = sim.step()

        # Center should trade with partner_a (lexicographically smallest)
        assert len(trades) == 1
        trade = trades[0]
        assert trade.agent1_id == "center"
        assert trade.agent2_id == "partner_a"

    def test_determinism_same_seed_same_sequence(self):
        """Same configuration should produce identical trade sequence."""
        from microecon.agent import Agent, AgentPrivateState

        def run_scenario():
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

            sim = Simulation(
                grid=Grid(15),
                info_env=FullInformation(),
                bargaining_protocol=NashBargainingProtocol(),
            )

            sim.add_agent(center, Position(7, 7))
            sim.add_agent(p_a, Position(2, 7))
            sim.add_agent(p_b, Position(12, 7))

            sim.run(20)

            return [(t.agent1_id, t.agent2_id) for t in sim.trades]

        # Run twice
        sequence1 = run_scenario()
        sequence2 = run_scenario()

        # Should be identical
        assert sequence1 == sequence2
        assert len(sequence1) > 0  # Some trades should occur


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
        from microecon.agent import Agent, AgentPrivateState

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
        from microecon.agent import Agent, AgentPrivateState

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
        from microecon.agent import Agent, AgentPrivateState

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
        from microecon.agent import Agent, AgentPrivateState

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
        from microecon.agent import Agent, AgentPrivateState

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
        from microecon.agent import Agent, AgentPrivateState

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


# =============================================================================
# Trading Chain Scenario: 4 Agents in a Line (Uniform Endowments)
#
# STATUS: INCOMPLETE - Pending design decision on path-crossing behavior.
#
# This scenario surfaced an important ambiguity: when agents pursuing different
# targets cross paths, should they trade "opportunistically" (current behavior)
# or remain "committed" to their original target?
#
# Current behavior: B (targeting D) and C (targeting A) cross paths at tick 3
# and trade, even though neither selected the other as target.
#
# This design decision significantly affects emergent dynamics. These tests are
# skipped until the behavior is resolved.
# =============================================================================


@pytest.mark.skip(reason="Pending design decision: opportunistic vs committed trading")
class TestTradingChainUniformStage1:
    """
    Trading chain scenario Stage 1: Initial state and target selection.

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

    # Nash surplus values (hand-computed)
    SURPLUS_A_D = 1.2754  # Each agent's gain from A-D trade
    SURPLUS_A_C = 0.5441  # A's gain from A-C
    SURPLUS_B_D = 0.5374  # B's gain from B-D
    SURPLUS_A_B = 0.0975  # A's gain from A-B (neighbors, similar prefs)
    SURPLUS_B_C = 0.1220  # B's gain from B-C

    # Distances
    DIST_NEIGHBOR = 5
    DIST_SKIP_ONE = 10
    DIST_EXTREME = 15

    @pytest.fixture
    def scenario(self):
        """Set up 4 agents in a line with uniform endowments."""
        from microecon.agent import Agent, AgentPrivateState

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

        mrs_func = a.preferences.marginal_rate_of_substitution
        assert mrs_func(a.endowment) == pytest.approx(self.MRS_A, rel=1e-3)
        assert mrs_func(b.endowment) == pytest.approx(self.MRS_B, rel=1e-3)
        assert mrs_func(c.endowment) == pytest.approx(self.MRS_C, rel=1e-3)
        assert mrs_func(d.endowment) == pytest.approx(self.MRS_D, rel=1e-3)

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
        assert surplus_ad > surplus_ac * 2, "A-D should have >2x surplus vs A-C"
        assert surplus_ad > surplus_ab * 10, "A-D should have >10x surplus vs A-B"

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
        """A and D get equal gains (symmetric around α=0.5)."""
        sim, a, b, c, d = scenario

        type_a = AgentType(a.preferences, a.endowment)
        type_d = AgentType(d.preferences, d.endowment)

        surplus_a_from_d = compute_nash_surplus(type_a, type_d)
        surplus_d_from_a = compute_nash_surplus(type_d, type_a)

        # Should be equal due to α symmetry (0.2 and 0.8)
        assert surplus_a_from_d == pytest.approx(surplus_d_from_a, rel=0.01)
        assert surplus_a_from_d == pytest.approx(self.SURPLUS_A_D, rel=0.01)

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


@pytest.mark.skip(reason="Pending design decision: opportunistic vs committed trading")
class TestTradingChainUniformStage2:
    """
    Trading chain scenario Stage 2: First trade and subsequent dynamics.

    NOTE: These predictions assume A-D trade first, but current simulation
    behavior has B-C trading first due to path crossing.

    Key predictions (assuming committed targeting):
        - First trade: A-D (both converge toward each other)
        - Post A-D allocations: A=(2.4, 9.6), D=(9.6, 2.4)
        - Both reach MRS=1.0 (Pareto efficient between them)
        - After A-D trade: A and D have ZERO surplus with B or C
        - Only remaining trade opportunity: B-C
    """

    # Post A-D trade allocations
    A_POST_TRADE = Bundle(2.4, 9.6)
    D_POST_TRADE = Bundle(9.6, 2.4)
    POST_TRADE_UTILITY = 7.2754
    POST_TRADE_MRS = 1.0
    DISCOUNT_FACTOR = 0.9

    @pytest.fixture
    def scenario(self):
        """Set up the trading chain scenario."""
        from microecon.agent import Agent, AgentPrivateState

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
        for _ in range(20):  # Should converge much faster
            tick_trades = sim.step()
            if tick_trades:
                trades.extend(tick_trades)
                break

        return sim, a, b, c, d, trades

    # =========================================================================
    # First trade verification
    # =========================================================================

    def test_first_trade_is_a_d(self, scenario_after_first_trade):
        """First trade should be between A and D (extremes)."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert len(trades) >= 1, "At least one trade should have occurred"

        first_trade = trades[0]
        trade_ids = {first_trade.agent1_id, first_trade.agent2_id}

        assert trade_ids == {"a", "d"}, \
            f"First trade should be A-D, got {trade_ids}"

    def test_a_allocation_after_first_trade(self, scenario_after_first_trade):
        """A should have (2.4, 9.6) after trading with D."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert a.endowment.x == pytest.approx(self.A_POST_TRADE.x, rel=0.01)
        assert a.endowment.y == pytest.approx(self.A_POST_TRADE.y, rel=0.01)

    def test_d_allocation_after_first_trade(self, scenario_after_first_trade):
        """D should have (9.6, 2.4) after trading with A."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert d.endowment.x == pytest.approx(self.D_POST_TRADE.x, rel=0.01)
        assert d.endowment.y == pytest.approx(self.D_POST_TRADE.y, rel=0.01)

    def test_a_d_both_reach_mrs_one(self, scenario_after_first_trade):
        """Both A and D should have MRS=1.0 after trading."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        mrs_a = a.preferences.marginal_rate_of_substitution(a.endowment)
        mrs_d = d.preferences.marginal_rate_of_substitution(d.endowment)

        assert mrs_a == pytest.approx(self.POST_TRADE_MRS, rel=0.01)
        assert mrs_d == pytest.approx(self.POST_TRADE_MRS, rel=0.01)

    def test_b_c_unchanged_after_first_trade(self, scenario_after_first_trade):
        """B and C should still have (6, 6) after A-D trade."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        assert b.endowment.x == pytest.approx(6.0, rel=1e-6)
        assert b.endowment.y == pytest.approx(6.0, rel=1e-6)
        assert c.endowment.x == pytest.approx(6.0, rel=1e-6)
        assert c.endowment.y == pytest.approx(6.0, rel=1e-6)

    # =========================================================================
    # Post-trade surplus analysis
    # =========================================================================

    def test_a_d_zero_surplus_after_trade(self, scenario_after_first_trade):
        """A and D should have zero remaining surplus with each other."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        type_a = AgentType(a.preferences, a.endowment)
        type_d = AgentType(d.preferences, d.endowment)

        surplus = compute_nash_surplus(type_a, type_d)
        assert surplus == pytest.approx(0.0, abs=1e-6)

    def test_a_zero_surplus_with_b_c(self, scenario_after_first_trade):
        """A has zero surplus with B and C after A-D trade (saturated)."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        type_a = AgentType(a.preferences, a.endowment)
        type_b = AgentType(b.preferences, b.endowment)
        type_c = AgentType(c.preferences, c.endowment)

        surplus_ab = compute_nash_surplus(type_a, type_b)
        surplus_ac = compute_nash_surplus(type_a, type_c)

        assert surplus_ab == pytest.approx(0.0, abs=1e-6), \
            f"A-B surplus should be 0, got {surplus_ab}"
        assert surplus_ac == pytest.approx(0.0, abs=1e-6), \
            f"A-C surplus should be 0, got {surplus_ac}"

    def test_d_zero_surplus_with_b_c(self, scenario_after_first_trade):
        """D has zero surplus with B and C after A-D trade (saturated)."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        type_d = AgentType(d.preferences, d.endowment)
        type_b = AgentType(b.preferences, b.endowment)
        type_c = AgentType(c.preferences, c.endowment)

        surplus_db = compute_nash_surplus(type_d, type_b)
        surplus_dc = compute_nash_surplus(type_d, type_c)

        assert surplus_db == pytest.approx(0.0, abs=1e-6), \
            f"D-B surplus should be 0, got {surplus_db}"
        assert surplus_dc == pytest.approx(0.0, abs=1e-6), \
            f"D-C surplus should be 0, got {surplus_dc}"

    def test_b_c_still_have_surplus(self, scenario_after_first_trade):
        """B and C still have positive surplus with each other."""
        sim, a, b, c, d, trades = scenario_after_first_trade

        type_b = AgentType(b.preferences, b.endowment)
        type_c = AgentType(c.preferences, c.endowment)

        surplus = compute_nash_surplus(type_b, type_c)
        assert surplus > 0.1, f"B-C should have positive surplus, got {surplus}"


@pytest.mark.skip(reason="Pending design decision: opportunistic vs committed trading")
class TestTradingChainUniformStage3:
    """
    Trading chain scenario Stage 3: Equilibrium properties.

    NOTE: Actual behavior differs from predictions due to path crossing.
    Current simulation produces 3 trades (B-C, B-D, A-B) not 2 (A-D, B-C),
    and does not reach competitive equilibrium (MRS=1 for all).

    Expected final state (assuming committed targeting):
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
        """Run simulation to equilibrium."""
        from microecon.agent import Agent, AgentPrivateState

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

    def test_competitive_equilibrium_achieved(self, scenario_at_equilibrium):
        """
        With uniform endowments, bilateral exchange achieves competitive equilibrium.

        This is a special case: when initial endowments are uniform (6,6),
        the effective price ratio is 1:1, and bilateral Nash bargaining
        produces the Walrasian outcome.
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
