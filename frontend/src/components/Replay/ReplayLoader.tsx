/**
 * Replay loader component.
 *
 * Lists available saved runs and allows loading them for replay.
 */

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { useReplayStore } from '@/store/replayStore';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { FileVideo, Loader2, X } from 'lucide-react';

export function ReplayLoader() {
  const replayMode = useReplayStore((state) => state.replayMode);
  const availableRuns = useReplayStore((state) => state.availableRuns);
  const setAvailableRuns = useReplayStore((state) => state.setAvailableRuns);
  const loadRun = useReplayStore((state) => state.loadRun);
  const exitReplay = useReplayStore((state) => state.exitReplay);

  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/runs');
      if (!response.ok) {
        throw new Error('Failed to fetch runs');
      }
      const runs = await response.json();
      setAvailableRuns(runs);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [setAvailableRuns]);

  // Fetch available runs when dialog opens
  useEffect(() => {
    if (open) {
      fetchRuns();
    }
  }, [open, fetchRuns]);

  const handleLoadRun = async (runName: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/runs/${runName}`);
      if (!response.ok) {
        throw new Error('Failed to load run');
      }
      const runData = await response.json();
      loadRun(runData);
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (replayMode) {
    return (
      <Button
        onClick={exitReplay}
        variant="outline"
        size="sm"
        className="gap-1"
      >
        <X className="h-4 w-4" />
        Exit Replay
      </Button>
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          title="Load Replay"
        >
          <FileVideo className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Load Saved Run</DialogTitle>
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

          {!loading && !error && availableRuns.length === 0 && (
            <div className="text-zinc-500 text-sm py-4">
              No saved runs found. Run a simulation with logging enabled to create runs.
            </div>
          )}

          {!loading && !error && availableRuns.length > 0 && (
            <div className="space-y-2">
              {availableRuns.map((run) => (
                <button
                  key={run.name}
                  onClick={() => handleLoadRun(run.name)}
                  className="w-full text-left p-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
                >
                  <div className="font-medium">{run.name}</div>
                  <div className="text-xs text-zinc-400 mt-1">
                    {run.protocol} | {run.n_agents} agents | {run.n_ticks} ticks
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
