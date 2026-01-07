# Phase 1 Resolution Options

**Purpose:** Options and tradeoffs for each finding in PHASE1-REVIEW-DECISIONS.md. Review independently, then discuss in a follow-up session.

---

## RESOLUTION-01: Wiring Belief Updates to Simulation Loop

### The Problem
`simulation.py` exchange phase executes trades but never triggers belief updates. Agents have memory infrastructure that's never used.

### Option A: Direct Calls in Simulation Loop

Add explicit calls in `simulation.py` after trade execution:

```python
# After successful trade in exchange phase
if agent_a.has_beliefs:
    agent_a.record_trade_observation(agent_b_id, observed_alpha, trade_bundle, price)
if agent_b.has_beliefs:
    agent_b.record_trade_observation(agent_a_id, observed_alpha, trade_bundle, price)

# When agents meet but don't trade
if agent_a.has_beliefs:
    agent_a.record_encounter(agent_b_id, observed_alpha)
```

**Pros:**
- Simple, explicit, easy to understand
- Low refactoring risk
- Easy to test

**Cons:**
- Simulation loop becomes aware of belief details
- Adding new belief triggers requires modifying simulation.py

### Option B: Event-Driven Architecture

Emit events from simulation; belief system subscribes:

```python
# simulation.py emits
self.emit_event(TradeExecuted(agent_a, agent_b, bundle, price))

# beliefs.py subscribes
@subscribe(TradeExecuted)
def on_trade(event):
    # update beliefs
```

**Pros:**
- Clean separation of concerns
- Extensible - new subscribers don't modify simulation
- Aligns with logging architecture (which already captures events)

**Cons:**
- More infrastructure to build
- Event ordering/timing complexity
- May be over-engineering for current needs

### Option C: Hook into Existing Logger

The logger already captures trade events. Belief updates could process logged events:

```python
# In logger or as post-processor
def on_trade_logged(trade_event):
    for agent in [trade_event.agent_a, trade_event.agent_b]:
        if agent.has_beliefs:
            agent.record_trade_observation(...)
```

**Pros:**
- Reuses existing infrastructure
- Beliefs update based on same events that are logged
- No changes to simulation.py core loop

**Cons:**
- Creates dependency between logging and belief updates
- Logging is currently optional; would beliefs be too?
- Ordering: do beliefs update before or after log write?

### Recommendation
**Option A** for Phase 1.5 completion. Simple, testable, ships quickly. Option B could be a Phase 2+ refactor if event patterns become common.

---

## RESOLUTION-02: Bargaining with Beliefs

### The Problem
Bargaining protocols use `agent.preferences` directly. Information asymmetry has no effect on exchange.

### Option A: Effective Type Parameter

Add optional `effective_type` parameter to bargaining methods:

```python
def solve(self, agent_a, agent_b, effective_type_a=None, effective_type_b=None):
    type_a = effective_type_a or agent_a.observable_type
    type_b = effective_type_b or agent_b.observable_type
    # compute based on types, apply to real endowments
```

**Pros:**
- Minimal API change
- Caller decides what types to use
- Backward compatible (None = use real types)

**Cons:**
- Caller must manage belief → effective type conversion
- "Effective type" concept adds cognitive load

### Option B: Belief Context Object

Pass a context object that encapsulates information environment:

```python
def solve(self, agent_a, agent_b, context: BargainingContext = None):
    # context.get_type(agent_a, as_seen_by=agent_b) returns believed type
```

**Pros:**
- Cleaner abstraction
- Context can handle complex scenarios (mutual beliefs, signaling)
- Separates "what agent knows" from "how bargaining works"

**Cons:**
- More design work upfront
- New abstraction to maintain

### Option C: Agent Method for "Presented Type"

Agent exposes `get_presented_type(to_observer)` that returns what it reveals:

```python
def solve(self, agent_a, agent_b):
    type_a = agent_a.get_presented_type(to=agent_b)  # what A shows to B
    type_b = agent_b.get_presented_type(to=agent_a)  # what B shows to A
```

**Pros:**
- Agent controls its own presentation
- Natural for signaling/screening extensions
- Bargaining code stays simple

**Cons:**
- Agent needs to know who's observing
- Conflates observation with strategic revelation

### Recommendation
**Option A** for immediate fix (simple, testable). Consider **Option B** for Phase 2 if belief interactions become more complex.

---

## RESOLUTION-03: Logging Belief State

