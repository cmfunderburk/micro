/**
 * Replay playback controls.
 *
 * Play/pause, step forward/backward, and speed controls for replay mode.
 */

import { useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { useReplayStore } from '@/store/replayStore';
import { Play, Pause, SkipForward, SkipBack, ChevronFirst, ChevronLast } from 'lucide-react';

export function ReplayControls() {
  const loadedRun = useReplayStore((state) => state.loadedRun);
  const currentTick = useReplayStore((state) => state.currentTick);
  const playing = useReplayStore((state) => state.playing);
  const playbackSpeed = useReplayStore((state) => state.playbackSpeed);
  const setPlaying = useReplayStore((state) => state.setPlaying);
  const setPlaybackSpeed = useReplayStore((state) => state.setPlaybackSpeed);
  const stepForward = useReplayStore((state) => state.stepForward);
  const stepBackward = useReplayStore((state) => state.stepBackward);
  const seekToTick = useReplayStore((state) => state.seekToTick);

  const playbackRef = useRef<number | null>(null);

  // Handle playback
  useEffect(() => {
    if (!playing || !loadedRun) {
      if (playbackRef.current) {
        clearInterval(playbackRef.current);
        playbackRef.current = null;
      }
      return;
    }

    const intervalMs = 1000 / playbackSpeed;
    playbackRef.current = window.setInterval(() => {
      const { currentTick, loadedRun, setPlaying } = useReplayStore.getState();
      if (!loadedRun) return;

      if (currentTick >= loadedRun.n_ticks - 1) {
        setPlaying(false);
      } else {
        stepForward();
      }
    }, intervalMs);

    return () => {
      if (playbackRef.current) {
        clearInterval(playbackRef.current);
        playbackRef.current = null;
      }
    };
  }, [playing, playbackSpeed, loadedRun, stepForward]);

  if (!loadedRun) return null;

  const maxTick = loadedRun.n_ticks - 1;
  const atStart = currentTick === 0;
  const atEnd = currentTick === maxTick;

  return (
    <div className="flex items-center gap-2">
      {/* Jump to start */}
      <Button
        onClick={() => seekToTick(0)}
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={atStart}
        title="Jump to start"
      >
        <ChevronFirst className="h-4 w-4" />
      </Button>

      {/* Step backward */}
      <Button
        onClick={stepBackward}
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={atStart}
        title="Step backward"
      >
        <SkipBack className="h-4 w-4" />
      </Button>

      {/* Play/Pause */}
      {playing ? (
        <Button
          onClick={() => setPlaying(false)}
          variant="outline"
          size="icon"
          className="h-8 w-8"
          title="Pause"
        >
          <Pause className="h-4 w-4" />
        </Button>
      ) : (
        <Button
          onClick={() => setPlaying(true)}
          variant="outline"
          size="icon"
          className="h-8 w-8"
          disabled={atEnd}
          title="Play"
        >
          <Play className="h-4 w-4" />
        </Button>
      )}

      {/* Step forward */}
      <Button
        onClick={stepForward}
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={atEnd}
        title="Step forward"
      >
        <SkipForward className="h-4 w-4" />
      </Button>

      {/* Jump to end */}
      <Button
        onClick={() => seekToTick(maxTick)}
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={atEnd}
        title="Jump to end"
      >
        <ChevronLast className="h-4 w-4" />
      </Button>

      {/* Speed control */}
      <div className="flex items-center gap-2 ml-2">
        <span className="text-xs text-zinc-400">Speed:</span>
        <Slider
          value={[playbackSpeed]}
          onValueChange={(value) => setPlaybackSpeed(value[0])}
          min={0.5}
          max={10}
          step={0.5}
          className="w-20"
        />
        <span className="text-xs w-10 font-mono">{playbackSpeed.toFixed(1)}x</span>
      </div>
    </div>
  );
}
