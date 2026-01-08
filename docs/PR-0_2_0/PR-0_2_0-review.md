# PR 0.2.0 Review Report

## Findings (ordered by severity)

### High
- Rubinstein protocol semantics are inconsistent with tests and documentation; the implementation uses BRW asymmetric Nash (no proposer advantage), while protocol docs and tests still assert proposer advantage, which will fail or mislead analyses if first-mover effects are expected. Evidence: `src/microecon/bargaining.py:650-725`, `tests/test_bargaining.py:421-469`.

### Medium
- Commitment matching discounts distance using `Position.chebyshev_distance_to` without grid wrapping, but search/movement use wrapped Chebyshev distance; if `Grid.wrap=True`, partner rankings and commitments will be inconsistent with actual movement costs. Evidence: `src/microecon/simulation.py:223-237`, `src/microecon/grid.py:286-292`.
- The simulation always computes full `evaluate_targets_detailed` results even when no logger is attached, which adds O(n^2) evaluation work and memory pressure in non-logging runs; this is a performance regression for larger agent counts. Evidence: `src/microecon/simulation.py:171-185`.

### Low
- Logged `TargetEvaluation.distance` is documented as Euclidean but is now Chebyshev distance (perception is square, not circular), which can mislead downstream analysis or visualizations that assume Euclidean metrics. Evidence: `src/microecon/logging/events.py:107-115`, `src/microecon/grid.py:208-246`, `src/microecon/search.py:240-289`.
- Belief update hooks exist for encounters and observed trades, but the simulation only calls `record_trade_observation`, so beliefs do not update on non-trade encounters or observations. This stalls learning in low-trade regimes and diverges from the belief architecture intent. Evidence: `src/microecon/simulation.py:384-403`, `src/microecon/beliefs.py:380-520`.

## Testing gaps and risk surface
- No integration tests cover commitment breakage when partners leave perception radius, and no tests assert correct commitment lifecycle in committed matching mode with logging enabled.
- New visualization features (Edgeworth popup, export, trade network, agent perspective mode) and data export paths lack automated tests, leaving regressions likely to slip through.
- Belief snapshot logging is not validated in tests (serialization or replay), and there are no tests for belief updates from encounter or observed trade paths.

## VISION.md alignment (current state)
- **Aligned**: Institutional visibility is substantially strengthened with protocol abstractions (Nash vs Rubinstein, opportunistic vs stable roommates), protocol-aware search, and detailed logging/analysis hooks for institutional comparisons.
- **Aligned**: The platform now supports richer empirical analysis (logging, replay, time-series, distributions, emergence metrics), consistent with research-first positioning.
- **Partial**: Information environments beyond full or noisy alpha are not implemented; signaling/screening and private information remain stubs, limiting the information-structure research agenda.
- **Partial**: Equilibrium benchmarks (Walrasian prices, explicit GE comparisons) are still missing, so the "benchmark comparison" axis remains largely aspirational.
- **Not yet**: Additional bargaining institutions (posted prices, double auction, TIOLI) are not present, so institutional breadth is still limited to Nash/Rubinstein.

## VISUALIZATION.md alignment (current state)
- **Aligned**: Core live/replay visualization, grid rendering, agent hover/selection, trade animations, time-series charts, overlays, and data export are now implemented.
- **Aligned**: Trade zoom via Edgeworth box is in place with indifference curves, contract curve, and utility breakdowns, matching the specification.
- **Aligned**: Agent perspective mode and belief visualization exist, enabling information asymmetry inspection.
- **Partial**: Aggregate metrics beyond welfare/trade count (distribution, Gini, clustering) are not fully surfaced in the UI.
- **Partial**: Benchmark comparison overlays (e.g., Nash vs actual or Walrasian) are not implemented.
- **Partial**: Layout modes (setup/run/analyze) and keyboard-first controls are not fully developed; live config modal exists but mode switching is not explicit.
- **Open aesthetic items**: Color palette, typography, and final UI layout proportions remain ad hoc relative to the design guidance.

## Open questions and assumptions
- Should Rubinstein remain in the BRW limit (no proposer advantage), or should the implementation/model/testing be aligned with classic alternating-offers proposer advantage? The current mix is inconsistent.
- Is grid wrapping intended to be a first-class feature? If yes, movement and matching distance metrics should be harmonized.
- Should beliefs update on non-trade encounters or observed trades in the core simulation loop, or is trade-only learning the intended baseline?

## Change summary (secondary)
- Added belief architecture (memory, type/price beliefs, update rules) and integrated it into search and trade logging.
- Added matching protocol abstraction with stable roommates implementation and commitment lifecycle management.
- Expanded logging, analysis, and replay infrastructure with richer event schemas and batch runs.
- Major visualization expansion: overlays, Edgeworth trade view, trade history, trade network panel, exports, belief and agent perspective modes, and live configuration modal.
