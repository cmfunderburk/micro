# P0 Stabilization Sprint Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all P0 correctness bugs and quality gaps (A-001 through A-007) to unblock Gate A Foundation Coherence.

**Architecture:** Bottom-up, dependency-ordered fixes starting from the data model (TradeEvent unification), then runtime correctness (RNG, info_env), then data pipeline (replay loader), then product surface (info regime UI), then quality baseline (lint).

**Tech Stack:** Python 3.12, FastAPI, React/TypeScript, Zustand, pytest, ESLint

---

### Task 1: A-005 — Remove Global RNG Mutation from Batch Runner

**Files:**
- Modify: `microecon/batch.py:131-133`
- Test: `tests/test_batch.py` (new test)

**Step 1: Write the failing test**

In `tests/test_batch.py`, find existing batch tests and add:

```python
def test_batch_run_does_not_mutate_global_rng():
    """A-005: Batch runs must not mutate global random state."""
    import random

    state_before = random.getstate()

    runner = BatchRunner(
        base_config={"n_agents": 4, "grid_size": 5, "seed": 42},
    )
    runner.run(ticks=5)

    state_after = random.getstate()
    assert state_before == state_after, "BatchRunner mutated global random state"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_batch.py::test_batch_run_does_not_mutate_global_rng -v`
Expected: FAIL — `random.seed(seed)` at batch.py:133 changes global state.

**Step 3: Delete the global RNG mutation**

In `microecon/batch.py`, remove lines 131-133:

```python
        # Create simulation using factory function but inject logger
        if seed is not None:
            random.seed(seed)
```

Replace with:

```python
        # Create simulation using factory function but inject logger
```

Also remove `import random` from the top of the file (line 12) if nothing else uses it.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_batch.py -v`
Expected: All batch tests pass including the new one.

**Step 5: Run full test suite**

Run: `uv run pytest -q`
Expected: 716+ passed, 15 skipped. No regressions.

**Step 6: Commit**

```
fix(batch): remove global RNG mutation from batch runner (A-005)

BatchRunner called random.seed() which leaked global state between
runs. create_simple_economy already creates per-instance Random(seed).
```

---

### Task 2: A-003 + A-006 — Unify TradeEvent and Fix Proposer ID

**Files:**
- Modify: `microecon/simulation.py:51-59` (delete runtime TradeEvent)
- Modify: `microecon/simulation.py:562-635` (_execute_trade, _build_trade_events_data)
- Modify: `microecon/simulation.py:637-726` (_log_tick trade section)
- Modify: `microecon/simulation.py:811-816` (welfare_gains)
- Modify: `microecon/simulation.py:781` (run method type hint)
- Modify: `microecon/simulation.py:97-103` (Simulation.trades type)
- Test: `tests/test_simulation.py` (new test)

This is the largest task. It has several sub-steps.

**Step 1: Write the failing test for proposer provenance**

Add to `tests/test_simulation.py`:

```python
def test_trade_event_has_correct_proposer_id():
    """A-003: Logged proposer_id must match actual proposer from bargaining protocol."""
    from microecon.simulation import Simulation, create_simple_economy
    from microecon.logging.events import TradeEvent

    sim = create_simple_economy(n_agents=4, grid_size=3, seed=42)
    sim.run(50)

    # After running, sim.trades should contain TradeEvent objects with proposer_id
    assert len(sim.trades) > 0, "Expected at least one trade to occur"
    for trade in sim.trades:
        assert isinstance(trade, TradeEvent), f"Expected logging TradeEvent, got {type(trade)}"
        assert trade.proposer_id in (trade.agent1_id, trade.agent2_id), (
            f"proposer_id '{trade.proposer_id}' not one of the trading agents"
        )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_simulation.py::test_trade_event_has_correct_proposer_id -v`
Expected: FAIL — current runtime TradeEvent has no `proposer_id` field.

**Step 3: Delete runtime TradeEvent and import canonical one**

In `microecon/simulation.py`, delete the runtime TradeEvent (lines 51-59):

```python
@dataclass
class TradeEvent:
    """Record of a trade that occurred."""
    tick: int
    agent1_id: str
    agent2_id: str
    outcome: BargainingOutcome
    pre_holdings_1: tuple[float, float]  # Agent 1's holdings before trade
    pre_holdings_2: tuple[float, float]  # Agent 2's holdings before trade
