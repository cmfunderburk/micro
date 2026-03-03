# ADR-002: Multi-State Interaction Machine

**Status:** Proposed
**Created:** 2026-01-09
**Theoretical Basis:** O&R Bargaining Ch 3-4 (alternating offers); mechanism design (commitment, timing)

---

## Context

The current implementation uses `CommitmentState` in `matching.py`:

```python
class CommitmentState:
    """Tracks mutual commitments between agent pairs."""
    _committed_pairs: set[frozenset[str]]
```

This is binary: agents are either committed to one partner or uncommitted. Problems:

1. **No proposal waiting.** Agents can't "propose and wait for response." Trade either happens this tick or doesn't.

2. **No rejection tracking.** When trade doesn't happen, there's no record of why, and no cooldown preventing immediate re-proposal.

3. **No negotiation state.** Bargaining executes instantly. Can't model multi-round negotiation or protocol-specific durations.

4. **Simulation-level, not agent-level.** CommitmentState is a simulation property, not agent property. Can't have per-agent interaction rules.

The AGENT-ARCHITECTURE.md specifies richer interaction semantics (§7.7) to enable multi-tick exchanges and explicit transaction costs.

---

## Decision

Replace binary CommitmentState with per-agent InteractionState machine:

```python
class InteractionState(Enum):
    AVAILABLE = "available"
    PROPOSAL_PENDING = "proposal_pending"
    NEGOTIATING = "negotiating"

@dataclass
class AgentInteractionState:
    state: InteractionState = InteractionState.AVAILABLE

    # If PROPOSAL_PENDING
    proposal_target: str | None = None
    proposal_tick: int | None = None

    # If NEGOTIATING
    negotiation_partner: str | None = None
    negotiation_protocol: BargainingProtocol | None = None
    negotiation_start_tick: int | None = None

    # Orthogonal to state
    rejection_cooldowns: dict[str, int] = field(default_factory=dict)
```

### State Semantics

**AVAILABLE:**
- Can propose to others (subject to cooldowns)
- Can receive and respond to proposals
- Can take other actions (Move, Wait)

**PROPOSAL_PENDING:**
- Has outbound proposal awaiting response
- Target specified in `proposal_target`
- **Locked mode (default):** Cannot take other actions until resolved
- Can receive proposals from others; accepting withdraws own pending proposal
- Transitions on: target accepts, target rejects, timeout (1 tick), co-location lost

**NEGOTIATING:**
- In active negotiation with `negotiation_partner`
- Cannot take other actions
- Cannot receive new proposals
- Duration: 1 tick (fixed for now; extensible later)
- Transitions on: protocol completes (success or failure), co-location lost

### Cooldowns

```python
rejection_cooldowns: dict[str, int]  # agent_id → ticks remaining
```

- Created when own proposal is rejected: `cooldowns[target] = 3`
- Decremented each tick
- Removed when reaches 0
- Agent cannot propose to target while cooldown active
- **Reason:** Prevents futile re-proposal spam; models learning from rejection

### State Transitions

| From | To | Trigger |
|------|-----|---------|
| AVAILABLE | PROPOSAL_PENDING | Agent chooses Propose(target) action |
| AVAILABLE | NEGOTIATING | Received proposal, chose Accept action |
| PROPOSAL_PENDING | NEGOTIATING | Target accepted |
| PROPOSAL_PENDING | AVAILABLE | Target rejected (+ cooldown added) |
| PROPOSAL_PENDING | AVAILABLE | Timeout (1 tick, no cooldown) |
| PROPOSAL_PENDING | AVAILABLE | Co-location lost (no cooldown) |
| PROPOSAL_PENDING | NEGOTIATING | Received proposal from C, chose Accept (withdraws own proposal) |
| NEGOTIATING | AVAILABLE | Protocol completes (trade succeeds or fails) |
| NEGOTIATING | AVAILABLE | Co-location lost (negotiation fails) |

### Mutual Proposal Detection

If A proposes to B **and** B proposes to A in the same tick:
- Detected during conflict resolution (Execute phase)
- Both transition directly to NEGOTIATING with each other
- No waiting period needed

---

## Consequences

### Enables

- **Multi-tick exchanges:** Proposal → response → negotiation → trade spans multiple ticks.
- **Transaction cost measurement:** Can count ticks from proposal to completion.
- **Coordination failure visibility:** Rejections tracked, cooldowns visible.
- **Per-agent interaction rules:** Each agent has own state, not shared simulation state.

### Requires

- **Agent attribute:** Add `interaction_state: AgentInteractionState` to Agent class.
- **Remove CommitmentState:** Delete from matching.py and all references in simulation.py.
- **Transition logic:** Execute phase must update interaction states based on actions.
- **Co-location validation:** Must check co-location persists throughout exchange sequence.

### Migration Impact

- **agent.py:** Add InteractionState to Agent.
- **matching.py:** Remove CommitmentState class; OpportunisticMatching continues to work (just checks co-location).
- **simulation.py:** Remove commitment tracking; add interaction state updates in Execute phase.

---

## Alternatives Considered

### Keep CommitmentState, Add States

Could extend CommitmentState with pending/negotiating tracking at simulation level.

**Rejected:** Maintains wrong ownership model. Interaction state should be per-agent, enabling heterogeneous rules.

### Implicit State via Action History

Could derive interaction state from recent actions rather than storing explicitly.

**Rejected:** More complex, harder to validate invariants, harder to serialize for logging.

---

## References

- **Alternating offers:** O&R Bargaining Ch 3-4 (multi-round negotiation structure)
- **Finite automata for protocol state:** Standard in distributed systems and mechanism design
- **Commitment in bargaining:** Schelling (1960) "The Strategy of Conflict"

---

*Awaiting approval before implementation proceeds.*
