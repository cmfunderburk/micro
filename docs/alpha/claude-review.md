# Comprehensive 0.0.1 Alpha Review

**Date:** 2026-01-02
**Reviewer:** Claude Opus 4.5
**Branch:** `tweaking`
**Scope:** Stabilization review for personal research use

---

## Executive Summary

The microecon platform is **substantially complete** for a 0.0.1 alpha release. The core simulation engine, bargaining protocols, matching protocols, and visualization are functional and theoretically grounded. Recent work on the BRW (Binmore-Rubinstein-Wolinsky) theoretical correction was excellent and addresses the most critical theoretical issue.

**Overall Assessment: 85/100 - Ready for alpha with targeted fixes**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Vision alignment | 90% | Core "institutional visibility" vision implemented |
| Code quality | 90% | Excellent type hints, docstrings, architecture |
| Theoretical correctness | 85% | BRW fix done; minor documentation gaps |
| Test coverage | 70% | Strong scenario tests; gaps in information, visualization |
| Visualization | 75% | Functional MVP; Phase 1 dashboard complete |
| Documentation | 80% | STATUS.md current; some stale session docs |

**Blockers for 0.0.1:** None critical. Recommended stabilization work totals ~2-3 focused sessions.

---

## Table of Contents

1. [Vision Alignment](#1-vision-alignment)
2. [Core Simulation Code Review](#2-core-simulation-code-review)
3. [Theoretical Correctness](#3-theoretical-correctness)
4. [Test Suite Analysis](#4-test-suite-analysis)
5. [Visualization Assessment](#5-visualization-assessment)
6. [Documentation Review](#6-documentation-review)
7. [Bugs and Issues](#7-bugs-and-issues)
8. [Recommended Tests to Add](#8-recommended-tests-to-add)
9. [Proposed Abstractions](#9-proposed-abstractions-for-future-generalization)
10. [0.0.1 Release Checklist](#10-001-release-checklist)

---

## 1. Vision Alignment

### 1.1 Core Insight: Institutional Visibility

**Status: FULLY IMPLEMENTED**

The platform achieves its central innovation of making institutions visible, configurable, and comparable:

| Institution | Implementation | Comparison Capability |
|-------------|----------------|----------------------|
| Bargaining protocols | `NashBargainingProtocol`, `RubinsteinBargainingProtocol` | `run_comparison()` for head-to-head |
| Matching protocols | `OpportunisticMatchingProtocol`, `StableRoommatesMatchingProtocol` | `run_matching_comparison()` |
| Information environments | `FullInformation` (only) | Architecture ready for expansion |
| Search mechanisms | Distance-discounted surplus | Protocol-aware since BRW fix |

The trading chain scenario empirically demonstrates institutional visibility: StableRoommates matching achieves 2.2% higher welfare than Opportunistic by finding globally optimal pairs.

### 1.2 Methodology Alignment

| Vision Principle | Status |
|------------------|--------|
| Equilibrium as comparison baseline, not foundation | Aligned - MRS equality noted as special case, not general claim |
| Textbook-grounded implementations | Aligned - References to Kreps I/II, O&R-B, MWG throughout |
| Framework-level investment | Aligned - ABC patterns, clean separations |
| Theoretical grounding as constraint | Aligned - All protocols cite canonical sources |

### 1.3 Gaps vs. Vision

| Vision Feature | Status | Priority for 0.0.1 |
|----------------|--------|-------------------|
| Additional bargaining protocols (TIOLI, double auction) | Not implemented | Low (future work) |
| Information regimes (private, signaled) | Architecture only | Low (documented limitation) |
| Agent sophistication levels | Single level | Low (future work) |
| Market emergence metrics | Basic welfare only | Low (future work) |
| Walrasian equilibrium benchmark | Not implemented | Low (noted in PLAN) |

**Recommendation:** Document current scope clearly in STATUS.md. The implemented subset is sufficient for meaningful research.

---

## 2. Core Simulation Code Review

### 2.1 Code Quality Summary

**Overall: EXCELLENT (90/100)**

The codebase demonstrates professional engineering practices:

- **Type hints:** 100% coverage across all 249 functions
- **Docstrings:** Comprehensive with theoretical grounding
- **Architecture:** Clean separation of concerns, no circular dependencies
- **Numerical stability:** Adaptive epsilon, tolerance comparisons throughout
- **Naming conventions:** Consistent, descriptive, follows PEP8

### 2.2 Module-by-Module Assessment

| Module | Lines | Quality | Issues |
|--------|-------|---------|--------|
| `bundle.py` | 105 | Excellent | `_unsafe_init` bypasses frozen dataclass (documented, acceptable) |
| `preferences.py` | 115 | Excellent | MRS boundary cases handled correctly |
| `agent.py` | 150 | Excellent | Clean private state / observable type separation |
| `grid.py` | 260 | Excellent | Toroidal wrap, efficient spatial queries |
| `information.py` | 100 | Good | Only `FullInformation` implemented; `PrivateInformation` placeholder |
| `bargaining.py` | 850 | Excellent | BRW implementation correct; golden section search robust |
| `search.py` | 280 | Very Good | Protocol-aware since recent fix |
| `matching.py` | 450 | Excellent | Irving's algorithm correctly implemented |
| `simulation.py` | 700 | Very Good | Four-phase tick loop clean; path crossing heuristic has edge case |
| `batch.py` | 350 | Excellent | Clean parameter expansion |

### 2.3 Architectural Strengths

1. **Protocol abstraction pattern:** `BargainingProtocol` and `MatchingProtocol` ABCs enable institutional comparison without code changes
2. **Layered dependencies:** Bundle → Preferences → Agent → Grid → Protocols → Simulation → Batch (no cycles)
3. **Type safety:** TYPE_CHECKING idiom correctly prevents runtime circular imports
4. **Immutability where appropriate:** Frozen dataclasses for value objects (Bundle, Position, AgentType)

### 2.4 Code Issues to Address

#### Issue 1: Path Crossing Heuristic Edge Case
**Location:** `simulation.py:293-304`
**Severity:** Low
**Description:** The heuristic for detecting agents crossing paths may miss diagonal crossings:
```python
crossed = (old1 == new2 and old2 == new1)
adjacent = new1.chebyshev_distance_to(new2) == 1
```
**Impact:** Rare edge case where agents might pass without meeting
**Recommendation:** Document as known limitation. The discrete grid model makes this acceptable.

#### Issue 2: Infinity Sentinels in Matching
**Location:** `matching.py:325-326`
**Severity:** Very Low
**Description:** Uses `float('inf')` as sentinel for "not in preference list"
**Impact:** None - only used in comparisons, never arithmetic
**Recommendation:** No action needed; pragmatic pattern.

---

## 3. Theoretical Correctness

### 3.1 Recent BRW Correction - Verified Correct

The implementation of asymmetric Nash bargaining for Rubinstein is **theoretically sound**:

```python
# bargaining.py - BRW weight computation
w1 = math.log(delta_2) / (math.log(delta_1) + math.log(delta_2))
w2 = math.log(delta_1) / (math.log(delta_1) + math.log(delta_2))
```

This correctly implements Binmore, Rubinstein, Wolinsky (1986):
- More patient player (higher δ) gets greater bargaining power
- Equal δ → equal weights (symmetric Nash)
- Proposer identity is irrelevant (correct for exchange economies)

### 3.2 Protocol-Aware Search - Verified Correct

Search now uses `protocol.compute_expected_surplus()` when provided:
- `search.py:120-123` falls back to Nash surplus if no protocol specified
- Distance discounting correctly applied: `surplus * (δ ** distance)`
- Matching applies same discounting for preference ranking

### 3.3 Theoretical Documentation Gaps

| Gap | Location | Severity |
|-----|----------|----------|
| Irving's algorithm (1985) not cited in code | `matching.py` | Low |
| Cobb-Douglas utility form not derived from primitives | `preferences.py` | Very Low |
| MRS = price ratio connection not documented | `preferences.py:102-106` | Very Low |

**Recommendation:** Add brief comments citing sources. The theoretical-foundations.md file handles high-level citations well.

### 3.4 Theoretical Concerns (Not Bugs)

#### Concern 1: Search Surplus Under Information Asymmetry
**Current behavior:** Agents know counterparty's discount factor when computing Rubinstein surplus
**Issue:** Under private information, agents wouldn't know partner's patience
**Status:** Correctly documented as future work in PLAN_theoretical_corrections.md §9

#### Concern 2: MRS Equality Claim
**Test renamed:** `test_competitive_equilibrium_achieved` → `test_mrs_equality_in_symmetric_case`
**Status:** Correctly clarifies this is a special case, not general property of bilateral exchange

---

## 4. Test Suite Analysis

### 4.1 Overview

**Total tests:** 352 (all passing)
**Test organization:** Well-structured by module and scenario

| Category | Tests | Quality |
|----------|-------|---------|
| Core modules (bundle, preferences, agent, grid) | 59 | Excellent |
| Bargaining protocols | 31 | Excellent - includes BRW validation |
| Matching protocols | 26 | Very Good |
| Scenario tests (2-agent, 3-agent, trading chain, hub-spoke) | 144 | **Exceptional** |
| Logging & analysis | 36 | Good |
| Batch infrastructure | 15 | Good |
| Scenarios (file loading) | 11 | Good |
| Search | 8 | **Needs expansion** |
| Simulation | 14 | Adequate |

### 4.2 Exceptional Quality: Scenario Tests

The scenario tests in `tests/scenarios/` are outstanding:

- **Hand-computed predictions:** Expected values derived mathematically, not empirically
- **5-phase structure:** Tests validate complete pipelines (initial state → search → movement → bargaining → equilibrium)
- **Pareto efficiency checks:** MRS equality verified where applicable
- **Institutional comparison:** Committed vs opportunistic matching welfare gap verified

Example from `test_trading_chain.py:1291-1401`:
```python
# Tests verify StableRoommates achieves 26.80 welfare vs Opportunistic 26.20
# This is the core demonstration of "institutional visibility"
```

### 4.3 Critical Test Gaps

#### Gap 1: Information Module (0 tests)
**Location:** `src/microecon/information.py` - NO TEST FILE EXISTS
**Risk:** Medium - InformationEnvironment ABC is central to architecture
**Recommendation:** Add `tests/test_information.py` with:
- `FullInformation.get_observable_type()` returns correct AgentType
- Agents within perception radius correctly identified
- Observable type matches private state under FullInformation

#### Gap 2: Visualization Module (0 tests)
**Location:** `src/microecon/visualization/` - NO TEST FILE EXISTS
**Risk:** Low for alpha - manual testing acceptable for personal research
**Recommendation:** Defer to post-alpha; note as technical debt

#### Gap 3: Search Module (shallow coverage)
**Location:** `tests/test_search.py` - only 8 tests
**Missing tests:**
- Protocol-aware target evaluation (Nash vs Rubinstein)
- Perception radius boundary conditions
- Movement budget exhaustion
- Extreme distance discounting

### 4.4 Test Quality Issues

| Issue | Location | Severity |
|-------|----------|----------|
| Cross-run agent comparison limited to same seed | `test_analysis.py:241-242` | Low (documented) |
| Hardcoded agent IDs make some tests brittle | Multiple files | Very Low |
| No commitment event unit tests | `test_logging.py` | Low |

---

## 5. Visualization Assessment

### 5.1 Implementation Status

**Phase 1 Dashboard: COMPLETE**
- Dual viewport comparison mode works
- Synchronized playback with timeline
- Trade animations and movement trails
- Metrics panel with welfare/trade counts
- Event markers on timeline (trades, commitments)

**Phases 2-4: NOT IMPLEMENTED (per design)**
- Scenario pipeline (YAML browser)
- Time-series charts (ImPlot integration)
- Export capabilities (PNG/GIF/MP4)

### 5.2 Visualization Bugs

#### Bug 1: Selection Persistence on Timeline Scrub
**Location:** `app.py:463-465`
**Description:** When scrubbing timeline in replay mode, `selected_agent` is NOT cleared
**Symptom:** Selected agent ring displays at wrong position after timeline jump
**Fix:**
```python
# Add to on_timeline_change callback:
self.selected_agent = None
```
**Priority:** Medium - visual confusion

#### Bug 2: Agent ID Truncation
**Location:** `app.py:834`
**Description:** UUIDs truncated to first 8 chars: `agent.id[:8]...`
**Impact:** Makes agent tracking difficult across sessions
**Fix:** Show full ID or use different identifier strategy
**Priority:** Medium - usability issue

#### Bug 3: Deferred Math Import
**Location:** `app.py:744, 1461`
**Description:** `import math` inside method body
**Impact:** None functional, but non-standard pattern
**Fix:** Move to top-level imports
**Priority:** Very Low

### 5.3 Visualization Limitations (Acceptable for Alpha)

| Limitation | Status | Recommendation |
|------------|--------|----------------|
| Overlays always on | Known | Document in STATUS.md |
| No keyboard shortcuts | Known | Note as future enhancement |
| No export capabilities | Known | Phase 4 work |
| Fixed animation durations | Acceptable | No action needed |

---

## 6. Documentation Review

### 6.1 Current State

| Document | Status | Issues |
|----------|--------|--------|
| VISION.md | Excellent | Authoritative, well-written |
| STATUS.md | Good | Needs minor updates for BRW fix |
| CLAUDE.md | Good | Development guide accurate |
| VISUALIZATION.md | Good | Design vision clear |
| theoretical-foundations.md | Good | BRW reference added |
| DESIGN_dashboard_integration.md | Good | Phase 1 complete, phases 2-4 documented |
| DESIGN_matching_protocol.md | Good | Empirical findings documented |
| PLAN_theoretical_corrections.md | Good | Implementation status clear |

### 6.2 Documentation Gaps

#### Gap 1: STATUS.md Updates Needed

Per `SESSION_2026-01-02_theoretical_corrections.md`, these corrections were deferred:

1. **Grid wrap clarification:** Current text says "NxN toroidal grid" but wrap is configurable
2. **Search limitation note:** Clarify protocol-aware search is now implemented
3. **Matching stability caveat:** Note that stable matching exists under perception constraints

#### Gap 2: Stale Session Documents

`docs/SESSION_*.md` files may contain outdated information:
- Some reference code state before BRW fix
- Commitment events ARE wired (code updated since doc written)

**Recommendation:** Add "Historical Context" note to session docs or move to archive folder.

#### Gap 3: No README.md

For personal research alpha this is acceptable, but a minimal README would help:
- Quick start: `uv run python -m microecon.visualization`
- Run tests: `uv run pytest`
- Key entry points

---

## 7. Bugs and Issues

### 7.1 Must Fix for 0.0.1

| Issue | Location | Severity | Fix Effort |
|-------|----------|----------|------------|
| Selection persistence on timeline scrub | `app.py:463-465` | Medium | 1 line |
| Agent ID truncation in tooltip | `app.py:834` | Medium | 1 line |

### 7.2 Should Fix for 0.0.1

| Issue | Location | Severity | Fix Effort |
|-------|----------|----------|------------|
| Deferred math import | `app.py:744, 1461` | Very Low | 2 lines |
| STATUS.md minor corrections | `STATUS.md` | Low | 10 min |

### 7.3 Can Defer (Technical Debt)

| Issue | Location | Notes |
|-------|----------|-------|
| Event type naming collision | `matching.py` vs `logging/events.py` | Different purposes, documented |
| Path crossing heuristic edge case | `simulation.py:293-304` | Rare, acceptable for discrete grid |
| Visualization tests | `tests/` | Manual testing OK for alpha |

---

## 8. Recommended Tests to Add

### 8.1 High Priority: Information Module

Create `tests/test_information.py`:

```python
class TestFullInformation:
    def test_observable_type_equals_private_state(self):
        """Under FullInformation, agents see true types."""
        ...

    def test_agent_list_correctly_filtered(self):
        """get_visible_agents respects perception radius."""
        ...
```

**Effort:** ~50 lines, 1 hour

### 8.2 High Priority: Protocol-Aware Search

Add to `tests/test_search.py`:

```python
def test_target_selection_differs_by_protocol():
    """Nash vs Rubinstein may rank targets differently."""
    # Setup: Agent A choosing between B (similar patience) and C (less patient)
    # Under Rubinstein, A might prefer C (captures more surplus)
    ...

def test_discount_factor_affects_ranking():
    """More patient seeker evaluates distant targets higher."""
    ...
```

**Effort:** ~100 lines, 2 hours

### 8.3 Medium Priority: Edge Cases

Add to relevant test files:

| Test | Location | Description |
|------|----------|-------------|
| `test_extreme_endowments` | `test_bargaining.py` | Verify stability with x=1000, y=0.001 |
| `test_grid_boundary_conditions` | `test_simulation.py` | Agents at corners, wrapping behavior |
| `test_commitment_duration` | `test_matching.py` | Track how long commitments persist |

**Effort:** ~150 lines, 3 hours total

### 8.4 Low Priority (Post-Alpha)

- Visualization tests (integration/snapshot testing)
- Performance benchmarks for batch runner
- Scenario file schema validation

---

## 9. Proposed Abstractions (For Future Generalization)

### 9.1 N-Good Economy Generalization

**Current constraint:** 2-good economy hardcoded throughout

**Proposed abstraction:**

```python
# bundle.py - generalized
@dataclass(frozen=True)
class Bundle:
    goods: tuple[float, ...]  # N-dimensional

    @classmethod
    def create(cls, *quantities: float) -> Bundle:
        return cls(goods=tuple(quantities))

    @property
    def dimension(self) -> int:
        return len(self.goods)

    def __getitem__(self, i: int) -> float:
        return self.goods[i]
```

**Affected modules:**
| Module | Change Required |
|--------|-----------------|
| `bundle.py` | Tuple-based storage, indexed access |
| `preferences.py` | CES generalization: `u(x) = (Σ αᵢ xᵢ^ρ)^(1/ρ)` |
| `agent.py` | No change (uses Bundle) |
| `bargaining.py` | Contract curve computation becomes N-dimensional optimization |
| `visualization/` | Color encoding needs rethinking for N>2 |

**Implementation path:**
1. Make Bundle N-dimensional (backwards compatible for N=2)
2. Add CES preference class (Cobb-Douglas is CES with ρ→0)
3. Generalize bargaining optimization (harder)
4. Defer visualization changes

**Recommendation for 0.0.1:** Document as future direction. Current 2-good model covers key research questions about institutional comparison.

### 9.2 Information Environment Extension

**Current constraint:** Only `FullInformation` implemented

**Proposed abstraction (already exists):**

```python
class InformationEnvironment(ABC):
    @abstractmethod
    def get_observable_type(self, observer: Agent, target: Agent) -> AgentType:
        """What can observer see about target?"""
        pass
```

**Proposed implementations for future:**

```python
class PrivateAlphaInformation(InformationEnvironment):
    """Agents cannot observe each other's preference parameters."""

    def get_observable_type(self, observer, target) -> AgentType:
        # Return type with noisy/estimated alpha
        return AgentType(
            alpha=self._estimate_alpha(observer, target),
            endowment=target.private_state.endowment,  # Visible
            discount_factor=target.private_state.discount_factor  # Visible
        )

class SignalingEnvironment(InformationEnvironment):
    """Agents can send costly signals about their type."""
    ...
```

**Affected modules:**
| Module | Change Required |
|--------|-----------------|
| `information.py` | Implement new classes |
| `search.py` | Use observable_type instead of private_state |
| `bargaining.py` | Handle information asymmetry |
| `visualization/` | Agent perspective mode (show what agent sees) |

**Recommendation for 0.0.1:** Architecture is ready. Document `PrivateInformation` as intentional placeholder.

### 9.3 Additional Bargaining Protocols

**Current protocols:** Nash, Rubinstein

**Proposed additions for future:**

```python
class TakeItOrLeaveItProtocol(BargainingProtocol):
    """Proposer captures all surplus beyond threat point."""
    # O&R-B Ch 3.1

class PostedPriceProtocol(BargainingProtocol):
    """Seller posts price, buyer accepts or rejects."""
    # Requires asymmetric roles

class DoubleAuctionProtocol(BargainingProtocol):
    """Both submit bids, trade at midpoint if overlap."""
    # Myerson-Satterthwaite considerations
```

**Recommendation for 0.0.1:** Document as extension points. Current two protocols demonstrate institutional visibility.

### 9.4 Walrasian Equilibrium Benchmark

**Current state:** No computed competitive equilibrium benchmark

**Proposed addition:**

```python
# analysis/equilibrium.py
def compute_walrasian_equilibrium(
    agents: list[Agent]
) -> WalrasianEquilibrium:
    """
    Compute competitive equilibrium prices and allocations.

    For 2-good Cobb-Douglas economy:
    p₁/p₂ = (Σ αᵢ Wᵢ₂) / (Σ (1-αᵢ) Wᵢ₁)
    """
    ...
```

**Use case:** Compare simulation outcomes to theoretical benchmark
- Efficiency gap: How far is final allocation from Pareto frontier?
- Price convergence: Do implicit exchange rates approach competitive prices?

**Recommendation for 0.0.1:** Note as future analysis capability. Current bilateral exchange model deliberately differs from Walrasian assumptions.

---

## 10. 0.0.1 Release Checklist

### 10.1 Must Do (Blockers)

- [ ] **Fix selection persistence bug** (`app.py:463-465`)
  - Add `self.selected_agent = None` to `on_timeline_change`

- [ ] **Fix agent ID truncation** (`app.py:834`)
  - Change to `f"ID: {agent.id}"` or implement copy button

### 10.2 Should Do (Recommended)

- [ ] **Add information module tests** (`tests/test_information.py`)
  - ~50 lines, validates core abstraction

- [ ] **Add protocol-aware search tests** (`tests/test_search.py`)
  - Verify BRW fix works in search context

- [ ] **Update STATUS.md** with minor corrections
  - Grid wrap clarification
  - Note protocol-aware search implemented

- [ ] **Move deferred import to top-level** (`app.py:744, 1461`)

### 10.3 Nice to Have (Optional)

- [ ] Add minimal README.md with quick start
- [ ] Add edge case tests (extreme endowments, grid boundaries)
- [ ] Archive or annotate stale session documents
- [ ] Document event type naming collision as known issue

### 10.4 Explicitly Not for 0.0.1

- Dashboard Phases 2-4 (scenarios, charts, exports)
- Additional bargaining protocols
- Information environment implementations
- N-good generalization
- Walrasian equilibrium benchmarks
- Visualization tests

---

## Appendix A: File Reference Quick Index

### Core Modules
| File | Lines | Purpose |
|------|-------|---------|
| `src/microecon/bundle.py` | 105 | 2-good bundles |
| `src/microecon/preferences.py` | 115 | Cobb-Douglas utility |
| `src/microecon/agent.py` | 150 | Agent with private/observable separation |
| `src/microecon/grid.py` | 260 | Spatial grid, positions, queries |
| `src/microecon/information.py` | 100 | Information environment abstraction |
| `src/microecon/bargaining.py` | 850 | Nash, Rubinstein (BRW) protocols |
| `src/microecon/search.py` | 280 | Target evaluation, movement |
| `src/microecon/matching.py` | 450 | Irving's stable roommates |
| `src/microecon/simulation.py` | 700 | Four-phase tick loop |
| `src/microecon/batch.py` | 350 | Parameter sweeps |

### Logging & Analysis
| File | Lines | Purpose |
|------|-------|---------|
| `src/microecon/logging/events.py` | 342 | Event dataclasses |
| `src/microecon/logging/logger.py` | 154 | SimulationLogger |
| `src/microecon/logging/formats.py` | 141 | JSON lines format |
| `src/microecon/analysis/loader.py` | 106 | Run loading utilities |
| `src/microecon/analysis/timeseries.py` | 211 | Time series metrics |
| `src/microecon/analysis/distributions.py` | 253 | Cross-run comparisons |
| `src/microecon/analysis/tracking.py` | 273 | Agent-level tracking |

### Visualization
| File | Lines | Purpose |
|------|-------|---------|
| `src/microecon/visualization/app.py` | 1808 | Main visualization |
| `src/microecon/visualization/replay.py` | 286 | Replay controllers |
| `src/microecon/visualization/browser.py` | 439 | Scenario browser |

### Tests (Scenario)
| File | Tests | Purpose |
|------|-------|---------|
| `tests/scenarios/test_two_agent.py` | 37 | 2-agent symmetric/asymmetric |
| `tests/scenarios/test_three_agent.py` | 6 | 3-agent sequential |
| `tests/scenarios/test_trading_chain.py` | 55 | Trading chain, matching comparison |
| `tests/scenarios/test_hub_and_spoke.py` | 46 | Hub-spoke dynamics |

---

## Appendix B: Theoretical References

### Implemented
| Concept | Source | Location |
|---------|--------|----------|
| Cobb-Douglas utility | Kreps I, Ch 2 | `preferences.py` |
| Nash bargaining solution | Nash (1950), O&R-B Ch 2 | `bargaining.py` |
| Rubinstein alternating offers | Rubinstein (1982), O&R-B Ch 3 | `bargaining.py` |
| BRW asymmetric Nash | BRW (1986), O&R-B Ch 4 | `bargaining.py` |
| Irving's stable roommates | Irving (1985) | `matching.py` |

### Not Yet Implemented (Future)
| Concept | Source | Notes |
|---------|--------|-------|
| TIOLI bargaining | O&R-B Ch 3.1 | Proposer captures all surplus |
| Gale-Shapley | Gale-Shapley (1962) | Two-sided matching |
| Signaling equilibrium | Spence (1973) | Requires information environments |
| Walrasian equilibrium | Kreps I, Ch 14 | For benchmark comparison |

---

**Document prepared:** 2026-01-02
**For version:** 0.0.1-alpha
**Scope:** Personal research use
