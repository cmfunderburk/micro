/**
 * Trade network visualization using D3-force.
 *
 * Displays agents as nodes and trades as edges.
 * Supports force-directed and circular layouts.
 *
 * Key optimization: Don't recreate the D3 simulation on every tick.
 * Only update link styles (recency coloring) when tick changes.
 */

import { useRef, useEffect, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import { useSimulationStore } from '@/store';

interface TradeNetworkProps {
  width?: number;
  height?: number;
  layout: 'force' | 'circular';
}

interface NetworkNode extends d3.SimulationNodeDatum {
  id: string;
  alpha: number;
}

interface NetworkLink extends d3.SimulationLinkDatum<NetworkNode> {
  count: number;
  lastTick: number;
}

// Map alpha (0-1) to color (red to blue via purple) - same as grid
function alphaToColor(alpha: number): string {
  const hue = alpha * 240;
  return `hsl(${hue}, 70%, 50%)`;
}

export function TradeNetwork({
  width = 400,
  height = 400,
  layout,
}: TradeNetworkProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<NetworkNode, NetworkLink> | null>(null);
  const linkSelectionRef = useRef<d3.Selection<SVGLineElement, NetworkLink, SVGGElement, unknown> | null>(null);
  const lastDataKeyRef = useRef<string>('');

  const agents = useSimulationStore((state) => state.agents);
  const tradeConnections = useSimulationStore((state) => state.tradeConnections);
  const tick = useSimulationStore((state) => state.tick);

  // Build network data - only depends on agents and connections, not tick
  const { nodes, links, maxCount, dataKey } = useMemo(() => {
    const agentIds = new Set(agents.map((a) => a.id));
    const nodeMap = new Map<string, NetworkNode>();

    // Create nodes for agents
    for (const agent of agents) {
      nodeMap.set(agent.id, {
        id: agent.id,
        alpha: agent.alpha,
      });
    }

    // Create links from trade connections
    const links: NetworkLink[] = [];
    let maxCount = 1;

    for (const conn of tradeConnections) {
      if (agentIds.has(conn.agent1_id) && agentIds.has(conn.agent2_id)) {
        links.push({
          source: conn.agent1_id,
          target: conn.agent2_id,
          count: conn.count,
          lastTick: conn.lastTick,
        });
        maxCount = Math.max(maxCount, conn.count);
      }
    }

    // Create a key to detect when structure changes (not just tick)
    const nodeIds = Array.from(nodeMap.keys()).sort().join(',');
    const linkKeys = links.map(l => `${l.source}-${l.target}-${l.count}`).sort().join('|');
    const dataKey = `${nodeIds}::${linkKeys}`;

    return {
      nodes: Array.from(nodeMap.values()),
      links,
      maxCount,
      dataKey,
    };
  }, [agents, tradeConnections]);

  // Position nodes in circular layout
  const positionCircular = useCallback(
    (nodes: NetworkNode[]) => {
      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.min(width, height) / 2 - 40;

      nodes.forEach((node, i) => {
        const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
        node.x = cx + radius * Math.cos(angle);
        node.y = cy + radius * Math.sin(angle);
        node.fx = node.x; // Fix position
        node.fy = node.y;
      });
    },
    [width, height]
  );

  // Full render - only when structure changes
  const renderFull = useCallback(() => {
    const svg = d3.select(svgRef.current);
    if (!svg.node()) return;

    // Stop existing simulation
    if (simulationRef.current) {
      simulationRef.current.stop();
      simulationRef.current = null;
    }

    // Clear previous content
    svg.selectAll('*').remove();

    // Create container group
    const g = svg.append('g');

    // Create a copy of nodes for this render
    const nodesCopy: NetworkNode[] = nodes.map((n) => ({ ...n }));
    const linksCopy: NetworkLink[] = links.map((l) => ({
      ...l,
      source: l.source,
      target: l.target,
    }));

    if (layout === 'circular') {
      positionCircular(nodesCopy);
    }

    // Draw links
    const linkGroup = g.append('g').attr('class', 'links');
    const link = linkGroup
      .selectAll('line')
      .data(linksCopy)
      .join('line')
      .attr('stroke', (d) => {
        const ticksSince = tick - d.lastTick;
        const alpha = Math.max(0.2, 1 - ticksSince / 50);
        return `rgba(168, 85, 247, ${alpha})`;
      })
      .attr('stroke-width', (d) => Math.min(1 + (d.count / maxCount) * 4, 5))
      .attr('stroke-linecap', 'round');

    // Store link selection for updates
    linkSelectionRef.current = link as unknown as d3.Selection<SVGLineElement, NetworkLink, SVGGElement, unknown>;

    // Draw nodes
    const nodeGroup = g.append('g').attr('class', 'nodes');
    const node = nodeGroup
      .selectAll('circle')
      .data(nodesCopy)
      .join('circle')
      .attr('r', 8)
      .attr('fill', (d) => alphaToColor(d.alpha))
      .attr('stroke', 'rgba(255, 255, 255, 0.3)')
      .attr('stroke-width', 1);

    // Add tooltips
    node.append('title').text((d) => `Agent: ${d.id.slice(-8)}\nα = ${d.alpha.toFixed(2)}`);

    if (layout === 'force') {
      // Create force simulation with higher alpha decay for faster settling
      const simulation = d3
        .forceSimulation<NetworkNode>(nodesCopy)
        .force(
          'link',
          d3
            .forceLink<NetworkNode, NetworkLink>(linksCopy)
            .id((d) => d.id)
            .distance(60)
        )
        .force('charge', d3.forceManyBody().strength(-100))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(12))
        .alphaDecay(0.05); // Faster settling

      simulationRef.current = simulation;

      simulation.on('tick', () => {
        link
          .attr('x1', (d) => (d.source as NetworkNode).x!)
          .attr('y1', (d) => (d.source as NetworkNode).y!)
          .attr('x2', (d) => (d.target as NetworkNode).x!)
          .attr('y2', (d) => (d.target as NetworkNode).y!);

        node.attr('cx', (d) => d.x!).attr('cy', (d) => d.y!);
      });

      // Add drag behavior
      node.call(
        d3
          .drag<SVGCircleElement, NetworkNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }) as never
      );
    } else {
      // Circular layout - positions already set
      link
        .attr('x1', (d) => (typeof d.source === 'object' ? d.source.x! : nodesCopy.find((n) => n.id === d.source)!.x!))
        .attr('y1', (d) => (typeof d.source === 'object' ? d.source.y! : nodesCopy.find((n) => n.id === d.source)!.y!))
        .attr('x2', (d) => (typeof d.target === 'object' ? d.target.x! : nodesCopy.find((n) => n.id === d.target)!.x!))
        .attr('y2', (d) => (typeof d.target === 'object' ? d.target.y! : nodesCopy.find((n) => n.id === d.target)!.y!));

      node.attr('cx', (d) => d.x!).attr('cy', (d) => d.y!);
    }

    lastDataKeyRef.current = dataKey;
  }, [nodes, links, maxCount, tick, width, height, layout, positionCircular, dataKey]);

  // Update link colors only (for tick changes)
  const updateLinkColors = useCallback(() => {
    if (!linkSelectionRef.current) return;

    linkSelectionRef.current.attr('stroke', (d) => {
      const ticksSince = tick - d.lastTick;
      const alpha = Math.max(0.2, 1 - ticksSince / 50);
      return `rgba(168, 85, 247, ${alpha})`;
    });
  }, [tick]);

  // Re-render when structure changes, update colors when tick changes
  useEffect(() => {
    if (dataKey !== lastDataKeyRef.current) {
      // Structure changed - full render
      renderFull();
    } else {
      // Only tick changed - update colors
      updateLinkColors();
    }

    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
      }
    };
  }, [dataKey, renderFull, updateLinkColors]);

  // Force re-render on layout change
  useEffect(() => {
    renderFull();
  }, [layout, width, height]);

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className="bg-zinc-900 rounded-lg"
    />
  );
}
