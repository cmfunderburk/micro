# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research-first agent-based microeconomics platform that gives canonical theoretical microeconomics computational form. The core insight is **institutional visibility**: making economic institutions (bargaining protocols, information structures, search mechanisms) explicit, configurable, and comparable.

See VISION.md for the authoritative statement of project identity and methodology.

## Architecture (Planned)

The platform consists of:
- **Core Engine**: Agents, simulation loop, events, phases, snapshots
- **Modules**: Preference foundations, consumer choice, production, bilateral exchange, search markets, signaling (developed as needed)
- **NxN Grid Visualization**: Spatial grounding for search, matching, and information phenomena

## Theoretical Grounding Requirements

All behavioral rules, bargaining protocols, and institutional mechanisms must have formal justification from:
- Canonical texts: Kreps (I/II), Osborne & Rubinstein (Bargaining, Game Theory), MWG
- Axiomatic foundations (Nash bargaining)
- Game-theoretic equilibrium (Rubinstein SPE)
- Learning theory (RL, evolutionary dynamics)
- Published literature

"It works" or "intuitive heuristic" are not valid justifications.

## Document Hierarchy

1. **VISION.md** - Authoritative on identity, scope, methodology
2. **theoretical-foundations.md** - Textbook mappings
3. **CLAUDE.md** - Development guidance

Architecture emerges through development rather than upfront specification.

## First Milestone: Grid Search and Matching

Build simulation infrastructure (no visualization yet) for agents searching on an NxN grid.

**Agent capabilities:**
- **Perception radius**: How much of the grid an agent can observe (configurable)
- **Movement budget**: Squares-per-tick (default: 1)
- **Target selection**: Agents search for other agents/opportunities that maximize expected utility, discounted per tick

**Economic grounding:**
- Perception radius = information structure (limited vs complete information)
- Movement budget = search cost (time/opportunity cost)
- Discounting = patience / time preference
- Target selection = utility maximization under constraints

**Coupling search and bargaining:**

Search is only meaningful when agents can anticipate gains from trade. Agents need to evaluate potential partners by computing expected surplus. The Nash bargaining solution serves as the default "reduced form" for expected outcomes:
- Axiomatic foundation (not tied to specific protocol mechanics)
- Unique prediction given preferences and disagreement point
- Agents use this to evaluate opportunities even if actual bargaining protocol differs

Target selection logic:
```
For each agent j in perception radius:
    expected_surplus[j] = nash_bargaining_surplus(self, j)
    discounted_value[j] = expected_surplus[j] * δ^(ticks_to_reach_j)
Move toward argmax(discounted_value)
```

**Economic structure:**
- 2-good economy
- Cobb-Douglas preferences: u(x,y) = x^α * y^(1-α)
- Heterogeneous endowments (drives gains from trade)

**Agent state vs. observable type:**

Agents have two distinct components:

1. **Private state**: The agent's true characteristics
   - Utility function (Cobb-Douglas α parameter)
   - Endowments (holdings of each good)
   - These determine actual behavior and payoffs

2. **Type**: Publicly observable characteristics
   - What other agents can perceive within their perception radius
   - The information available for evaluating potential trade partners
   - Content depends on the information environment

This separation is architecturally critical:
- **Full information**: Type exposes preferences and endowments (MVP default)
- **Private information**: Type may be hidden or partially revealed
- **Signaling**: Agents take costly actions to reveal type
- **Mechanism design**: Institutions elicit type reports

For the first milestone, type = private state (complete information). But the abstraction must keep them separate to support future information environments.

This aligns with game-theoretic foundations where "type" specifically means the publicly-relevant characteristics that other players can condition on (O&R-G Ch 11, Kreps II Ch 20-21).

**Scope:**
- Grid representation and agent placement
- Agent with private state (utility function, endowments) and observable type
- Information environment configuration (MVP: full information, type = private state)
- Simulation tick loop
- Movement and meeting mechanics
- Nash bargaining surplus calculation (for search evaluation, based on observed types)
- Exchange mechanics when agents meet (Nash bargaining outcome)
