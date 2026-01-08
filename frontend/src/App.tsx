import { useSimulationSocket } from '@/hooks/useSimulationSocket';
import { useSimulationStore } from '@/store';
import { useComparisonStore } from '@/store/comparisonStore';
import { useReplayStore } from '@/store/replayStore';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { GridCanvas, AgentTooltip } from '@/components/Grid';
import { WelfareChart, TradeCountChart } from '@/components/Charts';
import { OverlayToggles, PerspectiveMode } from '@/components/Controls';
import { BeliefPanel } from '@/components/Beliefs';
import { TradeHistoryPanel, EdgeworthModal } from '@/components/TradeInspection';
import { NetworkPanel } from '@/components/Network';
import { ConfigModal, ExportMenu } from '@/components/Config';
import {
  DualGridView,
  ComparisonControls,
  ComparisonWelfareChart,
  ComparisonTradeChart,
  ComparisonMetrics,
} from '@/components/Comparison';
import { ReplayLoader, ReplayView } from '@/components/Replay';
import { ScenarioBrowser } from '@/components/Scenarios';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Play, Pause, SkipForward, RotateCcw, Network, Settings, History } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

function App() {
  const { sendCommand } = useSimulationSocket();

  const connected = useSimulationStore((state) => state.connected);
  const running = useSimulationStore((state) => state.running);
  const tick = useSimulationStore((state) => state.tick);
  const metrics = useSimulationStore((state) => state.metrics);
  const speed = useSimulationStore((state) => state.speed);

  // Comparison mode state
  const comparisonMode = useComparisonStore((state) => state.comparisonMode);

  // Replay mode state
  const replayMode = useReplayStore((state) => state.replayMode);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    sendCommand,
    running,
    enabled: !comparisonMode, // Disable in comparison mode (controls both sims)
  });

  // Network panel state
  const [networkPanelOpen, setNetworkPanelOpen] = useState(false);

  // Config modal state
  const [configModalOpen, setConfigModalOpen] = useState(false);

  // Trade history modal state
  const [tradeHistoryOpen, setTradeHistoryOpen] = useState(false);

  // Trade inspection state
  const tradeHistory = useSimulationStore((state) => state.tradeHistory);
  const selectedTradeIndex = useSimulationStore((state) => state.selectedTradeIndex);
  const setSelectedTradeIndex = useSimulationStore((state) => state.setSelectedTradeIndex);
  const selectedTrade = selectedTradeIndex !== null ? tradeHistory[selectedTradeIndex] : null;

  // Grid container sizing for responsive square grid
  const gridContainerRef = useRef<HTMLDivElement>(null);
  const [gridSize, setGridSize] = useState(550);

  useEffect(() => {
    const container = gridContainerRef.current;
    if (!container) return;

    const updateGridSize = () => {
      const rect = container.getBoundingClientRect();
      // Take minimum of available width/height to maintain square, cap at 600px
      // Account for padding (6px on each side = 12px total from p-3)
      const availableWidth = rect.width - 12;
      const availableHeight = rect.height - 12;
      const availableSize = Math.min(availableWidth, availableHeight, 600);
      setGridSize(Math.max(300, Math.floor(availableSize)));
    };

    const resizeObserver = new ResizeObserver(updateGridSize);
    resizeObserver.observe(container);
    // Initial calculation with a small delay to ensure layout is complete
    requestAnimationFrame(updateGridSize);

    return () => resizeObserver.disconnect();
  }, []);

  const handleStart = () => sendCommand({ command: 'start' });
  const handleStop = () => sendCommand({ command: 'stop' });
  const handleStep = () => sendCommand({ command: 'step' });
  const handleReset = () => sendCommand({ command: 'reset' });
  const handleSpeedChange = (value: number[]) => {
    sendCommand({ command: 'speed', speed: value[0] });
  };

  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-zinc-50 p-3 overflow-hidden">
      {/* Header with controls */}
      <header className="flex items-center gap-4 mb-3 flex-shrink-0">
        <h1 className="text-xl font-bold whitespace-nowrap">Microecon</h1>

        {/* Simulation controls */}
        <div className="flex items-center gap-1">
          {running ? (
            <Button onClick={handleStop} variant="outline" size="icon" className="h-8 w-8">
              <Pause className="h-4 w-4" />
            </Button>
          ) : (
            <Button onClick={handleStart} variant="outline" size="icon" className="h-8 w-8">
              <Play className="h-4 w-4" />
            </Button>
          )}
          <Button
            onClick={handleStep}
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={running}
          >
            <SkipForward className="h-4 w-4" />
          </Button>
          <Button onClick={handleReset} variant="outline" size="icon" className="h-8 w-8">
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>

        {/* Speed slider */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-zinc-400">Speed:</span>
          <Slider
            value={[speed]}
            onValueChange={handleSpeedChange}
            min={0.5}
            max={10}
            step={0.5}
            className="w-24"
          />
          <span className="text-xs w-10 font-mono">{speed.toFixed(1)}x</span>
        </div>

        {/* Utility buttons */}
        <div className="flex items-center gap-1">
          <ScenarioBrowser sendCommand={sendCommand} disabled={comparisonMode || replayMode} />
          <ComparisonControls sendCommand={sendCommand} />
          <ReplayLoader />
          <Button
            onClick={() => setTradeHistoryOpen(true)}
            variant="outline"
            size="icon"
            className="h-8 w-8"
            title="Trade History"
            disabled={comparisonMode || replayMode}
          >
            <History className="h-4 w-4" />
          </Button>
          <Button
            onClick={() => setNetworkPanelOpen(true)}
            variant="outline"
            size="icon"
            className="h-8 w-8"
            title="Trade Network"
            disabled={comparisonMode || replayMode}
          >
            <Network className="h-4 w-4" />
          </Button>
          <Button
            onClick={() => setConfigModalOpen(true)}
            variant="outline"
            size="icon"
            className="h-8 w-8"
            title="Configuration"
            disabled={comparisonMode || replayMode}
          >
            <Settings className="h-4 w-4" />
          </Button>
          <ExportMenu />
        </div>

        {/* Connection status - push to right */}
        <div className="flex items-center gap-2 ml-auto">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              connected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-xs text-zinc-400">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>

      {/* Main content - conditional on mode */}
      {replayMode ? (
        /* Replay mode layout */
        <div className="flex-1 grid grid-cols-[200px_1fr_320px] gap-3 min-h-0">
          {/* Left column: Replay info */}
          <div className="flex flex-col gap-3 min-h-0">
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-shrink-0">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400">Replay Mode</h2>
              <p className="text-xs text-zinc-500">
                Viewing saved simulation run. Use controls below the grid to navigate.
              </p>
            </div>
            <div className="flex-1" />
          </div>

          {/* Middle column: Replay view */}
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 flex flex-col min-h-0">
            <ReplayView />
          </div>

          {/* Right column: Placeholder */}
          <div className="flex flex-col gap-3 min-h-0">
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-1 min-h-0 flex flex-col items-center justify-center">
              <p className="text-xs text-zinc-500 text-center">
                Charts coming soon for replay mode
              </p>
            </div>
          </div>
        </div>
      ) : comparisonMode ? (
        /* Comparison mode layout */
        <div className="flex-1 grid grid-cols-[200px_1fr_320px] gap-3 min-h-0">
          {/* Left column: Comparison Metrics */}
          <div className="flex flex-col gap-3 min-h-0">
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-shrink-0">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400">Comparison</h2>
              <ComparisonMetrics />
            </div>
            <div className="flex-1" />
          </div>

          {/* Middle column: Dual grids */}
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 flex flex-col min-h-0">
            <DualGridView />
          </div>

          {/* Right column: Comparison Charts */}
          <div className="flex flex-col gap-3 min-h-0">
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-1 min-h-0 flex flex-col">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400 flex-shrink-0">Welfare Comparison</h2>
              <div className="flex-1 min-h-0">
                <ComparisonWelfareChart />
              </div>
            </div>
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-1 min-h-0 flex flex-col">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400 flex-shrink-0">Trades Comparison</h2>
              <div className="flex-1 min-h-0">
                <ComparisonTradeChart />
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Normal mode layout */
        <div className="flex-1 grid grid-cols-[200px_1fr_320px] gap-3 min-h-0">
          {/* Left column: Metrics and Overlays */}
          <div className="flex flex-col gap-3 min-h-0">
            {/* Compact Metrics */}
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-shrink-0">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400">Metrics</h2>
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
            </div>

            {/* Overlays */}
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-shrink-0">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400">Overlays</h2>
              <OverlayToggles />
            </div>

            {/* Beliefs */}
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-shrink-0 overflow-hidden">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400">Beliefs</h2>
              <BeliefPanel />
            </div>

            {/* Perspective Mode */}
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-shrink-0">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400">Perspective</h2>
              <PerspectiveMode />
            </div>

            {/* Spacer to push content up */}
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
            {/* Welfare Chart */}
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-1 min-h-0 flex flex-col">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400 flex-shrink-0">Welfare</h2>
              <div className="flex-1 min-h-0">
                <WelfareChart />
              </div>
            </div>

            {/* Trade Count Chart */}
            <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800 flex-1 min-h-0 flex flex-col">
              <h2 className="text-sm font-semibold mb-2 text-zinc-400 flex-shrink-0">Trades</h2>
              <div className="flex-1 min-h-0">
                <TradeCountChart />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Trade History Modal */}
      <Dialog open={tradeHistoryOpen} onOpenChange={setTradeHistoryOpen}>
        <DialogContent className="max-w-md max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Trade History</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto min-h-0">
            <TradeHistoryPanel />
          </div>
        </DialogContent>
      </Dialog>

      {/* Edgeworth Box Modal */}
      <EdgeworthModal
        trade={selectedTrade}
        open={selectedTrade !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedTradeIndex(null);
        }}
      />

      {/* Network Panel */}
      <NetworkPanel
        open={networkPanelOpen}
        onOpenChange={setNetworkPanelOpen}
      />

      {/* Config Modal */}
      <ConfigModal
        open={configModalOpen}
        onOpenChange={setConfigModalOpen}
        sendCommand={sendCommand}
      />
    </div>
  );
}

export default App;
