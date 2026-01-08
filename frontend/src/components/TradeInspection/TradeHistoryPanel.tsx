/**
 * Panel showing trade history with clickable entries.
 */

import { useSimulationStore } from '@/store';

export function TradeHistoryPanel() {
  const tradeHistory = useSimulationStore((state) => state.tradeHistory);
  const selectedTradeIndex = useSimulationStore((state) => state.selectedTradeIndex);
  const setSelectedTradeIndex = useSimulationStore((state) => state.setSelectedTradeIndex);

  if (tradeHistory.length === 0) {
    return (
      <div className="text-zinc-500 text-sm italic">
        No trades yet
      </div>
    );
  }

  // Show most recent trades first
  const reversedHistory = [...tradeHistory].reverse();

  return (
    <div className="max-h-48 overflow-y-auto space-y-1">
      {reversedHistory.map((trade, reverseIndex) => {
        const actualIndex = tradeHistory.length - 1 - reverseIndex;
        const isSelected = selectedTradeIndex === actualIndex;

        return (
          <button
            key={`${trade.tick}-${trade.agent1_id}-${trade.agent2_id}`}
            className={`w-full text-left px-2 py-1.5 rounded text-sm transition-colors ${
              isSelected
                ? 'bg-zinc-700 text-zinc-100'
                : 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
            }`}
            onClick={() => setSelectedTradeIndex(isSelected ? null : actualIndex)}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs">T{trade.tick}</span>
              <span className="text-green-400 text-xs">
                +{(trade.gains[0] + trade.gains[1]).toFixed(2)}
              </span>
            </div>
            <div className="text-xs text-zinc-500 truncate">
              ...{trade.agent1_id.slice(-6)} ↔ ...{trade.agent2_id.slice(-6)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
