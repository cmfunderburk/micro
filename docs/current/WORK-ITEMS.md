# Work Items

**Date:** 2026-01-05
**Purpose:** Issue tracker style breakdown of development work
**Companion:** See `DEVELOPMENT-PLAN.md` for narrative context

---

## Labels

| Label | Meaning |
|-------|---------|
| `phase:0` | Theoretical alignment (foundation verification) |
| `phase:1` | Agent belief architecture |
| `phase:2` | Institutional primitives |
| `phase:3` | Benchmarks |
| `phase:4` | Research exploitation |
| `parallel:viz` | Visualization parallel track |
| `critical` | Architectural decision with broad implications |
| `blocked` | Cannot proceed until dependency resolved |
| `foundational` | Affects multiple downstream items |

---

## Critical Items

### ARCH-001: Multi-Agent Mechanism Architecture
**Labels:** `critical`, `foundational`, `blocked`
**Blocks:** PROT-004, PROT-005, all production work

**Description:**
The current four-phase tick loop (evaluate/decide/move/exchange) and `BargainingProtocol` interface assume bilateral exchange. Multi-agent mechanisms (double auction, centralized markets) and production require different coordination patterns.

**Required Decisions:**
- [ ] Extend tick loop or introduce new abstraction layer?
- [ ] Design interface for multi-agent mechanisms
- [ ] How does production integrate with exchange?
- [ ] How do agents choose mechanism participation?

**Action:** Dedicated architectural session required before implementation.

**Status:** Not started

---

## Phase 0: Theoretical Alignment

### THEORY-001: Review Nash Bargaining Implementation
**Labels:** `phase:0`
**Dependencies:** None

**Description:**
Verify that `NashBargainingProtocol` correctly maximizes the Nash product. Add tests checking:
- [ ] Nash product is maximized at computed solution
- [ ] Solution is Pareto efficient
- [ ] Surplus split is symmetric (equal bargaining weights)
- [ ] Handles edge cases (zero utility, no gains from trade)

**Files:** `src/microecon/bargaining.py`, `tests/theory/test_nash_bargaining.py`

**Status:** Not started

---

### THEORY-002: Review Rubinstein Implementation
**Labels:** `phase:0`
**Dependencies:** None

**Description:**
Verify that `RubinsteinBargainingProtocol` computes correct SPE allocation. Add tests checking:
- [ ] First-mover advantage proportional to patience ratio
- [ ] Converges to Nash as discount factors approach 1
- [ ] Handles asymmetric patience correctly
- [ ] Matches BRW (1986) asymmetric Nash weights

**Files:** `src/microecon/bargaining.py`, `tests/theory/test_rubinstein_bargaining.py`

**Status:** Not started

---

### THEORY-003: Review Utility/Preference Implementation
**Labels:** `phase:0`
**Dependencies:** None

**Description:**
Verify that `CobbDouglas` preferences and demand calculations match theory. Add tests checking:
- [ ] MRS computed correctly: MRS = (α/(1-α)) * (y/x)
- [ ] Indifference curves have correct shape
- [ ] Marshallian demand correct: x* = αM/p_x, y* = (1-α)M/p_y
- [ ] Hicksian demand and expenditure function (if implemented)

**Files:** `src/microecon/preferences.py`, `tests/theory/test_preferences.py`

**Status:** Not started

---

### THEORY-004: Review Gains from Trade Computation
**Labels:** `phase:0`
**Dependencies:** None

**Description:**
Verify that gains from trade and surplus calculations are correct. Add tests checking:
- [ ] Total surplus = sum of individual utility gains
- [ ] Gains exhausted at bargaining solution (no unexploited surplus)
- [ ] Contract curve correctly identified

**Files:** `src/microecon/bargaining.py`, `tests/theory/test_gains_from_trade.py`

**Status:** Not started

---

### THEORY-005: Review Pareto Efficiency of Outcomes
**Labels:** `phase:0`
**Dependencies:** THEORY-001, THEORY-002

**Description:**
Verify that bargaining outcomes are Pareto efficient. Add tests checking:
- [ ] No post-trade allocation Pareto dominates the outcome
- [ ] Outcome lies on contract curve
- [ ] Trade moves toward efficiency from initial endowment

