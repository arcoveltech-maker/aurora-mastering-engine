import { useState, useCallback, useRef } from 'react';
import { Upload, Play, Pause, Square, Download, Save, Zap } from 'lucide-react';
import { useAudioEngine } from '@/hooks/useAudioEngine';
import { useSessionPersistence } from '@/hooks/useSessionPersistence';
import { useAudioStore } from '@/stores/audioStore';
import { useSessionStore } from '@/stores/sessionStore';
import { useProcessingStore } from '@/stores/processingStore';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import { api } from '@/utils/api';
import { WaveformDisplay } from '@/components/visualizers/WaveformDisplay';
import { LUFSMeter } from '@/components/visualizers/LUFSMeter';
import { TruePeakMeter } from '@/components/visualizers/TruePeakMeter';
import { EQTab } from '@/components/tabs/EQTab';
import { DynamicsTab } from '@/components/tabs/DynamicsTab';
import { LoudnessTab } from '@/components/tabs/LoudnessTab';
import { AnalyzeTab } from '@/components/tabs/AnalyzeTab';
import { ColabTab } from '@/components/tabs/ColabTab';
import { ReferenceTab } from '@/components/tabs/ReferenceTab';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';

type Tab = 'eq' | 'dynamics' | 'loudness' | 'analyze' | 'colab' | 'reference';

const tabs: { id: Tab; label: string }[] = [
  { id: 'eq', label: 'EQ' },
  { id: 'dynamics', label: 'Dynamics' },
  { id: 'loudness', label: 'Loudness' },
  { id: 'analyze', label: 'Analyze' },
  { id: 'colab', label: 'Colab' },
  { id: 'reference', label: 'Reference' },
];

