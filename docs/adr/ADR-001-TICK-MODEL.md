# ADR-001: Three-Phase Tick Model

**Status:** Proposed
**Created:** 2026-01-09
**Theoretical Basis:** Simultaneous-move game theory; Coase (1937), Williamson (1985) on transaction costs

---

## Context

The current simulation uses a four-phase tick loop:

```
Phase 1: EVALUATE - Each agent computes surplus for visible targets
Phase 2: DECIDE - Matching protocol runs, movement targets set
Phase 3: MOVE - Agents move toward targets
Phase 4: EXCHANGE - Co-located pairs trade instantly
```

This structure has several problems:

1. **Actions are implicit, not explicit.** Movement happens automatically toward "best target." Trade happens automatically if `should_trade()` returns true. Agents don't choose actions; the simulation imposes behavior.

2. **Exchange is instantaneous.** Co-located agents trade within a single tick. This obscures negotiation costs and makes transaction cost comparison impossible.

3. **Phase logic is hardcoded.** Adding new action types (Gather, Produce, Wait) requires restructuring the tick loop.

4. **Categories drive structure.** The phases encode assumptions about what agents do (evaluate, then move, then trade) rather than letting agent decision-making determine behavior.

The VISION.md core insight is **institutional visibility**—making transaction costs explicit and comparable. The current tick model obscures these costs.

---

## Decision

Replace the four-phase tick loop with a three-phase model:

```
Phase 1: PERCEIVE
  - All agents observe frozen state_t (simultaneous snapshot)
  - Perception radius and information environment apply
  - No agent sees another's pending decision

Phase 2: DECIDE
  - All agents select ONE action from available_actions()
  - DecisionProcedure.choose() executes for each agent
  - Decisions are simultaneous; no agent observes another's choice

Phase 3: EXECUTE
  - Conflict resolution (multiple proposals to same target, etc.)
  - All actions execute against state_t
  - State changes combine to produce state_t+1
  - Validation (non-negative holdings, valid positions)
```

### Key Properties

**Simultaneous decision:** All agents decide based on the same frozen state. This is standard simultaneous-move game structure, enabling clean theoretical analysis.

**Explicit action selection:** Agents choose from an enumerated action set, not implicit behavior. Each action has preconditions, costs, and effects.

**Batched execution:** Actions don't resolve sequentially by agent. State changes are computed for all actions, then applied atomically. Execution order by agent_id is deterministic but shouldn't affect outcomes.

**No category hierarchy:** The tick loop doesn't know about "movement phase" vs "exchange phase." It asks each agent for an action, executes all actions, done. Categories exist as action metadata (tags), not structural phases.

---

## Consequences

### Enables

- **Transaction costs as ticks:** Proposal costs 1 tick. Negotiation costs 1+ ticks. These become measurable.
- **Extensible actions:** Adding Gather, Produce, Wait is defining new Action types, not restructuring phases.
- **Sophistication as variable:** Different DecisionProcedures can evaluate the same action space differently.
- **Protocol comparison:** Same economy under different protocols has different tick costs, directly observable.

### Requires

- **Action interface:** Must define Action ABC with type, cost(), preconditions(), transform().
- **DecisionProcedure interface:** Must define how agents choose among available actions.
- **Conflict resolution logic:** Multiple proposals to same target, mutual proposals, crossing paths.
- **InteractionState tracking:** Proposals and negotiations span ticks; state must persist. (See ADR-002)

### Migration Impact

- **simulation.py:** Complete rewrite of tick() method.
- **search.py:** Becomes input to DecisionProcedure, not driver of behavior.
- **matching.py:** CommitmentState removed; replaced by InteractionState.
- **Tests:** Many will break; accept temporary breakage.

---

## Alternatives Considered

### Keep Four-Phase, Add Action Choice Within

Could add action selection within existing phases (e.g., Phase 2 includes "decide to trade or not").

**Rejected:** Maintains implicit structure. Doesn't cleanly separate perception from decision from execution. Makes multi-tick exchanges awkward.

### Event-Driven Without Tick Structure

Could use pure event-driven model where agents act asynchronously.

**Rejected:** Loses simultaneous-move game structure. Harder to reason about theoretically. Introduces ordering dependencies.

---

## References

- **Simultaneous-move games:** Any game theory text (O&R Game Theory Ch 2-3)
- **Transaction costs:** Coase (1937) "The Nature of the Firm"; Williamson (1985) "The Economic Institutions of Capitalism"
- **Agent-based tick models:** Standard in ABM literature; ensures reproducibility via deterministic execution

---

*Awaiting approval before implementation proceeds.*
