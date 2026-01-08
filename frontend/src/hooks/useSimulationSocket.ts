/**
 * WebSocket hook for simulation connection.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useSimulationStore } from '@/store';
import type { TickMessage, SimulationConfig } from '@/types/simulation';

// Get reset function from store (outside of hook to avoid selector issues)
const getResetFn = () => useSimulationStore.getState().reset;

export type Command =
  | { command: 'start' }
  | { command: 'stop' }
  | { command: 'step' }
  | { command: 'reset' }
  | { command: 'speed'; speed: number }
  | { command: 'config'; config: Partial<SimulationConfig> };

export function useSimulationSocket() {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<number | null>(null);

  const setConnected = useSimulationStore((state) => state.setConnected);
  const setRunning = useSimulationStore((state) => state.setRunning);
  const setSpeed = useSimulationStore((state) => state.setSpeed);
  const setConfig = useSimulationStore((state) => state.setConfig);
  const updateTickData = useSimulationStore((state) => state.updateTickData);

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
        }
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };
  }, [setConnected, setRunning, setSpeed, setConfig, updateTickData]);

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
