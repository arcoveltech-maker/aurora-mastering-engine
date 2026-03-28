import { useRef, useEffect, useCallback } from 'react';

interface Props {
  analyserNode?: AnalyserNode | null;
  height?: number;
}

export function SpectrumAnalyzer({ analyserNode, height = 120 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyserNode) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyserNode.getByteFrequencyData(dataArray);

    const { width } = canvas;
    ctx.clearRect(0, 0, width, height);

    // Gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, '#3b82f6');
    grad.addColorStop(0.6, '#1d4ed8');
    grad.addColorStop(1, '#1e3a5f');

    const barWidth = width / bufferLength * 2.5;
    let x = 0;
    for (let i = 0; i < bufferLength; ++i) {
      const barH = ((dataArray[i] ?? 0) / 255) * height;
      ctx.fillStyle = grad;
      ctx.fillRect(x, height - barH, barWidth, barH);
      x += barWidth + 1;
    }

    rafRef.current = requestAnimationFrame(draw);
  }, [analyserNode, height]);

  useEffect(() => {
    if (analyserNode) {
      rafRef.current = requestAnimationFrame(draw);
    }
    return () => cancelAnimationFrame(rafRef.current);
  }, [analyserNode, draw]);

  // Static placeholder when no analyser
  useEffect(() => {
    if (analyserNode) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, height);
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, height);
    ctx.fillStyle = '#1e3a5f';
    for (let x = 0; x < canvas.width; x += 4) {
      const h = Math.random() * height * 0.3;
      ctx.fillRect(x, height - h, 2, h);
    }
  }, [analyserNode, height]);

  return (
    <canvas
      ref={canvasRef}
      width={512}
      height={height}
      className="w-full rounded bg-slate-950"
      style={{ height }}
    />
  );
}
