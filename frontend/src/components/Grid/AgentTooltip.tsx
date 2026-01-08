/**
 * Tooltip displayed when hovering over an agent.
 */

import { useSimulationStore } from '@/store';

export function AgentTooltip() {
  const agents = useSimulationStore((state) => state.agents);
  const hoveredAgentId = useSimulationStore((state) => state.hoveredAgentId);

  const hoveredAgent = hoveredAgentId
    ? agents.find((a) => a.id === hoveredAgentId)
    : null;

  if (!hoveredAgent) return null;

  return (
    <div className="absolute top-4 left-4 bg-zinc-800 border border-zinc-700 rounded-lg p-3 shadow-lg text-sm z-10">
      <div className="font-semibold text-zinc-50 mb-2">{hoveredAgent.id}</div>
      <div className="space-y-1 text-zinc-300">
        <div className="flex justify-between gap-4">
          <span className="text-zinc-400">Alpha:</span>
          <span className="font-mono">{hoveredAgent.alpha.toFixed(3)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-zinc-400">Utility:</span>
          <span className="font-mono">{hoveredAgent.utility.toFixed(2)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-zinc-400">Endowment:</span>
          <span className="font-mono">
            ({hoveredAgent.endowment[0].toFixed(1)}, {hoveredAgent.endowment[1].toFixed(1)})
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-zinc-400">Position:</span>
          <span className="font-mono">
            ({hoveredAgent.position[0]}, {hoveredAgent.position[1]})
          </span>
        </div>
      </div>
    </div>
  );
}
