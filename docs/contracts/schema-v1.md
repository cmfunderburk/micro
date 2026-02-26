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
