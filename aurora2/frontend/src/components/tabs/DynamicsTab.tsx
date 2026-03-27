import { useSessionStore } from '@/stores/sessionStore';
import { useSessionPersistence } from '@/hooks/useSessionPersistence';
import { useAuth } from '@/contexts/AuthContext';
import { MacroKnob } from '@/components/controls/MacroKnob';

export function DynamicsTab() {
  const { manifest } = useSessionStore();
  const { sessionToken } = useAuth();
  const { updateMacro } = useSessionPersistence(sessionToken);
  const macros = manifest?.macros ?? {};

  return (
    <div className="flex flex-col gap-6 p-4">
      <div>
        <h3 className="text-sm font-medium text-white/60 mb-4 uppercase tracking-wider">Dynamics</h3>
        <div className="flex gap-8 justify-center">
          <MacroKnob
            label="Punch"
            value={Number(macros['punch'] ?? 0)}
            onChange={(v) => updateMacro('punch', v)}
          />
          <MacroKnob
            label="Glue"
            value={Number(macros['glue'] ?? 0)}
            onChange={(v) => updateMacro('glue', v)}
          />
          <MacroKnob
            label="Width"
            value={Number(macros['width'] ?? 1)}
            min={0} max={2} step={0.01}
            onChange={(v) => updateMacro('width', v)}
          />
        </div>
      </div>
    </div>
  );
}
