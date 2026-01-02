"""
Visualization module for microecon simulation.

Provides a DearPyGui-based visualization of the search-and-exchange simulation.

Supports three modes:
- Live mode: Run a new simulation with real-time updates
- Replay mode: Play back a logged simulation run with timeline scrubbing
- Comparison mode: Side-by-side synchronized replay of two runs
"""

from microecon.visualization.app import (
    run_visualization,
    run_replay,
    run_replay_from_path,
    run_comparison,
    run_comparison_from_paths,
    run_protocol_comparison,
    VisualizationApp,
    DualVisualizationApp,
)
from microecon.visualization.replay import (
    ReplayController,
    DualReplayController,
)

__all__ = [
    # Live mode
    "run_visualization",
    # Replay mode
    "run_replay",
    "run_replay_from_path",
    # Comparison mode
    "run_comparison",
    "run_comparison_from_paths",
    "run_protocol_comparison",
    # App classes
    "VisualizationApp",
    "DualVisualizationApp",
    # Replay controllers
    "ReplayController",
    "DualReplayController",
]
