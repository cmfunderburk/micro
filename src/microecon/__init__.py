"""
Microecon Platform: Agent-based microeconomics simulation.

A research-first platform that gives canonical theoretical microeconomics
computational form through simulated agents interacting under configurable
institutional rules.
"""

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.agent import Agent, AgentPrivateState, AgentType
from microecon.grid import Grid, Position
from microecon.information import InformationEnvironment, FullInformation
from microecon.bargaining import (
    nash_bargaining_solution,
    compute_nash_surplus,
    rubinstein_share,
    rubinstein_bargaining_solution,
    compute_rubinstein_surplus,
    BargainingProtocol,
    NashBargainingProtocol,
    RubinsteinBargainingProtocol,
)
from microecon.matching import (
    MatchingProtocol,
    OpportunisticMatchingProtocol,
    StableRoommatesMatchingProtocol,
    CommitmentState,
)
from microecon.simulation import Simulation, create_simple_economy

__all__ = [
    # Core types
    "Bundle",
    "CobbDouglas",
    "Agent",
    "AgentPrivateState",
    "AgentType",
    "Grid",
    "Position",
    # Information environments
    "InformationEnvironment",
    "FullInformation",
    # Bargaining - Nash (axiomatic)
    "nash_bargaining_solution",
    "compute_nash_surplus",
    # Bargaining - Rubinstein (strategic)
    "rubinstein_share",
    "rubinstein_bargaining_solution",
    "compute_rubinstein_surplus",
    # Bargaining protocols (institutional abstraction)
    "BargainingProtocol",
    "NashBargainingProtocol",
    "RubinsteinBargainingProtocol",
    # Matching protocols (institutional abstraction)
    "MatchingProtocol",
    "OpportunisticMatchingProtocol",
    "StableRoommatesMatchingProtocol",
    "CommitmentState",
    # Simulation
    "Simulation",
    "create_simple_economy",
]
