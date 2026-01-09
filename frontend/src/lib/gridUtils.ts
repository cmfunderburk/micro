/**
 * Shared utilities for grid canvas rendering.
 *
 * Provides common calculations and rendering functions used by
 * GridCanvas, ComparisonGridCanvas, and ReplayCanvas.
 */

import type { Agent } from '@/types/simulation';

/**
 * Converts grid position to canvas pixel coordinates.
 */
export function posToCanvas(
  row: number,
  col: number,
  cellSize: number
): [number, number] {
  const x = (col + 0.5) * cellSize;
  const y = (row + 0.5) * cellSize;
  return [x, y];
}

/**
 * Groups agents by their grid position.
 * Returns a map from position key "row,col" to array of agents at that position.
 */
export function groupAgentsByPosition(agents: Agent[]): Map<string, Agent[]> {
  const posMap = new Map<string, Agent[]>();
  for (const agent of agents) {
    const key = `${agent.position[0]},${agent.position[1]}`;
    const existing = posMap.get(key) || [];
    existing.push(agent);
    posMap.set(key, existing);
  }
  return posMap;
}

/**
 * Gets canvas position for an agent, with offset for co-located agents.
 */
export function getAgentCanvasPos(
  agent: Agent,
  posMap: Map<string, Agent[]>,
  cellSize: number,
  agentRadius: number
): [number, number] {
  const [row, col] = agent.position;
  const [baseX, baseY] = posToCanvas(row, col, cellSize);

  const key = `${row},${col}`;
  const colocated = posMap.get(key);

  // If only one agent at this position, no offset needed
  if (!colocated || colocated.length <= 1) {
    return [baseX, baseY];
  }

  // Find this agent's index among co-located agents
  const index = colocated.findIndex((a) => a.id === agent.id);
  const count = colocated.length;

  // Offset in a circular pattern around the cell center
  const offsetRadius = agentRadius * 0.6;
  const angle = (2 * Math.PI * index) / count;
  const offsetX = Math.cos(angle) * offsetRadius;
  const offsetY = Math.sin(angle) * offsetRadius;

  return [baseX + offsetX, baseY + offsetY];
}

/**
 * Gets the draw radius for an agent, accounting for co-location.
 */
export function getAgentDrawRadius(
  agent: Agent,
  posMap: Map<string, Agent[]>,
  baseRadius: number
): number {
  const key = `${agent.position[0]},${agent.position[1]}`;
  const colocatedCount = posMap.get(key)?.length ?? 1;
  return colocatedCount > 1 ? baseRadius * 0.7 : baseRadius;
}

/**
 * Draws grid lines on a canvas context.
 */
export function drawGridLines(
  ctx: CanvasRenderingContext2D,
  gridSize: number,
  cellSize: number,
  width: number,
  height: number
): void {
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
}

/**
 * Clears canvas with background color.
 */
export function clearCanvas(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): void {
  ctx.fillStyle = '#0f172a'; // slate-900
  ctx.fillRect(0, 0, width, height);
}

/**
 * Creates an agent lookup map by ID.
 */
export function createAgentLookup(agents: Agent[]): Map<string, Agent> {
  const lookup = new Map<string, Agent>();
  for (const agent of agents) {
    lookup.set(agent.id, agent);
  }
  return lookup;
}
