# Design Document: Matching Protocol Abstraction

**Date:** 2026-01-02
**Status:** Revised (Phase 1 complete, Phase 2 refined)
**Addresses:** Trading chain path-crossing design question (see SESSION_REVIEW_2026_01_01_trading_chain.md)

**Revision Note (2026-01-02):** Design discussion refined the tick structure to four explicit phases (Evaluate → Decide → Move → Exchange) with clarified semantics for both committed and opportunistic modes. Phase 1 implementation is complete; this revision informs Phase 2 integration.

---

## 1. Problem Statement

The trading chain scenario surfaced a fundamental design question:

> **Scenario:** A is moving toward B. D is also moving toward B. A and D cross paths.

| Behavior | Description |
|----------|-------------|
| **Opportunistic** | A trades with D when they meet, even though A was heading to B |
| **Committed** | A continues to B, ignores D en route |

Both behaviors are economically defensible. The trading sequence and emergent outcomes differ substantially depending on this choice.

### Current Behavior

Opportunistic: agents trade with whoever they're co-located with, regardless of who they were targeting. This is implicit—there's no explicit matching phase, just spatial co-location enabling exchange.

---

## 2. Design Decision

**Make matching an explicit institutional variable** via a new `MatchingProtocol` abstraction, parallel to `BargainingProtocol`.

This aligns with VISION.md's core insight:

> Search and matching (random, directed, algorithmic) become visible mechanisms

The research question extends: *Same preferences, same endowments, same bargaining protocol—different matching rules. What emerges?*

---

## 3. The Two Modes

### 3.1 Opportunistic Matching (Current Behavior)

- No explicit matching phase
- Any co-located agents can trade
- Trade partner selection from co-located set (lexicographic tie-breaking)
- Simple, baseline behavior

### 3.2 Committed Matching (New)

- Explicit matching phase forms **committed pairs**
- Only mutually committed + co-located agents can trade
- Uncommitted agents cannot trade, even if co-located with potential partners
- Creates distinct emergent dynamics

---

## 4. Committed Mode Specification

### 4.1 Matching Algorithm: Irving's Stable Roommates

**Why not Gale-Shapley?** Gale-Shapley requires two-sided markets (proposers/acceptors). Our bilateral exchange is one-sided—any agent can match with any other. This is the **stable roommates problem** (Irving 1985).

**Irving's Algorithm:**
- Finds stable matching if one exists (no blocking pairs)
- Polynomial time O(n²)
- May fail to find stable matching in some configurations
- Theoretically grounded, well-documented

**Future alternatives** (not implemented now):
- Maximum weight matching (efficiency-maximizing)
- Random matching (baseline comparison)
- Serial dictatorship (strategy-proof)

### 4.2 Matching Constraints

| Constraint | Details |
|------------|---------|
| **Perception-constrained** | Can only match with agents within perception radius |
| **Surplus-discounted preferences** | Preference ranking by distance-discounted bilateral surplus (consistent with existing search) |

### 4.3 Commitment Lifecycle

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
    ┌───────────────────────────┐                        │
    │       UNCOMMITTED         │                        │
    │  (participates in match)  │                        │
    └───────────────────────────┘                        │
              │                                          │
              │ Irving's algorithm                       │
              │ finds mutual match                       │
              ▼                                          │
    ┌───────────────────────────┐                        │
    │        COMMITTED          │──── partner exits ─────┘
    │   (skips match phase)     │     perception radius
    │   (moves toward partner)  │
    └───────────────────────────┘
              │
              │ co-located +
              │ successful trade
              ▼
    ┌───────────────────────────┐
    │   TRADE EXECUTED          │
    │   (both → UNCOMMITTED)    │
    └───────────────────────────┘
```

**Formation:** Irving's algorithm on uncommitted agents, constrained by perception

**Persistence:** Until successful trade OR partner leaves perception radius

**Breaking conditions:**
1. Successful trade with committed partner
2. Partner exits perception radius

### 4.4 Agent Behavior by State

**Under Committed Mode:**

| State | Decide Phase | Movement | Can Trade? |
|-------|--------------|----------|------------|
| **Uncommitted** | Participates in Irving's | Toward fallback target | No |
| **Committed** | Skips (has partner) | Toward committed partner | Yes (if co-located with partner) |
| **Unmatched** | Attempted Irving's, no match | Toward best visible target | No |

**Under Opportunistic Mode:**

| State | Decide Phase | Movement | Can Trade? |
|-------|--------------|----------|------------|
| **All agents** | Select best surplus target | Toward selected target | Yes (if co-located with anyone) |

Note: Under opportunistic mode, there is no "committed" or "unmatched" state—all agents follow the same logic.

### 4.5 Tick Structure

The simulation tick has four phases:

```
Each Tick:
1. EVALUATE PHASE
   - All agents observe visible others (within perception radius)
   - Compute surplus rankings for visible agents
   - Information gathering—no decisions yet

