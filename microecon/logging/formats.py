"""Log file formats for simulation logging.

Supports tiered approach:
- JSONLinesFormat: Human-readable, one JSON object per line (default)
- Future: MsgPackFormat for compact binary storage
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from .events import RunSummary, SimulationConfig, TickRecord

if TYPE_CHECKING:
    from .logger import RunData


class LogFormat(ABC):
    """Abstract base class for log file formats."""

    @abstractmethod
    def write_config(self, config: SimulationConfig, path: Path) -> None:
        """Write simulation config to output directory."""
        ...

    @abstractmethod
    def write_tick(self, tick: TickRecord, path: Path) -> None:
        """Append a tick record to the log file."""
        ...

    @abstractmethod
    def write_summary(self, summary: RunSummary, path: Path) -> None:
        """Write run summary to output directory."""
        ...

    @abstractmethod
    def read_run(self, path: Path) -> "RunData":
        """Load a complete run from disk."""
        ...


class JSONLinesFormat(LogFormat):
    """Human-readable JSON lines format.

    File structure:
        run_directory/
        ├── config.json     # SimulationConfig
        ├── ticks.jsonl     # One TickRecord per line
        └── summary.json    # RunSummary (written at end)
    """

    CONFIG_FILE = "config.json"
    TICKS_FILE = "ticks.jsonl"
    SUMMARY_FILE = "summary.json"

    def write_config(self, config: SimulationConfig, path: Path) -> None:
        """Write config.json to output directory."""
        config_path = path / self.CONFIG_FILE
        with open(config_path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

    def write_tick(self, tick: TickRecord, path: Path) -> None:
        """Append tick record as a line to ticks.jsonl."""
        ticks_path = path / self.TICKS_FILE
        with open(ticks_path, "a") as f:
            f.write(json.dumps(tick.to_dict()) + "\n")

    def write_summary(self, summary: RunSummary, path: Path) -> None:
        """Write summary.json to output directory."""
        summary_path = path / self.SUMMARY_FILE
        with open(summary_path, "w") as f:
            json.dump(summary.to_dict(), f, indent=2)

    def read_run(self, path: Path) -> "RunData":
        """Load complete run from directory.

        Args:
            path: Directory containing config.json, ticks.jsonl, and optionally summary.json

        Returns:
            RunData with config, ticks, and summary
        """
        from .logger import RunData

        # Read config
        config_path = path / self.CONFIG_FILE
        with open(config_path) as f:
            config = SimulationConfig.from_dict(json.load(f))

        # Read ticks
        ticks_path = path / self.TICKS_FILE
        ticks = []
        if ticks_path.exists():
            with open(ticks_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        ticks.append(TickRecord.from_dict(json.loads(line)))

        # Read summary if present
        summary = None
        summary_path = path / self.SUMMARY_FILE
        if summary_path.exists():
            with open(summary_path) as f:
                summary = RunSummary.from_dict(json.load(f))

        return RunData(config=config, ticks=ticks, summary=summary)


def load_run(path: Path) -> "RunData":
    """Load a run from disk, auto-detecting format.

    Args:
        path: Directory containing the run data

    Returns:
        RunData with config, ticks, and summary
    """
    # Currently only JSON lines format is supported
    # Future: detect format from file contents
    fmt = JSONLinesFormat()
    return fmt.read_run(path)


def load_batch(path: Path) -> list["RunData"]:
    """Load all runs from a batch directory.

    Assumes each subdirectory is a separate run.

    Args:
        path: Directory containing run subdirectories

    Returns:
        List of RunData objects
    """
    runs = []
    for subdir in sorted(path.iterdir()):
        if subdir.is_dir() and (subdir / JSONLinesFormat.CONFIG_FILE).exists():
            runs.append(load_run(subdir))
    return runs
