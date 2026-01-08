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
import random

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


class NoisyAlphaInformation(InformationEnvironment):
    """
    Noisy alpha information environment: agents observe noisy estimates of
    counterparty preference parameters.

    In this environment:
    - Endowments are observable (agents can see what others hold)
    - Preference parameter (alpha) is observed with Gaussian noise
    - Each observation is a fresh noisy draw (no memory)

    The noise model: observed_alpha = true_alpha + N(0, noise_std)
    The observed alpha is clipped to (0.01, 0.99) to remain valid.

    This models situations where agents can observe holdings directly but must
    infer preferences from behavior, leading to estimation error.

    Attributes:
        noise_std: Standard deviation of the Gaussian noise added to alpha
        seed: Random seed for reproducibility (optional)

    Reference: Kreps II Ch 20 (adverse selection), O&R-G Ch 11
    """

    def __init__(self, noise_std: float, seed: int | None = None):
        if noise_std < 0:
            raise ValueError(f"noise_std must be non-negative, got {noise_std}")
        self.noise_std = noise_std
        self.seed = seed
        self._rng = random.Random(seed)

    def get_observable_type(self, agent: Agent) -> AgentType:
        """
        Return type with noisy alpha but true endowment.

        The alpha parameter is perturbed by Gaussian noise and clipped
        to remain in the valid range (0, 1).
        """
        from microecon.agent import AgentType
        from microecon.preferences import CobbDouglas

        true_alpha = agent.private_state.preferences.alpha

        # Add Gaussian noise
        noise = self._rng.gauss(0, self.noise_std)
        noisy_alpha = true_alpha + noise

        # Clip to valid range (epsilon away from boundaries)
        noisy_alpha = max(0.01, min(0.99, noisy_alpha))

        return AgentType(
            preferences=CobbDouglas(noisy_alpha),
            endowment=agent.private_state.endowment,
        )

    def can_observe(self, observer: Agent, target: Agent, distance: float) -> bool:
        """Check if target is within observer's perception radius."""
        return distance <= observer.perception_radius

    def get_true_type(self, agent: Agent) -> AgentType:
        """
        Return the true type (for visualization/analysis purposes).

        This should NOT be used for agent decision-making, only for
        comparing perceived vs actual types in analysis.
        """
        from microecon.agent import AgentType
        return AgentType.from_private_state(agent.private_state)
