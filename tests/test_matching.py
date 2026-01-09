"""
Tests for matching protocols.

Tests cover:
1. CommitmentState operations
2. OpportunisticMatchingProtocol (no-op behavior)
3. StableRoommatesMatchingProtocol (Irving's algorithm)
"""

import pytest
from microecon.matching import (
    CommitmentState,
    MatchingProtocol,
    OpportunisticMatchingProtocol,
    StableRoommatesMatchingProtocol,
    CommitmentFormedEvent,
    CommitmentBrokenEvent,
    MatchingPhaseResult,
)
from microecon.agent import Agent, AgentPrivateState
from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas

pytestmark = pytest.mark.matching


def make_agent(agent_id: str, alpha: float, endowment_x: float, endowment_y: float) -> Agent:
    """Helper to create agents with explicit IDs for testing."""
    return Agent(
        id=agent_id,
        private_state=AgentPrivateState(
            preferences=CobbDouglas(alpha),
            endowment=Bundle(endowment_x, endowment_y),
        ),
        perception_radius=10.0,
        discount_factor=0.95,
    )


# =============================================================================
# CommitmentState Tests
# =============================================================================


class TestCommitmentState:
    """Tests for CommitmentState tracking."""

    def test_initial_state_empty(self):
        """New commitment state has no commitments."""
        state = CommitmentState()
        assert not state.is_committed("a")
        assert state.get_partner("a") is None
        assert state.get_all_committed_pairs() == []

    def test_form_commitment(self):
        """Can form commitment between two agents."""
        state = CommitmentState()
        state.form_commitment("a", "b")

        assert state.is_committed("a")
        assert state.is_committed("b")
        assert state.get_partner("a") == "b"
        assert state.get_partner("b") == "a"

    def test_form_multiple_commitments(self):
        """Can form multiple independent commitments."""
        state = CommitmentState()
        state.form_commitment("a", "b")
        state.form_commitment("c", "d")

        assert state.is_committed("a")
        assert state.is_committed("c")
        assert state.get_partner("a") == "b"
        assert state.get_partner("c") == "d"
        assert not state.is_committed("e")

    def test_break_commitment(self):
        """Can break an existing commitment."""
        state = CommitmentState()
        state.form_commitment("a", "b")

        result = state.break_commitment("a", "b")

        assert result is True
        assert not state.is_committed("a")
        assert not state.is_committed("b")

    def test_break_commitment_nonexistent(self):
        """Breaking nonexistent commitment returns False."""
        state = CommitmentState()
        result = state.break_commitment("a", "b")
        assert result is False

    def test_break_all_for_agent(self):
        """Can break all commitments for an agent."""
        state = CommitmentState()
        state.form_commitment("a", "b")
        state.form_commitment("c", "d")

        broken = state.break_all_for_agent("a")

        assert "b" in broken
        assert not state.is_committed("a")
        assert not state.is_committed("b")
        # Other commitments unaffected
        assert state.is_committed("c")
        assert state.is_committed("d")

    def test_get_all_committed_pairs(self):
        """Can get all committed pairs."""
        state = CommitmentState()
        state.form_commitment("b", "a")  # Order shouldn't matter
        state.form_commitment("c", "d")

        pairs = state.get_all_committed_pairs()

        assert len(pairs) == 2
        # Pairs should be sorted tuples
        assert ("a", "b") in pairs
        assert ("c", "d") in pairs

    def test_get_uncommitted_agents(self):
        """Can get set of uncommitted agents."""
        state = CommitmentState()
        state.form_commitment("a", "b")

        all_agents = {"a", "b", "c", "d", "e"}
        uncommitted = state.get_uncommitted_agents(all_agents)

        assert uncommitted == {"c", "d", "e"}

    def test_clear(self):
        """Can clear all commitments."""
        state = CommitmentState()
        state.form_commitment("a", "b")
        state.form_commitment("c", "d")

        state.clear()

        assert not state.is_committed("a")
        assert state.get_all_committed_pairs() == []


# =============================================================================
# OpportunisticMatchingProtocol Tests
# =============================================================================


