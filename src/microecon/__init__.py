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
from microecon.information import InformationEnvironment, FullInformation, NoisyAlphaInformation
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
from microecon.beliefs import (
    # Memory structures
    TradeMemory,
    PriceObservation,
    InteractionRecord,
    AgentMemory,
    # Belief representations
    PriceBelief,
    TypeBelief,
    # Update rules
    BeliefUpdateRule,
    BayesianUpdateRule,
    HeuristicUpdateRule,
    # Integration functions
    record_trade_observation,
    record_encounter,
    record_observed_trade,
)

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
    "NoisyAlphaInformation",
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
    # Beliefs - Memory structures
    "TradeMemory",
    "PriceObservation",
    "InteractionRecord",
    "AgentMemory",
    # Beliefs - Belief representations
    "PriceBelief",
    "TypeBelief",
    # Beliefs - Update rules
    "BeliefUpdateRule",
    "BayesianUpdateRule",
    "HeuristicUpdateRule",
    # Beliefs - Integration functions
    "record_trade_observation",
    "record_encounter",
    "record_observed_trade",
]
