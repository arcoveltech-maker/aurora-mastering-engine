import { useRef, useEffect } from 'react';
import { useAudioStore } from '@/stores/audioStore';

interface Props {
  height?: number;
}

export function WaveformDisplay({ height = 80 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { waveformPeaks, playbackPosition, duration } = useAudioStore();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !waveformPeaks) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width } = canvas;
    ctx.clearRect(0, 0, width, height);

    const progress = duration > 0 ? playbackPosition / duration : 0;
    const playedPixels = Math.floor(progress * width);

    for (let x = 0; x < width; ++x) {
      const idx = Math.floor((x / width) * waveformPeaks.length);
      const peak = waveformPeaks[idx] ?? 0;
      const barH = peak * height * 0.9;
      const y = (height - barH) / 2;

      ctx.fillStyle = x < playedPixels ? '#3b82f6' : '#1e3a5f';
      ctx.fillRect(x, y, 1, barH);
    }
  }, [waveformPeaks, playbackPosition, duration, height]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={height}
      className="w-full rounded"
      style={{ height }}
    />
  );
}
