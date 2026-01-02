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
