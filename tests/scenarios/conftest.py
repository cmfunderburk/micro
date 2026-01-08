"""
Shared fixtures and imports for theoretical scenario tests.

These tests verify that simulation outcomes match analytically-derived
theoretical predictions. Each scenario is simple enough to compute by hand,
providing rigorous validation of the simulation's economic correctness.
"""

import pytest
import math

from microecon.bundle import Bundle
from microecon.preferences import CobbDouglas
from microecon.grid import Grid, Position
from microecon.agent import create_agent, AgentType
from microecon.information import FullInformation
from microecon.simulation import Simulation
from microecon.bargaining import (
    nash_bargaining_solution,
    compute_nash_surplus,
    NashBargainingProtocol,
    RubinsteinBargainingProtocol,
)
from microecon.search import evaluate_targets, SearchResult
