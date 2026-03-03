# A-101: Canonical Schema Package Definition — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish the canonical schema with versioning, build-time TS generation, explicit server→logging config mapping, and documented contract.

**Architecture:** The frozen dataclasses in `microecon/logging/events.py` are the single source of truth. A build-time script introspects them and generates `frontend/src/types/canonical.ts`. Schema version lives in `config.json` and the replay API envelope. The live WebSocket and replay paths are explicit presentation adapters — derived fields (alpha1/alpha2, split holdings, field renames) live in adapters, not canonical schema.

**Tech Stack:** Python dataclasses (canonical), `dataclasses.fields()` introspection (generation), TypeScript (generated types)

**Decisions (locked):**
1. Canonical core + adapters (TickRecord is source of truth)
2. Python canonical → generated TS types (build-time script)
3. Global semver schema_version
4. Version in config.json + replay API envelope
5. Derived fields in adapters only, not canonical schema
6. N and N-1 readable; writes latest only

---

### Task 1: Add `schema_version` to logging SimulationConfig

**Files:**
- Modify: `microecon/logging/events.py:12-65`
- Modify: `tests/test_logging.py:31-43`

**Step 1: Write the failing test**

In `tests/test_logging.py`, add to `TestEventSerialization`:

```python
def test_simulation_config_includes_schema_version(self):
    config = SimulationConfig(
        n_agents=10,
        grid_size=15,
        seed=42,
        protocol_name="nash",
    )
    d = config.to_dict()
    assert "schema_version" in d
    assert d["schema_version"] == "1.0"

def test_simulation_config_from_dict_without_schema_version(self):
    """Pre-versioning configs (no schema_version key) load as version 0.0."""
    d = {
        "n_agents": 10,
        "grid_size": 15,
        "seed": 42,
        "protocol_name": "nash",
    }
    config = SimulationConfig.from_dict(d)
    assert config.schema_version == "0.0"

def test_simulation_config_roundtrip_preserves_schema_version(self):
    config = SimulationConfig(
        n_agents=10, grid_size=15, seed=42, protocol_name="nash",
    )
    d = config.to_dict()
    restored = SimulationConfig.from_dict(d)
    assert restored.schema_version == "1.0"
    assert restored == config
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_logging.py::TestEventSerialization::test_simulation_config_includes_schema_version tests/test_logging.py::TestEventSerialization::test_simulation_config_from_dict_without_schema_version tests/test_logging.py::TestEventSerialization::test_simulation_config_roundtrip_preserves_schema_version -v`
Expected: FAIL (no `schema_version` field)

**Step 3: Implement**

In `microecon/logging/events.py`, modify `SimulationConfig`:

1. Add a module-level constant above the class (line ~11):
   ```python
   SCHEMA_VERSION = "1.0"
   ```

2. Add field to `SimulationConfig` (after `info_env_params`, line ~34):
   ```python
   schema_version: str = SCHEMA_VERSION
   ```

3. Add to `to_dict()` (line ~37, add as first entry):
   ```python
   "schema_version": self.schema_version,
   ```

4. Add to `from_dict()` (line ~53):
   ```python
   schema_version=d.get("schema_version", "0.0"),
   ```

