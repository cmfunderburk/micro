/**
 * Timeline slider for replay mode.
 *
 * Allows seeking to any tick in the loaded replay.
 */

import { useReplayStore } from '@/store/replayStore';
import { Slider } from '@/components/ui/slider';

export function TimelineSlider() {
  const loadedRun = useReplayStore((state) => state.loadedRun);
  const currentTick = useReplayStore((state) => state.currentTick);
  const seekToTick = useReplayStore((state) => state.seekToTick);

  if (!loadedRun) return null;

  const maxTick = loadedRun.n_ticks - 1;

  return (
    <div className="flex items-center gap-3 w-full">
      <span className="text-xs text-zinc-400 font-mono w-10">
        {currentTick}
      </span>
      <Slider
        value={[currentTick]}
        onValueChange={(value) => seekToTick(value[0])}
        min={0}
        max={maxTick}
        step={1}
        className="flex-1"
      />
      <span className="text-xs text-zinc-400 font-mono w-10">
        {maxTick}
      </span>
    </div>
  );
}
