/**
 * Perspective mode controls.
 *
 * Allows viewing the simulation from a specific agent's perspective,
 * showing only what that agent can see (within perception radius).
 */

import { useSimulationStore } from '@/store';

export function PerspectiveMode() {
  const agents = useSimulationStore((state) => state.agents);
  const perspectiveMode = useSimulationStore((state) => state.perspectiveMode);
  const perspectiveAgentId = useSimulationStore((state) => state.perspectiveAgentId);
  const showGroundTruth = useSimulationStore((state) => state.showGroundTruth);
  const setPerspectiveMode = useSimulationStore((state) => state.setPerspectiveMode);
  const setPerspectiveAgentId = useSimulationStore((state) => state.setPerspectiveAgentId);
  const setShowGroundTruth = useSimulationStore((state) => state.setShowGroundTruth);

  return (
    <div className="space-y-3">
      {/* Enable toggle */}
      <label className="flex items-center gap-3 cursor-pointer">
        <div className="relative">
          <input
            type="checkbox"
            checked={perspectiveMode}
            onChange={(e) => setPerspectiveMode(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-8 h-4 bg-zinc-700 rounded-full peer-checked:bg-green-600 transition-colors" />
          <div className="absolute left-0.5 top-0.5 w-3 h-3 bg-zinc-300 rounded-full transition-transform peer-checked:translate-x-4 peer-checked:bg-white" />
        </div>
        <span className="text-sm text-zinc-200">Enable Perspective</span>
      </label>

      {/* Agent selector */}
      {perspectiveMode && (
        <div className="space-y-2">
          <label className="text-xs text-zinc-400 block">View From:</label>
          <select
            value={perspectiveAgentId ?? ''}
            onChange={(e) => setPerspectiveAgentId(e.target.value || null)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-100"
          >
            <option value="">Select agent...</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.id.slice(0, 8)}... (alpha={agent.alpha.toFixed(2)})
              </option>
            ))}
          </select>

          {/* Ground truth comparison toggle */}
          <label className="flex items-center gap-3 cursor-pointer mt-2">
            <div className="relative">
              <input
                type="checkbox"
                checked={showGroundTruth}
                onChange={(e) => setShowGroundTruth(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-zinc-700 rounded-full peer-checked:bg-green-600 transition-colors" />
              <div className="absolute left-0.5 top-0.5 w-3 h-3 bg-zinc-300 rounded-full transition-transform peer-checked:translate-x-4 peer-checked:bg-white" />
            </div>
            <div>
              <span className="text-xs text-zinc-300">Show Ground Truth</span>
              <p className="text-xs text-zinc-500">Overlay true positions</p>
            </div>
          </label>

          {/* Status indicator */}
          {perspectiveAgentId && (
            <div className="text-xs text-green-400">
              Viewing from: {perspectiveAgentId.slice(0, 8)}...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
