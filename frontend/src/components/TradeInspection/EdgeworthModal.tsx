/**
 * Modal dialog for trade inspection with Edgeworth box.
 */

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import type { Trade } from '@/types/simulation';
import { EdgeworthBox } from './EdgeworthBox';
import { cobbDouglasUtility } from './edgeworthMath';

interface EdgeworthModalProps {
  trade: Trade | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EdgeworthModal({ trade, open, onOpenChange }: EdgeworthModalProps) {
  if (!trade) return null;

  // Compute utilities
  const utilityA_before = cobbDouglasUtility(
    trade.pre_endowment_1[0],
    trade.pre_endowment_1[1],
    trade.alpha1
  );
  const utilityA_after = cobbDouglasUtility(
    trade.post_allocation_1[0],
    trade.post_allocation_1[1],
    trade.alpha1
  );
  const utilityB_before = cobbDouglasUtility(
    trade.pre_endowment_2[0],
    trade.pre_endowment_2[1],
    trade.alpha2
  );
  const utilityB_after = cobbDouglasUtility(
    trade.post_allocation_2[0],
    trade.post_allocation_2[1],
    trade.alpha2
  );

  const gainA = utilityA_after - utilityA_before;
  const gainB = utilityB_after - utilityB_before;

  // Trade amounts
  const dxA = trade.post_allocation_1[0] - trade.pre_endowment_1[0];
  const dyA = trade.post_allocation_1[1] - trade.pre_endowment_1[1];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl bg-zinc-900 border-zinc-700">
        <DialogHeader>
          <DialogTitle className="text-zinc-100">
            Trade at Tick {trade.tick}
          </DialogTitle>
        </DialogHeader>

        <div className="flex gap-4">
          {/* Edgeworth Box */}
          <div className="flex-shrink-0">
            <EdgeworthBox trade={trade} width={350} height={350} />
            {/* Legend */}
            <div className="flex items-center gap-4 mt-2 text-sm">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-amber-400" />
                <span className="text-zinc-400">Endowment</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-zinc-400">Allocation</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-1 bg-fuchsia-400" />
                <span className="text-zinc-400">Contract</span>
              </div>
            </div>
          </div>

          {/* Trade Details */}
          <div className="flex-1 text-sm space-y-4">
            {/* Agent A */}
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-blue-400 font-semibold mb-2">
                Agent A (α = {trade.alpha1.toFixed(2)})
              </div>
              <div className="text-zinc-400 text-xs mb-1">
                ID: ...{trade.agent1_id.slice(-8)}
              </div>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Endowment:</span>
                  <span className="font-mono text-zinc-300">
                    ({trade.pre_endowment_1[0].toFixed(2)}, {trade.pre_endowment_1[1].toFixed(2)})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Allocation:</span>
                  <span className="font-mono text-zinc-300">
                    ({trade.post_allocation_1[0].toFixed(2)}, {trade.post_allocation_1[1].toFixed(2)})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Trade:</span>
                  <span className={`font-mono ${dxA >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ({dxA >= 0 ? '+' : ''}{dxA.toFixed(2)}, {dyA >= 0 ? '+' : ''}{dyA.toFixed(2)})
                  </span>
                </div>
                <div className="border-t border-zinc-700 my-1" />
                <div className="flex justify-between">
                  <span className="text-zinc-500">Utility:</span>
                  <span className="font-mono text-zinc-300">
                    {utilityA_before.toFixed(3)} → {utilityA_after.toFixed(3)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Gain:</span>
                  <span className={`font-mono ${gainA >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {gainA >= 0 ? '+' : ''}{gainA.toFixed(3)}
                  </span>
                </div>
              </div>
            </div>

            {/* Agent B */}
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-orange-400 font-semibold mb-2">
                Agent B (α = {trade.alpha2.toFixed(2)})
              </div>
              <div className="text-zinc-400 text-xs mb-1">
                ID: ...{trade.agent2_id.slice(-8)}
              </div>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Endowment:</span>
                  <span className="font-mono text-zinc-300">
                    ({trade.pre_endowment_2[0].toFixed(2)}, {trade.pre_endowment_2[1].toFixed(2)})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Allocation:</span>
                  <span className="font-mono text-zinc-300">
                    ({trade.post_allocation_2[0].toFixed(2)}, {trade.post_allocation_2[1].toFixed(2)})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Trade:</span>
                  <span className={`font-mono ${-dxA >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ({-dxA >= 0 ? '+' : ''}{(-dxA).toFixed(2)}, {-dyA >= 0 ? '+' : ''}{(-dyA).toFixed(2)})
                  </span>
                </div>
                <div className="border-t border-zinc-700 my-1" />
                <div className="flex justify-between">
                  <span className="text-zinc-500">Utility:</span>
                  <span className="font-mono text-zinc-300">
                    {utilityB_before.toFixed(3)} → {utilityB_after.toFixed(3)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Gain:</span>
                  <span className={`font-mono ${gainB >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {gainB >= 0 ? '+' : ''}{gainB.toFixed(3)}
                  </span>
                </div>
              </div>
            </div>

            {/* Total Surplus */}
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="flex justify-between">
                <span className="text-zinc-400">Total Surplus:</span>
                <span className="font-mono text-green-400">
                  +{(gainA + gainB).toFixed(3)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
