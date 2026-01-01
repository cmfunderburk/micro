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
2. **comprehensive-spec.md** - Technical architecture (when created)
3. **theoretical-foundations.md** - Textbook mappings (when created)
4. **CLAUDE.md** - Development guidance
