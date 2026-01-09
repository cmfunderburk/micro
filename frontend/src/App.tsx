import { useSimulationSocket } from '@/hooks/useSimulationSocket';
import { useSimulationStore } from '@/store';
import { useComparisonStore } from '@/store/comparisonStore';
import { useReplayStore } from '@/store/replayStore';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { TradeHistoryPanel, EdgeworthModal } from '@/components/TradeInspection';
import { NetworkPanel } from '@/components/Network';
import { ConfigModal, ExportMenu } from '@/components/Config';
import { ComparisonControls, ComparisonTradeHistoryModal } from '@/components/Comparison';
import { ReplayLoader } from '@/components/Replay';
import { ScenarioBrowser } from '@/components/Scenarios';
import { NormalModeLayout, ComparisonModeLayout, ReplayModeLayout } from '@/components/Layout';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Play, Pause, SkipForward, RotateCcw, Network, Settings, History } from 'lucide-react';
import { useState, type ReactElement } from 'react';

function App(): ReactElement {
  const { sendCommand } = useSimulationSocket();

  const connected = useSimulationStore((state) => state.connected);
  const running = useSimulationStore((state) => state.running);
  const speed = useSimulationStore((state) => state.speed);

  // Mode states
  const comparisonMode = useComparisonStore((state) => state.comparisonMode);
  const replayMode = useReplayStore((state) => state.replayMode);

  // Keyboard shortcuts (disabled in comparison mode since it controls both sims)
  useKeyboardShortcuts({
    sendCommand,
    running,
    enabled: !comparisonMode,
  });

  // Modal states
  const [networkPanelOpen, setNetworkPanelOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [tradeHistoryOpen, setTradeHistoryOpen] = useState(false);
  const [comparisonTradeHistoryOpen, setComparisonTradeHistoryOpen] = useState(false);

  // Trade inspection state
  const tradeHistory = useSimulationStore((state) => state.tradeHistory);
  const selectedTradeIndex = useSimulationStore((state) => state.selectedTradeIndex);
  const setSelectedTradeIndex = useSimulationStore((state) => state.setSelectedTradeIndex);
  const selectedTrade = selectedTradeIndex !== null ? tradeHistory[selectedTradeIndex] : null;

  // Command handlers
  const handleStart = (): void => sendCommand({ command: 'start' });
  const handleStop = (): void => sendCommand({ command: 'stop' });
  const handleStep = (): void => sendCommand({ command: 'step' });
  const handleReset = (): void => sendCommand({ command: 'reset' });
  const handleSpeedChange = (value: number[]): void => {
    sendCommand({ command: 'speed', speed: value[0] });
  };

  // Render the appropriate layout based on mode
  function renderMainContent(): ReactElement {
    if (replayMode) {
      return <ReplayModeLayout />;
    }
    if (comparisonMode) {
      return <ComparisonModeLayout />;
    }
    return <NormalModeLayout />;
  }

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
            onClick={() => {
              if (comparisonMode) {
                setComparisonTradeHistoryOpen(true);
              } else {
                setTradeHistoryOpen(true);
              }
            }}
            variant="outline"
            size="icon"
            className="h-8 w-8"
            title="Trade History"
            disabled={replayMode}
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

      {/* Main content - renders appropriate layout based on mode */}
      {renderMainContent()}

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

      {/* Comparison Trade History Modal */}
      <ComparisonTradeHistoryModal
        open={comparisonTradeHistoryOpen}
        onOpenChange={setComparisonTradeHistoryOpen}
      />
    </div>
  );
}

export default App;
