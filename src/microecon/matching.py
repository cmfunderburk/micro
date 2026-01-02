"""
Matching protocols for bilateral exchange.

This module implements matching protocols that determine how agents form
trading pairs. Different protocols create different emergent dynamics:

1. Opportunistic Matching (default)
   - No explicit matching phase
   - Any co-located agents can trade
   - Current behavior preserved

2. Stable Roommates Matching (Irving's algorithm)
   - Agents form committed pairs before trading
   - Only mutually committed + co-located pairs can trade
   - Produces stable matching (no blocking pairs) when solution exists

The matching protocol abstraction enables comparing outcomes under different
institutional rules - a core value proposition per VISION.md.

Reference: DESIGN_matching_protocol.md, Irving (1985)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from microecon.agent import Agent


@dataclass
class CommitmentState:
    """
    Tracks mutual commitments between agents.

    Commitments persist until:
    1. Successful trade between committed partners
    2. Partner exits perception radius

    Attributes:
        _commitments: Set of frozensets, each containing two agent IDs
    """
    _commitments: Set[frozenset] = field(default_factory=set)

    def is_committed(self, agent_id: str) -> bool:
        """Check if an agent has an active commitment."""
        return any(agent_id in pair for pair in self._commitments)

    def get_partner(self, agent_id: str) -> Optional[str]:
        """Get the committed partner for an agent, if any."""
        for pair in self._commitments:
            if agent_id in pair:
                other = pair - {agent_id}
                if other:
                    return next(iter(other))
        return None

    def form_commitment(self, agent_a: str, agent_b: str) -> None:
        """Form a mutual commitment between two agents."""
        self._commitments.add(frozenset({agent_a, agent_b}))

    def break_commitment(self, agent_a: str, agent_b: str) -> bool:
        """
        Break a commitment between two agents.

        Returns:
            True if a commitment was broken, False if none existed
        """
        pair = frozenset({agent_a, agent_b})
        if pair in self._commitments:
            self._commitments.discard(pair)
            return True
        return False

    def break_all_for_agent(self, agent_id: str) -> List[str]:
        """
        Break all commitments involving an agent.

        Returns:
            List of partner IDs whose commitments were broken
        """
        broken = []
        to_remove = set()
        for pair in self._commitments:
            if agent_id in pair:
                to_remove.add(pair)
                other = pair - {agent_id}
                if other:
                    broken.append(next(iter(other)))
        self._commitments -= to_remove
        return broken

    def get_all_committed_pairs(self) -> List[Tuple[str, str]]:
        """Get all committed pairs as a list of tuples."""
        return [tuple(sorted(pair)) for pair in self._commitments]

    def get_uncommitted_agents(self, all_agent_ids: Set[str]) -> Set[str]:
        """Get the set of agents without commitments."""
        committed = set()
        for pair in self._commitments:
            committed.update(pair)
        return all_agent_ids - committed

    def clear(self) -> None:
        """Clear all commitments."""
        self._commitments.clear()


class MatchingProtocol(ABC):
    """
    Abstract base class for matching protocols.

    Matching protocols determine how agents form trading pairs:
    - Opportunistic: Any co-located pair can trade (no explicit matching)
    - Committed: Agents must form mutual commitments before trading

    This abstraction enables comparing outcomes under different institutional
    matching rules, parallel to how BargainingProtocol enables comparing
    different bargaining rules.

    Usage:
        protocol = OpportunisticMatchingProtocol()
        # or
        protocol = StableRoommatesMatchingProtocol()

        # Compute matches among uncommitted agents
        new_pairs = protocol.compute_matches(uncommitted, visibility, surplus_fn)
    """

    @property
    @abstractmethod
    def requires_commitment(self) -> bool:
        """
        Whether trade requires explicit mutual commitment.

        If True: Only committed + co-located pairs can trade
        If False: Any co-located pair can trade (opportunistic)
        """
        pass

    @abstractmethod
    def compute_matches(
        self,
        agents: List[Agent],
        visibility: Dict[str, Set[str]],
        surplus_fn: Callable[[Agent, Agent], float],
    ) -> List[Tuple[str, str]]:
        """
        Compute committed pairs for this tick.

        Args:
            agents: Uncommitted agents to consider for matching
            visibility: Map of agent_id -> set of visible agent_ids
            surplus_fn: Function computing bilateral surplus between agents

        Returns:
            List of (agent_id, agent_id) pairs that form commitments
        """
        pass


class OpportunisticMatchingProtocol(MatchingProtocol):
    """
    Opportunistic matching - no explicit commitment required.

    This preserves the current behavior:
    - Any co-located agents can trade
    - No matching phase needed
    - Trade partner selected from co-located set (lexicographic tie-breaking)

    This is the default matching protocol.
    """

    @property
    def requires_commitment(self) -> bool:
        return False

    def compute_matches(
        self,
        agents: List[Agent],
        visibility: Dict[str, Set[str]],
        surplus_fn: Callable[[Agent, Agent], float],
    ) -> List[Tuple[str, str]]:
        """No explicit matching in opportunistic mode."""
        return []


class StableRoommatesMatchingProtocol(MatchingProtocol):
    """
    Stable Roommates matching using Irving's algorithm.

    Forms committed pairs with the stability property: no two agents
    would both prefer to be matched with each other over their current
    partners (when a stable matching exists).

    Properties:
    - One-sided matching (any agent can match with any other)
    - Stable when solution exists (no blocking pairs)
    - May fail to find stable matching in some configurations
    - Perception-constrained: only match with visible agents
    - Surplus-discounted preferences: rankings based on bilateral surplus

    When no stable matching exists or agents are unmatched, they use
    fallback behavior (approach best visible target).

    Reference: Irving, R.W. (1985). "An efficient algorithm for the
    stable roommates problem." Journal of Algorithms 6(4): 577-595.
    """

    @property
    def requires_commitment(self) -> bool:
        return True

    def compute_matches(
        self,
        agents: List[Agent],
        visibility: Dict[str, Set[str]],
        surplus_fn: Callable[[Agent, Agent], float],
    ) -> List[Tuple[str, str]]:
        """
        Compute stable matching among agents using Irving's algorithm.

        Args:
            agents: Uncommitted agents to consider for matching
            visibility: Map of agent_id -> set of visible agent_ids
            surplus_fn: Function computing bilateral surplus (distance-discounted)

        Returns:
            List of (agent_id, agent_id) pairs forming stable matches
        """
        if len(agents) < 2:
            return []

        # Build agent lookup
        agent_map = {a.id: a for a in agents}
        agent_ids = list(agent_map.keys())

        # Build preference lists based on surplus (higher = more preferred)
        # Only include visible agents with positive surplus
        preferences: Dict[str, List[str]] = {}

        for agent in agents:
            visible = visibility.get(agent.id, set())
            candidates = []

            for other_id in visible:
                if other_id == agent.id:
                    continue
                other = agent_map.get(other_id)
                if other is None:
                    continue

                surplus = surplus_fn(agent, other)
                if surplus > 0:
                    candidates.append((surplus, other_id))

            # Sort by surplus (descending), then by ID (for determinism)
            candidates.sort(key=lambda x: (-x[0], x[1]))
            preferences[agent.id] = [c[1] for c in candidates]

        # Run Irving's algorithm
        return self._irving_algorithm(agent_ids, preferences)

    def _irving_algorithm(
        self,
        agents: List[str],
        preferences: Dict[str, List[str]],
    ) -> List[Tuple[str, str]]:
        """
        Irving's Stable Roommates algorithm.

        Phase 1: Proposal phase (like Gale-Shapley)
        - Each agent proposes to their most preferred
        - Each agent holds at most one proposal, rejecting worse ones
        - Rejected agents propose to next choice

        Phase 2: Rotation elimination (unique to stable roommates)
        - Find and eliminate "rotations" that must be removed
        - Continue until matching found or proven impossible

        Returns:
            List of matched pairs, or partial matching if no stable solution
        """
        n = len(agents)
        if n < 2:
            return []

        # Deep copy preference lists (we'll modify them)
        prefs = {a: list(preferences.get(a, [])) for a in agents}

        # Track who each agent is currently holding (proposal from)
        holding: Dict[str, Optional[str]] = {a: None for a in agents}

        # Phase 1: Proposal phase
        # Each agent proposes to their first choice
        proposers = list(agents)

        while proposers:
            proposer = proposers.pop(0)

            if not prefs[proposer]:
                # No one left to propose to
                continue

            # Propose to first choice
            target = prefs[proposer][0]

            if target not in prefs:
                # Target not in our agent set, skip
                prefs[proposer].pop(0)
                if prefs[proposer]:
                    proposers.append(proposer)
                continue

            current_holder = holding[target]

            if current_holder is None:
                # Target is free, accept proposal
                holding[target] = proposer
            else:
                # Target compares current holder vs new proposer
                target_prefs = prefs[target]

                # Find positions in preference list
                proposer_rank = target_prefs.index(proposer) if proposer in target_prefs else float('inf')
                holder_rank = target_prefs.index(current_holder) if current_holder in target_prefs else float('inf')

                if proposer_rank < holder_rank:
                    # New proposer is better, reject current holder
                    holding[target] = proposer
                    # Current holder must propose again
                    prefs[current_holder].remove(target)
                    if prefs[current_holder]:
                        proposers.append(current_holder)
                else:
                    # Keep current holder, reject new proposer
                    prefs[proposer].remove(target)
                    if prefs[proposer]:
                        proposers.append(proposer)

        # After phase 1, reduce preference lists
        # Remove anyone worse than current holder from each preference list
        for agent in agents:
            holder = holding[agent]
            if holder is not None and holder in prefs[agent]:
                holder_idx = prefs[agent].index(holder)
                # Remove everyone after holder
                worse = prefs[agent][holder_idx + 1:]
                prefs[agent] = prefs[agent][:holder_idx + 1]
                # Also remove agent from those worse agents' lists
                for w in worse:
                    if agent in prefs.get(w, []):
                        prefs[w].remove(agent)

        # Phase 2: Rotation elimination
        # Find rotations and eliminate them until lists have length 1 or failure
        max_iterations = n * n  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Check for completion or failure
            all_single = True
            any_empty = False

            for agent in agents:
                if len(prefs[agent]) == 0:
                    any_empty = True
                elif len(prefs[agent]) > 1:
                    all_single = False

            if all_single:
                break  # Found stable matching

            if any_empty:
                break  # No stable matching exists

            # Find a rotation
            rotation = self._find_rotation(agents, prefs)

            if rotation is None:
                break  # No rotation found, done

            # Eliminate the rotation
            self._eliminate_rotation(rotation, prefs)

        # Build matching from reduced preference lists
        matches = []
        matched = set()

        for agent in sorted(agents):  # Sorted for determinism
            if agent in matched:
                continue

            if prefs[agent]:
                partner = prefs[agent][0]
                if partner not in matched and agent in prefs.get(partner, []):
                    matches.append((agent, partner) if agent < partner else (partner, agent))
                    matched.add(agent)
                    matched.add(partner)

        return matches

    def _find_rotation(
        self,
        agents: List[str],
        prefs: Dict[str, List[str]],
    ) -> Optional[List[Tuple[str, str]]]:
        """
        Find a rotation in the reduced preference lists.

        A rotation is a sequence [(p0, q0), (p1, q1), ..., (pr, qr)] where:
        - qi is second on pi's list
        - p(i+1 mod r+1) is last on qi's list

        Returns:
            Rotation as list of (p, q) pairs, or None if not found
        """
        # Find an agent with list length > 1
        start = None
        for agent in agents:
            if len(prefs[agent]) > 1:
                start = agent
                break

        if start is None:
            return None

        rotation = []
        p = start
        visited = set()

        while p not in visited:
            visited.add(p)

            if len(prefs[p]) < 2:
                return None  # Can't form rotation

            q = prefs[p][1]  # Second on p's list

            if not prefs.get(q):
                return None

            # Find last person on q's list
            next_p = prefs[q][-1]

            rotation.append((p, q))
            p = next_p

        # Find where the cycle starts
        cycle_start_idx = None
        for i, (pi, _) in enumerate(rotation):
            if pi == p:
                cycle_start_idx = i
                break

        if cycle_start_idx is None:
            return None

        return rotation[cycle_start_idx:]

    def _eliminate_rotation(
        self,
        rotation: List[Tuple[str, str]],
        prefs: Dict[str, List[str]],
    ) -> None:
        """
        Eliminate a rotation from the preference lists.

        For rotation [(p0, q0), (p1, q1), ..., (pr, qr)]:
        - For each (pi, qi): remove qi from pi's list and pi from qi's list
        """
        for p, q in rotation:
            if q in prefs.get(p, []):
                prefs[p].remove(q)
            if p in prefs.get(q, []):
                prefs[q].remove(p)


# =============================================================================
# Matching Event Types (for logging)
# =============================================================================


@dataclass
class CommitmentFormedEvent:
    """Record of a commitment forming between two agents."""
    tick: int
    agent_a: str
    agent_b: str


@dataclass
class CommitmentBrokenEvent:
    """Record of a commitment breaking."""
    tick: int
    agent_a: str
    agent_b: str
    reason: str  # "trade_completed" or "left_perception"


@dataclass
class MatchingPhaseResult:
    """Summary of a matching phase."""
    tick: int
    new_pairs: List[Tuple[str, str]]
    unmatched_agents: List[str]
    algorithm_succeeded: bool
