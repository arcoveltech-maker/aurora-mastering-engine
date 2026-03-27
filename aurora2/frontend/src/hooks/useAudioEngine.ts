import { useRef, useCallback, useEffect } from 'react';
import { useAudioStore } from '@/stores/audioStore';
import { extractWaveformPeaks } from '@/utils/audio';

export function useAudioEngine() {
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const bufferRef = useRef<AudioBuffer | null>(null);
  const startTimeRef = useRef<number>(0);
  const offsetRef = useRef<number>(0);
  const animFrameRef = useRef<number>(0);

  const {
    setIsPlaying,
    setPlaybackPosition,
    setDuration,
    setWaveformPeaks,
    setMeters,
    setMomentaryLUFS,
  } = useAudioStore();

  const getCtx = useCallback(() => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext();
    }
    return audioCtxRef.current;
  }, []);

  const loadBuffer = useCallback(async (file: File) => {
    const ctx = getCtx();
    const arrayBuffer = await file.arrayBuffer();
    const decoded = await ctx.decodeAudioData(arrayBuffer);
    bufferRef.current = decoded;
    setDuration(decoded.duration);
    setWaveformPeaks(extractWaveformPeaks(decoded, 1024));
    return decoded;
  }, [getCtx, setDuration, setWaveformPeaks]);

  const play = useCallback((offset = 0) => {
    if (!bufferRef.current) return;
    const ctx = getCtx();
    if (ctx.state === 'suspended') ctx.resume();

    sourceRef.current?.stop();
    const source = ctx.createBufferSource();
    source.buffer = bufferRef.current;
    source.connect(ctx.destination);
    source.start(0, offset);
    source.onended = () => setIsPlaying(false);

    sourceRef.current = source;
    startTimeRef.current = ctx.currentTime;
    offsetRef.current = offset;
    setIsPlaying(true);

    const tick = () => {
      if (!audioCtxRef.current) return;
      const pos = offsetRef.current + (audioCtxRef.current.currentTime - startTimeRef.current);
      setPlaybackPosition(Math.min(pos, bufferRef.current?.duration ?? 0));
      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);
  }, [getCtx, setIsPlaying, setPlaybackPosition]);

  const pause = useCallback(() => {
    if (!audioCtxRef.current || !sourceRef.current) return;
    offsetRef.current += audioCtxRef.current.currentTime - startTimeRef.current;
    sourceRef.current.stop();
    cancelAnimationFrame(animFrameRef.current);
    setIsPlaying(false);
  }, [setIsPlaying]);

  const stop = useCallback(() => {
    sourceRef.current?.stop();
    cancelAnimationFrame(animFrameRef.current);
    offsetRef.current = 0;
    setIsPlaying(false);
    setPlaybackPosition(0);
  }, [setIsPlaying, setPlaybackPosition]);

  useEffect(() => {
    return () => {
      cancelAnimationFrame(animFrameRef.current);
      audioCtxRef.current?.close();
    };
  }, []);

  return { loadBuffer, play, pause, stop };
}
