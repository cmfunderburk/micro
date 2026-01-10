/**
 * Export menu for PNG, CSV, and JSON export.
 */

import { useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { useSimulationStore } from '@/store';
import { Image, FileSpreadsheet, FileJson } from 'lucide-react';

export function ExportMenu() {
  const tick = useSimulationStore((state) => state.tick);
  const agents = useSimulationStore((state) => state.agents);
  const tradeHistory = useSimulationStore((state) => state.tradeHistory);
  const history = useSimulationStore((state) => state.history);
  const config = useSimulationStore((state) => state.config);

  // Export PNG from grid canvas
  const exportPNG = useCallback(() => {
    // Specifically target the grid canvas by id
    const canvas = document.getElementById('grid-canvas') as HTMLCanvasElement | null;
    if (!canvas) {
      console.warn('Grid canvas not found');
      return;
    }

    const link = document.createElement('a');
    link.download = `simulation-tick-${tick}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, [tick]);

  // Export CSV
  const exportCSV = useCallback(() => {
    // Build CSV content
    const lines: string[] = [];

    // Agent data
    lines.push('# Agents');
    lines.push('id,position_row,position_col,holdings_x,holdings_y,alpha,utility,perception_radius,discount_factor');
    for (const agent of agents) {
      lines.push(
        [
          agent.id,
          agent.position[0],
          agent.position[1],
          agent.endowment[0],
          agent.endowment[1],
          agent.alpha,
          agent.utility,
          agent.perception_radius,
          agent.discount_factor,
        ].join(',')
      );
    }

    lines.push('');
    lines.push('# Trades');
    lines.push('tick,agent1_id,agent2_id,alpha1,alpha2,pre_x1,pre_y1,pre_x2,pre_y2,post_x1,post_y1,post_x2,post_y2,gain1,gain2');
    for (const trade of tradeHistory) {
      lines.push(
        [
          trade.tick,
          trade.agent1_id,
          trade.agent2_id,
          trade.alpha1,
          trade.alpha2,
          trade.pre_endowment_1[0],
          trade.pre_endowment_1[1],
          trade.pre_endowment_2[0],
          trade.pre_endowment_2[1],
          trade.post_allocation_1[0],
          trade.post_allocation_1[1],
          trade.post_allocation_2[0],
          trade.post_allocation_2[1],
          trade.gains[0],
          trade.gains[1],
        ].join(',')
      );
    }

    lines.push('');
    lines.push('# Time Series');
    lines.push('tick,welfare,trades');
    for (const point of history) {
      lines.push([point.tick, point.welfare, point.trades].join(','));
    }

    const csv = lines.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.download = `simulation-tick-${tick}.csv`;
    link.href = url;
    link.click();

    URL.revokeObjectURL(url);
  }, [agents, tradeHistory, history, tick]);

  // Export JSON
  const exportJSON = useCallback(() => {
    const data = {
      tick,
      config,
      agents,
      trades: tradeHistory,
      timeSeries: history,
      exportedAt: new Date().toISOString(),
    };

    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.download = `simulation-tick-${tick}.json`;
    link.href = url;
    link.click();

    URL.revokeObjectURL(url);
  }, [tick, config, agents, tradeHistory, history]);

  return (
    <div className="flex gap-1">
      <Button
        variant="outline"
        size="icon"
        onClick={exportPNG}
        title="Export PNG"
      >
        <Image className="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="icon"
        onClick={exportCSV}
        title="Export CSV"
      >
        <FileSpreadsheet className="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="icon"
        onClick={exportJSON}
        title="Export JSON"
      >
        <FileJson className="h-4 w-4" />
      </Button>
    </div>
  );
}
