"""
Microecon Platform Demo

Demonstrates the grid-based search and exchange simulation with
agents having Cobb-Douglas preferences and Nash bargaining.
"""

from microecon.simulation import create_simple_economy


def main():
    print("Microecon Platform - Grid Search and Exchange Demo")
    print("=" * 50)

    # Create a simple economy with 6 agents on a 10x10 grid
    sim = create_simple_economy(
        n_agents=6,
        grid_size=10,
        perception_radius=5.0,
        discount_factor=0.95,
        seed=42,
    )

    print(f"\nInitial state:")
    print(f"  Agents: {len(sim.agents)}")
    print(f"  Grid size: {sim.grid.size}x{sim.grid.size}")
    print(f"  Initial total welfare: {sim.total_welfare():.2f}")

    print("\nAgent details:")
    for agent in sim.agents:
        pos = sim.grid.get_position(agent)
        print(
            f"  {agent.id}: alpha={agent.preferences.alpha:.2f}, "
            f"endowment=({agent.endowment.x:.1f}, {agent.endowment.y:.1f}), "
            f"position=({pos.row}, {pos.col}), utility={agent.utility():.2f}"
        )

    # Run simulation
    print("\nRunning simulation for 50 ticks...")

    def tick_callback(tick: int, trades):
        if trades:
            for trade in trades:
                print(
                    f"  Tick {tick}: Trade between {trade.agent1_id} and {trade.agent2_id} "
                    f"(gains: {trade.gains[0] + trade.gains[1]:.2f})"
                )

    sim.run(50, callback=tick_callback)

    print(f"\nFinal state:")
    print(f"  Total ticks: {sim.tick}")
    print(f"  Total trades: {len(sim.trades)}")
    print(f"  Final total welfare: {sim.total_welfare():.2f}")
    print(f"  Total welfare gains: {sim.welfare_gains():.2f}")

    print("\nFinal agent states:")
    for agent in sim.agents:
        pos = sim.grid.get_position(agent)
        print(
            f"  {agent.id}: endowment=({agent.endowment.x:.2f}, {agent.endowment.y:.2f}), "
            f"position=({pos.row}, {pos.col}), utility={agent.utility():.2f}"
        )


if __name__ == "__main__":
    main()
