"""
Matching protocols for bilateral exchange.

This module implements matching protocols that determine how agents form
trading pairs. The current implementation uses opportunistic matching,
where any adjacent agents can trade without explicit commitment.

The matching protocol abstraction exists to enable future comparison of
outcomes under different institutional rules - a core value proposition
per VISION.md.

Reference: VISION.md (institutional visibility)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Set, Tuple

from microecon.agent import Agent


class MatchingProtocol(ABC):
    """
    Abstract base class for matching protocols.

    Matching protocols determine how agents form trading pairs:
    - Opportunistic: Any adjacent pair can trade (no explicit matching)

    This abstraction enables comparing outcomes under different institutional
    matching rules, parallel to how BargainingProtocol enables comparing
    different bargaining rules.

    Usage:
        protocol = OpportunisticMatchingProtocol()

        # Compute matches among agents (currently a no-op for opportunistic)
        new_pairs = protocol.compute_matches(agents, visibility, surplus_fn)
    """

    @property
    @abstractmethod
    def requires_commitment(self) -> bool:
        """
        Whether trade requires explicit mutual commitment.

        If True: Only committed + adjacent pairs can trade
        If False: Any adjacent pair can trade (opportunistic)
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
            agents: Agents to consider for matching
            visibility: Map of agent_id -> set of visible agent_ids
            surplus_fn: Function computing bilateral surplus between agents

        Returns:
            List of (agent_id, agent_id) pairs that form commitments
        """
        pass


class OpportunisticMatchingProtocol(MatchingProtocol):
    """
    Opportunistic matching - no explicit commitment required.

    Any adjacent agents can trade without prior coordination:
    - No matching phase needed
    - Trade partner selected via proposal/acceptance during Execute phase
    - Agents autonomously decide whether to propose and accept

    This is the default (and currently only) matching protocol.
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
