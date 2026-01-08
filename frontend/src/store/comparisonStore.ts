/**
 * Zustand store for comparison mode state.
 *
 * Manages two simultaneous simulations for side-by-side protocol comparison.
 */

import { create } from 'zustand';
import type {
  Agent,
  Trade,
  Metrics,
  SimulationConfig,
  ComparisonSimulation,
  ComparisonTimeSeriesPoint,
  BeliefMap,
} from '@/types/simulation';

// State for a single simulation in comparison mode
interface SimulationState {
  sim_id: string;
  label: string;
  config: SimulationConfig | null;
  tick: number;
  agents: Agent[];
  trades: Trade[];
  metrics: Metrics;
  gridSize: number;
  beliefs: BeliefMap;
}

const initialMetrics: Metrics = {
  total_welfare: 0,
  welfare_gains: 0,
  cumulative_trades: 0,
};

const initialSimState = (): SimulationState => ({
  sim_id: '',
  label: '',
  config: null,
  tick: 0,
  agents: [],
  trades: [],
  metrics: initialMetrics,
  gridSize: 15,
  beliefs: {},
});

interface ComparisonState {
  // Whether comparison mode is active
  comparisonMode: boolean;
  setComparisonMode: (active: boolean) => void;

  // The two simulations
  simulationA: SimulationState;
  simulationB: SimulationState;

  // Time series history for comparison charts
  history: ComparisonTimeSeriesPoint[];
  maxHistoryLength: number;

  // Actions
  initComparison: (
    simA: ComparisonSimulation,
    simB: ComparisonSimulation,
    configA: SimulationConfig,
    configB: SimulationConfig
  ) => void;

  updateComparisonTick: (simulations: ComparisonSimulation[]) => void;

  reset: () => void;
}

export const useComparisonStore = create<ComparisonState>((set, get) => ({
  comparisonMode: false,
  setComparisonMode: (active) => set({ comparisonMode: active }),

  simulationA: initialSimState(),
  simulationB: initialSimState(),

  history: [],
  maxHistoryLength: 1000,

  initComparison: (simA, simB, configA, configB) => {
    set({
      comparisonMode: true,
      simulationA: {
        sim_id: simA.sim_id,
        label: simA.label,
        config: configA,
        tick: simA.tick,
        agents: simA.agents,
        trades: simA.trades,
        metrics: simA.metrics,
        gridSize: simA.config?.grid_size ?? 15,
        beliefs: simA.beliefs ?? {},
      },
      simulationB: {
        sim_id: simB.sim_id,
        label: simB.label,
        config: configB,
        tick: simB.tick,
        agents: simB.agents,
        trades: simB.trades,
        metrics: simB.metrics,
        gridSize: simB.config?.grid_size ?? 15,
        beliefs: simB.beliefs ?? {},
      },
      history: [],
    });
  },

  updateComparisonTick: (simulations) => {
    const state = get();
    if (simulations.length < 2) return;

    // Match simulations to A/B by sim_id
    const simA = simulations.find((s) => s.sim_id === state.simulationA.sim_id) ?? simulations[0];
    const simB = simulations.find((s) => s.sim_id === state.simulationB.sim_id) ?? simulations[1];

    // Add to history
    const newPoint: ComparisonTimeSeriesPoint = {
      tick: simA.tick,
      welfare_a: simA.metrics.total_welfare,
      welfare_b: simB.metrics.total_welfare,
      trades_a: simA.metrics.cumulative_trades,
      trades_b: simB.metrics.cumulative_trades,
    };

    const newHistory = [...state.history, newPoint].slice(-state.maxHistoryLength);

    set({
      simulationA: {
        ...state.simulationA,
        tick: simA.tick,
        agents: simA.agents,
        trades: simA.trades,
        metrics: simA.metrics,
        gridSize: simA.config?.grid_size ?? state.simulationA.gridSize,
        beliefs: simA.beliefs ?? {},
      },
      simulationB: {
        ...state.simulationB,
        tick: simB.tick,
        agents: simB.agents,
        trades: simB.trades,
        metrics: simB.metrics,
        gridSize: simB.config?.grid_size ?? state.simulationB.gridSize,
        beliefs: simB.beliefs ?? {},
      },
      history: newHistory,
    });
  },

  reset: () =>
    set({
      comparisonMode: false,
      simulationA: initialSimState(),
      simulationB: initialSimState(),
      history: [],
    }),
}));
