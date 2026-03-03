/**
 * Shared chart configuration for Recharts components.
 *
 * Provides consistent styling across all charts in the application.
 */

/**
 * Default tooltip styling for dark theme.
 */
export const TOOLTIP_STYLE = {
  backgroundColor: '#27272a',
  border: '1px solid #3f3f46',
  borderRadius: '0.375rem',
  fontSize: '12px',
} as const;

/**
 * Alternative tooltip styling for comparison charts.
 */
export const TOOLTIP_STYLE_ALT = {
  backgroundColor: '#18181b',
  border: '1px solid #27272a',
  borderRadius: '0.5rem',
  fontSize: '0.75rem',
} as const;

/**
 * Axis stroke color (zinc-500).
 */
export const AXIS_STROKE = '#71717a';

/**
 * Grid line stroke color (zinc-700).
 */
export const GRID_STROKE = '#3f3f46';

/**
 * Chart colors.
 */
export const CHART_COLORS = {
  welfare: '#22c55e', // green-500
  trades: '#3b82f6', // blue-500
  protocolA: '#f97316', // orange-500
  protocolB: '#3b82f6', // blue-500
} as const;

/**
 * Common axis props for Recharts.
 */
export const AXIS_PROPS = {
  stroke: AXIS_STROKE,
  tick: { fontSize: 10 },
  tickLine: false,
} as const;

/**
 * Downsamples time series data to approximately maxPoints.
 * Always includes the last point.
 */
export function downsampleData<T>(data: T[], maxPoints: number = 100): T[] {
  if (data.length <= maxPoints) return data;

  const step = Math.ceil(data.length / maxPoints);
  return data.filter((_, i) => i % step === 0 || i === data.length - 1);
}
