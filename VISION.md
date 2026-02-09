# Microecon Platform Vision

**Status:** Source of truth  
**Last Updated:** 2026-02-09

## 1. Purpose
Microecon is a research platform for computational microeconomics.

The project goal is to make institutional assumptions explicit, configurable, and testable in simulation:
- same agents
- same endowments
- same environment
- different institutional rules
- different observed outcomes

Core research question:

**What difference does the institution make?**

## 2. Theoretical Position
The platform is grounded in three layers:

1. **Decision-theoretic agents**
- Agents have preferences, constraints, and a decision procedure.
- Rationality level is a model variable (fully rational, bounded, heuristic, learning).

2. **Game-theoretic interaction mechanisms**
- Coordination and exchange are governed by explicit mechanisms.
- Mechanisms should map to known theoretical objects where possible.

3. **Applied microeconomic interpretation**
- Results are analyzed in welfare, efficiency, distribution, and network terms.
- The platform prioritizes interpretable mechanism comparisons over black-box behavior.

## 3. Platform Identity
This is not a generic ABM sandbox.

It is a mechanism-comparison laboratory for microeconomic institutions, centered on:
- bargaining rules
- matching/clearing rules
- information regimes
- search frictions and transaction costs

## 4. Current Scope
Current implemented domain:
- two-good exchange economy
- bilateral trade
- spatial search on discrete grid
- action-based tick model
- protocol-comparison workflows via tests, analysis, and web UI

Current implemented institutional flexibility:
- bargaining: Nash, Rubinstein (BRW mapping), Asymmetric Nash, TIOLI
- information: full and noisy-alpha observation
- decision procedure: rational baseline with opportunity-cost acceptance logic

## 5. Direction of Expansion
Priority expansion areas:
1. Make matching/clearing as explicit and swappable as bargaining.
2. Strengthen benchmark interpretation (e.g., equilibrium/reference comparisons).
3. Move from finite exchange episodes toward sustained economies (consumption/replenishment loops).
4. Increase belief/information causality in decisions and acceptance behavior.

## 6. Design Principles
1. **Institutional visibility over hidden assumptions**
- Rules must be explicit in code and configuration.

2. **Comparability by construction**
- Hold initial conditions fixed across institutional variants.

3. **Theory-linked implementation**
- Prefer constructs with clear micro/game-theory interpretation.

4. **Determinism and reproducibility**
- Seeded runs and deterministic tie-breaking where practical.

5. **Analysis-first instrumentation**
- Logging and metrics are first-class, not an afterthought.

6. **Separation of normative docs**
- Vision and architecture documents define intent and model semantics.
- Time-stamped reviews/chats are reference artifacts and should be archived.

## 7. Non-Goals (For Now)
- Macroeconomic calibration or policy forecasting.
- High-frequency/continuous-time market microstructure realism.
- Domain-specific production sectors with heavy empirical calibration.

## 8. Success Criteria
The platform is successful when it can reliably support:
- controlled institutional A/B comparisons
- theory-consistent behavior in core mechanisms
- interpretable, reproducible outputs
- efficient reorientation for new work without document ambiguity

## 9. Documentation Hierarchy
Primary active documents:
1. `VISION.md` (this file): identity, scope, and design principles
2. `docs/current/AGENT-ARCHITECTURE.md`: implemented architecture and invariants
3. `STATUS.md`: operational capabilities and known limitations
4. `theoretical-foundations.md`: theory mappings and references

Historical, exploratory, and date-stamped docs belong in `.archived/`.
