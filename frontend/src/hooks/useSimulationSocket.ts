/**
 * WebSocket hook for simulation connection.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useSimulationStore } from '@/store';
import { useComparisonStore } from '@/store/comparisonStore';
import type { TickMessage, SimulationConfig, ComparisonSimulation } from '@/types/simulation';

// Get reset functions from stores (outside of hook to avoid selector issues)
const getResetFn = () => useSimulationStore.getState().reset;
const getComparisonResetFn = () => useComparisonStore.getState().reset;

export type Command =
  | { command: 'start' }
  | { command: 'stop' }
  | { command: 'step' }
  | { command: 'reset' }
  | { command: 'speed'; speed: number }
  | { command: 'config'; config: Partial<SimulationConfig> }
  | { command: 'comparison'; config1: Partial<SimulationConfig>; config2: Partial<SimulationConfig>; label1?: string; label2?: string }
  | { command: 'exit_comparison' };

export function useSimulationSocket() {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<number | null>(null);

  const setConnected = useSimulationStore((state) => state.setConnected);
  const setRunning = useSimulationStore((state) => state.setRunning);
  const setSpeed = useSimulationStore((state) => state.setSpeed);
  const setConfig = useSimulationStore((state) => state.setConfig);
  const updateTickData = useSimulationStore((state) => state.updateTickData);

  // Comparison store accessors
  const setComparisonMode = useComparisonStore((state) => state.setComparisonMode);
  const initComparison = useComparisonStore((state) => state.initComparison);
  const updateComparisonTick = useComparisonStore((state) => state.updateComparisonTick);

  const connect = useCallback(() => {
    // Use relative URL - Vite proxy will handle it
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/simulation`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
      setRunning(false);

      // Attempt to reconnect after 2 seconds
      reconnectTimeout.current = window.setTimeout(() => {
        console.log('Attempting to reconnect...');
        connect();
      }, 2000);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.current.onmessage = (event) => {
      try {
        const data: TickMessage = JSON.parse(event.data);

        switch (data.type) {
          case 'init':
          case 'tick':
            updateTickData({
              tick: data.tick,
              agents: data.agents,
              trades: data.trades,
              metrics: data.metrics,
              config: data.config ? { grid_size: data.config.grid_size } : undefined,
              beliefs: data.beliefs,
            });
            if (data.config) {
              setConfig(data.config);
            }
            // Sync running state from init message
            if (data.type === 'init' && data.running !== undefined) {
              setRunning(data.running);
            }
            break;

          case 'reset':
          case 'config':
            // Clear all UI state first, then set new data
            getResetFn()();
            updateTickData({
              tick: data.tick,
              agents: data.agents,
              trades: data.trades,
              metrics: data.metrics,
              config: data.config ? { grid_size: data.config.grid_size } : undefined,
              beliefs: data.beliefs,
            });
            if (data.config) {
              setConfig(data.config);
            }
            break;

          case 'status':
            if (data.running !== undefined) {
              setRunning(data.running);
            }
            break;

          case 'speed':
            if (data.speed !== undefined) {
              setSpeed(data.speed);
            }
            break;

          case 'error':
            console.error('Server error:', data.message);
            break;

          case 'comparison_init': {
            // Entering comparison mode
            const compareData = data as unknown as {
              type: string;
              comparison_mode: boolean;
              simulations: Array<{
                sim_id: string;
                label: string;
                config: SimulationConfig;
                tick_data: ComparisonSimulation;
              }>;
              running: boolean;
            };
            if (compareData.simulations?.length >= 2) {
              const simA = compareData.simulations[0];
              const simB = compareData.simulations[1];
              initComparison(
                { ...simA.tick_data, sim_id: simA.sim_id, label: simA.label },
                { ...simB.tick_data, sim_id: simB.sim_id, label: simB.label },
                simA.config,
                simB.config
              );
              setComparisonMode(true);
              if (compareData.running !== undefined) {
                setRunning(compareData.running);
              }
            }
            break;
          }

          case 'comparison_tick': {
            // Update comparison tick data
            const tickData = data as unknown as {
              type: string;
              comparison_mode: boolean;
              simulations: ComparisonSimulation[];
            };
            if (tickData.simulations) {
              updateComparisonTick(tickData.simulations);
            }
            break;
          }

          case 'comparison_exit':
            // Exiting comparison mode
            getComparisonResetFn()();
            setComparisonMode(false);
            // Handle the normal tick data that comes with exit
            updateTickData({
              tick: data.tick,
              agents: data.agents,
              trades: data.trades,
              metrics: data.metrics,
              config: data.config ? { grid_size: data.config.grid_size } : undefined,
              beliefs: data.beliefs,
            });
            if (data.config) {
              setConfig(data.config);
            }
            break;
        }
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };
  }, [setConnected, setRunning, setSpeed, setConfig, updateTickData, setComparisonMode, initComparison, updateComparisonTick]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);

  const sendCommand = useCallback((command: Command) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(command));
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    connected: ws.current?.readyState === WebSocket.OPEN,
    sendCommand,
    reconnect: connect,
  };
}
