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
from microecon.bargaining import nash_bargaining_solution, compute_nash_surplus
from microecon.simulation import Simulation

__all__ = [
    "Bundle",
    "CobbDouglas",
    "Agent",
    "AgentPrivateState",
    "AgentType",
    "Grid",
    "Position",
    "InformationEnvironment",
    "FullInformation",
    "nash_bargaining_solution",
    "compute_nash_surplus",
    "Simulation",
]
