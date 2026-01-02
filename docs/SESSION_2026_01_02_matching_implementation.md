# Session Review: Matching Protocol Implementation

**Date:** 2026-01-02
**Branch:** `tweaking`
**Commits:** `70a0946`, `debcb63`

---

## 1. What Was Accomplished

### Matching Protocol Integration (Phase 2 Complete)

Integrated the `MatchingProtocol` abstraction into the simulation engine with a four-phase tick structure:

```
Each Tick:
1. EVALUATE  - Observe visible agents, compute surplus rankings
2. DECIDE    - Form commitments (committed) or select targets (opportunistic)
3. MOVE      - Move toward committed partner or selected target
4. EXCHANGE  - Execute bargaining (commitment-gated or any co-located)

Pre-tick: Commitment maintenance (break stale commitments)
```

### Key Finding: Welfare Gap Between Protocols

The trading chain scenario (4 agents, α ∈ {0.2, 0.4, 0.6, 0.8}) revealed that **matching protocols affect outcomes, not just paths**:

| Metric | Committed | Opportunistic |
|--------|-----------|---------------|
| Trades | 2 (optimal pairs: A-D, B-C) | 3 (suboptimal: B-C, B-D, A-B) |
| Final MRS | All = 1.0 | Varies (0.66 - 1.88) |
| Welfare | 26.80 | 26.20 |
| Efficiency | 100% | 97.8% |

**Why opportunistic underperforms:** After B-C trade, B continues toward D and trades opportunistically. This "uses up" D before A arrives, forcing A to trade with B instead of optimal partner D.

### Test Coverage

Expanded trading chain tests from 29 to 55:
- `TestTradingChainCommittedStage1-3`: Committed mode behavior
- `TestTradingChainOpportunisticStage1-3`: Opportunistic mode behavior
- `TestMatchingProtocolComparison`: Direct welfare comparison

Total test count: 341 (up from ~160)

### Documentation Updated

- `DESIGN_matching_protocol.md`: Added empirical findings section (§8)
- `STATUS.md`: Updated with matching protocols, four-phase tick, test counts
- `CLAUDE.md`: Added matching.py module, matching protocol abstraction

---

## 2. Next Priority: Logging Integration

### Current State

Event types are **defined** in `matching.py` but **not wired** into `SimulationLogger`:

```python
@dataclass
class CommitmentFormedEvent:
    tick: int
    agent_a: str
    agent_b: str

@dataclass
class CommitmentBrokenEvent:
    tick: int
    agent_a: str
    agent_b: str
    reason: str  # "trade_completed" | "left_perception"

@dataclass
class MatchingPhaseResult:
    tick: int
    new_pairs: List[Tuple[str, str]]
    unmatched_agents: List[str]
    algorithm_succeeded: bool
```

### Work Needed

1. **Extend `SimulationLogger`** (`logging/logger.py`):
   - Add `log_commitment_formed(tick, agent_a, agent_b)`
   - Add `log_commitment_broken(tick, agent_a, agent_b, reason)`
   - Add `log_matching_phase(tick, pairs, unmatched, success)`

2. **Emit events from `simulation.py`**:
   - After `commitments.form_commitment()` calls
   - After `commitments.break_commitment()` calls
   - After `matching_protocol.compute_matches()` returns

3. **Update `events.py`**:
   - Include commitment events in `TickRecord` (or as separate stream)
   - Consider whether to include in JSON lines format

4. **Add analysis functions** (`analysis/`):
   - Commitment duration statistics
   - Match success rate per tick
   - Protocol comparison utilities

### Value

Enables systematic batch runs comparing protocols across:
- Different agent counts
- Different spatial configurations
- Different preference distributions
- Random seeds for statistical significance

---

## 3. Next Priority: More Scenarios

### Candidates

| Scenario | Configuration | Research Question |
|----------|---------------|-------------------|
| **Hub-and-spoke** | 1 center + N ring agents | How does committed matching handle asymmetric topology? |
| **Two clusters** | Two groups separated by distance | Inter-cluster vs intra-cluster matching dynamics |
| **Random placement** | Uniform random positions | Stochastic welfare comparisons |
| **Odd agents** | 3, 5, 7 agents | Irving's partial matching behavior |
| **Preference spread** | Narrow vs wide α distribution | When does protocol choice matter most? |

### Suggested First: Hub-and-Spoke

The hub-and-spoke scenario exists in `tests/scenarios/test_hub_and_spoke.py` but predates matching protocols. Update to:
1. Test with both `OpportunisticMatchingProtocol` and `StableRoommatesMatchingProtocol`
2. Verify different dynamics (does hub get matched first? Do spokes wait?)
3. Measure welfare gap

---

## 4. Medium-Term: Dashboard Integration

### Vision

Test scenarios become **example simulations** in the visualization dashboard:

```
┌─────────────────────────────────────────────────┐
│  Example Scenarios                              │
│  ┌───────────────┐ ┌───────────────┐            │
│  │ Trading Chain │ │ Hub & Spoke   │            │
│  │ 4 agents      │ │ 5 agents      │            │
│  │ α: 0.2-0.8    │ │ center + ring │            │
│  └───────────────┘ └───────────────┘            │
│  ┌───────────────┐ ┌───────────────┐            │
│  │ Two Agent     │ │ Random (20)   │            │
│  │ Baseline      │ │ Stochastic    │            │
│  └───────────────┘ └───────────────┘            │
└─────────────────────────────────────────────────┘
```

### Requirements

1. **Scenario definition format**: JSON/YAML files specifying:
   - Agent positions, preferences, endowments
   - Protocol configurations
   - Expected outcomes (for comparison)

2. **Scenario browser**: UI component to select and load scenarios

3. **Pre-configured comparisons**: Side-by-side runs with different protocols

4. **Logged data display**: Show commitment events, welfare curves

### Blockers

- Need logging integration first (to capture data for display)
- Need scenarios defined (to populate the browser)
- ImPlot integration for time-series charts (deferred)

---

## 5. Files Changed This Session

```
src/microecon/simulation.py       # Four-phase tick structure
tests/scenarios/test_trading_chain.py  # 55 tests (was 29)
docs/DESIGN_matching_protocol.md  # Empirical findings
STATUS.md                         # Updated capabilities
CLAUDE.md                         # Updated module list
```

---

## 6. Starting Point for Next Session

**Option A: Logging Integration**
```bash
# Start here:
src/microecon/logging/logger.py   # Add commitment event methods
src/microecon/logging/events.py   # Extend TickRecord
src/microecon/simulation.py       # Emit events
```

**Option B: More Scenarios**
```bash
# Start here:
tests/scenarios/test_hub_and_spoke.py  # Add protocol variants
tests/scenarios/test_properties.py     # Property-based tests with matching
```

**Recommended:** Start with logging (1-2 hours), then use logging to validate new scenarios.

---

**Document Version:** 1.0
**Author:** Session 2026-01-02
