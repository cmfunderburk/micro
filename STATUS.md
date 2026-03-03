# Current Project Status

**Version:** 0.5.0 (Gate A complete)
**Date:** 2026-03-02
**Purpose:** Definitive reference for current capabilities

This document describes what exists and works today. For the long-term vision, see `docs/VISION/VISION-WORKFLOW-MASTER-SPEC.md`. For implementation semantics, see `docs/current/AGENT-ARCHITECTURE.md`.

---

## 1. What Works

### Simulation Core

A complete simulation engine for bilateral exchange in a spatial economy:

| Module | Capability |
|--------|------------|
| `bundle.py` | 2-good bundles with arithmetic operations |
| `preferences.py` | Cobb-Douglas utility with MRS, indifference curves, Marshallian demand |
| `agent.py` | Agents with private state / observable type, InteractionState machine, cooldowns |
| `grid.py` | NxN toroidal grid, positions, movement, spatial queries |
| `information.py` | Information environment abstraction (`FullInformation`, `NoisyAlphaInformation`) |
| `beliefs.py` | Agent memory, type beliefs, price beliefs, Bayesian and heuristic update rules |
| `bargaining.py` | Bargaining protocols (Nash, Rubinstein, Asymmetric Nash, TIOLI) with belief-aware surplus |
| `matching.py` | Swappable matching protocols (`BilateralProposalMatching`, `CentralizedClearingMatching`) |
| `search.py` | Target evaluation (discounted surplus), movement decisions, belief integration |
| `actions.py` | Action ABC and types: MoveAction, ProposeAction, AcceptAction, RejectAction, WaitAction |
| `decisions.py` | DecisionProcedure interface, RationalDecisionProcedure implementation |
| `simulation.py` | Three-phase tick loop (Perceive-Decide-Execute), `create_simple_economy()` factory |
| `batch.py` | `BatchRunner` for parameter sweeps with matching protocol support |

### Bargaining Protocols

Four complete implementations with theoretical grounding (O&R = Osborne & Rubinstein, *Bargaining and Markets*):

**Nash Bargaining** (`NashBargainingProtocol`) — O&R Ch 2
- Axiomatic solution maximizing Nash product
- Symmetric surplus split (equal bargaining power)
- Golden section search for numerical optimization

**Rubinstein Alternating Offers** (`RubinsteinBargainingProtocol`) — O&R Ch 3
- Uses BRW (1986) limit: patience determines bargaining power, not proposer identity
- More patient agent (higher delta) captures larger share of surplus
- Equal discount factors → symmetric Nash outcome

**Asymmetric Nash Bargaining** (`AsymmetricNashBargainingProtocol`) — O&R Ch 2.6
- Weighted Nash product: (u1-d1)^beta x (u2-d2)^(1-beta)
- beta = w1/(w1+w2) where w = `agent.bargaining_power` attribute
- Equal weights → symmetric Nash outcome
- Distinct from Rubinstein: power comes from exogenous attribute, not patience

**Take-It-Or-Leave-It** (`TIOLIBargainingProtocol`) — O&R S2.8
- Proposer extracts all surplus; responder receives exactly disagreement utility
- Lexicographic proposer selection (smaller agent ID proposes by default)
- Closed-form solution via golden section search on responder's indifference curve

### Matching Protocols

Matching is a first-class swappable component via the `MatchingProtocol` ABC (see ADR-006). Implementations receive all proposals and return a `MatchResult` with three disjoint sets: trades, rejections, and non-selections.

**BilateralProposalMatching** (default)
- Decentralized propose/accept/reject model
- Step 1: Mutual proposals (both agents propose to each other) trade immediately
- Step 2: Remaining proposals evaluated by target against opportunity cost
- Rejections add per-partner cooldowns (3 ticks); non-selections do not
- Deterministic: sorted agent ID iteration, lexicographic tie-breaking

**CentralizedClearingMatching**
- Centralized welfare-maximizing auctioneer
- Computes bilateral surplus for all adjacent proposer-target pairs
- Greedy assignment by descending surplus (each agent matched at most once)
- No rejections — unmatched proposals are non-selections (no cooldowns)

Both protocols satisfy the `MatchingProtocol` contract: deterministic, pure (no state mutation), and produce disjoint coverage of all proposers. Conformance tests enforce these properties.

