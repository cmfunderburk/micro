/**
 * Time-series chart showing cumulative trade count over time.
 */

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useSimulationStore } from '@/store';

export function TradeCountChart() {
  const history = useSimulationStore((state) => state.history);

  // Downsample if too many points
  const data = useMemo(() => {
    if (history.length <= 100) return history;

    // Take every nth point to get roughly 100 points
    const step = Math.ceil(history.length / 100);
    return history.filter((_, i) => i % step === 0 || i === history.length - 1);
  }, [history]);

  if (data.length === 0) {
    return (
      <div className="h-full min-h-[100px] bg-zinc-800 rounded flex items-center justify-center text-zinc-400 text-sm">
        Run simulation to see trade chart
      </div>
    );
  }

  return (
    <div className="h-full min-h-[100px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
          <XAxis
            dataKey="tick"
            stroke="#71717a"
            tick={{ fontSize: 10 }}
            tickLine={false}
          />
          <YAxis
            stroke="#71717a"
            tick={{ fontSize: 10 }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#27272a',
              border: '1px solid #3f3f46',
              borderRadius: '0.375rem',
              fontSize: '12px',
            }}
            labelFormatter={(tick) => `Tick ${tick}`}
            formatter={(value) => [value, 'Trades']}
          />
          <Line
            type="monotone"
            dataKey="trades"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
