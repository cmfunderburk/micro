/**
 * Modal showing side-by-side trade histories for comparison mode.
 *
 * Displays trades from both simulations in parallel columns.
 * Click any trade to open Edgeworth box visualization.
 */

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useComparisonStore } from '@/store/comparisonStore';
import { EdgeworthModal } from '@/components/TradeInspection/EdgeworthModal';
import { cobbDouglasUtility } from '@/components/TradeInspection/edgeworthMath';
import type { Trade } from '@/types/simulation';

// Compute utility gains from trade allocations
function computeTradeGains(trade: Trade): { gainA: number; gainB: number; total: number } {
  const utilityA_before = cobbDouglasUtility(trade.pre_holdings_1[0], trade.pre_holdings_1[1], trade.alpha1);
  const utilityA_after = cobbDouglasUtility(trade.post_allocation_1[0], trade.post_allocation_1[1], trade.alpha1);
  const utilityB_before = cobbDouglasUtility(trade.pre_holdings_2[0], trade.pre_holdings_2[1], trade.alpha2);
  const utilityB_after = cobbDouglasUtility(trade.post_allocation_2[0], trade.post_allocation_2[1], trade.alpha2);
  const gainA = utilityA_after - utilityA_before;
  const gainB = utilityB_after - utilityB_before;
  return { gainA, gainB, total: gainA + gainB };
}

interface ComparisonTradeHistoryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface TradeListProps {
  trades: Trade[];
  label: string;
  protocol: string;
  onSelectTrade: (trade: Trade) => void;
}

function TradeList({ trades, label, protocol, onSelectTrade }: TradeListProps) {
  // Show most recent trades first
  const reversedTrades = [...trades].reverse();

  return (
    <div className="flex-1 min-w-0">
      <div className="text-sm font-semibold text-zinc-300 mb-2">
        {label}{' '}
        <span className="text-zinc-500 font-normal">({protocol})</span>
      </div>
      <div className="text-xs text-zinc-500 mb-2">
        {trades.length} trade{trades.length !== 1 ? 's' : ''}
      </div>
      <div className="max-h-[400px] overflow-y-auto space-y-1 pr-1">
        {reversedTrades.length === 0 ? (
          <div className="text-zinc-500 text-sm italic py-4 text-center">
            No trades yet
          </div>
        ) : (
          reversedTrades.map((trade) => {
            const { gainA, gainB, total } = computeTradeGains(trade);
            return (
              <button
                key={`${trade.tick}-${trade.agent1_id}-${trade.agent2_id}`}
                className="w-full text-left px-2 py-1.5 rounded text-sm transition-colors
                  bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
                onClick={() => onSelectTrade(trade)}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs">T{trade.tick}</span>
                  <span className="text-green-400 text-xs">
                    +{total.toFixed(2)}
                  </span>
                </div>
                <div className="text-xs text-zinc-500 truncate">
                  ...{trade.agent1_id.slice(-6)} ↔ ...{trade.agent2_id.slice(-6)}
                </div>
                <div className="text-xs text-zinc-600 flex justify-between mt-0.5">
                  <span>A: +{gainA.toFixed(2)}</span>
                  <span>B: +{gainB.toFixed(2)}</span>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}

export function ComparisonTradeHistoryModal({
  open,
  onOpenChange,
}: ComparisonTradeHistoryModalProps) {
  const simulationA = useComparisonStore((state) => state.simulationA);
  const simulationB = useComparisonStore((state) => state.simulationB);

  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [edgeworthOpen, setEdgeworthOpen] = useState(false);

  const handleSelectTrade = (trade: Trade) => {
    setSelectedTrade(trade);
    setEdgeworthOpen(true);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl bg-zinc-900 border-zinc-700">
          <DialogHeader>
            <DialogTitle className="text-zinc-100">
              Trade History Comparison
            </DialogTitle>
          </DialogHeader>

          <div className="flex gap-4">
            <TradeList
              trades={simulationA.tradeHistory}
              label={simulationA.label}
              protocol={simulationA.config?.bargaining_protocol ?? 'N/A'}
              onSelectTrade={handleSelectTrade}
            />

            <div className="w-px bg-zinc-700" />

            <TradeList
              trades={simulationB.tradeHistory}
              label={simulationB.label}
              protocol={simulationB.config?.bargaining_protocol ?? 'N/A'}
              onSelectTrade={handleSelectTrade}
            />
          </div>

          <div className="text-xs text-zinc-500 mt-2">
            Click any trade to view Edgeworth box
          </div>
        </DialogContent>
      </Dialog>

      <EdgeworthModal
        trade={selectedTrade}
        open={edgeworthOpen}
        onOpenChange={setEdgeworthOpen}
      />
    </>
  );
}
