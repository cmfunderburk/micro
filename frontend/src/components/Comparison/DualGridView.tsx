/**
 * Dual grid view for comparison mode.
 *
 * Renders two simulation grids side-by-side with labels.
 */

import { useRef, useEffect, useCallback, useState } from 'react';
import { useComparisonStore } from '@/store/comparisonStore';
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

// Map alpha (0-1) to color (red to blue via purple)
function alphaToColor(alpha: number): string {
  const hue = alpha * 240;
  return `hsl(${hue}, 70%, 50%)`;
}

function ComparisonGridCanvas({
  width,
  height,
  agents,
  trades,
  gridSize,
  label,
}: GridCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const tradeAnimationsRef = useRef<Map<string, { trade: Trade; startTime: number }>>(new Map());

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

  const agentsByPosition = useCallback(() => {
    const posMap = new Map<string, Agent[]>();
    for (const agent of agents) {
      const key = `${agent.position[0]},${agent.position[1]}`;
      const existing = posMap.get(key) || [];
      existing.push(agent);
      posMap.set(key, existing);
    }
    return posMap;
  }, [agents]);

  const getAgentCanvasPos = useCallback(
    (agent: Agent, posMap?: Map<string, Agent[]>): [number, number] => {
      const [row, col] = agent.position;
      const [baseX, baseY] = posToCanvas(row, col);

      if (!posMap) return [baseX, baseY];

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
    },
    [posToCanvas, agentRadius]
  );

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

    const agentById = new Map<string, Agent>();
    for (const agent of agents) {
      agentById.set(agent.id, agent);
    }
    const posMap = agentsByPosition();

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

      const [x1, y1] = getAgentCanvasPos(agent1, posMap);
      const [x2, y2] = getAgentCanvasPos(agent2, posMap);

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
      const [x, y] = getAgentCanvasPos(agent, posMap);
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

    if (tradeAnimationsRef.current.size > 0) {
      animationRef.current = requestAnimationFrame(render);
    }
  }, [agents, gridSize, cellSize, width, height, agentRadius, getAgentCanvasPos, agentsByPosition]);

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

export function DualGridView() {
  const simulationA = useComparisonStore((state) => state.simulationA);
  const simulationB = useComparisonStore((state) => state.simulationB);
  const comparisonMode = useComparisonStore((state) => state.comparisonMode);

  const containerRef = useRef<HTMLDivElement>(null);
  const [gridSize, setGridSize] = useState(280);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateGridSize = () => {
      const rect = container.getBoundingClientRect();
      // Each grid takes half the width minus gap
      const availableWidth = (rect.width - 24) / 2;
      const availableHeight = rect.height - 40; // Account for labels
      const size = Math.min(availableWidth, availableHeight, 400);
      setGridSize(Math.max(200, Math.floor(size)));
    };

    const resizeObserver = new ResizeObserver(updateGridSize);
    resizeObserver.observe(container);
    requestAnimationFrame(updateGridSize);

    return () => resizeObserver.disconnect();
  }, []);

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
