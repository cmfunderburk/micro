# Comprehensive Planning Proposal: Institutional Visibility & Market Emergence

**Author:** Gemini 3 Pro (Interactive CLI Agent)
**Date:** 2026-01-05
**Purpose:** Provide detailed, justified recommendations for resolving all open questions in the current planning documentation.
**Status:** Proposal for review and iteration.

---

## Executive Summary

This proposal provides a rigorous roadmap for evolving the Microecon platform from its current bilateral exchange focus (v0.1.0) toward a comprehensive framework for institutional comparison. We prioritize **theoretical grounding** and **architectural extensibility** to ensure the platform remains a robust research instrument.

Key highlights include:
- A **Mechanism-Phase** architecture that unifies bilateral and multilateral exchange.
- A **State-Space** approach to agent beliefs, balancing tractability with Bayesian rigor.
- A **Multi-Pillar** operational definition of market emergence to ensure research validity.
- A **Spatial-Index** strategy to maintain performance as agent populations scale.

---

## Part I: Critical Architectural Decisions

### 1. ARCH-001: Multi-Agent Mechanism Architecture

**Decision:** Adopt a **Mechanism-Phase** abstraction (Option B from Planning Review).

**Justification:**
1. **Institutional Visibility:** The core vision defines institutions as swappable modules. A `Mechanism` interface allows the platform to treat a "Double Auction" or a "Bilateral Nash Negotiation" as first-class institutional objects.
2. **Phase Decoupling:** Multi-agent mechanisms (like call auctions) often operate on a different temporal logic than bilateral barter. By delegating the execution to a `Mechanism` object, we avoid bloating the main simulation loop with conditional logic for every new institutional type.
3. **Unified Interface:** Both bilateral protocols and complex market structures can be represented as "venues" where agents submit actions and the mechanism returns transfers.

**Proposed Implementation:**
Introduce a `Mechanism` abstract base class. The `Simulation.step()` will include an `EXCHANGE` phase that iterates through all active `Mechanism` instances. Bilateral exchange is simply a `Mechanism` involving two agents.

---

### 2. Production: Minimal Model

**Decision:** Defer implementation until Phase 4, but ensure **Commodity Space Extensibility**.

**Justification:**
1. **Research Focus:** The first program (Market Emergence) is fundamentally about the transition from barter to market price discovery in an exchange economy. Production introduces supply-side dynamics that confound the study of institutional effects on trade frictions.
2. **Minimal Interference:** Production should be modeled as an agent's internal "transformation mechanism." By keeping the `Bundle` and `Mechanism` interfaces clean now, we can add a `ProductionMechanism` later that maps an input bundle to an output bundle based on technology.

---

### 3. Roles and Asymmetry: Buyer/Seller & Proposer/Responder

**Decision:** **Endogenous Economic Roles** with **Mechanism-Assigned Procedural Roles**.

**Justification:**
1. **Economic Realism:** In a general equilibrium framework, "buyer" and "seller" are not fixed identities but emergent states based on MRS relative to market prices. Agents should realize they are sellers when their endowment of $x$ is high and their preference for $x$ is low.
2. **Procedural Clarity:** Rules like "who proposes first" are institutional, not behavioral. The `Mechanism` should assign these roles (e.g., `Proposer`, `Responder`) to participants upon entry.
3. **Symmetry:** This preserves the symmetry of the `Agent` class while allowing asymmetric protocols (like TIOLI or Posted Price) to function.

---

## Part II: Agent Architecture Decisions

### 4. Belief Representation: Minimal Model

**Decision:** **Recursive Sufficient Statistics** (Mean/Variance) with a **Bayesian Update** path.

