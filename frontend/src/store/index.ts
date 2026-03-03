/**
 * Zustand store for simulation state.
 */

import { create } from 'zustand';
import type { Agent, Trade, Metrics, SimulationConfig, TimeSeriesPoint, BeliefMap } from '@/types/simulation';

// Position history for movement trails
interface PositionHistory {
  [agentId: string]: Array<[number, number]>; // Array of [row, col]
}

// Trade history for connections overlay
interface TradeConnection {
  agent1_id: string;
  agent2_id: string;
  count: number;
  lastTick: number;
}

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

  // Beliefs
  beliefs: BeliefMap;

  // Time series history
  history: TimeSeriesPoint[];
  maxHistoryLength: number;

  // Position history for trails
  positionHistory: PositionHistory;
  maxTrailLength: number;

  // Trade connections for overlay (pruned to maxTradeConnections)
  tradeConnections: TradeConnection[];
  maxTradeConnections: number;

  // Trade history for inspection
  tradeHistory: Trade[];
  maxTradeHistory: number;
  selectedTradeIndex: number | null;
  setSelectedTradeIndex: (index: number | null) => void;

  // Selected agent
  selectedAgentId: string | null;
  setSelectedAgentId: (id: string | null) => void;

  // Hovered agent
  hoveredAgentId: string | null;
  setHoveredAgentId: (id: string | null) => void;

  // Perspective mode - view simulation from a specific agent's perspective
  perspectiveMode: boolean;
  perspectiveAgentId: string | null;
  showGroundTruth: boolean;
  setPerspectiveMode: (enabled: boolean) => void;
  setPerspectiveAgentId: (id: string | null) => void;
  setShowGroundTruth: (show: boolean) => void;

  // Overlays (default to off for a neutral simulation baseline)
  overlays: {
    trails: boolean;
    perceptionRadius: boolean;
    tradeConnections: boolean;
    beliefConnections: boolean;
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
    beliefs?: BeliefMap;
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

  // Beliefs
  beliefs: {},

  // Time series history
  history: [],
  maxHistoryLength: 1000,

  // Position history for trails
  positionHistory: {},
  maxTrailLength: 20,

  // Trade connections for overlay
  tradeConnections: [],
  maxTradeConnections: 100,

  // Trade history for inspection
  tradeHistory: [],
  maxTradeHistory: 100,
  selectedTradeIndex: null,
  setSelectedTradeIndex: (index) => set({ selectedTradeIndex: index }),

  // Selected agent
  selectedAgentId: null,
  setSelectedAgentId: (id) => set({ selectedAgentId: id }),

  // Hovered agent
  hoveredAgentId: null,
  setHoveredAgentId: (id) => set({ hoveredAgentId: id }),

  // Perspective mode
  perspectiveMode: false,
  perspectiveAgentId: null,
  showGroundTruth: false,
  setPerspectiveMode: (enabled) => set({
    perspectiveMode: enabled,
    // Clear agent selection when disabling
    perspectiveAgentId: enabled ? null : null,
  }),
  setPerspectiveAgentId: (id) => set({ perspectiveAgentId: id }),
  setShowGroundTruth: (show) => set({ showGroundTruth: show }),

  // Overlays (default to off for a neutral simulation baseline)
  overlays: {
    trails: false,
    perceptionRadius: false,
    tradeConnections: false,
    beliefConnections: false,
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

    // Update position history for trails
    const newPositionHistory: PositionHistory = { ...state.positionHistory };
    for (const agent of data.agents) {
      const history = newPositionHistory[agent.id] || [];
      history.push(agent.position);
      // Keep trail bounded
      newPositionHistory[agent.id] = history.slice(-state.maxTrailLength);
    }

    // Update trade connections
    let newConnections = [...state.tradeConnections];
    for (const trade of data.trades) {
      // Find existing connection
      const existing = newConnections.find(
        (c) =>
          (c.agent1_id === trade.agent1_id && c.agent2_id === trade.agent2_id) ||
          (c.agent1_id === trade.agent2_id && c.agent2_id === trade.agent1_id)
      );
      if (existing) {
        existing.count++;
        existing.lastTick = data.tick;
      } else {
        newConnections.push({
          agent1_id: trade.agent1_id,
          agent2_id: trade.agent2_id,
          count: 1,
          lastTick: data.tick,
        });
      }
    }
    // Prune old connections: keep most recent by lastTick
    if (newConnections.length > state.maxTradeConnections) {
      newConnections = newConnections
        .sort((a, b) => b.lastTick - a.lastTick)
        .slice(0, state.maxTradeConnections);
    }

    // Append new trades to history
    const newTradeHistory = [...state.tradeHistory, ...data.trades].slice(-state.maxTradeHistory);

    set({
      tick: data.tick,
      agents: data.agents,
      trades: data.trades,
      metrics: data.metrics,
      gridSize: data.config?.grid_size ?? state.gridSize,
      history: newHistory,
      positionHistory: newPositionHistory,
      tradeConnections: newConnections,
      tradeHistory: newTradeHistory,
      recentTrades: data.trades, // Current tick's trades for animation
      beliefs: data.beliefs ?? state.beliefs,
    });
  },

  reset: () =>
    set({
      tick: 0,
      agents: [],
      trades: [],
      metrics: initialMetrics,
      history: [],
      positionHistory: {},
      tradeConnections: [],
      tradeHistory: [],
      selectedTradeIndex: null,
      recentTrades: [],
      selectedAgentId: null,
      beliefs: {},
      perspectiveMode: false,
      perspectiveAgentId: null,
      showGroundTruth: false,
    }),
}));
