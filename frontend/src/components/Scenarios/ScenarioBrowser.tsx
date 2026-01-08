/**
 * Scenario browser component.
 *
 * Lists pre-defined scenarios grouped by complexity level.
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { BookOpen, Loader2, Star } from 'lucide-react';
import type { Command } from '@/hooks/useSimulationSocket';

interface ScenarioInfo {
  name: string;
  title: string;
  complexity: number;
  description: string;
  n_agents: number;
  grid_size: number;
}

interface ScenarioBrowserProps {
  sendCommand: (command: Command) => void;
  disabled?: boolean;
}

// Complexity level labels
const COMPLEXITY_LABELS: Record<number, string> = {
  1: 'Basic',
  2: 'Intermediate',
  3: 'Advanced',
  4: 'Expert',
};

function ComplexityStars({ level }: { level: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: level }).map((_, i) => (
        <Star key={i} className="h-3 w-3 fill-amber-400 text-amber-400" />
      ))}
      {Array.from({ length: Math.max(0, 4 - level) }).map((_, i) => (
        <Star key={`empty-${i}`} className="h-3 w-3 text-zinc-600" />
      ))}
    </div>
  );
}

export function ScenarioBrowser({ sendCommand, disabled }: ScenarioBrowserProps) {
  const [open, setOpen] = useState(false);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      fetchScenarios();
    }
  }, [open]);

  const fetchScenarios = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/scenarios');
      if (!response.ok) {
        throw new Error('Failed to fetch scenarios');
      }
      const data = await response.json();
      setScenarios(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadScenario = async (scenarioName: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/scenarios/${scenarioName}`);
      if (!response.ok) {
        throw new Error('Failed to load scenario');
      }
      const data = await response.json();

      // Send config command with scenario config
      sendCommand({ command: 'config', config: data.config });
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // Group scenarios by complexity
  const scenariosByComplexity = scenarios.reduce((acc, s) => {
    if (!acc[s.complexity]) {
      acc[s.complexity] = [];
    }
    acc[s.complexity].push(s);
    return acc;
  }, {} as Record<number, ScenarioInfo[]>);

  const complexityLevels = Object.keys(scenariosByComplexity)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          title="Browse Scenarios"
          disabled={disabled}
        >
          <BookOpen className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Browse Scenarios</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto min-h-0 py-4">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
            </div>
          )}

          {error && (
            <div className="text-red-500 text-sm py-4">
              {error}
            </div>
          )}

          {!loading && !error && scenarios.length === 0 && (
            <div className="text-zinc-500 text-sm py-4">
              No scenarios found. Add YAML scenario files to the scenarios/ directory.
            </div>
          )}

          {!loading && !error && scenarios.length > 0 && (
            <div className="space-y-6">
              {complexityLevels.map((level) => (
                <div key={level}>
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-sm font-semibold text-zinc-300">
                      {COMPLEXITY_LABELS[level] ?? `Level ${level}`}
                    </h3>
                    <ComplexityStars level={level} />
                  </div>
                  <div className="space-y-2">
                    {scenariosByComplexity[level].map((scenario) => (
                      <button
                        key={scenario.name}
                        onClick={() => handleLoadScenario(scenario.name)}
                        className="w-full text-left p-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
                      >
                        <div className="font-medium">{scenario.title}</div>
                        {scenario.description && (
                          <div className="text-xs text-zinc-400 mt-1">
                            {scenario.description}
                          </div>
                        )}
                        <div className="text-xs text-zinc-500 mt-1">
                          {scenario.n_agents} agents | {scenario.grid_size}x{scenario.grid_size} grid
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