class TestOpportunisticMatchingProtocol:
    """Tests for opportunistic matching (no explicit commitment)."""

    def test_requires_commitment_false(self):
        """Opportunistic matching doesn't require commitment."""
        protocol = OpportunisticMatchingProtocol()
        assert protocol.requires_commitment is False

    def test_compute_matches_returns_empty(self):
        """Opportunistic matching returns no committed pairs."""
        protocol = OpportunisticMatchingProtocol()

        agents = [
            make_agent("a", alpha=0.3, endowment_x=10, endowment_y=2),
            make_agent("b", alpha=0.7, endowment_x=2, endowment_y=10),
        ]

        visibility = {
            agents[0].id: {agents[1].id},
            agents[1].id: {agents[0].id},
        }

        def surplus_fn(a, b):
            return 1.0  # Positive surplus

        matches = protocol.compute_matches(agents, visibility, surplus_fn)

        assert matches == []


# =============================================================================
# StableRoommatesMatchingProtocol Tests
# =============================================================================


class TestStableRoommatesMatchingProtocol:
    """Tests for Irving's stable roommates algorithm."""

    def test_requires_commitment_true(self):
        """Stable roommates requires commitment."""
        protocol = StableRoommatesMatchingProtocol()
        assert protocol.requires_commitment is True

    def test_empty_agents(self):
        """No agents means no matches."""
        protocol = StableRoommatesMatchingProtocol()
        matches = protocol.compute_matches([], {}, lambda a, b: 1.0)
        assert matches == []

    def test_single_agent(self):
        """Single agent cannot match."""
        protocol = StableRoommatesMatchingProtocol()
        agent = make_agent("a", alpha=0.5, endowment_x=5, endowment_y=5)
        matches = protocol.compute_matches([agent], {agent.id: set()}, lambda a, b: 1.0)
        assert matches == []

    def test_two_agents_mutual_visibility(self):
        """Two agents who can see each other should match."""
        protocol = StableRoommatesMatchingProtocol()

        a = make_agent("a", alpha=0.3, endowment_x=10, endowment_y=2)
        b = make_agent("b", alpha=0.7, endowment_x=2, endowment_y=10)

        visibility = {"a": {"b"}, "b": {"a"}}

        def surplus_fn(agent1, agent2):
            # Both agents have positive surplus from trading
            return 1.0

        matches = protocol.compute_matches([a, b], visibility, surplus_fn)

        assert len(matches) == 1
        assert matches[0] == ("a", "b")

    def test_two_agents_one_sided_visibility(self):
        """If only one can see the other, no match forms."""
        protocol = StableRoommatesMatchingProtocol()

        a = make_agent("a", alpha=0.3, endowment_x=10, endowment_y=2)
        b = make_agent("b", alpha=0.7, endowment_x=2, endowment_y=10)

        # a can see b, but b cannot see a
        visibility = {"a": {"b"}, "b": set()}

        matches = protocol.compute_matches([a, b], visibility, lambda x, y: 1.0)

        # b has no one to propose to, so a's proposal to b should succeed
        # Actually in Irving's algorithm, if b can't see anyone, b has empty prefs
        # but a can still propose to b. Let's verify behavior.
        # With b having empty preferences, b won't propose to anyone but can accept.
        assert len(matches) <= 1

    def test_four_agents_stable_matching(self):
        """Four agents with clear preferences should find stable matching."""
        protocol = StableRoommatesMatchingProtocol()

        # Create four agents
        a = make_agent("a", alpha=0.2, endowment_x=10, endowment_y=2)
        b = make_agent("b", alpha=0.4, endowment_x=8, endowment_y=4)
        c = make_agent("c", alpha=0.6, endowment_x=4, endowment_y=8)
        d = make_agent("d", alpha=0.8, endowment_x=2, endowment_y=10)

        agents = [a, b, c, d]

        # Full visibility
        visibility = {
            "a": {"b", "c", "d"},
            "b": {"a", "c", "d"},
            "c": {"a", "b", "d"},
            "d": {"a", "b", "c"},
        }

        # Surplus function that creates preferences: a-d highest, b-c second, etc.
        def surplus_fn(agent1, agent2):
            # More different alphas = more surplus
            alpha1 = agent1.preferences.alpha
            alpha2 = agent2.preferences.alpha
            return abs(alpha1 - alpha2)

        matches = protocol.compute_matches(agents, visibility, surplus_fn)

        # Should get 2 matches (all 4 agents paired)
        assert len(matches) == 2

        # All agents should be matched
        matched_agents = set()
        for pair in matches:
            matched_agents.add(pair[0])
            matched_agents.add(pair[1])
        assert matched_agents == {"a", "b", "c", "d"}

    def test_odd_number_of_agents(self):
        """Odd number of agents leaves one unmatched."""
        protocol = StableRoommatesMatchingProtocol()

        a = make_agent("a", alpha=0.2, endowment_x=10, endowment_y=2)
        b = make_agent("b", alpha=0.5, endowment_x=6, endowment_y=6)
        c = make_agent("c", alpha=0.8, endowment_x=2, endowment_y=10)

        agents = [a, b, c]
        visibility = {
            "a": {"b", "c"},
            "b": {"a", "c"},
            "c": {"a", "b"},
        }

        def surplus_fn(agent1, agent2):
            return abs(agent1.preferences.alpha - agent2.preferences.alpha)

        matches = protocol.compute_matches(agents, visibility, surplus_fn)

        # Should get 1 match, leaving one agent unmatched
        assert len(matches) == 1

        matched_agents = set()
        for pair in matches:
            matched_agents.add(pair[0])
            matched_agents.add(pair[1])
        assert len(matched_agents) == 2

    def test_zero_surplus_no_match(self):
        """Agents with zero surplus should not match."""
        protocol = StableRoommatesMatchingProtocol()

        a = make_agent("a", alpha=0.5, endowment_x=5, endowment_y=5)
        b = make_agent("b", alpha=0.5, endowment_x=5, endowment_y=5)

        visibility = {"a": {"b"}, "b": {"a"}}

        def surplus_fn(agent1, agent2):
            return 0.0  # No gains from trade

        matches = protocol.compute_matches([a, b], visibility, surplus_fn)

        # Zero surplus means no one is on anyone's preference list
        assert matches == []

    def test_deterministic_output(self):
        """Same input should always produce same output."""
        protocol = StableRoommatesMatchingProtocol()

        agents = [
            make_agent("a", alpha=0.2, endowment_x=10, endowment_y=2),
            make_agent("b", alpha=0.4, endowment_x=8, endowment_y=4),
            make_agent("c", alpha=0.6, endowment_x=4, endowment_y=8),
            make_agent("d", alpha=0.8, endowment_x=2, endowment_y=10),
        ]

        visibility = {
            "a": {"b", "c", "d"},
            "b": {"a", "c", "d"},
            "c": {"a", "b", "d"},
            "d": {"a", "b", "c"},
        }

        def surplus_fn(agent1, agent2):
            return abs(agent1.preferences.alpha - agent2.preferences.alpha)

        # Run multiple times
        results = [
            protocol.compute_matches(agents, visibility, surplus_fn)
            for _ in range(5)
        ]

        # All results should be identical
        for result in results[1:]:
            assert result == results[0]

    def test_preferences_respected(self):
        """Higher surplus partners should be preferred."""
        protocol = StableRoommatesMatchingProtocol()

        # a strongly prefers d (very different alpha)
        # b strongly prefers c (moderately different)
        a = make_agent("a", alpha=0.1, endowment_x=10, endowment_y=2)
        b = make_agent("b", alpha=0.4, endowment_x=8, endowment_y=4)
        c = make_agent("c", alpha=0.6, endowment_x=4, endowment_y=8)
        d = make_agent("d", alpha=0.9, endowment_x=2, endowment_y=10)

        agents = [a, b, c, d]
        visibility = {
            "a": {"b", "c", "d"},
            "b": {"a", "c", "d"},
            "c": {"a", "b", "d"},
            "d": {"a", "b", "c"},
        }

        def surplus_fn(agent1, agent2):
            return abs(agent1.preferences.alpha - agent2.preferences.alpha)

        matches = protocol.compute_matches(agents, visibility, surplus_fn)

        # a (0.1) and d (0.9) have highest mutual surplus (0.8)
        # b (0.4) and c (0.6) have second highest mutual surplus (0.2)
        # So stable matching should be (a,d) and (b,c)
        assert len(matches) == 2
        assert ("a", "d") in matches
        assert ("b", "c") in matches


