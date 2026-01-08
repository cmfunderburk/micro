#!/usr/bin/env python3
"""
Benchmark script for microecon simulation performance.

Quick performance test - runs in <30 seconds.

Usage:
    uv run python scripts/benchmark.py
"""

import time
from microecon.simulation import create_simple_economy


def main():
    print()
    print("MICROECON PERFORMANCE BENCHMARK")
    print("=" * 50)
    print()

    # Test agent scaling (O(n²) expected)
    scenarios = [
        (5, 10, 20),
        (10, 10, 20),
        (15, 12, 20),
        (20, 15, 15),
    ]

    for n_agents, grid_size, ticks in scenarios:
        sim = create_simple_economy(n_agents=n_agents, grid_size=grid_size, seed=42)
        start = time.perf_counter()
        sim.run(ticks=ticks)
        elapsed = time.perf_counter() - start
        tps = ticks / elapsed

        print(f"{n_agents:3} agents, {grid_size:2}x{grid_size:2} grid: {tps:6.1f} ticks/sec")

    print()
    print("Note: Scaling is O(n²) due to pairwise search/matching comparisons.")
    print()


if __name__ == "__main__":
    main()
