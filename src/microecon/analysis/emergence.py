"""Market emergence analysis.

Provides tools for analyzing emergent market-like behavior from bilateral exchange:
- Trade network analysis (graph structure, hubs, clusters)
- Welfare efficiency gap (achieved vs theoretical maximum)
- Trading cluster detection (spatial hotspots)
- Agent trajectory analysis (convergence patterns)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
import math

from microecon.logging import RunData, AgentSnapshot


@dataclass
class TradeNetworkStats:
    """Statistics about the trade network structure.

    The trade network is a graph where nodes are agents and edges represent
    trades between them. Edge weights are the number of trades.
    """
    n_nodes: int  # Number of agents
    n_edges: int  # Number of unique trading pairs
    total_trades: int  # Total number of trades (counting repeats)
    density: float  # Actual edges / possible edges
    avg_degree: float  # Average number of trading partners
    max_degree: int  # Maximum number of trading partners (hub)
    hub_agent_ids: list[str]  # Agents with max degree
    isolated_agent_ids: list[str]  # Agents with no trades
    clustering_coefficient: float  # Network clustering (0-1)


@dataclass
class TradeEdge:
    """A trade relationship between two agents."""
    agent1_id: str
    agent2_id: str
    trade_count: int  # Number of times they traded
    total_surplus: float  # Sum of surpluses from all trades


def build_trade_network(run: RunData) -> dict[str, dict[str, TradeEdge]]:
    """Build an adjacency list representation of the trade network.

    Args:
        run: RunData object

    Returns:
        Dict mapping agent_id -> dict of (partner_id -> TradeEdge)
    """
    network: dict[str, dict[str, TradeEdge]] = defaultdict(dict)

    for tick in run.ticks:
        for trade in tick.trades:
            if not trade.trade_occurred:
                continue

            a1, a2 = trade.agent1_id, trade.agent2_id

            # Ensure consistent ordering (smaller ID first)
            if a1 > a2:
                a1, a2 = a2, a1

            # Get or create edge
            if a2 not in network[a1]:
                network[a1][a2] = TradeEdge(a1, a2, 0, 0.0)
                network[a2][a1] = network[a1][a2]  # Symmetric

            edge = network[a1][a2]
            edge.trade_count += 1
            # Sum of both agents' gains
            if trade.gains:
                edge.total_surplus += sum(trade.gains)

    return dict(network)


def trade_network_stats(run: RunData) -> TradeNetworkStats:
    """Compute statistics about the trade network.

    Args:
        run: RunData object

    Returns:
        TradeNetworkStats with network metrics
    """
    if not run.ticks:
        return TradeNetworkStats(
            n_nodes=0, n_edges=0, total_trades=0, density=0.0,
            avg_degree=0.0, max_degree=0, hub_agent_ids=[],
            isolated_agent_ids=[], clustering_coefficient=0.0
        )

    network = build_trade_network(run)

    # Get all agents from initial tick
    initial_agents = {s.agent_id for s in run.ticks[0].agent_snapshots}
    n_nodes = len(initial_agents)

    # Count edges and degree
    seen_edges: set[tuple[str, str]] = set()
    degree: dict[str, int] = defaultdict(int)
    total_trades = 0

    for a1, partners in network.items():
        for a2, edge in partners.items():
            if a1 < a2:  # Count each edge once
                seen_edges.add((a1, a2))
                total_trades += edge.trade_count
            degree[a1] += 1

    n_edges = len(seen_edges)

    # Density: fraction of possible edges that exist
    max_edges = n_nodes * (n_nodes - 1) // 2 if n_nodes > 1 else 1
    density = n_edges / max_edges if max_edges > 0 else 0.0

    # Degree statistics
    max_degree = max(degree.values()) if degree else 0
    avg_degree = sum(degree.values()) / n_nodes if n_nodes > 0 else 0.0

    # Find hubs (agents with max degree) and isolated agents
    hub_agent_ids = [aid for aid, d in degree.items() if d == max_degree]
    isolated_agent_ids = [aid for aid in initial_agents if aid not in degree]

    # Clustering coefficient: fraction of agent's neighbors that are connected
    # For each agent, count triangles
    local_clustering = []
    for agent_id in network:
        neighbors = list(network[agent_id].keys())
        if len(neighbors) < 2:
            continue
        # Count how many neighbor pairs are connected
        connected_pairs = 0
        possible_pairs = len(neighbors) * (len(neighbors) - 1) // 2
        for i, n1 in enumerate(neighbors):
            for n2 in neighbors[i + 1:]:
                if n2 in network.get(n1, {}):
                    connected_pairs += 1
        if possible_pairs > 0:
            local_clustering.append(connected_pairs / possible_pairs)

    clustering_coefficient = (
        sum(local_clustering) / len(local_clustering) if local_clustering else 0.0
    )

    return TradeNetworkStats(
        n_nodes=n_nodes,
        n_edges=n_edges,
        total_trades=total_trades,
        density=density,
        avg_degree=avg_degree,
        max_degree=max_degree,
        hub_agent_ids=hub_agent_ids,
        isolated_agent_ids=isolated_agent_ids,
        clustering_coefficient=clustering_coefficient,
    )


@dataclass
class WelfareEfficiencyResult:
    """Result of welfare efficiency analysis.

    Compares achieved welfare gains to theoretical maximum.
    """
    initial_welfare: float
    final_welfare: float
    achieved_gains: float
    theoretical_max_gains: float  # Estimated maximum possible gains
    efficiency_ratio: float  # achieved / theoretical (0-1)


def compute_theoretical_max_gains(run: RunData) -> float:
    """Estimate maximum possible gains from trade using optimal matching.

    Computes the maximum total welfare gains achievable if agents were
    optimally paired. Uses greedy maximum weight matching on bilateral
    surpluses (both agents' gains, not just one side).

    This is a much tighter bound than summing all pairwise surpluses,
    which overcounts since each agent can only trade once per matching.

    Note: Greedy matching gives a 2-approximation of optimal. For typical
    simulation sizes (n ≤ 50), this is accurate enough for efficiency analysis.

    Args:
        run: RunData object

    Returns:
        Estimated maximum total welfare gains from optimal matching
    """
    from microecon.bargaining import nash_bargaining_solution
    from microecon.agent import AgentType
    from microecon.preferences import CobbDouglas
    from microecon.bundle import Bundle

    if not run.ticks:
        return 0.0

    # Get initial agent states
    initial = run.ticks[0].agent_snapshots

    # Build AgentType objects for computing surplus
    types = []
    for snapshot in initial:
        agent_type = AgentType(
            preferences=CobbDouglas(snapshot.alpha),
            endowment=Bundle(snapshot.endowment[0], snapshot.endowment[1]),
        )
        types.append(agent_type)

    n = len(types)
    if n < 2:
        return 0.0

    # Compute bilateral surpluses for all pairs
    # Each entry: (surplus, agent_i, agent_j)
    pair_surpluses: list[tuple[float, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            outcome = nash_bargaining_solution(
                types[i].preferences,
                types[i].endowment,
                types[j].preferences,
                types[j].endowment,
            )
            # Use bilateral surplus (both agents' gains)
            bilateral_surplus = outcome.gains_1 + outcome.gains_2
            if bilateral_surplus > 0:
                pair_surpluses.append((bilateral_surplus, i, j))

    # Greedy maximum weight matching
    # Sort by surplus descending, greedily select non-overlapping pairs
    pair_surpluses.sort(reverse=True, key=lambda x: x[0])

    matched: set[int] = set()
    total_surplus = 0.0

    for surplus, i, j in pair_surpluses:
        if i not in matched and j not in matched:
            total_surplus += surplus
            matched.add(i)
            matched.add(j)

    return total_surplus


def welfare_efficiency(run: RunData) -> WelfareEfficiencyResult:
    """Compute welfare efficiency gap.

    Compares achieved welfare gains to theoretical maximum.

    Args:
        run: RunData object

    Returns:
        WelfareEfficiencyResult with efficiency metrics
    """
    if not run.ticks:
        return WelfareEfficiencyResult(
            initial_welfare=0.0,
            final_welfare=0.0,
            achieved_gains=0.0,
            theoretical_max_gains=0.0,
            efficiency_ratio=0.0,
        )

    initial_welfare = run.ticks[0].total_welfare
    final_welfare = run.ticks[-1].total_welfare
    achieved_gains = final_welfare - initial_welfare
    theoretical_max = compute_theoretical_max_gains(run)

    efficiency_ratio = (
        achieved_gains / theoretical_max if theoretical_max > 0 else 1.0
    )

    return WelfareEfficiencyResult(
        initial_welfare=initial_welfare,
        final_welfare=final_welfare,
        achieved_gains=achieved_gains,
        theoretical_max_gains=theoretical_max,
        efficiency_ratio=efficiency_ratio,
    )


@dataclass
class SpatialCluster:
    """A spatial cluster of trading activity."""
    center: tuple[int, int]  # (row, col) center of cluster
    radius: float  # Approximate radius
    trade_count: int  # Number of trades in this region
    agent_ids: set[str]  # Agents who traded in this cluster


def detect_trading_clusters(
    run: RunData,
    min_cluster_size: int = 3,
    merge_distance: float = 3.0,
) -> list[SpatialCluster]:
    """Detect spatial regions where trading concentrates.

    Uses a simple density-based clustering approach:
    1. Collect all trade locations
    2. Group nearby locations
    3. Filter by minimum size

    Args:
        run: RunData object
        min_cluster_size: Minimum trades to form a cluster
        merge_distance: Maximum distance to merge trade locations

    Returns:
        List of SpatialCluster objects
    """
    if not run.ticks:
        return []

    # Collect trade locations and participating agents
    trade_locations: list[tuple[tuple[int, int], str, str]] = []

    for tick in run.ticks:
        # Build position lookup from agent snapshots
        positions = {s.agent_id: s.position for s in tick.agent_snapshots}

        for trade in tick.trades:
            if not trade.trade_occurred:
                continue
            # Use first agent's position as trade location
            pos = positions.get(trade.agent1_id)
            if pos:
                trade_locations.append((pos, trade.agent1_id, trade.agent2_id))

    if not trade_locations:
        return []

    # Simple clustering: group nearby locations
    clusters: list[dict] = []  # Each has: locations, agents, center

    for pos, a1, a2 in trade_locations:
        # Find nearest cluster
        nearest_idx = None
        nearest_dist = float('inf')

        for i, cluster in enumerate(clusters):
            cx, cy = cluster['center']
            dist = math.sqrt((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_idx = i

        if nearest_idx is not None and nearest_dist <= merge_distance:
            # Add to existing cluster
            cluster = clusters[nearest_idx]
            cluster['locations'].append(pos)
            cluster['agents'].add(a1)
            cluster['agents'].add(a2)
            # Update center (mean)
            locs = cluster['locations']
            cluster['center'] = (
                sum(p[0] for p in locs) / len(locs),
                sum(p[1] for p in locs) / len(locs),
            )
        else:
            # Create new cluster
            clusters.append({
                'locations': [pos],
                'agents': {a1, a2},
                'center': (float(pos[0]), float(pos[1])),
            })

    # Filter by minimum size and convert to SpatialCluster
    result = []
    for cluster in clusters:
        if len(cluster['locations']) >= min_cluster_size:
            locs = cluster['locations']
            center = cluster['center']

            # Compute radius as max distance from center
            radius = max(
                math.sqrt((p[0] - center[0]) ** 2 + (p[1] - center[1]) ** 2)
                for p in locs
            ) if locs else 0.0

            result.append(SpatialCluster(
                center=(int(round(center[0])), int(round(center[1]))),
                radius=radius,
                trade_count=len(locs),
                agent_ids=cluster['agents'],
            ))

    return result


@dataclass
class AgentTrajectory:
    """An agent's movement trajectory during the simulation."""
    agent_id: str
    alpha: float
    positions: list[tuple[int, int]]  # Position at each tick
    total_distance: float  # Total distance traveled
    final_distance_from_start: float  # Net displacement


def agent_trajectories(run: RunData) -> list[AgentTrajectory]:
    """Extract movement trajectories for all agents.

    Args:
        run: RunData object

    Returns:
        List of AgentTrajectory for each agent
    """
    if not run.ticks:
        return []

    # Track positions over time per agent
    position_series: dict[str, list[tuple[int, int]]] = defaultdict(list)
    alphas: dict[str, float] = {}

    for tick in run.ticks:
        for snapshot in tick.agent_snapshots:
            position_series[snapshot.agent_id].append(snapshot.position)
            alphas[snapshot.agent_id] = snapshot.alpha

    result = []
    for agent_id, positions in position_series.items():
        # Compute total distance traveled
        total_distance = 0.0
        for i in range(1, len(positions)):
            p1, p2 = positions[i - 1], positions[i]
            total_distance += math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

        # Net displacement from start to end
        if len(positions) >= 2:
            start, end = positions[0], positions[-1]
            final_distance = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
        else:
            final_distance = 0.0

        result.append(AgentTrajectory(
            agent_id=agent_id,
            alpha=alphas.get(agent_id, 0.0),
            positions=positions,
            total_distance=total_distance,
            final_distance_from_start=final_distance,
        ))

    return result


@dataclass
class ConvergenceStats:
    """Statistics about agent convergence to trading hotspots."""
    avg_total_distance: float  # Average total distance traveled
    avg_net_displacement: float  # Average net displacement
    agents_at_hotspots: int  # Number of agents ending at hotspots
    hotspot_convergence_rate: float  # Fraction at hotspots


def convergence_analysis(
    run: RunData,
    hotspot_radius: float = 2.0,
) -> ConvergenceStats:
    """Analyze whether agents converge to trading hotspots.

    A hotspot is defined as a location where trading clusters form.

    Args:
        run: RunData object
        hotspot_radius: Distance from cluster center to count as "at hotspot"

    Returns:
        ConvergenceStats with convergence metrics
    """
    trajectories = agent_trajectories(run)
    clusters = detect_trading_clusters(run, min_cluster_size=2)

    if not trajectories:
        return ConvergenceStats(
            avg_total_distance=0.0,
            avg_net_displacement=0.0,
            agents_at_hotspots=0,
            hotspot_convergence_rate=0.0,
        )

    avg_total = sum(t.total_distance for t in trajectories) / len(trajectories)
    avg_net = sum(t.final_distance_from_start for t in trajectories) / len(trajectories)

    # Count agents ending at hotspots
    cluster_centers = [c.center for c in clusters]
    at_hotspots = 0

    for traj in trajectories:
        if not traj.positions:
            continue
        final_pos = traj.positions[-1]
        for center in cluster_centers:
            dist = math.sqrt((final_pos[0] - center[0]) ** 2 + (final_pos[1] - center[1]) ** 2)
            if dist <= hotspot_radius:
                at_hotspots += 1
                break

    convergence_rate = at_hotspots / len(trajectories) if trajectories else 0.0

    return ConvergenceStats(
        avg_total_distance=avg_total,
        avg_net_displacement=avg_net,
        agents_at_hotspots=at_hotspots,
        hotspot_convergence_rate=convergence_rate,
    )


@dataclass
class MarketEmergenceReport:
    """Comprehensive report on market emergence from bilateral exchange.

    Combines trade network, welfare efficiency, spatial clustering,
    and agent trajectory analyses.
    """
    network: TradeNetworkStats
    efficiency: WelfareEfficiencyResult
    clusters: list[SpatialCluster]
    convergence: ConvergenceStats
    n_agents: int
    total_ticks: int


def analyze_market_emergence(run: RunData) -> MarketEmergenceReport:
    """Run comprehensive market emergence analysis on a simulation run.

    Args:
        run: RunData object

    Returns:
        MarketEmergenceReport with all analysis results
    """
    return MarketEmergenceReport(
        network=trade_network_stats(run),
        efficiency=welfare_efficiency(run),
        clusters=detect_trading_clusters(run),
        convergence=convergence_analysis(run),
        n_agents=run.config.n_agents,
        total_ticks=len(run.ticks),
    )


def compare_emergence(run_a: RunData, run_b: RunData) -> tuple[MarketEmergenceReport, MarketEmergenceReport]:
    """Compare market emergence between two runs.

    Args:
        run_a: First run
        run_b: Second run

    Returns:
        Tuple of (report_a, report_b)
    """
    return analyze_market_emergence(run_a), analyze_market_emergence(run_b)
