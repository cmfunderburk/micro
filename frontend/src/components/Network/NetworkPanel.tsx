/**
 * Network panel with trade network visualization and statistics.
 */

import { useState, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useSimulationStore } from '@/store';
import { TradeNetwork } from './TradeNetwork';

interface NetworkPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NetworkPanel({ open, onOpenChange }: NetworkPanelProps) {
  const [layout, setLayout] = useState<'force' | 'circular'>('force');

  const agents = useSimulationStore((state) => state.agents);
  const tradeConnections = useSimulationStore((state) => state.tradeConnections);

  // Compute network statistics
  const stats = useMemo(() => {
    const n = agents.length;
    const m = tradeConnections.length; // Number of unique trading pairs

    // Maximum possible edges in undirected graph
    const maxEdges = (n * (n - 1)) / 2;

    // Density: actual edges / max edges
    const density = maxEdges > 0 ? m / maxEdges : 0;

    // Degree of each node
    const degrees = new Map<string, number>();
    for (const agent of agents) {
      degrees.set(agent.id, 0);
    }
    for (const conn of tradeConnections) {
      degrees.set(conn.agent1_id, (degrees.get(conn.agent1_id) || 0) + 1);
      degrees.set(conn.agent2_id, (degrees.get(conn.agent2_id) || 0) + 1);
    }

    // Average degree
    const avgDegree =
      n > 0
        ? Array.from(degrees.values()).reduce((a, b) => a + b, 0) / n
        : 0;

    // Max degree
    const maxDegree = Math.max(0, ...Array.from(degrees.values()));

    // Total trades (sum of all connection counts)
    const totalTrades = tradeConnections.reduce((sum, c) => sum + c.count, 0);

    // Connected components (simple approach using BFS)
    const visited = new Set<string>();
    let components = 0;

    for (const agent of agents) {
      if (!visited.has(agent.id)) {
        components++;
        // BFS to find all connected nodes
        const queue = [agent.id];
        while (queue.length > 0) {
          const nodeId = queue.shift()!;
          if (visited.has(nodeId)) continue;
          visited.add(nodeId);

          for (const conn of tradeConnections) {
            if (conn.agent1_id === nodeId && !visited.has(conn.agent2_id)) {
              queue.push(conn.agent2_id);
            } else if (conn.agent2_id === nodeId && !visited.has(conn.agent1_id)) {
              queue.push(conn.agent1_id);
            }
          }
        }
      }
    }

    return {
      nodes: n,
      edges: m,
      density,
      avgDegree,
      maxDegree,
      totalTrades,
      components,
    };
  }, [agents, tradeConnections]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl bg-zinc-900 border-zinc-700">
        <DialogHeader>
          <DialogTitle className="text-zinc-100">Trade Network</DialogTitle>
        </DialogHeader>

        <div className="flex gap-4">
          {/* Network Visualization */}
          <div className="flex-1">
            <TradeNetwork width={400} height={400} layout={layout} />

            {/* Layout Toggle */}
            <div className="flex gap-2 mt-2">
              <Button
                variant={layout === 'force' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setLayout('force')}
                className="flex-1"
              >
                Force
              </Button>
              <Button
                variant={layout === 'circular' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setLayout('circular')}
                className="flex-1"
              >
                Circular
              </Button>
            </div>
          </div>

          {/* Statistics */}
          <div className="w-48 space-y-3">
            <div className="bg-zinc-800 rounded-lg p-3">
              <h3 className="text-sm font-semibold text-zinc-300 mb-2">Network Stats</h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Nodes</span>
                  <span className="font-mono text-zinc-300">{stats.nodes}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Edges</span>
                  <span className="font-mono text-zinc-300">{stats.edges}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Density</span>
                  <span className="font-mono text-zinc-300">{(stats.density * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>

            <div className="bg-zinc-800 rounded-lg p-3">
              <h3 className="text-sm font-semibold text-zinc-300 mb-2">Degree</h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Average</span>
                  <span className="font-mono text-zinc-300">{stats.avgDegree.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Maximum</span>
                  <span className="font-mono text-zinc-300">{stats.maxDegree}</span>
                </div>
              </div>
            </div>

            <div className="bg-zinc-800 rounded-lg p-3">
              <h3 className="text-sm font-semibold text-zinc-300 mb-2">Activity</h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Total Trades</span>
                  <span className="font-mono text-zinc-300">{stats.totalTrades}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Components</span>
                  <span className="font-mono text-zinc-300">{stats.components}</span>
                </div>
              </div>
            </div>

            {/* Legend */}
            <div className="bg-zinc-800 rounded-lg p-3">
              <h3 className="text-sm font-semibold text-zinc-300 mb-2">Legend</h3>
              <div className="space-y-1 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-zinc-400">α = 0</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-purple-500" />
                  <span className="text-zinc-400">α = 0.5</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-zinc-400">α = 1</span>
                </div>
                <div className="border-t border-zinc-700 my-2" />
                <div className="flex items-center gap-2">
                  <div className="w-6 h-0.5 bg-purple-500" />
                  <span className="text-zinc-400">Recent trade</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-0.5 bg-purple-900" />
                  <span className="text-zinc-400">Older trade</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
