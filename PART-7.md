# Part 7: React context, Web Audio, WebGL, dual-mode UI

**Scope:** Phase 7A, 7B, 7C, 7D.  
**Do not proceed to Part 8 until instructed.**

---

## Phase 7A — React context and auth flow

**TASK 7A-1 — Volatile audio store (Zustand)**  
`frontend/src/stores/audioStore.ts`: NOT React Context. create + subscribeWithSelector. State: playbackPosition, isPlaying, meters (left/right/center/lfe/surrounds), momentaryLUFS, shortTermLUFS, integratedLUFS, truePeakDBTP, waveformPeaks. Actions: setPlaybackPosition, setMeterLevels, setLUFS, setTruePeak, setIsPlaying, setWaveformPeaks, reset. Selector hooks (usePlaybackPosition, useIsPlaying, useMeterLevels, useLUFSMeters). getAudioStoreState() for non-React (AudioWorklet, render loop)—no re-renders.

**TASK 7A-2 — Auth context**  
`frontend/src/contexts/AuthContext.tsx`: AuthContextState (isAuthenticated, user, permissions, sessionToken); subscription (state, tier, tracksUsed/Limit, storageUsed/Limit). checkAuth via /api/auth/me (credentials: include); refresh /api/auth/refresh. login, logout, refreshToken, register. Token in httpOnly cookie; 45min refresh interval. Export useAuth.

**TASK 7A-3 — Processing context**  
`frontend/src/contexts/ProcessingContext.tsx`: macros (7), macroSource, macroConfidence, macroUncertainty, renderStatus, renderProgress, renderStage, renderJobId, undoStack, redoStack (max 100). setMacro → push undo, clear redo, macroSource='manual'. setAllMacros, undo, redo. startRender: POST /api/render, subscribe SSE /api/render/progress/{session_id}. cancelRender.

**TASK 7A-4 — Session context**  
`frontend/src/contexts/SessionContext.tsx`: sessionId, versionId, versionHistory, isDirty, lastSaved, title, sourceFile, features, collaborationState. createSession: presign → PUT → confirm → POST session → analyze → predict-macros → set ProcessingContext. loadSession, saveSession, createVersion, restoreVersion, setTitle. Auto-save debounce 5s after macro change.

**TASK 7A-5 — Reference context**  
`frontend/src/contexts/ReferenceContext.tsx`: reference buffer, profiles (tonal, dynamic, stereo, transient), matchStrength 0–100%, matchMode (tonal, dynamic, full). Upload and profile extraction.

**TASK 7A-6 — Theme context**  
`frontend/src/contexts/ThemeContext.tsx`: themes default, analog, quantum, spatial, dark-studio. CSS vars (--bg-primary, --accent-primary, --meter-*, etc.). Persist to localStorage. Default dark-studio.

**TASK 7A-7 — Toast context**  
`frontend/src/contexts/ToastContext.tsx`: notifications (id, severity, message, duration). Severity styling (info/success/warning/error/billing). Auto-dismiss 5s/10s; error/billing until dismissed. Aurora error codes.

**TASK 7A-8 — App root**  
`frontend/src/App.tsx`: ThemeProvider → ToastProvider → AuthProvider → SessionProvider → ProcessingProvider → ReferenceProvider → Router. Routes: /, /login, /register, /pricing, /app (ProtectedRoute MasteringApp), /app/session/:sessionId, /settings. ProtectedRoute redirect to /login if not authenticated.

**TASK 7A-9 — Auth pages**  
LoginPage (email/password, Google, forgot stub, link register). RegisterPage (email, password ≥12, display name, ToS, success → verify message). PricingPage (3 tiers, annual default, feature table, Artist/Pro checkout, Enterprise contact, Join Waitlist).

**TASK 7A-10 — API client**  
`frontend/src/utils/api.ts`: AuroraAPI baseUrl /api, request with credentials: include. login, register, logout, getMe; createSession, getSession, listSessions, updateSession; getPresignedUpload, confirmUpload; analyze, predictMacros; startRender, getRenderStatus, cancelRender; subscribeToRenderProgress (EventSource, progress/complete/error); getSubscription, createCheckoutSession, createPortalSession; createCollabSession, inviteToCollab; chatStream. AuroraAPIError(code, message, severity, details, httpStatus).

**TASK 7A-11 — Build**  
Run: cd frontend && npx tsc --noEmit. Zero errors. Report files.

---

## Phase 7B — Web Audio and AudioWorklet

**TASK 7B-1 — Audio engine**  
`frontend/src/audio/AudioEngine.ts`: AudioContext(sampleRate 48000), load preview-processor.js, AnalyserNode, GainNode, AudioWorkletNode 'preview-processor'. Source → worklet → gain → analyser → destination. loadAudioFile(file), loadAudioFromUrl(url); generateWaveformPeaks → setWaveformPeaks. play(offset), pause, stop, seekTo; setVolume. updatePreviewParams(macros) → worklet port postMessage set_params. Metering loop: requestAnimationFrame; store setPlaybackPosition, setMeterLevels (from analyser); optional WASM LUFS/TP if available. export audioEngine singleton.

**TASK 7B-2 — Preview processor**  
`frontend/public/audio/preview-processor.js`: AudioWorkletProcessor. Params from macros (brighten, glue, width, punch, warmth, depth, air). Simplified: EQ (low shelf warmth, high shelf brighten/air), compression (glue), M/S side gain (width), tanh saturation (warmth), limiter -1 dBFS. updateCoefficients(); process(inputs, outputs). registerProcessor('preview-processor', PreviewProcessor).

