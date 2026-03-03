/**
 * Controls for entering/exiting comparison mode.
 *
 * Allows user to configure two simulations with different protocols
 * and compare them side-by-side.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useComparisonStore } from '@/store/comparisonStore';
import { useSimulationStore } from '@/store';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { GitCompare, X } from 'lucide-react';
import type { SimulationConfig } from '@/types/simulation';
import type { Command } from '@/hooks/useSimulationSocket';

type BargainingProtocol = 'nash' | 'rubinstein' | 'tioli' | 'asymmetric_nash';

// Protocol display configuration - matches ConfigModal for consistency
const BARGAINING_PROTOCOLS: { value: BargainingProtocol; label: string; shortLabel: string }[] = [
  { value: 'nash', label: 'Nash (Symmetric)', shortLabel: 'Nash' },
  { value: 'rubinstein', label: 'Nash (Patience)', shortLabel: 'Rubinstein' },
  { value: 'asymmetric_nash', label: 'Nash (Power)', shortLabel: 'Asymmetric' },
  { value: 'tioli', label: 'Take-It-Or-Leave-It', shortLabel: 'TIOLI' },
];

interface ComparisonControlsProps {
  sendCommand: (command: Command) => void;
}

export function ComparisonControls({ sendCommand }: ComparisonControlsProps) {
  const comparisonMode = useComparisonStore((state) => state.comparisonMode);
  const config = useSimulationStore((state) => state.config);
  const [open, setOpen] = useState(false);

  // Configuration for the comparison
  const [protocol1, setProtocol1] = useState<BargainingProtocol>('nash');
  const [protocol2, setProtocol2] = useState<BargainingProtocol>('rubinstein');
  const [nAgents, setNAgents] = useState(config?.n_agents ?? 10);
  const [gridSizeVal, setGridSizeVal] = useState(config?.grid_size ?? 15);
  const [seed, setSeed] = useState<number | ''>('');

  const handleStartComparison = () => {
    // Create two configs with the same base settings but different protocols
    const baseConfig: Partial<SimulationConfig> = {
      n_agents: nAgents,
      grid_size: gridSizeVal,
      perception_radius: config?.perception_radius ?? 7.0,
      discount_factor: config?.discount_factor ?? 0.95,
      seed: seed === '' ? Math.floor(Math.random() * 1000000) : seed,
      // matching_protocol removed - agents now use DecisionProcedure
      use_beliefs: config?.use_beliefs ?? false,
    };

    const config1: Partial<SimulationConfig> = {
      ...baseConfig,
      bargaining_protocol: protocol1,
    };

    const config2: Partial<SimulationConfig> = {
      ...baseConfig,
      bargaining_protocol: protocol2,
    };

    // Get short labels for display
    const getShortLabel = (p: BargainingProtocol) =>
      BARGAINING_PROTOCOLS.find((bp) => bp.value === p)?.shortLabel ?? p;

    sendCommand({
      command: 'comparison',
      config1,
      config2,
      label1: getShortLabel(protocol1),
      label2: getShortLabel(protocol2),
    });

    setOpen(false);
  };

  const handleExitComparison = () => {
    sendCommand({ command: 'exit_comparison' });
  };

  if (comparisonMode) {
    return (
      <Button
        onClick={handleExitComparison}
        variant="outline"
        size="sm"
        className="gap-1"
      >
        <X className="h-4 w-4" />
        Exit Compare
      </Button>
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          title="Compare Protocols"
        >
          <GitCompare className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Compare Protocols</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <p className="text-sm text-zinc-400">
            Run two simulations side-by-side with different bargaining protocols
            but the same initial conditions (seed).
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Protocol A</label>
              <select
                value={protocol1}
                onChange={(e) => setProtocol1(e.target.value as BargainingProtocol)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm"
              >
                {BARGAINING_PROTOCOLS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Protocol B</label>
              <select
                value={protocol2}
                onChange={(e) => setProtocol2(e.target.value as BargainingProtocol)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm"
              >
                {BARGAINING_PROTOCOLS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Agents</label>
              <input
                type="number"
                value={nAgents}
                onChange={(e) => setNAgents(Number(e.target.value))}
                min={2}
                max={50}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Grid Size</label>
              <input
                type="number"
                value={gridSizeVal}
                onChange={(e) => setGridSizeVal(Number(e.target.value))}
                min={5}
                max={30}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="Random"
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm"
              />
            </div>
          </div>

          <Button onClick={handleStartComparison} className="w-full">
            Start Comparison
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
