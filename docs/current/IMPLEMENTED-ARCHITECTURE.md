# Implemented Agent Architecture

**Date:** 2026-01-10
**Purpose:** Document the *currently implemented* agent architecture, distinct from the design vision in AGENT-ARCHITECTURE.md

This document describes what is actually built and working in the codebase, based on analysis of the implementation files.

---

## Overview

The implementation follows a **3-phase tick model** (Perceive → Decide → Execute) where agents are autonomous decision-makers with:
- Private state (true preferences/endowment)
- Observable type (what others see)
- Holdings (current goods, mutable)
- Interaction state machine
- Optional beliefs

---

## 1. Agent Structure (`agent.py`)

```
Agent
├── private_state: AgentPrivateState
│   ├── preferences: CobbDouglas(alpha)
│   └── endowment: Bundle (immutable, defines Nash disagreement point)
│
├── holdings: Bundle (mutable, updated by trades)
│
├── interaction_state: AgentInteractionState
│   ├── state: AVAILABLE | PROPOSAL_PENDING | NEGOTIATING
│   ├── proposal_target / negotiation_partner
│   └── cooldowns: {agent_id: ticks_remaining}
│
├── perception_radius: float
├── discount_factor: float (δ)
├── bargaining_power: float
├── movement_budget: int
│
├── opportunity_cost: float (set during Decide, used for acceptance)
│
└── Optional beliefs (memory, type_beliefs, price_belief)
```

### Key Design Decisions

| Decision | Implementation |
|----------|----------------|
| `endowment` vs `holdings` | Endowment is immutable disagreement point for Nash bargaining; holdings track current goods |
| `opportunity_cost` | Computed during Decide phase, stored in agent state, used in Execute for acceptance checks |
| Cooldowns | Per-partner: if B rejects A, A can't propose to B for 3 ticks |
| Beliefs | Architecturally present but behaviorally optional (agents work without them) |

---

## 2. Action Types (`actions.py`)

| Action | Cost | Purpose |
|--------|------|---------|
| `MoveAction(target_position)` | 1 | Move toward position |
| `ProposeAction(target_id, fallback)` | 1 | Initiate trade with adjacent agent |
| `WaitAction` | 1 | Do nothing |
| `AcceptAction` / `RejectAction` | — | **Not chosen during Decide** |

### Critical Insight

`AcceptAction`/`RejectAction` are **not** actions agents select during the Decide phase. Acceptance is an **institutional constraint** evaluated during Execute—the simulation checks if the target's surplus ≥ their opportunity cost.

### Fallback Mechanism

`ProposeAction` includes a pre-computed **fallback** (either `MoveAction` toward target or `WaitAction`). If the proposal fails, the proposer executes their fallback instead. This ensures failed proposals don't waste the agent's tick.

---

## 3. Tick Model (`simulation.py`)

```
PRE-TICK
├── Tick all cooldowns (decrement, remove expired)
└── Expire stale proposals/negotiations (adjacency lost)

PERCEIVE
├── Build frozen state snapshot
├── For each agent: evaluate all visible targets
│   └── SearchResult: best_target, discounted_value
└── Build ActionContext with positions, adjacencies, cooldowns

DECIDE
└── For each agent:
    ├── DecisionProcedure.choose(agent, context)
    │   ├── Enumerate: WaitAction, MoveAction(per visible target), ProposeAction(per adjacent)
    │   ├── Evaluate each action by expected utility
    │   ├── Store opportunity_cost = value of chosen action
    │   └── Attach fallback to ProposeAction if selected
    └── agent_actions[agent_id] = chosen action

EXECUTE
├── Step 1: Detect mutual proposals (A→B and B→A)
│   └── Both enter NEGOTIATING → trade → AVAILABLE
│
├── Step 2: Process non-mutual proposals (same-tick resolution)
│   ├── For each proposal:
│   │   ├── Check adjacency
│   │   ├── Target immediately decides: surplus >= opportunity_cost?
│   │   ├── Accept: trade executes, both → AVAILABLE
│   │   └── Reject: proposer gets cooldown, marked for fallback
│   └── Track: rejected_proposers, non_selected_proposers
│
├── Step 3: Execute fallbacks for failed proposals
│   └── rejected/non-selected proposers execute their fallback action
│
└── Step 4: Execute MoveActions (for agents that didn't trade/fallback)
```