**Justification:**
1. **Computational Tractability:** Storing full distributions or long histories for $N^2$ pairs is prohibitive. Mean and variance (Welford's algorithm) allow $O(1)$ updates and $O(1)$ storage per belief.
2. **Decision Relevance:** For Cobb-Douglas agents, the "expected price" and "confidence" (uncertainty) are the primary drivers of search and reservation price decisions.
3. **Consistency:** This aligns with "Bounded Rationality" as an experimental variable. We can compare agents with "Perfect Memory" vs. "Moving Average Memory" vs. "Bayesian Priors."

--- 

### 5. Price Definition in 2-Good Barter

**Decision:** **Transaction Exchange Rate** ($\Delta y / \Delta x$) as the Primary Observable.

**Justification:**
1. **Law of One Price:** Market emergence is characterized by the convergence of exchange rates across space and time.
2. **Empirical Grounding:** In real-world barter, the exchange rate is the only "price" visible to participants.
3. **Benchmark Comparison:** This allows direct comparison to the Walrasian price ratio $p^*$. We will also track **Shadow Prices** (MRS) as an internal metric for efficiency analysis.

---

## Part III: Institutional Design Decisions

### 6. Information Taxonomy

**Decision:** Prioritize **Private Values with Noisy Signals** (Incremental from MVP).

**Justification:**
1. **Path of Least Resistance:** The current `NoisyAlphaInformation` already provides a foundation. Generalizing this to a `SignalEnvironment` is the most direct path to "Institutional Visibility."
2. **Signaling vs. Screening:** Signaling (Spence) is more naturally modeled in our agent-centric framework (agents *choose* to signal) than Screening, which often requires centralized menu design.
3. **Theoretical Richness:** Private values allow us to study the "Winner's Curse" and "Adverse Selection" without the extreme complexity of Common Values models.

---

### 7. Benchmarks: Essential Set

**Decision:** **Walrasian Competitive Equilibrium** and **Gains-from-Trade Efficiency**.

**Justification:**
1. **Walrasian Benchmark:** For Cobb-Douglas, the competitive equilibrium is unique and easily computed. It provides the "North Star" for price convergence.
2. **Efficiency Metrics:** We must measure how much of the potential surplus is captured. This is more critical for the "Market Failure" research agenda than complex Core membership checks (which are $O(2^N)$).
3. **Core Membership (Optional):** Only for small-population validation runs.

---

## Part IV: Research Infrastructure Decisions

### 8. Market Emergence: Operational Definition

**Decision:** A **Triple-Condition Threshold**.
1. **Price Dispersion:** $CV(\text{Price}) < \epsilon$ (Law of One Price).
2. **Allocative Efficiency:** $\text{Realized Surplus} / \text{Potential Surplus} > 1 - \delta$.
3. **Network Connectivity:** The trade graph must be a single giant component (integrated market).

**Justification:**
- Price convergence alone doesn't prove an efficient market (could converge to a "bad" price).
- Efficiency alone doesn't prove a "market" (could be a few lucky bilateral trades).
- Network integration ensures the "market" is a systemic phenomenon, not a collection of isolated islands.

---

### 9. Experimental Design Representation

**Decision:** **Declarative Factorial YAML** with a **Seed-Replicate** structure.

**Justification:**
1. **Reproducibility:** A single YAML file should describe the entire experiment (all 1000+ runs).
2. **Parallelization:** This format is natively compatible with batch runners and HPC cluster managers.
3. **Comparison:** It allows researchers to easily define a "Sweep" over a specific parameter (e.g., `noise_std: [0, 0.1, 0.2]`).

---

### 10. Performance and Scaling: $O(N^2)$ Strategy

**Decision:** **Spatial Bucketing (Grid-Based Indexing)** for Search and Matching.

**Justification:**
1. **Locality:** Agents rarely need to evaluate partners on the other side of the grid. $O(N \cdot R^2)$ where $R$ is perception radius is far superior to $O(N^2)$.
2. **Memory Efficiency:** Grid bucketing fits the existing `Grid` class naturally.
3. **Realistic Frictions:** Real economic agents have local information. Global $O(N^2)$ search is an unrealistic benchmark that should be an optional "Perfect Information" flag.

---

## Conclusion and Next Steps

This proposal provides a coherent path forward. The immediate next step is to implement the **Mechanism Abstraction** (ARCH-001) as it is the prerequisite for all Phase 2 institutional primitives. We will then proceed to Phase 0 (Theoretical Alignment) to ensure the foundation is rock-solid.
