/**
 * Belief panel showing selected agent's beliefs.
 *
 * Displays:
 * - Price belief statistics (mean, variance, n_observations)
 * - Type beliefs list (beliefs about other agents' alpha values)
 * - Memory statistics (trades in memory)
 */

import { useSimulationStore } from '@/store';

export function BeliefPanel() {
  const selectedAgentId = useSimulationStore((state) => state.selectedAgentId);
  const beliefs = useSimulationStore((state) => state.beliefs);
  const agents = useSimulationStore((state) => state.agents);

  // Find selected agent
  const selectedAgent = agents.find((a) => a.id === selectedAgentId);
  const agentBeliefs = selectedAgentId ? beliefs[selectedAgentId] : null;

  if (!selectedAgentId || !selectedAgent) {
    return (
      <div className="text-zinc-500 text-sm italic">
        Select an agent to view beliefs
      </div>
    );
  }

  if (!selectedAgent.has_beliefs || !agentBeliefs) {
    return (
      <div className="space-y-2">
        <div className="text-sm text-zinc-300">
          Agent: <span className="font-mono">{selectedAgentId.slice(0, 8)}...</span>
        </div>
        <div className="text-zinc-500 text-sm italic">
          No beliefs (use_beliefs disabled)
        </div>
      </div>
    );
  }

  const { type_beliefs, price_belief, n_trades_in_memory } = agentBeliefs;

  // Sort type beliefs by confidence (most confident first)
  const sortedTypeBeliefs = [...type_beliefs].sort((a, b) => b.confidence - a.confidence);

  return (
    <div className="space-y-3">
      {/* Agent header */}
      <div className="text-sm text-zinc-300">
        Agent: <span className="font-mono">{selectedAgentId.slice(0, 8)}...</span>
      </div>

      {/* Price belief */}
      <div className="space-y-1">
        <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
          Price Belief
        </div>
        {price_belief && price_belief.n_observations > 0 ? (
          <div className="text-sm text-zinc-300 font-mono">
            <div>mean = {price_belief.mean.toFixed(3)}</div>
            <div>variance = {price_belief.variance.toFixed(4)}</div>
            <div>n = {price_belief.n_observations}</div>
          </div>
        ) : (
          <div className="text-sm text-zinc-500 italic">No price observations</div>
        )}
      </div>

      {/* Memory stats */}
      <div className="space-y-1">
        <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
          Memory
        </div>
        <div className="text-sm text-zinc-300">
          {n_trades_in_memory} trades in memory
        </div>
      </div>

      {/* Type beliefs */}
      <div className="space-y-1">
        <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
          Type Beliefs ({type_beliefs.length})
        </div>
        {sortedTypeBeliefs.length > 0 ? (
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {sortedTypeBeliefs.slice(0, 10).map((tb) => (
              <div
                key={tb.target_id}
                className="text-xs text-zinc-300 font-mono flex justify-between gap-2"
              >
                <span className="truncate">{tb.target_id.slice(0, 6)}...</span>
                <span>
                  alpha={tb.believed_alpha.toFixed(2)} c={tb.confidence.toFixed(2)}
                </span>
              </div>
            ))}
            {sortedTypeBeliefs.length > 10 && (
              <div className="text-xs text-zinc-500 italic">
                +{sortedTypeBeliefs.length - 10} more
              </div>
            )}
          </div>
        ) : (
          <div className="text-sm text-zinc-500 italic">No type beliefs</div>
        )}
      </div>
    </div>
  );
}
