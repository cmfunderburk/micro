# GPT Agent Architecture Discussion (Current Implementation)

## Recent commit context (last 5)
- 99557e4 feat: Add edge case tests for action budget model (FEAT-009)
- 889692f feat: Add scenario tests for action budget model (FEAT-008)
- 116f32d feat: Add theory verification tests for action budget model (FEAT-007)
- d2d219b feat(search): Exclude cooldown targets from search (FEAT-006)
- 81cde5f feat(simulation): Execute fallback on proposal failure (FEAT-005)

These commits clarify and lock in the action-budget tick model behavior
(fallbacks, cooldowns, same-tick coordination) and enforce cooldown-aware
search. The codebase now reflects those mechanics, with tests covering
edge cases, theory constraints, and end-to-end scenarios.

---

## Current implemented architecture (big picture)

### 1) Core agent model
Agents are defined in `microecon/agent.py` with a strict separation between
private state, observable type, and mutable holdings:
- `AgentPrivateState`: true preferences and endowment. Endowment is immutable
  and defines the disagreement point for bargaining.
- `AgentType`: observable type constructed by an information environment.
  In full information, type mirrors preferences and current holdings.
- `Agent`: the runtime entity with holdings, interaction state, search params,
  movement budget, discount factor, and optional belief system.

Key characteristics that are implemented now:
- Preferences: only Cobb-Douglas is implemented (`microecon/preferences.py`).
- Goods space: exactly two goods, represented by `Bundle(x, y)`.
- Holdings vs endowment: holdings are mutable and are what bargaining
  protocols operate on; endowment is immutable and only used as the
  disagreement point reference.
- Time preference: `discount_factor` is used for distance discounting in
  search/decision evaluation and for Rubinstein bargaining weights.
- Bargaining power: `bargaining_power` exists for the asymmetric Nash protocol.
- Spatial agency: agents have `perception_radius` and `movement_budget`.

### 2) Interaction state and cooldowns
An explicit interaction state machine exists (`AgentInteractionState`), with
states `AVAILABLE`, `PROPOSAL_PENDING`, and `NEGOTIATING`, plus per-partner
cooldowns. In the current simulation loop:
- `AVAILABLE` and `NEGOTIATING` are used.
- `PROPOSAL_PENDING` exists but is not reached because proposals are resolved
  within the same tick.
- Cooldowns are real: explicit rejection adds a 3-tick cooldown to the proposer.
- Cooldowns tick down each tick in `_pre_tick_maintenance()`.

### 3) Tick model: Perceive -> Decide -> Execute
The simulation (`microecon/simulation.py`) runs a three-phase tick:

1) PERCEIVE
- A frozen snapshot is built.
- Visibility is computed via `evaluate_targets_detailed()` in `microecon/search.py`.
- Visibility is controlled by the information environment and perception radius.
- Cooldown targets are excluded from visibility-based evaluation (FEAT-006).

2) DECIDE
- Each agent selects exactly one action via a `DecisionProcedure`.
- Current default: `RationalDecisionProcedure`.
- Actions include `Wait`, `Move`, and `Propose`.
- Proposal acceptance is NOT decided here (see Execute).
- The chosen action's value is stored as the agent's `opportunity_cost`.

3) EXECUTE
- Proposals are coordinated and resolved within the same tick.
- Trades happen immediately if accepted.
- Agents who trade do not also move (trade consumes the action for both parties).
- Failed proposals execute their pre-computed fallback actions.

### 4) Decision procedure (Rational baseline)
`RationalDecisionProcedure` is the only implemented procedure. It:
- Enumerates actions: `Wait`, `Move` toward visible agents, `Propose` to adjacent
  agents. Accept/Reject are not enumerated.
- Evaluates actions using expected surplus from the current bargaining protocol.
- Discounts move value by distance: `delta ** distance`.
- Uses deterministic tie-breaking with action-type priorities.
- Stores `opportunity_cost` on the agent for later acceptance checks.
- Attaches a fallback to each `ProposeAction`:
  - If co-located, fallback is `Wait`.
  - If adjacent, fallback is `Move` toward target.

### 5) Action budget model (as implemented)
The action budget model is enforced by the structure of the tick:
- Each agent chooses exactly one action per tick.
- Trade execution consumes that action for both parties, so no movement occurs
  for those agents in the same tick.
- Coordination (propose/accept/reject) is effectively free because acceptance
  happens inside Execute and does not replace the chosen action; it only
  overrides it if the trade is accepted.
- `Action.cost()` exists but is not currently used in the simulation loop.

Important implemented details:
- Proposals can be made to adjacent agents (Chebyshev distance <= 1), not only
  co-located agents. This is a deliberate deviation from strict co-location to
  avoid oscillation.
- Mutual proposals are detected and resolved first (direct trade, no pending).
- Non-mutual proposals are processed in iteration order; the first acceptable
  proposal to a target wins. There is no surplus-maximization across competing
  proposals in the current implementation.

### 6) Acceptance logic and opportunity cost
Acceptance is implemented as an institutional constraint in Execute:
- The target evaluates whether `surplus >= opportunity_cost`.
- `opportunity_cost` is set during Decide, based on the chosen action.
- The surplus calculation uses the bargaining protocol and current holdings.

Note: acceptance currently uses full information about agent types. It does not
use noisy observations or beliefs during the acceptance decision.

