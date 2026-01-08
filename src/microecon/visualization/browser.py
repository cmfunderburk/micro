"""
Scenario browser and startup mode selector.

Provides a launcher UI that allows users to:
- Start a new live simulation
- Browse and run pre-defined scenarios
- Load a previously-saved run for replay
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, Literal

import dearpygui.dearpygui as dpg

from microecon.scenarios import Scenario, load_all_scenarios


@dataclass
class LaunchConfig:
    """Configuration for launching a visualization mode."""

    mode: Literal["live", "scenario", "browse", "cancel"]
    # Live mode params
    n_agents: int = 10
    grid_size: int = 15
    seed: Optional[int] = None
    # Institutional params
    bargaining_protocol: Literal["nash", "rubinstein"] = "nash"
    matching_protocol: Literal["opportunistic", "stable_roommates"] = "opportunistic"
    # Search params
    perception_radius: float = 7.0
    discount_factor: float = 0.95
    # Scenario mode params
    scenario: Optional[Scenario] = None


class LiveConfigModal:
    """
    Configuration modal for live simulation parameters.

    Presents three collapsible sections:
    - Basic Parameters: agents, grid size, seed
    - Institutions: bargaining protocol, matching protocol
    - Search Parameters: perception radius, discount factor
    """

    WINDOW_WIDTH = 450
    WINDOW_HEIGHT = 480

    # Friendly display names for protocols
    BARGAINING_PROTOCOLS = {
        "nash": "Nash Bargaining",
        "rubinstein": "Rubinstein (Alternating Offers)",
    }
    MATCHING_PROTOCOLS = {
        "opportunistic": "Opportunistic",
        "stable_roommates": "Stable Roommates",
    }

    def __init__(
        self,
        n_agents: int = 10,
        grid_size: int = 15,
        seed: Optional[int] = None,
    ):
        # Basic params (pre-filled from StartupSelector)
        self.n_agents = n_agents
        self.grid_size = grid_size
        self.seed = seed

        # Institutional params (defaults)
        self.bargaining_protocol: Literal["nash", "rubinstein"] = "nash"
        self.matching_protocol: Literal["opportunistic", "stable_roommates"] = "opportunistic"

        # Search params (defaults)
        self.perception_radius = 7.0
        self.discount_factor = 0.95

        self.result: Optional[LaunchConfig] = None
        self._closed = False

    def setup(self) -> None:
        """Set up the DearPyGui context and window."""
        dpg.create_context()
        dpg.create_viewport(
            title="Configure Simulation",
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
            resizable=False,
        )

        with dpg.window(label="Configure Simulation", tag="main_window", no_title_bar=True):
            dpg.add_text("Configure Simulation", color=(200, 200, 200))
            dpg.add_separator()
            dpg.add_spacer(height=10)

            # Basic Parameters section
            with dpg.collapsing_header(label="Basic Parameters", default_open=True):
                dpg.add_spacer(height=5)

                with dpg.group(horizontal=True):
                    dpg.add_text("Agents:", indent=10)
                    dpg.add_spacer(width=45)
                    dpg.add_input_int(
                        tag="input_agents",
                        default_value=self.n_agents,
                        min_value=2,
                        max_value=50,
                        width=120,
                        callback=lambda s, a: setattr(self, 'n_agents', a),
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Grid size:", indent=10)
                    dpg.add_spacer(width=30)
                    dpg.add_input_int(
                        tag="input_grid_size",
                        default_value=self.grid_size,
                        min_value=5,
                        max_value=50,
                        width=120,
                        callback=lambda s, a: setattr(self, 'grid_size', a),
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Seed:", indent=10)
                    dpg.add_spacer(width=53)
                    dpg.add_input_int(
                        tag="input_seed",
                        default_value=self.seed if self.seed is not None else 0,
                        width=120,
                        callback=self._on_seed_change,
                    )
                    dpg.add_text("(0 = random)", color=(100, 100, 100))

                dpg.add_spacer(height=5)

            dpg.add_spacer(height=5)

            # Institutions section
            with dpg.collapsing_header(label="Institutions", default_open=True):
                dpg.add_spacer(height=5)

                dpg.add_text("Bargaining Protocol:", indent=10, color=(150, 150, 150))
                with dpg.group(indent=20):
                    dpg.add_radio_button(
                        tag="radio_bargaining",
                        items=list(self.BARGAINING_PROTOCOLS.values()),
                        default_value=self.BARGAINING_PROTOCOLS[self.bargaining_protocol],
                        callback=self._on_bargaining_change,
                    )

                dpg.add_spacer(height=10)

                dpg.add_text("Matching Protocol:", indent=10, color=(150, 150, 150))
                with dpg.group(indent=20):
                    dpg.add_radio_button(
                        tag="radio_matching",
                        items=list(self.MATCHING_PROTOCOLS.values()),
                        default_value=self.MATCHING_PROTOCOLS[self.matching_protocol],
                        callback=self._on_matching_change,
                    )

                dpg.add_spacer(height=5)

            dpg.add_spacer(height=5)

            # Search Parameters section
            with dpg.collapsing_header(label="Search Parameters", default_open=True):
                dpg.add_spacer(height=5)

                with dpg.group(horizontal=True):
                    dpg.add_text("Perception radius:", indent=10)
                    dpg.add_input_float(
                        tag="input_perception",
                        default_value=self.perception_radius,
                        min_value=1.0,
                        max_value=20.0,
                        width=80,
                        format="%.1f",
                        callback=lambda s, a: setattr(self, 'perception_radius', a),
                    )
                dpg.add_text("(how far agents can see)", indent=10, color=(100, 100, 100))

                dpg.add_spacer(height=5)

                with dpg.group(horizontal=True):
                    dpg.add_text("Discount factor:", indent=10)
                    dpg.add_spacer(width=10)
                    dpg.add_input_float(
                        tag="input_discount",
                        default_value=self.discount_factor,
                        min_value=0.5,
                        max_value=0.99,
                        width=80,
                        format="%.2f",
                        step=0.01,
                        callback=lambda s, a: setattr(self, 'discount_factor', a),
                    )
                dpg.add_text("(agent patience)", indent=10, color=(100, 100, 100))

                dpg.add_spacer(height=5)

            # Buttons at bottom
            dpg.add_spacer(height=20)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=100)
                dpg.add_button(
                    label="Cancel",
                    callback=self._on_cancel,
                    width=120,
                )
                dpg.add_spacer(width=20)
                dpg.add_button(
                    label="Start Simulation",
                    callback=self._on_start,
                    width=140,
                )

        dpg.set_primary_window("main_window", True)
        dpg.setup_dearpygui()
        dpg.show_viewport()

    def _on_seed_change(self, sender: int, app_data: int) -> None:
        """Handle seed input change."""
        self.seed = app_data if app_data != 0 else None

    def _on_bargaining_change(self, sender: int, app_data: str) -> None:
        """Handle bargaining protocol selection."""
        # Reverse lookup from display name to key
        for key, name in self.BARGAINING_PROTOCOLS.items():
            if name == app_data:
                self.bargaining_protocol = key
                break

    def _on_matching_change(self, sender: int, app_data: str) -> None:
        """Handle matching protocol selection."""
        # Reverse lookup from display name to key
        for key, name in self.MATCHING_PROTOCOLS.items():
            if name == app_data:
                self.matching_protocol = key
                break

    def _on_cancel(self) -> None:
        """Handle cancel button - return without starting."""
        self.result = None
        self._closed = True

    def _on_start(self) -> None:
        """Handle start button - create config and close."""
        self.result = LaunchConfig(
            mode="live",
            n_agents=self.n_agents,
            grid_size=self.grid_size,
            seed=self.seed,
            bargaining_protocol=self.bargaining_protocol,
            matching_protocol=self.matching_protocol,
            perception_radius=self.perception_radius,
            discount_factor=self.discount_factor,
        )
        self._closed = True

    def run(self) -> Optional[LaunchConfig]:
        """Run the modal and return the config (or None if cancelled)."""
        self.setup()

        while dpg.is_dearpygui_running() and not self._closed:
            dpg.render_dearpygui_frame()

        dpg.destroy_context()
        return self.result


class StartupSelector:
    """
    Startup mode selector window.

    Presents three options:
    - Live Mode: Run a new random simulation
    - Browse Scenarios: Open the scenario browser
    - (Future: Load Run - open a saved run for replay)
    """

    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 400

    def __init__(self):
        self.result: Optional[LaunchConfig] = None
        self._closed = False
        self._pending_action: Optional[str] = None  # "browse" or None

        # Live mode params
        self.n_agents = 10
        self.grid_size = 15
        self.seed: Optional[int] = None

    def setup(self) -> None:
        """Set up the DearPyGui context and window."""
        dpg.create_context()
        dpg.create_viewport(
            title="Microecon - Launch",
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
            resizable=False,
        )

        with dpg.window(label="Select Mode", tag="main_window", no_title_bar=True):
            dpg.add_text("Microecon Simulation", color=(200, 200, 200))
            dpg.add_text("Select a mode to begin:", color=(150, 150, 150))
            dpg.add_separator()
            dpg.add_spacer(height=20)

            # Live Mode section
            with dpg.collapsing_header(label="Live Mode", default_open=True):
                dpg.add_text("Run a new simulation with random agents", color=(150, 150, 150))
                dpg.add_spacer(height=10)

                with dpg.group(horizontal=True):
                    dpg.add_text("Agents:")
                    dpg.add_input_int(
                        default_value=10,
                        min_value=2,
                        max_value=50,
                        width=100,
                        callback=lambda s, a: setattr(self, 'n_agents', a),
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Grid size:")
                    dpg.add_input_int(
                        default_value=15,
                        min_value=5,
                        max_value=50,
                        width=100,
                        callback=lambda s, a: setattr(self, 'grid_size', a),
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Seed:")
                    dpg.add_input_int(
                        default_value=0,
                        width=100,
                        callback=self._on_seed_change,
                    )
                    dpg.add_text("(0 = random)", color=(100, 100, 100))

                dpg.add_spacer(height=10)
                dpg.add_button(
                    label="Configure Simulation...",
                    callback=self._on_configure_live,
                    width=-1,
                )

            dpg.add_spacer(height=10)

            # Browse Scenarios section
            with dpg.collapsing_header(label="Browse Scenarios", default_open=True):
                dpg.add_text("Run pre-defined scenarios for comparison", color=(150, 150, 150))
                dpg.add_spacer(height=10)
                dpg.add_button(
                    label="Open Scenario Browser",
                    callback=self._on_browse_scenarios,
                    width=-1,
                )

            dpg.add_spacer(height=10)

            # Load Run section (placeholder for future)
            with dpg.collapsing_header(label="Load Saved Run", default_open=False):
                dpg.add_text("Replay a previously saved simulation", color=(150, 150, 150))
                dpg.add_text("(Coming soon)", color=(100, 100, 100))

        dpg.set_primary_window("main_window", True)
        dpg.setup_dearpygui()
        dpg.show_viewport()

    def _on_seed_change(self, sender: int, app_data: int) -> None:
        """Handle seed input change."""
        self.seed = app_data if app_data != 0 else None

    def _on_configure_live(self) -> None:
        """Handle configure simulation button click - open modal."""
        self._pending_action = "configure"
        self._closed = True

    def _on_browse_scenarios(self) -> None:
        """Handle browse scenarios button click."""
        # Set pending action - don't destroy context from within callback
        self._pending_action = "browse"
        self._closed = True

    def run(self) -> Optional[LaunchConfig]:
        """Run the startup selector and return the selected config."""
        self.setup()

        while dpg.is_dearpygui_running() and not self._closed:
            dpg.render_dearpygui_frame()

        dpg.destroy_context()

        # Handle pending action after context is destroyed
        if self._pending_action == "browse":
            return LaunchConfig(mode="browse")
        elif self._pending_action == "configure":
            # Open the configuration modal with current values
            modal = LiveConfigModal(
                n_agents=self.n_agents,
                grid_size=self.grid_size,
                seed=self.seed,
            )
            config = modal.run()
            if config is not None:
                return config
            # User cancelled - return cancel to show selector again
            return LaunchConfig(mode="cancel")

        return self.result


class ScenarioBrowser:
    """
    Scenario browser window.

    Displays available scenarios organized by complexity level.
    Clicking a scenario launches it in comparison mode.
    """

    WINDOW_WIDTH = 700
    WINDOW_HEIGHT = 600

    def __init__(self, scenarios_dir: Optional[Path] = None):
        self.scenarios_dir = scenarios_dir
        self.scenarios = load_all_scenarios(scenarios_dir)
        self.selected_scenario: Optional[Scenario] = None
        self._closed = False

    def setup(self) -> None:
        """Set up the DearPyGui context and window."""
        dpg.create_context()
        dpg.create_viewport(
            title="Scenario Browser",
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
        )

        with dpg.window(label="Scenarios", tag="main_window", no_title_bar=True):
            with dpg.group(horizontal=True):
                dpg.add_text("Scenario Browser", color=(200, 200, 200))
                dpg.add_spacer(width=20)
                dpg.add_button(
                    label="Back",
                    callback=self._on_back,
                    width=80,
                )

            dpg.add_separator()
            dpg.add_text(
                "Select a scenario to run in comparison mode (Opportunistic vs StableRoommates)",
                color=(150, 150, 150),
            )
            dpg.add_spacer(height=10)

            if not self.scenarios:
                dpg.add_text("No scenarios found.", color=(200, 100, 100))
                dpg.add_text(
                    f"Add YAML files to: {self.scenarios_dir or 'scenarios/'}",
                    color=(150, 150, 150),
                )
            else:
                # Group scenarios by complexity
                by_complexity: dict[int, list[Scenario]] = {}
                for scenario in self.scenarios:
                    level = scenario.complexity
                    if level not in by_complexity:
                        by_complexity[level] = []
                    by_complexity[level].append(scenario)

                complexity_labels = {
                    1: "Fundamentals",
                    2: "Spatial Patterns",
                    3: "Protocol Comparisons",
                    4: "Complex Dynamics",
                }

                for level in sorted(by_complexity.keys()):
                    level_name = complexity_labels.get(level, f"Level {level}")

                    with dpg.collapsing_header(
                        label=f"Level {level}: {level_name}",
                        default_open=True,
                    ):
                        for scenario in by_complexity[level]:
                            self._render_scenario_card(scenario)

        dpg.set_primary_window("main_window", True)
        dpg.setup_dearpygui()
        dpg.show_viewport()

    def _render_scenario_card(self, scenario: Scenario) -> None:
        """Render a single scenario as a clickable card."""
        with dpg.child_window(height=100, border=True):
            with dpg.group(horizontal=True):
                with dpg.group():
                    dpg.add_text(scenario.title, color=(100, 200, 100))

                    # Truncate description to first 100 chars
                    desc = scenario.description
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    dpg.add_text(desc, color=(150, 150, 150), wrap=500)

                    # Tags
                    if scenario.tags:
                        with dpg.group(horizontal=True):
                            for tag in scenario.tags[:4]:  # Show max 4 tags
                                dpg.add_text(f"[{tag}]", color=(100, 100, 150))

                dpg.add_spacer(width=20)

                # Run button (right-aligned)
                with dpg.group():
                    dpg.add_spacer(height=20)
                    dpg.add_button(
                        label="Run",
                        callback=self._on_select_scenario,
                        user_data=scenario,
                        width=80,
                    )
                    dpg.add_text(
                        f"{len(scenario.config.agents)} agents",
                        color=(100, 100, 100),
                    )

    def _on_select_scenario(self, sender, app_data, user_data: Scenario) -> None:
        """Handle scenario selection."""
        self.selected_scenario = user_data
        self._closed = True

    def _on_back(self) -> None:
        """Handle back button - return to startup selector."""
        self.selected_scenario = None
        self._closed = True

    def run(self) -> Optional[Scenario]:
        """Run the browser and return the selected scenario."""
        self.setup()

        while dpg.is_dearpygui_running() and not self._closed:
            dpg.render_dearpygui_frame()

        dpg.destroy_context()
        return self.selected_scenario


def run_scenario_comparison(scenario: Scenario) -> None:
    """
    Run a scenario in comparison mode (Opportunistic vs StableRoommates).

    Creates two simulations from the scenario config and runs them
    with different matching protocols, then displays in dual viewport.
    """
    from microecon.bundle import Bundle
    from microecon.preferences import CobbDouglas
    from microecon.agent import Agent, AgentPrivateState
    from microecon.grid import Grid, Position
    from microecon.information import FullInformation
    from microecon.simulation import Simulation
    from microecon.bargaining import NashBargainingProtocol
    from microecon.matching import OpportunisticMatchingProtocol, StableRoommatesMatchingProtocol
    from microecon.logging import SimulationLogger, SimulationConfig

    config = scenario.config

    def create_simulation_and_logger(matching_protocol, protocol_name: str):
        """Create a simulation with logger from scenario config."""
        # Determine matching protocol name
        matching_name = type(matching_protocol).__name__.replace("Protocol", "").lower()

        # Create simulation config for logger (LA-1: include institutional metadata)
        sim_config = SimulationConfig(
            n_agents=len(config.agents),
            grid_size=config.grid_size,
            seed=0,  # Deterministic from scenario
            protocol_name="nash",
            protocol_params={},
            perception_radius=config.perception_radius,
            discount_factor=config.discount_factor,
            matching_protocol_name=matching_name,
            info_env_name="full_information",
            info_env_params={},
        )

        # Create logger
        logger = SimulationLogger(config=sim_config)

        # Create simulation
        sim = Simulation(
            grid=Grid(config.grid_size),
            info_env=FullInformation(),
            bargaining_protocol=NashBargainingProtocol(),
            matching_protocol=matching_protocol,
        )

        # Add agents from scenario
        for agent_cfg in config.agents:
            agent = Agent(
                id=agent_cfg.id,
                private_state=AgentPrivateState(
                    preferences=CobbDouglas(agent_cfg.alpha),
                    endowment=Bundle(agent_cfg.endowment[0], agent_cfg.endowment[1]),
                ),
                perception_radius=config.perception_radius,
                discount_factor=config.discount_factor,
            )
            pos = Position(agent_cfg.position[1], agent_cfg.position[0])  # (row, col) from (x, y)
            sim.add_agent(agent, pos)

        # Attach logger to simulation
        sim.logger = logger

        return sim, logger

    # Create both simulations with loggers
    sim_opp, logger_opp = create_simulation_and_logger(
        OpportunisticMatchingProtocol(), "opportunistic"
    )
    sim_sr, logger_sr = create_simulation_and_logger(
        StableRoommatesMatchingProtocol(), "stable_roommates"
    )

    # Run both simulations (50 ticks should be enough for most scenarios)
    max_ticks = 50
    sim_opp.run(max_ticks)
    sim_sr.run(max_ticks)

    # Finalize and get run data
    run_opp = logger_opp.finalize()
    run_sr = logger_sr.finalize()

    # Launch comparison view
    from microecon.visualization.app import DualVisualizationApp

    app = DualVisualizationApp(
        run_opp,
        run_sr,
        label_a="Opportunistic",
        label_b="StableRoommates",
    )
    app.run()


def run_with_startup_selector() -> None:
    """
    Main entry point that shows the startup selector.

    This is the recommended way to launch the visualization,
    as it provides access to all modes.
    """
    while True:
        selector = StartupSelector()
        config = selector.run()

        if config is None:
            # User closed window - exit
            break

        if config.mode == "cancel":
            # Cancelled from browser - show selector again
            continue

        if config.mode == "live":
            from microecon.visualization.app import run_visualization
            run_visualization(
                n_agents=config.n_agents,
                grid_size=config.grid_size,
                seed=config.seed,
                bargaining_protocol=config.bargaining_protocol,
                matching_protocol=config.matching_protocol,
                perception_radius=config.perception_radius,
                discount_factor=config.discount_factor,
            )
            break  # Exit after live mode closes

        elif config.mode == "browse":
            # Open scenario browser
            browser = ScenarioBrowser()
            scenario = browser.run()

            if scenario is not None:
                # Run the selected scenario
                run_scenario_comparison(scenario)
                break  # Exit after comparison closes
            # else: scenario was None (user clicked Back) - loop continues to show selector

        elif config.mode == "scenario" and config.scenario is not None:
            run_scenario_comparison(config.scenario)
            break  # Exit after comparison closes