5. Export `SCHEMA_VERSION` from `microecon/logging/__init__.py` — add to imports and `__all__`.

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_logging.py::TestEventSerialization -v`
Expected: ALL PASS

**Step 5: Run full logging test suite**

Run: `.venv/bin/pytest tests/test_logging.py -v`
Expected: ALL PASS (existing roundtrip tests still work because `schema_version` has a default)

**Step 6: Commit**

```bash
git add microecon/logging/events.py microecon/logging/__init__.py tests/test_logging.py
git commit -m "feat(schema): add schema_version to SimulationConfig (A-101)"
```

---

### Task 2: Version validation on load

**Files:**
- Modify: `microecon/logging/formats.py:75-108`
- Modify: `microecon/logging/events.py` (import SCHEMA_VERSION)
- Test: `tests/test_logging.py`

**Step 1: Write the failing test**

In `tests/test_logging.py`, add a new test class:

```python
class TestSchemaVersionValidation:
    """Test schema version validation on load."""

    def test_load_current_version(self):
        """Loading a run with current schema_version succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            fmt = JSONLinesFormat()

            config = SimulationConfig(
                n_agents=2, grid_size=5, seed=42, protocol_name="nash",
            )
            fmt.write_config(config, path)

            # Write one tick so the run is valid
            tick = TickRecord(
                tick=1, agent_snapshots=(), search_decisions=(),
                movements=(), trades=(), total_welfare=10.0,
                cumulative_trades=0,
            )
            fmt.write_tick(tick, path)

            run_data = fmt.read_run(path)
            assert run_data.config.schema_version == "1.0"

    def test_load_pre_versioning_run(self):
        """Loading a run without schema_version succeeds (version 0.0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Write a config.json WITHOUT schema_version (simulates old run)
            config_dict = {
                "n_agents": 2, "grid_size": 5, "seed": 42,
                "protocol_name": "nash",
            }
            with open(path / "config.json", "w") as f:
                json.dump(config_dict, f)

            # Write one tick
            tick = TickRecord(
                tick=1, agent_snapshots=(), search_decisions=(),
                movements=(), trades=(), total_welfare=10.0,
                cumulative_trades=0,
            )
            with open(path / "ticks.jsonl", "w") as f:
                f.write(json.dumps(tick.to_dict()) + "\n")

            run_data = load_run(path)
            assert run_data.config.schema_version == "0.0"

    def test_load_future_version_raises(self):
        """Loading a run with unsupported future version raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            config_dict = {
                "n_agents": 2, "grid_size": 5, "seed": 42,
                "protocol_name": "nash",
                "schema_version": "99.0",
            }
            with open(path / "config.json", "w") as f:
                json.dump(config_dict, f)

            with open(path / "ticks.jsonl", "w") as f:
                f.write("{}\n")  # Minimal tick (will fail to parse, but we check version first)

            with pytest.raises(ValueError, match="Unsupported schema version"):
                load_run(path)
```

**Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_logging.py::TestSchemaVersionValidation -v`
Expected: `test_load_future_version_raises` FAILS (no version check exists yet)

**Step 3: Implement**

In `microecon/logging/formats.py`, modify `JSONLinesFormat.read_run()` (line ~88):

After reading config (line 89), add version validation:

```python
# Read config
config_path = path / self.CONFIG_FILE
with open(config_path) as f:
    config = SimulationConfig.from_dict(json.load(f))

# Validate schema version
_validate_schema_version(config.schema_version)
```

Add the validation function above the class (after imports):

```python
from .events import SCHEMA_VERSION

_SUPPORTED_VERSIONS = {"0.0", SCHEMA_VERSION}

def _validate_schema_version(version: str) -> None:
    """Validate that a schema version is supported.

    Supports current version and one prior (N and N-1 policy).
    Pre-versioning runs have version "0.0".
    """
    if version not in _SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported schema version: {version!r}. "
            f"Supported versions: {sorted(_SUPPORTED_VERSIONS)}. "
            f"This run may have been created by a newer version of microecon."
        )
```

**Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_logging.py::TestSchemaVersionValidation -v`
Expected: ALL PASS

**Step 5: Full suite check**

Run: `.venv/bin/pytest tests/test_logging.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add microecon/logging/formats.py tests/test_logging.py
git commit -m "feat(schema): add version validation on load (A-101)"
```

---

### Task 3: Add `schema_version` to replay API envelope

**Files:**
- Modify: `server/routes.py:286-291`
- Modify: `tests/test_replay_loader.py`

**Step 1: Write the failing test**

In `tests/test_replay_loader.py`, add:

```python
def test_replay_config_includes_schema_version(run_dir):
    """Persisted config.json must include schema_version."""
    config_file = run_dir / "config.json"

    with open(config_file) as f:
        config = json.load(f)

    assert "schema_version" in config
    assert config["schema_version"] == "1.0"
```

**Step 2: Run to verify**

Run: `.venv/bin/pytest tests/test_replay_loader.py::test_replay_config_includes_schema_version -v`
Expected: PASS (Task 1 already adds schema_version to to_dict/config.json). If it fails, Task 1 has a bug.

**Step 3: Update the replay API response envelope**

In `server/routes.py`, modify the return block (line ~286):

```python
return {
    "name": run_name,
    "config": config,
    "ticks": ticks,
    "n_ticks": len(ticks),
    "schema_version": config.get("schema_version", "0.0"),
}
```

**Step 4: Commit**

```bash
git add server/routes.py tests/test_replay_loader.py
git commit -m "feat(schema): include schema_version in replay API envelope (A-101)"
```

---

### Task 4: Explicit server → logging config conversion

**Files:**
- Modify: `server/simulation_manager.py:36-107`
- Create: `tests/test_config_conversion.py`

**Step 1: Write the failing test**

Create `tests/test_config_conversion.py`:

```python
"""Tests for server → logging SimulationConfig conversion."""

import pytest

from server.simulation_manager import SimulationConfig as ServerConfig
from microecon.logging import SimulationConfig as LoggingConfig


class TestServerToLoggingConfigConversion:
    """Test explicit config conversion between server and logging domains."""

    def test_basic_conversion(self):
        server_config = ServerConfig(
            n_agents=10,
            grid_size=15,
            perception_radius=7.0,
            discount_factor=0.95,
            seed=42,
            bargaining_protocol="nash",
        )
        logging_config = server_config.to_logging_config()

        assert isinstance(logging_config, LoggingConfig)
        assert logging_config.n_agents == 10
        assert logging_config.grid_size == 15
        assert logging_config.seed == 42
        assert logging_config.protocol_name == "nash"
        assert logging_config.perception_radius == 7.0
        assert logging_config.discount_factor == 0.95

    def test_protocol_name_mapping(self):
        """Server uses 'bargaining_protocol', logging uses 'protocol_name'."""
        for protocol in ["nash", "rubinstein", "tioli", "asymmetric_nash"]:
            server_config = ServerConfig(
                seed=42, bargaining_protocol=protocol,
            )
            logging_config = server_config.to_logging_config()
            assert logging_config.protocol_name == protocol

    def test_info_env_mapping(self):
        server_config = ServerConfig(
            seed=42,
            info_env_name="noisy_alpha",
            info_env_params={"noise_std": 0.2},
        )
        logging_config = server_config.to_logging_config()
        assert logging_config.info_env_name == "noisy_alpha"
        assert logging_config.info_env_params == {"noise_std": 0.2}

    def test_schema_version_is_current(self):
        from microecon.logging.events import SCHEMA_VERSION

        server_config = ServerConfig(seed=42)
        logging_config = server_config.to_logging_config()
        assert logging_config.schema_version == SCHEMA_VERSION

    def test_seed_none_raises(self):
        """Logging config requires a seed; conversion should raise if missing."""
        server_config = ServerConfig(seed=None)
        with pytest.raises(ValueError, match="seed"):
            server_config.to_logging_config()
```

**Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_config_conversion.py -v`
Expected: FAIL (`to_logging_config` doesn't exist)

**Step 3: Implement**

In `server/simulation_manager.py`, add method to `SimulationConfig` (after `from_dict`, around line ~108):

```python
def to_logging_config(self) -> "LoggingSimulationConfig":
    """Convert server config to logging config for run persistence.

    The server config captures user intent (what to create).
    The logging config captures what was created (for reproducibility).
    """
    from microecon.logging.events import SimulationConfig as LoggingSimulationConfig

    if self.seed is None:
        raise ValueError(
            "Cannot convert to logging config without a seed. "
            "Assign a seed before persisting."
        )

    # Map server field names to logging field names
    return LoggingSimulationConfig(
        n_agents=self.n_agents,
        grid_size=self.grid_size,
        seed=self.seed,
        protocol_name=self.bargaining_protocol,  # rename
        perception_radius=self.perception_radius,
        discount_factor=self.discount_factor,
        info_env_name=self.info_env_name,
        info_env_params=self.info_env_params,
    )
```

**Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_config_conversion.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add server/simulation_manager.py tests/test_config_conversion.py
git commit -m "feat(schema): add explicit server→logging config conversion (A-101)"
```

---

### Task 5: Build TS type generation script

**Files:**
- Create: `scripts/generate_ts_types.py`
- Test: `tests/test_ts_generation.py`

**Step 1: Write the test**

Create `tests/test_ts_generation.py`:

```python
"""Tests for TypeScript type generation from canonical Python dataclasses."""

import importlib
import sys
from pathlib import Path

import pytest

# Import the generation script as a module
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


def _load_generator():
    """Load the generation script as a module."""
    spec = importlib.util.spec_from_file_location(
        "generate_ts_types", SCRIPTS_DIR / "generate_ts_types.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestTypeMapping:
    """Test Python → TypeScript type mapping."""

    def test_primitive_types(self):
        gen = _load_generator()
        assert gen.python_type_to_ts("str") == "string"
        assert gen.python_type_to_ts("int") == "number"
        assert gen.python_type_to_ts("float") == "number"
        assert gen.python_type_to_ts("bool") == "boolean"

    def test_tuple_fixed(self):
        gen = _load_generator()
        assert gen.python_type_to_ts("tuple[int, int]") == "[number, number]"
        assert gen.python_type_to_ts("tuple[float, float]") == "[number, number]"

    def test_tuple_variable(self):
        gen = _load_generator()
        # tuple[X, ...] means variable-length array
        assert gen.python_type_to_ts("tuple[AgentSnapshot, ...]") == "AgentSnapshot[]"

    def test_nested_tuple(self):
        gen = _load_generator()
        assert gen.python_type_to_ts(
            "tuple[tuple[float, float], tuple[float, float]]"
        ) == "[[number, number], [number, number]]"

    def test_optional(self):
        gen = _load_generator()
        assert gen.python_type_to_ts("str | None") == "string | null"
        assert gen.python_type_to_ts("float | None") == "number | null"

    def test_dict(self):
        gen = _load_generator()
        assert gen.python_type_to_ts("dict[str, Any]") == "Record<string, unknown>"


class TestGeneration:
    """Test that generation produces valid output."""

    def test_generates_all_canonical_types(self):
        gen = _load_generator()
        output = gen.generate()

        # Must include all canonical dataclasses
        for name in [
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
        ]:
            assert f"export interface {name}" in output, f"Missing interface: {name}"

    def test_includes_schema_version_constant(self):
        gen = _load_generator()
        output = gen.generate()
        assert "SCHEMA_VERSION" in output

    def test_includes_do_not_edit_header(self):
        gen = _load_generator()
        output = gen.generate()
        assert "DO NOT EDIT" in output
        assert "generate_ts_types.py" in output

    def test_schema_version_field_on_config(self):
        gen = _load_generator()
        output = gen.generate()
        assert "schema_version: string" in output
```

**Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_ts_generation.py -v`
Expected: FAIL (script doesn't exist)

**Step 3: Implement the generation script**

Create `scripts/generate_ts_types.py`:

```python
#!/usr/bin/env python3
"""Generate TypeScript interfaces from canonical Python dataclasses.

Reads the frozen dataclasses in microecon/logging/events.py and emits
TypeScript interfaces to frontend/src/types/canonical.ts.

Usage:
    python scripts/generate_ts_types.py          # prints to stdout
    python scripts/generate_ts_types.py --write   # writes to canonical.ts
"""

import dataclasses
import re
import sys
import typing
from pathlib import Path

# Add project root to path so we can import microecon
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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

# Ordered so that referenced types appear before referencing types
CANONICAL_CLASSES = [
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

OUTPUT_PATH = PROJECT_ROOT / "frontend" / "src" / "types" / "canonical.ts"


def python_type_to_ts(type_str: str) -> str:
    """Convert a Python type annotation string to TypeScript."""
    type_str = type_str.strip()

    # Primitives
    primitives = {"str": "string", "int": "number", "float": "number", "bool": "boolean"}
    if type_str in primitives:
        return primitives[type_str]

    # Any
    if type_str == "Any":
        return "unknown"

    # Optional / union with None: "X | None"
    if type_str.endswith(" | None"):
        inner = type_str[: -len(" | None")]
        return f"{python_type_to_ts(inner)} | null"

    # dict[str, Any] → Record<string, unknown>
    dict_match = re.match(r"dict\[(\w+),\s*(\w+)\]", type_str)
    if dict_match:
        key_type = python_type_to_ts(dict_match.group(1))
        val_type = python_type_to_ts(dict_match.group(2))
        return f"Record<{key_type}, {val_type}>"

    # tuple[X, ...] → X[] (variable-length)
    varlen_match = re.match(r"tuple\[(\w+),\s*\.\.\.\]", type_str)
    if varlen_match:
        inner = varlen_match.group(1)
        return f"{python_type_to_ts(inner)}[]"

    # tuple[tuple[float, float], tuple[float, float]] → nested
    nested_tuple_match = re.match(
        r"tuple\[(tuple\[.+?\]),\s*(tuple\[.+?\])\]", type_str
    )
    if nested_tuple_match:
        t1 = python_type_to_ts(nested_tuple_match.group(1))
        t2 = python_type_to_ts(nested_tuple_match.group(2))
        return f"[{t1}, {t2}]"

    # tuple[X, Y] → [X, Y] (fixed-length)
    fixed_tuple_match = re.match(r"tuple\[(.+)\]", type_str)
    if fixed_tuple_match:
        inner = fixed_tuple_match.group(1)
        parts = [p.strip() for p in inner.split(",")]
        ts_parts = [python_type_to_ts(p) for p in parts]
        return f"[{', '.join(ts_parts)}]"

    # Fallback: assume it's a known interface name
    return type_str


def _get_type_string(field_obj: dataclasses.Field) -> str:
    """Extract a clean type string from a dataclass field."""
    t = field_obj.type

    # Handle actual type objects (not strings)
    if hasattr(t, "__origin__"):
        origin = getattr(t, "__origin__", None)
        args = typing.get_args(t)

        if origin is tuple:
            if len(args) == 2 and args[1] is Ellipsis:
                return f"tuple[{args[0].__name__}, ...]"
            inner_parts = []
            for a in args:
                if hasattr(a, "__origin__") and getattr(a, "__origin__") is tuple:
                    sub_args = typing.get_args(a)
                    inner_parts.append(
                        f"tuple[{', '.join(sa.__name__ for sa in sub_args)}]"
                    )
                elif hasattr(a, "__name__"):
                    inner_parts.append(a.__name__)
                else:
                    inner_parts.append(str(a))
            return f"tuple[{', '.join(inner_parts)}]"

        if origin is dict:
            key_t = args[0].__name__ if hasattr(args[0], "__name__") else str(args[0])
            val_t = args[1].__name__ if hasattr(args[1], "__name__") else str(args[1])
            return f"dict[{key_t}, {val_t}]"

    # types.UnionType: X | None
    if hasattr(t, "__args__") and type(t).__name__ == "UnionType":
        args = t.__args__
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            name = non_none[0].__name__ if hasattr(non_none[0], "__name__") else str(non_none[0])
            return f"{name} | None"

    if isinstance(t, str):
        return t

    if hasattr(t, "__name__"):
        return t.__name__

    return str(t)


def _field_is_optional(field_obj: dataclasses.Field) -> bool:
    """Check if a field has a default value (making it optional in TS)."""
    return (
        field_obj.default is not dataclasses.MISSING
        or field_obj.default_factory is not dataclasses.MISSING
    )


def generate_interface(cls: type) -> str:
    """Generate a TypeScript interface from a Python dataclass."""
    lines = [f"export interface {cls.__name__} {{"]

    for f in dataclasses.fields(cls):
        # Skip internal fields
        if f.name.startswith("_"):
            continue

        ts_type = python_type_to_ts(_get_type_string(f))
        optional = "?" if _field_is_optional(f) else ""
        lines.append(f"  {f.name}{optional}: {ts_type};")

    lines.append("}")
    return "\n".join(lines)


def generate() -> str:
    """Generate the complete canonical.ts file content."""
    header = f"""\
/**
 * Canonical schema types — DO NOT EDIT
 *
 * Generated by scripts/generate_ts_types.py from microecon/logging/events.py.
 * These types represent the persisted schema (what's on disk).
 * Presentation types (what the frontend receives) are in simulation.ts.
 *
 * Schema version: {SCHEMA_VERSION}
 */

export const SCHEMA_VERSION = "{SCHEMA_VERSION}";
"""

    interfaces = []
    for cls in CANONICAL_CLASSES:
        interfaces.append(generate_interface(cls))

    return header + "\n" + "\n\n".join(interfaces) + "\n"


def main() -> None:
    output = generate()

    if "--write" in sys.argv:
        OUTPUT_PATH.write_text(output)
        print(f"Written to {OUTPUT_PATH}")
    else:
        print(output)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_ts_generation.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add scripts/generate_ts_types.py tests/test_ts_generation.py
git commit -m "feat(schema): add TS type generation script (A-101)"
```

---

### Task 6: Generate canonical types and integrate into frontend

**Files:**
- Create: `frontend/src/types/canonical.ts` (generated)
- Modify: `frontend/src/types/simulation.ts`

**Step 1: Run the generation script**

Run: `.venv/bin/python scripts/generate_ts_types.py --write`
Expected: `Written to frontend/src/types/canonical.ts`

**Step 2: Verify the generated file**

Read `frontend/src/types/canonical.ts` and confirm it contains all 13 interfaces with correct field types. Spot-check:
- `SimulationConfig` has `schema_version?: string`
- `AgentSnapshot` has `endowment?: [number, number]`
- `TradeEvent` has `pre_holdings?: [[number, number], [number, number]]`
- `TickRecord` has `agent_snapshots?: AgentSnapshot[]`

**Step 3: Update simulation.ts with canonical type references**

In `frontend/src/types/simulation.ts`, add an import and document the adapter relationship. At the top of the file:

```typescript
/**
 * Presentation types for simulation data received from the backend.
 *
 * These types describe the ADAPTER OUTPUT — what the frontend actually receives
 * from the live WebSocket and replay API. They differ from the canonical schema
 * (see canonical.ts) in field names and derived fields:
 *
 * Adapter mappings:
 *   canonical AgentSnapshot.agent_id  → Agent.id
 *   canonical AgentSnapshot.endowment → Agent.endowment (current holdings, not initial)
 *   canonical TradeEvent.pre_holdings[0] → Trade.pre_holdings_1
 *   canonical TradeEvent.post_allocations[0] → Trade.post_allocation_1
 *   Trade.alpha1, Trade.alpha2 — derived from AgentSnapshot.alpha (not in canonical TradeEvent)
 *
 * See docs/contracts/schema-v1.md for the full contract specification.
 */
```

Remove the old single-line doc comment at the top (`/** Types for simulation data received from the backend. */`).

**Step 4: Run frontend typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors (canonical.ts is standalone, nothing imports it yet)

**Step 5: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: Clean

**Step 6: Commit**

```bash
git add frontend/src/types/canonical.ts frontend/src/types/simulation.ts
git commit -m "feat(schema): generate canonical.ts and document adapter mappings (A-101)"
```

---

### Task 7: Document the schema contract

**Files:**
- Create: `docs/contracts/schema-v1.md`

**Step 1: Write the contract document**

Create `docs/contracts/schema-v1.md`:

```markdown
# Schema Contract v1.0

**Canonical source:** `microecon/logging/events.py`
**Generated types:** `frontend/src/types/canonical.ts`
**Presentation types:** `frontend/src/types/simulation.ts`

---

## Versioning

- **Format:** Semantic versioning (MAJOR.MINOR)
- **Current version:** 1.0
- **Location:** `schema_version` field in `config.json` and replay API envelope
- **Compatibility policy:** Readers support version N (current) and N-1. Writes always use latest version.
- **Pre-versioning runs:** Loaded as version "0.0" (N-1 of 1.0)

## Canonical Schema Family

These frozen dataclasses in `microecon/logging/events.py` are the single source of truth:

| Dataclass | Purpose | Persisted | Live WS |
|---|---|---|---|
| SimulationConfig | Run configuration and institutional settings | config.json | — |
| AgentSnapshot | Agent state at a point in time | tick.agent_snapshots | — |
| TargetEvaluation | Search target analysis | tick.search_decisions[].evaluations | — |
| SearchDecision | Agent search logic record | tick.search_decisions | — |
| MovementEvent | Physical movement record | tick.movements | — |
| TradeEvent | Bilateral exchange record | tick.trades | — |
| CommitmentFormedEvent | Matching state formation | tick.commitments_formed | — |
| CommitmentBrokenEvent | Matching state dissolution | tick.commitments_broken | — |
| TypeBeliefSnapshot | Type belief state | tick.belief_snapshots[].type_beliefs | — |
| PriceBeliefSnapshot | Price belief state | tick.belief_snapshots[].price_belief | — |
| BeliefSnapshot | Complete belief state | tick.belief_snapshots | — |
| TickRecord | Complete tick snapshot | ticks.jsonl (one per line) | — |
| RunSummary | Final run statistics | summary.json | — |

## Persisted File Layout

```
run_directory/
├── config.json     # SimulationConfig.to_dict() — includes schema_version
├── ticks.jsonl     # One TickRecord.to_dict() per line
└── summary.json    # RunSummary.to_dict()
```

## Presentation Adapters

The frontend receives data through two adapters that transform canonical schema into presentation format:

### Live WebSocket (server/simulation_manager.py)

Built from live Simulation objects. Includes fields not in the canonical schema:
- `interaction_state` — agent's exchange sequence state machine
- `bargaining_power` — institutional bargaining weight
- `alpha1`, `alpha2` on trades — looked up from agents at serialization time

### Replay API (server/routes.py)

Built from persisted TickRecord data. Transforms include:
- `agent_id` → `id` (field rename)
- `target_agent_id` → `target_id` (field rename in beliefs)
- `pre_holdings[0]` → `pre_holdings_1` (tuple unpacking)
- `post_allocations[0]` → `post_allocation_1` (tuple unpacking)
- `alpha1`, `alpha2` — derived from AgentSnapshot.alpha on same tick
- `belief_snapshots` array → `beliefs` map keyed by agent_id

## Derived Fields Policy

Derived fields are computed by presentation adapters, NOT stored in the canonical schema:

| Derived Field | Source | Adapter |
|---|---|---|
| Trade.alpha1 | AgentSnapshot.alpha for agent1_id | Both |
| Trade.alpha2 | AgentSnapshot.alpha for agent2_id | Both |
| Trade.pre_holdings_1 | TradeEvent.pre_holdings[0] | Replay |
| Trade.pre_holdings_2 | TradeEvent.pre_holdings[1] | Replay |
| Trade.post_allocation_1 | TradeEvent.post_allocations[0] | Replay |
| Trade.post_allocation_2 | TradeEvent.post_allocations[1] | Replay |

## Server vs Logging SimulationConfig

Two separate config dataclasses serve different roles:

| | Server (simulation_manager.py) | Logging (events.py) |
|---|---|---|
| Purpose | What to create | What was created |
| Key field | `bargaining_protocol` | `protocol_name` |
| Has `use_beliefs` | Yes | No |
| Has `agents` (scenario) | Yes | No |
| Has `movement_budget` | No | Yes |
| Has `schema_version` | No | Yes |
| Conversion | `server_config.to_logging_config()` | — |

## Build-Time Type Generation

Run `python scripts/generate_ts_types.py --write` to regenerate `frontend/src/types/canonical.ts` from the Python dataclasses. The generated file should be committed to version control.

Regenerate after any change to dataclass fields in `microecon/logging/events.py`.
```

**Step 2: Commit**

```bash
mkdir -p docs/contracts
git add docs/contracts/schema-v1.md
git commit -m "docs(schema): add schema contract v1.0 specification (A-101)"
```

---

## Summary of All Files Changed

| File | Action |
|---|---|
| `microecon/logging/events.py` | Add `SCHEMA_VERSION`, `schema_version` field |
| `microecon/logging/formats.py` | Add `_validate_schema_version()` |
| `microecon/logging/__init__.py` | Export `SCHEMA_VERSION` |
| `server/routes.py` | Add `schema_version` to replay response |
| `server/simulation_manager.py` | Add `to_logging_config()` method |
| `scripts/generate_ts_types.py` | New: generation script |
| `frontend/src/types/canonical.ts` | New: generated canonical types |
| `frontend/src/types/simulation.ts` | Update doc comment with adapter mappings |
| `docs/contracts/schema-v1.md` | New: contract documentation |
| `tests/test_logging.py` | Add schema_version + validation tests |
| `tests/test_config_conversion.py` | New: server→logging conversion tests |
| `tests/test_ts_generation.py` | New: generation script tests |
| `tests/test_replay_loader.py` | Add schema_version in config test |
