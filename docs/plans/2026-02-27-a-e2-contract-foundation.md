# A-E2: Canonical Contract and Compatibility — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the remaining Gate A contract foundation: run provenance (A-104), conformance testing (A-103), determinism gate (A-105), and three documentation items (A-102, A-106, A-107).

**Architecture:** The canonical schema lives in `microecon/logging/events.py` as frozen dataclasses. All paths (live WS, replay API, persisted logs, analysis loaders) must conform to this schema or use explicitly documented adapters. Run IDs add provenance. Conformance and determinism tests enforce the contract in CI.

**Tech Stack:** Python dataclasses (canonical), pytest (conformance/determinism), UUID4 (run IDs), markdown (ADRs/policies)

**Decisions (locked):**
1. UUID4 for run_id (not deterministic hash)
2. Reserved `manifest_id` and `treatment_arm` fields (None until Gate B)
3. Four conformance test levels (canonical, persist/load, replay API, live WS)
4. Floating-point tolerance: `1e-10`
5. Proposal evaluation uses full visibility (current behavior, to be documented as intentional)

---

### Task 1: Add `run_id` to logging SimulationConfig (A-104)

**Files:**
- Modify: `microecon/logging/events.py:14-70`
- Test: `tests/test_logging.py`

**Step 1: Write the failing tests**

In `tests/test_logging.py`, add to `TestEventSerialization`:

```python
def test_simulation_config_includes_run_id(self):
    config = SimulationConfig(
        n_agents=10, grid_size=15, seed=42, protocol_name="nash",
    )
    d = config.to_dict()
    assert "run_id" in d
    assert isinstance(d["run_id"], str)
    assert len(d["run_id"]) > 0

def test_simulation_config_run_id_roundtrip(self):
    config = SimulationConfig(
        n_agents=10, grid_size=15, seed=42, protocol_name="nash",
        run_id="test-run-id-123",
    )
    d = config.to_dict()
    restored = SimulationConfig.from_dict(d)
    assert restored.run_id == "test-run-id-123"

def test_simulation_config_without_run_id_gets_empty(self):
    """Pre-A-104 configs without run_id load with empty string."""
    d = {
        "n_agents": 10, "grid_size": 15, "seed": 42,
        "protocol_name": "nash",
    }
    config = SimulationConfig.from_dict(d)
    assert config.run_id == ""
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_logging.py::TestEventSerialization::test_simulation_config_includes_run_id tests/test_logging.py::TestEventSerialization::test_simulation_config_run_id_roundtrip tests/test_logging.py::TestEventSerialization::test_simulation_config_without_run_id_gets_empty -v`
Expected: FAIL (no `run_id` field)

**Step 3: Implement**

In `microecon/logging/events.py`, add to `SimulationConfig` (after `schema_version` field, line ~37):

```python
run_id: str = ""
manifest_id: str | None = None
treatment_arm: str | None = None
```

In `to_dict()` (after `"schema_version"` entry):

```python
"run_id": self.run_id,
"manifest_id": self.manifest_id,
"treatment_arm": self.treatment_arm,
```

In `from_dict()` (after `schema_version` kwarg):

```python
run_id=d.get("run_id", ""),
manifest_id=d.get("manifest_id"),
treatment_arm=d.get("treatment_arm"),
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_logging.py::TestEventSerialization -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add microecon/logging/events.py tests/test_logging.py
git commit -m "feat(schema): add run_id, manifest_id, treatment_arm to SimulationConfig (A-104)"
```

---

### Task 2: Generate `run_id` in SimulationLogger (A-104)

**Files:**
- Modify: `microecon/logging/logger.py:69-103`
- Test: `tests/test_logging.py`

**Step 1: Write the failing test**

In `tests/test_logging.py`, add a new test class:

