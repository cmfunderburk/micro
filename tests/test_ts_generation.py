"""Tests for TypeScript type generation script."""

import importlib.util
import sys
from pathlib import Path

# Load the script as a module via importlib
_script_path = Path(__file__).resolve().parent.parent / "scripts" / "generate_ts_types.py"
_spec = importlib.util.spec_from_file_location("generate_ts_types", _script_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["generate_ts_types"] = _mod
_spec.loader.exec_module(_mod)

python_type_to_ts = _mod.python_type_to_ts
generate = _mod.generate


CANONICAL_TYPES = [
    "SimulationConfig",
    "AgentSnapshot",
    "TargetEvaluation",
    "SearchDecision",
    "MovementEvent",
    "TradeEvent",
    "CommitmentFormedEvent",
    "CommitmentBrokenEvent",
    "TypeBeliefSnapshot",
    "PriceBeliefSnapshot",
    "BeliefSnapshot",
    "TickRecord",
    "RunSummary",
]


class TestTypeMapping:
    """Test Python-to-TypeScript type mapping."""

    def test_primitive_types(self):
        assert python_type_to_ts("str") == "string"
        assert python_type_to_ts("int") == "number"
        assert python_type_to_ts("float") == "number"
        assert python_type_to_ts("bool") == "boolean"

    def test_tuple_fixed(self):
        assert python_type_to_ts("tuple[int, int]") == "[number, number]"

    def test_tuple_variable(self):
        assert python_type_to_ts("tuple[AgentSnapshot, ...]") == "AgentSnapshot[]"

    def test_nested_tuple(self):
        result = python_type_to_ts(
            "tuple[tuple[float, float], tuple[float, float]]"
        )
        assert result == "[[number, number], [number, number]]"

    def test_optional(self):
        assert python_type_to_ts("str | None") == "string | null"
        assert python_type_to_ts("float | None") == "number | null"

    def test_dict(self):
        assert python_type_to_ts("dict[str, Any]") == "Record<string, unknown>"


class TestGeneration:
    """Test full TypeScript generation output."""

    def setup_method(self):
        self.output = generate()

    def test_generates_all_canonical_types(self):
        for name in CANONICAL_TYPES:
            assert f"export interface {name}" in self.output, (
                f"Missing export interface {name}"
            )

    def test_includes_schema_version_constant(self):
        assert "SCHEMA_VERSION" in self.output

    def test_includes_do_not_edit_header(self):
        assert "DO NOT EDIT" in self.output
        assert "generate_ts_types.py" in self.output

    def test_schema_version_field_on_config(self):
        # schema_version has a default, so it is marked optional in TS output
        assert "schema_version?: string" in self.output
