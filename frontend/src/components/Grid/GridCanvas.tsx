/**
 * Canvas-based grid visualization for the simulation.
 *
 * Renders:
 * - Grid lines
 * - Agents as colored circles (color based on alpha: red=0, blue=1)
 * - Trade animations (lines between trading agents that fade)
 * - Selection highlight for selected agent
 * - Perception radius overlay for selected agent
 */

import { useRef, useEffect, useCallback } from 'react';
import { useSimulationStore } from '@/store';
import type { Agent, Trade } from '@/types/simulation';

interface GridCanvasProps {
  width?: number;
  height?: number;
}

// Map alpha (0-1) to color (red to blue via purple)
function alphaToColor(alpha: number): string {
  // HSL interpolation: 0 (red) = hue 0, 1 (blue) = hue 240
  const hue = alpha * 240;
  return `hsl(${hue}, 70%, 50%)`;
}

export function GridCanvas({ width = 600, height = 600 }: GridCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const tradeAnimationsRef = useRef<Map<string, { trade: Trade; startTime: number }>>(new Map());

  const agents = useSimulationStore((state) => state.agents);
  const gridSize = useSimulationStore((state) => state.gridSize);
  const recentTrades = useSimulationStore((state) => state.recentTrades);
  const selectedAgentId = useSimulationStore((state) => state.selectedAgentId);
  const setSelectedAgentId = useSimulationStore((state) => state.setSelectedAgentId);
  const hoveredAgentId = useSimulationStore((state) => state.hoveredAgentId);
  const setHoveredAgentId = useSimulationStore((state) => state.setHoveredAgentId);
  const overlays = useSimulationStore((state) => state.overlays);

  const cellSize = Math.min(width, height) / gridSize;
  const agentRadius = cellSize * 0.35;

  // Get agent position in canvas coordinates
  const getAgentCanvasPos = useCallback(
    (agent: Agent): [number, number] => {
      const [row, col] = agent.position;
      const x = (col + 0.5) * cellSize;
      const y = (row + 0.5) * cellSize;
      return [x, y];
    },
    [cellSize]
  );

  // Find agent at canvas coordinates
  const findAgentAtPos = useCallback(
    (canvasX: number, canvasY: number): Agent | null => {
      for (const agent of agents) {
        const [ax, ay] = getAgentCanvasPos(agent);
        const dist = Math.sqrt((canvasX - ax) ** 2 + (canvasY - ay) ** 2);
        if (dist <= agentRadius) {
          return agent;
        }
      }
      return null;
    },
    [agents, getAgentCanvasPos, agentRadius]
  );

  // Handle mouse events
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const agent = findAgentAtPos(x, y);
      setHoveredAgentId(agent?.id ?? null);
    },
    [findAgentAtPos, setHoveredAgentId]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const agent = findAgentAtPos(x, y);
      setSelectedAgentId(agent?.id ?? null);
    },
    [findAgentAtPos, setSelectedAgentId]
  );

  // Add new trades to animation queue
  useEffect(() => {
    const now = Date.now();
    for (const trade of recentTrades) {
      const key = `${trade.agent1_id}-${trade.agent2_id}-${trade.tick}`;
      if (!tradeAnimationsRef.current.has(key)) {
        tradeAnimationsRef.current.set(key, { trade, startTime: now });
      }
    }
  }, [recentTrades]);

  // Main render function
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const now = Date.now();
    const TRADE_ANIMATION_DURATION = 2000; // 2 seconds

    // Clear canvas
    ctx.fillStyle = '#0f172a'; // slate-900
    ctx.fillRect(0, 0, width, height);

    // Draw grid lines
    ctx.strokeStyle = '#1e293b'; // slate-800
    ctx.lineWidth = 1;

    for (let i = 0; i <= gridSize; i++) {
      const pos = i * cellSize;

      // Vertical lines
      ctx.beginPath();
      ctx.moveTo(pos, 0);
      ctx.lineTo(pos, height);
      ctx.stroke();

      // Horizontal lines
      ctx.beginPath();
      ctx.moveTo(0, pos);
      ctx.lineTo(width, pos);
      ctx.stroke();
    }

    // Build agent lookup for trade animations
    const agentById = new Map<string, Agent>();
    for (const agent of agents) {
      agentById.set(agent.id, agent);
    }

    // Draw trade animations (before agents so they appear behind)
    for (const [key, { trade, startTime }] of tradeAnimationsRef.current) {
      const elapsed = now - startTime;
      if (elapsed > TRADE_ANIMATION_DURATION) {
        tradeAnimationsRef.current.delete(key);
        continue;
      }

      const agent1 = agentById.get(trade.agent1_id);
      const agent2 = agentById.get(trade.agent2_id);
      if (!agent1 || !agent2) continue;

      const [x1, y1] = getAgentCanvasPos(agent1);
      const [x2, y2] = getAgentCanvasPos(agent2);

      // Fade out over animation duration
      const alpha = 1 - elapsed / TRADE_ANIMATION_DURATION;

      ctx.strokeStyle = `rgba(34, 197, 94, ${alpha})`; // green-500
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }

    // Draw perception radius for selected agent
    if (overlays.perceptionRadius && selectedAgentId) {
      const selectedAgent = agentById.get(selectedAgentId);
      if (selectedAgent) {
        const [x, y] = getAgentCanvasPos(selectedAgent);
        const radiusPixels = selectedAgent.perception_radius * cellSize;

        ctx.strokeStyle = 'rgba(99, 102, 241, 0.3)'; // indigo-500
        ctx.fillStyle = 'rgba(99, 102, 241, 0.1)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, radiusPixels, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
    }

    // Draw agents
    for (const agent of agents) {
      const [x, y] = getAgentCanvasPos(agent);
      const color = alphaToColor(agent.alpha);

      // Draw selection ring
      if (agent.id === selectedAgentId) {
        ctx.strokeStyle = '#fbbf24'; // amber-400
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(x, y, agentRadius + 4, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Draw hover ring
      if (agent.id === hoveredAgentId && agent.id !== selectedAgentId) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, agentRadius + 2, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Draw agent circle
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, agentRadius, 0, Math.PI * 2);
      ctx.fill();

      // Draw border
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Continue animation loop if there are active trade animations
    if (tradeAnimationsRef.current.size > 0) {
      animationRef.current = requestAnimationFrame(render);
    }
  }, [
    agents,
    gridSize,
    cellSize,
    width,
    height,
    agentRadius,
    selectedAgentId,
    hoveredAgentId,
    overlays.perceptionRadius,
    getAgentCanvasPos,
  ]);

  // Start render loop
  useEffect(() => {
    render();

    // Request frame when we have trade animations
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
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="rounded-lg cursor-crosshair"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoveredAgentId(null)}
      onClick={handleClick}
    />
  );
}
