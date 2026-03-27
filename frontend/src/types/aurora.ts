/**
 * Aurora frontend types (v4.0 Section 22.1 session manifest, contexts).
 */

export type SubscriptionTier = 'trial' | 'artist' | 'pro' | 'enterprise'

export type AuroraErrorCode =
  | 'AURORA-E001'
  | 'AURORA-E002'
  | 'AURORA-E007'
  | 'AURORA-E100'
  | 'AURORA-E104'
  | 'AURORA-E301'
  | 'AURORA-E602'
  | 'AURORA-E700'
  | 'AURORA-E701'
  | 'AURORA-B001'
  | 'AURORA-B002'
  | 'AURORA-B003'
  | 'AURORA-B005'
  | string

export interface AudioContextState {
  playbackPosition: number
  isPlaying: boolean
  meters: { left: number; right: number; center?: number; lfe?: number; surrounds?: number[] }
  momentaryLUFS: number
  shortTermLUFS: number
  integratedLUFS: number
  truePeakDBTP: number
  waveformPeaks: Float32Array | null
}

export interface ProcessingContextState {
  macros: Record<string, number>
  macroSource: 'model' | 'heuristic' | 'manual'
  macroConfidence: number
  macroUncertainty: number
  renderStatus: 'idle' | 'running' | 'completed' | 'failed'
  renderProgress: number
  renderStage: string
  renderJobId: string | null
  undoStack: unknown[]
  redoStack: unknown[]
}

export interface SessionContextState {
  sessionId: string | null
  versionId: string | null
  versionHistory: unknown[]
  isDirty: boolean
  lastSaved: string | null
  title: string
  sourceFile: string | null
  features: unknown | null
  collaborationState: unknown
}

export interface ReferenceContextState {
  referenceBuffer: ArrayBuffer | null
  profiles: unknown[]
  matchStrength: number
  matchMode: 'tonal' | 'dynamic' | 'full'
}

export interface ThemeContextState {
  theme: string
  cssVars: Record<string, string>
}

export interface ToastContextState {
  notifications: Array<{ id: string; severity: string; message: string; duration?: number }>
}

export interface AuthContextState {
  isAuthenticated: boolean
  user: { id: string; email: string; displayName: string; role: string } | null
  permissions: string[]
  sessionToken: string | null
  subscription: {
    state: string
    tier: SubscriptionTier
    tracksUsed: number
    tracksLimit: number | null
    storageUsed: number
    storageLimit: number | null
  } | null
}

/** Session manifest (v4.0 Section 22.1) */
export interface SessionManifest {
  session_id: string
  user_id: string
  version_id?: string
  macros?: Record<string, number>
  genre?: string
  stems?: unknown
  master_bus?: unknown
  repair?: unknown
  loudness?: { target_lufs?: number; ceiling_dbtp?: number }
  qc?: unknown
  forensics?: unknown
  render_settings?: unknown
  source_file?: string
  aurora_dsp_version?: string
  aurora_dsp_wasm_hash?: string
  auroranet_model?: string
  [key: string]: unknown
}
