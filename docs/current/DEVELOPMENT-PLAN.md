# Development Plan: Framework Completeness

**Date:** 2026-01-05
**Purpose:** Narrative roadmap for completing the microeconomics platform framework
**Companion:** See `WORK-ITEMS.md` for the issue tracker style breakdown

---

## Overview

This document describes the development arc from the current implementation (v0.1.0) toward a complete framework capable of supporting systematic institutional comparison research. The guiding principle is **framework completeness before research exploitation**: building out the full spectrum of institutional primitives, agent capabilities, and benchmarks before conducting major research investigations.

The first major research output—understanding when and how markets emerge from bilateral exchange—depends on having configurable institutional options. Market emergence is not a single phenomenon but a dependent variable shaped by bargaining protocols, information structures, matching mechanisms, and agent sophistication. Therefore, the framework must be complete enough to isolate and compare these effects.

---

## Critical Architectural Decision Point

**Multi-Agent Mechanisms and Production**

The current architecture assumes bilateral exchange:
- Four-phase tick loop: evaluate → decide → move → exchange
- `BargainingProtocol` interface designed for two-agent negotiation
- Search evaluates bilateral surplus, movement seeks bilateral partners

This architecture cannot naturally accommodate:
- **Double auctions** and centralized market mechanisms (multi-agent, simultaneous)
- **Production** (agents choosing to produce vs. trade vs. participate in mechanisms)
- **Mechanism participation decisions** (agents choosing *which* market to enter)

Before implementing multi-agent mechanisms (double auction, posted price markets with multiple buyers), we need a focused architectural session to:
1. Evaluate whether to extend the existing tick loop or introduce a new abstraction layer
2. Design the interface for multi-agent mechanisms
3. Consider how production integrates with exchange
4. Ensure the agent decision model generalizes appropriately

**This is not a blocking issue for the near-term work** (bilateral protocols, information regimes, belief architecture can proceed), but it **must be resolved before implementing double auction** or any production capabilities.

---

## Phase 0: Theoretical Alignment

**Goal:** Verify that current implementation matches theoretical foundations; reveal gaps through testing.

The platform claims to implement canonical microeconomic theory. Before extending, we must verify this claim rigorously. This phase adds comprehensive tests that check whether agent behavior, bargaining solutions, and market outcomes align with textbook predictions.

**Scope:**
- Review each module against its theoretical grounding (per `theoretical-foundations.md`)
- Add tests verifying:
  - Nash bargaining maximizes Nash product
  - Rubinstein SPE has correct first-mover advantage
  - Utility maximization produces correct MRS relationships
  - Gains from trade computed correctly
  - Pareto efficiency of bargaining outcomes
- Document any divergences discovered
- Fix issues revealed by theoretical tests

**Outputs:**
- Theoretical alignment test suite (`tests/theory/`)
- Issue list of divergences (if any)
- Confidence that foundation is sound before extension

**Dependencies:** None. This is the starting point.

---

## Phase 1: Agent Belief Architecture

**Goal:** Extend agent model to support integrated beliefs over prices and opponent types.

Currently, agents are myopic: they evaluate visible others using Nash surplus discounted by distance, with no memory across ticks. For meaningful market emergence study, agents need:
- **Price beliefs:** Accumulated observations of trade prices, forming expectations
- **Partner beliefs:** Learning about opponent types, past behavior, reliability
- **Memory:** State persisting across ticks

This is foundational work. Adding beliefs later would require retrofitting all protocols and search logic. Therefore, this must come before new institutional primitives.

**Scope:**
- Design belief representation (distribution over prices? Point estimates with uncertainty?)
- Add agent memory structure (observation history, trade history)
- Update agent decision model to incorporate beliefs
- Ground design in Kreps decision theory (choice under uncertainty, learning)
- Ensure compatibility with existing `InformationEnvironment` abstraction

**Key Design Questions:**
- How do beliefs update? (Bayesian? Heuristic? Configurable?)
- What information do agents remember? (All observations? Last N? Sufficient statistics?)
- How do beliefs influence search and exchange decisions?
- How does this interact with information asymmetry (agents may have false beliefs)?

**Outputs:**
- Extended `Agent` class with belief/memory attributes
- Belief update logic
- Tests verifying belief dynamics
- Documentation of design decisions

