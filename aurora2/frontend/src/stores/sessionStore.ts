import { create } from 'zustand';
import type { SessionManifest } from '@/types/aurora';

interface SessionStore {
  sessionId: string | null;
  versionId: string | null;
  manifest: SessionManifest | null;
  isDirty: boolean;
  lastSaved: string | null;
  title: string;
  sourceFileKey: string | null;
  sourceFileName: string | null;

  setSessionId: (id: string) => void;
  setVersionId: (id: string) => void;
  setManifest: (m: SessionManifest) => void;
  patchManifest: (patch: Partial<SessionManifest>) => void;
  setIsDirty: (v: boolean) => void;
  setLastSaved: (v: string) => void;
  setTitle: (v: string) => void;
  setSourceFile: (key: string, name: string) => void;
  reset: () => void;
}

const defaultManifest: SessionManifest = {
  spec_version: '4.0',
  session_id: '',
  user_id: '',
  version_id: '',
  title: 'Untitled Master',
  macros: {
    warmth: 0, brightness: 0, air: 0,
    punch: 0, depth: 0, width: 1.0,
    clarity: 0, glue: 0,
  },
  genre: 'other',
  stems: {},
  master_bus: {},
  repair: {},
  loudness: { target_lufs: -14.0, ceiling_dbtp: -1.0 },
  qc: {},
  forensics: {},
  render_settings: { codec: 'wav', bit_depth: 24, sample_rate: 44100 },
  source_file: '',
  aurora_dsp_version: '5.0.0',
  aurora_dsp_wasm_hash: '',
  auroranet_model: 'heuristic',
};

export const useSessionStore = create<SessionStore>((set, get) => ({
  sessionId: null,
  versionId: null,
  manifest: null,
  isDirty: false,
  lastSaved: null,
  title: 'Untitled Master',
  sourceFileKey: null,
  sourceFileName: null,

  setSessionId: (id) => set({ sessionId: id }),
  setVersionId: (id) => set({ versionId: id }),
  setManifest: (m) => set({ manifest: m }),
  patchManifest: (patch) => {
    const current = get().manifest ?? { ...defaultManifest };
    set({ manifest: { ...current, ...patch }, isDirty: true });
  },
  setIsDirty: (v) => set({ isDirty: v }),
  setLastSaved: (v) => set({ lastSaved: v, isDirty: false }),
  setTitle: (v) => set({ title: v }),
  setSourceFile: (key, name) => set({ sourceFileKey: key, sourceFileName: name }),
  reset: () => set({
    sessionId: null, versionId: null, manifest: null,
    isDirty: false, lastSaved: null, title: 'Untitled Master',
    sourceFileKey: null, sourceFileName: null,
  }),
}));

export { defaultManifest };
