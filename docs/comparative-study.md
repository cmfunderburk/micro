# Comparative Study: Institutional Effects on Market Emergence

**Purpose:** Demonstrate how institutional rules affect market emergence from bilateral exchange.

**Method:** Run the same initial conditions (agent preferences, endowments, positions) under different institutional rules and compare outcomes.

## Configuration

| Parameter | Value |
|-----------|-------|
| Agents | 30 |
| Grid Size | 15x15 |
| Ticks | 80 |
| Seed | 42 |
| Perception Radius | 5.0 |
| Alpha Range | 0.2 - 0.8 |
| Endowment Types | x-rich (12,4), y-rich (4,12) |

## Results Summary

| Protocol | Matching | Trades | Efficiency | Avg Degree | Clusters |
|----------|----------|--------|------------|------------|----------|
| Nash | Opportunistic | 35 | 13.4% | 2.13 | 6 |
| Nash | StableRoommates | 21 | 13.1% | 1.40 | 3 |
| Rubinstein | Opportunistic | 47 | 13.5% | 2.87 | 5 |

## Analysis

### Trade Volume

**Rubinstein generates more trades than Nash.** With opportunistic matching, Rubinstein bargaining produced 47 trades vs Nash's 35 (34% more). This aligns with theory: Rubinstein's alternating-offers protocol allows for first-mover advantage, potentially leading to quicker agreement.

**Stable matching reduces trade volume.** Nash + StableRoommates produced only 21 trades (40% fewer than Nash + Opportunistic). This is expected: stable matching commits agents to partners, reducing the flexibility to trade opportunistically with nearby agents.

### Welfare Efficiency

All configurations achieved similar efficiency ratios (13.1-13.5%). This suggests that in this scenario, the choice of protocol affects *how* welfare gains are distributed rather than *whether* they are achieved.

The theoretical maximum gains represent the sum of all pairwise surpluses - an upper bound achievable only with perfect matching and full information. The 13% efficiency indicates substantial room for improvement, likely due to:
- Search frictions (agents don't always find optimal partners)
- Spatial constraints (distance limits meetings)
- Sequential trading (early trades may preclude later optimal matches)

### Network Structure

**Average degree** measures how many unique partners each agent traded with on average.

- Rubinstein + Opportunistic: 2.87 (most connected)
- Nash + Opportunistic: 2.13 (moderate)
- Nash + StableRoommates: 1.40 (most concentrated)

Higher average degree suggests more fluid market behavior, while lower degree indicates concentration around committed partnerships.

### Spatial Clustering

All configurations produced trading clusters (3-6), indicating that markets spontaneously form spatial hotspots. This emergence of "market places" from decentralized bilateral exchange is a key demonstration of the platform's research value.

## Interpretation

### Institutional Visibility

This comparison demonstrates the platform's core methodological contribution: **making institutions visible**. By holding the environment constant (same agents, same endowments, same initial positions) and varying only the institutional rules, we can isolate the effect of institutions on outcomes.

### Key Findings

1. **Bargaining protocol affects trade frequency** but not necessarily efficiency
2. **Matching protocol affects network structure** - stable matching creates concentrated partnerships while opportunistic matching creates fluid markets
3. **Markets emerge spatially** under all configurations, but with different densities

### Limitations

- This is a single run (seed=42). Statistical confidence requires multiple seeds.
- 80 ticks may not be long enough for full equilibration
- 30 agents is at the lower end of "market" scale

## Reproducibility

This study can be reproduced with:

```python
from microecon.scenarios import MarketEmergenceConfig, run_market_emergence
from microecon.bargaining import NashBargainingProtocol, RubinsteinBargainingProtocol
from microecon.matching import OpportunisticMatchingProtocol, StableRoommatesMatchingProtocol

config = MarketEmergenceConfig(
    n_agents=30,
    grid_size=15,
    ticks=80,
    seed=42,
)

# Run with different configurations
result_nash_opp = run_market_emergence(
    config,
    bargaining_protocol=NashBargainingProtocol(),
    matching_protocol=OpportunisticMatchingProtocol(),
)

result_nash_stable = run_market_emergence(
    config,
    bargaining_protocol=NashBargainingProtocol(),
    matching_protocol=StableRoommatesMatchingProtocol(),
)

result_rub_opp = run_market_emergence(
    config,
    bargaining_protocol=RubinsteinBargainingProtocol(),
    matching_protocol=OpportunisticMatchingProtocol(),
)

# Access analysis results
for result in [result_nash_opp, result_nash_stable, result_rub_opp]:
    a = result.analysis
    print(f"{result.protocol_name} + {result.matching_name}:")
    print(f"  Trades: {a.network.total_trades}")
    print(f"  Efficiency: {a.efficiency.efficiency_ratio:.1%}")
```

---

**Date:** 2026-01-03
**Platform Version:** Development (pre-release)
