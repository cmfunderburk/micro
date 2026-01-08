/**
 * Configuration modal for simulation parameters.
 */

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { useSimulationStore } from '@/store';
import type { Command } from '@/hooks/useSimulationSocket';

interface ConfigModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sendCommand: (cmd: Command) => void;
}

interface FormConfig {
  n_agents: number;
  grid_size: number;
  perception_radius: number;
  discount_factor: number;
  seed: number | null;
  bargaining_protocol: 'nash' | 'rubinstein' | 'tioli' | 'asymmetric_nash';
  matching_protocol: 'opportunistic' | 'stable_roommates';
  bargaining_power_distribution: 'uniform' | 'gaussian' | 'bimodal';
  use_beliefs: boolean;
}

// Protocol display configuration with labels and tooltips
const BARGAINING_PROTOCOLS = [
  {
    value: 'nash' as const,
    label: 'Nash (Symmetric)',
    tooltip: 'Equal split of gains. Neither agent has bargaining advantage.',
  },
  {
    value: 'rubinstein' as const,
    label: 'Nash (Patience)',
    tooltip: 'Patient agents (high discount factor) get larger share. Based on Rubinstein/BRW.',
  },
  {
    value: 'asymmetric_nash' as const,
    label: 'Nash (Power)',
    tooltip: 'Agents with higher bargaining_power attribute get larger share.',
  },
  {
    value: 'tioli' as const,
    label: 'Take-It-Or-Leave-It',
    tooltip: 'Proposer extracts all gains. Responder gets exactly their outside option.',
  },
] as const;

const POWER_DISTRIBUTIONS = [
  { value: 'uniform' as const, label: 'Uniform [0.5, 1.5]' },
  { value: 'gaussian' as const, label: 'Gaussian (mean=1, std=0.3)' },
  { value: 'bimodal' as const, label: 'Bimodal (0.5 and 1.5)' },
] as const;

export function ConfigModal({ open, onOpenChange, sendCommand }: ConfigModalProps) {
  const config = useSimulationStore((state) => state.config);

  const [formConfig, setFormConfig] = useState<FormConfig>({
    n_agents: 10,
    grid_size: 15,
    perception_radius: 7,
    discount_factor: 0.95,
    seed: null,
    bargaining_protocol: 'nash',
    matching_protocol: 'opportunistic',
    bargaining_power_distribution: 'uniform',
    use_beliefs: false,
  });

  // Sync form with current config when modal opens
  useEffect(() => {
    if (open && config) {
      setFormConfig({
        n_agents: config.n_agents,
        grid_size: config.grid_size,
        perception_radius: config.perception_radius,
        discount_factor: config.discount_factor,
        seed: config.seed,
        bargaining_protocol: config.bargaining_protocol as FormConfig['bargaining_protocol'],
        matching_protocol: config.matching_protocol as 'opportunistic' | 'stable_roommates',
        bargaining_power_distribution: (config.bargaining_power_distribution || 'uniform') as FormConfig['bargaining_power_distribution'],
        use_beliefs: config.use_beliefs,
      });
    }
  }, [open, config]);

  const handleApply = () => {
    // Use WebSocket command for proper broadcast to all clients
    sendCommand({ command: 'config', config: formConfig });
    onOpenChange(false);
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
            <div className="grid grid-cols-2 gap-2">
              {BARGAINING_PROTOCOLS.map((protocol) => (
                <Button
                  key={protocol.value}
                  variant={formConfig.bargaining_protocol === protocol.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFormConfig({ ...formConfig, bargaining_protocol: protocol.value })}
                  className="text-xs"
                  title={protocol.tooltip}
                >
                  {protocol.label}
                </Button>
              ))}
            </div>
            <p className="text-xs text-zinc-500 mt-1">
              {BARGAINING_PROTOCOLS.find(p => p.value === formConfig.bargaining_protocol)?.tooltip}
            </p>
          </div>

          {/* Bargaining Power Distribution (only for asymmetric_nash) */}
          {formConfig.bargaining_protocol === 'asymmetric_nash' && (
            <div>
              <label className="text-sm text-zinc-400 block mb-2">Bargaining Power Distribution</label>
              <div className="flex gap-2">
                {POWER_DISTRIBUTIONS.map((dist) => (
                  <Button
                    key={dist.value}
                    variant={formConfig.bargaining_power_distribution === dist.value ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFormConfig({ ...formConfig, bargaining_power_distribution: dist.value })}
                    className="flex-1 text-xs"
                  >
                    {dist.label.split(' ')[0]}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-zinc-500 mt-1">
                How bargaining power is distributed across agents
              </p>
            </div>
          )}

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

          {/* Use Beliefs */}
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={formConfig.use_beliefs}
                  onChange={(e) => setFormConfig({ ...formConfig, use_beliefs: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-8 h-4 bg-zinc-700 rounded-full peer-checked:bg-green-600 transition-colors" />
                <div className="absolute left-0.5 top-0.5 w-3 h-3 bg-zinc-300 rounded-full transition-transform peer-checked:translate-x-4 peer-checked:bg-white" />
              </div>
              <div>
                <span className="text-sm text-zinc-400">Enable Belief System</span>
                <p className="text-xs text-zinc-500">Agents learn about others through observation</p>
              </div>
            </label>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleApply}>
            Apply & Reset
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