```

Add import at the top of the file (in the imports section, around line 21):

```python
from microecon.logging.events import TradeEvent
```

**Step 4: Update `_execute_trade` to build canonical TradeEvent**

Replace the event construction in `_execute_trade` (lines 581-589):

Old:
```python
        if outcome.trade_occurred:
            event = TradeEvent(
                tick=self.tick,
                agent1_id=agent1.id,
                agent2_id=agent2.id,
                outcome=outcome,
                pre_holdings_1=pre_holdings1,
                pre_holdings_2=pre_holdings2,
            )
```

New:
```python
        if outcome.trade_occurred:
            event = TradeEvent(
                agent1_id=agent1.id,
                agent2_id=agent2.id,
                proposer_id=proposer.id,
                pre_holdings=(pre_holdings1, pre_holdings2),
                post_allocations=(
                    (outcome.allocation_1.x, outcome.allocation_1.y),
                    (outcome.allocation_2.x, outcome.allocation_2.y),
                ),
                utilities=(outcome.utility_1, outcome.utility_2),
                gains=(outcome.gains_1, outcome.gains_2),
                trade_occurred=outcome.trade_occurred,
            )
```

Note: Keep the `outcome` local variable — it's still used for belief updates below.

**Step 5: Delete `_build_trade_events_data` entirely**

Delete the entire method (lines 617-635):

```python
    def _build_trade_events_data(
        self,
        tick_trades: list[TradeEvent],
    ) -> list[tuple]:
        """Build trade events data for logging."""
        trade_events_data = []
        for event in tick_trades:
            trade_events_data.append((
                event.agent1_id,
                event.agent2_id,
                event.agent1_id,  # proposer_id (simplified)
                (event.pre_holdings_1, event.pre_holdings_2),
                ((event.outcome.allocation_1.x, event.outcome.allocation_1.y),
                 (event.outcome.allocation_2.x, event.outcome.allocation_2.y)),
                (event.outcome.utility_1, event.outcome.utility_2),
                (event.outcome.gains_1, event.outcome.gains_2),
                event.outcome.trade_occurred,
            ))
        return trade_events_data
```

**Step 6: Update `_log_tick` to accept TradeEvent objects directly**

Change the `_log_tick` signature — replace the `trade_events_data: list` parameter with `trade_events: list[TradeEvent]`:

Old signature:
```python
    def _log_tick(
        self,
        search_decisions_data: list,
        movement_events_data: list,
        trade_events_data: list,
        commitments_formed_data: list[tuple[str, str]],
        commitments_broken_data: list[tuple[str, str, str]],
    ) -> None:
```

New signature:
```python
    def _log_tick(
        self,
        search_decisions_data: list,
        movement_events_data: list,
        trade_events: list[TradeEvent],
        commitments_formed_data: list[tuple[str, str]],
        commitments_broken_data: list[tuple[str, str, str]],
    ) -> None:
```

Replace the trade event creation block inside `_log_tick` (the section that unpacks tuples into `create_trade_event` calls):

Old:
```python
        # Create trade events
        trades = [
            create_trade_event(
                agent1_id=a1,
                agent2_id=a2,
                proposer_id=proposer,
                pre_holdings=pre,
                post_allocations=post,
                utilities=utils,
                gains=gains,
                trade_occurred=occurred,
            )
            for a1, a2, proposer, pre, post, utils, gains, occurred in trade_events_data
        ]
```

New:
```python
        # Trade events are already canonical TradeEvent objects
        trades = trade_events
```

Also remove the `create_trade_event` import from the local imports inside `_log_tick` (line 654).

**Step 7: Update the call site in `step()`**

In the `step()` method (around line 273-282), replace:

Old:
```python
        if self.logger is not None:
            trade_events_data = self._build_trade_events_data(tick_trades)
            self._log_tick(
                search_decisions_data,
                movement_events_data,
                trade_events_data,
                [],  # No commitment events in new model
                [],  # No commitment events in new model
            )
```

New:
```python
        if self.logger is not None:
            self._log_tick(
                search_decisions_data,
                movement_events_data,
                tick_trades,
                [],  # No commitment events in new model
                [],  # No commitment events in new model
            )
