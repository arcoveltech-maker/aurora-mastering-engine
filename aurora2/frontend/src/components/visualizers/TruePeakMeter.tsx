import { useAudioStore } from '@/stores/audioStore';
import { formatDBTP } from '@/utils/audio';

export function TruePeakMeter() {
  const { truePeakDBTP } = useAudioStore();
  const isRed = truePeakDBTP > -1.0;
  const pct = Math.max(0, Math.min(100, ((truePeakDBTP + 30) / 30) * 100));

  return (
    <div className="flex flex-col gap-2 p-3 bg-slate-900 rounded-lg">
      <div className="flex items-center justify-between">
        <span className="text-xs text-white/40 uppercase tracking-wider font-medium">True Peak</span>
        <span className={`text-xs font-mono font-bold ${isRed ? 'text-red-400' : 'text-green-400'}`}>
          {formatDBTP(truePeakDBTP)} dBTP
        </span>
      </div>
      <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-75 ${isRed ? 'bg-red-500' : 'bg-green-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-white/25 font-mono">
        <span>-30</span><span>-20</span><span>-10</span><span>-1</span><span>0</span>
      </div>
    </div>
  );
}