**TASK 7B-3 — Hook**  
`frontend/src/hooks/useAudioEngine.ts`: useAudioEngine() → loadFile, play, pause, stop, seekTo, setVolume, updatePreviewParams, isInitialized, duration, sampleRate, channels. Init on first use; sync macros to engine; cleanup on unmount.

---

## Phase 7C — WebGL2 visualizers

**Rule:** requestAnimationFrame loop reads Zustand/analyser; no setState in loop. Frame <4ms.

**TASK 7C-1 — WebGL base**  
`frontend/src/components/visualizers/WebGLRenderer.ts`: getContext('webgl2', alpha:false, antialias:false, desynchronized:true). context lost/restored handlers. compileShader, createProgram. start/stop animate loop. resize(width, height). Subclass: setupShaders(), render().

**TASK 7C-2 — Waveform**  
WaveformRenderer: peak/RMS, cursor, clipping indicators. Data from store waveformPeaks + playbackPosition. GL_LINES or equivalent.

**TASK 7C-3 — Spectrogram**  
SpectrogramRenderer: FFT from AnalyserNode, scrolling texture, color map (magma/viridis/etc.), freq scale (linear/log/mel). FFT size 2048/4096/8192.

**TASK 7C-4 — Phase correlation**  
PhaseCorrelationRenderer: L/R time domain → XY plot; correlation value; persistence/decay.

**TASK 7C-5 — LUFS history**  
LUFSHistoryRenderer: circular buffer; momentary/short-term/integrated lines; target line; read from store.

**TASK 7C-6 — React wrappers**  
Waveform.tsx, Spectrogram.tsx, PhaseCorrelation.tsx, LUFSHistory.tsx: useRef canvas, useEffect create renderer, ResizeObserver, cleanup. React.memo. No re-render during playback.

**TASK 7C-7 — Canvas2D fallback**  
When WebGL context lost: simplified waveform/spectrogram, text LUFS, notify user.

**TASK 7C-8 — Tests**  
visualizers.test.ts: waveform mounts; context loss handling; spectrogram color change; phase correlation mono ≈1; LUFS buffer wrap. npx vitest run.

---

## Phase 7D — Simple / Advanced mode UI

**TASK 7D-1 — App shell**  
`frontend/src/pages/MasteringApp.tsx`: TopNav (logo, session title, mode toggle Simple/Advanced, user menu, notifications). Main: mode===simple ? SimpleMode : AdvancedMode. Bottom TransportBar. Mode in localStorage aurora_ui_mode, default simple.

**TASK 7D-2 — Simple mode**  
`frontend/src/components/modes/SimpleMode.tsx`: States—Upload (drop zone, genre grid); Processing (12-stage pipeline display, progress, LUFS, platform score); Results (before/after, metrics, platform table, AI summary, download, “Master another”, upgrade CTA); Error (code, retry). sessionId/renderStatus drive state.

**TASK 7D-3 — DropZone**  
Drag-drop; validate format/size (500 MB); lossy warning AURORA-E007; presign → PUT → confirm → create session flow. SUPPORTED_FORMATS, LOSSY_FORMATS.

**TASK 7D-4 — Advanced mode**  
Tab sidebar (Master, Stems, Reference, Repair, QC, Export, Collab; stubs Versions, Spatial per spec). Top 40%: waveform + spectrogram. Bottom 60%: tab content. Right: LUFS, True Peak, PhaseCorrelation.

**TASK 7D-5 — Master tab**  
Macro knobs (0–10), uncertainty arc, source badge (model/heuristic/manual). Interaction indicators (synergy/tension). Analog Warmth Engine (character, drive). Loudness target, ceiling, platform penalty.

**TASK 7D-6 — Stems tab**  
Per-stem level, solo, mute, pan; confidence; waveform thumb; conflict matrix.

**TASK 7D-7 — QC tab**  
18-check list (PASS/WARNING/FAIL/REMEDIATED); expand details; auto-remediation toggles; re-run QC.

**TASK 7D-8 — Export tab**  
Formats by tier; locked + upgrade prompt; download per format; Download All (zip).

**TASK 7D-9 — Transport bar**  
Play/Pause, Stop, position, scrubber, volume, A/B. Position via ref + requestAnimationFrame from store (no React state in loop).

**TASK 7D-10 — Landing**  
Hero, how it works (3 steps), features, pricing link, Get Early Access → waitlist. Footer Terms, Privacy, Cookies.

**TASK 7D-11 — Settings**  
Profile, Billing (plan, usage, Stripe portal), Security (password, 2FA), Data (download, delete).

**TASK 7D-12 — Shortcuts**  
useKeyboardShortcuts: Space play/pause, Escape stop, Cmd+Z undo, Cmd+Shift+Z redo, Cmd+S save, A A/B, S mode toggle, 1–7 macro focus, Tab cycle tabs.

**TASK 7D-13 — Build**  
npm run build; bundle <500 KB gzipped (excl. WASM). Report.

---

## End of Part 7

**Halt.** Report: (1) Files created/modified. (2) tsc and build success. (3) Vitest visualizer tests. (4) Any deviations.  
**Do not proceed to Part 8 until instructed.**
