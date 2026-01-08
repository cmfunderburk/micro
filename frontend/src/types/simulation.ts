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
  bargaining_power: number;
  has_beliefs?: boolean;
}

// Belief system types
export interface TypeBelief {
  target_id: string;
  believed_alpha: number;
  confidence: number;
  n_interactions: number;
}

export interface PriceBelief {
  mean: number;
  variance: number;
  n_observations: number;
}

export interface AgentBeliefs {
  type_beliefs: TypeBelief[];
  price_belief: PriceBelief | null;
  n_trades_in_memory: number;
}

export type BeliefMap = Record<string, AgentBeliefs>;

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
  bargaining_protocol: "nash" | "rubinstein" | "tioli" | "asymmetric_nash";
  matching_protocol: "opportunistic" | "stable_roommates";
  bargaining_power_distribution?: "uniform" | "gaussian" | "bimodal";
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
  beliefs?: BeliefMap;
}

export interface WebSocketMessage {
  type: "init" | "tick" | "status" | "reset" | "speed" | "config" | "error" | "comparison_init" | "comparison_tick" | "comparison_exit";
  running?: boolean;
  speed?: number;
  message?: string;
  config?: SimulationConfig;
  comparison_mode?: boolean;
}

export type TickMessage = TickData & WebSocketMessage;

// Time series data point for charts
export interface TimeSeriesPoint {
  tick: number;
  welfare: number;
  trades: number;
}

// Comparison mode types
export interface ComparisonSimulation {
  sim_id: string;
  label: string;
  tick: number;
  agents: Agent[];
  trades: Trade[];
  metrics: Metrics;
  config: {
    grid_size: number;
  };
  beliefs: BeliefMap;
}

export interface ComparisonTickData {
  comparison_mode: boolean;
  simulations: ComparisonSimulation[];
}

export interface ComparisonTimeSeriesPoint {
  tick: number;
  welfare_a: number;
  welfare_b: number;
  trades_a: number;
  trades_b: number;
}
