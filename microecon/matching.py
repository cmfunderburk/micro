"""
Matching protocols for bilateral exchange.

NOTE: The previous MatchingProtocol abstraction (OpportunisticMatchingProtocol,
StableRoommatesMatchingProtocol) has been removed. Matching is now handled
through the action-based propose/accept/reject system:

- Agents choose ProposeAction to initiate trades with adjacent partners
- Targets evaluate proposals against their opportunity cost (value of chosen action)
- AcceptAction/RejectAction resolve during the Execute phase
- Cooldowns prevent re-proposing to agents who rejected

This decentralized, agent-autonomous approach replaces the centralized
compute_matches() pattern. The current implementation is ad-hoc and not
grounded in matching theory (stable matching, deferred acceptance, etc.).

FUTURE WORK: Design theory-based matching protocols compatible with the
action-budget tick model. This is non-trivial because classic matching
algorithms assume centralized coordination, while the current architecture
emphasizes agent autonomy.

Reference: ADR-001-TICK-MODEL.md, ADR-003-EXCHANGE-SEQUENCE.md
"""

# No exports - matching is handled through actions.py and decisions.py
