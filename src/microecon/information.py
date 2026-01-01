"""
Information environment configuration.

This module defines how agents observe each other. The information environment
determines what aspects of an agent's private state are revealed as their
observable type.

Reference: CLAUDE.md, O&R-G Ch 11 (games with imperfect information)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from microecon.agent import Agent, AgentType


class InformationEnvironment(ABC):
    """
    Abstract base class for information environments.

    An information environment maps agents' private states to observable types.
    Different environments model different information structures:
    - Full information: type = private state
    - Private information: type reveals nothing or partial information
    - Signaling: type depends on costly actions taken by the agent
    """

    @abstractmethod
    def get_observable_type(self, agent: Agent) -> AgentType:
        """
        Generate the observable type for an agent.

        Args:
            agent: The agent whose type to generate

        Returns:
            AgentType representing what other agents can observe
        """
        pass

    @abstractmethod
    def can_observe(self, observer: Agent, target: Agent, distance: float) -> bool:
        """
        Check if observer can see target at given distance.

        This combines the observer's perception radius with any
        environment-specific visibility rules.

        Args:
            observer: The agent trying to observe
            target: The agent being observed
            distance: Distance between them on the grid

        Returns:
            True if observer can see target
        """
        pass


class FullInformation(InformationEnvironment):
    """
    Full information environment: type = private state.

    In this environment, all agents can observe each other's true
    preferences and endowments within their perception radius.
    This is the MVP default.

    Game-theoretically, this corresponds to complete information games
    where the structure of the game (including player types) is common knowledge.
    """

    def get_observable_type(self, agent: Agent) -> AgentType:
        """Return full private state as observable type."""
        from microecon.agent import AgentType
        return AgentType.from_private_state(agent.private_state)

    def can_observe(self, observer: Agent, target: Agent, distance: float) -> bool:
        """
        Check if target is within observer's perception radius.

        In full information, the only constraint is distance.
        """
        return distance <= observer.perception_radius


class PrivateInformation(InformationEnvironment):
    """
    Private information environment: agents cannot observe each other's types.

    This is a placeholder for future implementation. In private information
    settings, agents must form beliefs about other agents' types based on
    observable behavior or signaling.

    Reference: Kreps II Ch 20 (adverse selection), O&R-G Ch 11
    """

    def get_observable_type(self, agent: Agent) -> AgentType:
        """
        Return a type that reveals no information.

        For now, raise NotImplementedError as this is future work.
        """
        raise NotImplementedError("PrivateInformation environment not yet implemented")

    def can_observe(self, observer: Agent, target: Agent, distance: float) -> bool:
        """Observation is still distance-based, but type content differs."""
        return distance <= observer.perception_radius