### The Problem
Logs capture true types but not believed types. Belief dynamics are invisible.

### Option A: Extend Existing Events

Add fields to existing event dataclasses:

```python
@dataclass
class TargetEvaluation:
    ...
    observed_alpha: float
    believed_alpha: float | None  # NEW
    used_belief: bool  # NEW
```

**Pros:**
- Minimal structural change
- Backward compatible (new fields optional)
- Immediate visibility

**Cons:**
- Events grow larger
- Not all events need belief data

### Option B: Separate Belief Snapshot Events

Create dedicated belief logging events:

```python
@dataclass
class BeliefSnapshot:
    tick: int
    agent_id: str
    type_beliefs: dict[str, TypeBelief]
    price_belief: PriceBelief
```

Log periodically (every N ticks) or on change.

**Pros:**
- Clean separation
- Can log full belief state, not just per-interaction
- Enables belief trajectory analysis

**Cons:**
- More events in log
- Requires coordination on when to snapshot

### Option C: Both

Extend existing events with `used_belief` flag + add periodic snapshots.

**Pros:**
- Per-decision visibility AND trajectory visibility
- Most complete picture

**Cons:**
- More implementation work
- Larger logs

### Recommendation
**Option C** - both are valuable. Start with Option A (extend existing), add Option B snapshots as follow-up.

---

## RESOLUTION-04: Using Price Beliefs

### The Problem
`PriceBelief` exists but nothing consumes it. BELIEF-004 ("price expectations influence surplus calculation") is unmet.

### Option A: Price-Filtered Target Selection

Use price belief as a filter in `evaluate_targets`:

```python
def evaluate_targets(self, ...):
    for target in candidates:
        implied_price = estimate_trade_price(self, target)
        if not self.price_belief.is_acceptable(implied_price):
            continue  # skip targets with bad expected prices
        # ... rest of evaluation
```

**Pros:**
- Price beliefs affect behavior
- Computationally cheap (filter before surplus calc)

**Cons:**
- "Acceptable" threshold is a new design decision
- May be too aggressive (filters out learning opportunities)

### Option B: Price-Adjusted Surplus

Incorporate price belief into surplus calculation:

```python
expected_surplus = nash_surplus * price_confidence_factor
# or
expected_surplus = nash_surplus - price_risk_penalty
```

**Pros:**
- Continuous influence rather than hard filter
- More nuanced decision-making

**Cons:**
- How to combine? Multiplicative? Additive?
- Risk of ad-hoc formula without theoretical grounding

### Option C: Reserve Price from Belief

Agent computes a reservation price from beliefs; surplus calculated relative to that:

```python
reserve = self.price_belief.mean
trade_value = actual_price - reserve
```

**Pros:**
- Theoretically grounded (reservation prices are standard)
- Clear interpretation

**Cons:**
- Requires defining what "price" means in 2-good economy
- May need richer price belief structure

### Option D: Defer

Price beliefs are a Phase 2+ concern. Document as intentionally deferred.

**Pros:**
- Simplifies Phase 1.5 scope
- Avoids premature design decisions

**Cons:**
- BELIEF-004 remains unmet
- Dead code persists

### Recommendation
**Option D** (defer) unless there's a clear theoretical model for how price beliefs should affect search. This needs more design thought.

---

## RESOLUTION-05: `evaluate_targets` Using `bargaining_protocol`

### The Problem
The function accepts `bargaining_protocol` parameter but always uses Nash surplus.

### Option A: Use Protocol's Surplus Method

```python
def evaluate_targets(self, bargaining_protocol, ...):
    if bargaining_protocol:
        surplus = bargaining_protocol.compute_expected_surplus(...)
    else:
        surplus = compute_nash_surplus(...)
```

**Pros:**
- Parameter actually does something
- Search becomes institution-aware
- Enables protocol comparison experiments

**Cons:**
- Protocol must implement `compute_expected_surplus`
- Rubinstein surplus may be expensive to compute

### Option B: Remove the Parameter

If search should always use Nash surplus (as baseline/heuristic), remove the misleading parameter.

**Pros:**
- Honest API
- Simpler code

**Cons:**
- Loses institutional visibility in search
- May need to re-add later

### Option C: Strategy Pattern

Let caller specify surplus computation strategy:

```python
def evaluate_targets(self, surplus_fn=compute_nash_surplus, ...):
    ...
    surplus = surplus_fn(self, target)
```

**Pros:**
- Maximum flexibility
- No protocol dependency