---

## 4. Acceptance Logic (`decisions.py:443-460`)

When a target receives a proposal, acceptance is **deterministic** given their utility function:

```python
def evaluate_proposal(self, agent, proposer, context):
    surplus = bargaining_protocol.compute_expected_surplus(agent, proposer)
    return surplus >= agent.opportunity_cost
```

- `opportunity_cost` = discounted value of the target's chosen action (computed in Decide)
- If target was going to Wait, opportunity_cost = 0, so any positive surplus is accepted
- If target was moving toward a better partner, they'll reject mediocre proposals

---

## 5. Cooldown Rules

| Trigger | Cooldown? | Rationale |
|---------|-----------|-----------|
| Explicit rejection | Yes (3 ticks) | Target evaluated and said no |
| Implicit non-selection (target accepted another) | No | Not a rejection, just lost to competitor |
| Target unavailable | No | Bad timing, not rejection |

During cooldown, the target is **excluded from utility calculations** (`search.py:173-174`)—the agent won't even consider them when evaluating moves.

---

## 6. Search and Target Evaluation (`search.py`)

Agents evaluate potential trade partners by:

1. Find all agents within perception radius
2. Skip agents on cooldown
3. For each visible agent:
   - Get observable type (via information environment)
   - Compute expected surplus using bargaining protocol
   - Discount by δ^(ticks_to_reach)
4. Select target with maximum discounted value

The search integrates with the decision procedure—`MoveAction` values come from discounted surplus at destination.

---

## Scenario Walkthroughs

### Scenario 1: Two Agents, Mutual Interest (Immediate Trade)

**Setup:**
- Agent A: α=0.3, holdings=(8, 2), position=(2, 2)
- Agent B: α=0.7, holdings=(2, 8), position=(2, 3)
- Adjacent (Chebyshev distance = 1)

**Tick 1:**

| Phase | Agent A | Agent B |
|-------|---------|---------|
| **Perceive** | Sees B at (2,3), discounted_surplus = 2.5 | Sees A at (2,2), discounted_surplus = 2.5 |
| **Decide** | ProposeAction(B, fallback=Move(2,3)), opp_cost=2.5 | ProposeAction(A, fallback=Move(2,2)), opp_cost=2.5 |
| **Execute** | Mutual proposal detected | Mutual proposal detected |
|  | Both → NEGOTIATING | Both → NEGOTIATING |
|  | Nash bargaining executes | Trade occurs |
|  | A: (6.0, 5.0), B: (4.0, 5.0) | Both → AVAILABLE |

**Outcome:** Trade happens immediately. No cooldowns needed.

---

### Scenario 2: Three Agents, Competition for Target

**Setup:**
- Agent A: α=0.3, holdings=(8, 2), position=(2, 2)
- Agent B: α=0.7, holdings=(2, 8), position=(2, 3) — target
- Agent C: α=0.5, holdings=(5, 5), position=(2, 4)
- A and C both adjacent to B

**Tick 1:**

| Phase | Agent A | Agent B | Agent C |
|-------|---------|---------|---------|
| **Perceive** | Best: B (surplus=2.5) | Best: A (surplus=2.5) | Best: B (surplus=0.8) |
| **Decide** | ProposeAction(B), opp_cost=2.5 | ProposeAction(A), opp_cost=2.5 | ProposeAction(B), opp_cost=0.8 |

**Execute phase resolution:**
1. **Mutual proposals:** A→B and B→A detected. They trade immediately.
2. **C's proposal:** C proposed to B, but B already traded with A (is in `traded_this_tick`).
3. **C outcome:** Implicit non-selection → C executes fallback (Move toward B), **no cooldown**.

**Tick 2:**
- C is now at (2,3) with B
- C can propose to B again (no cooldown!)

