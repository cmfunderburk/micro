/**
 * Keyboard shortcuts hook.
 *
 * Provides global keyboard shortcuts for simulation control:
 * - Space: Play/pause
 * - Right arrow: Step forward
 * - Left arrow: Step backward (replay mode only)
 */

import { useEffect, useCallback } from 'react';
import type { Command } from './useSimulationSocket';
import { useReplayStore } from '@/store/replayStore';

interface UseKeyboardShortcutsOptions {
  sendCommand: (command: Command) => void;
  running: boolean;
  enabled?: boolean;
}

export function useKeyboardShortcuts({
  sendCommand,
  running,
  enabled = true,
}: UseKeyboardShortcutsOptions) {
  const replayMode = useReplayStore((state) => state.replayMode);
  const stepForward = useReplayStore((state) => state.stepForward);
  const stepBackward = useReplayStore((state) => state.stepBackward);
  const playing = useReplayStore((state) => state.playing);
  const setPlaying = useReplayStore((state) => state.setPlaying);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger if user is typing in an input
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement
      ) {
        return;
      }

      switch (event.code) {
        case 'Space':
          event.preventDefault();
          if (replayMode) {
            // Toggle replay playback
            setPlaying(!playing);
          } else {
            // Toggle simulation running
            if (running) {
              sendCommand({ command: 'stop' });
            } else {
              sendCommand({ command: 'start' });
            }
          }
          break;

        case 'ArrowRight':
          event.preventDefault();
          if (replayMode) {
            stepForward();
          } else if (!running) {
            sendCommand({ command: 'step' });
          }
          break;

        case 'ArrowLeft':
          event.preventDefault();
          if (replayMode) {
            stepBackward();
          }
          // No step backward for live simulation
          break;

        case 'KeyR':
          // Reset simulation (Ctrl/Cmd + R is browser refresh, so just R)
          if (!event.ctrlKey && !event.metaKey) {
            event.preventDefault();
            if (!replayMode) {
              sendCommand({ command: 'reset' });
            }
          }
          break;
      }
    },
    [enabled, replayMode, running, playing, sendCommand, stepForward, stepBackward, setPlaying]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);
}