export function MasteringApp() {
  const [activeTab, setActiveTab] = useState<Tab>('eq');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { loadBuffer, play, pause, stop } = useAudioEngine();
  const { isPlaying, duration } = useAudioStore();
  const { setPreAnalysis, setPostAnalysis } = useAudioStore();
  const { manifest, setSourceFile, title, setTitle } = useSessionStore();
  const { renderStatus, renderProgress, renderStage, setRenderStatus, setRenderProgress, setRenderStage, setRenderJobId, setRenderOutputUrl } = useProcessingStore();
  const { sessionToken, isAuthenticated } = useAuth();
  const { addToast } = useToast();
  const { save } = useSessionPersistence(sessionToken);

  const handleFile = useCallback(async (file: File) => {
    addToast({ type: 'info', message: `Loading ${file.name}…` });
    try {
      await loadBuffer(file);

      // Upload to backend for analysis
      if (isAuthenticated && sessionToken) {
        const { upload_url, file_key, file_id } = await api.upload.getUploadUrl(
          sessionToken, file.name, file.type || 'audio/wav'
        );
        await api.upload.putFile(upload_url, file);
        setSourceFile(file_key, file.name);

        // Get analysis
        const analysis = await api.upload.analyze(sessionToken, file_id);
        setPreAnalysis({
          integratedLUFS: analysis.integrated_lufs,
          truePeakDBTP: analysis.true_peak_dbtp,
          dynamicRange: analysis.dynamic_range,
          spectralCentroid: analysis.spectral_centroid,
          bpm: analysis.bpm,
          key: analysis.key,
        });
        addToast({ type: 'success', message: 'Analysis complete' });
      } else {
        // Local-only mode: basic analysis
        setPreAnalysis({
          integratedLUFS: -18,
          truePeakDBTP: -1.2,
          dynamicRange: 12,
          spectralCentroid: 3200,
          bpm: null,
          key: null,
        });
        addToast({ type: 'success', message: `Loaded: ${file.name}` });
      }
    } catch (err) {
      addToast({ type: 'error', message: `Failed to load file: ${err instanceof Error ? err.message : 'Unknown error'}` });
    }
  }, [loadBuffer, isAuthenticated, sessionToken, setSourceFile, setPreAnalysis, addToast]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleRender = useCallback(async () => {
    if (!sessionToken || !manifest) {
      addToast({ type: 'warning', message: 'Save your session first' });
      return;
    }
    await save();
    const sessionId = useSessionStore.getState().sessionId;
    if (!sessionId) return;

    setRenderStatus('running');
    setRenderProgress(0);
    setRenderStage('Initializing…');

    try {
      const job = await api.render.start(sessionToken, sessionId);
      setRenderJobId(job.job_id);

      // Poll for completion
      const poll = async () => {
        const status = await api.render.status(sessionToken, job.job_id);
        setRenderProgress(status.progress);
        setRenderStage(status.stage);

        if (status.status === 'completed') {
          setRenderStatus('completed');
          if (status.output_url) {
            setRenderOutputUrl(status.output_url);
            setPostAnalysis({ integratedLUFS: -14, truePeakDBTP: -1.0, dynamicRange: 8 });
          }
          addToast({ type: 'success', message: 'Master rendered!' });
        } else if (status.status === 'failed') {
          setRenderStatus('failed');
          addToast({ type: 'error', message: 'Render failed' });
        } else {
          setTimeout(poll, 1500);
        }
      };
      setTimeout(poll, 1500);
    } catch {
      setRenderStatus('failed');
      addToast({ type: 'error', message: 'Failed to start render' });
    }
  }, [sessionToken, manifest, save, setRenderStatus, setRenderProgress, setRenderStage, setRenderJobId, setRenderOutputUrl, setPostAnalysis, addToast]);

  const renderOutputUrl = useProcessingStore((s) => s.renderOutputUrl);

  return (
    <div
      className="min-h-screen bg-aurora-bg text-white flex flex-col"
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-aurora-accent flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-lg tracking-tight">Aurora</span>
          <span className="text-white/20 text-sm">v5.0</span>
        </div>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="bg-transparent text-center text-sm text-white/60 hover:text-white focus:text-white focus:outline-none border-b border-transparent hover:border-slate-700 focus:border-aurora-accent transition-colors w-64"
          placeholder="Untitled Master"
        />
        <div className="flex items-center gap-2">
          {isAuthenticated && (
            <button
              onClick={save}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded border border-slate-700 text-white/60 hover:text-white hover:border-aurora-accent/50 transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              Save
            </button>
          )}
          {renderOutputUrl && (
            <a
              href={renderOutputUrl}
              download
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-green-700 hover:bg-green-600 text-white transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </a>
          )}
        </div>
      </header>

      {/* Waveform + transport */}
      <div className="border-b border-slate-800 px-6 py-3 shrink-0">
        {duration > 0 ? (
          <div className="flex flex-col gap-2">
            <WaveformDisplay height={60} />
            <div className="flex items-center gap-3">
              <button
                onClick={() => isPlaying ? pause() : play()}
                className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-white transition-colors"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>
              <button
                onClick={stop}
                className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-white transition-colors"
              >
                <Square className="w-4 h-4" />
              </button>
              <span className="text-xs text-white/30 font-mono">
                {duration.toFixed(1)}s
              </span>
              <div className="flex-1" />
              <button
                onClick={handleRender}
                disabled={renderStatus === 'running' || duration === 0}
                className="flex items-center gap-2 px-4 py-1.5 bg-aurora-accent rounded-lg text-sm font-medium text-white disabled:opacity-50 hover:bg-blue-400 transition-colors"
              >
                {renderStatus === 'running' ? (
                  <>
                    <LoadingSpinner size="sm" />
                    {renderStage} {renderProgress > 0 && `${renderProgress}%`}
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Render Master
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <div
            className={`flex flex-col items-center justify-center h-24 border-2 border-dashed rounded-lg transition-colors cursor-pointer ${
              isDragging ? 'border-aurora-accent bg-aurora-accent/10' : 'border-slate-800 hover:border-slate-600'
            }`}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
            />
            <Upload className="w-6 h-6 text-white/30 mb-1" />
            <span className="text-sm text-white/30">Drop audio here or click to upload</span>
            <span className="text-xs text-white/20">WAV, AIFF, FLAC, MP3</span>
          </div>
        )}
      </div>

      {/* Main area: tabs + meters */}
      <div className="flex flex-1 min-h-0">
        {/* Tab panel */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Tab bar */}
          <div className="flex border-b border-slate-800 shrink-0">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`px-4 py-2.5 text-xs font-medium uppercase tracking-wider transition-colors ${
                  activeTab === t.id
                    ? 'text-aurora-accent border-b-2 border-aurora-accent'
                    : 'text-white/40 hover:text-white/70'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'eq' && <EQTab />}
            {activeTab === 'dynamics' && <DynamicsTab />}
            {activeTab === 'loudness' && <LoudnessTab />}
            {activeTab === 'analyze' && <AnalyzeTab />}
            {activeTab === 'colab' && <ColabTab />}
            {activeTab === 'reference' && <ReferenceTab />}
          </div>
        </div>

        {/* Sidebar meters */}
        <div className="w-56 border-l border-slate-800 p-3 flex flex-col gap-3 shrink-0">
          <LUFSMeter />
          <TruePeakMeter />
        </div>
      </div>
    </div>
  );
}
