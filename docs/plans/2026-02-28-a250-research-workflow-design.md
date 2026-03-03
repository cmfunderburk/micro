# A-250: Scripted Research Workflow — Design

**Date:** 2026-02-28
**Epic:** A-E4 (Gate A.5 Research Workflow Proof)
**Status:** Approved

## Goal

Deliver a single Python script that configures an experiment, runs a batch, computes comparison outputs, and writes structured JSON evidence artifacts. The workflow must reproduce identical outputs under declared seeds and be runnable without manual code edits.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Form | Python script | User preference; no CLI framework needed |
| Approach | Flat sequential | YAGNI — proof-of-concept, not reusable infra |
| Comparisons | Both matching + bargaining | Richer evidence set for Gate B |
| Outputs | JSON evidence files only | Directly consumable by Gate B frontend |
| Seeds | 3 per configuration | Balances reproducibility evidence vs runtime |
| Agents / Grid / Ticks | 10 / 15 / 100 | Matches existing BatchRunner defaults |

## Prerequisite: BatchRunner matching_protocol support

`BatchRunner._create_simulation()` does not pass `matching_protocol` to `create_simple_economy()`, and `_config_to_simulation_config()` does not set `matching_protocol_name`. Fix:

- Add `_get_matching_protocol_name()` helper (mirrors `_get_protocol_name()`)
- Extract `matching_protocol` from config dict in `_create_simulation()` and pass through
- Set `matching_protocol_name` in `_config_to_simulation_config()`

## Script: `scripts/research_workflow.py`

Flat sequential, ~100 lines. Steps:

1. **Configure** — hardcoded constants at top (n_agents=10, grid_size=15, ticks=100, seeds=[0,1,2])
2. **Matching comparison** — BatchRunner with variations: `matching_protocol` x `seed` (2x3=6 runs). Bargaining held constant (Nash).
3. **Bargaining comparison** — BatchRunner with variations: `protocol` x `seed` (2x3=6 runs). Matching held constant (bilateral).
4. **Compute metrics** — welfare, trades, welfare gain, efficiency ratio per run. Cohen's d across protocol groups.
5. **Write evidence** — JSON files to `output/evidence/`.

Total runtime: 12 runs x ~60s = ~12 minutes.

## Output Artifacts

```
output/evidence/
  manifest.json                  # timestamp, seeds, git hash
  matching_comparison.json       # bilateral vs centralized metrics
  bargaining_comparison.json     # nash vs rubinstein metrics
```

### manifest.json

```json
{
  "timestamp": "2026-02-28T...",
  "git_commit": "abc1234",
  "seeds": [0, 1, 2],
  "n_agents": 10,
  "grid_size": 15,
  "ticks": 100
}
```

### comparison JSON (matching or bargaining)

```json
{
  "config": {
    "varying": "matching_protocol",
    "group_a": "bilateral_proposal",
    "group_b": "centralized_clearing",
    "held_constant": {"protocol": "nash"}
  },
  "metrics": {
    "final_welfare": {
      "group_a_mean": 12.5,
      "group_b_mean": 13.1,
      "difference": 0.6,
      "effect_size": 0.82,
      "group_a_values": [12.3, 12.5, 12.7],
      "group_b_values": [12.9, 13.1, 13.3]
    }
  },
  "per_run_summaries": [
    {
      "seed": 0,
      "protocol": "bilateral_proposal",
      "final_welfare": 12.3,
      "total_trades": 45,
      "welfare_gain": 2.1,
      "efficiency_ratio": 0.78
    }
  ]
}
```

## Scope exclusions

- No CLI argument parsing
- No matplotlib/plots
- No console output beyond progress indicators
- No verification re-run (determinism guaranteed by A-105 seed policy)
- No new analysis abstractions
