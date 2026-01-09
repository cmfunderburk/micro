"""
THEORY: Verify TIOLI (Take-It-Or-Leave-It) Bargaining Properties.

Tests verifying TIOLIBargainingProtocol and tioli_bargaining_solution()
correctly implement TIOLI properties from O&R Bargaining Chapter 3:

1. Proposer extracts full surplus - No feasible allocation gives proposer more
   while responder >= disagreement
2. Responder at indifference - responder_utility == disagreement_utility (within 1e-6)
3. Pareto efficiency - Allocation on contract curve
4. Proposer identity matters - Swapping proposer swaps surplus recipient

Theoretical References:
- Osborne & Rubinstein, Bargaining and Markets, Chapter 3
- theoretical-foundations.md

Test tolerance: 1e-6 for closed-form solutions
"""

import pytest
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import create_agent
from microecon.bargaining import (
    tioli_bargaining_solution,
    nash_bargaining_solution,
    TIOLIBargainingProtocol,
)

pytestmark = pytest.mark.theory


class TestTIOLIProposerExtractsFullSurplus:
    """
    FEAT-006: Test that TIOLI proposer receives maximum utility consistent
    with responder's IR constraint.

    The proposer should extract all surplus - no feasible allocation should
    give the proposer more utility while still giving the responder at least
    their disagreement utility.
    """

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        # Standard case - gains from trade exist
        (0.8, 0.2, 5.0, 15.0, 15.0, 5.0),
        # Symmetric preferences, asymmetric endowments
        (0.5, 0.5, 10.0, 2.0, 2.0, 10.0),
        # Asymmetric preferences
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        # Strong preference asymmetry
        (0.9, 0.1, 5.0, 20.0, 20.0, 5.0),
        # Nearly equal endowments
        (0.4, 0.6, 10.0, 10.0, 12.0, 8.0),
    ])
    def test_proposer_extracts_full_surplus(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        Verify via grid search that no feasible allocation gives proposer more
        utility while responder >= disagreement.
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        # Disagreement utilities
        d1 = prefs_1.utility(endowment_1)
        d2 = prefs_2.utility(endowment_2)

        # TIOLI with agent 1 as proposer
        outcome = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=1
        )

        if not outcome.trade_occurred:
            # No beneficial trade - skip grid search
            return

        proposer_utility = outcome.utility_1
        responder_utility = outcome.utility_2

        # Grid search to verify no feasible allocation beats proposer utility
        # while keeping responder >= disagreement
        W_x = e1_x + e2_x
        W_y = e1_y + e2_y
        n_points = 50

        for i in range(1, n_points):
            for j in range(1, n_points):
                x1 = (i / n_points) * W_x
                y1 = (j / n_points) * W_y
                x2 = W_x - x1
                y2 = W_y - y1

                if x2 < 0 or y2 < 0:
                    continue

                test_u1 = prefs_1.utility(Bundle(x1, y1))
                test_u2 = prefs_2.utility(Bundle(x2, y2))

                # Check if responder meets IR constraint
                if test_u2 >= d2 - 1e-9:
                    # Proposer should not be able to do better
                    assert proposer_utility >= test_u1 - 1e-6, (
                        f"Found feasible allocation with higher proposer utility: "
                        f"TIOLI={proposer_utility:.6f}, test={test_u1:.6f} "
                        f"at ({x1:.2f}, {y1:.2f}) with responder u2={test_u2:.6f} >= d2={d2:.6f}"
                    )

    def test_proposer_gets_more_than_nash(self):
        """TIOLI proposer should get more than symmetric Nash would give."""
        prefs_1 = CobbDouglas(0.7)
        prefs_2 = CobbDouglas(0.3)
        endowment_1 = Bundle(5.0, 15.0)
        endowment_2 = Bundle(15.0, 5.0)

        tioli = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=1
        )
        nash = nash_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2
        )

        if tioli.trade_occurred and nash.trade_occurred:
            # TIOLI proposer should get at least as much as Nash
            # (actually more, since they extract all surplus)
            assert tioli.utility_1 >= nash.utility_1 - 1e-6, (
                f"TIOLI proposer utility {tioli.utility_1} < Nash {nash.utility_1}"
            )


