import { useRef, useCallback } from 'react';

interface Props {
  label: string;
  value: number;        // 0-1 (or 0-2 for width)
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  onChange: (v: number) => void;
}

export function MacroKnob({ label, value, min = 0, max = 1, step = 0.01, unit = '', onChange }: Props) {
  const dragRef = useRef<{ startY: number; startVal: number } | null>(null);

  const pct = (value - min) / (max - min);
  const angle = -135 + pct * 270;

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { startY: e.clientY, startVal: value };

    const onMove = (me: MouseEvent) => {
      if (!dragRef.current) return;
      const delta = (dragRef.current.startY - me.clientY) / 150;
      const newVal = Math.min(max, Math.max(min, dragRef.current.startVal + delta * (max - min)));
      onChange(Math.round(newVal / step) * step);
    };
    const onUp = () => {
      dragRef.current = null;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [value, min, max, step, onChange]);

  const displayVal = Number.isInteger(step) ? value.toFixed(0) : value.toFixed(2);

  return (
    <div className="flex flex-col items-center gap-1 select-none">
      <div
        className="w-12 h-12 rounded-full bg-slate-800 border-2 border-slate-700 cursor-ns-resize relative flex items-center justify-center hover:border-aurora-accent/60 transition-colors"
        onMouseDown={onMouseDown}
        role="slider"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={min}
        aria-valuemax={max}
      >
        {/* Arc indicator */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="18" fill="none" stroke="#1e293b" strokeWidth="3" strokeDasharray="113" strokeDashoffset="0" strokeLinecap="round" transform="rotate(135 24 24)" />
          <circle
            cx="24" cy="24" r="18"
            fill="none"
            stroke="#3b82f6"
            strokeWidth="3"
            strokeDasharray={`${pct * 113} 113`}
            strokeLinecap="round"
            transform="rotate(135 24 24)"
          />
        </svg>
        {/* Dot indicator */}
        <div
          className="absolute w-1.5 h-1.5 bg-white rounded-full"
          style={{
            top: '50%',
            left: '50%',
            transformOrigin: '0 0',
            transform: `rotate(${angle}deg) translateY(-14px) translate(-50%, -50%)`,
          }}
        />
      </div>
      <span className="text-xs text-white/60 font-medium">{label}</span>
      <span className="text-xs font-mono text-aurora-accent">{displayVal}{unit}</span>
    </div>
  );
}
