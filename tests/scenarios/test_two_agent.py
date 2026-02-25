"""
Two-agent theoretical scenario tests.

Test classes:
- TestTwoAgentSymmetricScenario: Identical preferences, complementary endowments
- TestTwoAgentNoTradeScenario: No gains from trade exist
- TestTwoAgentAsymmetricScenario: Mirror-symmetric preferences
- TestRubinsteinProtocol: Alternating-offers bargaining protocol
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

    def test_agents_eventually_meet_or_trade(self, scenario):
        """Agents should get adjacent (for trade) within Chebyshev distance ticks."""
        sim, agent_a, agent_b = scenario

        # Run for enough ticks to guarantee adjacency/meeting
        # With both moving, should get adjacent in ceil(5/2) = 3 ticks at most
        # With adjacency-based trading, trade may occur before exact co-location
        for _ in range(self.CHEBYSHEV_DISTANCE):
            sim.step()
            pos_a = sim.grid.get_position(agent_a)
            pos_b = sim.grid.get_position(agent_b)
            # Adjacent means Chebyshev distance <= 1 (includes co-located)
            if pos_a.chebyshev_distance_to(pos_b) <= 1:
                break

        pos_a = sim.grid.get_position(agent_a)
        pos_b = sim.grid.get_position(agent_b)
        # With adjacency-based trading, agents trade when adjacent (not necessarily co-located)
        assert pos_a.chebyshev_distance_to(pos_b) <= 1 or len(sim.trades) > 0

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
        assert sim.trades[0].trade_occurred

    def test_allocation_matches_nash_solution(self, scenario):
        """Post-trade allocations should be (6, 6) for each."""
        sim, agent_a, agent_b = scenario

        # Run until trade occurs
        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        # Verify exact allocations (within numerical tolerance)
        # Note: After trade, check holdings (current allocation) not endowment (initial)
        assert agent_a.holdings.x == pytest.approx(self.POST_TRADE_ALLOCATION[0], rel=0.01)
        assert agent_a.holdings.y == pytest.approx(self.POST_TRADE_ALLOCATION[1], rel=0.01)
        assert agent_b.holdings.x == pytest.approx(self.POST_TRADE_ALLOCATION[0], rel=0.01)
        assert agent_b.holdings.y == pytest.approx(self.POST_TRADE_ALLOCATION[1], rel=0.01)

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
        mrs_a = agent_a.preferences.marginal_rate_of_substitution(agent_a.holdings)
        mrs_b = agent_b.preferences.marginal_rate_of_substitution(agent_b.holdings)

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

        final_total_x = agent_a.holdings.x + agent_b.holdings.x
        final_total_y = agent_a.holdings.y + agent_b.holdings.y

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

        # Compute surplus with post-trade holdings
        type_a = AgentType(agent_a.preferences, agent_a.holdings)
        type_b = AgentType(agent_b.preferences, agent_b.holdings)

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

        initial_holdings_a = (agent_a.holdings.x, agent_a.holdings.y)
        initial_holdings_b = (agent_b.holdings.x, agent_b.holdings.y)

        # Run several ticks
        for _ in range(5):
            sim.step()

        # No trades should occur
        assert len(sim.trades) == 0

        # Holdings unchanged (no trades occurred)
        assert (agent_a.holdings.x, agent_a.holdings.y) == initial_holdings_a
        assert (agent_b.holdings.x, agent_b.holdings.y) == initial_holdings_b

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
        assert agent_a.holdings.x < initial_a_x
        assert agent_a.holdings.y > initial_a_y

        # B should have more x, less y
        assert agent_b.holdings.x > initial_b_x
        assert agent_b.holdings.y < initial_b_y

    def test_allocation_matches_theory(self, scenario):
        """Post-trade allocations should match Nash solution: A=(3,9), B=(9,3)."""
        sim, agent_a, agent_b = scenario

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        assert agent_a.holdings.x == pytest.approx(self.POST_TRADE_ALLOCATION_A[0], rel=0.01)
        assert agent_a.holdings.y == pytest.approx(self.POST_TRADE_ALLOCATION_A[1], rel=0.01)
        assert agent_b.holdings.x == pytest.approx(self.POST_TRADE_ALLOCATION_B[0], rel=0.01)
        assert agent_b.holdings.y == pytest.approx(self.POST_TRADE_ALLOCATION_B[1], rel=0.01)

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
        assert trade.gains[0] == pytest.approx(trade.gains[1], rel=0.01)

    def test_pareto_efficiency(self, scenario):
        """Post-trade allocation should have equal MRS = 1.0."""
        sim, agent_a, agent_b = scenario

        for _ in range(10):
            trades = sim.step()
            if trades:
                break

        mrs_a = agent_a.preferences.marginal_rate_of_substitution(agent_a.holdings)
        mrs_b = agent_b.preferences.marginal_rate_of_substitution(agent_b.holdings)

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

        type_a = AgentType(agent_a.preferences, agent_a.holdings)
        type_b = AgentType(agent_b.preferences, agent_b.holdings)

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

    def test_equal_delta_gives_equal_shares(self, symmetric_agents):
        """Equal patience (δ1 = δ2) should give equal shares (BRW formulation).

        Under BRW (1986), when discount factors are equal, the bargaining
        weights are equal, giving the symmetric Nash solution.
        """
        from microecon.bargaining import RubinsteinBargainingProtocol, compute_brw_weights

        sim, agent_a, agent_b = symmetric_agents
        protocol = RubinsteinBargainingProtocol()

        # BRW weights should be equal when δ1 = δ2
        w1, w2 = compute_brw_weights(0.9, 0.9)
        assert w1 == pytest.approx(0.5, rel=1e-6)
        assert w2 == pytest.approx(0.5, rel=1e-6)

        outcome = protocol.solve(agent_a, agent_b, proposer=agent_a)

        # Equal patience → equal shares (approximately)
        actual_share = outcome.gains_1 / outcome.total_gains
        assert actual_share == pytest.approx(0.5, rel=0.01)

    def test_proposer_identity_irrelevant_brw(self, symmetric_agents):
        """Proposer identity should not affect outcome under BRW formulation.

        Under BRW (1986), the Rubinstein outcome for exchange economies
        depends on patience ratio, not proposer identity.
        """
        from microecon.bargaining import RubinsteinBargainingProtocol

        sim, agent_a, agent_b = symmetric_agents
        protocol = RubinsteinBargainingProtocol()

        # Outcomes should be identical regardless of proposer
        outcome_a_proposes = protocol.solve(agent_a, agent_b, proposer=agent_a)
        outcome_b_proposes = protocol.solve(agent_a, agent_b, proposer=agent_b)

        assert outcome_a_proposes.gains_1 == pytest.approx(outcome_b_proposes.gains_1, rel=1e-6)
        assert outcome_a_proposes.gains_2 == pytest.approx(outcome_b_proposes.gains_2, rel=1e-6)

    def test_brw_weights_formula(self, symmetric_agents):
        """Surplus shares should match BRW asymmetric Nash weights."""
        from microecon.bargaining import RubinsteinBargainingProtocol, compute_brw_weights

        sim, agent_a, agent_b = symmetric_agents
        protocol = RubinsteinBargainingProtocol()

        outcome = protocol.solve(agent_a, agent_b)

        # Get BRW weights
        w1, w2 = compute_brw_weights(0.9, 0.9)

        # With equal δ, shares should be ~0.5 each
        actual_share_a = outcome.gains_1 / outcome.total_gains
        actual_share_b = outcome.gains_2 / outcome.total_gains

        # Note: actual shares differ from weights due to non-linear utility
        # but with equal weights and symmetric setup, shares should be equal
        assert actual_share_a == pytest.approx(0.5, rel=0.01)
        assert actual_share_b == pytest.approx(0.5, rel=0.01)

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

        mrs_a = agent_a.preferences.marginal_rate_of_substitution(agent_a.holdings)
        mrs_b = agent_b.preferences.marginal_rate_of_substitution(agent_b.holdings)

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
        assert trade.gains[0] > trade.gains[1]

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

        # solve() doesn't modify agents, so we can call both without reset
        nash_outcome = nash_protocol.solve(agent_a, agent_b)
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
        type_a = AgentType(agent_a.preferences, agent_a.holdings)
        type_b = AgentType(agent_b.preferences, agent_b.holdings)

        surplus = compute_nash_surplus(type_a, type_b)

        # Should be essentially zero
        assert surplus == pytest.approx(0.0, abs=0.1)