2. DECIDE PHASE
   Semantics depend on matching protocol:

   Committed mode:
   - Committed agents: skip (already have partner)
   - Uncommitted agents: run Irving's on visible subgraph
   - Result: some form commitments, some remain unmatched
   - Unmatched agents select fallback targets

   Opportunistic mode:
   - All agents select movement targets (best surplus partner)
   - No commitments formed
   - Target guides movement but does not gate trade

3. MOVE PHASE
   - Committed: move toward committed partner
   - Opportunistic/Unmatched: move toward selected target

4. EXCHANGE PHASE
   - Committed mode: only committed + co-located pairs trade
   - Opportunistic mode: any co-located pairs trade
   - After trade, endowments change—target re-evaluation
     happens at start of next tick's Evaluate phase
```

**Key insight:** The Decide phase has dual semantics:
- Under committed protocols: forms binding commitments that gate trade
- Under opportunistic protocols: selects targets that guide movement (trade ungated)

### 4.6 Edge Cases

| Case | Handling |
|------|----------|
| **Odd number of agents** | One agent unmatched, uses fallback behavior |
| **No stable matching exists** | Irving's algorithm fails; all agents use fallback |
| **No visible partners** | Agent is unmatched, random walk or stay put |
| **Partner exits perception after commitment** | Commitment breaks, rejoin matching pool |

---

## 5. Architecture

### 5.1 New Abstraction: MatchingProtocol

```python
from abc import ABC, abstractmethod
from typing import List, Tuple, Set
from microecon.agent import Agent

class MatchingProtocol(ABC):
    """
    Determines how agents form trading pairs.

    Parallel to BargainingProtocol—an institutional variable
    that affects emergent market outcomes.
    """

    @abstractmethod
    def compute_matches(
        self,
        agents: List[Agent],
        visibility: Dict[str, Set[str]],  # agent_id -> visible agent_ids
        surplus_fn: Callable[[Agent, Agent], float]
    ) -> List[Tuple[str, str]]:
        """
        Compute committed pairs for this tick.

        Args:
            agents: All agents in simulation
            visibility: Which agents each agent can see
            surplus_fn: Function computing bilateral surplus

        Returns:
            List of (agent_id, agent_id) committed pairs
        """
        pass

    @property
    @abstractmethod
    def requires_mutual_commitment(self) -> bool:
        """Whether trade requires explicit mutual commitment."""
        pass
```

### 5.2 Implementations

```python
class OpportunisticMatchingProtocol(MatchingProtocol):
    """
    Current behavior: no explicit matching, any co-located pair can trade.
    """

    def compute_matches(self, agents, visibility, surplus_fn):
        return []  # No pre-committed pairs; matching is implicit via co-location

    @property
    def requires_mutual_commitment(self) -> bool:
        return False


class StableRoommatesMatchingProtocol(MatchingProtocol):
    """
    Irving's stable roommates algorithm.
    Forms committed pairs with no blocking pairs (when solution exists).
    """

    def compute_matches(self, agents, visibility, surplus_fn):
        # Build preference lists from surplus_fn
        # Run Irving's algorithm
        # Return stable matching (or partial if no stable solution)
        ...

    @property
    def requires_mutual_commitment(self) -> bool:
        return True
```

### 5.3 Integration with Simulation

```python
class Simulation:
    def __init__(
        self,
        ...,
        matching_protocol: MatchingProtocol = OpportunisticMatchingProtocol(),
        bargaining_protocol: BargainingProtocol = NashBargainingProtocol(),
    ):
        self.matching_protocol = matching_protocol
        self.bargaining_protocol = bargaining_protocol
        self._commitments: Dict[str, str] = {}  # agent_id -> committed_partner_id
```

### 5.4 Commitment State

New agent state for tracking commitments:

```python
# In Simulation or separate CommitmentTracker
@dataclass
class CommitmentState:
    committed_pairs: Set[Tuple[str, str]]  # Frozenset of committed pairs

    def is_committed(self, agent_id: str) -> bool:
        ...

    def get_partner(self, agent_id: str) -> Optional[str]:
        ...

    def form_commitment(self, agent_a: str, agent_b: str):
        ...

    def break_commitment(self, agent_a: str, agent_b: str):
        ...