class TestTIOLIResponderAtIndifference:
    """
    FEAT-007: Test that TIOLI responder receives exactly their disagreement
    utility (within tolerance).

    This is THE defining property of TIOLI - the responder is indifferent
    between accepting and rejecting the offer.
    """

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        # Standard case
        (0.8, 0.2, 5.0, 15.0, 15.0, 5.0),
        # Symmetric
        (0.5, 0.5, 10.0, 2.0, 2.0, 10.0),
        # Asymmetric
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
        (0.9, 0.1, 5.0, 20.0, 20.0, 5.0),
        (0.4, 0.6, 10.0, 10.0, 12.0, 8.0),
        # Edge: small endowments
        (0.5, 0.5, 1.0, 5.0, 5.0, 1.0),
    ])
    def test_responder_utility_equals_disagreement(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        Responder utility must equal disagreement utility within 1e-6.
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        # Agent 1 as proposer, Agent 2 as responder
        d2 = prefs_2.utility(endowment_2)
        outcome = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=1
        )

        if outcome.trade_occurred:
            assert abs(outcome.utility_2 - d2) < 1e-6, (
                f"Responder utility {outcome.utility_2} != disagreement {d2}, "
                f"difference = {abs(outcome.utility_2 - d2)}"
            )
            # Gains should be essentially zero
            assert abs(outcome.gains_2) < 1e-6, (
                f"Responder gains {outcome.gains_2} should be ~0"
            )

    def test_responder_indifference_both_directions(self):
        """Test responder indifference when either agent proposes."""
        prefs_1 = CobbDouglas(0.6)
        prefs_2 = CobbDouglas(0.4)
        endowment_1 = Bundle(8.0, 12.0)
        endowment_2 = Bundle(12.0, 8.0)

        d1 = prefs_1.utility(endowment_1)
        d2 = prefs_2.utility(endowment_2)

        # Agent 1 proposes -> Agent 2 is responder
        outcome_1 = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=1
        )
        if outcome_1.trade_occurred:
            assert abs(outcome_1.utility_2 - d2) < 1e-6, (
                f"When A1 proposes, responder (A2) utility {outcome_1.utility_2} != d2 {d2}"
            )

        # Agent 2 proposes -> Agent 1 is responder
        outcome_2 = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=2
        )
        if outcome_2.trade_occurred:
            assert abs(outcome_2.utility_1 - d1) < 1e-6, (
                f"When A2 proposes, responder (A1) utility {outcome_2.utility_1} != d1 {d1}"
            )


class TestTIOLIProposerIdentityMatters:
    """
    FEAT-008: Test that swapping which agent proposes swaps who receives
    the surplus.

    This distinguishes TIOLI from symmetric protocols like Nash.
    """

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.8, 0.2, 5.0, 15.0, 15.0, 5.0),
        (0.5, 0.5, 10.0, 2.0, 2.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
    ])
    def test_proposer_identity_swaps_surplus_recipient(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        When agent 1 proposes: agent 1 gets surplus, agent 2 at disagreement.
        When agent 2 proposes: agent 2 gets surplus, agent 1 at disagreement.
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        d1 = prefs_1.utility(endowment_1)
        d2 = prefs_2.utility(endowment_2)

        outcome_1prop = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=1
        )
        outcome_2prop = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=2
        )

        if outcome_1prop.trade_occurred:
            # A1 proposes: A1 should get positive gains, A2 at disagreement
            assert outcome_1prop.gains_1 > 1e-6, (
                f"Proposer A1 should have positive gains, got {outcome_1prop.gains_1}"
            )
            assert abs(outcome_1prop.utility_2 - d2) < 1e-6, (
                f"Responder A2 should be at disagreement"
            )

        if outcome_2prop.trade_occurred:
            # A2 proposes: A2 should get positive gains, A1 at disagreement
            assert outcome_2prop.gains_2 > 1e-6, (
                f"Proposer A2 should have positive gains, got {outcome_2prop.gains_2}"
            )
            assert abs(outcome_2prop.utility_1 - d1) < 1e-6, (
                f"Responder A1 should be at disagreement"
            )

    def test_total_surplus_same_regardless_of_proposer(self):
        """
        Total gains from trade should be approximately equal regardless of
        who proposes (Pareto efficiency), but distribution differs completely.
        """
        prefs_1 = CobbDouglas(0.7)
        prefs_2 = CobbDouglas(0.3)
        endowment_1 = Bundle(5.0, 15.0)
        endowment_2 = Bundle(15.0, 5.0)

        outcome_1prop = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=1
        )
        outcome_2prop = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=2
        )

        if outcome_1prop.trade_occurred and outcome_2prop.trade_occurred:
            # The proposer takes all surplus in each case
            # So outcome_1prop.gains_1 ≈ outcome_2prop.gains_2 ≈ total_gains
            # And outcome_1prop.gains_2 ≈ outcome_2prop.gains_1 ≈ 0

            # Both proposers should get similar total surplus
            # (not exact due to different optimal allocations)
            assert abs(outcome_1prop.gains_1 - outcome_2prop.gains_2) < 0.5, (
                f"Proposer surplus should be similar regardless of identity: "
                f"A1 as proposer gets {outcome_1prop.gains_1}, "
                f"A2 as proposer gets {outcome_2prop.gains_2}"
            )