```

**Step 8: Update `welfare_gains` to use canonical field names**

Old (lines 811-816):
```python
    def welfare_gains(self) -> float:
        """Compute total gains from trade (sum of all trade surpluses)."""
        return sum(
            trade.outcome.gains_1 + trade.outcome.gains_2
            for trade in self.trades
        )
```

New:
```python
    def welfare_gains(self) -> float:
        """Compute total gains from trade (sum of all trade surpluses)."""
        return sum(
            trade.gains[0] + trade.gains[1]
            for trade in self.trades
        )
```

**Step 9: Remove unused imports**

`BargainingOutcome` is no longer needed in the `TradeEvent` dataclass (it was the `outcome` field type). Check if it's still used elsewhere in `simulation.py`. It IS still used in `_execute_trade` as a local variable type, so keep the import.

**Step 10: Run the new test**

Run: `uv run pytest tests/test_simulation.py::test_trade_event_has_correct_proposer_id -v`
Expected: PASS

**Step 11: Run the full test suite**

Run: `uv run pytest -q`
Expected: 716+ passed. If any tests fail, they'll be tests that constructed the old runtime TradeEvent — update those to use the canonical one.

**Step 12: Commit**

```
fix(simulation): unify TradeEvent and fix proposer ID provenance (A-003, A-006)

Replace dual TradeEvent models (runtime + logging) with single canonical
model from microecon.logging.events. Proposer ID now captured from
actual bargaining protocol selection instead of hardcoded to agent1.
Eliminates the ad-hoc tuple transform in _build_trade_events_data.
```

---

### Task 3: A-002 — Fix Batch info_env Execution

**Files:**
- Modify: `microecon/simulation.py:819-861` (create_simple_economy signature)
- Modify: `microecon/batch.py:119-142` (_create_simulation)
- Test: `tests/test_batch.py` (new test)

**Step 1: Write the failing test**

Add to `tests/test_batch.py`:

```python
def test_batch_runner_honors_info_env():
    """A-002: BatchRunner must pass configured info_env to simulation."""
    from microecon.information import NoisyAlphaInformation

    info_env = NoisyAlphaInformation(noise_std=0.2)
    runner = BatchRunner(
        base_config={
            "n_agents": 4,
            "grid_size": 5,
            "seed": 42,
            "info_env": info_env,
        },
    )

    # Patch _create_simulation to capture the simulation before it runs
    original = runner._create_simulation
    created_sims = []
    def capturing_create(config, logger):
        sim = original(config, logger)
        created_sims.append(sim)
        return sim
    runner._create_simulation = capturing_create

    runner.run(ticks=5)

    assert len(created_sims) == 1
    sim = created_sims[0]
    assert isinstance(sim.info_env, NoisyAlphaInformation), (
        f"Expected NoisyAlphaInformation, got {type(sim.info_env)}"
    )
    assert sim.info_env.noise_std == 0.2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_batch.py::test_batch_runner_honors_info_env -v`
Expected: FAIL — `sim.info_env` is `FullInformation`.

**Step 3: Add `info_env` parameter to `create_simple_economy`**

In `microecon/simulation.py`, update `create_simple_economy` signature and body:

Add parameter after `bargaining_protocol`:
```python
def create_simple_economy(
    n_agents: int,
    grid_size: int = 10,
    perception_radius: float = 7.0,
    discount_factor: float = 0.95,
    seed: Optional[int] = None,
    bargaining_protocol: Optional[BargainingProtocol] = None,
    decision_procedure: Optional[DecisionProcedure] = None,
    use_beliefs: bool = False,
    info_env: Optional[InformationEnvironment] = None,
) -> Simulation:
```

Update the Simulation construction to use it:

Old:
```python
    sim = Simulation(
        grid=Grid(grid_size),
        info_env=FullInformation(),
        bargaining_protocol=bargaining_protocol or NashBargainingProtocol(),
        decision_procedure=decision_procedure or RationalDecisionProcedure(),
        _rng=rng,
    )
```

New:
```python
    sim = Simulation(
        grid=Grid(grid_size),
        info_env=info_env or FullInformation(),
        bargaining_protocol=bargaining_protocol or NashBargainingProtocol(),
        decision_procedure=decision_procedure or RationalDecisionProcedure(),
        _rng=rng,
    )
