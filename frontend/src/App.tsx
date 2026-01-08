import { useSimulationSocket } from '@/hooks/useSimulationSocket';
import { useSimulationStore } from '@/store';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { GridCanvas, AgentTooltip } from '@/components/Grid';
import { WelfareChart, TradeCountChart } from '@/components/Charts';
import { OverlayToggles } from '@/components/Controls';
import { TradeHistoryPanel, EdgeworthModal } from '@/components/TradeInspection';
import { Play, Pause, SkipForward, RotateCcw } from 'lucide-react';

function App() {
  const { sendCommand } = useSimulationSocket();

  const connected = useSimulationStore((state) => state.connected);
  const running = useSimulationStore((state) => state.running);
  const tick = useSimulationStore((state) => state.tick);
  const metrics = useSimulationStore((state) => state.metrics);
  const speed = useSimulationStore((state) => state.speed);
  const selectedAgentId = useSimulationStore((state) => state.selectedAgentId);
  const agents = useSimulationStore((state) => state.agents);

  const selectedAgent = selectedAgentId
    ? agents.find((a) => a.id === selectedAgentId)
    : null;

  // Trade inspection state
  const tradeHistory = useSimulationStore((state) => state.tradeHistory);
  const selectedTradeIndex = useSimulationStore((state) => state.selectedTradeIndex);
  const setSelectedTradeIndex = useSimulationStore((state) => state.setSelectedTradeIndex);
  const selectedTrade = selectedTradeIndex !== null ? tradeHistory[selectedTradeIndex] : null;

  const handleStart = () => sendCommand({ command: 'start' });
  const handleStop = () => sendCommand({ command: 'stop' });
  const handleStep = () => sendCommand({ command: 'step' });
  const handleReset = () => sendCommand({ command: 'reset' });
  const handleSpeedChange = (value: number[]) => {
    sendCommand({ command: 'speed', speed: value[0] });
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 p-4">
      <header className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Microecon Simulation</h1>
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${
              connected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-sm text-zinc-400">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-[1fr_300px] gap-4">
        {/* Main grid area */}
        <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
          <div className="relative">
            <GridCanvas width={600} height={600} />
            <AgentTooltip />
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2 mt-4">
            {running ? (
              <Button onClick={handleStop} variant="outline" size="icon">
                <Pause className="h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={handleStart} variant="outline" size="icon">
                <Play className="h-4 w-4" />
              </Button>
            )}
            <Button
              onClick={handleStep}
              variant="outline"
              size="icon"
              disabled={running}
            >
              <SkipForward className="h-4 w-4" />
            </Button>
            <Button onClick={handleReset} variant="outline" size="icon">
              <RotateCcw className="h-4 w-4" />
            </Button>

            <div className="flex items-center gap-2 ml-4 flex-1 max-w-xs">
              <span className="text-sm text-zinc-400">Speed:</span>
              <Slider
                value={[speed]}
                onValueChange={handleSpeedChange}
                min={0.5}
                max={10}
                step={0.5}
                className="flex-1"
              />
              <span className="text-sm w-12">{speed.toFixed(1)}x</span>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Metrics */}
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <h2 className="text-lg font-semibold mb-3">Metrics</h2>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-zinc-400">Tick</span>
                <span className="font-mono">{tick}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Total Trades</span>
                <span className="font-mono">{metrics.cumulative_trades}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Total Welfare</span>
                <span className="font-mono">
                  {metrics.total_welfare.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Welfare Gains</span>
                <span className="font-mono text-green-500">
                  +{metrics.welfare_gains.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          {/* Overlays */}
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <h2 className="text-lg font-semibold mb-3">Overlays</h2>
            <OverlayToggles />
          </div>

          {/* Selected Agent Details */}
          {selectedAgent && (
            <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
              <h2 className="text-lg font-semibold mb-3">Selected Agent</h2>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-zinc-400">ID</span>
                  <span className="font-mono">{selectedAgent.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Alpha</span>
                  <span className="font-mono">{selectedAgent.alpha.toFixed(3)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Utility</span>
                  <span className="font-mono">{selectedAgent.utility.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Endowment</span>
                  <span className="font-mono">
                    ({selectedAgent.endowment[0].toFixed(1)}, {selectedAgent.endowment[1].toFixed(1)})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Position</span>
                  <span className="font-mono">
                    ({selectedAgent.position[0]}, {selectedAgent.position[1]})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Perception</span>
                  <span className="font-mono">{selectedAgent.perception_radius}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Discount</span>
                  <span className="font-mono">{selectedAgent.discount_factor.toFixed(2)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Welfare Chart */}
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <h2 className="text-lg font-semibold mb-3">Welfare</h2>
            <WelfareChart />
          </div>

          {/* Trade Count Chart */}
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <h2 className="text-lg font-semibold mb-3">Trades</h2>
            <TradeCountChart />
          </div>

          {/* Trade History */}
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <h2 className="text-lg font-semibold mb-3">Trade History</h2>
            <TradeHistoryPanel />
          </div>
        </div>
      </div>

      {/* Edgeworth Box Modal */}
      <EdgeworthModal
        trade={selectedTrade}
        open={selectedTrade !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedTradeIndex(null);
        }}
      />
    </div>
  );
}

export default App;