**Files:** `tests/theory/test_pareto_efficiency.py`

**Status:** Not started

---

### THEORY-006: Document and Fix Divergences
**Labels:** `phase:0`
**Dependencies:** THEORY-001 through THEORY-005

**Description:**
Compile findings from theoretical review. Document any divergences. Fix implementation issues revealed.

**Outputs:** Issue list, code fixes, updated documentation

**Status:** Not started

---

## Phase 1: Agent Belief Architecture

### BELIEF-001: Design Belief Representation
**Labels:** `phase:1`, `foundational`
**Dependencies:** Phase 0 complete

**Description:**
Design the data structures for agent beliefs:
- [ ] Price beliefs: Distribution? Point estimate with variance? Confidence intervals?
- [ ] Partner beliefs: Type estimates? Behavioral predictions? Reputation?
- [ ] Memory structure: What gets stored? How much history?

**Reference:** Kreps I, Chapter 5-7 (Choice under Uncertainty, Dynamic Choice)

**Outputs:** Design document, dataclass definitions

**Status:** Not started

---

### BELIEF-002: Implement Agent Memory
**Labels:** `phase:1`
**Dependencies:** BELIEF-001

**Description:**
Add memory/observation history to Agent class:
- [ ] Trade history (who, what, when)
- [ ] Price observations
- [ ] Partner interaction history
- [ ] Configurable memory depth/structure

**Files:** `src/microecon/agent.py`

**Status:** Not started

---

### BELIEF-003: Implement Belief Updates
**Labels:** `phase:1`
**Dependencies:** BELIEF-001, BELIEF-002

**Description:**
Implement belief update logic:
- [ ] Price belief updates from observations
- [ ] Partner type belief updates
- [ ] Configurable update rules (Bayesian, heuristic)

**Files:** `src/microecon/beliefs.py` (new)

**Status:** Not started

---

### BELIEF-004: Integrate Beliefs with Search
**Labels:** `phase:1`
**Dependencies:** BELIEF-003

**Description:**
Update search logic to incorporate beliefs:
- [ ] Target evaluation uses beliefs about partner types
- [ ] Price expectations influence surplus calculation
- [ ] Movement decisions account for learned information

**Files:** `src/microecon/search.py`

**Status:** Not started

---

### BELIEF-005: Integrate Beliefs with Exchange
**Labels:** `phase:1`
**Dependencies:** BELIEF-003

**Description:**
Update bargaining to incorporate beliefs:
- [ ] Agents use believed types (not true types) for strategy
- [ ] Information revelation during bargaining updates beliefs
- [ ] Post-trade belief updates

**Files:** `src/microecon/bargaining.py`

**Status:** Not started

---

### BELIEF-006: Belief System Tests
**Labels:** `phase:1`
**Dependencies:** BELIEF-003, BELIEF-004, BELIEF-005

**Description:**
Comprehensive tests for belief architecture:
- [ ] Belief update correctness (Bayesian tests)
- [ ] Memory management (no leaks, correct eviction)
- [ ] Integration with search and exchange
- [ ] Edge cases (no observations, conflicting information)

**Status:** Not started

---

## Phase 2: Institutional Primitives

### PROT-001: Implement TIOLI Protocol
**Labels:** `phase:2`
**Dependencies:** Phase 1 complete (beliefs may influence TIOLI strategy)

**Description:**
Implement Take-It-Or-Leave-It bargaining:
- [ ] Proposer determined (random? based on arrival?)
- [ ] Proposer makes single offer
- [ ] Responder accepts or rejects
- [ ] Proposer captures all surplus if accepted

**Reference:** O&R-B Chapter 3.1

**Files:** `src/microecon/bargaining.py`, `tests/test_tioli.py`

**Status:** Not started

---

### PROT-002: Implement Posted Price Protocol
**Labels:** `phase:2`
**Dependencies:** Phase 1 complete

**Description:**
Implement posted price mechanism:
- [ ] Seller posts price
- [ ] Buyer accepts or rejects
- [ ] Price-setting strategy (configurable?)
- [ ] Asymmetric roles (buyer/seller distinction)

**Files:** `src/microecon/bargaining.py`, `tests/test_posted_price.py`

**Status:** Not started

---

