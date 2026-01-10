# ADR-004: Exchange Event Correlation via exchange_id

**Status:** Proposed
**Created:** 2026-01-09
**Theoretical Basis:** Event sourcing; transaction cost measurement requirements

---

## Context

The current logging system captures events within ticks:

```python
@dataclass
class TickRecord:
    tick: int
    search_decisions: list[SearchDecision]
    commitments_formed: list[tuple[str, str]]
    commitments_broken: list[tuple[str, str]]
    movements: list[Movement]
    trades: list[TradeEvent]
    ...
```

With instantaneous exchange, a `TradeEvent` captures everything: who traded, what was exchanged, when. But with multi-tick exchanges (ADR-003), a single trade spans multiple events across ticks:

```
Tick 5: ProposalEvent (A proposes to B)
Tick 6: AcceptanceEvent (B accepts)
Tick 6: NegotiationEvent (negotiation starts)
Tick 6: TradeEvent (trade executes)
```

Without correlation, answering "how long did this exchange take?" requires manual reconstruction.

---

## Decision

Add `exchange_id` to all events in an exchange sequence, enabling correlation and transaction cost measurement.

### Exchange ID Generation

```python
import uuid

def generate_exchange_id() -> str:
    """Generate unique identifier for an exchange attempt."""
    return str(uuid.uuid4())[:8]  # Short form sufficient for typical runs
```

Generated when Propose action is chosen. Carried through all subsequent events regardless of outcome.

### Event Types

```python
@dataclass
class ProposalEvent:
    """Agent proposes exchange to target."""
    tick: int
    exchange_id: str
    proposer_id: str
    target_id: str
    proposer_position: tuple[int, int]

@dataclass
class ProposalResponseEvent:
    """Target responds to proposal."""
    tick: int
    exchange_id: str
    responder_id: str
    proposer_id: str
    response: Literal["accept", "reject", "timeout", "colocation_lost"]

@dataclass
class NegotiationEvent:
    """Negotiation phase of exchange."""
    tick: int
    exchange_id: str
    agent_a_id: str
    agent_b_id: str
    protocol: str  # Protocol name
    outcome: Literal["success", "failure", "colocation_lost"]
    # If success, TradeEvent follows with same exchange_id

@dataclass
class TradeEvent:
    """Existing event, extended with exchange_id."""
    tick: int
    exchange_id: str  # NEW: links to preceding proposal/negotiation
    agent_a_id: str
    agent_b_id: str
    bundle_a_gave: Bundle
    bundle_b_gave: Bundle
    protocol: str
    agent_a_surplus: float
    agent_b_surplus: float

@dataclass
class CooldownEvent:
    """Cooldown imposed after rejection."""
    tick: int
    exchange_id: str  # Links to the rejection that caused it
    agent_id: str
    target_id: str
    duration: int
    reason: Literal["rejection"]
```

### TickRecord Structure

```python
@dataclass
class TickRecord:
    tick: int

    # State snapshot (for visualization)
    agent_states: dict[str, AgentStateSnapshot]
    interaction_states: dict[str, InteractionState]

    # Events this tick (for analysis)
    events: list[Event]  # Union of all event types

    # Convenience accessors
    @property
    def proposals(self) -> list[ProposalEvent]: ...

    @property
    def trades(self) -> list[TradeEvent]: ...

    # ... etc
```

### Analysis Queries Enabled

```python
def exchange_duration(events: list[Event], exchange_id: str) -> int | None:
    """Ticks from proposal to trade completion."""
    proposal = find_event(events, exchange_id, ProposalEvent)
    trade = find_event(events, exchange_id, TradeEvent)
    if proposal and trade:
        return trade.tick - proposal.tick
    return None

def exchange_outcome(events: list[Event], exchange_id: str) -> str:
    """Final outcome of exchange attempt."""
    for event in reversed(events):
        if event.exchange_id == exchange_id:
            if isinstance(event, TradeEvent):
                return "completed"
            if isinstance(event, ProposalResponseEvent):
                return event.response  # "reject", "timeout", "colocation_lost"
            if isinstance(event, NegotiationEvent) and event.outcome != "success":
                return f"negotiation_{event.outcome}"
    return "unknown"

def transaction_cost_by_protocol(runs: list[Run]) -> dict[str, float]:
    """Average ticks per completed exchange, grouped by protocol."""
    # Group by protocol, compute mean duration
    ...

def rejection_rate(events: list[Event]) -> float:
    """Fraction of proposals that were rejected."""
    proposals = count_events(events, ProposalEvent)
    rejections = count_events(events, ProposalResponseEvent, response="reject")
    return rejections / proposals if proposals > 0 else 0.0
```

---

## Consequences

### Enables

- **Transaction cost measurement:** `exchange_duration()` directly measures ticks consumed.
- **Protocol comparison:** Group by protocol, compare mean durations and success rates.
- **Coordination failure analysis:** Track rejection rates, timeout rates, co-location loss rates.
- **Exchange-level replay:** Given exchange_id, reconstruct full sequence for debugging.

### Requires

- **ID generation:** Simple UUID generation at proposal time.
- **ID propagation:** All subsequent events receive the same exchange_id.
- **Event types:** Define new event dataclasses (Proposal, ProposalResponse, Negotiation, Cooldown).
- **Analysis utilities:** Functions to query and aggregate by exchange_id.

### Migration Impact

- **logging/events.py:** Add new event types; extend TradeEvent with exchange_id.
- **simulation.py:** Generate exchange_id on Propose, propagate through sequence.
- **analysis/*.py:** Update analysis functions to use new event structure.
- **Backward compatibility:** Old logs won't have exchange_id; analysis should handle gracefully.

---

## Alternatives Considered

### Derive from Timestamps Only

Could correlate events by tick proximity and agent pairing without explicit ID.

**Rejected:** Ambiguous when multiple exchanges involve same agents. Fails for long-running negotiations.

### Composite Key (proposer, target, proposal_tick)

Could use tuple as implicit correlation key.

**Rejected:** Verbose, error-prone, not as clean as single ID. What if same pair proposes multiple times in different scenarios?

### Event Sourcing with Full Replay

Could store only atomic events and derive all state via replay.

**Rejected:** Overkill for research platform. Hybrid (events + snapshots) is sufficient and simpler.

---

## References

- **Event sourcing:** Fowler, "Event Sourcing" (martinfowler.com)
- **Correlation in distributed systems:** Standard practice for request tracing
- **Transaction cost measurement:** Directly operationalizes Coase/Williamson

---

*Awaiting approval before implementation proceeds.*
