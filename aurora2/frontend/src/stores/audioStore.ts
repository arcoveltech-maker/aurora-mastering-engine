import { create } from 'zustand';

interface Meters {
  left: number;
  right: number;
}

interface AudioStore {
  // Playback
  isPlaying: boolean;
  playbackPosition: number;
  duration: number;
  // Metering
  meters: Meters;
  momentaryLUFS: number;
  shortTermLUFS: number;
  integratedLUFS: number;
  truePeakDBTP: number;
  waveformPeaks: Float32Array | null;
  // Pre-mastering analysis (from upload)
  preAnalysis: {
    integratedLUFS: number;
    truePeakDBTP: number;
    dynamicRange: number;
    spectralCentroid: number;
    bpm: number | null;
    key: string | null;
  } | null;
  // Post-mastering analysis
  postAnalysis: {
    integratedLUFS: number;
    truePeakDBTP: number;
    dynamicRange: number;
  } | null;
  // Actions
  setIsPlaying: (v: boolean) => void;
  setPlaybackPosition: (v: number) => void;
  setDuration: (v: number) => void;
  setMeters: (m: Meters) => void;
  setMomentaryLUFS: (v: number) => void;
  setShortTermLUFS: (v: number) => void;
  setIntegratedLUFS: (v: number) => void;
  setTruePeakDBTP: (v: number) => void;
  setWaveformPeaks: (peaks: Float32Array) => void;
  setPreAnalysis: (a: AudioStore['preAnalysis']) => void;
  setPostAnalysis: (a: AudioStore['postAnalysis']) => void;
}

export const useAudioStore = create<AudioStore>((set) => ({
  isPlaying: false,
  playbackPosition: 0,
  duration: 0,
  meters: { left: -70, right: -70 },
  momentaryLUFS: -70,
  shortTermLUFS: -70,
  integratedLUFS: -70,
  truePeakDBTP: -100,
  waveformPeaks: null,
  preAnalysis: null,
  postAnalysis: null,
  setIsPlaying: (v) => set({ isPlaying: v }),
  setPlaybackPosition: (v) => set({ playbackPosition: v }),
  setDuration: (v) => set({ duration: v }),
  setMeters: (m) => set({ meters: m }),
  setMomentaryLUFS: (v) => set({ momentaryLUFS: v }),
  setShortTermLUFS: (v) => set({ shortTermLUFS: v }),
  setIntegratedLUFS: (v) => set({ integratedLUFS: v }),
  setTruePeakDBTP: (v) => set({ truePeakDBTP: v }),
  setWaveformPeaks: (peaks) => set({ waveformPeaks: peaks }),
  setPreAnalysis: (a) => set({ preAnalysis: a }),
  setPostAnalysis: (a) => set({ postAnalysis: a }),
}));