### Schema and Contracts

Canonical schema versioning (Gate A, A-101 through A-107):

| Artifact | Description |
|----------|-------------|
| `logging/events.py` | Canonical dataclasses: `SimulationConfig`, `TradeEvent`, `TickRecord`, `RunSummary` |
| `SCHEMA_VERSION` | Currently `"1.0"`. Persisted in every run's `config.json` |
| `logging/formats.py` | Version validation on load (N/N-1 policy) |
| `scripts/generate_ts_types.py` | Auto-generates `frontend/src/types/canonical.ts` from Python schema |
| `docs/contracts/schema-v1.md` | Canonical schema specification |
| `docs/contracts/compatibility-policy.md` | Read/write compatibility rules |
| `docs/contracts/determinism-policy.md` | Seeded rerun equivalence policy |

Run provenance fields: `run_id` (UUID4, auto-generated), `manifest_id` and `treatment_arm` (stubs for Gate B).

### Agent Belief System

Complete belief architecture enabling agent learning:

- **Memory**: Trade history, price observations, partner interaction history (configurable depth)
- **Type Beliefs**: Beliefs about partner preference parameters (alpha), confidence tracking
- **Price Beliefs**: Mean-variance representation of expected exchange rate (deferred from decision logic)
- **Update Rules**: `BayesianUpdateRule` (conjugate prior), `HeuristicUpdateRule` (exponential moving average)
- **Integration**: Beliefs wire into search (surplus calculation) and bargaining (effective types). Snapshots logged each tick.

### Batch Runs & Research Workflow

| Module | Capability |
|--------|------------|
| `batch.py` | `BatchRunner` for parameter sweeps across bargaining and matching protocols |
| `scripts/research_workflow.py` | End-to-end research reproducibility flow (A-250) |
| `logging/events.py` | Versioned event types with schema compatibility |
| `logging/logger.py` | `SimulationLogger` with run_id generation |
| `logging/formats.py` | JSON lines format with version validation on load |

Batch runs require explicit seeds. The research workflow (`scripts/research_workflow.py`) demonstrates a complete protocol comparison: configure experiment, run batch, compute comparison outputs, produce evidence artifact.

### Analysis

Post-hoc analysis of logged runs:

| Module | Capability |
|--------|------------|
| `analysis/loader.py` | Load runs from disk, group by protocol/seed |
| `analysis/timeseries.py` | Welfare and trade counts over time |
| `analysis/distributions.py` | Cross-run statistical comparisons |
| `analysis/tracking.py` | Agent-level outcome tracking |
| `analysis/emergence.py` | Market emergence metrics |

### Web Frontend (Primary UI)

React 19 + Zustand + Vite. Three modes: Normal, Comparison, Replay. Shadcn-style Radix UI components.

```bash
./scripts/dev.sh                # Backend (:8000) + frontend (:5173)
```

**Live Mode**: Real-time WebSocket, config modal (agents, grid, seed, bargaining protocol, bargaining power distribution, info env, perception radius, discount factor, beliefs toggle), play/pause/step/reset, keyboard shortcuts.

**Comparison Mode**: Side-by-side dual grids, same seed + different protocols, synchronized controls, overlaid welfare/trade charts, real-time difference metrics.

**Replay Mode**: Load saved runs, timeline slider, step forward/backward, playback controls.

**Visualization**: Agent tooltips, perception radius overlay, movement trails, trade connections, belief connections, agent perspective mode, Edgeworth box trade inspection, D3 trade network panel, scenario browser.

**Export**: PNG/SVG frames, GIF recording, CSV (agent states, trades), JSON (full tick data).

### Test Coverage

848 tests (835 passing, 15 skipped) covering all core modules. Key test markers:

| Marker | Count | Scope |
|--------|-------|-------|
| `contract` | 48 | Schema conformance (4 levels: round-trip, persist/load, replay API, live WS) |
| `determinism` | 10 | Seeded rerun equivalence (all protocols + matching + noisy info + beliefs) |
| `theory` | ~100 | Bargaining theory verification (Nash product, Rubinstein limits, TIOLI extraction) |
| `matching` | ~80 | Matching protocol unit + conformance tests |
| `integration` | ~10 | Full pipeline tests |

