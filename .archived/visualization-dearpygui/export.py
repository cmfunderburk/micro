"""Export functionality for visualization (VIZ-008 to VIZ-011).

Provides export capabilities for:
- PNG screenshots (VIZ-008)
- SVG vector export (VIZ-009)
- GIF animation export (VIZ-010)
- CSV/JSON data export (VIZ-011)
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional
import json
import csv
import io

if TYPE_CHECKING:
    from microecon.visualization.app import VisualizationApp
    from microecon.logging.events import TickRecord


# ============================================================================
# PNG Export (VIZ-008)
# ============================================================================

def export_png(
    output_path: Path | str,
    scale: float = 1.0,
) -> bool:
    """
    Export current frame as PNG using DearPyGui's screenshot capability.

    Args:
        output_path: Path to save the PNG file
        scale: Resolution scale factor (1.0 = native, 2.0 = 2x resolution)

    Returns:
        True if export succeeded, False otherwise

    Note:
        This function must be called while the DearPyGui viewport is active.
    """
    try:
        import dearpygui.dearpygui as dpg
        from PIL import Image

        if isinstance(output_path, str):
            output_path = Path(output_path)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use DearPyGui's frame buffer output
        # Note: This captures the entire viewport
        width = dpg.get_viewport_client_width()
        height = dpg.get_viewport_client_height()

        # Get frame buffer data
        frame_data = dpg.output_frame_buffer()

        if frame_data is None or len(frame_data) == 0:
            return False

        # Convert to PIL Image
        # DearPyGui returns RGBA data as a flat list
        img = Image.frombytes('RGBA', (width, height), bytes(frame_data))

        # Scale if requested
        if scale != 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save as PNG
        img.save(output_path, 'PNG')
        return True

    except ImportError:
        print("PNG export requires pillow. Install with: uv pip install pillow")
        return False
    except Exception as e:
        print(f"PNG export failed: {e}")
        return False


# ============================================================================
# SVG Export (VIZ-009)
# ============================================================================

@dataclass
class SVGExportConfig:
    """Configuration for SVG export."""
    width: int = 800
    height: int = 800
    include_grid: bool = True
    include_agents: bool = True
    include_trails: bool = False
    include_perception: bool = False


def export_svg(
    app: "VisualizationApp",
    output_path: Path | str,
    config: Optional[SVGExportConfig] = None,
) -> bool:
    """
    Export current visualization state as SVG.

    Args:
        app: The visualization app instance
        output_path: Path to save the SVG file
        config: Export configuration options

    Returns:
        True if export succeeded, False otherwise

    Note:
        SVG is generated manually since DearPyGui doesn't support SVG output.
        This creates a simplified representation of the grid and agents.
    """
    try:
        if isinstance(output_path, str):
            output_path = Path(output_path)

        if config is None:
            config = SVGExportConfig()

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build SVG content
        svg_lines = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{config.width}" height="{config.height}" viewBox="0 0 {config.width} {config.height}">',
            f'  <rect width="100%" height="100%" fill="#1e1e1e"/>',  # Background
        ]

        # Calculate grid layout
        margin = 40
        grid_size = min(config.width, config.height) - 2 * margin
        cell_size = grid_size / app.grid_size
        origin_x = (config.width - grid_size) / 2
        origin_y = (config.height - grid_size) / 2

        # Grid lines
        if config.include_grid:
            svg_lines.append('  <g id="grid" stroke="#c8c8c8" stroke-opacity="0.4" stroke-width="1">')
            for i in range(app.grid_size + 1):
                x = origin_x + i * cell_size
                y = origin_y + i * cell_size
                svg_lines.append(f'    <line x1="{x}" y1="{origin_y}" x2="{x}" y2="{origin_y + grid_size}"/>')
                svg_lines.append(f'    <line x1="{origin_x}" y1="{y}" x2="{origin_x + grid_size}" y2="{y}"/>')
            svg_lines.append('  </g>')

        # Agents
        if config.include_agents:
            svg_lines.append('  <g id="agents">')
            agent_radius = cell_size * 0.35

            for agent in app.get_agents():
                cx = origin_x + (agent.position.col + 0.5) * cell_size
                cy = origin_y + (agent.position.row + 0.5) * cell_size

                # Color based on alpha
                r = int(70 + agent.alpha * (255 - 70))
                g = int(130 + agent.alpha * (140 - 130))
                b = int(180 + agent.alpha * (0 - 180))
                color = f'rgb({r},{g},{b})'

                svg_lines.append(
                    f'    <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{agent_radius:.1f}" fill="{color}"/>'
                )
            svg_lines.append('  </g>')

        svg_lines.append('</svg>')

        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(svg_lines))

        return True

    except Exception as e:
        print(f"SVG export failed: {e}")
        return False


# ============================================================================
# GIF Export (VIZ-010)
# ============================================================================

@dataclass
class GIFExportConfig:
    """Configuration for GIF animation export."""
    start_tick: int = 0
    end_tick: Optional[int] = None  # None = all ticks
    frame_duration_ms: int = 200    # Duration of each frame in milliseconds
    loop: int = 0                    # 0 = loop forever, 1 = play once
    scale: float = 1.0               # Resolution scale


def export_gif(
    output_path: Path | str,
    frames: list[bytes],
    frame_size: tuple[int, int],
    config: Optional[GIFExportConfig] = None,
) -> bool:
    """
    Export frames as animated GIF.

    Args:
        output_path: Path to save the GIF file
        frames: List of RGBA frame data as bytes
        frame_size: (width, height) of each frame
        config: Export configuration options

    Returns:
        True if export succeeded, False otherwise
    """
    try:
        import imageio
        from PIL import Image

        if isinstance(output_path, str):
            output_path = Path(output_path)

        if config is None:
            config = GIFExportConfig()

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert frames to PIL Images
        pil_frames = []
        width, height = frame_size

        for frame_data in frames:
            img = Image.frombytes('RGBA', (width, height), frame_data)

            # Scale if requested
            if config.scale != 1.0:
                new_width = int(width * config.scale)
                new_height = int(height * config.scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to RGB (GIF doesn't support RGBA well)
            img = img.convert('RGB')
            pil_frames.append(img)

        if not pil_frames:
            return False

        # Save as GIF
        pil_frames[0].save(
            output_path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=config.frame_duration_ms,
            loop=config.loop,
        )

        return True

    except ImportError:
        print("GIF export requires pillow and imageio. Install with: uv pip install pillow imageio")
        return False
    except Exception as e:
        print(f"GIF export failed: {e}")
        return False


class GIFRecorder:
    """
    Helper class to record frames for GIF export.

    Usage:
        recorder = GIFRecorder()
        # During playback:
        recorder.capture_frame()
        # When done:
        recorder.export("output.gif")
    """

    def __init__(self):
        self.frames: list[bytes] = []
        self.frame_size: Optional[tuple[int, int]] = None

    def capture_frame(self) -> bool:
        """Capture current viewport frame."""
        try:
            import dearpygui.dearpygui as dpg

            width = dpg.get_viewport_client_width()
            height = dpg.get_viewport_client_height()

            frame_data = dpg.output_frame_buffer()
            if frame_data is None:
                return False

            self.frames.append(bytes(frame_data))
            self.frame_size = (width, height)
            return True

        except Exception:
            return False

    def clear(self) -> None:
        """Clear recorded frames."""
        self.frames.clear()
        self.frame_size = None

    def export(
        self,
        output_path: Path | str,
        config: Optional[GIFExportConfig] = None,
    ) -> bool:
        """Export recorded frames as GIF."""
        if not self.frames or self.frame_size is None:
            return False
        return export_gif(output_path, self.frames, self.frame_size, config)


# ============================================================================
# Data Export (VIZ-011)
# ============================================================================

@dataclass
class DataExportConfig:
    """Configuration for data export."""
    include_agents: bool = True
    include_trades: bool = True
    include_beliefs: bool = True
    include_search_decisions: bool = False
    include_movements: bool = False


def export_tick_json(
    tick_record: "TickRecord",
    output_path: Path | str,
    config: Optional[DataExportConfig] = None,
) -> bool:
    """
    Export tick record as JSON.

    Args:
        tick_record: The tick record to export
        output_path: Path to save the JSON file
        config: Export configuration options

    Returns:
        True if export succeeded, False otherwise
    """
    try:
        if isinstance(output_path, str):
            output_path = Path(output_path)

        if config is None:
            config = DataExportConfig()

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build export data
        data: dict = {
            "tick": tick_record.tick,
            "total_welfare": tick_record.total_welfare,
            "cumulative_trades": tick_record.cumulative_trades,
        }

        if config.include_agents:
            data["agents"] = [s.to_dict() for s in tick_record.agent_snapshots]

        if config.include_trades:
            data["trades"] = [t.to_dict() for t in tick_record.trades]

        if config.include_beliefs:
            data["beliefs"] = [b.to_dict() for b in tick_record.belief_snapshots]

        if config.include_search_decisions:
            data["search_decisions"] = [d.to_dict() for d in tick_record.search_decisions]

        if config.include_movements:
            data["movements"] = [m.to_dict() for m in tick_record.movements]

        # Write JSON
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        return True

    except Exception as e:
        print(f"JSON export failed: {e}")
        return False


def export_agents_csv(
    tick_record: "TickRecord",
    output_path: Path | str,
) -> bool:
    """
    Export agent snapshots as CSV.

    Args:
        tick_record: The tick record to export
        output_path: Path to save the CSV file

    Returns:
        True if export succeeded, False otherwise
    """
    try:
        if isinstance(output_path, str):
            output_path = Path(output_path)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'tick', 'agent_id', 'position_row', 'position_col',
                'endowment_x', 'endowment_y', 'alpha', 'utility',
                'has_beliefs', 'n_trades_in_memory', 'n_type_beliefs'
            ])

            # Rows
            for agent in tick_record.agent_snapshots:
                writer.writerow([
                    tick_record.tick,
                    agent.agent_id,
                    agent.position[0],
                    agent.position[1],
                    agent.endowment[0],
                    agent.endowment[1],
                    agent.alpha,
                    agent.utility,
                    agent.has_beliefs,
                    agent.n_trades_in_memory,
                    agent.n_type_beliefs,
                ])

        return True

    except Exception as e:
        print(f"CSV export failed: {e}")
        return False


def export_trades_csv(
    tick_record: "TickRecord",
    output_path: Path | str,
) -> bool:
    """
    Export trades as CSV.

    Args:
        tick_record: The tick record to export
        output_path: Path to save the CSV file

    Returns:
        True if export succeeded, False otherwise
    """
    try:
        if isinstance(output_path, str):
            output_path = Path(output_path)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'tick', 'agent1_id', 'agent2_id', 'proposer_id',
                'pre_endow1_x', 'pre_endow1_y', 'pre_endow2_x', 'pre_endow2_y',
                'post_alloc1_x', 'post_alloc1_y', 'post_alloc2_x', 'post_alloc2_y',
                'utility1', 'utility2', 'gain1', 'gain2', 'trade_occurred'
            ])

            # Rows
            for trade in tick_record.trades:
                writer.writerow([
                    tick_record.tick,
                    trade.agent1_id,
                    trade.agent2_id,
                    trade.proposer_id,
                    trade.pre_endowments[0][0],
                    trade.pre_endowments[0][1],
                    trade.pre_endowments[1][0],
                    trade.pre_endowments[1][1],
                    trade.post_allocations[0][0],
                    trade.post_allocations[0][1],
                    trade.post_allocations[1][0],
                    trade.post_allocations[1][1],
                    trade.utilities[0],
                    trade.utilities[1],
                    trade.gains[0],
                    trade.gains[1],
                    trade.trade_occurred,
                ])

        return True

    except Exception as e:
        print(f"CSV export failed: {e}")
        return False
