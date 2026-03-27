import { useState } from 'react';
import { Upload } from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';

type MatchMode = 'tonal' | 'dynamic' | 'full';

export function ReferenceTab() {
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [matchMode, setMatchMode] = useState<MatchMode>('full');
  const [matchStrength, setMatchStrength] = useState(0.5);
  const { addToast } = useToast();

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('audio/')) {
      setReferenceFile(file);
      addToast({ type: 'success', message: `Reference loaded: ${file.name}` });
    }
  };

  return (
    <div className="flex flex-col gap-4 p-4">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-slate-700 rounded-lg p-6 flex flex-col items-center gap-2 hover:border-aurora-accent/50 transition-colors cursor-pointer"
        onClick={() => document.getElementById('ref-input')?.click()}
      >
        <input
          id="ref-input"
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) { setReferenceFile(f); addToast({ type: 'success', message: `Reference: ${f.name}` }); }
          }}
        />
        <Upload className="w-8 h-8 text-white/30" />
        <span className="text-sm text-white/40">
          {referenceFile ? referenceFile.name : 'Drop a reference track here'}
        </span>
      </div>

      <div className="flex gap-2">
        {(['tonal', 'dynamic', 'full'] as MatchMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => setMatchMode(mode)}
            className={`flex-1 py-1.5 text-xs rounded capitalize transition-colors ${
              matchMode === mode
                ? 'bg-aurora-accent text-white'
                : 'bg-slate-800 text-white/50 hover:text-white'
            }`}
          >
            {mode}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-xs text-white/40">
          <span>Match Strength</span>
          <span className="text-aurora-accent">{(matchStrength * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range"
          min={0} max={1} step={0.01}
          value={matchStrength}
          onChange={(e) => setMatchStrength(Number(e.target.value))}
          className="accent-aurora-accent"
        />
      </div>
    </div>
  );
}
