# Consolidated Issues: Post-Alpha Review

**Created:** 2026-01-05
**Sources:** REVIEW_0.1.0.md, claude-alpha-review.md
**Structure:** By subsystem, ordered by logical dependency within each

---

## Overview

This document consolidates findings from two independent reviews:
- **REVIEW_0.1.0.md** — Completion criteria alignment focus
- **claude-alpha-review.md** — Code quality and theoretical soundness focus

Where reviews disagree or frame issues differently, reconciliation notes are provided.

### Subsystem Index

| Subsystem | Issues | Critical | Checklist |
|-----------|--------|----------|-----------|
| [Core Engine](#1-core-engine) | 8 | 2 | [issues-core-engine.md](issues-core-engine.md) |
| [Logging & Analysis](#2-logging--analysis) | 4 | 1 | [issues-logging-analysis.md](issues-logging-analysis.md) |
| [Visualization](#3-visualization) | 3 | 0 | [issues-visualization.md](issues-visualization.md) |
| [Documentation](#4-documentation) | 4 | 0 | [issues-documentation.md](issues-documentation.md) |
| [Testing](#5-testing) | 3 | 0 | [issues-testing.md](issues-testing.md) |

---

## 1. Core Engine

Issues in `simulation.py`, `bargaining.py`, `search.py`, `matching.py`, `information.py`, `agent.py`, `grid.py`, `bundle.py`.

### CE-1: Information asymmetry does not affect behavior (CRITICAL)

**Sources:** REVIEW_0.1.0 §1, §6
**Agreement:** Single source, not addressed in claude-alpha-review

`NoisyAlphaInformation` exists but observed types are not used in search, matching, or bargaining decisions. The information environment is architecturally present but behaviorally inert.

**Dependency:** Unblocks CE-2, T-1, V-1

### CE-2: Self-observation applies noise incorrectly

**Sources:** REVIEW_0.1.0 §6
**Agreement:** Single source

When `evaluate_targets` uses `info_env.get_observable_type` on the observer, noise is applied to the observer's own alpha. Agents should know their own preferences exactly.

**Dependency:** Blocked by CE-1 (only matters if info env is used)

### CE-3: Reproducibility not guaranteed (CRITICAL)

**Sources:** REVIEW_0.1.0 §2
**Agreement:** Single source

Two issues undermine deterministic runs:
1. `Simulation` uses global `random` module for proposer selection (not seeded per-simulation)
2. Agent IDs use `uuid` (not seeded), and IDs are used as tie-breakers in search

**Dependency:** Independent, but affects LA-1 (logging completeness)

### CE-4: Distance metric inconsistency

**Sources:** claude-alpha-review §3.1
**Agreement:** Single source

Perception radius uses Euclidean distance, movement uses Chebyshev. Creates edge cases where agents see targets they can't reach optimally.

**Dependency:** Independent

### CE-5: Wrapped grid Chebyshev missing

**Sources:** claude-alpha-review §3.3
**Agreement:** Single source

`Position.chebyshev_distance_to()` doesn't account for wrapping when `grid.wrap=True`.

**Dependency:** Related to CE-4

### CE-6: Dead Rubinstein code

**Sources:** claude-alpha-review §2.2
**Agreement:** Single source

`_solve_rubinstein_allocation()` (96 lines) is defined but never called after BRW transition. The `proposer` parameter is vestigial.

**Dependency:** Independent (cleanup)

### CE-7: Legacy execute_trade function

**Sources:** claude-alpha-review §3.4
**Agreement:** Single source

Standalone `execute_trade()` always uses Nash, predates protocol abstraction. Creates dual API paths.

**Dependency:** Independent (cleanup)

### CE-8: Unsafe Bundle construction

**Sources:** claude-alpha-review §3.2
**Agreement:** Single source

`Bundle.__sub__` uses `_unsafe_init` bypassing validation. Could allow invalid bundles if callers forget to validate.

**Dependency:** Independent (future improvement)

---

## 2. Logging & Analysis

Issues in `logging/events.py`, `analysis/emergence.py`, `scenarios/market_emergence.py`.

### LA-1: Logging config missing institutional metadata (HIGH)

**Sources:** REVIEW_0.1.0 §4
**Agreement:** Single source

`SimulationConfig` only stores bargaining protocol. Missing: matching protocol, information environment, noise parameters.

**Dependency:** Blocked by CE-3 (full reproducibility requires determinism first)

### LA-2: MRS trend metric missing (HIGH)

**Sources:** REVIEW_0.1.0 §5
**Agreement:** Single source

Completion criteria expects MRS trends in market emergence measures. No MRS time-series analysis exists.

**Dependency:** Independent

### LA-3: Welfare efficiency calculation flawed (CRITICAL)

**Sources:** claude-alpha-review §2.1
**Reconciliation:** REVIEW_0.1.0 mentions "theoretical max is upper bound, acceptable if documented" but doesn't identify the calculation errors.

Two compounding problems in `compute_theoretical_max_gains()`:
1. **Overcounting pairs:** Sums ALL pairwise surpluses, but agents can only trade once
2. **Undercounting per pair:** Uses `gains_1` only, not bilateral total

**Dependency:** Independent

### LA-4: MarketEmergenceConfig lacks validation (LOW)

**Sources:** REVIEW_0.1.0 §9
**Agreement:** Single source

Unknown `endowment_types` raises KeyError during agent creation instead of clear error message.

**Dependency:** Independent

---

## 3. Visualization

Issues in `visualization/app.py`, `visualization/replay.py`.

### V-1: Perceived vs true visualization missing (HIGH)

**Sources:** REVIEW_0.1.0 §3
**Agreement:** Single source

`AgentSnapshot` only logs true alpha. No data path for observed types, so UI can't show perceived vs actual.

**Dependency:** Blocked by CE-1 (requires info env to be behaviorally meaningful first)

### V-2: Monolithic app.py

**Sources:** claude-alpha-review §7.1
**Agreement:** Single source

1,912 lines in single file. Suggested decomposition into colors, proxies, rendering, controls, metrics modules.

**Dependency:** Independent (maintainability)

### V-3: Hardcoded layout dimensions

**Sources:** claude-alpha-review §7.2
**Agreement:** Single source

Fixed window dimensions don't scale for different displays.

**Dependency:** Independent (polish)

---

## 4. Documentation

Issues in `STATUS.md`, `CLAUDE.md`, `README.md`, `docs/comparative-study.md`.

### D-1: STATUS.md contradictions (MEDIUM)

**Sources:** REVIEW_0.1.0 §7
**Agreement:** Both reviews note documentation issues

Examples:
- Claims "Search uses Nash surplus regardless of protocol" but search uses active protocol
- Claims "No configuration files" but YAML scenarios exist
- Says info regimes implemented, but behavior ignores info_env

**Dependency:** Should follow CE-1 resolution (behavior changes affect what's documented)

### D-2: Python version mismatch

**Sources:** claude-alpha-review §4.1
**Agreement:** Single source

README says 3.11+, pyproject.toml requires 3.12+.

**Dependency:** Independent (trivial fix)

### D-3: CLAUDE.md outdated

**Sources:** claude-alpha-review §4.4
**Agreement:** Single source

"Next Development Directions" lists already-implemented items (time series charts, config files).

**Dependency:** Independent

### D-4: STATUS.md file structure outdated

**Sources:** claude-alpha-review §4.2
**Agreement:** Single source

Missing: `scenarios/`, `visualization/browser.py`, `visualization/timeseries.py`, `analysis/emergence.py`.

**Dependency:** Independent

---

## 5. Testing

Issues in test suite and comparative study methodology.

### T-1: Integration tests don't validate info environment effects (MEDIUM)

**Sources:** REVIEW_0.1.0 §8
**Agreement:** Single source

Tests run `NoisyAlphaInformation` but don't assert behavioral differences. Visualization data flow left to manual testing.

**Dependency:** Blocked by CE-1 (can't test effects that don't exist)

### T-2: pytest.mark.slow unregistered

**Sources:** claude-alpha-review §5.3
**Agreement:** Single source

Warning: `PytestUnknownMarkWarning: Unknown pytest.mark.slow`

**Dependency:** Independent (trivial)

### T-3: Comparative study single-seed limitation

**Sources:** claude-alpha-review §6.3, REVIEW_0.1.0 §2.2
**Reconciliation:** Both note this, framed differently

Study uses single seed (42), 30 agents, 80 ticks. Results not statistically rigorous.

**Dependency:** Blocked by CE-3 (multi-seed only meaningful with determinism)

---

## Dependency Graph

```
CE-1 (info env behavior)
  ├── CE-2 (self-observation)
  ├── V-1 (perceived vs true viz)
  ├── T-1 (info env tests)
  └── D-1 (STATUS.md accuracy)

CE-3 (reproducibility)
  ├── LA-1 (logging completeness)
  └── T-3 (multi-seed study)

LA-3 (welfare calculation) — independent
LA-2 (MRS metrics) — independent
CE-4, CE-5 (distance metrics) — related pair
CE-6, CE-7 (dead code cleanup) — independent pair
```

---

## Recommended Session Order

1. **Session A:** CE-3 (reproducibility) — foundational, unblocks logging and study improvements
2. **Session B:** CE-1 + CE-2 (info env behavior) — enables testing and viz features
3. **Session C:** LA-3 (welfare calculation) — theoretical correctness
4. **Session D:** LA-1 + LA-2 (logging + MRS) — analysis completeness
5. **Session E:** V-1 + T-1 (perceived viz + tests) — requires CE-1 complete
6. **Session F:** D-1 through D-4 (documentation sweep) — after behavior changes
7. **Session G:** CE-4 through CE-8, V-2, V-3, T-2, LA-4 (cleanup and polish)