---

### Scenario 3: Rejection and Cooldown

**Setup:**
- Agent A: α=0.3, holdings=(8, 2), position=(2, 2)
- Agent B: α=0.7, holdings=(2, 8), position=(2, 3)
- Agent D: α=0.9, holdings=(1, 15), position=(2, 5) — B's preferred partner

**Tick 1:**

| Phase | Agent A | Agent B |
|-------|---------|---------|
| **Perceive** | Best: B (surplus=2.5, δ¹) | Best: D (surplus=4.0, δ²=0.9² ×4.0=3.24) |
| **Decide** | ProposeAction(B), opp_cost=2.5 | MoveAction(2,5), opp_cost=3.24 |
| **Execute** | A proposes to B | B evaluates: surplus(A)=2.5 vs opp_cost=3.24 |
|  | | **2.5 < 3.24 → REJECT** |
|  | Cooldown(B, 3 ticks) | Executes Move toward D |
|  | Executes fallback: Move(2,3) | |

**Result:**
- A moves to (2,3), but gets 3-tick cooldown for B
- B moves to (2,4), heading toward D
- A can't propose to B until tick 4

**Tick 2:**
- A evaluates targets: B is in cooldowns, **excluded from search**
- A sees other agents (if any) or waits

---

### Scenario 4: Four Agents, Complex Coordination

**Setup:**
- A: α=0.2, (10, 0), position=(0, 0)
- B: α=0.8, (0, 10), position=(0, 1) — adjacent to A
- C: α=0.3, (8, 2), position=(3, 3)
- D: α=0.7, (2, 8), position=(3, 4) — adjacent to C

**Tick 1:**

All agents see each other (assume large perception radius).

| Agent | Best Target | Chosen Action | Opp Cost |
|-------|-------------|---------------|----------|
| A | B (adjacent, surplus=3.2) | ProposeAction(B) | 3.2 |
| B | A (adjacent, surplus=3.2) | ProposeAction(A) | 3.2 |
| C | D (adjacent, surplus=2.1) | ProposeAction(D) | 2.1 |
| D | C (adjacent, surplus=2.1) | ProposeAction(C) | 2.1 |

**Execute:**
1. Mutual proposals: {A,B} and {C,D}
2. Both pairs trade simultaneously
3. All agents → AVAILABLE

**Outcome:** Two trades occur in parallel. The simulation correctly handles independent bilateral exchanges.

---

## Differences from Design Document

| Aspect | Design Doc (AGENT-ARCHITECTURE.md) | Implementation |
|--------|-----------------------------------|----------------|
| Metabolism | Defined (Bundle, for Phase B+) | Not implemented (None always) |
| StoredHoldings | Defined | Not implemented |
| Negotiation duration | "Protocol-specific (1+ ticks)" | Always 1 tick (immediate) |
| Accept/Reject as actions | Listed as action types | Institutional constraint, not agent choice |
| Action budget cost | Trade=1, Move=1, coordination=free | Move=1, Propose=1 (effectively trade=1 per party) |
| Multilateral exchange | Extension point identified | Not implemented |
| Endogenous action budgets | Mentioned | Not implemented |

The implementation has focused on **Phase A** (static equilibrium) with same-tick proposal resolution. The design document's multi-tick negotiation and metabolism features are architectural placeholders for Phase B+.

---

## File References

| File | Key Components |
|------|----------------|
| `microecon/agent.py` | Agent, AgentPrivateState, AgentType, AgentInteractionState |
| `microecon/actions.py` | Action ABC, MoveAction, ProposeAction, WaitAction, ActionContext |
| `microecon/decisions.py` | DecisionProcedure, RationalDecisionProcedure, DecisionContext |
| `microecon/simulation.py` | Simulation, step(), _execute_actions(), _execute_trade() |
| `microecon/search.py` | evaluate_targets_detailed(), SearchResult, TargetEvaluationResult |

---

**Document Version:** 1.0
**Created:** 2026-01-10
**Based on commits:** 99557e4 (FEAT-009) and prior
