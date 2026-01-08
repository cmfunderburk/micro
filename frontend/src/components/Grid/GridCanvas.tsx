/**
 * Canvas-based grid visualization for the simulation.
 *
 * Renders:
 * - Grid lines
 * - Agents as colored circles (color based on alpha: red=0, blue=1)
 * - Trade animations (lines between trading agents that fade)
 * - Selection highlight for selected agent
 * - Overlays: perception radius, movement trails, trade connections
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
  const tick = useSimulationStore((state) => state.tick);
  const recentTrades = useSimulationStore((state) => state.recentTrades);
  const selectedAgentId = useSimulationStore((state) => state.selectedAgentId);
  const setSelectedAgentId = useSimulationStore((state) => state.setSelectedAgentId);
  const hoveredAgentId = useSimulationStore((state) => state.hoveredAgentId);
  const setHoveredAgentId = useSimulationStore((state) => state.setHoveredAgentId);
  const overlays = useSimulationStore((state) => state.overlays);
  const positionHistory = useSimulationStore((state) => state.positionHistory);
  const tradeConnections = useSimulationStore((state) => state.tradeConnections);
  const beliefs = useSimulationStore((state) => state.beliefs);

  // Perspective mode
  const perspectiveMode = useSimulationStore((state) => state.perspectiveMode);
  const perspectiveAgentId = useSimulationStore((state) => state.perspectiveAgentId);
  const showGroundTruth = useSimulationStore((state) => state.showGroundTruth);

  const cellSize = Math.min(width, height) / gridSize;
  const agentRadius = cellSize * 0.35;

  // Helper to check if target agent is visible from perspective agent
  const isVisibleFromPerspective = useCallback(
    (perspectiveAgent: Agent, targetAgent: Agent): boolean => {
      if (perspectiveAgent.id === targetAgent.id) return true;
      const [pr, pc] = perspectiveAgent.position;
      const [tr, tc] = targetAgent.position;
      const distance = Math.sqrt((pr - tr) ** 2 + (pc - tc) ** 2);
      return distance <= perspectiveAgent.perception_radius;
    },
    []
  );

  // Get position in canvas coordinates
  const posToCanvas = useCallback(
    (row: number, col: number): [number, number] => {
      const x = (col + 0.5) * cellSize;
      const y = (row + 0.5) * cellSize;
      return [x, y];
    },
    [cellSize]
  );

  // Group agents by position for co-location offset calculation
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

  // Get agent position in canvas coordinates, with offset for co-located agents
  const getAgentCanvasPos = useCallback(
    (agent: Agent, posMap?: Map<string, Agent[]>): [number, number] => {
      const [row, col] = agent.position;
      const [baseX, baseY] = posToCanvas(row, col);

      // If no position map provided, return base position
      if (!posMap) return [baseX, baseY];

      const key = `${row},${col}`;
      const colocated = posMap.get(key);

      // If only one agent at this position, no offset needed
      if (!colocated || colocated.length <= 1) return [baseX, baseY];

      // Find this agent's index among co-located agents
      const index = colocated.findIndex(a => a.id === agent.id);
      const count = colocated.length;

      // Offset in a circular pattern around the cell center
      const offsetRadius = agentRadius * 0.6; // How far to offset
      const angle = (2 * Math.PI * index) / count;
      const offsetX = Math.cos(angle) * offsetRadius;
      const offsetY = Math.sin(angle) * offsetRadius;

      return [baseX + offsetX, baseY + offsetY];
    },
    [posToCanvas, agentRadius]
  );

  // Find agent at canvas coordinates (accounts for co-location offsets)
  const findAgentAtPos = useCallback(
    (canvasX: number, canvasY: number): Agent | null => {
      const posMap = agentsByPosition();
      for (const agent of agents) {
        const [ax, ay] = getAgentCanvasPos(agent, posMap);
        // Use smaller hit radius for co-located agents
        const posKey = `${agent.position[0]},${agent.position[1]}`;
        const colocatedCount = posMap.get(posKey)?.length ?? 1;
        const hitRadius = colocatedCount > 1 ? agentRadius * 0.7 : agentRadius;
        const dist = Math.sqrt((canvasX - ax) ** 2 + (canvasY - ay) ** 2);
        if (dist <= hitRadius) {
          return agent;
        }
      }
      return null;
    },
    [agents, getAgentCanvasPos, agentRadius, agentsByPosition]
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

    // Build agent lookup and position map for co-location
    const agentById = new Map<string, Agent>();
    for (const agent of agents) {
      agentById.set(agent.id, agent);
    }
    const posMap = agentsByPosition();

    // Draw trade connections overlay (behind everything else)
    if (overlays.tradeConnections) {
      for (const conn of tradeConnections) {
        const agent1 = agentById.get(conn.agent1_id);
        const agent2 = agentById.get(conn.agent2_id);
        if (!agent1 || !agent2) continue;

        const [x1, y1] = getAgentCanvasPos(agent1, posMap);
        const [x2, y2] = getAgentCanvasPos(agent2, posMap);

        // Fade based on recency (stronger for recent trades)
        const ticksSinceTrade = tick - conn.lastTick;
        const recencyAlpha = Math.max(0.1, 1 - ticksSinceTrade / 50);

        // Width based on trade count
        const lineWidth = Math.min(1 + conn.count * 0.5, 5);

        ctx.strokeStyle = `rgba(168, 85, 247, ${recencyAlpha * 0.5})`; // purple-500
        ctx.lineWidth = lineWidth;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }

    // Draw belief connections overlay (lines between agents with beliefs about each other)
    if (overlays.beliefConnections) {
      // Draw all type beliefs as directional lines
      for (const [agentId, agentBeliefs] of Object.entries(beliefs)) {
        const sourceAgent = agentById.get(agentId);
        if (!sourceAgent) continue;

        const [x1, y1] = getAgentCanvasPos(sourceAgent, posMap);

        for (const typeBelief of agentBeliefs.type_beliefs) {
          const targetAgent = agentById.get(typeBelief.target_id);
          if (!targetAgent) continue;

          const [x2, y2] = getAgentCanvasPos(targetAgent, posMap);

          // Opacity based on confidence
          const opacity = 0.2 + typeBelief.confidence * 0.5;
          // Width based on number of interactions
          const lineWidth = Math.min(1 + typeBelief.n_interactions * 0.3, 3);

          ctx.strokeStyle = `rgba(59, 130, 246, ${opacity})`; // blue-500
          ctx.lineWidth = lineWidth;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }
    }

    // Draw movement trails overlay
    if (overlays.trails) {
      for (const agent of agents) {
        const history = positionHistory[agent.id];
        if (!history || history.length < 2) continue;

        const color = alphaToColor(agent.alpha);

        for (let i = 1; i < history.length; i++) {
          const [prevRow, prevCol] = history[i - 1];
          const [currRow, currCol] = history[i];

          const [x1, y1] = posToCanvas(prevRow, prevCol);
          const [x2, y2] = posToCanvas(currRow, currCol);

          // Fade older positions
          const alpha = (i / history.length) * 0.5;

          ctx.strokeStyle = color.replace('50%)', `50%, ${alpha})`).replace('hsl', 'hsla');
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }
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

      const [x1, y1] = getAgentCanvasPos(agent1, posMap);
      const [x2, y2] = getAgentCanvasPos(agent2, posMap);

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
        const [x, y] = getAgentCanvasPos(selectedAgent, posMap);
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

    // Get perspective agent if in perspective mode
    const perspectiveAgent = perspectiveMode && perspectiveAgentId
      ? agentById.get(perspectiveAgentId) ?? null
      : null;

    // Draw perspective agent's perception radius if active
    if (perspectiveAgent) {
      const [px, py] = getAgentCanvasPos(perspectiveAgent, posMap);
      const radiusPixels = perspectiveAgent.perception_radius * cellSize;

      ctx.strokeStyle = 'rgba(34, 197, 94, 0.4)'; // green-500
      ctx.fillStyle = 'rgba(34, 197, 94, 0.05)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(px, py, radiusPixels, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }

    // Draw agents
    for (const agent of agents) {
      const [x, y] = getAgentCanvasPos(agent, posMap);
      const color = alphaToColor(agent.alpha);

      // Check if agent is co-located (use smaller radius like Python impl)
      const posKey = `${agent.position[0]},${agent.position[1]}`;
      const colocatedCount = posMap.get(posKey)?.length ?? 1;
      const drawRadius = colocatedCount > 1 ? agentRadius * 0.7 : agentRadius;

      // Calculate visibility/opacity based on perspective mode
      let opacity = 1.0;
      let isPerspectiveAgent = false;
      if (perspectiveAgent) {
        isPerspectiveAgent = agent.id === perspectiveAgent.id;
        if (!isPerspectiveAgent) {
          const isVisible = isVisibleFromPerspective(perspectiveAgent, agent);
          opacity = isVisible ? 1.0 : (showGroundTruth ? 0.15 : 0);
        }
      }

      // Skip drawing if completely invisible
      if (opacity === 0) continue;

      // Draw selection ring
      if (agent.id === selectedAgentId) {
        ctx.strokeStyle = `rgba(251, 191, 36, ${opacity})`; // amber-400
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(x, y, drawRadius + 4, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Draw hover ring
      if (agent.id === hoveredAgentId && agent.id !== selectedAgentId) {
        ctx.strokeStyle = `rgba(255, 255, 255, ${0.5 * opacity})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, drawRadius + 2, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Draw perspective agent highlight
      if (isPerspectiveAgent) {
        ctx.strokeStyle = 'rgba(34, 197, 94, 0.8)'; // green-500
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(x, y, drawRadius + 5, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Draw agent circle with opacity
      const [h, s, l] = color.match(/\d+/g)!.map(Number);
      ctx.fillStyle = `hsla(${h}, ${s}%, ${l}%, ${opacity})`;
      ctx.beginPath();
      ctx.arc(x, y, drawRadius, 0, Math.PI * 2);
      ctx.fill();

      // Draw border
      ctx.strokeStyle = `rgba(255, 255, 255, ${0.3 * opacity})`;
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
    tick,
    cellSize,
    width,
    height,
    agentRadius,
    selectedAgentId,
    hoveredAgentId,
    overlays,
    positionHistory,
    tradeConnections,
    beliefs,
    getAgentCanvasPos,
    posToCanvas,
    agentsByPosition,
    perspectiveMode,
    perspectiveAgentId,
    showGroundTruth,
    isVisibleFromPerspective,
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
      id="grid-canvas"
      width={width}
      height={height}
      className="rounded-lg cursor-crosshair"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoveredAgentId(null)}
      onClick={handleClick}
    />
  );
}
