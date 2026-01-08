/**
 * Replay view component.
 *
 * Shows the simulation state at the current replay tick.
 */

import { useRef, useEffect, useCallback, useState } from 'react';
import { useReplayStore } from '@/store/replayStore';
import { TimelineSlider } from './TimelineSlider';
import { ReplayControls } from './ReplayControls';
import type { Agent } from '@/types/simulation';

// Map alpha (0-1) to color (red to blue via purple)
function alphaToColor(alpha: number): string {
  const hue = alpha * 240;
  return `hsl(${hue}, 70%, 50%)`;
}

interface ReplayCanvasProps {
  width: number;
  height: number;
}

function ReplayCanvas({ width, height }: ReplayCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const getCurrentTickData = useReplayStore((state) => state.getCurrentTickData);
  const currentTick = useReplayStore((state) => state.currentTick);

  const tickData = getCurrentTickData();

  const gridSize = tickData?.agents[0]
    ? Math.max(...tickData.agents.map(a => Math.max(a.position[0], a.position[1]))) + 1
    : 15;

  const cellSize = Math.min(width, height) / gridSize;
  const agentRadius = cellSize * 0.35;

  const posToCanvas = useCallback(
    (row: number, col: number): [number, number] => {
      const x = (col + 0.5) * cellSize;
      const y = (row + 0.5) * cellSize;
      return [x, y];
    },
    [cellSize]
  );

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, height);

    // Draw grid lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;

    for (let i = 0; i <= gridSize; i++) {
      const pos = i * cellSize;
      ctx.beginPath();
      ctx.moveTo(pos, 0);
      ctx.lineTo(pos, height);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, pos);
      ctx.lineTo(width, pos);
      ctx.stroke();
    }

    if (!tickData) return;

    // Build position map for co-location
    const posMap = new Map<string, Agent[]>();
    for (const agent of tickData.agents) {
      const key = `${agent.position[0]},${agent.position[1]}`;
      const existing = posMap.get(key) || [];
      existing.push(agent);
      posMap.set(key, existing);
    }

    const getAgentCanvasPos = (agent: Agent): [number, number] => {
      const [row, col] = agent.position;
      const [baseX, baseY] = posToCanvas(row, col);

      const key = `${row},${col}`;
      const colocated = posMap.get(key);

      if (!colocated || colocated.length <= 1) return [baseX, baseY];

      const index = colocated.findIndex(a => a.id === agent.id);
      const count = colocated.length;

      const offsetRadius = agentRadius * 0.6;
      const angle = (2 * Math.PI * index) / count;
      const offsetX = Math.cos(angle) * offsetRadius;
      const offsetY = Math.sin(angle) * offsetRadius;

      return [baseX + offsetX, baseY + offsetY];
    };

    // Draw agents
    for (const agent of tickData.agents) {
      const [x, y] = getAgentCanvasPos(agent);
      const color = alphaToColor(agent.alpha);

      const posKey = `${agent.position[0]},${agent.position[1]}`;
      const colocatedCount = posMap.get(posKey)?.length ?? 1;
      const drawRadius = colocatedCount > 1 ? agentRadius * 0.7 : agentRadius;

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, drawRadius, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }, [tickData, gridSize, cellSize, width, height, agentRadius, posToCanvas]);

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

export function ReplayView() {
  const loadedRun = useReplayStore((state) => state.loadedRun);
  const getCurrentTickData = useReplayStore((state) => state.getCurrentTickData);

  const containerRef = useRef<HTMLDivElement>(null);
  const [gridSize, setGridSize] = useState(500);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateGridSize = () => {
      const rect = container.getBoundingClientRect();
      const availableWidth = rect.width - 12;
      const availableHeight = rect.height - 80; // Account for controls
      const size = Math.min(availableWidth, availableHeight, 600);
      setGridSize(Math.max(300, Math.floor(size)));
    };

    const resizeObserver = new ResizeObserver(updateGridSize);
    resizeObserver.observe(container);
    requestAnimationFrame(updateGridSize);

    return () => resizeObserver.disconnect();
  }, []);

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