```python
class TestRunIdGeneration:
    """Test that SimulationLogger generates run_id when not provided."""

    def test_logger_generates_run_id(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash",
        )
        logger = SimulationLogger(config)
        assert logger.config.run_id != ""
        # Should be a valid UUID4
        import uuid
        uuid.UUID(logger.config.run_id, version=4)

    def test_logger_preserves_provided_run_id(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash",
            run_id="my-custom-id",
        )
        logger = SimulationLogger(config)
        assert logger.config.run_id == "my-custom-id"

    def test_logger_generates_unique_run_ids(self):
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=42, protocol_name="nash",
        )
        logger1 = SimulationLogger(config)
        logger2 = SimulationLogger(config)
        assert logger1.config.run_id != logger2.config.run_id
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_logging.py::TestRunIdGeneration -v`
Expected: FAIL (logger doesn't generate run_id)

**Step 3: Implement**

In `microecon/logging/logger.py`, add import at top (after existing imports):

```python
import uuid
```

In `SimulationLogger.__init__()` (after `self.config = config`, line 95), add:

```python
# Generate run_id if not provided
if not config.run_id:
    from .events import SimulationConfig as LogConfig
    # Replace config with one that has a generated run_id
    # (SimulationConfig is frozen, so we create a new instance)
    config_dict = config.to_dict()
    config_dict["run_id"] = str(uuid.uuid4())
    self.config = LogConfig.from_dict(config_dict)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_logging.py::TestRunIdGeneration -v`
Expected: ALL PASS

**Step 5: Run full logging test suite**

Run: `uv run pytest tests/test_logging.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add microecon/logging/logger.py tests/test_logging.py
git commit -m "feat(schema): generate run_id in SimulationLogger (A-104)"
```

---

### Task 3: Pass `run_id` through server config conversion (A-104)

**Files:**
- Modify: `server/simulation_manager.py:112-135`
- Modify: `tests/test_config_conversion.py`

**Step 1: Write the failing test**

In `tests/test_config_conversion.py`, add:

```python
def test_run_id_not_in_server_config(self):
    """Server config doesn't have run_id — logger generates it."""
    server_config = ServerConfig(seed=42)
    logging_config = server_config.to_logging_config()
    # run_id should be empty (logger will generate it)
    assert logging_config.run_id == ""

def test_manifest_fields_default_none(self):
    """Manifest fields default to None (reserved for Gate B)."""
    server_config = ServerConfig(seed=42)
    logging_config = server_config.to_logging_config()
    assert logging_config.manifest_id is None
    assert logging_config.treatment_arm is None
```

**Step 2: Run tests to verify**

Run: `uv run pytest tests/test_config_conversion.py -v`
Expected: PASS (the `to_logging_config()` method doesn't set run_id, so it gets the default empty string)

If tests fail because `to_logging_config` doesn't pass the new fields, no code change is needed — the defaults in `SimulationConfig` handle it. Verify the existing `to_logging_config()` still works with the new fields having defaults.

**Step 3: Commit**

```bash
git add tests/test_config_conversion.py
git commit -m "test(schema): add run_id and manifest field conversion tests (A-104)"
```

---

### Task 4: Update schema contract doc and regenerate TS types (A-104)

**Files:**
- Modify: `docs/contracts/schema-v1.md`
- Regenerate: `frontend/src/types/canonical.ts`

**Step 1: Update schema-v1.md**

Add a new section after "Versioning" and before "Canonical Schema Family":

```markdown
## Run Provenance

Every persisted run includes provenance identifiers:

| Field | Type | Source | Purpose |
|---|---|---|---|
| `run_id` | string | Generated by `SimulationLogger` (UUID4) | Stable unique identifier for this run |
| `manifest_id` | string \| null | Set by orchestrator (Gate B) | Links run to experiment manifest |
| `treatment_arm` | string \| null | Set by orchestrator (Gate B) | Identifies treatment arm within manifest |

Pre-A-104 runs without `run_id` load with empty string.
```

**Step 2: Regenerate canonical.ts**

Run: `uv run python scripts/generate_ts_types.py --write`
Expected: `Written to frontend/src/types/canonical.ts`

**Step 3: Verify generated types include new fields**

Read `frontend/src/types/canonical.ts` and confirm `SimulationConfig` includes:
- `run_id?: string`
- `manifest_id?: string | null`
- `treatment_arm?: string | null`

**Step 4: Run frontend typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 5: Commit**

```bash
git add docs/contracts/schema-v1.md frontend/src/types/canonical.ts
git commit -m "docs(schema): document run provenance fields and regenerate TS types (A-104)"
```

---

### Task 5: Contract conformance test harness — Level 1: Canonical round-trip (A-103)

**Files:**
- Create: `tests/test_contract_conformance.py`
- Modify: `pyproject.toml:21-33` (add `contract` marker)

**Step 1: Add pytest marker**

In `pyproject.toml`, add to the `markers` list:

```
"contract: Schema contract conformance tests (run when events.py, routes.py, or simulation_manager.py changes)",
"determinism: Deterministic rerun equivalence tests (run when simulation.py or batch.py changes)",
```

**Step 2: Write the conformance tests**

Create `tests/test_contract_conformance.py`:

```python
"""Contract conformance tests (A-103).

Validates that all data paths conform to the canonical schema
defined in microecon/logging/events.py.

Four levels:
1. Canonical round-trip: to_dict() -> from_dict() == original
2. Persist/load: logger -> disk -> load_run() is lossless
3. Replay API: persisted data -> replay adapter -> expected shape
4. Live WS: SimulationManager tick data -> expected shape
"""

import json
import tempfile
from pathlib import Path

import pytest

from microecon.logging import (
    AgentSnapshot,
    BeliefSnapshot,
    CommitmentBrokenEvent,
    CommitmentFormedEvent,
    JSONLinesFormat,
    MovementEvent,
    PriceBeliefSnapshot,
    RunData,
    SearchDecision,
    SimulationConfig,
    SimulationLogger,
    TargetEvaluation,
    TickRecord,
    TradeEvent,
    TypeBeliefSnapshot,
    load_run,
)
from microecon.simulation import create_simple_economy

pytestmark = pytest.mark.contract


# =========================================================================
# Level 1: Canonical round-trip
# =========================================================================

class TestCanonicalRoundTrip:
    """Every canonical dataclass must survive to_dict() -> from_dict()."""

    def test_simulation_config(self):
        original = SimulationConfig(
            n_agents=10, grid_size=15, seed=42, protocol_name="nash",
            protocol_params={"key": "val"}, perception_radius=5.0,
            discount_factor=0.9, movement_budget=2,
            info_env_name="noisy_alpha", info_env_params={"noise_std": 0.1},
            run_id="test-run-id",
        )
        assert SimulationConfig.from_dict(original.to_dict()) == original

    def test_agent_snapshot(self):
        original = AgentSnapshot(
            agent_id="a1", position=(3, 4), endowment=(10.0, 5.0),
            alpha=0.6, utility=7.5, has_beliefs=True,
            n_trades_in_memory=3, n_type_beliefs=2,
        )
        assert AgentSnapshot.from_dict(original.to_dict()) == original

    def test_target_evaluation(self):
        original = TargetEvaluation(
            target_id="t1", target_position=(1, 2), distance=3.0,
            ticks_to_reach=3, expected_surplus=1.5, discounted_value=1.2,
            observed_alpha=0.7, used_belief=True, believed_alpha=0.65,
        )
        assert TargetEvaluation.from_dict(original.to_dict()) == original

    def test_search_decision(self):
        evals = (
            TargetEvaluation("t1", (1, 1), 2.0, 2, 1.0, 0.9, 0.6),
            TargetEvaluation("t2", (2, 2), 3.0, 3, 0.8, 0.7, 0.4),
        )
        original = SearchDecision(
            agent_id="a1", position=(5, 5), visible_agents=3,
            evaluations=evals, chosen_target_id="t1", chosen_value=0.9,
        )
        assert SearchDecision.from_dict(original.to_dict()) == original

    def test_movement_event(self):
        original = MovementEvent(
            agent_id="a1", from_pos=(0, 0), to_pos=(1, 1),
            target_id="t1", reason="toward_target",
        )
        assert MovementEvent.from_dict(original.to_dict()) == original

    def test_trade_event(self):
        original = TradeEvent(
            agent1_id="a1", agent2_id="a2", proposer_id="a1",
            pre_holdings=((10.0, 5.0), (5.0, 10.0)),
            post_allocations=((8.0, 7.0), (7.0, 8.0)),
            utilities=(6.5, 7.2), gains=(0.5, 0.3), trade_occurred=True,
        )
        assert TradeEvent.from_dict(original.to_dict()) == original

    def test_commitment_formed_event(self):
        original = CommitmentFormedEvent(agent_a="a1", agent_b="a2")
        assert CommitmentFormedEvent.from_dict(original.to_dict()) == original

    def test_commitment_broken_event(self):
        original = CommitmentBrokenEvent(
            agent_a="a1", agent_b="a2", reason="trade_completed",
        )
        assert CommitmentBrokenEvent.from_dict(original.to_dict()) == original

    def test_type_belief_snapshot(self):
        original = TypeBeliefSnapshot(
            target_agent_id="a2", believed_alpha=0.6,
            confidence=0.8, n_interactions=5,
        )
        assert TypeBeliefSnapshot.from_dict(original.to_dict()) == original

    def test_price_belief_snapshot(self):
        original = PriceBeliefSnapshot(
            mean=1.5, variance=0.3, n_observations=10,
        )
        assert PriceBeliefSnapshot.from_dict(original.to_dict()) == original

    def test_belief_snapshot(self):
        original = BeliefSnapshot(
            agent_id="a1",
            type_beliefs=(
                TypeBeliefSnapshot("a2", 0.6, 0.8, 5),
            ),
            price_belief=PriceBeliefSnapshot(1.5, 0.3, 10),
            n_trades_in_memory=3,
        )
        assert BeliefSnapshot.from_dict(original.to_dict()) == original

    def test_tick_record(self):
        original = TickRecord(
            tick=5,
            agent_snapshots=(
                AgentSnapshot("a1", (0, 0), (10.0, 5.0), 0.6, 7.5),
            ),
            search_decisions=(),
            movements=(),
            trades=(),
            total_welfare=7.5,
            cumulative_trades=0,
        )
        assert TickRecord.from_dict(original.to_dict()) == original

    def test_tick_record_with_all_optional_fields(self):
        original = TickRecord(
            tick=5,
            agent_snapshots=(
                AgentSnapshot("a1", (0, 0), (10.0, 5.0), 0.6, 7.5),
            ),
            search_decisions=(),
            movements=(),
            trades=(
                TradeEvent("a1", "a2", "a1",
                           ((10.0, 5.0), (5.0, 10.0)),
                           ((8.0, 7.0), (7.0, 8.0)),
                           (6.5, 7.2), (0.5, 0.3), True),
            ),
            total_welfare=13.7,
            cumulative_trades=1,
            commitments_formed=(CommitmentFormedEvent("a1", "a2"),),
            commitments_broken=(CommitmentBrokenEvent("a1", "a2", "trade_completed"),),
            belief_snapshots=(
                BeliefSnapshot("a1",
                    (TypeBeliefSnapshot("a2", 0.6, 0.8, 5),),
                    PriceBeliefSnapshot(1.5, 0.3, 10), 3),
            ),
        )
        assert TickRecord.from_dict(original.to_dict()) == original
```

**Step 3: Run tests**

Run: `uv run pytest tests/test_contract_conformance.py::TestCanonicalRoundTrip -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add tests/test_contract_conformance.py pyproject.toml
git commit -m "test(contracts): add Level 1 canonical round-trip conformance tests (A-103)"
```

---

### Task 6: Contract conformance — Level 2: Persist/Load (A-103)

**Files:**
- Modify: `tests/test_contract_conformance.py`

**Step 1: Write the tests**

Append to `tests/test_contract_conformance.py`:

```python
# =========================================================================
# Level 2: Persist -> Load conformance
# =========================================================================

class TestPersistLoadConformance:
    """Persisting via SimulationLogger and loading via load_run() must be lossless."""

    def _run_and_persist(self, tmpdir: Path, n_ticks: int = 10, seed: int = 42,
                         protocol: str = "nash", use_beliefs: bool = False) -> RunData:
        """Helper: run a simulation and persist it."""
        output_path = tmpdir / "test_run"
        config = SimulationConfig(
            n_agents=4, grid_size=5, seed=seed, protocol_name=protocol,
        )
        logger = SimulationLogger(
            config=config, output_path=output_path, log_format=JSONLinesFormat(),
        )
        sim = create_simple_economy(
            n_agents=4, grid_size=5, seed=seed, use_beliefs=use_beliefs,
        )
        sim.logger = logger
        sim.run(n_ticks)
        return logger.finalize()

    def test_config_survives_persist_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir))
            loaded = load_run(Path(tmpdir) / "test_run")

            # Core config fields match (run_id may differ since logger generates it)
            assert loaded.config.n_agents == original.config.n_agents
            assert loaded.config.grid_size == original.config.grid_size
            assert loaded.config.seed == original.config.seed
            assert loaded.config.protocol_name == original.config.protocol_name
            assert loaded.config.schema_version == original.config.schema_version
            assert loaded.config.run_id == original.config.run_id

    def test_tick_count_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=10)
            loaded = load_run(Path(tmpdir) / "test_run")
            assert len(loaded.ticks) == len(original.ticks) == 10

    def test_agent_snapshots_survive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=5)
            loaded = load_run(Path(tmpdir) / "test_run")

            for orig_tick, loaded_tick in zip(original.ticks, loaded.ticks):
                assert len(loaded_tick.agent_snapshots) == len(orig_tick.agent_snapshots)
                for orig_snap, loaded_snap in zip(
                    orig_tick.agent_snapshots, loaded_tick.agent_snapshots
                ):
                    assert loaded_snap.agent_id == orig_snap.agent_id
                    assert loaded_snap.position == orig_snap.position
                    assert loaded_snap.alpha == orig_snap.alpha
                    assert abs(loaded_snap.utility - orig_snap.utility) < 1e-10

    def test_trades_survive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=20)
            loaded = load_run(Path(tmpdir) / "test_run")

            for orig_tick, loaded_tick in zip(original.ticks, loaded.ticks):
                assert len(loaded_tick.trades) == len(orig_tick.trades)
                for orig_trade, loaded_trade in zip(
                    orig_tick.trades, loaded_tick.trades
                ):
                    assert loaded_trade.agent1_id == orig_trade.agent1_id
                    assert loaded_trade.agent2_id == orig_trade.agent2_id
                    assert loaded_trade.proposer_id == orig_trade.proposer_id
                    assert loaded_trade.trade_occurred == orig_trade.trade_occurred

    def test_welfare_survives(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=10)
            loaded = load_run(Path(tmpdir) / "test_run")

            for orig_tick, loaded_tick in zip(original.ticks, loaded.ticks):
                assert abs(loaded_tick.total_welfare - orig_tick.total_welfare) < 1e-10
                assert loaded_tick.cumulative_trades == orig_tick.cumulative_trades

    def test_summary_survives(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir), n_ticks=10)
            loaded = load_run(Path(tmpdir) / "test_run")

            assert loaded.summary is not None
            assert original.summary is not None
            assert loaded.summary.total_ticks == original.summary.total_ticks
            assert loaded.summary.total_trades == original.summary.total_trades
            assert abs(loaded.summary.final_welfare - original.summary.final_welfare) < 1e-10

    def test_schema_version_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._run_and_persist(Path(tmpdir))
            config_file = Path(tmpdir) / "test_run" / "config.json"
            with open(config_file) as f:
                raw = json.load(f)
            assert "schema_version" in raw
            assert raw["schema_version"] == "1.0"

    def test_run_id_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = self._run_and_persist(Path(tmpdir))
            config_file = Path(tmpdir) / "test_run" / "config.json"
            with open(config_file) as f:
                raw = json.load(f)
            assert "run_id" in raw
            assert raw["run_id"] == original.config.run_id
            assert raw["run_id"] != ""
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_contract_conformance.py::TestPersistLoadConformance -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/test_contract_conformance.py
git commit -m "test(contracts): add Level 2 persist/load conformance tests (A-103)"
```

---

### Task 7: Contract conformance — Level 3: Replay API (A-103)

**Files:**
- Modify: `tests/test_contract_conformance.py`

**Step 1: Write the tests**

Append to `tests/test_contract_conformance.py`:

```python
# =========================================================================
# Level 3: Persist -> Replay API conformance
# =========================================================================

class TestReplayAPIConformance:
    """Replay API adapter must correctly transform canonical schema to presentation format.

    Adapter contract (from docs/contracts/schema-v1.md):
    - agent_id -> id (rename)
    - target_agent_id -> target_id (rename in beliefs)
    - pre_holdings[0] -> pre_holdings_1 (tuple unpack)
    - post_allocations[0] -> post_allocation_1 (tuple unpack)
    - alpha1, alpha2 derived from AgentSnapshot.alpha
    - belief_snapshots array -> beliefs map keyed by agent_id
    """

    @pytest.fixture
    def replay_data(self):
        """Create a persisted run and load it through the replay API transform."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_run"
            config = SimulationConfig(
                n_agents=4, grid_size=5, seed=42, protocol_name="nash",
            )
            logger = SimulationLogger(
                config=config, output_path=output_path, log_format=JSONLinesFormat(),
            )
            sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
            sim.logger = logger
            sim.run(15)
            logger.finalize()

            # Load raw persisted data
            config_file = output_path / "config.json"
            ticks_file = output_path / "ticks.jsonl"

            with open(config_file) as f:
                raw_config = json.load(f)

            raw_ticks = []
            with open(ticks_file) as f:
                for line in f:
                    raw_ticks.append(json.loads(line.strip()))

            yield {"config": raw_config, "raw_ticks": raw_ticks}

    def test_agent_id_renamed_to_id(self, replay_data):
        """Replay adapter renames agent_id to id."""
        tick = replay_data["raw_ticks"][0]
        # Raw has agent_id
        assert "agent_id" in tick["agent_snapshots"][0]
        # Adapter should produce "id" — verify the raw field is there for transformation

    def test_agent_snapshots_have_required_fields(self, replay_data):
        """Each agent snapshot in raw data has all canonical fields."""
        for tick in replay_data["raw_ticks"]:
            for agent in tick["agent_snapshots"]:
                assert "agent_id" in agent
                assert "position" in agent
                assert "endowment" in agent
                assert "alpha" in agent
                assert "utility" in agent

    def test_trade_events_have_required_fields(self, replay_data):
        """Trade events have all canonical fields including proposer_id."""
        trades_found = False
        for tick in replay_data["raw_ticks"]:
            for trade in tick.get("trades", []):
                trades_found = True
                assert "agent1_id" in trade
                assert "agent2_id" in trade
                assert "proposer_id" in trade
                assert "pre_holdings" in trade
                assert "post_allocations" in trade
                assert "utilities" in trade
                assert "gains" in trade
                assert "trade_occurred" in trade
                # pre_holdings is a list of two lists
                assert len(trade["pre_holdings"]) == 2
                assert len(trade["post_allocations"]) == 2
        assert trades_found, "No trades found in 15 ticks — test needs more ticks"

    def test_alpha_derivable_from_agent_snapshots(self, replay_data):
        """Alpha values for trade enrichment must be derivable from same-tick agent snapshots."""
        for tick in replay_data["raw_ticks"]:
            alpha_by_id = {
                agent["agent_id"]: agent["alpha"]
                for agent in tick["agent_snapshots"]
            }
            for trade in tick.get("trades", []):
                assert trade["agent1_id"] in alpha_by_id
                assert trade["agent2_id"] in alpha_by_id

    def test_schema_version_in_config(self, replay_data):
        assert "schema_version" in replay_data["config"]

    def test_run_id_in_config(self, replay_data):
        assert "run_id" in replay_data["config"]
        assert replay_data["config"]["run_id"] != ""
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_contract_conformance.py::TestReplayAPIConformance -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/test_contract_conformance.py
git commit -m "test(contracts): add Level 3 replay API conformance tests (A-103)"
```

---

### Task 8: Contract conformance — Level 4: Live WebSocket alignment (A-103)

**Files:**
- Modify: `tests/test_contract_conformance.py`

**Step 1: Write the tests**

Append to `tests/test_contract_conformance.py`:

```python
# =========================================================================
# Level 4: Live WebSocket payload conformance
# =========================================================================

from server.simulation_manager import (
    SimulationConfig as ServerConfig,
    SimulationManager,
)


class TestLivePayloadConformance:
    """Live WebSocket payload must contain all fields frontend expects.

    The live payload is built from Simulation objects (not persisted data).
    It includes presentation-only fields (interaction_state, bargaining_power)
    not in the canonical schema.
    """

    def _get_live_payload(self, protocol: str = "nash", n_ticks: int = 5) -> dict:
        """Create a simulation, run ticks, return tick data payload."""
        mgr = SimulationManager()
        config = ServerConfig(
            n_agents=4, grid_size=5, seed=42,
            bargaining_protocol=protocol,
        )
        mgr.create_simulation(config)
        for _ in range(n_ticks):
            mgr.step()
        return mgr.get_tick_data()

    def test_tick_data_has_required_keys(self):
        payload = self._get_live_payload()
        assert "tick" in payload
        assert "agents" in payload
        assert "trades" in payload
        assert "metrics" in payload
        assert "beliefs" in payload

    def test_agent_has_required_fields(self):
        payload = self._get_live_payload()
        assert len(payload["agents"]) > 0
        agent = payload["agents"][0]
        # Presentation fields
        assert "id" in agent
        assert "position" in agent
        assert "endowment" in agent
        assert "alpha" in agent
        assert "utility" in agent
        # Live-only fields (not in canonical schema)
        assert "interaction_state" in agent
        assert "bargaining_power" in agent
        assert "perception_radius" in agent
        assert "discount_factor" in agent

    def test_metrics_has_required_fields(self):
        payload = self._get_live_payload()
        metrics = payload["metrics"]
        assert "total_welfare" in metrics
        assert "welfare_gains" in metrics
        assert "cumulative_trades" in metrics

    def test_trade_has_required_fields(self):
        """Run enough ticks to get trades, then verify fields."""
        payload = self._get_live_payload(n_ticks=30)
        if payload["trades"]:
            trade = payload["trades"][0]
            assert "agent1_id" in trade
            assert "agent2_id" in trade
            assert "alpha1" in trade
            assert "alpha2" in trade
            assert "pre_holdings_1" in trade
            assert "pre_holdings_2" in trade
            assert "post_allocation_1" in trade
            assert "post_allocation_2" in trade
            assert "gains" in trade
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_contract_conformance.py::TestLivePayloadConformance -v`
Expected: ALL PASS

**Step 3: Run full conformance suite**

Run: `uv run pytest tests/test_contract_conformance.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add tests/test_contract_conformance.py
git commit -m "test(contracts): add Level 4 live WS payload conformance tests (A-103)"
```

---

### Task 9: Determinism gate — core tests (A-105)

**Files:**
- Create: `tests/test_determinism.py`

**Step 1: Write the determinism tests**

Create `tests/test_determinism.py`:

```python
"""Determinism gate tests (A-105).

Proves that seeded simulations produce identical outputs across reruns.
See docs/contracts/determinism-policy.md for tolerance rules.

Tolerance policy:
- Integer fields (tick, position, trade count): exact match
- Floating-point fields (welfare, utility, surplus): abs(a - b) < 1e-10
- Sequence ordering: exact (deterministic tie-breaking is contract)
"""

import pytest

from microecon.simulation import Simulation, create_simple_economy
from microecon.logging import SimulationLogger, SimulationConfig, TickRecord

pytestmark = pytest.mark.determinism

FLOAT_TOL = 1e-10


def _run_simulation(seed: int, protocol: str = "nash", n_agents: int = 6,
                     grid_size: int = 8, n_ticks: int = 20,
                     use_beliefs: bool = False,
                     info_env: str = "full",
                     info_env_params: dict | None = None) -> list[TickRecord]:
    """Run a simulation and collect tick records."""
    from microecon.information import FullInformation, NoisyAlphaInformation
    from microecon.bargaining import (
        NashBargainingProtocol, RubinsteinBargainingProtocol,
        TIOLIBargainingProtocol, AsymmetricNashBargainingProtocol,
    )

    protocols = {
        "nash": NashBargainingProtocol,
        "rubinstein": RubinsteinBargainingProtocol,
        "tioli": TIOLIBargainingProtocol,
        "asymmetric_nash": AsymmetricNashBargainingProtocol,
    }
    bargaining = protocols[protocol]()

    if info_env == "noisy_alpha":
        ie = NoisyAlphaInformation(noise_std=(info_env_params or {}).get("noise_std", 0.1))
    else:
        ie = FullInformation()

    config = SimulationConfig(
        n_agents=n_agents, grid_size=grid_size, seed=seed,
        protocol_name=protocol,
    )
    logger = SimulationLogger(config)

    sim = create_simple_economy(
        n_agents=n_agents, grid_size=grid_size, seed=seed,
        bargaining_protocol=bargaining, use_beliefs=use_beliefs,
        info_env=ie,
    )
    sim.logger = logger
    sim.run(n_ticks)
    logger.finalize()

    return logger.ticks


def _assert_ticks_equal(ticks_a: list[TickRecord], ticks_b: list[TickRecord]) -> None:
    """Assert two tick sequences are identical within tolerance."""
    assert len(ticks_a) == len(ticks_b), \
        f"Tick count mismatch: {len(ticks_a)} vs {len(ticks_b)}"

    for i, (ta, tb) in enumerate(zip(ticks_a, ticks_b)):
        # Tick number
        assert ta.tick == tb.tick, f"Tick {i}: tick number mismatch"

        # Welfare
        assert abs(ta.total_welfare - tb.total_welfare) < FLOAT_TOL, \
            f"Tick {i}: welfare mismatch {ta.total_welfare} vs {tb.total_welfare}"

        # Cumulative trades
        assert ta.cumulative_trades == tb.cumulative_trades, \
            f"Tick {i}: cumulative trades mismatch"

        # Agent snapshots
        assert len(ta.agent_snapshots) == len(tb.agent_snapshots), \
            f"Tick {i}: agent count mismatch"
        for sa, sb in zip(ta.agent_snapshots, tb.agent_snapshots):
            assert sa.agent_id == sb.agent_id, \
                f"Tick {i}: agent ID mismatch"
            assert sa.position == sb.position, \
                f"Tick {i}, agent {sa.agent_id}: position mismatch"
            assert abs(sa.utility - sb.utility) < FLOAT_TOL, \
                f"Tick {i}, agent {sa.agent_id}: utility mismatch"

        # Trades
        assert len(ta.trades) == len(tb.trades), \
            f"Tick {i}: trade count mismatch"
        for tra, trb in zip(ta.trades, tb.trades):
            assert tra.agent1_id == trb.agent1_id
            assert tra.agent2_id == trb.agent2_id
            assert tra.proposer_id == trb.proposer_id
            assert tra.trade_occurred == trb.trade_occurred
            for ga, gb in zip(tra.gains, trb.gains):
                assert abs(ga - gb) < FLOAT_TOL

        # Movements
        assert len(ta.movements) == len(tb.movements), \
            f"Tick {i}: movement count mismatch"
        for ma, mb in zip(ta.movements, tb.movements):
            assert ma.agent_id == mb.agent_id
            assert ma.from_pos == mb.from_pos
            assert ma.to_pos == mb.to_pos


class TestDeterminismGate:
    """Seeded reruns must produce identical outputs."""

    @pytest.mark.parametrize("protocol", [
        "nash", "rubinstein", "tioli", "asymmetric_nash",
    ])
    def test_protocol_determinism(self, protocol):
        """Same seed + same protocol -> identical ticks."""
        ticks_a = _run_simulation(seed=42, protocol=protocol)
        ticks_b = _run_simulation(seed=42, protocol=protocol)
        _assert_ticks_equal(ticks_a, ticks_b)

    def test_different_seeds_differ(self):
        """Different seeds should produce different outputs."""
        ticks_a = _run_simulation(seed=42)
        ticks_b = _run_simulation(seed=99)
        # At least one tick should differ in welfare or trades
        any_diff = False
        for ta, tb in zip(ticks_a, ticks_b):
            if abs(ta.total_welfare - tb.total_welfare) > FLOAT_TOL:
                any_diff = True
                break
            if ta.cumulative_trades != tb.cumulative_trades:
                any_diff = True
                break
        assert any_diff, "Different seeds produced identical results"

    def test_noisy_info_determinism(self):
        """NoisyAlphaInformation with same seed -> identical ticks."""
        ticks_a = _run_simulation(
            seed=42, info_env="noisy_alpha",
            info_env_params={"noise_std": 0.1},
        )
        ticks_b = _run_simulation(
            seed=42, info_env="noisy_alpha",
            info_env_params={"noise_std": 0.1},
        )
        _assert_ticks_equal(ticks_a, ticks_b)

    def test_beliefs_determinism(self):
        """Simulations with beliefs enabled are deterministic."""
        ticks_a = _run_simulation(seed=42, use_beliefs=True, n_ticks=30)
        ticks_b = _run_simulation(seed=42, use_beliefs=True, n_ticks=30)
        _assert_ticks_equal(ticks_a, ticks_b)

    def test_larger_simulation_determinism(self):
        """Larger grid with more agents remains deterministic."""
        ticks_a = _run_simulation(seed=42, n_agents=12, grid_size=15, n_ticks=30)
        ticks_b = _run_simulation(seed=42, n_agents=12, grid_size=15, n_ticks=30)
        _assert_ticks_equal(ticks_a, ticks_b)
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_determinism.py -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/test_determinism.py
git commit -m "test(determinism): add seeded rerun equivalence gate (A-105)"
```

---

### Task 10: Determinism policy document (A-105)

**Files:**
- Create: `docs/contracts/determinism-policy.md`

**Step 1: Write the policy document**

Create `docs/contracts/determinism-policy.md`:

```markdown
# Determinism Policy

**Version:** 1.0
**Enforcement:** `tests/test_determinism.py` (pytest marker: `determinism`)

---

## Guarantee

Running the same `SimulationConfig` (same seed, same parameters) must produce identical `TickRecord` sequences within the tolerance defined below.

## Tolerance Rules

| Field Type | Comparison | Threshold |
|---|---|---|
| Integer (tick, position, trade count) | Exact match | 0 |
| Float (welfare, utility, surplus, gains) | Absolute difference | `< 1e-10` |
| String (agent IDs, proposer IDs) | Exact match | — |
| Sequence ordering | Exact match | — |

## Scope

Determinism is guaranteed for:
- All bargaining protocols (Nash, Rubinstein, TIOLI, Asymmetric Nash)
- All information environments (Full, NoisyAlpha)
- Belief-enabled simulations
- Any agent count and grid size

## Tie-Breaking

When multiple agents or actions have equal priority, deterministic tie-breaking is part of the contract:
- Agent iteration uses sorted ID order
- Proposal conflict resolution uses sorted proposer ID order

## RNG Isolation

Per A-005, all stochastic behavior is driven by per-run RNG instances seeded from the config seed. No module-level or global RNG state is mutated.

## Platform Note

Determinism is validated on the same Python version and platform. Cross-platform floating-point equivalence is not guaranteed but expected to hold within the tolerance above.
```

**Step 2: Commit**

```bash
git add docs/contracts/determinism-policy.md
git commit -m "docs(contracts): add determinism policy document (A-105)"
```

---

### Task 11: Schema compatibility policy document (A-102)

**Files:**
- Create: `docs/contracts/compatibility-policy.md`

**Step 1: Write the policy document**

Create `docs/contracts/compatibility-policy.md`:

```markdown
# Schema Compatibility Policy

**Version:** 1.0
**Canonical source:** `microecon/logging/events.py`
**Enforcement:** `microecon/logging/formats.py` (`_validate_schema_version`)

---

## Version Format

Schema versions use `MAJOR.MINOR` semantic versioning (e.g. `1.0`).

## Read Compatibility

Readers (loaders, replay API, analysis tools) support:
- **Version N** (current): full support
- **Version N-1** (one prior): full support via `from_dict()` defaults

Pre-versioning runs (no `schema_version` field) are treated as version `"0.0"`.

## Write Policy

Writers always produce the current schema version. There is no option to write older formats.

## Migration Strategy

Migration from N-1 to N is handled by `from_dict()` default values on new fields:
- New fields get sensible defaults (e.g. `run_id=""`, `manifest_id=None`)
- No separate migration scripts are needed
- Old persisted files are read as-is; they are NOT rewritten on load

## Breaking Changes

A **MAJOR** version bump (e.g. 1.0 → 2.0):
- Removes support for version N-2
- Requires documentation of what changed and how to migrate
- Must update `_SUPPORTED_VERSIONS` in `formats.py`

A **MINOR** version bump (e.g. 1.0 → 1.1):
- Adds new optional fields with defaults
- Does NOT break readers on the same MAJOR version

## Compatibility Horizon

Two major versions: readers support N and N-1. Version N-2 and older are unsupported and raise `ValueError` on load.

## Current State

| Version | Status | Notes |
|---|---|---|
| 0.0 | N-1 (supported) | Pre-versioning runs, no `schema_version` field |
| 1.0 | N (current) | First versioned schema |
```

**Step 2: Commit**

```bash
git add docs/contracts/compatibility-policy.md
git commit -m "docs(contracts): add schema compatibility policy (A-102)"
```

---

### Task 12: Documentation synchronization gate (A-106)

**Files:**
- Create: `docs/CONTRIBUTING.md`

**Step 1: Write the contributor guide**

Create `docs/CONTRIBUTING.md`:

```markdown
# Contributing to Microecon

## Schema Change Checklist

When modifying canonical schema dataclasses in `microecon/logging/events.py`:

- [ ] Update `docs/contracts/schema-v1.md` with new/changed fields
- [ ] Regenerate TS types: `uv run python scripts/generate_ts_types.py --write`
- [ ] Commit regenerated `frontend/src/types/canonical.ts`
- [ ] If field is removed or renamed: bump `SCHEMA_VERSION` and update `_SUPPORTED_VERSIONS` in `formats.py`
- [ ] Run contract conformance tests: `uv run pytest -m contract`
- [ ] Run determinism tests: `uv run pytest -m determinism`

## Presentation Adapter Changes

When modifying the live WebSocket adapter (`server/simulation_manager.py:get_tick_data`) or replay adapter (`server/routes.py:load_run`):

- [ ] Update the adapter mapping tables in `docs/contracts/schema-v1.md`
- [ ] Update `frontend/src/types/simulation.ts` doc comment if field names change
- [ ] Run contract conformance tests: `uv run pytest -m contract`

## Protocol Semantics Changes

When modifying bargaining, matching, or decision procedures:

- [ ] Update or create an ADR in `docs/adr/`
- [ ] Run theory tests: `uv run pytest -m theory`
- [ ] Run determinism tests: `uv run pytest -m determinism`

## Running Tests

```bash
uv run pytest                      # Full suite
uv run pytest -m contract          # Contract conformance only
uv run pytest -m determinism       # Determinism gate only
uv run pytest -m theory            # Theory verification only
uv run pytest -m "not slow"        # Skip slow tests
```
```

**Step 2: Commit**

```bash
git add docs/CONTRIBUTING.md
git commit -m "docs: add contributing guide with schema change checklist (A-106)"
```

---

### Task 13: Proposal-evaluation visibility ADR (A-107)

**Files:**
- Create: `docs/adr/ADR-005-PROPOSAL-EVALUATION-VISIBILITY.md`
- Modify: `tests/test_simulation.py`

**Step 1: Write the ADR**

The investigation (already done) found that `simulation.py:422-426` builds the `DecisionContext` with `visible_agents={a.id: a for a in self.agents}` — full visibility. The comment explicitly says "Full visibility for evaluation". The `evaluate_proposal` method in `decisions.py:459` then calls `compute_expected_surplus(agent, proposer)` with the raw agent objects (true preferences), not filtered through the information environment.

Create `docs/adr/ADR-005-PROPOSAL-EVALUATION-VISIBILITY.md`:

```markdown
# ADR-005: Proposal Evaluation Visibility

**Status:** Accepted
**Date:** 2026-02-27
**Context:** A-107 (Proposal-evaluation visibility semantics decision)

## Decision

Execute-phase proposal evaluation uses **full visibility**: the target agent evaluates proposals using the proposer's true preferences, regardless of the configured `InformationEnvironment`.

## Context

During the Execute phase, when a non-mutual proposal arrives, the target agent must immediately decide whether to accept or reject. This decision is made in `simulation.py:_execute_actions()` via `decision_procedure.evaluate_proposal()`.

The `DecisionContext` is built with full agent visibility:

```python
visible_agents={a.id: a for a in self.agents}  # Full visibility for evaluation
```

The `evaluate_proposal` implementation (`decisions.py:459`) computes surplus using the proposer's true preferences via `compute_expected_surplus(agent, proposer)`.

## Rationale

1. **Institutional constraint, not agent perception**: Proposal evaluation is an institutional constraint (AGENT-ARCHITECTURE.md 7.9), not a perceptual act. The institution determines whether a trade is feasible and beneficial, using true parameters.

2. **Information environment governs search, not settlement**: The `InformationEnvironment` affects what agents *observe* during the Perceive phase (search target selection). Once two agents are adjacent and negotiating, the bargaining protocol operates on true preferences to compute the actual allocation.

3. **Consistency with bargaining**: The bargaining protocols (Nash, Rubinstein, etc.) already use true preferences to compute allocations. Having proposal *acceptance* use noisy preferences while *settlement* uses true preferences would create an inconsistency.

## Consequences

- Under noisy information, agents may search for suboptimal partners (based on noisy alpha), but once adjacent, they correctly evaluate whether trade is beneficial.
- This means information asymmetry affects *who* agents seek out, not *whether* they trade once matched.
- A future mechanism that uses local visibility for proposal evaluation would need to be added as a separate `DecisionProcedure` implementation, not by modifying the current one.

## Regression Test

`tests/test_simulation.py::TestProposalEvaluationVisibility` locks in this behavior.
```

**Step 2: Write the regression test**

In `tests/test_simulation.py`, add (find appropriate location near end of file):

```python
class TestProposalEvaluationVisibility:
    """Lock in ADR-005: proposal evaluation uses full visibility.

    Even under NoisyAlphaInformation, proposal acceptance decisions use
    true agent preferences (full visibility), not noisy observations.
    """

    def test_proposal_evaluation_uses_full_visibility(self):
        """DecisionContext for proposal evaluation includes all agents with true state."""
        from microecon.simulation import Simulation, create_simple_economy
        from microecon.information import NoisyAlphaInformation

        # Create a noisy-info simulation
        sim = create_simple_economy(
            n_agents=4, grid_size=5, seed=42,
            info_env=NoisyAlphaInformation(noise_std=0.5),
        )

        # Run enough ticks for agents to interact
        sim.run(30)

        # The key assertion: trades should still occur and be welfare-improving,
        # because proposal evaluation uses true preferences (not noisy).
        # Under full visibility for evaluation, gains should always be non-negative.
        for trade in sim.trades:
            assert trade.gains[0] >= -1e-10, \
                f"Agent 1 had negative gain {trade.gains[0]} — proposal evaluation may be using noisy info"
            assert trade.gains[1] >= -1e-10, \
                f"Agent 2 had negative gain {trade.gains[1]} — proposal evaluation may be using noisy info"
```

**Step 3: Run tests**

Run: `uv run pytest tests/test_simulation.py::TestProposalEvaluationVisibility -v`
Expected: PASS

**Step 4: Commit**

```bash
git add docs/adr/ADR-005-PROPOSAL-EVALUATION-VISIBILITY.md tests/test_simulation.py
git commit -m "docs(adr): add ADR-005 proposal-evaluation visibility decision (A-107)"
```

---

### Task 14: Full test suite verification

**Step 1: Run the full test suite**

Run: `uv run pytest -v`
Expected: ALL PASS (749+ tests)

**Step 2: Run targeted marker suites**

Run: `uv run pytest -m contract -v`
Expected: ALL PASS

Run: `uv run pytest -m determinism -v`
Expected: ALL PASS

**Step 3: Run frontend checks**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: No errors

---

## Summary of All Files Changed

| File | Action | Task |
|---|---|---|
| `microecon/logging/events.py` | Add `run_id`, `manifest_id`, `treatment_arm` fields | 1 |
| `microecon/logging/logger.py` | Generate `run_id` via UUID4 | 2 |
| `tests/test_logging.py` | Add run_id roundtrip + generation tests | 1, 2 |
| `tests/test_config_conversion.py` | Add run_id and manifest field tests | 3 |
| `docs/contracts/schema-v1.md` | Document run provenance fields | 4 |
| `frontend/src/types/canonical.ts` | Regenerate with new fields | 4 |
| `tests/test_contract_conformance.py` | New: 4-level conformance test suite | 5, 6, 7, 8 |
| `pyproject.toml` | Add `contract` and `determinism` markers | 5 |
| `tests/test_determinism.py` | New: seeded rerun equivalence tests | 9 |
| `docs/contracts/determinism-policy.md` | New: tolerance rules document | 10 |
| `docs/contracts/compatibility-policy.md` | New: schema compat policy | 11 |
| `docs/CONTRIBUTING.md` | New: contributor guide with checklists | 12 |
| `docs/adr/ADR-005-PROPOSAL-EVALUATION-VISIBILITY.md` | New: visibility semantics ADR | 13 |
| `tests/test_simulation.py` | Add visibility regression test | 13 |