**Dependencies:** Phase 0 (foundation verified before extending)

---

## Phase 2: Institutional Primitives

**Goal:** Complete the spectrum of configurable institutional rules.

This phase adds the remaining bargaining protocols, information environments, and matching mechanisms needed for meaningful institutional comparison.

### 2A: Bargaining Protocols (Bilateral)

Current: Nash, Rubinstein
To add:
- **TIOLI (Take-It-Or-Leave-It):** Proposer captures all surplus. Simplest bilateral mechanism.
- **Posted Prices:** One agent posts a price, other accepts/rejects. Asymmetric power.

**Note:** Double auction deferred pending architectural decision (see Critical Decision Point above).

### 2B: Information Environments

Current: FullInformation, NoisyAlphaInformation
To add:
- **Private Values:** Agents know own type perfectly, observe noisy signals of others
- **Common Values:** Correlated types with noisy signals (e.g., winner's curse setup)
- **Signaling:** Agents can send costly signals about their type
- **Screening:** Agents can design menus to separate types

The information taxonomy should be developed incrementally, with each regime rigorously tested before proceeding to the next.

### 2C: Matching Mechanisms

Current: Opportunistic, StableRoommates
To add:
- **Random Matching:** Baseline random pairing for comparison
- **Gale-Shapley:** Two-sided matching (when buyer/seller distinction matters)
- Additional mechanisms as research questions demand

### 2D: Scenario Configuration

Extend YAML schema to support new configuration options:
- All new protocol choices
- Information environment parameters
- Belief system configuration
- More flexible agent heterogeneity specification

**Dependencies:** Phase 1 (belief architecture in place; protocols may interact with beliefs)

---

## Phase 3: Benchmarks

**Goal:** Compute equilibrium benchmarks for comparison with simulation outcomes.

Market emergence research requires comparing simulation outcomes to theoretical predictions. This phase adds computational tools for equilibrium analysis.

**Scope:**
- **Walrasian Equilibrium:** Compute competitive equilibrium prices and allocations for the specified preferences and endowments
- **Core:** Verify whether simulation outcomes lie in the core
- **Efficiency Metrics:** Quantify divergence from Pareto frontier

**Outputs:**
- `analysis/equilibrium.py` module
- Integration with batch analysis (compare runs to benchmarks)
- Metrics for "distance from equilibrium" over time

**Dependencies:** Phase 2 (full primitive set needed for meaningful comparison)

---

## Phase 4: Market Emergence Research

**Goal:** Systematic investigation of when and how markets emerge.

With the framework complete, conduct the first major research program:
- Vary institutional rules systematically (factorial design over protocols, information, matching)
- Measure emergence indicators (price convergence, trade network structure, welfare efficiency)
- Identify conditions under which "market" behavior emerges vs. fails

This is research exploitation, not framework development.

**Dependencies:** Phases 0-3 complete.

---

## Parallel Track: Visualization

Visualization development proceeds incrementally alongside core work:
- **Near-term:** Maintain current functionality, fix bugs as encountered
- **Medium-term:** Add export capabilities (PNG/GIF) for publication figures
- **Longer-term:** Edgeworth box trade detail view, belief visualization (when belief architecture exists)

Visualization is not blocking for framework completeness but is necessary for research presentation.

---

## Document Relationships

This plan relates to existing documentation as follows:

| Document | Role |
|----------|------|
| `VISION.md` | Authoritative on identity and methodology; this plan implements the vision |
| `STATUS.md` | Current capabilities; update as phases complete |
| `theoretical-foundations.md` | Reference for Phase 0 theoretical alignment |
| `VISUALIZATION.md` | Design spec for visualization parallel track |
| `WORK-ITEMS.md` | Issue tracker breakdown of this plan |

---

## Success Criteria

The framework is "complete" for research purposes when:
1. All bilateral bargaining protocols implemented and tested
2. Full information environment taxonomy available
3. Agent belief architecture supports price and partner learning
4. Walrasian benchmark computable for comparison
5. Batch infrastructure supports factorial experimental design
6. Visualization can export publication-quality figures

At that point, the first major research investigation (market emergence) can proceed with confidence that institutional effects are cleanly isolated.

---

**Document Version:** 1.0
**Created:** 2026-01-05