```bash
uv run pytest                    # All tests
uv run pytest -m contract        # Schema conformance
uv run pytest -m determinism     # Determinism gate
uv run pytest -m theory          # Theory verification
```

---

## 2. Known Limitations

### Architectural

**Matching protocols not yet theory-grounded**
- `BilateralProposalMatching` and `CentralizedClearingMatching` are functional but not derived from formal matching theory (stable roommates, deferred acceptance, etc.)
- The `MatchingProtocol` abstraction makes it straightforward to add theory-based implementations
- See ADR-006 for design rationale

**2-good economy only**
- `Bundle(x, y)` is hardcoded for 2 goods
- Cobb-Douglas preferences assume 2 goods
- Visualization color encoding assumes 2 goods

**Belief system limitations**
- Price beliefs exist but are not yet consumed by decision logic
- Type beliefs track alpha only (not full AgentType with endowments)
- No reinforcement learning or evolutionary dynamics beyond belief updates

**No manifest/orchestrator services**
- Experiment manifests, execution orchestration, and artifact bundling are Gate B work
- Current batch runs are script-driven, not product-service-driven

### Scale Boundaries

**Recommended agent count: 2-200**
- Optimal: 50-100 agents (market emergence visible, reasonable runtime)
- Maximum tested: 200 agents (~5 minutes for 100 ticks)

**Grid size relative to agents**
- Recommended: grid_size >= sqrt(n_agents) to avoid excessive crowding

---

## 3. Architecture Notes

### Simulation Phases (Three-Phase Tick)

Each tick executes in order (per ADR-001):

1. **Perceive**: All agents observe frozen state (simultaneous snapshot)
2. **Decide**: All agents select ONE action (MoveAction, ProposeAction, WaitAction)
3. **Execute**: Matching protocol resolves proposals, trades execute, cooldowns apply, fallback actions run

### Key Interfaces

```python
class BargainingProtocol(ABC):
    def solve(self, agent_a, agent_b, ...) -> BargainingSolution | None: ...
    def execute(self, agent_a, agent_b, info_env, rng) -> TradeResult | None: ...

class MatchingProtocol(ABC):
    def resolve(self, propose_actions, agents, positions,
                decision_procedure, bargaining_protocol,
                action_context) -> MatchResult: ...
```

### Agent State Separation

```
AgentPrivateState     AgentType (Observable)
+-- preferences       +-- preferences*
+-- endowment         +-- endowment*
+-- discount_factor   +-- discount_factor*

* Controlled by InformationEnvironment
  FullInformation: identical to private state
  NoisyAlphaInformation: alpha + noise
```

---

## 4. Entry Points

```bash
# Web frontend (recommended)
./scripts/dev.sh

# Research workflow (protocol comparison)
uv run python scripts/research_workflow.py

# Tests
uv run pytest                        # All
uv run pytest -m contract            # Schema conformance
uv run pytest -m determinism         # Determinism gate
uv run pytest -m theory              # Theory verification
uv run pytest --cov=microecon        # Coverage
```

---

## 5. Gaps vs Vision

Status relative to `docs/VISION/VISION-WORKFLOW-MASTER-SPEC.md`:

| Vision Goal | Status |
|-------------|--------|
| Institutional visibility (swap protocols) | **Implemented** for bargaining and matching |
| Information regimes | **Implemented** (FullInformation, NoisyAlphaInformation) |
| Agent beliefs and learning | **Implemented** (type beliefs, memory, Bayesian/heuristic updates) |
| Matching/clearing abstraction | **Implemented** (MatchingProtocol ABC, 2 implementations) |
| Schema contracts and versioning | **Implemented** (v1.0, compatibility policy, conformance tests) |
| Deterministic reproducibility | **Implemented** (seeded reruns, tolerance policy, 10 determinism tests) |
| Research workflow proof | **Implemented** (scripted end-to-end, A-250) |
| Experiment manifest service | **Not started** (Gate B) |
| Execution orchestrator | **Not started** (Gate B) |
| Research/education track UIs | **Not started** (Gate B) |
| Narrative record and traceability | **Not started** (Gate B) |
| Publication bundles and audit | **Not started** (Gate C) |

---

## 6. File Structure