```

---

## 6. Implementation Plan

### Phase 1: Core Abstraction (Minimal)

1. **Add `MatchingProtocol` ABC** to new file `src/microecon/matching.py`
2. **Implement `OpportunisticMatchingProtocol`** (wraps current behavior)
3. **Add `matching_protocol` parameter to `Simulation`**
4. **Verify all existing tests pass** (opportunistic is default)

### Phase 2: Tick Structure Integration

Modify `Simulation.step()` to implement the four-phase tick structure:

1. **EVALUATE phase:**
   - Compute visible agents for each agent (within perception radius)
   - Calculate surplus rankings for visible partners
   - Store rankings for use in Decide phase

2. **DECIDE phase:**
   - If `matching_protocol.requires_commitment`:
     - Committed agents: skip
     - Uncommitted agents: run `matching_protocol.compute_matches()`
     - Form new commitments via `CommitmentState`
     - Unmatched agents select fallback targets
   - If opportunistic:
     - All agents select best surplus target (no commitments)

3. **MOVE phase:**
   - Committed agents: move toward committed partner
   - Others: move toward selected target

4. **EXCHANGE phase:**
   - If `matching_protocol.requires_commitment`:
     - Only committed + co-located pairs execute bargaining
   - If opportunistic:
     - Any co-located pairs execute bargaining
   - Break commitments after successful trades

5. **Commitment maintenance:**
   - At start of tick (before Evaluate): check perception radius
   - Break commitments when partner exits visibility

### Phase 3: Testing

1. **Unit tests for Irving's algorithm**
   - Known stable solutions
   - No-solution cases
   - Odd-agent cases

2. **Update trading chain tests**
   - Remove `@pytest.mark.skip`
   - Add variants for both matching protocols
   - Verify different emergent behaviors

3. **New scenario tests**
   - Committed mode hub-and-spoke
   - Perception radius commitment breaking
   - Path-crossing behavior verification

### Phase 4: Logging & Analysis

1. **New event types:**
   - `CommitmentFormed(tick, agent_a, agent_b)`
   - `CommitmentBroken(tick, agent_a, agent_b, reason)`
   - `MatchingPhaseResult(tick, pairs, unmatched)`

2. **Analysis extensions:**
   - Commitment duration statistics
   - Match failure frequency
   - Comparison: opportunistic vs committed outcomes

---

## 7. Future Extensions (Not Now)

Documented for future reference, not part of current implementation:

| Extension | Description |
|-----------|-------------|
| **Alternative algorithms** | Max-weight matching, random matching, serial dictatorship |
| **Alternative breaking conditions** | Timeout-based, trade-away detection |
| **Alternative fallback behaviors** | Stay put, random walk, second-best cascade |
| **Explicit commitment mechanisms** | Contracts, deposits, reputation systems |
| **Configurable matching frequency** | Every N ticks rather than every tick |

---

## 8. Rationale Summary

### Why MatchingProtocol Abstraction?

1. **Institutional visibility**: Makes matching rules explicit and comparable (VISION.md core principle)
2. **Research value**: Enables studying how matching institutions affect outcomes
3. **Extensibility**: Clean abstraction for future matching algorithms
4. **Consistency**: Parallel structure to BargainingProtocol

### Why Irving's Stable Roommates?

1. **Theoretical grounding**: Well-studied algorithm with stability guarantee
2. **One-sided markets**: Correct algorithm for our setting (not Gale-Shapley)
3. **Published literature**: Irving 1985, extensive follow-up work
4. **Real-world relevance**: Kidney exchange, roommate assignment

### Why Perception-Constrained + Surplus-Discounted?

1. **Consistency**: Matches existing search behavior
2. **Spatial grounding**: Respects the grid as meaningful (VISION.md §4)
3. **Economic intuition**: Distance matters for matching, not just exchange

---

## 9. Open Questions

1. **Irving's algorithm library**: Implement from scratch or use existing package?
2. **Partial matching**: When no stable solution exists, what partial matching to return?
3. **Visualization**: How to show commitment status in the UI?
4. **Performance**: Irving's is O(n²)—acceptable for expected agent counts?

---

## 10. References

- Irving, R.W. (1985). "An efficient algorithm for the stable roommates problem." *Journal of Algorithms* 6(4): 577-595.
- VISION.md §4 (Spatial Grounding), §5 (Research Agenda)
- SESSION_REVIEW_2026_01_01_trading_chain.md (problem statement)
- Roth, A.E. (2008). "Deferred acceptance algorithms: history, theory, practice." *International Journal of Game Theory* 36(3): 537-569.

---

**Document Version:** 1.1
**Authors:** Discussion session 2026-01-02
**Revised:** 2026-01-02 (tick structure refinement)