### PROT-003: Implement Random Matching
**Labels:** `phase:2`
**Dependencies:** None

**Description:**
Implement random matching as baseline:
- [ ] Random pairing among co-located agents
- [ ] No preference-based selection
- [ ] Useful for comparison with other protocols

**Files:** `src/microecon/matching.py`, `tests/test_random_matching.py`

**Status:** Not started

---

### PROT-004: Implement Double Auction
**Labels:** `phase:2`, `blocked`
**Dependencies:** ARCH-001 (architecture decision)

**Description:**
Implement continuous double auction:
- [ ] Buyers submit bids
- [ ] Sellers submit asks
- [ ] Matching rule (price-time priority?)
- [ ] Multi-agent coordination

**Blocked by:** ARCH-001 - requires architectural decision on multi-agent mechanisms

**Status:** Blocked

---

### PROT-005: Implement Gale-Shapley Matching
**Labels:** `phase:2`
**Dependencies:** Buyer/seller role distinction in agent model

**Description:**
Implement deferred acceptance matching:
- [ ] Two-sided market structure
- [ ] Proposing and receiving sides
- [ ] Stable matching output
- [ ] Strategy-proofness for proposing side

**Reference:** Kreps II Chapter 25

**Files:** `src/microecon/matching.py`, `tests/test_gale_shapley.py`

**Status:** Not started

---

### INFO-001: Implement Private Values Environment
**Labels:** `phase:2`
**Dependencies:** Phase 1 (belief architecture)

**Description:**
Private values information structure:
- [ ] Agents know own type perfectly
- [ ] Agents observe noisy signals of others' types
- [ ] No correlation between types
- [ ] Classic auction/bargaining setup

**Files:** `src/microecon/information.py`, `tests/test_private_values.py`

**Status:** Not started

---

### INFO-002: Implement Common Values Environment
**Labels:** `phase:2`
**Dependencies:** INFO-001

**Description:**
Common values information structure:
- [ ] Types correlated across agents
- [ ] Each agent observes noisy signal of common value
- [ ] Winner's curse potential
- [ ] Auction-style information revelation

