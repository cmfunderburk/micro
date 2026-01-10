# ADR-003: Multi-Tick Bilateral Exchange Sequence

**Status:** Proposed
**Created:** 2026-01-09
**Theoretical Basis:** O&R Bargaining Ch 2-4; Coase (1937); Williamson (1985) on transaction costs

---

## Context

Currently, bilateral exchange happens within a single tick:

```
Tick N:
  - A and B are co-located
  - should_trade(A, B) returns True
  - Bargaining protocol computes outcome
  - Holdings update
  - Done
```

This instantaneous exchange has no transaction cost—negotiation is free. But VISION.md identifies **transaction costs made explicit** as a corollary insight:

> The tick-based simulation model operationalizes transaction cost economics. Each phase of economic activity consumes time:
> - Search costs = ticks spent moving toward partners
> - Proposal costs = ticks spent initiating exchange
> - Negotiation costs = ticks spent in bargaining
> - Coordination failure costs = ticks wasted on rejected proposals

With instant exchange, only search costs are visible. Proposal, negotiation, and coordination failure costs are zero, making institutional comparison meaningless for these dimensions.

---

## Decision

Implement multi-tick bilateral exchange sequence:

```
Tick T: PROPOSE
  Agent A chooses Propose(target=B) action
  A enters PROPOSAL_PENDING state
  A is locked (cannot take other actions until resolved)
  Requires: A and B co-located, A not in cooldown for B

Tick T+1: RESPOND
  B observes pending proposal from A
  B chooses Accept(A) | Reject(A) | other action

  If Accept:
    Both enter NEGOTIATING state
    Negotiation begins

  If Reject:
    A returns to AVAILABLE
    A.cooldowns[B] = 3 (cannot re-propose for 3 ticks)

  If other action (implicit ignore):
    Proposal times out
    A returns to AVAILABLE (no cooldown)

  If co-location lost (B moved):
    Proposal expires
    A returns to AVAILABLE (no cooldown)

Tick T+1 (or T+2 if negotiation spans ticks): NEGOTIATE
  Bargaining protocol executes
  Duration: 1 tick (configurable later)

  If success:
    Trade outcome computed
    Proceed to EXECUTE

  If failure (no zone of agreement):
    Both return to AVAILABLE
    No cooldown (good faith negotiation)

  If co-location lost:
    Negotiation fails
    Both return to AVAILABLE

Tick T+2 (or T+3): EXECUTE
  Holdings update according to trade outcome
  Both return to AVAILABLE
  TradeEvent logged with exchange_id
```

### Timing Summary (Default Configuration)

| Event | Tick | Notes |
|-------|------|-------|
| A proposes | T | A enters PROPOSAL_PENDING |
| B responds | T+1 | Accept → both enter NEGOTIATING |
| Negotiation | T+1 | Same tick as acceptance (1 tick duration) |
| Trade executes | T+1 | Holdings update |

Minimum exchange duration: **2 ticks** (propose → accept+negotiate+execute)

With rejection: **1 tick wasted** + 3-tick cooldown before retry

### Co-location Requirement

**Strict throughout the sequence:**

- Proposal requires co-location to initiate
- Proposal expires if co-location lost before response
- Negotiation requires co-location; either agent moving causes failure
- Trade execution requires co-location

This makes **staying** a meaningful choice. Agents in PROPOSAL_PENDING or NEGOTIATING implicitly choose not to move (locked mode).

### Configuration Parameters

```python
@dataclass
class ExchangeConfig:
    proposal_timeout: int = 1          # Ticks before unanswered proposal expires
    proposal_locked: bool = True       # Proposer cannot act while waiting
    negotiation_duration: int = 1      # Ticks for negotiation phase
    rejection_cooldown: int = 3        # Ticks before can re-propose after rejection
    multiple_proposals: str = "exclusive"  # "exclusive" | "broadcast" (future)
```

For initial implementation:
- `proposal_timeout = 1` (configurable)
- `proposal_locked = True` (fixed, extend later)
- `negotiation_duration = 1` (fixed, extend later)
- `rejection_cooldown = 3` (fixed, extend later)
- `multiple_proposals = "exclusive"` (fixed, extend later)

---

## Consequences

### Enables

- **Transaction cost measurement:** Proposal costs 1 tick. Negotiation costs 1 tick. Rejection wastes 1 tick + 3 tick cooldown.
- **Protocol comparison:** Different protocols could have different negotiation durations (future extension).
- **Coordination failure analysis:** Can measure rejection rates, cooldown impact.
- **Strategic waiting:** Agents can choose to not propose (Wait action) if expected value is low.

### Transaction Cost Comparison Example

| Scenario | Ticks to Trade | Notes |
|----------|---------------|-------|
| Direct trade (current) | 1 | Instantaneous |
| Successful proposal | 2 | Propose + accept/negotiate/execute |
| Rejected, retry succeeds | 6 | Propose + reject + 3 cooldown + propose + accept |
| Two rejections, then success | 11 | Propose + reject + 3 + propose + reject + 3 + propose + accept |

### Requires

- **ADR-001 (Tick Model):** Three-phase tick structure with explicit actions.
- **ADR-002 (Interaction State):** Per-agent state machine tracking proposal/negotiation status.
- **Action types:** Propose, Accept, Reject as explicit actions.
- **Conflict resolution:** Handle multiple proposals to same target.

### Migration Impact

- **simulation.py:** Exchange logic moves from Phase 4 into Execute phase action dispatch.
- **bargaining.py:** Protocols still compute outcomes; now called during NEGOTIATING state.
- **search.py:** `should_trade()` becomes input to Accept decision, not automatic trade trigger.

---

## Conflict Resolution

### Multiple Proposals to Same Target

If agents A and C both propose to B in the same tick:

1. B evaluates both proposals (expected surplus)
2. B chooses one to Accept (highest surplus; ties by agent_id)
3. Non-selected proposal treated as "target unavailable" (not rejection)
4. Non-selected proposer returns to AVAILABLE, no cooldown

**Rationale:** B didn't reject; B was simply unavailable. No learning signal for A.

### Mutual Proposals

If A proposes to B **and** B proposes to A in same tick:

1. Detected during conflict resolution
2. Interpreted as mutual interest
3. Both skip PROPOSAL_PENDING, enter NEGOTIATING directly
4. Saves 1 tick (no waiting for response)

---

## References

- **Bargaining timing:** O&R Bargaining Ch 3-4 (alternating offers as multi-round game)
- **Transaction costs:** Coase (1937), Williamson (1985)
- **Search and matching:** Diamond-Mortensen-Pissarides (labor search; proposal/acceptance structure)

---

*Awaiting approval before implementation proceeds.*
