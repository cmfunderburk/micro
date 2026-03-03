/**
 * Time-series chart showing total welfare over time.
 */

import { useMemo, type ReactElement } from 'react';
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
import {
  TOOLTIP_STYLE,
  AXIS_PROPS,
  GRID_STROKE,
  CHART_COLORS,
  downsampleData,
} from '@/lib/chartConfig';

export function WelfareChart(): ReactElement {
  const history = useSimulationStore((state) => state.history);
  const data = useMemo(() => downsampleData(history), [history]);

  if (data.length === 0) {
    return (
      <div className="h-full min-h-[100px] bg-zinc-800 rounded flex items-center justify-center text-zinc-400 text-sm">
        Run simulation to see welfare chart
      </div>
    );
  }

  return (
    <div className="h-full min-h-[100px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis dataKey="tick" {...AXIS_PROPS} />
          <YAxis {...AXIS_PROPS} tickFormatter={(value) => value.toFixed(0)} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelFormatter={(tick) => `Tick ${tick}`}
            formatter={(value) => [typeof value === 'number' ? value.toFixed(2) : value, 'Welfare']}
          />
          <Line
            type="monotone"
            dataKey="welfare"
            stroke={CHART_COLORS.welfare}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
