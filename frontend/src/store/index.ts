/**
 * Zustand store for simulation state.
 */

import { create } from 'zustand';
import type { Agent, Trade, Metrics, SimulationConfig, TimeSeriesPoint } from '@/types/simulation';

interface SimulationState {
  // Connection state
  connected: boolean;
  setConnected: (connected: boolean) => void;

  // Simulation state
  running: boolean;
  setRunning: (running: boolean) => void;

  speed: number;
  setSpeed: (speed: number) => void;

  // Tick data
  tick: number;
  agents: Agent[];
  trades: Trade[];
  metrics: Metrics;
  gridSize: number;

  // Configuration
  config: SimulationConfig | null;
  setConfig: (config: SimulationConfig) => void;

  // Time series history
  history: TimeSeriesPoint[];
  maxHistoryLength: number;

  // Selected agent
  selectedAgentId: string | null;
  setSelectedAgentId: (id: string | null) => void;

  // Hovered agent
  hoveredAgentId: string | null;
  setHoveredAgentId: (id: string | null) => void;

  // Overlays
  overlays: {
    trails: boolean;
    perceptionRadius: boolean;
    heatmap: boolean;
    tradeConnections: boolean;
  };
  toggleOverlay: (overlay: keyof SimulationState['overlays']) => void;

  // Trade animations (recent trades that should animate)
  recentTrades: Trade[];

  // Actions
  updateTickData: (data: {
    tick: number;
    agents: Agent[];
    trades: Trade[];
    metrics: Metrics;
    config?: { grid_size: number };
  }) => void;

  reset: () => void;
}

const initialMetrics: Metrics = {
  total_welfare: 0,
  welfare_gains: 0,
  cumulative_trades: 0,
};

export const useSimulationStore = create<SimulationState>((set, get) => ({
  // Connection state
  connected: false,
  setConnected: (connected) => set({ connected }),

  // Simulation state
  running: false,
  setRunning: (running) => set({ running }),

  speed: 1.0,
  setSpeed: (speed) => set({ speed }),

  // Tick data
  tick: 0,
  agents: [],
  trades: [],
  metrics: initialMetrics,
  gridSize: 15,

  // Configuration
  config: null,
  setConfig: (config) => set({ config }),

  // Time series history
  history: [],
  maxHistoryLength: 1000,

  // Selected agent
  selectedAgentId: null,
  setSelectedAgentId: (id) => set({ selectedAgentId: id }),

  // Hovered agent
  hoveredAgentId: null,
  setHoveredAgentId: (id) => set({ hoveredAgentId: id }),

  // Overlays
  overlays: {
    trails: false,
    perceptionRadius: true,
    heatmap: false,
    tradeConnections: false,
  },
  toggleOverlay: (overlay) =>
    set((state) => ({
      overlays: {
        ...state.overlays,
        [overlay]: !state.overlays[overlay],
      },
    })),

  // Trade animations
  recentTrades: [],

  // Actions
  updateTickData: (data) => {
    const state = get();
    const newPoint: TimeSeriesPoint = {
      tick: data.tick,
      welfare: data.metrics.total_welfare,
      trades: data.metrics.cumulative_trades,
    };

    // Keep history bounded
    const newHistory = [...state.history, newPoint].slice(-state.maxHistoryLength);

    set({
      tick: data.tick,
      agents: data.agents,
      trades: data.trades,
      metrics: data.metrics,
      gridSize: data.config?.grid_size ?? state.gridSize,
      history: newHistory,
      recentTrades: data.trades, // Current tick's trades for animation
    });
  },

  reset: () =>
    set({
      tick: 0,
      agents: [],
      trades: [],
      metrics: initialMetrics,
      history: [],
      recentTrades: [],
      selectedAgentId: null,
    }),
}));
