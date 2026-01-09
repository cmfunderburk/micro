/**
 * Main layout components for different simulation modes.
 *
 * Extracts the three main content layouts from App.tsx for better readability:
 * - NormalModeLayout: Standard simulation view
 * - ComparisonModeLayout: Side-by-side protocol comparison
 * - ReplayModeLayout: Playback of saved runs
 */

import { useRef, useEffect, useState, type ReactElement } from 'react';
import { useSimulationStore } from '@/store';
import { GridCanvas, AgentTooltip } from '@/components/Grid';
import { WelfareChart, TradeCountChart } from '@/components/Charts';
import { OverlayToggles, PerspectiveMode } from '@/components/Controls';
import { BeliefPanel } from '@/components/Beliefs';
import {
  DualGridView,
  ComparisonWelfareChart,
  ComparisonTradeChart,
  ComparisonMetrics,
} from '@/components/Comparison';
import { ReplayView } from '@/components/Replay';

/**
 * Panel wrapper with consistent styling.
 */
interface PanelProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

function Panel({ title, children, className = '' }: PanelProps): ReactElement {
  return (
    <div className={`bg-zinc-900 rounded-lg p-3 border border-zinc-800 ${className}`}>
      {title && <h2 className="text-sm font-semibold mb-2 text-zinc-400">{title}</h2>}
      {children}
    </div>
  );
}

/**
 * Normal simulation mode layout.
 */
export function NormalModeLayout(): ReactElement {
  const tick = useSimulationStore((state) => state.tick);
  const metrics = useSimulationStore((state) => state.metrics);

  const gridContainerRef = useRef<HTMLDivElement>(null);
  const [gridSize, setGridSize] = useState(550);

  useEffect(() => {
    const container = gridContainerRef.current;
    if (!container) return;

    const updateGridSize = (): void => {
      const rect = container.getBoundingClientRect();
      const availableWidth = rect.width - 12;
      const availableHeight = rect.height - 12;
      const availableSize = Math.min(availableWidth, availableHeight, 600);
      setGridSize(Math.max(300, Math.floor(availableSize)));
    };

    const resizeObserver = new ResizeObserver(updateGridSize);
    resizeObserver.observe(container);
    requestAnimationFrame(updateGridSize);

    return () => resizeObserver.disconnect();
  }, []);

  return (
    <div className="flex-1 grid grid-cols-[200px_1fr_320px] gap-3 min-h-0">
      {/* Left column: Metrics and Overlays */}
      <div className="flex flex-col gap-3 min-h-0">
        <Panel title="Metrics" className="flex-shrink-0">
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-zinc-500 text-xs">Tick</span>
              <span className="font-mono text-xs">{tick}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500 text-xs">Trades</span>
              <span className="font-mono text-xs">{metrics.cumulative_trades}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500 text-xs">Welfare</span>
              <span className="font-mono text-xs">{metrics.total_welfare.toFixed(1)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500 text-xs">Gains</span>
              <span className="font-mono text-xs text-green-500">
                +{metrics.welfare_gains.toFixed(1)}
              </span>
            </div>
          </div>
        </Panel>

        <Panel title="Overlays" className="flex-shrink-0">
          <OverlayToggles />
        </Panel>

        <Panel title="Beliefs" className="flex-shrink-0 overflow-hidden">
          <BeliefPanel />
        </Panel>

        <Panel title="Perspective" className="flex-shrink-0">
          <PerspectiveMode />
        </Panel>

        <div className="flex-1" />
      </div>

      {/* Middle column: Grid canvas */}
      <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex flex-col min-h-0">
        <div
          ref={gridContainerRef}
          className="flex-1 flex items-center justify-center min-h-0"
        >
          <div className="relative">
            <GridCanvas width={gridSize} height={gridSize} />
            <AgentTooltip />
          </div>
        </div>
      </div>

      {/* Right column: Charts */}
      <div className="flex flex-col gap-3 min-h-0">
        <Panel title="Welfare" className="flex-1 min-h-0 flex flex-col">
          <div className="flex-1 min-h-0">
            <WelfareChart />
          </div>
        </Panel>

        <Panel title="Trades" className="flex-1 min-h-0 flex flex-col">
          <div className="flex-1 min-h-0">
            <TradeCountChart />
          </div>
        </Panel>
      </div>
    </div>
  );
}

/**
 * Comparison mode layout for side-by-side protocol comparison.
 */
export function ComparisonModeLayout(): ReactElement {
  return (
    <div className="flex-1 grid grid-cols-[200px_1fr_320px] gap-3 min-h-0">
      {/* Left column: Comparison Metrics */}
      <div className="flex flex-col gap-3 min-h-0">
        <Panel title="Comparison" className="flex-shrink-0">
          <ComparisonMetrics />
        </Panel>
        <div className="flex-1" />
      </div>

      {/* Middle column: Dual grids */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 flex flex-col min-h-0">
        <DualGridView />
      </div>

      {/* Right column: Comparison Charts */}
      <div className="flex flex-col gap-3 min-h-0">
        <Panel title="Welfare Comparison" className="flex-1 min-h-0 flex flex-col">
          <div className="flex-1 min-h-0">
            <ComparisonWelfareChart />
          </div>
        </Panel>
        <Panel title="Trades Comparison" className="flex-1 min-h-0 flex flex-col">
          <div className="flex-1 min-h-0">
            <ComparisonTradeChart />
          </div>
        </Panel>
      </div>
    </div>
  );
}

/**
 * Replay mode layout for viewing saved simulation runs.
 */
export function ReplayModeLayout(): ReactElement {
  return (
    <div className="flex-1 grid grid-cols-[200px_1fr_320px] gap-3 min-h-0">
      {/* Left column: Replay info */}
      <div className="flex flex-col gap-3 min-h-0">
        <Panel title="Replay Mode" className="flex-shrink-0">
          <p className="text-xs text-zinc-500">
            Viewing saved simulation run. Use controls below the grid to navigate.
          </p>
        </Panel>
        <div className="flex-1" />
      </div>

      {/* Middle column: Replay view */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 flex flex-col min-h-0">
        <ReplayView />
      </div>

      {/* Right column: Placeholder */}
      <div className="flex flex-col gap-3 min-h-0">
        <Panel className="flex-1 min-h-0 flex flex-col items-center justify-center">
          <p className="text-xs text-zinc-500 text-center">
            Charts coming soon for replay mode
          </p>
        </Panel>
      </div>
    </div>
  );
}

// Note: The parent App component handles mode switching using these layout components.
// Each layout component is self-contained and can be rendered directly based on mode state.
