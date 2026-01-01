# Microecon Platform: Foundational Vision

**Status:** Authoritative foundational document
**Date:** 2026-01-01
**Purpose:** Define the methodological vision, research agenda, and core identity of the platform

---

## 1. What This Is

### Identity

This is a **research-first agent-based microeconomics platform**. It gives canonical theoretical microeconomics (Kreps, MWG, Rubinstein) computational form through simulated agents interacting under configurable institutional rules.

The platform is:
- A **personal research instrument** that may generate publications
- A **methodology contribution** to economics - a new way to study micro
- **Framework-level software** designed for long-term extensibility

The platform is not primarily:
- A teaching tool (though it has pedagogical value)
- A replacement for existing ABM frameworks
- A tool for specific pre-defined research questions

### Core Insight: Institutional Visibility

The central innovation is **making institutions visible**.

Traditional microeconomics treats institutions as implicit assumptions: the Walrasian auctioneer clears markets instantaneously, agents have costless access to complete information, search is frictionless. These assumptions are buried in model setup and often invisible to the analyst.

This platform makes institutional rules **explicit, configurable, and comparable**:

- Bargaining protocols (Nash, Rubinstein, TIOLI, posted prices) become swappable modules
- Information structures (complete, private, signaled) become configuration choices
- Search and matching (random, directed, algorithmic) become visible mechanisms
- Market structures (bilateral, multilateral, centralized) become observable outcomes

By making institutions visible, we can ask: *What difference does the institution make?* Same preferences, same endowments, different rules - what emerges?

---

## 2. Methodological Position

### Relation to Equilibrium Analysis

Equilibrium analysis is **one tool among many**, neither foundation nor competitor.

The platform computes equilibrium benchmarks (Nash bargaining solution, Walrasian prices, Rubinstein SPE) as **comparison baselines**. Divergence between simulation and benchmark is interesting, not wrong - it reveals what the equilibrium analysis leaves out (dynamics, heterogeneity, path-dependence, bounded rationality).

The platform does not aim to:
- Validate equilibrium theory (simulations should "converge to" predictions)
- Replace equilibrium analysis (agent-based as "alternative paradigm")
- Privilege simulation over theory (emergence as more "real")

### Relation to Textbooks

Canonical texts (Kreps I/II, O&R Bargaining and Game Theory, MWG) are **references for rigor**, not blueprints for implementation.

The texts ensure:
- Bargaining protocols derive from axiomatic or game-theoretic foundations
- Agent behavior has formal justification (optimization, equilibrium, learning rule)
- Concepts map to established theory (no ad-hoc inventions)

The platform may:
- Adapt presentation for spatial/agent-based framing
- Combine concepts across texts creatively
- Develop its own identity distinct from any single textbook

### Relation to ABM and Computational Economics

The platform is distinguished from general ABM frameworks (Mesa, NetLogo) and computational economics traditions by:

1. **Microeconomic specificity**: Purpose-built for preferences, exchange, information, bargaining - not general "emergence"
2. **Economic rigor**: Grounded in canonical theory, not emergent behavior without theoretical anchor
3. **Visualization focus**: Primary emphasis on making economic phenomena visually intuitive

This is not agent-based computational economics in the Tesfatsion/LeBaron tradition. It is theoretical microeconomics given agent-based computational form.

---

## 3. What the Platform Enables

### Value Propositions

**Visualize theory**: See abstract concepts (equilibria, convergence, information asymmetry) come alive through spatial simulation and visual representation.

**Compare mechanisms**: Hold environment constant (preferences, endowments, number of agents) and swap institutional rules. Observe how outcomes differ. The institution becomes the independent variable.

**Study emergence**: Watch macro patterns (prices, trade networks, welfare distributions) emerge from micro interactions. Study when and why markets form, fail, or exhibit pathologies.

### Agent Sophistication as Experimental Variable

Agents can operate at different sophistication levels:
- Rule-based (simple heuristics)
- Bounded rationality (optimize with limits)
- Full rationality (equilibrium strategies)
- Learning (RL, evolutionary dynamics)

These levels exist **for comparison**, not because bounded rationality is inherently interesting. The question is: *What changes when agents are smarter or dumber?* Sophistication is an experimental variable, like the institution.

---

## 4. The Grid and Spatial Grounding

### When Space Adds Value

The NxN grid visualization is **genuinely illuminating** for:

- **Search and matching**: Physical search, meeting costs, local information
- **Bilateral bargaining**: Finding partners before bargaining (bargaining itself is non-spatial)
- **Information and signaling**: Visibility ranges, observation, signal propagation

The grid makes abstract frictions concrete. Search costs become literal movement. Information asymmetry becomes visibility radius. This concreteness aids intuition.

### When Space Is Metaphor

For some phenomena, the grid is metaphor rather than natural:

- **Preferences and choice**: Grid as commodity space is conceptual, not physical
- **Pure bargaining**: The negotiation itself has no spatial dimension

