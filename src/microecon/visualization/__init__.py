"""
Visualization module for microecon simulation.

Provides a DearPyGui-based visualization of the search-and-exchange simulation.

Supports three modes:
- Live mode: Run a new simulation with real-time updates
- Replay mode: Play back a logged simulation run with timeline scrubbing
- Comparison mode: Side-by-side synchronized replay of two runs
- Scenario mode: Browse and run pre-defined scenarios
"""

from microecon.visualization.app import (
    run_visualization,
    run_replay,
    run_replay_from_path,
    run_comparison,
    run_comparison_from_paths,
    run_protocol_comparison,
    run_matching_protocol_comparison,
    VisualizationApp,
    DualVisualizationApp,
)
from microecon.visualization.replay import (
    ReplayController,
    DualReplayController,
)
from microecon.visualization.browser import (
    run_with_startup_selector,
    run_scenario_comparison,
    StartupSelector,
    ScenarioBrowser,
)

__all__ = [
    # Main entry point (startup selector)
    "run_with_startup_selector",
    # Live mode
    "run_visualization",
    # Replay mode
    "run_replay",
    "run_replay_from_path",
    # Comparison mode
    "run_comparison",
    "run_comparison_from_paths",
    "run_protocol_comparison",
    "run_matching_protocol_comparison",
    # Scenario mode
    "run_scenario_comparison",
    # App classes
    "VisualizationApp",
    "DualVisualizationApp",
    "StartupSelector",
    "ScenarioBrowser",
    # Replay controllers
    "ReplayController",
    "DualReplayController",
]
