/**
 * Types for simulation data received from the backend.
 */

export interface Agent {
  id: string;
  position: [number, number]; // [row, col]
  endowment: [number, number]; // [x, y]
  alpha: number;
  utility: number;
  perception_radius: number;
  discount_factor: number;
}

export interface Trade {
  tick: number;
  agent1_id: string;
  agent2_id: string;
  alpha1: number;
  alpha2: number;
  pre_endowment_1: [number, number];
  pre_endowment_2: [number, number];
  post_allocation_1: [number, number];
  post_allocation_2: [number, number];
  gains: [number, number];
}

export interface Metrics {
  total_welfare: number;
  welfare_gains: number;
  cumulative_trades: number;
}

export interface SimulationConfig {
  n_agents: number;
  grid_size: number;
  perception_radius: number;
  discount_factor: number;
  seed: number | null;
  bargaining_protocol: "nash" | "rubinstein";
  matching_protocol: "opportunistic" | "stable_roommates";
  use_beliefs: boolean;
}

export interface TickData {
  tick: number;
  agents: Agent[];
  trades: Trade[];
  metrics: Metrics;
  config?: {
    grid_size: number;
  };
}

export interface WebSocketMessage {
  type: "init" | "tick" | "status" | "reset" | "speed" | "config" | "error";
  running?: boolean;
  speed?: number;
  message?: string;
  config?: SimulationConfig;
}

export type TickMessage = TickData & WebSocketMessage;

// Time series data point for charts
export interface TimeSeriesPoint {
  tick: number;
  welfare: number;
  trades: number;
}
