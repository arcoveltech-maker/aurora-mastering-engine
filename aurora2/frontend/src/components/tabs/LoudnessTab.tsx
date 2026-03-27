import { useSessionStore } from '@/stores/sessionStore';
import { useSessionPersistence } from '@/hooks/useSessionPersistence';
import { useAuth } from '@/contexts/AuthContext';
import { LoudnessTarget } from '@/components/controls/LoudnessTarget';
import { LUFSMeter } from '@/components/visualizers/LUFSMeter';
import { TruePeakMeter } from '@/components/visualizers/TruePeakMeter';

export function LoudnessTab() {
  const { manifest } = useSessionStore();
  const { sessionToken } = useAuth();
  const { updateMacro } = useSessionPersistence(sessionToken);

  const loudness = manifest?.loudness ?? {};
  const targetLUFS = loudness.target_lufs ?? -14;
  const ceilingDBTP = loudness.ceiling_dbtp ?? -1;

  return (
    <div className="flex flex-col gap-4 p-4">
      <LoudnessTarget
        targetLUFS={targetLUFS}
        ceilingDBTP={ceilingDBTP}
        onTargetChange={(v) => updateMacro('target_lufs', v)}
        onCeilingChange={(v) => updateMacro('ceiling_dbtp', v)}
      />
      <div className="grid grid-cols-2 gap-3">
        <LUFSMeter />
        <TruePeakMeter />
      </div>
    </div>
  );
}
