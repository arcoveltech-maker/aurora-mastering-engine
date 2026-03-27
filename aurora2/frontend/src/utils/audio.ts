// Web Audio API utilities for preview playback and real-time metering

export function decodeAudioFile(file: File): Promise<AudioBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      const arrayBuffer = e.target?.result as ArrayBuffer;
      const ctx = new AudioContext();
      try {
        const decoded = await ctx.decodeAudioData(arrayBuffer);
        resolve(decoded);
      } catch (err) {
        reject(err);
      } finally {
        ctx.close();
      }
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(file);
  });
}

export function extractWaveformPeaks(buffer: AudioBuffer, numPeaks = 1024): Float32Array {
  const channelData = buffer.getChannelData(0);
  const blockSize = Math.floor(channelData.length / numPeaks);
  const peaks = new Float32Array(numPeaks);

  for (let i = 0; i < numPeaks; ++i) {
    let max = 0;
    const start = i * blockSize;
    const end = Math.min(start + blockSize, channelData.length);
    for (let j = start; j < end; ++j) {
      const abs = Math.abs(channelData[j]!);
      if (abs > max) max = abs;
    }
    peaks[i] = max;
  }
  return peaks;
}

export function interleaveChannels(buffer: AudioBuffer): Float32Array {
  const { numberOfChannels, length } = buffer;
  const interleaved = new Float32Array(length * numberOfChannels);
  for (let i = 0; i < length; ++i) {
    for (let c = 0; c < numberOfChannels; ++c) {
      interleaved[i * numberOfChannels + c] = buffer.getChannelData(c)[i]!;
    }
  }
  return interleaved;
}

export function dbToLinear(db: number): number {
  return Math.pow(10, db / 20);
}

export function linearToDb(linear: number): number {
  return 20 * Math.log10(Math.max(linear, 1e-10));
}

export function formatLUFS(lufs: number): string {
  if (lufs <= -70) return '-∞';
  return lufs.toFixed(1);
}

export function formatDBTP(dbtp: number): string {
  if (dbtp <= -100) return '-∞';
  return (dbtp >= 0 ? '+' : '') + dbtp.toFixed(1);
}
