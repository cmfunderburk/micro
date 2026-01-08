/**
 * Zustand store for replay mode state.
 *
 * Manages loaded run data and playback position for replay.
 * Client-side seeking per ADR-002.
 */

import { create } from 'zustand';
import type { Agent, Trade, Metrics, TimeSeriesPoint, BeliefMap } from '@/types/simulation';

interface ReplayTickData {
  tick: number;
  agents: Agent[];
  trades: Trade[];
  metrics: Metrics;
  beliefs: BeliefMap;
}

interface RunInfo {
  name: string;
  path: string;
  n_ticks: number;
  protocol: string;
  n_agents: number;
}

interface LoadedRun {
  name: string;
  config: Record<string, unknown>;
  ticks: ReplayTickData[];
  n_ticks: number;
}

interface ReplayState {
  // Whether replay mode is active
  replayMode: boolean;
  setReplayMode: (active: boolean) => void;

  // Available runs (from server)
  availableRuns: RunInfo[];
  setAvailableRuns: (runs: RunInfo[]) => void;

  // Loaded run data
  loadedRun: LoadedRun | null;
  setLoadedRun: (run: LoadedRun | null) => void;

  // Current playback position
  currentTick: number;
  setCurrentTick: (tick: number) => void;

  // Playback state
  playing: boolean;
  playbackSpeed: number;
  setPlaying: (playing: boolean) => void;
  setPlaybackSpeed: (speed: number) => void;

  // Computed: current tick data
  getCurrentTickData: () => ReplayTickData | null;

  // Computed: time series history up to current tick
  getHistoryUpToTick: () => TimeSeriesPoint[];

  // Actions
  loadRun: (run: LoadedRun) => void;
  seekToTick: (tick: number) => void;
  stepForward: () => void;
  stepBackward: () => void;
  exitReplay: () => void;
}

export const useReplayStore = create<ReplayState>((set, get) => ({
  replayMode: false,
  setReplayMode: (active) => set({ replayMode: active }),

  availableRuns: [],
  setAvailableRuns: (runs) => set({ availableRuns: runs }),

  loadedRun: null,
  setLoadedRun: (run) => set({ loadedRun: run }),

  currentTick: 0,
  setCurrentTick: (tick) => set({ currentTick: tick }),

  playing: false,
  playbackSpeed: 1.0,
  setPlaying: (playing) => set({ playing }),
  setPlaybackSpeed: (speed) => set({ playbackSpeed: Math.max(0.1, Math.min(speed, 10.0)) }),

  getCurrentTickData: () => {
    const { loadedRun, currentTick } = get();
    if (!loadedRun || currentTick < 0 || currentTick >= loadedRun.ticks.length) {
      return null;
    }
    return loadedRun.ticks[currentTick];
  },

  getHistoryUpToTick: () => {
    const { loadedRun, currentTick } = get();
    if (!loadedRun) return [];

    return loadedRun.ticks
      .slice(0, currentTick + 1)
      .map((t) => ({
        tick: t.tick,
        welfare: t.metrics.total_welfare,
        trades: t.metrics.cumulative_trades,
      }));
  },

  loadRun: (run) => {
    set({
      loadedRun: run,
      currentTick: 0,
      replayMode: true,
      playing: false,
    });
  },

  seekToTick: (tick) => {
    const { loadedRun } = get();
    if (!loadedRun) return;

    const clampedTick = Math.max(0, Math.min(tick, loadedRun.n_ticks - 1));
    set({ currentTick: clampedTick });
  },

  stepForward: () => {
    const { loadedRun, currentTick } = get();
    if (!loadedRun) return;

    if (currentTick < loadedRun.n_ticks - 1) {
      set({ currentTick: currentTick + 1 });
    }
  },

  stepBackward: () => {
    const { currentTick } = get();
    if (currentTick > 0) {
      set({ currentTick: currentTick - 1 });
    }
  },

  exitReplay: () => {
    set({
      replayMode: false,
      loadedRun: null,
      currentTick: 0,
      playing: false,
    });
  },
}));
