/**
 * Comparison charts showing metrics for both simulations.
 *
 * Overlays welfare and trade count lines for side-by-side comparison.
 */

import { useComparisonStore } from '@/store/comparisonStore';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export function ComparisonWelfareChart() {
  const history = useComparisonStore((state) => state.history);
  const simulationA = useComparisonStore((state) => state.simulationA);
  const simulationB = useComparisonStore((state) => state.simulationB);

  // Limit to last 100 points for performance
  const displayData = history.slice(-100);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={displayData}>
        <XAxis
          dataKey="tick"
          stroke="#71717a"
          fontSize={10}
          tickLine={false}
          axisLine={{ stroke: '#27272a' }}
        />
        <YAxis
          stroke="#71717a"
          fontSize={10}
          tickLine={false}
          axisLine={{ stroke: '#27272a' }}
          width={40}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            borderRadius: '0.5rem',
            fontSize: '0.75rem',
          }}
          labelStyle={{ color: '#a1a1aa' }}
        />
        <Legend
          wrapperStyle={{ fontSize: '0.75rem' }}
          iconSize={8}
        />
        <Line
          type="monotone"
          dataKey="welfare_a"
          name={simulationA.label || 'A'}
          stroke="#f97316"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="welfare_b"
          name={simulationB.label || 'B'}
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ComparisonTradeChart() {
  const history = useComparisonStore((state) => state.history);
  const simulationA = useComparisonStore((state) => state.simulationA);
  const simulationB = useComparisonStore((state) => state.simulationB);

  const displayData = history.slice(-100);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={displayData}>
        <XAxis
          dataKey="tick"
          stroke="#71717a"
          fontSize={10}
          tickLine={false}
          axisLine={{ stroke: '#27272a' }}
        />
        <YAxis
          stroke="#71717a"
          fontSize={10}
          tickLine={false}
          axisLine={{ stroke: '#27272a' }}
          width={40}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            borderRadius: '0.5rem',
            fontSize: '0.75rem',
          }}
          labelStyle={{ color: '#a1a1aa' }}
        />
        <Legend
          wrapperStyle={{ fontSize: '0.75rem' }}
          iconSize={8}
        />
        <Line
          type="monotone"
          dataKey="trades_a"
          name={simulationA.label || 'A'}
          stroke="#f97316"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="trades_b"
          name={simulationB.label || 'B'}
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ComparisonMetrics() {
  const simulationA = useComparisonStore((state) => state.simulationA);
  const simulationB = useComparisonStore((state) => state.simulationB);

  return (
    <div className="grid grid-cols-2 gap-4 text-sm">
      <div className="space-y-2">
        <div className="font-medium text-orange-500">{simulationA.label}</div>
        <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
          <span className="text-zinc-500">Tick</span>
          <span className="font-mono">{simulationA.tick}</span>
          <span className="text-zinc-500">Trades</span>
          <span className="font-mono">{simulationA.metrics.cumulative_trades}</span>
          <span className="text-zinc-500">Welfare</span>
          <span className="font-mono">{simulationA.metrics.total_welfare.toFixed(1)}</span>
          <span className="text-zinc-500">Gains</span>
          <span className="font-mono text-green-500">+{simulationA.metrics.welfare_gains.toFixed(1)}</span>
        </div>
      </div>
      <div className="space-y-2">
        <div className="font-medium text-blue-500">{simulationB.label}</div>
        <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
          <span className="text-zinc-500">Tick</span>
          <span className="font-mono">{simulationB.tick}</span>
          <span className="text-zinc-500">Trades</span>
          <span className="font-mono">{simulationB.metrics.cumulative_trades}</span>
          <span className="text-zinc-500">Welfare</span>
          <span className="font-mono">{simulationB.metrics.total_welfare.toFixed(1)}</span>
          <span className="text-zinc-500">Gains</span>
          <span className="font-mono text-green-500">+{simulationB.metrics.welfare_gains.toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
}
