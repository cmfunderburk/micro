/**
 * Toggle controls for grid overlays.
 */

import { useSimulationStore } from '@/store';

export function OverlayToggles() {
  const overlays = useSimulationStore((state) => state.overlays);
  const toggleOverlay = useSimulationStore((state) => state.toggleOverlay);

  const overlayOptions = [
    { key: 'trails' as const, label: 'Trails', description: 'Show movement history' },
    { key: 'perceptionRadius' as const, label: 'Perception', description: 'Show view range' },
    { key: 'tradeConnections' as const, label: 'Connections', description: 'Show trade links' },
  ];

  return (
    <div className="space-y-2">
      {overlayOptions.map(({ key, label, description }) => (
        <label
          key={key}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="relative">
            <input
              type="checkbox"
              checked={overlays[key]}
              onChange={() => toggleOverlay(key)}
              className="sr-only peer"
            />
            <div className="w-8 h-4 bg-zinc-700 rounded-full peer-checked:bg-green-600 transition-colors" />
            <div className="absolute left-0.5 top-0.5 w-3 h-3 bg-zinc-300 rounded-full transition-transform peer-checked:translate-x-4 peer-checked:bg-white" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-medium text-zinc-200">{label}</div>
            <div className="text-xs text-zinc-500">{description}</div>
          </div>
        </label>
      ))}
    </div>
  );
}
