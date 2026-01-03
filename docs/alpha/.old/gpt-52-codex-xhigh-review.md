# 0.0.1 Pre-Alpha Comprehensive Review (GPT-5.2 Codex, x-high)

## Critical Findings (Blockers for 0.0.1)
- Rubinstein protocol tests still assert proposer advantage, but the implementation uses BRW asymmetric Nash where proposer identity should not matter; this is a direct theoretical inconsistency that breaks the "absolute certainty" requirement. `tests/test_bargaining.py:456` `tests/test_bargaining.py:499` `src/microecon/bargaining.py:12` `src/microecon/bargaining.py:579`
- Reproducibility is not guaranteed even with explicit seeds because agent IDs are random UUIDs and tie-breaking is lexicographic on IDs; this can change partner selection and trade order across runs. `src/microecon/agent.py:103` `src/microecon/search.py:134` `src/microecon/simulation.py:344`
- Matching protocol is not recorded in run metadata, so matching comparisons are not auditable and "institutional visibility" is lost in logs/analysis. `src/microecon/logging/events.py:12` `src/microecon/batch.py:145` `src/microecon/visualization/browser.py:326`
- Scenario runner is too narrow to meet the nonnegotiable "fleshed out scenario runner" goal; it only runs opportunistic vs stable matching, hardcodes Nash bargaining, and fixes ticks at 50 with no scenario-controlled parameters. `src/microecon/visualization/browser.py:208` `src/microecon/visualization/browser.py:320` `src/microecon/visualization/browser.py:377`
- Additional bargaining protocols (TIOLI + at least one more) are not implemented yet, so the nonnegotiable "few more protocols" is unmet. `src/microecon/bargaining.py:890` `src/microecon/bargaining.py:932`

## High-Severity Findings
- The public API still exposes fixed-pie Rubinstein share formulas and module docs still describe first-mover advantage; this contradicts the exchange-economy BRW formulation used elsewhere and risks misuse. `src/microecon/bargaining.py:12` `src/microecon/bargaining.py:518` `src/microecon/__init__.py:17`
- Documentation drift is substantial in core reference docs, which undermines theoretical certainty and onboarding. `STATUS.md:22` `STATUS.md:38` `STATUS.md:138` `STATUS.md:161` `CLAUDE.md:64` `CLAUDE.md:113` `CLAUDE.md:121` `THEORETICAL_TESTS.md:11`
- Scenario coordinate convention is ambiguous; YAML positions are treated as (x, y) but tests and grid APIs use (row, col), causing silent transposition risk. `src/microecon/visualization/browser.py:361` `src/microecon/grid.py:99`

## Medium-Severity Findings
- Distance discounting assumes movement_budget=1; if movement_budget changes, search and matching use incorrect ticks_to_reach. `src/microecon/search.py:128` `src/microecon/simulation.py:231`
- Wraparound support is inconsistent: grid supports wrap, but commitment maintenance uses unwrapped Euclidean distance and docs claim toroidal default. `src/microecon/simulation.py:437` `src/microecon/grid.py:111` `STATUS.md:22`
- Scenario loader silently drops invalid YAML without surfacing errors, which makes the scenario browser fail quietly and hides authoring mistakes. `src/microecon/scenarios/loader.py:137`
- Logged TargetEvaluation fields are labeled as Nash surplus, but protocol-aware search means these values may be Rubinstein/TIOLI/etc; analysis labels will be misleading. `src/microecon/search.py:6` `src/microecon/logging/events.py:82`
- Unused or legacy code paths remain (Rubinstein allocation helper, mutual surplus helper, legacy execute_trade import), which adds confusion to the theoretical surface. `src/microecon/bargaining.py:494` `src/microecon/bargaining.py:628` `src/microecon/simulation.py:21`

## Low-Severity Findings
- Visualization color encoding uses alpha only, not goods-mix encoding described in the visualization vision; this is a mismatch but not a blocker for 0.0.1. `src/microecon/visualization/app.py:22` `VISUALIZATION.md:57`
- Always-on movement trails and limited overlay toggles conflict with stated UI/UX intent for progressive disclosure. `src/microecon/visualization/app.py:615` `VISUALIZATION.md:106`
- Version labeling is inconsistent (pyproject 0.1.0 vs alpha 0.0.1), though you requested leaving it unchanged for now. `pyproject.toml:3` `STATUS.md:3`

