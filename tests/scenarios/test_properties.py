"""
Behavioral property tests for simulation invariants.

Test classes:
- TestNashSymmetry: Nash solution symmetry with respect to agent ordering
- TestPerceptionBoundary: Perception radius boundary conditions
- TestTieBreakingDeterminism: Deterministic tie-breaking with lexicographic ordering
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

        # Chebyshev distance = max(5, 0) = 5 (exactly at perception boundary)
        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 0))

        agents_by_id = {a.id: a for a in sim.agents}
        result = evaluate_targets(agent_a, sim.grid, sim.info_env, agents_by_id)

        # Should find agent_b (Chebyshev distance == perception_radius is visible)
        assert result.best_target_id == agent_b.id

    def test_agent_outside_perception_not_found(self):
        """Agent just outside perception radius should not be found."""
        agent_a = create_agent(
            alpha=0.5,
            endowment_x=10.0,
            endowment_y=2.0,
            perception_radius=4.9,  # Just under Chebyshev distance of 5
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

        # Chebyshev distance = max(5, 3) = 5, but A's perception = 4.9
        sim.add_agent(agent_a, Position(0, 0))
        sim.add_agent(agent_b, Position(5, 3))

        agents_by_id = {a.id: a for a in sim.agents}
        result = evaluate_targets(agent_a, sim.grid, sim.info_env, agents_by_id)

        # A should NOT find B (Chebyshev distance 5 > perception_radius 4.9)
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