```

**Step 4: Pass info_env through in BatchRunner._create_simulation**

In `microecon/batch.py`, update `_create_simulation`:

Add extraction of info_env (after line 129):
```python
        info_env = config.get("info_env")
```

Pass it to `create_simple_economy`:
```python
        sim = create_simple_economy(
            n_agents=n_agents,
            grid_size=grid_size,
            perception_radius=perception_radius,
            discount_factor=discount_factor,
            seed=seed,
            bargaining_protocol=bargaining_protocol,
            info_env=info_env,
        )
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_batch.py -v`
Expected: All pass.

Run: `uv run pytest -q`
Expected: 716+ passed.

**Step 6: Commit**

```
fix(batch): pass configured info_env to simulation creation (A-002)

BatchRunner recorded info_env in metadata but created simulations with
hardcoded FullInformation. Now extracts info_env from config dict and
passes through create_simple_economy.
```

---

### Task 4: A-001 — Fix Replay Loader Schema Mismatch

**Files:**
- Modify: `server/routes.py:216-252`
- Modify: `frontend/src/types/simulation.ts:47-58`
- Test: `tests/test_replay_loader.py` (new file)

**Step 1: Write the integration test**

Create `tests/test_replay_loader.py`:

```python
"""Integration tests for replay loader endpoint (A-001)."""

import json
import tempfile
from pathlib import Path

import pytest

from microecon.simulation import create_simple_economy
from microecon.logging import SimulationLogger, SimulationConfig, JSONLinesFormat