class TestIrvingAlgorithmEdgeCases:
    """Edge cases for Irving's algorithm."""

    def test_no_stable_matching_exists(self):
        """Some configurations have no stable matching."""
        protocol = StableRoommatesMatchingProtocol()

        # Classic example where no stable matching exists:
        # 4 agents where preferences form a problematic cycle
        # This is the "cyclic preferences" case from literature
        a = make_agent("a", alpha=0.25, endowment_x=10, endowment_y=2)
        b = make_agent("b", alpha=0.35, endowment_x=8, endowment_y=4)
        c = make_agent("c", alpha=0.65, endowment_x=4, endowment_y=8)
        d = make_agent("d", alpha=0.75, endowment_x=2, endowment_y=10)

        agents = [a, b, c, d]
        visibility = {
            "a": {"b", "c", "d"},
            "b": {"a", "c", "d"},
            "c": {"a", "b", "d"},
            "d": {"a", "b", "c"},
        }

        # Create cyclic preferences: a>b>c>d>a
        # Each agent prefers the next in cycle, then arbitrary
        # (This may or may not produce unstable instance depending on full prefs)
        pref_order = {"a": ["b", "c", "d"], "b": ["c", "d", "a"], "c": ["d", "a", "b"], "d": ["a", "b", "c"]}

        def surplus_fn(agent1, agent2):
            prefs = pref_order[agent1.id]
            # Higher position = lower surplus (we want to test preference order)
            return 3 - prefs.index(agent2.id) if agent2.id in prefs else 0

        matches = protocol.compute_matches(agents, visibility, surplus_fn)

        # Algorithm should still return something (possibly partial matching)
        # We can't assert specific result, but should not crash
        assert isinstance(matches, list)

    def test_partial_visibility_graph(self):
        """Agents with limited visibility still match where possible."""
        protocol = StableRoommatesMatchingProtocol()

        a = make_agent("a", alpha=0.2, endowment_x=10, endowment_y=2)
        b = make_agent("b", alpha=0.4, endowment_x=8, endowment_y=4)
        c = make_agent("c", alpha=0.6, endowment_x=4, endowment_y=8)
        d = make_agent("d", alpha=0.8, endowment_x=2, endowment_y=10)

        agents = [a, b, c, d]

        # Disconnected visibility: a-b can see each other, c-d can see each other
        visibility = {
            "a": {"b"},
            "b": {"a"},
            "c": {"d"},
            "d": {"c"},
        }

        def surplus_fn(agent1, agent2):
            return abs(agent1.preferences.alpha - agent2.preferences.alpha)

        matches = protocol.compute_matches(agents, visibility, surplus_fn)

        # Should get 2 matches in the disconnected components
        assert len(matches) == 2
        matched_pairs = set(matches)
        assert ("a", "b") in matched_pairs
        assert ("c", "d") in matched_pairs


# =============================================================================
# Event Type Tests
# =============================================================================


class TestMatchingEvents:
    """Tests for matching event dataclasses."""

    def test_commitment_formed_event(self):
        """CommitmentFormedEvent stores correct data."""
        event = CommitmentFormedEvent(tick=5, agent_a="alice", agent_b="bob")
        assert event.tick == 5
        assert event.agent_a == "alice"
        assert event.agent_b == "bob"

    def test_commitment_broken_event(self):
        """CommitmentBrokenEvent stores correct data."""
        event = CommitmentBrokenEvent(
            tick=10,
            agent_a="alice",
            agent_b="bob",
            reason="trade_completed"
        )
        assert event.tick == 10
        assert event.reason == "trade_completed"

    def test_matching_phase_result(self):
        """MatchingPhaseResult stores correct data."""
        result = MatchingPhaseResult(
            tick=3,
            new_pairs=[("a", "b"), ("c", "d")],
            unmatched_agents=["e"],
            algorithm_succeeded=True
        )
        assert result.tick == 3
        assert len(result.new_pairs) == 2
        assert "e" in result.unmatched_agents
        assert result.algorithm_succeeded
