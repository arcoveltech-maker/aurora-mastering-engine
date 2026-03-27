import { useAudioStore } from '@/stores/audioStore';
import { formatLUFS, formatDBTP } from '@/utils/audio';
import { SpectrumAnalyzer } from '@/components/visualizers/SpectrumAnalyzer';

function Metric({ label, pre, post, unit = '' }: { label: string; pre: string; post: string | null; unit?: string }) {
  return (
    <div className="flex flex-col gap-1 p-3 bg-slate-900 rounded-lg">
      <span className="text-xs text-white/40 uppercase tracking-wider">{label}</span>
      <div className="flex items-end justify-between gap-2">
        <div className="flex flex-col">
          <span className="text-xs text-white/30">Before</span>
          <span className="text-lg font-mono font-semibold text-white/70">{pre}{unit}</span>
        </div>
        {post !== null && (
          <>
            <span className="text-white/20 pb-1">→</span>
            <div className="flex flex-col items-end">
              <span className="text-xs text-aurora-accent/70">After</span>
              <span className="text-lg font-mono font-semibold text-aurora-accent">{post}{unit}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export function AnalyzeTab() {
  const { preAnalysis, postAnalysis } = useAudioStore();

  if (!preAnalysis) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-white/30 gap-2">
        <span className="text-4xl">📊</span>
        <p className="text-sm">Upload a track to see analysis</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <SpectrumAnalyzer height={100} />

      <div className="grid grid-cols-2 gap-2">
        <Metric
          label="Integrated LUFS"
          pre={formatLUFS(preAnalysis.integratedLUFS)}
          post={postAnalysis ? formatLUFS(postAnalysis.integratedLUFS) : null}
          unit=" LUFS"
        />
        <Metric
          label="True Peak"
          pre={formatDBTP(preAnalysis.truePeakDBTP)}
          post={postAnalysis ? formatDBTP(postAnalysis.truePeakDBTP) : null}
          unit=" dBTP"
        />
        <Metric
          label="Dynamic Range"
          pre={preAnalysis.dynamicRange.toFixed(1)}
          post={postAnalysis ? postAnalysis.dynamicRange.toFixed(1) : null}
          unit=" dB"
        />
        <Metric
          label="Spectral Centroid"
          pre={(preAnalysis.spectralCentroid / 1000).toFixed(1)}
          post={null}
          unit=" kHz"
        />
      </div>

      {(preAnalysis.bpm || preAnalysis.key) && (
        <div className="grid grid-cols-2 gap-2">
          {preAnalysis.bpm && (
            <Metric label="BPM" pre={preAnalysis.bpm.toFixed(0)} post={null} />
          )}
          {preAnalysis.key && (
            <Metric label="Key" pre={preAnalysis.key} post={null} />
          )}
        </div>
      )}
    </div>
  );
}