class TestTIOLIProtocolClass:
    """Test TIOLIBargainingProtocol class specifically."""

    def test_protocol_uses_lexicographic_proposer_by_default(self):
        """Default proposer selection should be lexicographically smaller ID."""
        a1 = create_agent(alpha=0.6, endowment_x=5, endowment_y=15, agent_id='aaa')
        a2 = create_agent(alpha=0.4, endowment_x=15, endowment_y=5, agent_id='bbb')

        protocol = TIOLIBargainingProtocol()
        outcome = protocol.solve(a1, a2)

        # 'aaa' < 'bbb', so a1 should propose, a2 should be at disagreement
        d2 = a2.preferences.utility(a2.endowment)
        if outcome.trade_occurred:
            assert abs(outcome.utility_2 - d2) < 1e-6, (
                f"Agent with larger ID (bbb) should be responder at disagreement"
            )

    def test_protocol_explicit_proposer_overrides_default(self):
        """Explicit proposer parameter should override lexicographic default."""
        a1 = create_agent(alpha=0.6, endowment_x=5, endowment_y=15, agent_id='aaa')
        a2 = create_agent(alpha=0.4, endowment_x=15, endowment_y=5, agent_id='bbb')

        protocol = TIOLIBargainingProtocol()

        # Explicitly make a2 the proposer (overriding lexicographic default)
        outcome = protocol.solve(a1, a2, proposer=a2)

        # Now a1 should be at disagreement
        d1 = a1.preferences.utility(a1.endowment)
        if outcome.trade_occurred:
            assert abs(outcome.utility_1 - d1) < 1e-6, (
                f"When a2 explicitly proposes, a1 should be at disagreement"
            )

    def test_protocol_compute_expected_surplus(self):
        """Test compute_expected_surplus method."""
        a1 = create_agent(alpha=0.7, endowment_x=5, endowment_y=15, agent_id='a')
        a2 = create_agent(alpha=0.3, endowment_x=15, endowment_y=5, agent_id='b')

        protocol = TIOLIBargainingProtocol()
        surplus = protocol.compute_expected_surplus(a1, a2)

        # Since a1.id < a2.id, a1 proposes, so a1 should get all surplus
        outcome = protocol.solve(a1, a2)
        assert abs(surplus - outcome.gains_1) < 1e-9


class TestTIOLIParetoEfficiency:
    """Test that TIOLI allocations are Pareto efficient."""

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.8, 0.2, 5.0, 15.0, 15.0, 5.0),
        (0.5, 0.5, 10.0, 2.0, 2.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
    ])
    def test_tioli_is_pareto_efficient(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """
        TIOLI allocation should be on the Pareto frontier - no reallocation
        can make one agent better off without making the other worse off.
        """
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        outcome = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=1
        )

        if not outcome.trade_occurred:
            return

        u1_tioli = outcome.utility_1
        u2_tioli = outcome.utility_2

        # Grid search: no allocation should Pareto dominate TIOLI
        W_x = e1_x + e2_x
        W_y = e1_y + e2_y
        n_points = 50

        for i in range(1, n_points):
            for j in range(1, n_points):
                x1 = (i / n_points) * W_x
                y1 = (j / n_points) * W_y
                x2 = W_x - x1
                y2 = W_y - y1

                if x2 < 0 or y2 < 0:
                    continue

                test_u1 = prefs_1.utility(Bundle(x1, y1))
                test_u2 = prefs_2.utility(Bundle(x2, y2))

                # No allocation should make both strictly better
                pareto_dominates = (
                    test_u1 > u1_tioli + 1e-6 and test_u2 > u2_tioli + 1e-6
                )
                assert not pareto_dominates, (
                    f"Found Pareto dominating allocation: "
                    f"TIOLI=({u1_tioli:.4f}, {u2_tioli:.4f}), "
                    f"test=({test_u1:.4f}, {test_u2:.4f})"
                )


