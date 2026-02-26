#!/usr/bin/env python3
"""Generate TypeScript interfaces from canonical event dataclasses.

Introspects the frozen dataclasses in microecon/logging/events.py and emits
TypeScript interfaces suitable for the frontend replay viewer.

Usage:
    python scripts/generate_ts_types.py          # prints to stdout
    python scripts/generate_ts_types.py --write   # writes to frontend/src/types/canonical.ts
"""

from __future__ import annotations

import argparse
import dataclasses
import re
import sys
import types
import typing
from pathlib import Path

from microecon.logging.events import (
    SCHEMA_VERSION,
    AgentSnapshot,
    BeliefSnapshot,
    CommitmentBrokenEvent,
    CommitmentFormedEvent,
    MovementEvent,
    PriceBeliefSnapshot,
    RunSummary,
    SearchDecision,
    SimulationConfig,
    TargetEvaluation,
    TickRecord,
    TradeEvent,
    TypeBeliefSnapshot,
)

# Ordered so referenced types appear before referencing types.
DATACLASSES: list[type] = [
    SimulationConfig,
    AgentSnapshot,
    TargetEvaluation,
    SearchDecision,
    MovementEvent,
    TradeEvent,
    CommitmentFormedEvent,
    CommitmentBrokenEvent,
    TypeBeliefSnapshot,
    PriceBeliefSnapshot,
    BeliefSnapshot,
    TickRecord,
    RunSummary,
]

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "frontend" / "src" / "types" / "canonical.ts"

# ── primitive mapping ────────────────────────────────────────────────

_PRIMITIVES: dict[str, str] = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "Any": "unknown",
}


# ── string-based type mapper (public, tested directly) ───────────────

def python_type_to_ts(type_str: str) -> str:
    """Convert a Python type-annotation *string* to its TypeScript equivalent.

    Examples:
        "str"                                       -> "string"
        "tuple[int, int]"                           -> "[number, number]"
        "tuple[AgentSnapshot, ...]"                 -> "AgentSnapshot[]"
        "tuple[tuple[float, float], ...]"           -> "[number, number][]"
        "str | None"                                -> "string | null"
        "dict[str, Any]"                            -> "Record<string, unknown>"
    """
    s = type_str.strip()

    # Handle union with None  (X | None)
    if " | None" in s:
        inner = s.replace(" | None", "")
        return f"{python_type_to_ts(inner)} | null"

    # Handle dict[K, V]
    m = re.match(r"^dict\[(.+)\]$", s)
    if m:
        parts = _split_top_level(m.group(1))
        if len(parts) == 2:
            k = python_type_to_ts(parts[0])
            v = python_type_to_ts(parts[1])
            return f"Record<{k}, {v}>"

    # Handle tuple[...]
    m = re.match(r"^tuple\[(.+)\]$", s)
    if m:
        inner = m.group(1)
        parts = _split_top_level(inner)
        # Variable-length: tuple[X, ...]
        if len(parts) == 2 and parts[1].strip() == "...":
            elem = python_type_to_ts(parts[0])
            return f"{elem}[]"
        # Fixed-length: tuple[X, Y, ...]
        ts_parts = [python_type_to_ts(p) for p in parts]
        return "[" + ", ".join(ts_parts) + "]"

    # Primitives
    if s in _PRIMITIVES:
        return _PRIMITIVES[s]

    # Unknown type -- pass through as-is (assumes it's an interface name)
    return s


def _split_top_level(s: str) -> list[str]:
    """Split a comma-separated string respecting bracket nesting."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in s:
        if ch in "([":
            depth += 1
            current.append(ch)
        elif ch in ")]":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return parts


# ── runtime type introspection ───────────────────────────────────────

def _get_type_string(field: dataclasses.Field) -> str:
    """Convert a dataclass field's runtime type to a parseable string.

    Handles:
      - plain types (str, int, float, bool)
      - tuple[X, Y], tuple[X, ...]
      - nested tuples
      - X | None  (union with NoneType)
      - dict[K, V]
      - typing.Any
    """
    return _type_to_str(field.type)


def _type_to_str(t: type) -> str:
    """Recursively convert a runtime type annotation to a string."""
    # NoneType
    if t is type(None):
        return "None"

    # typing.Any
    if t is typing.Any:
        return "Any"

    # Union types  (X | None  or  typing.Union[X, None])
    origin = getattr(t, "__origin__", None)

    # Python 3.10+ union syntax: X | None -> types.UnionType
    if isinstance(t, types.UnionType):
        args = t.__args__
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return f"{_type_to_str(non_none[0])} | None"
        # General union (shouldn't appear in our schema, but handle anyway)
        return " | ".join(_type_to_str(a) for a in args)

    # typing.Union
    if origin is typing.Union:
        args = typing.get_args(t)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return f"{_type_to_str(non_none[0])} | None"
        return " | ".join(_type_to_str(a) for a in args)

    # tuple
    if origin is tuple:
        args = typing.get_args(t)
        if not args:
            return "tuple"
        inner = ", ".join(
            "..." if a is Ellipsis else _type_to_str(a)
            for a in args
        )
        return f"tuple[{inner}]"

    # dict
    if origin is dict:
        args = typing.get_args(t)
        if len(args) == 2:
            return f"dict[{_type_to_str(args[0])}, {_type_to_str(args[1])}]"
        return "dict"

    # list
    if origin is list:
        args = typing.get_args(t)
        if args:
            return f"list[{_type_to_str(args[0])}]"
        return "list"

    # Plain class
    if hasattr(t, "__name__"):
        return t.__name__

    # Fallback
    return str(t)


# ── interface generation ─────────────────────────────────────────────

_MISSING = dataclasses.MISSING


def _generate_interface(cls: type) -> str:
    """Generate a single TypeScript interface from a frozen dataclass."""
    lines: list[str] = []
    lines.append(f"export interface {cls.__name__} {{")
    for f in dataclasses.fields(cls):
        ts_type = python_type_to_ts(_get_type_string(f))
        optional = f.default is not _MISSING or f.default_factory is not _MISSING
        name = f.name
        opt = "?" if optional else ""
        lines.append(f"  {name}{opt}: {ts_type};")
    lines.append("}")
    return "\n".join(lines)


def generate() -> str:
    """Generate the complete TypeScript file content."""
    parts: list[str] = []

    # Header
    parts.append("// DO NOT EDIT — this file is auto-generated.")
    parts.append(f"// Generated by scripts/generate_ts_types.py from SCHEMA_VERSION {SCHEMA_VERSION}")
    parts.append("")

    # Schema version constant
    parts.append(f'export const SCHEMA_VERSION = "{SCHEMA_VERSION}";')
    parts.append("")

    # Interfaces
    for cls in DATACLASSES:
        parts.append(_generate_interface(cls))
        parts.append("")

    return "\n".join(parts)


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate TypeScript interfaces from canonical event dataclasses.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help=f"Write output to {OUTPUT_PATH} instead of stdout.",
    )
    args = parser.parse_args()

    output = generate()

    if args.write:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(output)
        print(f"Wrote {OUTPUT_PATH}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
