interface Props {
  targetLUFS: number;
  ceilingDBTP: number;
  onTargetChange: (v: number) => void;
  onCeilingChange: (v: number) => void;
}

const presets = [
  { label: 'Streaming', lufs: -14, ceil: -1 },
  { label: 'YouTube', lufs: -13, ceil: -1 },
  { label: 'CD', lufs: -9, ceil: -0.1 },
  { label: 'Broadcast', lufs: -23, ceil: -1 },
  { label: 'Apple Digital', lufs: -16, ceil: -1 },
];

export function LoudnessTarget({ targetLUFS, ceilingDBTP, onTargetChange, onCeilingChange }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1.5">
        {presets.map((p) => (
          <button
            key={p.label}
            onClick={() => { onTargetChange(p.lufs); onCeilingChange(p.ceil); }}
            className={`px-2 py-1 text-xs rounded border transition-colors ${
              targetLUFS === p.lufs && ceilingDBTP === p.ceil
                ? 'bg-aurora-accent border-aurora-accent text-white'
                : 'border-slate-700 text-white/50 hover:border-aurora-accent/50 hover:text-white/80'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-white/40">Target LUFS</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={-30} max={-6} step={0.5}
              value={targetLUFS}
              onChange={(e) => onTargetChange(Number(e.target.value))}
              className="flex-1 accent-aurora-accent"
            />
            <span className="text-xs font-mono text-aurora-accent w-12 text-right">
              {targetLUFS.toFixed(1)}
            </span>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-white/40">True Peak</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={-6} max={0} step={0.1}
              value={ceilingDBTP}
              onChange={(e) => onCeilingChange(Number(e.target.value))}
              className="flex-1 accent-aurora-accent"
            />
            <span className="text-xs font-mono text-aurora-accent w-12 text-right">
              {ceilingDBTP.toFixed(1)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
