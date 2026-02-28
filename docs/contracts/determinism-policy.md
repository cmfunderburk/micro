# Determinism Policy

**Version:** 1.0
**Enforcement:** `tests/test_determinism.py` (pytest marker: `determinism`)

---

## Guarantee

Running the same `SimulationConfig` (same seed, same parameters) must produce identical `TickRecord` sequences within the tolerance defined below.

## Tolerance Rules

| Field Type | Comparison | Threshold |
|---|---|---|
| Integer (tick, position, trade count) | Exact match | 0 |
| Float (welfare, utility, surplus, gains) | Absolute difference | `< 1e-10` |
| String (agent IDs, proposer IDs) | Exact match | — |
| Sequence ordering | Exact match | — |

## Scope

Determinism is guaranteed for:
- All bargaining protocols (Nash, Rubinstein, TIOLI, Asymmetric Nash)
- All information environments (Full, NoisyAlpha)
- Belief-enabled simulations
- Any agent count and grid size

## Tie-Breaking

When multiple agents or actions have equal priority, deterministic tie-breaking is part of the contract:
- Agent iteration uses sorted ID order
- Proposal conflict resolution uses sorted proposer ID order

## RNG Isolation

Per A-005, all stochastic behavior is driven by per-run RNG instances seeded from the config seed. No module-level or global RNG state is mutated.

## Platform Note

Determinism is validated on the same Python version and platform. Cross-platform floating-point equivalence is not guaranteed but expected to hold within the tolerance above.
