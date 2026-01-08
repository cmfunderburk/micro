/**
 * Configuration modal for simulation parameters.
 */

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { useSimulationStore } from '@/store';

interface ConfigModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface FormConfig {
  n_agents: number;
  grid_size: number;
  perception_radius: number;
  discount_factor: number;
  seed: number | null;
  bargaining_protocol: 'nash' | 'rubinstein';
  matching_protocol: 'opportunistic' | 'stable_roommates';
  use_beliefs: boolean;
}

export function ConfigModal({ open, onOpenChange }: ConfigModalProps) {
  const config = useSimulationStore((state) => state.config);
  const setConfig = useSimulationStore((state) => state.setConfig);
  const reset = useSimulationStore((state) => state.reset);

  const [formConfig, setFormConfig] = useState<FormConfig>({
    n_agents: 10,
    grid_size: 15,
    perception_radius: 7,
    discount_factor: 0.95,
    seed: null,
    bargaining_protocol: 'nash',
    matching_protocol: 'opportunistic',
    use_beliefs: false,
  });

  const [loading, setLoading] = useState(false);

  // Sync form with current config when modal opens
  useEffect(() => {
    if (open && config) {
      setFormConfig({
        n_agents: config.n_agents,
        grid_size: config.grid_size,
        perception_radius: config.perception_radius,
        discount_factor: config.discount_factor,
        seed: config.seed,
        bargaining_protocol: config.bargaining_protocol as 'nash' | 'rubinstein',
        matching_protocol: config.matching_protocol as 'opportunistic' | 'stable_roommates',
        use_beliefs: config.use_beliefs,
      });
    }
  }, [open, config]);

  const handleApply = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formConfig),
      });

      if (response.ok) {
        const newConfig = await response.json();
        setConfig(newConfig);
        reset();
        onOpenChange(false);
      }
    } catch (error) {
      console.error('Failed to apply config:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-zinc-900 border-zinc-700">
        <DialogHeader>
          <DialogTitle className="text-zinc-100">Simulation Configuration</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Number of Agents */}
          <div>
            <label className="text-sm text-zinc-400 block mb-1">
              Number of Agents: {formConfig.n_agents}
            </label>
            <Slider
              value={[formConfig.n_agents]}
              onValueChange={([v]) => setFormConfig({ ...formConfig, n_agents: v })}
              min={2}
              max={50}
              step={1}
            />
          </div>

          {/* Grid Size */}
          <div>
            <label className="text-sm text-zinc-400 block mb-1">
              Grid Size: {formConfig.grid_size}
            </label>
            <Slider
              value={[formConfig.grid_size]}
              onValueChange={([v]) => setFormConfig({ ...formConfig, grid_size: v })}
              min={5}
              max={50}
              step={1}
            />
          </div>

          {/* Perception Radius */}
          <div>
            <label className="text-sm text-zinc-400 block mb-1">
              Perception Radius: {formConfig.perception_radius.toFixed(1)}
            </label>
            <Slider
              value={[formConfig.perception_radius]}
              onValueChange={([v]) => setFormConfig({ ...formConfig, perception_radius: v })}
              min={1}
              max={20}
              step={0.5}
            />
          </div>

          {/* Discount Factor */}
          <div>
            <label className="text-sm text-zinc-400 block mb-1">
              Discount Factor: {formConfig.discount_factor.toFixed(2)}
            </label>
            <Slider
              value={[formConfig.discount_factor]}
              onValueChange={([v]) => setFormConfig({ ...formConfig, discount_factor: v })}
              min={0.5}
              max={1}
              step={0.01}
            />
          </div>

          {/* Bargaining Protocol */}
          <div>
            <label className="text-sm text-zinc-400 block mb-2">Bargaining Protocol</label>
            <div className="flex gap-2">
              <Button
                variant={formConfig.bargaining_protocol === 'nash' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFormConfig({ ...formConfig, bargaining_protocol: 'nash' })}
                className="flex-1"
              >
                Nash
              </Button>
              <Button
                variant={formConfig.bargaining_protocol === 'rubinstein' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFormConfig({ ...formConfig, bargaining_protocol: 'rubinstein' })}
                className="flex-1"
              >
                Rubinstein
              </Button>
            </div>
          </div>

          {/* Matching Protocol */}
          <div>
            <label className="text-sm text-zinc-400 block mb-2">Matching Protocol</label>
            <div className="flex gap-2">
              <Button
                variant={formConfig.matching_protocol === 'opportunistic' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFormConfig({ ...formConfig, matching_protocol: 'opportunistic' })}
                className="flex-1"
              >
                Opportunistic
              </Button>
              <Button
                variant={formConfig.matching_protocol === 'stable_roommates' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFormConfig({ ...formConfig, matching_protocol: 'stable_roommates' })}
                className="flex-1"
              >
                Stable
              </Button>
            </div>
          </div>

          {/* Seed */}
          <div>
            <label className="text-sm text-zinc-400 block mb-1">
              Random Seed (optional)
            </label>
            <input
              type="number"
              value={formConfig.seed ?? ''}
              onChange={(e) =>
                setFormConfig({
                  ...formConfig,
                  seed: e.target.value ? parseInt(e.target.value, 10) : null,
                })
              }
              placeholder="Leave empty for random"
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleApply} disabled={loading}>
            {loading ? 'Applying...' : 'Apply & Reset'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
