/**
 * Replay view component.
 *
 * Shows the simulation state at the current replay tick.
 */

import { useRef, useEffect, useCallback, type ReactElement } from 'react';
import { useReplayStore } from '@/store/replayStore';
import { useContainerSize } from '@/hooks/useContainerSize';
import { alphaToColor } from '@/lib/colors';
import {
  groupAgentsByPosition,
  getAgentCanvasPos,
  getAgentDrawRadius,
  drawGridLines,
  clearCanvas,
} from '@/lib/gridUtils';
import { TimelineSlider } from './TimelineSlider';
import { ReplayControls } from './ReplayControls';
interface ReplayCanvasProps {
  width: number;
  height: number;
}

function ReplayCanvas({ width, height }: ReplayCanvasProps): ReactElement {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const getCurrentTickData = useReplayStore((state) => state.getCurrentTickData);
  const loadedRun = useReplayStore((state) => state.loadedRun);
  const currentTick = useReplayStore((state) => state.currentTick);

  const tickData = getCurrentTickData();

  // Use config grid_size from loaded run, fallback to 15
  const gridSize = (loadedRun?.config?.grid_size as number) ?? 15;

  const cellSize = Math.min(width, height) / gridSize;
  const agentRadius = cellSize * 0.35;

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    clearCanvas(ctx, width, height);
    drawGridLines(ctx, gridSize, cellSize, width, height);

    if (!tickData) return;

    const posMap = groupAgentsByPosition(tickData.agents);

    // Draw agents
    for (const agent of tickData.agents) {
      const [x, y] = getAgentCanvasPos(agent, posMap, cellSize, agentRadius);
      const color = alphaToColor(agent.alpha);
      const drawRadius = getAgentDrawRadius(agent, posMap, agentRadius);

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, drawRadius, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }, [tickData, gridSize, cellSize, width, height, agentRadius]);

  useEffect(() => {
    render();
  }, [render, currentTick]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="rounded-lg"
    />
  );
}

export function ReplayView(): ReactElement | null {
  const loadedRun = useReplayStore((state) => state.loadedRun);
  const getCurrentTickData = useReplayStore((state) => state.getCurrentTickData);
  const { containerRef, size: gridSize } = useContainerSize({ heightOffset: 80 });

  if (!loadedRun) return null;

  const tickData = getCurrentTickData();

  return (
    <div ref={containerRef} className="flex-1 flex flex-col min-h-0 p-3">
      {/* Replay info bar */}
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm">
          <span className="text-zinc-400">Replay:</span>{' '}
          <span className="font-medium">{loadedRun.name}</span>
        </div>
        <div className="text-xs text-zinc-500">
          Tick {tickData?.tick ?? 0} / {loadedRun.n_ticks - 1}
        </div>
      </div>

      {/* Timeline slider */}
      <div className="mb-3">
        <TimelineSlider />
      </div>

      {/* Controls */}
      <div className="mb-3 flex justify-center">
        <ReplayControls />
      </div>

      {/* Canvas */}
      <div className="flex-1 flex items-center justify-center min-h-0">
        <ReplayCanvas width={gridSize} height={gridSize} />
      </div>
    </div>
  );
}
