# Archived: DearPyGui Visualization

**Archived**: 2026-01-08
**Reason**: Replaced by web-based frontend (React/Vite)

## What This Was

A DearPyGui-based desktop visualization for the microecon simulation, providing:
- Live simulation view with agent grid
- Replay mode for logged runs
- Dual comparison mode for protocol comparisons
- Scenario browser
- Trade inspection with Edgeworth box
- Export (PNG/SVG/GIF/CSV/JSON)

## Why Archived

The web frontend (`frontend/` + `backend/`) provides equivalent functionality with:
- Better cross-platform support (browser-based)
- Modern UI framework (React + Tailwind)
- WebSocket-based real-time updates
- Easier deployment and sharing

## Files

```
visualization/
├── __init__.py      # Module exports
├── __main__.py      # Entry point: python -m microecon.visualization
├── app.py           # Main VisualizationApp and DualVisualizationApp
├── browser.py       # Scenario browser, startup selector
├── edgeworth.py     # Edgeworth box trade visualization
├── export.py        # PNG/SVG/GIF/CSV/JSON export
├── network.py       # Trade network graph panel
├── replay.py        # ReplayController for logged runs
└── timeseries.py    # Time-series charts (ImPlot)
```

## Original Usage

```bash
# Live mode
uv run python -m microecon.visualization

# With parameters
uv run python -c "from microecon.visualization import run_visualization; run_visualization(n_agents=20, grid_size=20, seed=42)"

# Replay mode
uv run python -c "from microecon.visualization import run_replay_from_path; run_replay_from_path('runs/example/run.jsonl')"
```

## Dependencies (no longer in main project)

- dearpygui
- dearpygui-ext (for file dialogs)
- PIL/Pillow (for export)

## Restoration

To restore, move back to `src/microecon/visualization/` and add DearPyGui dependencies to pyproject.toml.