### 7) Search, visibility, and information environments
Search is used for perception and logging, not direct action selection:
- `evaluate_targets_detailed()` uses the information environment and (optional)
  beliefs to compute target evaluations and visibility.
- The decision procedure uses visibility filtering, but uses true agent
  characteristics to compute surplus.

Information environments implemented:
- `FullInformation`: type = true preferences + current holdings.
- `NoisyAlphaInformation`: noisy alpha, true holdings; primarily affects logging
  and belief updates.
- `PrivateInformation`: placeholder, raises NotImplementedError.

### 8) Bargaining protocols
Bargaining is protocol-driven (`microecon/bargaining.py`):
- `NashBargainingProtocol`: symmetric Nash solution (default).
- `RubinsteinBargainingProtocol`: BRW limit, asymmetry from discount factors.
- `TIOLIBargainingProtocol`: proposer takes all surplus; proposer selected by
  lexicographic ID unless specified.
- `AsymmetricNashBargainingProtocol`: bargaining power from `bargaining_power`.

All protocols:
- Operate on current holdings (not endowment).
- Provide `compute_expected_surplus()` for search/decision evaluation.
- Use `select_proposer()` to pick a proposer during execution.

### 9) Beliefs and memory
Beliefs exist and are fully implemented but are optional:
- Agents must call `enable_beliefs()` to activate memory and beliefs.
- After each trade, `record_trade_observation()` logs memory and updates beliefs.
- Beliefs can influence search evaluation (in `evaluate_targets*`) but are not
  currently used by the decision procedure when selecting actions.

### 10) Logging and analysis surfaces
The simulation can attach a `SimulationLogger` to record:
- Agent snapshots (position, holdings, utility, belief presence).
- Search decision evaluations (for analysis of search choices).
- Movement events and trade events.
- Belief snapshots for agents with beliefs enabled.

### 11) Notable deltas vs AGENT-ARCHITECTURE.md
These are the key mismatches between the design doc and current code:
- Proposals can target adjacent agents, not only co-located agents.
- `PROPOSAL_PENDING` is not used; proposals resolve in the same tick.
- Competing proposals to the same target are not compared by surplus. The
  current resolution is order-based (first acceptable proposal wins).
- No multi-tick negotiation; `NEGOTIATING` is entered only briefly and trade
  executes immediately in the same tick.
- Action costs are defined on actions but not enforced; the model is effectively
  "one action per tick" without variable budgets or zero-cost waiting.
- Acceptance and decision evaluation use true agent types rather than noisy
  observations, so noisy information currently affects logging and beliefs
  more than actual decision-making.

---

## Scenario walkthroughs (2-4 agents)

### Scenario 1: 2 agents, co-located, mutual proposal and trade
Agents:
- A: alpha=0.3, endowment (10, 2)
- B: alpha=0.7, endowment (2, 10)
- Both at Position(5, 5)

Tick flow:
1) PERCEIVE
- Each sees the other (within perception radius).
- Both have positive expected surplus from Nash bargaining.

2) DECIDE
- A chooses `Propose(B)` with fallback `Wait` (co-located).
- B chooses `Propose(A)` with fallback `Wait`.
- Each agent stores `opportunity_cost` equal to the value of its chosen action.

3) EXECUTE
- Mutual proposals are detected first.
- Both agents enter `NEGOTIATING`, the trade executes immediately, and both
  return to `AVAILABLE`.
- Neither agent moves because the trade consumed their action for the tick.

Outcome:
- One trade is logged.
- Holdings update to the Nash allocation.
- Beliefs are updated if enabled.

### Scenario 2: 3 agents, competing proposals and fallback
Agents:
- A: alpha=0.3, endowment (10, 2)
- B: alpha=0.7, endowment (2, 10)
- C: alpha=0.4, endowment (8, 4)
- All co-located at Position(5, 5)

Tick flow:
1) PERCEIVE
- All agents observe each other.
- A and C both see positive surplus with B.

2) DECIDE
- A chooses `Propose(B)` with fallback `Wait` (co-located).
- C chooses `Propose(B)` with fallback `Wait` (co-located).
- B chooses its own action (often `Propose(A)` or `Propose(C)` depending on
  action evaluation and tie-breaking), and stores `opportunity_cost`.

3) EXECUTE
- No mutual proposal pair unless B also proposed to A or C.
- Non-mutual proposals are processed in iteration order.
- The first proposer to be processed gets B's acceptance check:
  - If `surplus >= opportunity_cost`, B accepts and trades with that proposer.
  - The other proposer becomes "non-selected" and executes fallback (Wait).
  - No cooldown is applied for the non-selected proposer.
- If B rejects (surplus < opportunity cost), the rejected proposer executes
  fallback and receives a cooldown for B.

Outcome:
- At most one trade occurs for B in the tick.
- Exactly one proposer trades; the other executes fallback.
- Cooldowns only appear for explicit rejection, not for non-selection.

---

## Quick summary
- The implemented architecture follows the action-budget tick model from
  AGENT-ARCHITECTURE.md, with same-tick coordination and fallback execution.
- The core loop is Perceive -> Decide -> Execute with deterministic action
  selection and immediate bargaining on accepted proposals.
- The largest design-to-implementation gaps are proposal adjacency, lack of
  surplus-based conflict resolution, and the unused PROPOSAL_PENDING state.
- The belief system exists and updates on trade but does not yet drive
  decision-making or acceptance in the default procedure.
