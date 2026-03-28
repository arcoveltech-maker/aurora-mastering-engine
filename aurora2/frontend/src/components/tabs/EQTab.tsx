import { useSessionStore } from '@/stores/sessionStore';
import { useSessionPersistence } from '@/hooks/useSessionPersistence';
import { useAuth } from '@/contexts/AuthContext';
import { MacroKnob } from '@/components/controls/MacroKnob';

export function EQTab() {
  const { manifest } = useSessionStore();
  const { sessionToken } = useAuth();
  const { updateMacro } = useSessionPersistence(sessionToken);
  const macros = manifest?.macros ?? {};

  return (
    <div className="flex flex-col gap-6 p-4">
      <div>
        <h3 className="text-sm font-medium text-white/60 mb-4 uppercase tracking-wider">Tonal Balance</h3>
        <div className="flex gap-8 justify-center">
          <MacroKnob
            label="Warmth"
            value={Number(macros['warmth'] ?? 0)}
            onChange={(v) => updateMacro('warmth', v)}
          />
          <MacroKnob
            label="Brightness"
            value={Number(macros['brightness'] ?? 0)}
            onChange={(v) => updateMacro('brightness', v)}
          />
          <MacroKnob
            label="Air"
            value={Number(macros['air'] ?? 0)}
            onChange={(v) => updateMacro('air', v)}
          />
          <MacroKnob
            label="Depth"
            value={Number(macros['depth'] ?? 0)}
            onChange={(v) => updateMacro('depth', v)}
          />
          <MacroKnob
            label="Clarity"
            value={Number(macros['clarity'] ?? 0)}
            onChange={(v) => updateMacro('clarity', v)}
          />
        </div>
      </div>
    </div>
  );
}
