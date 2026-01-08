import { useSimulationSocket } from '@/hooks/useSimulationSocket';
import { useSimulationStore } from '@/store';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Play, Pause, SkipForward, RotateCcw } from 'lucide-react';

function App() {
  const { sendCommand } = useSimulationSocket();

  const connected = useSimulationStore((state) => state.connected);
  const running = useSimulationStore((state) => state.running);
  const tick = useSimulationStore((state) => state.tick);
  const metrics = useSimulationStore((state) => state.metrics);
  const speed = useSimulationStore((state) => state.speed);
  const agents = useSimulationStore((state) => state.agents);
  const gridSize = useSimulationStore((state) => state.gridSize);

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
          <div
            className="bg-slate-900 rounded-lg flex items-center justify-center"
            style={{ height: '500px' }}
          >
            <div className="text-center text-zinc-400">
              <p className="text-lg mb-2">Grid View</p>
              <p className="text-sm">
                {agents.length} agents on {gridSize}x{gridSize} grid
              </p>
              <p className="text-sm">Tick: {tick}</p>
            </div>
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

          {/* Charts placeholder */}
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <h2 className="text-lg font-semibold mb-3">Charts</h2>
            <div className="h-32 bg-slate-900 rounded flex items-center justify-center text-zinc-400 text-sm">
              Charts coming in Phase 4
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
