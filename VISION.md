# Microecon Platform: Vision

**Status:** Authoritative foundational document
**Purpose:** Define the identity, methodology, and theoretical grounding of the platform

---

## 1. What This Is

A research framework and platform for simulating and visualizing economic agents on a spatial grid.

**Individual decisions** follow decision theory (Kreps I): agents have preferences, face constraints, and optimize. This need not be "pure" rationality—prospect theory, bounded rationality, and learning rules are all mathematically specifiable within this framework.

**Coordination** follows game theory (Kreps II, O&R): when agents must coordinate with others—bargaining, matching, any N-agent interaction—the interaction is governed by game-theoretic mechanisms with known equilibrium properties.

**Applied orientation** draws from Chicago Price Theory (CPT): while CPT largely takes price-taking and equilibrium as given (not "agent-based" in our sense), it demonstrates the empirical richness of price-theoretic analysis across domains—market equilibrium, factor markets, durable goods, health, addiction, crime. CPT provides guidance for what the general approach can illuminate.

The platform gives these theoretical foundations computational form through simulation.

---

## 2. Theoretical Architecture

### Layer 1: Individual Decision-Making

Agents are autonomous decision-makers who optimize subject to constraints. The formal foundations come from decision theory:

- Preference axioms (completeness, transitivity, continuity)
- Choice under uncertainty (expected utility, or alternatives like prospect theory)
- Constrained optimization

An agent's "type" in game-theoretic terms derives from attributes (preferences, endowments, patience, beliefs) plus the information environment—it is not primitive.

### Layer 2: Strategic Interaction

When multiple agents interact, coordination problems arise. Game theory provides the analytical tools:

- **Bargaining**: Nash axiomatic solution, Rubinstein alternating-offers, take-it-or-leave-it
- **Matching**: Bilateral proposal/acceptance, search with frictions
- **General mechanisms**: Any N-agent interaction with strategic interdependence

These mechanisms have known equilibrium characterizations. The platform implements them as configurable modules, enabling comparison: same agents, different coordination rules, different outcomes.

### Layer 3: Applied Analysis

Chicago Price Theory demonstrates the scope of price-theoretic reasoning:

- Market equilibrium and competitive analysis
- Factor markets and derived demand
- Durable goods and intertemporal choice
- Extensions to "non-market" domains (health, addiction, crime, family)

CPT's role is not to provide rigorous foundations (that's Kreps/O&R) but to show what questions the framework can address and how to reason about empirical phenomena.

---

## 3. Spatial Representation

Agents operate on a 2D grid. This representation:

- Makes search costs concrete (movement = ticks)
- Gives information structure spatial form (visibility radius, local observation)
- Enables visualization of emergent patterns (clustering, trade networks, market formation)

The grid is the current representation. It may expand to other topologies (networks, continuous space) as research needs evolve. The core decision/game-theoretic architecture is representation-independent.

---

## 4. Institutional Visibility

Making coordination mechanisms explicit has a methodological payoff: **institutions become visible and comparable**.

Traditional theory often buries institutional assumptions (frictionless search, costless information, implicit market clearing). By implementing mechanisms as swappable modules, we can ask: *what difference does the institution make?*

- Same preferences and endowments, different bargaining protocol → different surplus division
- Same agents, different information structure → different equilibrium behavior
- Same environment, different matching mechanism → different efficiency

This is a consequence of the architecture, not its primary purpose. The primary purpose is giving decision theory and game theory computational form.

**Emergent Network Structure**

Agent interactions produce network structure: who trades with whom, who has interacted, who observes whom. This emergent structure is itself an outcome of institutional choices—a dependent variable, not a primitive.

Jackson's *Social and Economic Networks* provides the analytical framework:

- **Descriptive tools**: Degree distributions, clustering coefficients, centrality measures, path lengths—vocabulary for characterizing emergent patterns
- **Theoretical predictions**: What network structures emerge from strategic behavior? Pairwise stability, efficiency, the tension between them
- **Implications of structure**: How network topology affects diffusion, learning, and welfare

The research question extends: same agents, different institution → different emergent network → different aggregate properties. Network analysis complements welfare comparisons as a way of understanding institutional effects.

---

## 5. Scope

The platform addresses phenomena tractable within the microeconomic tradition:

- Exchange and bilateral bargaining
- Search and matching markets
- Information asymmetry, signaling, screening
- Production and factor markets
- Extensions in the Chicago tradition (human capital, health, etc.)

The practical boundary is complexity: some phenomena require substantial infrastructure. The platform grows toward comprehensiveness but remains anchored in the theoretical foundations.

---

## 6. Document Hierarchy

- **VISION.md** (this document): Identity, methodology, theoretical grounding
- **theoretical-foundations.md**: Detailed mappings to primary sources (Kreps, O&R, CPT, Jackson)
- **STATUS.md**: Current implementation state
- **CLAUDE.md**: Development conventions

---

**Document Version:** 2.1
**Updated:** 2026-01-12