**Reference:** Kreps II Chapter 24 (winner's curse)

**Files:** `src/microecon/information.py`, `tests/test_common_values.py`

**Status:** Not started

---

### INFO-003: Implement Signaling
**Labels:** `phase:2`
**Dependencies:** Phase 1 (beliefs update from signals)

**Description:**
Costly signaling mechanism:
- [ ] Agents can send signals about type
- [ ] Signals have cost (possibly type-dependent)
- [ ] Receivers update beliefs from signals
- [ ] Single-crossing condition for separation

**Reference:** Kreps II Chapter 20, Spence (1973)

**Files:** `src/microecon/signaling.py` (new), `tests/test_signaling.py`

**Status:** Not started

---

### INFO-004: Implement Screening
**Labels:** `phase:2`
**Dependencies:** INFO-003

**Description:**
Menu-based screening mechanism:
- [ ] Uninformed agent offers menu of contracts
- [ ] Informed agent self-selects
- [ ] Incentive compatibility constraints
- [ ] Rothschild-Stiglitz style separation

**Reference:** Kreps II Chapter 20

**Files:** `src/microecon/screening.py` (new), `tests/test_screening.py`

**Status:** Not started

---

### SCENARIO-001: Extend YAML Schema
**Labels:** `phase:2`
**Dependencies:** Protocols and info environments implemented

**Description:**
Extend scenario configuration to support new options:
- [ ] All new protocol choices
- [ ] Information environment parameters
- [ ] Belief system configuration
- [ ] Heterogeneous agent specification

**Files:** `src/microecon/scenarios/schema.py`

**Status:** Not started

---

## Phase 3: Benchmarks

### BENCH-001: Implement Walrasian Equilibrium Computation
**Labels:** `phase:3`
**Dependencies:** Phase 2 complete

**Description:**
Compute competitive equilibrium for comparison:
- [ ] Excess demand function computation
- [ ] Price adjustment algorithm (tatonnement?)
- [ ] Equilibrium allocation computation
- [ ] Handle non-existence, multiplicity

**Reference:** Kreps I Chapter 14

**Files:** `src/microecon/analysis/equilibrium.py` (new)

**Status:** Not started

---

### BENCH-002: Core Membership Verification
**Labels:** `phase:3`
**Dependencies:** BENCH-001

**Description:**
Verify whether simulation outcomes lie in the core:
- [ ] Core computation for exchange economy
- [ ] Test allocation against blocking coalitions
- [ ] Distance from core metric

**Reference:** Kreps I Chapter 15

**Files:** `src/microecon/analysis/equilibrium.py`

**Status:** Not started

---

### BENCH-003: Efficiency Metrics
**Labels:** `phase:3`
**Dependencies:** BENCH-001

**Description:**
Quantify welfare efficiency of simulation outcomes:
- [ ] Distance from Pareto frontier
- [ ] Welfare loss relative to Walrasian
- [ ] Distributional metrics (inequality measures)

**Files:** `src/microecon/analysis/equilibrium.py`

**Status:** Not started

---

### BENCH-004: Integrate with Batch Analysis
**Labels:** `phase:3`
**Dependencies:** BENCH-001, BENCH-002, BENCH-003

**Description:**
Add benchmark comparison to batch analysis workflow:
- [ ] Automatic equilibrium computation for batch configs
- [ ] Comparison metrics in run summaries
- [ ] Time series of "distance from equilibrium"

**Files:** `src/microecon/batch.py`, `src/microecon/analysis/`

**Status:** Not started

---

## Parallel Track: Visualization

### VIZ-001: Export PNG Frames
**Labels:** `parallel:viz`
**Dependencies:** None

**Description:**
Add capability to export individual frames:
- [ ] Export current state as PNG
- [ ] High-resolution option for publication
- [ ] Configurable output path

**Files:** `src/microecon/visualization/app.py`

**Status:** Not started

---

### VIZ-002: Export GIF Animation
**Labels:** `parallel:viz`
**Dependencies:** VIZ-001

**Description:**
Export simulation run as animated GIF:
- [ ] Frame-by-frame capture during replay
- [ ] Configurable frame rate
- [ ] Optimization (file size)

**Files:** `src/microecon/visualization/`

**Status:** Not started

---

### VIZ-003: Edgeworth Box Trade View
**Labels:** `parallel:viz`
**Dependencies:** None

**Description:**
Detail view showing trade in Edgeworth box:
- [ ] Click on trade to open detail view
- [ ] Show pre/post-trade allocations
- [ ] Indifference curves for both agents
- [ ] Contract curve and gains from trade

**Files:** `src/microecon/visualization/` (new component)

**Status:** Not started

---

### VIZ-004: Belief Visualization
**Labels:** `parallel:viz`
**Dependencies:** Phase 1 (belief architecture)

**Description:**
Visualize agent beliefs:
- [ ] Price belief distributions
- [ ] Partner type estimates
- [ ] Belief evolution over time

**Files:** `src/microecon/visualization/`

**Status:** Not started

---

### VIZ-005: Overlay Toggles
**Labels:** `parallel:viz`
**Dependencies:** None

**Description:**
Add UI controls for overlay visibility:
- [ ] Toggle movement trails
- [ ] Toggle perception radius
- [ ] Toggle trade animations
- [ ] Toggle grid lines

**Files:** `src/microecon/visualization/app.py`

**Status:** Not started

---

## Phase 4: Research

### RESEARCH-001: Market Emergence Investigation
**Labels:** `phase:4`
**Dependencies:** Phases 0-3 complete

**Description:**
Systematic investigation of market emergence:
- [ ] Factorial design over protocols, info, matching
- [ ] Define emergence indicators (price convergence, network, welfare)
- [ ] Run batch experiments
- [ ] Analyze and document findings

**Status:** Not started

---

## Summary Statistics

| Label | Count | Blocked |
|-------|-------|---------|
| `phase:0` | 6 | 0 |
| `phase:1` | 6 | 0 |
| `phase:2` | 11 | 1 |
| `phase:3` | 4 | 0 |
| `phase:4` | 1 | 0 |
| `parallel:viz` | 5 | 0 |
| `critical` | 1 | - |

**Total items:** 34
**Blocked items:** 2 (PROT-004, and by extension some others depend on ARCH-001)

---

**Document Version:** 1.0
**Created:** 2026-01-05