**Cons:**
- More abstract
- Caller must understand surplus functions

### Recommendation
**Option A** - the parameter exists because institutional visibility is a core goal. Make it work.

---

## RESOLUTION-06: ADR/Code Interface Alignment

### The Problem
ADR says `AgentType`; code uses `float` (observed_alpha).

### Option A: Update ADR to Match Code

Document that the simplified interface (`float`) was chosen for Phase 1; `AgentType` deferred.

**Pros:**
- Documentation matches reality
- Acknowledges deliberate simplification

**Cons:**
- Loses the richer design
- May cement a limitation

### Option B: Update Code to Match ADR

Refactor to use `AgentType` in memory and update interfaces.

**Pros:**
- Enables multi-dimensional type learning (endowments, not just alpha)
- Fulfills original design

**Cons:**
- More refactoring
- May be premature if only alpha matters now

### Option C: Document as Divergence

Add to THEORY-DIVERGENCES.md with rationale for why simplification is acceptable.

**Pros:**
- Explicit acknowledgment
- Preserves both perspectives

**Cons:**
- Divergence persists
- Doesn't resolve the tension

### Recommendation
**Option A** - update ADR to match code, with a "Future Considerations" section noting `AgentType` as an extension path.

---

## RESOLUTION-07: Completing Integration Tests

### The Problem
Tests exist but don't assert. `test_should_trade_uses_beliefs` computes results but verifies nothing.

### Option A: Add Assertions to Existing Tests

Fill in the missing assertions:

```python
def test_should_trade_uses_beliefs():
    ...
    result_with_beliefs = ...
    result_without_beliefs = ...
    assert result_with_beliefs != result_without_beliefs  # beliefs matter
    # or more specific assertions about the difference
```

**Pros:**
- Quick fix
- Tests already set up scenarios

**Cons:**
- May need to understand intended behavior first

### Option B: Delete Placeholder, Write Fresh

Remove incomplete tests; write new tests with clear specifications:

```python
def test_trade_decision_affected_by_believed_alpha():
    """Agent with high believed_alpha of partner should be more willing to trade."""
    # clear setup, clear assertion
```

**Pros:**
- Clean slate
- Tests have clear intent from start

**Cons:**
- Loses any useful setup from existing tests

### Recommendation
**Option A** if the scenarios are sound; **Option B** if the test design is unclear.

---

## RESOLUTION-08: Factory Enabling Beliefs

### The Problem
`create_simple_economy` doesn't call `enable_beliefs()`.

### Option A: Add `use_beliefs` Parameter

```python
def create_simple_economy(..., use_beliefs: bool = False):
    ...
    if use_beliefs:
        for agent in agents:
            agent.enable_beliefs()
```

**Pros:**
- Opt-in, backward compatible
- Clear control point

**Cons:**
- Another parameter to manage

### Option B: Separate Factory Function

```python
def create_belief_enabled_economy(...):
    sim = create_simple_economy(...)
    for agent in sim.agents:
        agent.enable_beliefs()
    return sim
```

**Pros:**
- No change to existing function
- Clear intent from name

**Cons:**
- Code duplication or wrapper complexity

### Recommendation
**Option A** - single factory with flag is cleaner than parallel factories.

---

## Summary Table

| Finding | Recommended Resolution | Complexity | Priority |
|---------|----------------------|------------|----------|
| FIND-01 | Option A (direct calls) | Low | High |
| FIND-02 | Option A (effective type param) | Medium | High |
| FIND-03 | Option C (extend events + snapshots) | Medium | High |
| FIND-04 | Option D (defer) | N/A | Low |
| FIND-05 | Option A (use protocol method) | Low | Medium |
| FIND-06 | Option A (update ADR) | Low | Low |
| FIND-07 | Option A (add assertions) | Low | Medium |
| FIND-08 | Option A (add parameter) | Low | Medium |

---

## Suggested Implementation Order

1. **FIND-08** (factory flag) - enables testing everything else
2. **FIND-01** (wire simulation loop) - beliefs start updating
3. **FIND-07** (complete tests) - verify wiring works
4. **FIND-02** (bargaining with beliefs) - beliefs affect outcomes
5. **FIND-03** (logging) - make beliefs visible
6. **FIND-05** (evaluate_targets protocol) - search becomes institution-aware
7. **FIND-06** (ADR update) - documentation cleanup
8. **FIND-04** (price beliefs) - defer to Phase 2