These modules use the grid for visualization but the spatial interpretation is weaker. The platform accommodates both physical and conceptual interpretations.

---

## 5. Research Agenda

### First Major Scenario: Market Emergence

The initial demonstration of institutional visibility: **when and how do markets emerge from bilateral exchange?**

Start with agents capable only of bilateral barter. Under what conditions does "market" behavior emerge - common prices, reliable trading partners, spatial clustering, efficient allocation? How do institutional rules (matching, bargaining, information) affect whether markets form or fail?

This scenario demonstrates:
- Emergence of macro patterns from micro interactions
- Institutional visibility (swap rules, observe differences)
- Comparison to theoretical benchmarks (Walrasian equilibrium)

### Mechanism Comparison Research

**Bargaining protocols**: Nash vs Rubinstein vs TIOLI vs double auction. How do outcomes differ? What drives the differences (patience, commitment, information)?

**Search vs centralized matching**: Decentralized search vs Gale-Shapley algorithm. What does spatial friction cost? When does decentralization outperform?

**Information regimes**: Complete vs private information, signaling vs screening. How does visibility shape behavior and outcomes?

**Market structures**: Bilateral vs posted prices vs auction. Monopoly vs competition. When do price-taking assumptions hold?

### Emergence Patterns

**Price convergence**: How and whether prices converge to Walrasian predictions. Speed, variance, path-dependence.

**Trade networks**: Who trades with whom. Network structure emergence, stability, efficiency.

**Welfare distribution**: How gains from trade distribute across agents. Inequality, bargaining power, institutional effects.

**Market failure**: When and why markets fail to clear. Adverse selection, coordination failure, search frictions.

---

## 6. Scope and Boundaries

### What Is In Scope

Anything that can be modeled in the microeconomic tradition in an agent-based setting. In theory, this covers practically all of economics.

The practical boundary is complexity: some phenomena require substantial infrastructure to model properly. The platform grows toward comprehensiveness but must remain tractable.

### Conceptual Non-Goals

The platform does not aim for:
- Macro phenomena (business cycles, growth) except as emergent from micro
- Massive scale (millions of agents) at expense of comprehensibility
- Real-world calibration (matching empirical data, parameter estimation)

These are not ruled out permanently but are not the driving focus.

---

## 7. Architecture Principles

### Framework-Level Investment

The platform invests upfront in robust, extensible architecture. This is not minimal-viable-product thinking. The goal is long-term flexibility for unforeseen research needs.

The core engine (agents, simulation loop, events, phases, snapshots) receives detailed specification. This infrastructure supports all future modules and must be stable.

### Organic Module Growth

Modules emerge from research needs rather than upfront specification. The preference foundations module exists; other modules (consumer choice, production, bilateral exchange, search markets, signaling) will develop as needed.

Module design follows patterns established by early modules but adapts to domain specifics. Comprehensive upfront specification of all modules is premature.

### Theoretical Grounding as Constraint

No ad-hoc solutions. Every behavioral rule, bargaining protocol, and institutional mechanism must have formal justification:
- Textbook derivation (Kreps, O&R, MWG)
- Axiomatic foundation (Nash bargaining)
- Game-theoretic equilibrium (Rubinstein SPE)
- Learning theory (RL, evolutionary)
- Published literature

"It works" is not justification. "It's an intuitive heuristic" is not justification. The platform maintains theoretical rigor even when implementation is creative.

---

## 8. Success Criteria

### 2-3 Year Horizon

The platform is successful if it:

1. **Enables personal research**: Functions as a productive research instrument for investigating economic phenomena
2. **Generates publications**: Produces novel results or methodological contributions worthy of publication

External adoption (teaching use, community contributions) is welcome but not primary.

### Minimum Viable Demonstration

The first compelling demonstration: **N agents in a search market with configurable matching and bargaining**, showing:
- Market emergence under different institutional rules
- Comparison to theoretical benchmarks
- Visual intuition for how institutions shape outcomes

This demonstrates institutional visibility, the core methodological insight.

---

## 9. Relationship to Prior Work

### From VMT

The platform takes inspiration from VMT's problem space:
- NxN grid visualization
- Agent movement, search, interaction
- Bilateral exchange
- Configurable protocols


### New in This Platform

- Institutional visibility as core methodological contribution
- Canonical theoretical grounding (Kreps/O&R/MWG)
- Framework-level architecture for long-term extensibility
- Agent sophistication as experimental variable
- Equilibrium benchmarks as comparison baselines

---

## 10. Document Hierarchy

This document (**VISION.md**) is the authoritative statement of project identity and direction.

Other documents serve supporting roles:
- **theoretical-foundations.md**: Textbook mappings and implementation notes
- **CLAUDE.md**: Development guidance and conventions

Architecture emerges through development rather than upfront specification.

When documents conflict, this vision document takes precedence on matters of identity, scope, and methodology.

---

**Document Version:** 1.0
**Created:** 2026-01-01