```
microecon/                   # Core simulation library
+-- bundle.py                # 2-good bundles
+-- preferences.py           # Cobb-Douglas utility
+-- agent.py                 # Agent with private state, InteractionState, cooldowns
+-- grid.py                  # NxN toroidal grid, positions, movement
+-- information.py           # Information environments (Full, NoisyAlpha)
+-- beliefs.py               # Agent memory, type/price beliefs, update rules
+-- bargaining.py            # Bargaining protocols (Nash, Rubinstein, Asymmetric Nash, TIOLI)
+-- matching.py              # MatchingProtocol ABC, BilateralProposalMatching, CentralizedClearingMatching
+-- search.py                # Target evaluation and movement
+-- actions.py               # Action types: Move, Propose, Accept, Reject, Wait
+-- decisions.py             # DecisionProcedure interface, RationalDecisionProcedure
+-- simulation.py            # Three-phase tick engine, create_simple_economy() factory
+-- batch.py                 # BatchRunner for parameter sweeps
+-- logging/
|   +-- events.py            # Canonical schema: SimulationConfig, TradeEvent, TickRecord, RunSummary
|   +-- logger.py            # SimulationLogger with run_id generation
|   +-- formats.py           # JSON lines format, version validation
+-- analysis/
|   +-- loader.py            # Load runs from disk
|   +-- timeseries.py        # Welfare/trades over time
|   +-- distributions.py     # Cross-run statistical comparisons
|   +-- tracking.py          # Agent-level outcome tracking
|   +-- emergence.py         # Market emergence metrics
+-- scenarios/
    +-- schema.py            # YAML scenario schema
    +-- loader.py            # Scenario loading utilities
    +-- market_emergence.py  # MarketEmergenceConfig

server/                      # FastAPI WebSocket server
+-- app.py                   # Application factory
+-- websocket.py             # WebSocket handlers
+-- simulation_manager.py    # Simulation lifecycle, config conversion
+-- routes.py                # REST API (config, scenarios, runs, replay)

scripts/
+-- generate_ts_types.py     # Python schema -> TypeScript types
+-- research_workflow.py     # End-to-end protocol comparison workflow

frontend/src/                # React 19 + Zustand + Vite
+-- App.tsx
+-- components/
|   +-- Grid/                # GridCanvas, AgentTooltip
|   +-- Charts/              # WelfareChart, TradeCountChart
|   +-- Controls/            # OverlayToggles, PerspectiveMode
|   +-- Config/              # ConfigModal, ExportMenu
|   +-- Beliefs/             # BeliefPanel
|   +-- Network/             # NetworkPanel, TradeNetwork
|   +-- TradeInspection/     # TradeHistoryPanel, EdgeworthBox, EdgeworthModal
|   +-- Comparison/          # DualGridView, ComparisonControls, ComparisonChart
|   +-- Replay/              # ReplayLoader, TimelineSlider, ReplayView
|   +-- Scenarios/           # ScenarioBrowser
|   +-- Layout/              # MainLayout
|   +-- ui/                  # Shadcn-style Radix primitives
+-- hooks/                   # useSimulationSocket, useKeyboardShortcuts, useContainerSize
+-- store/                   # Zustand: index, comparisonStore, replayStore
+-- types/                   # canonical.ts (auto-generated), simulation.ts
+-- lib/                     # chartConfig, colors, gridUtils, utils

tests/
+-- theory/                  # Bargaining theory verification
+-- scenarios/               # Scenario-based integration tests
+-- test_contract_conformance.py  # 4-level schema conformance
+-- test_determinism.py      # Seeded rerun equivalence
+-- test_matching.py         # Matching protocol tests
+-- test_matching_conformance.py  # Protocol contract conformance
+-- test_simulation.py       # Simulation engine tests
+-- ...                      # 44 test files total

docs/
+-- VISION/                  # Master spec, implementation plan, execution board
+-- adr/                     # 6 architectural decision records (ADR-001 through ADR-006)
+-- contracts/               # Schema v1, compatibility policy, determinism policy
+-- current/                 # AGENT-ARCHITECTURE.md (implementation reference)
+-- plans/                   # Active implementation plans
+-- CONTRIBUTING.md          # Schema change protocol, PR checklist
```

---

**Document Version:** 0.5.0
**Last Updated:** 2026-03-02 (Gate A: Foundation Coherence complete)