@pytest.fixture
def run_dir():
    """Create a real simulation run and return its directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_run"

        config = SimulationConfig(
            n_agents=4,
            grid_size=5,
            seed=42,
            protocol_name="nash",
        )
        logger = SimulationLogger(
            config=config,
            output_path=output_path,
            log_format=JSONLinesFormat(),
        )

        sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
        sim.logger = logger
        sim.run(10)
        logger.finalize()

        yield output_path


def test_replay_loads_logged_run(run_dir):
    """Replay loader must successfully parse runs from SimulationLogger."""
    config_file = run_dir / "config.json"
    ticks_file = run_dir / "ticks.jsonl"

    assert config_file.exists()
    assert ticks_file.exists()

    with open(config_file) as f:
        config = json.load(f)

    ticks = []
    with open(ticks_file) as f:
        for line in f:
            tick_data = json.loads(line)
            ticks.append(tick_data)

    assert len(ticks) == 10

    # Verify the actual field names match what AgentSnapshot.to_dict() produces
    first_tick = ticks[0]
    assert "agent_snapshots" in first_tick
    agent = first_tick["agent_snapshots"][0]
    assert "agent_id" in agent
    assert "endowment" in agent  # list [x, y], not endowment_x/endowment_y
    assert isinstance(agent["endowment"], list)
    assert len(agent["endowment"]) == 2

    # Verify trade field names match TradeEvent.to_dict()
    # Find a tick with trades
    ticks_with_trades = [t for t in ticks if t["trades"]]
    if ticks_with_trades:
        trade = ticks_with_trades[0]["trades"][0]
        assert "agent1_id" in trade  # not agent_1_id
        assert "proposer_id" in trade
        assert "pre_holdings" in trade
        assert "post_allocations" in trade

    # Verify belief_snapshots field exists
    assert "belief_snapshots" in first_tick
```

**Step 2: Run test to verify it passes (this tests the raw data, not the route)**

Run: `uv run pytest tests/test_replay_loader.py -v`
Expected: PASS — this validates the data format. The actual bug is in the route transform.

**Step 3: Fix the replay loader transform in `server/routes.py`**

Replace lines 216-252 of the transform block inside `load_run()`:

Old:
```python
                ticks.append({
                    "tick": tick_data["tick"],
                    "agents": [
                        {
                            "id": agent["agent_id"],
                            "position": agent["position"],
                            "endowment": [agent["endowment_x"], agent["endowment_y"]],
                            "alpha": agent["alpha"],
                            "utility": agent["utility"],
                            "perception_radius": agent.get("perception_radius", 7.0),
                            "discount_factor": agent.get("discount_factor", 0.95),
                            "has_beliefs": agent.get("has_beliefs", False),
                        }
                        for agent in tick_data.get("agent_snapshots", [])
                    ],
                    "trades": [
                        {
                            "tick": trade["tick"],
                            "agent1_id": trade["agent_1_id"],
                            "agent2_id": trade["agent_2_id"],
                            "alpha1": trade.get("alpha_1", 0.5),
                            "alpha2": trade.get("alpha_2", 0.5),
                            "pre_holdings_1": trade.get("pre_holdings_1", trade.get("pre_endowment_1", [0, 0])),
                            "pre_holdings_2": trade.get("pre_holdings_2", trade.get("pre_endowment_2", [0, 0])),
                            "post_allocation_1": [trade["allocation_1_x"], trade["allocation_1_y"]],
                            "post_allocation_2": [trade["allocation_2_x"], trade["allocation_2_y"]],
                            "gains": [trade.get("gain_1", 0), trade.get("gain_2", 0)],
                        }
                        for trade in tick_data.get("trades", [])
                    ],
                    "metrics": {
                        "total_welfare": tick_data.get("total_welfare", 0),
                        "welfare_gains": tick_data.get("total_welfare", 0) - config.get("initial_welfare", 0),
                        "cumulative_trades": tick_data.get("cumulative_trades", 0),
                    },
                    "beliefs": {},  # Beliefs not stored in standard format yet
                })
```

New:
```python
                # Build belief map from belief_snapshots
                beliefs = {}
                for bs in tick_data.get("belief_snapshots", []):
                    beliefs[bs["agent_id"]] = {
                        "type_beliefs": [
                            {
                                "target_id": tb["agent_id"],
                                "believed_alpha": tb["believed_alpha"],
                                "confidence": tb["confidence"],
                                "n_interactions": tb["n_interactions"],
                            }
                            for tb in bs.get("type_beliefs", [])
                        ],
                        "price_belief": {
                            "mean": bs["price_belief"]["mean"],
                            "variance": bs["price_belief"]["variance"],
                            "n_observations": bs["price_belief"]["n_observations"],
                        } if bs.get("price_belief") else None,
                        "n_trades_in_memory": bs.get("n_trades_in_memory", 0),
                    }

                ticks.append({
                    "tick": tick_data["tick"],
                    "agents": [
                        {
                            "id": agent["agent_id"],
                            "position": agent["position"],
                            "endowment": agent["endowment"],
                            "alpha": agent["alpha"],
                            "utility": agent["utility"],
                            "perception_radius": agent.get("perception_radius", 7.0),
                            "discount_factor": agent.get("discount_factor", 0.95),
                            "has_beliefs": agent.get("has_beliefs", False),
                        }
                        for agent in tick_data.get("agent_snapshots", [])
                    ],
                    "trades": [
                        {
                            "tick": tick_data["tick"],
                            "agent1_id": trade["agent1_id"],
                            "agent2_id": trade["agent2_id"],
                            "proposer_id": trade.get("proposer_id"),
                            "pre_holdings_1": trade["pre_holdings"][0],
                            "pre_holdings_2": trade["pre_holdings"][1],
                            "post_allocation_1": trade["post_allocations"][0],
                            "post_allocation_2": trade["post_allocations"][1],
                            "gains": trade["gains"],
                        }
                        for trade in tick_data.get("trades", [])
                    ],
                    "metrics": {
                        "total_welfare": tick_data.get("total_welfare", 0),
                        "welfare_gains": tick_data.get("total_welfare", 0) - config.get("initial_welfare", 0),
                        "cumulative_trades": tick_data.get("cumulative_trades", 0),
                    },
                    "beliefs": beliefs,
                })
```

**Step 4: Add `proposer_id` to frontend Trade type**

In `frontend/src/types/simulation.ts`, update the Trade interface:

Old:
```typescript
export interface Trade {
  tick: number;
  agent1_id: string;
  agent2_id: string;
  alpha1: number;
  alpha2: number;
  pre_holdings_1: [number, number];
  pre_holdings_2: [number, number];
  post_allocation_1: [number, number];
  post_allocation_2: [number, number];
  gains: [number, number];
}
```

New:
```typescript
export interface Trade {
  tick: number;
  agent1_id: string;
  agent2_id: string;
  proposer_id?: string;
  pre_holdings_1: [number, number];
  pre_holdings_2: [number, number];
  post_allocation_1: [number, number];
  post_allocation_2: [number, number];
  gains: [number, number];
}
```

(Remove `alpha1` and `alpha2` — they were never actually populated with real data.)

**Step 5: Run backend tests**

Run: `uv run pytest tests/test_replay_loader.py -v`
Expected: PASS

Run: `uv run pytest -q`
Expected: 716+ passed.

**Step 6: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds. If any component relied on `alpha1`/`alpha2`, fix those references.

**Step 7: Commit**

```
fix(replay): align replay loader with actual log schema (A-001)

Route transform now reads correct field names from AgentSnapshot.to_dict()
and TradeEvent.to_dict() output. Adds belief snapshot parsing, proposer_id
passthrough, and removes phantom alpha1/alpha2 fields.
```

---

### Task 5: A-007 — Wire Information-Regime Product Surface

**Files:**
- Modify: `server/simulation_manager.py:37-100` (SimulationConfig)
- Modify: `server/simulation_manager.py:239-315` (_create_simulation_from_config)
- Modify: `server/routes.py:22-31` (ConfigRequest)
- Modify: `frontend/src/types/simulation.ts:66-76` (SimulationConfig type)
- Modify: `frontend/src/components/Config/ConfigModal.tsx`
- Test: `tests/test_info_env_surface.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_info_env_surface.py`:

```python
"""Integration tests for information-regime product surface (A-007)."""

from server.simulation_manager import SimulationConfig, _create_simulation_from_config
from microecon.information import NoisyAlphaInformation, FullInformation


def test_config_with_noisy_alpha_creates_noisy_simulation():
    """Server config with info_env_name='noisy_alpha' must create NoisyAlphaInformation."""
    config = SimulationConfig(
        n_agents=4,
        grid_size=5,
        seed=42,
        bargaining_protocol="nash",
        info_env_name="noisy_alpha",
        info_env_params={"noise_std": 0.2},
    )
    sim = _create_simulation_from_config(config)
    assert isinstance(sim.info_env, NoisyAlphaInformation)
    assert sim.info_env.noise_std == 0.2


def test_config_default_creates_full_information():
    """Default config must still create FullInformation."""
    config = SimulationConfig(
        n_agents=4,
        grid_size=5,
        seed=42,
        bargaining_protocol="nash",
    )
    sim = _create_simulation_from_config(config)
    assert isinstance(sim.info_env, FullInformation)


def test_config_roundtrip_preserves_info_env():
    """SimulationConfig to_dict/from_dict must preserve info_env fields."""
    config = SimulationConfig(
        n_agents=4,
        grid_size=5,
        seed=42,
        bargaining_protocol="nash",
        info_env_name="noisy_alpha",
        info_env_params={"noise_std": 0.3},
    )
    d = config.to_dict()
    restored = SimulationConfig.from_dict(d)
    assert restored.info_env_name == "noisy_alpha"
    assert restored.info_env_params == {"noise_std": 0.3}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_info_env_surface.py -v`
Expected: FAIL — `SimulationConfig` (server version) has no `info_env_name` field, and `_create_simulation_from_config` hardcodes `FullInformation()`.

**Step 3: Add info_env fields to server SimulationConfig**

In `server/simulation_manager.py`, add fields to the `SimulationConfig` dataclass (after `bargaining_power_distribution`):

```python
    info_env_name: str = "full"
    info_env_params: dict[str, Any] = field(default_factory=dict)
```

Update `to_dict()` to include them:

```python
        result["info_env_name"] = self.info_env_name
        result["info_env_params"] = self.info_env_params
```

Update `from_dict()` to parse them:

```python
            info_env_name=d.get("info_env_name", "full"),
            info_env_params=d.get("info_env_params", {}),
```

**Step 4: Add info_env factory and wire `_create_simulation_from_config`**

Add a factory function near the top of `server/simulation_manager.py`:

```python
def _create_info_env(name: str, params: dict[str, Any]) -> InformationEnvironment:
    """Create an InformationEnvironment from name and params."""
    if name == "noisy_alpha":
        return NoisyAlphaInformation(noise_std=params.get("noise_std", 0.1))
    return FullInformation()
```

Add the import for `NoisyAlphaInformation`:

```python
from microecon.information import FullInformation, InformationEnvironment, NoisyAlphaInformation
```

In `_create_simulation_from_config`, replace the hardcoded `FullInformation()` usages:

Where `info_env=FullInformation()` appears (both in the scenario branch ~line 273 and the create_simple_economy call path), replace with:

```python
    info_env = _create_info_env(config.info_env_name, config.info_env_params)
```

Then pass `info_env=info_env` to the `Simulation()` constructor and to `create_simple_economy()`.

**Step 5: Add info_env fields to ConfigRequest**

In `server/routes.py`, update `ConfigRequest`:

```python
class ConfigRequest(BaseModel):
    n_agents: int = 10
    grid_size: int = 15
    perception_radius: float = 7.0
    discount_factor: float = 0.95
    seed: int | None = None
    bargaining_protocol: str = "nash"
    use_beliefs: bool = False
    info_env_name: str = "full"
    info_env_params: dict[str, Any] = {}
```

Add the `Any` import from `typing` if not already present.

**Step 6: Run tests**

Run: `uv run pytest tests/test_info_env_surface.py -v`
Expected: PASS

Run: `uv run pytest -q`
Expected: 716+ passed.

**Step 7: Update frontend SimulationConfig type**

In `frontend/src/types/simulation.ts`:

```typescript
export interface SimulationConfig {
  n_agents: number;
  grid_size: number;
  perception_radius: number;
  discount_factor: number;
  seed: number | null;
  bargaining_protocol: "nash" | "rubinstein" | "tioli" | "asymmetric_nash";
  bargaining_power_distribution?: "uniform" | "gaussian" | "bimodal";
  use_beliefs: boolean;
  info_env_name?: string;
  info_env_params?: Record<string, number>;
}
```

**Step 8: Add info_env controls to ConfigModal**

In `frontend/src/components/Config/ConfigModal.tsx`:

Add `info_env_name` and `info_env_params` to the `FormConfig` type (at the type definition):

```typescript
  info_env_name: 'full' | 'noisy_alpha';
  info_env_params: { noise_std?: number };
```

Add defaults in the initial state and sync effect.

Add UI controls after the existing bargaining protocol select — a dropdown for info environment and a conditional noise_std slider:

```tsx
{/* Information Environment */}
<div className="space-y-2">
  <Label>Information Environment</Label>
  <Select
    value={formConfig.info_env_name}
    onValueChange={(v) => setFormConfig({ ...formConfig, info_env_name: v as FormConfig['info_env_name'] })}
  >
    <SelectTrigger><SelectValue /></SelectTrigger>
    <SelectContent>
      <SelectItem value="full">Full Information</SelectItem>
      <SelectItem value="noisy_alpha">Noisy Alpha</SelectItem>
    </SelectContent>
  </Select>
</div>

{formConfig.info_env_name === 'noisy_alpha' && (
  <div className="space-y-2">
    <Label>Noise Std: {formConfig.info_env_params?.noise_std ?? 0.1}</Label>
    <Slider
      value={[formConfig.info_env_params?.noise_std ?? 0.1]}
      onValueChange={([v]) => setFormConfig({
        ...formConfig,
        info_env_params: { noise_std: v },
      })}
      min={0.01}
      max={0.5}
      step={0.01}
    />
  </div>
)}
```

**Step 9: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 10: Commit**

```
feat(server): add information-regime config pathway (A-007)

Add info_env_name and info_env_params to server SimulationConfig,
ConfigRequest, and frontend config. Supports full information (default)
and noisy alpha with configurable noise_std. Simulation creation now
uses configured info environment instead of hardcoded FullInformation.
```

---

### Task 6: A-004 — Frontend Lint Cleanup

**Files:**
- Modify: `frontend/src/hooks/useSimulationSocket.ts`
- Modify: `frontend/src/components/Grid/GridCanvas.tsx`
- Modify: `frontend/src/components/Comparison/DualGridView.tsx`
- Modify: `frontend/src/components/Config/ConfigModal.tsx`
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/components/Network/TradeNetwork.tsx`
- Modify: `frontend/src/components/Replay/ReplayLoader.tsx`

**Step 1: Fix self-referencing `connect()` in useSimulationSocket.ts**

The `connect` function calls itself in the `onclose` reconnect timeout. Fix by using a ref:

Add after existing refs (around line 25):
```typescript
const connectRef = useRef<() => void>();
```

After the `connect` useCallback definition (after line 196), add:
```typescript
connectRef.current = connect;
```

Inside the `onclose` handler, replace `connect()` (line 64) with:
```typescript
connectRef.current?.();
```

**Step 2: Fix self-referencing `render()` in GridCanvas.tsx**

Same pattern. Add a ref:
```typescript
const renderRef = useRef<() => void>();
```

After the `render` useCallback, add:
```typescript
renderRef.current = render;
```

Replace `requestAnimationFrame(render)` (line 441) with:
```typescript
requestAnimationFrame(() => renderRef.current?.());
```

**Step 3: Fix self-referencing `render()` in DualGridView.tsx**

Same pattern as GridCanvas. Add ref, assign after useCallback, replace the `requestAnimationFrame(render)` call (line 115).

**Step 4: Fix setState-in-effect in ConfigModal.tsx**

The `useEffect` that syncs form state when modal opens (line 75-88) triggers a lint warning. This is a standard "sync form from external state" pattern. The cleanest fix is to key the dialog content on `open` state so it re-mounts with fresh state, OR use `useMemo` for initial state. However, the simplest fix that preserves behavior:

Replace the `useEffect` with a `useMemo`-based approach, or add a functional update:

```typescript
  useEffect(() => {
    if (open && config) {
      setFormConfig(prev => {
        const next = {
          n_agents: config.n_agents,
          grid_size: config.grid_size,
          perception_radius: config.perception_radius,
          discount_factor: config.discount_factor,
          seed: config.seed,
          bargaining_protocol: config.bargaining_protocol as FormConfig['bargaining_protocol'],
          bargaining_power_distribution: (config.bargaining_power_distribution || 'uniform') as FormConfig['bargaining_power_distribution'],
          use_beliefs: config.use_beliefs,
          info_env_name: (config.info_env_name || 'full') as FormConfig['info_env_name'],
          info_env_params: config.info_env_params || {},
        };
        return next;
      });
    }
  }, [open, config]);
```

Note: Check if `react-hooks/set-state-in-effect` is satisfied by a functional update — if not, extract into a derived-state pattern or add an eslint-disable for this specific line with a comment explaining the sync pattern.

**Step 5: Fix non-component export in button.tsx**

Add eslint-disable comment above the export:

```typescript
// eslint-disable-next-line react-refresh/only-export-components
export { Button, buttonVariants }
```

This is standard for shadcn/ui components.

**Step 6: Fix missing deps in TradeNetwork.tsx**

Add `renderFull` to the dependency array (line 263):

Old: `}, [layout, width, height]);`
New: `}, [layout, width, height, renderFull]);`

**Step 7: Fix missing deps in ReplayLoader.tsx**

Wrap `fetchRuns` in `useCallback`, then add it to the effect deps:

```typescript
const fetchRuns = useCallback(async () => {
  // ... existing body ...
}, []);

useEffect(() => {
  if (open) {
    fetchRuns();
  }
}, [open, fetchRuns]);
```

**Step 8: Verify lint passes**

Run: `cd frontend && npm run lint`
Expected: 0 errors, 0 warnings.

**Step 9: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 10: Commit**

```
fix(frontend): resolve all ESLint errors and warnings (A-004)

Fix hook immutability violations using useRef pattern for self-referencing
callbacks. Fix setState-in-effect with functional update. Fix missing
exhaustive-deps. Add eslint-disable for shadcn/ui buttonVariants export.
```

---

### Task 7: Final Verification

**Step 1: Run full backend test suite**

Run: `uv run pytest -q`
Expected: 716+ passed (plus new tests), 15 skipped.

**Step 2: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: Clean.

**Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Success.

**Step 4: Quick manual smoke test**

Run: `uv run python -c "from microecon.batch import BatchRunner; from microecon.information import NoisyAlphaInformation; r = BatchRunner(base_config={'n_agents': 4, 'grid_size': 5, 'seed': 42, 'info_env': NoisyAlphaInformation(noise_std=0.2)}); results = r.run(ticks=10); print(f'{len(results)} runs, {results[0].summary}')"`
Expected: Prints 1 run with summary stats.

**Step 5: Commit any final adjustments if needed**
