# Gemini Codebase Review: Path to 0.0.1 Alpha

**Date:** 2026-01-02
**Status:** Strategic Review
**Target:** 0.0.1 Alpha Release

## 1. Executive Summary

The project has a robust theoretical core (`simulation.py`, `bargaining.py`, `matching.py`) that successfully implements the "Institutional Visibility" vision. The "Live" and "Replay" visualization modes function well as individual components.

However, the project currently feels like a collection of strong mechanisms rather than a cohesive application. The primary gap preventing a "complete" 0.0.1 alpha is the lack of connective tissue between **Configuration** (YAML scenarios), **Execution** (Simulation), and **Output** (UI/Export).

The "Scenario Pipeline" is effectively broken: we can load YAML (`loader.py`), and we can run a hardcoded simulation (`create_simple_economy`), but we cannot yet run a YAML-defined simulation.

## 2. Critical Blockers (Must-Fix for 0.0.1)

### 2.1 The Missing "Scenario Bridge"
**Severity: Critical**

We have the *Data* (`scenarios/*.yaml`) and the *Parser* (`src/microecon/scenarios/loader.py`), but we lack the *Factory* to actually build a simulation from that data.

*   **Issue:** `simulation.py` relies on `create_simple_economy()` which has hardcoded logic.
*   **Requirement:** A new factory function (likely in `src/microecon/scenarios/factory.py`) that accepts a `ScenarioConfig` object and returns a fully populated `Simulation` instance (placing agents at specific coordinates, setting specific alphas/endowments defined in YAML).
*   **User Impact:** Without this, users cannot run the scenarios defined in the design docs (`trading_chain`, `hub_and_spoke`) without writing Python code.

### 2.2 UI Integration: Load & Export
**Severity: High**

The user requirements specify "Load Scenario" and "Export" are hard requirements.

*   **Load Scenario:** The `VisualizationApp` currently defaults immediately to `create_simple_economy`. It needs a startup screen or a menu bar to select a YAML file from `scenarios/`, parse it, and initialize the simulation using the factory described in 2.1.
*   **Export Data:** Currently, "Live" runs in `VisualizationApp` do not initialize a `SimulationLogger`. If a user sees an interesting phenomenon in Live mode, it is lost forever.
    *   *Fix:* Live mode should optionally auto-log to a temp directory, or allow "Save Run" which dumps the history to JSONL.
*   **Export Image:** No mechanism exists to capture the current grid state as PNG/SVG.

### 2.3 Documentation Consistency
**Severity: Medium**

*   **Issue:** `THEORETICAL_TESTS.md` refers to `tests/test_theoretical_scenarios.py`, which no longer exists (refactored into `tests/scenarios/`).
*   **Fix:** Update documentation to reflect the current file structure.

## 3. Code Quality & Refactoring

### 3.1 Visualization DRY (Don't Repeat Yourself)
**Severity: Medium**

`VisualizationApp` and `DualVisualizationApp` in `src/microecon/visualization/app.py` share significant rendering logic (grid lines, agent drawing, tooltips, trail rendering).
*   **Recommendation:** Extract a `GridRenderer` class that handles the DearPyGui drawlist operations. Both apps should delegate drawing to this renderer. This ensures visual consistency and makes adding features (like "Export Image") easier to implement in one place.

### 3.2 Scenario Loader Robustness
**Severity: Low**

The current `loader.py` attempts to guess the scenarios directory.
*   **Recommendation:** Make the scenarios directory strictly configurable or explicitly passed, rather than guessing relative to `__file__`. Add schema validation (using Pydantic or strict checking) to ensure YAML files perfectly match the `AgentConfig` expectations before crashing the simulation.

## 4. UX/UI Polish

### 4.1 Unified Entry Point
The current CLI (`python -m microecon.visualization`) is functional but opaque.
*   **Recommendation:** Implement a proper CLI using `argparse` or `click` that clearly separates modes:
    *   `microecon viz` (Opens UI launcher)
    *   `microecon viz --scenario scenarios/trading_chain.yaml` (Direct load)
    *   `microecon viz --replay runs/run_123` (Direct replay)
    *   `microecon viz --compare runs/run_A runs/run_B` (Comparison mode)

### 4.2 Dashboard "Mode Switcher"
Currently, you cannot switch between "Live", "Replay", and "Comparison" without restarting the application. A simple "File > Load..." or mode switching dropdown in the UI would significantly improve the "Application" feel.

## 5. Implementation Plan

To reach 0.0.1 Alpha, I recommend the following ordered tasks:

1.  **Build the Factory:** Implement `src/microecon/scenarios/factory.py` to convert `ScenarioConfig` -> `Simulation`.
2.  **Connect the Pipes:** Update `src/microecon/visualization/app.py` to accept a `scenario_path` argument.
3.  **UI Controls:** Add a "Load Scenario" file selector to the DearPyGui window.
4.  **Logging Integration:** Ensure Live runs produce logs (enabled by default or toggleable), enabling "Save" functionality.
5.  **Refactor Viz:** Extract `GridRenderer` to clean up `app.py`.
6.  **Docs Update:** Fix `THEORETICAL_TESTS.md`.

## 6. Conclusion

The codebase is technically sound but operationally disjointed. We have the ingredients for a meal but are currently serving them on separate plates. Connecting the **Scenario Loader** to the **Simulation Engine** and exposing that via the **Visualization UI** is the definitive path to a release-worthy 0.0.1.
