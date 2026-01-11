/**
 * Edgeworth box visualization component.
 *
 * Renders the allocation space for a 2-agent, 2-good economy:
 * - Box dimensions = total endowments (X, Y)
 * - Endowment point and allocation point
 * - Indifference curves for both agents
 * - Contract curve
 * - Trade arrow
 */

import { useRef, useEffect, useCallback } from 'react';
import type { Trade } from '@/types/simulation';
import {
  cobbDouglasUtility,
  computeIndifferenceCurve,
  computeContractCurve,
} from './edgeworthMath';

interface EdgeworthBoxProps {
  trade: Trade;
  width?: number;
  height?: number;
}

const MARGIN = 40;

export function EdgeworthBox({ trade, width = 350, height = 350 }: EdgeworthBoxProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Compute total endowments (box dimensions)
  const totalX = trade.pre_holdings_1[0] + trade.pre_holdings_2[0];
  const totalY = trade.pre_holdings_1[1] + trade.pre_holdings_2[1];

  // Box dimensions in pixels
  const boxWidth = width - 2 * MARGIN;
  const boxHeight = height - 2 * MARGIN;

  // Convert goods coordinates to pixel coordinates
  const toPixel = useCallback(
    (x: number, y: number): [number, number] => {
      const px = MARGIN + (x / totalX) * boxWidth;
      // Flip y axis (y increases upward in goods space, downward in pixels)
      const py = MARGIN + boxHeight - (y / totalY) * boxHeight;
      return [px, py];
    },
    [totalX, totalY, boxWidth, boxHeight]
  );

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = '#1e293b'; // slate-800
    ctx.fillRect(0, 0, width, height);

    // Draw box border
    ctx.strokeStyle = '#94a3b8'; // slate-400
    ctx.lineWidth = 2;
    ctx.strokeRect(MARGIN, MARGIN, boxWidth, boxHeight);

    // Draw axis labels
    ctx.fillStyle = '#60a5fa'; // blue-400
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Agent A', MARGIN + boxWidth / 2, height - 8);

    ctx.fillStyle = '#fb923c'; // orange-400
    ctx.fillText('Agent B', MARGIN + boxWidth / 2, 14);

    // Compute utilities
    const utilityA_before = cobbDouglasUtility(
      trade.pre_holdings_1[0],
      trade.pre_holdings_1[1],
      trade.alpha1
    );
    const utilityA_after = cobbDouglasUtility(
      trade.post_allocation_1[0],
      trade.post_allocation_1[1],
      trade.alpha1
    );
    const utilityB_before = cobbDouglasUtility(
      trade.pre_holdings_2[0],
      trade.pre_holdings_2[1],
      trade.alpha2
    );
    const utilityB_after = cobbDouglasUtility(
      trade.post_allocation_2[0],
      trade.post_allocation_2[1],
      trade.alpha2
    );

    // Draw contract curve
    const contractPoints = computeContractCurve(
      trade.alpha1,
      trade.alpha2,
      totalX,
      totalY,
      40
    );
    if (contractPoints.length > 1) {
      ctx.strokeStyle = 'rgba(232, 121, 249, 0.5)'; // fuchsia-400
      ctx.lineWidth = 2;
      ctx.beginPath();
      const [startX, startY] = toPixel(contractPoints[0][0], contractPoints[0][1]);
      ctx.moveTo(startX, startY);
      for (let i = 1; i < contractPoints.length; i++) {
        const [px, py] = toPixel(contractPoints[i][0], contractPoints[i][1]);
        ctx.lineTo(px, py);
      }
      ctx.stroke();
    }

    // Draw indifference curves for Agent A (blue)
    const drawICurveA = (utility: number, alpha: number, lineWidth: number) => {
      const points = computeIndifferenceCurve(trade.alpha1, utility, 0.01 * totalX, 0.99 * totalX, 40);
      if (points.length < 2) return;

      ctx.strokeStyle = `rgba(96, 165, 250, ${alpha})`; // blue-400
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      let started = false;
      for (const [x, y] of points) {
        if (y > totalY) continue; // Clip to box
        const [px, py] = toPixel(x, y);
        if (!started) {
          ctx.moveTo(px, py);
          started = true;
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();
    };

    // Draw indifference curves for Agent B (orange)
    // B's coordinates need to be transformed: (x_B, y_B) -> (totalX - x_B, totalY - y_B)
    const drawICurveB = (utility: number, alpha: number, lineWidth: number) => {
      const points = computeIndifferenceCurve(trade.alpha2, utility, 0.01 * totalX, 0.99 * totalX, 40);
      if (points.length < 2) return;

      ctx.strokeStyle = `rgba(251, 146, 60, ${alpha})`; // orange-400
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      let started = false;
      for (const [xB, yB] of points) {
        // Transform to A's frame
        const xA = totalX - xB;
        const yA = totalY - yB;
        if (yA < 0 || yA > totalY) continue; // Clip to box
        const [px, py] = toPixel(xA, yA);
        if (!started) {
          ctx.moveTo(px, py);
          started = true;
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();
    };

    // Draw A's indifference curves (before = dashed, after = solid)
    drawICurveA(utilityA_before, 0.4, 1);
    drawICurveA(utilityA_after, 0.8, 1.5);

    // Draw B's indifference curves
    drawICurveB(utilityB_before, 0.4, 1);
    drawICurveB(utilityB_after, 0.8, 1.5);

    // Draw endowment point (orange/yellow)
    const [endowX, endowY] = toPixel(trade.pre_holdings_1[0], trade.pre_holdings_1[1]);
    ctx.fillStyle = '#fbbf24'; // amber-400
    ctx.strokeStyle = '#fbbf24';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(endowX, endowY, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Draw allocation point (green)
    const [allocX, allocY] = toPixel(trade.post_allocation_1[0], trade.post_allocation_1[1]);
    ctx.fillStyle = '#22c55e'; // green-500
    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(allocX, allocY, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Draw trade arrow (from endowment to allocation)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(endowX, endowY);
    ctx.lineTo(allocX, allocY);
    ctx.stroke();

    // Draw arrowhead
    const angle = Math.atan2(allocY - endowY, allocX - endowX);
    const arrowSize = 8;
    ctx.beginPath();
    ctx.moveTo(allocX, allocY);
    ctx.lineTo(
      allocX - arrowSize * Math.cos(angle - Math.PI / 6),
      allocY - arrowSize * Math.sin(angle - Math.PI / 6)
    );
    ctx.moveTo(allocX, allocY);
    ctx.lineTo(
      allocX - arrowSize * Math.cos(angle + Math.PI / 6),
      allocY - arrowSize * Math.sin(angle + Math.PI / 6)
    );
    ctx.stroke();
  }, [trade, width, height, boxWidth, boxHeight, totalX, totalY, toPixel]);

  useEffect(() => {
    render();
  }, [render]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="rounded-lg"
    />
  );
}