## Nonnegotiable Readiness Assessment
| Requirement | Current state | Required work |
| --- | --- | --- |
| Fleshed out scenario runner | Basic UI exists but only fixed comparison and fixed ticks | Add protocol selection, scenario-controlled ticks, optional single-run mode, log metadata, and scenario validation |
| Additional bargaining protocols | Only Nash and Rubinstein (BRW) implemented | Implement TIOLI and one more canonical protocol, update expected surplus logic and tests |
| Absolute theoretical certainty | BRW changes not fully reflected in tests/docs | Align tests, docs, API surface, and logging labels with actual theory |

## 0.0.1 Build Recommendations (Ordered)
- Fix Rubinstein theory alignment: update tests to match BRW, clarify or remove fixed-pie rubinstein_share API, and update module-level docs. `tests/test_bargaining.py:456` `src/microecon/bargaining.py:12` `src/microecon/bargaining.py:518`
- Make reproducibility deterministic by default: replace UUID agent IDs with a seeded or sequential scheme when using scenario runner and create_simple_economy; keep UUIDs optional. `src/microecon/agent.py:103` `src/microecon/simulation.py:344`
- Extend run metadata to include matching protocol and scenario name; update analysis grouping to include matching. `src/microecon/logging/events.py:12` `src/microecon/batch.py:145` `src/microecon/analysis/loader.py:39`
- Expand scenario runner: allow scenario YAML to declare protocol(s), tick count, and expected outcomes; surface YAML parse errors in UI; enable single-run + comparison modes. `src/microecon/visualization/browser.py:208` `src/microecon/scenarios/loader.py:137`
- Implement TIOLI plus one additional canonical protocol (suggested: posted-price or Kalai-Smorodinsky) with explicit theoretical references, compute_expected_surplus implementations, and tests. `src/microecon/bargaining.py:890` `src/microecon/bargaining.py:932`
- Bring docs up to date with code reality and theoretical choices, especially STATUS.md, CLAUDE.md, and THEORETICAL_TESTS.md. `STATUS.md:22` `CLAUDE.md:113` `THEORETICAL_TESTS.md:11`

## Scenario Runner Expansion (Concrete Targets)
- Add per-scenario runtime controls (ticks, seed, protocol selection) to YAML and UI, and default to deterministic seeds for reproducibility. `src/microecon/scenarios/schema.py:41` `src/microecon/visualization/browser.py:326`
- Encode expected outcomes in YAML (e.g., target welfare/trades) and show them in UI; optionally validate after run and flag divergence. `docs/DESIGN_dashboard_integration.md:122` `src/microecon/visualization/browser.py:251`
- Allow single-protocol runs for theory validation, not only comparison runs. `src/microecon/visualization/browser.py:307`

## Theoretical Certainty Checklist
- Update Rubinstein tests that assume proposer advantage, and add direct BRW regression tests for expected weights and allocations. `tests/test_bargaining.py:456` `tests/test_bargaining.py:517`
- Rename or annotate all "Nash surplus" labels in search/logging to "expected surplus" and document protocol-dependence. `src/microecon/search.py:6` `src/microecon/logging/events.py:82`
- Add tests for TIOLI and the second protocol, including search expected surplus behavior and matching preference ordering. `tests/test_search.py:9` `tests/test_matching.py:147`

## UX/UI Concerns (For Personal Use)
- Scenario browser currently hides YAML errors and gives no explanation when scenarios fail to load; surface errors in the UI or log to console. `src/microecon/scenarios/loader.py:137` `src/microecon/visualization/browser.py:215`
- Comparison view is strong, but lacks scenario context in the UI (title, description, what to watch), which is useful for validating theory quickly. `src/microecon/visualization/app.py:1018`

## Positive Alignment Notes (Brief)
- Institutional visibility is already visible in matching/bargaining comparisons, and the test suite has solid theoretical coverage for small-N scenarios. `tests/scenarios/test_trading_chain.py:1` `STATUS.md:52`
- The BRW correction and protocol-aware search are aligned with VISION.md's emphasis on theoretical rigor and institutional visibility. `src/microecon/bargaining.py:579` `src/microecon/search.py:119`

## Open Questions to Resolve During Implementation
- Should rubinstein_share remain as a fixed-pie helper (with explicit naming) or be removed from the public API to prevent misuse? `src/microecon/bargaining.py:518` `src/microecon/__init__.py:17`
- Should scenario YAML be the single source of truth for theoretical scenarios, or should tests continue to hardcode them in Python? `tests/scenarios/test_two_agent.py:1` `scenarios/two_agent_baseline.yaml:1`

## Verification Notes
- Tests were not run in this review; prioritizing a full run after reconciling BRW-related tests is advised.
