/**
 * Dual grid view for comparison mode.
 *
 * Renders two simulation grids side-by-side with labels.
 */

import { useRef, useEffect, useCallback, type ReactElement } from 'react';
import { useComparisonStore } from '@/store/comparisonStore';
import { useDualContainerSize } from '@/hooks/useContainerSize';
import { alphaToColor } from '@/lib/colors';
import {
  groupAgentsByPosition,
  getAgentCanvasPos,
  getAgentDrawRadius,
  drawGridLines,
  clearCanvas,
  createAgentLookup,
} from '@/lib/gridUtils';
import type { Agent, Trade } from '@/types/simulation';

interface GridCanvasProps {
  width: number;
  height: number;
  agents: Agent[];
  trades: Trade[];
  gridSize: number;
  tick: number;
  label: string;
}

function ComparisonGridCanvas({
  width,
  height,
  agents,
  trades,
  gridSize,
  label,
}: GridCanvasProps): ReactElement {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const tradeAnimationsRef = useRef<Map<string, { trade: Trade; startTime: number }>>(new Map());
  const renderRef = useRef<(() => void) | undefined>(undefined);

  const cellSize = Math.min(width, height) / gridSize;
  const agentRadius = cellSize * 0.35;

  // Add new trades to animation queue
  useEffect(() => {
    const now = Date.now();
    for (const trade of trades) {
      const key = `${trade.agent1_id}-${trade.agent2_id}-${trade.tick}`;
      if (!tradeAnimationsRef.current.has(key)) {
        tradeAnimationsRef.current.set(key, { trade, startTime: now });
      }
    }
  }, [trades]);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const now = Date.now();
    const TRADE_ANIMATION_DURATION = 2000;

    clearCanvas(ctx, width, height);
    drawGridLines(ctx, gridSize, cellSize, width, height);

    const agentById = createAgentLookup(agents);
    const posMap = groupAgentsByPosition(agents);

    // Draw trade animations
    for (const [key, { trade, startTime }] of tradeAnimationsRef.current) {
      const elapsed = now - startTime;
      if (elapsed > TRADE_ANIMATION_DURATION) {
        tradeAnimationsRef.current.delete(key);
        continue;
      }

      const agent1 = agentById.get(trade.agent1_id);
      const agent2 = agentById.get(trade.agent2_id);
      if (!agent1 || !agent2) continue;

      const [x1, y1] = getAgentCanvasPos(agent1, posMap, cellSize, agentRadius);
      const [x2, y2] = getAgentCanvasPos(agent2, posMap, cellSize, agentRadius);

      const alpha = 1 - elapsed / TRADE_ANIMATION_DURATION;

      ctx.strokeStyle = `rgba(34, 197, 94, ${alpha})`;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }

    // Draw agents
    for (const agent of agents) {
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

    if (tradeAnimationsRef.current.size > 0) {
      animationRef.current = requestAnimationFrame(() => renderRef.current?.());
    }
  }, [agents, gridSize, cellSize, width, height, agentRadius]);

  useEffect(() => {
    renderRef.current = render;
  }, [render]);

  useEffect(() => {
    render();
    if (tradeAnimationsRef.current.size > 0) {
      animationRef.current = requestAnimationFrame(render);
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [render]);

  return (
    <div className="flex flex-col">
      <div className="text-sm font-semibold text-zinc-300 mb-1 text-center">{label}</div>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="rounded-lg"
      />
    </div>
  );
}

export function DualGridView(): ReactElement | null {
  const simulationA = useComparisonStore((state) => state.simulationA);
  const simulationB = useComparisonStore((state) => state.simulationB);
  const comparisonMode = useComparisonStore((state) => state.comparisonMode);
  const { containerRef, size: gridSize } = useDualContainerSize();

  if (!comparisonMode) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 flex items-center justify-center gap-6 min-h-0 p-3"
    >
      <ComparisonGridCanvas
        width={gridSize}
        height={gridSize}
        agents={simulationA.agents}
        trades={simulationA.trades}
        gridSize={simulationA.gridSize}
        tick={simulationA.tick}
        label={`${simulationA.label} (${simulationA.config?.bargaining_protocol ?? 'N/A'})`}
      />
      <ComparisonGridCanvas
        width={gridSize}
        height={gridSize}
        agents={simulationB.agents}
        trades={simulationB.trades}
        gridSize={simulationB.gridSize}
        tick={simulationB.tick}
        label={`${simulationB.label} (${simulationB.config?.bargaining_protocol ?? 'N/A'})`}
      />
    </div>
  );
}
