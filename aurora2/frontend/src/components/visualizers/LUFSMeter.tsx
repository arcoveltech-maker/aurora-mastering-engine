import { useAudioStore } from '@/stores/audioStore';
import { formatLUFS } from '@/utils/audio';

export function LUFSMeter() {
  const { momentaryLUFS, shortTermLUFS, integratedLUFS } = useAudioStore();

  const toBar = (lufs: number) => Math.max(0, Math.min(100, ((lufs + 70) / 60) * 100));

  return (
    <div className="flex flex-col gap-2 p-3 bg-slate-900 rounded-lg">
      <div className="text-xs text-white/40 uppercase tracking-wider font-medium">LUFS</div>
      {[
        { label: 'M', value: momentaryLUFS, color: 'bg-blue-500' },
        { label: 'S', value: shortTermLUFS, color: 'bg-indigo-500' },
        { label: 'I', value: integratedLUFS, color: 'bg-purple-500' },
      ].map(({ label, value, color }) => (
        <div key={label} className="flex items-center gap-2">
          <span className="text-xs text-white/50 w-3">{label}</span>
          <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full ${color} transition-all duration-100`}
              style={{ width: `${toBar(value)}%` }}
            />
          </div>
          <span className="text-xs font-mono text-white/80 w-12 text-right">
            {formatLUFS(value)}
          </span>
        </div>
      ))}
    </div>
  );
}
