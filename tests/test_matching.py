"""
Tests for matching mechanism documentation.

NOTE: The MatchingProtocol abstraction has been removed. Matching is now
handled through the action-based propose/accept/reject system:

- Agents choose ProposeAction to initiate trades with adjacent partners
- Targets evaluate proposals against their opportunity cost
- AcceptAction/RejectAction resolve during the Execute phase
- Cooldowns prevent re-proposing to agents who rejected

See microecon/matching.py for full documentation.

Tests for the propose/accept/reject mechanism are in:
- tests/theory/test_action_budget_*.py (theory verification)
- tests/test_simulation.py (integration)
"""

import pytest

pytestmark = pytest.mark.matching


class TestMatchingMechanismDocumentation:
    """Document that matching is now via propose/accept/reject actions."""

    def test_matching_module_exists_with_documentation(self):
        """The matching module exists with documentation about the new approach."""
        import microecon.matching as matching
        assert "propose/accept/reject" in matching.__doc__

    def test_matching_protocol_not_exported(self):
        """MatchingProtocol is no longer exported from microecon."""
        import microecon
        assert not hasattr(microecon, 'MatchingProtocol')
        assert not hasattr(microecon, 'OpportunisticMatchingProtocol')

    def test_propose_action_exists(self):
        """ProposeAction is the new way to initiate trades."""
        from microecon import ProposeAction
        assert ProposeAction is not None

    def test_accept_reject_actions_exist(self):
        """AcceptAction and RejectAction handle proposal responses."""
        from microecon import AcceptAction, RejectAction
        assert AcceptAction is not None
        assert RejectAction is not None