class TestTIOLIFeasibility:
    """Test that TIOLI allocations are feasible."""

    @pytest.mark.parametrize("alpha1,alpha2,e1_x,e1_y,e2_x,e2_y", [
        (0.8, 0.2, 5.0, 15.0, 15.0, 5.0),
        (0.5, 0.5, 10.0, 2.0, 2.0, 10.0),
        (0.3, 0.7, 10.0, 5.0, 5.0, 10.0),
    ])
    def test_tioli_allocation_exhausts_resources(
        self, alpha1, alpha2, e1_x, e1_y, e2_x, e2_y
    ):
        """Allocation should sum to total endowment (no waste)."""
        prefs_1 = CobbDouglas(alpha1)
        prefs_2 = CobbDouglas(alpha2)
        endowment_1 = Bundle(e1_x, e1_y)
        endowment_2 = Bundle(e2_x, e2_y)

        outcome = tioli_bargaining_solution(
            prefs_1, endowment_1, prefs_2, endowment_2, proposer=1
        )

        W_x = e1_x + e2_x
        W_y = e1_y + e2_y

        total_x = outcome.allocation_1.x + outcome.allocation_2.x
        total_y = outcome.allocation_1.y + outcome.allocation_2.y

        assert abs(total_x - W_x) < 1e-6, (
            f"X allocation {total_x} != total {W_x}"
        )
        assert abs(total_y - W_y) < 1e-6, (
            f"Y allocation {total_y} != total {W_y}"
        )

    def test_tioli_allocations_non_negative(self):
        """All allocations should be non-negative."""
        prefs_1 = CobbDouglas(0.3)
        prefs_2 = CobbDouglas(0.7)
        endowment_1 = Bundle(10.0, 5.0)
        endowment_2 = Bundle(5.0, 10.0)

        for proposer in [1, 2]:
            outcome = tioli_bargaining_solution(
                prefs_1, endowment_1, prefs_2, endowment_2, proposer=proposer
            )

            assert outcome.allocation_1.x >= -1e-9, "Allocation 1.x negative"
            assert outcome.allocation_1.y >= -1e-9, "Allocation 1.y negative"
            assert outcome.allocation_2.x >= -1e-9, "Allocation 2.x negative"
            assert outcome.allocation_2.y >= -1e-9, "Allocation 2.y negative"


class TestTIOLIProposerSelection:
    """
    Test that TIOLI proposer selection is consistent between
    select_proposer() and solve()/compute_expected_surplus().

    This ensures search evaluation and execution use the same proposer.
    """

    def test_select_proposer_returns_lexicographic_smaller(self):
        """select_proposer should return agent with smaller ID."""
        a1 = create_agent(alpha=0.5, endowment_x=10, endowment_y=5, agent_id='aaa')
        a2 = create_agent(alpha=0.5, endowment_x=5, endowment_y=10, agent_id='bbb')

        protocol = TIOLIBargainingProtocol()

        # a1.id ('aaa') < a2.id ('bbb'), so a1 should propose
        assert protocol.select_proposer(a1, a2) is a1
        assert protocol.select_proposer(a2, a1) is a1  # Order shouldn't matter

    def test_select_proposer_ignores_rng(self):
        """TIOLI select_proposer should be deterministic (ignore rng)."""
        import random
        a1 = create_agent(alpha=0.5, endowment_x=10, endowment_y=5, agent_id='xyz')
        a2 = create_agent(alpha=0.5, endowment_x=5, endowment_y=10, agent_id='abc')

        protocol = TIOLIBargainingProtocol()
        rng = random.Random(12345)

        # a2.id ('abc') < a1.id ('xyz'), so a2 should always propose
        for _ in range(10):
            assert protocol.select_proposer(a1, a2, rng) is a2

    def test_select_proposer_consistent_with_solve(self):
        """select_proposer and solve should use same proposer logic."""
        a1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id='first')
        a2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id='second')

        protocol = TIOLIBargainingProtocol()

        # Get the expected proposer
        expected_proposer = protocol.select_proposer(a1, a2)
        assert expected_proposer is a1  # 'first' < 'second'

        # Solve without explicit proposer (should use same logic)
        outcome_default = protocol.solve(a1, a2)

        # Solve with explicit proposer = a1
        outcome_explicit = protocol.solve(a1, a2, proposer=a1)

        # Should be identical since default proposer is a1
        assert abs(outcome_default.gains_1 - outcome_explicit.gains_1) < 1e-9
        assert abs(outcome_default.gains_2 - outcome_explicit.gains_2) < 1e-9

    def test_select_proposer_consistent_with_expected_surplus(self):
        """select_proposer and compute_expected_surplus should agree."""
        a1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id='alpha')
        a2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id='beta')

        protocol = TIOLIBargainingProtocol()

        # a1 ('alpha') < a2 ('beta'), so a1 proposes and gets all surplus
        expected_proposer = protocol.select_proposer(a1, a2)
        assert expected_proposer is a1

        # Expected surplus for a1 (proposer) should equal all gains
        surplus_a1 = protocol.compute_expected_surplus(a1, a2)
        outcome = protocol.solve(a1, a2)

        # a1 is proposer, so a1's surplus should equal total surplus
        assert abs(surplus_a1 - outcome.total_gains) < 1e-6, (
            f"Proposer surplus {surplus_a1} != total gains {outcome.total_gains}"
        )

        # a2's surplus should be ~0 (responder at indifference)
        surplus_a2 = protocol.compute_expected_surplus(a2, a1)
        assert abs(surplus_a2) < 1e-6, f"Responder surplus {surplus_a2} should be ~0"
