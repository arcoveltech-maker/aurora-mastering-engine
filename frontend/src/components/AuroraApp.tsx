import { useState, useRef, useEffect, useCallback } from 'react'

// ─── DESIGN SYSTEM ────────────────────────────────────────────────────────────
const T = {
  bg: '#0A0A0B', panel: '#111114', panelAlt: '#16161A', border: '#1E1E24', borderHi: '#2A2A34',
  accent: '#E8FF6B', cyan: '#6BFFD8', purple: '#B06BFF', red: '#FF4D6B', orange: '#FF9B4D',
  text: '#E8E8F0', sub: '#7A7A8A', dim: '#3A3A44',
  mono: "'IBM Plex Mono', monospace", display: "'Bebas Neue', sans-serif", ui: "'Inter', sans-serif",
  r: '4px', rM: '8px', rL: '12px', u: 8,
}

// ─── TYPES ────────────────────────────────────────────────────────────────────
interface AnalysisResult {
  lufs_integrated: number; lufs_short_term: number; true_peak: number
  dynamic_range: number; lra: number; crest_factor: number
  phase_correlation: number; spectral_centroid: number
  platform_scores: Record<string, number>
  sample_rate: number; bit_depth: number; duration: number; channels: number
}
type StemName = 'vocals'|'lead_vox'|'harmonies'|'bass'|'drums'|'kick'|'snare'|'cymbals'|'guitar'|'piano'|'strings'|'other'
interface StemData { name: StemName; confidence: number; rms: number; peak: number; downloadUrl?: string }
interface ConflictMatrix { [k: string]: Record<string, number> }
interface Macros { loudness: number; warmth: number; brighten: number; punch: number; glue: number }
type HardwareModel = 'ssl_g'|'api_2500'|'neve_8078'|'chandler_tg1'|'tube_tech'
interface SpatialPosition { stem: StemName; x: number; y: number; elevation: number; distance: number }
type QCStatus = 'PASS'|'FAIL'|'WARN'|'FIX'
interface QCResult { id: string; label: string; status: QCStatus; detail: string; value?: number; remediated: boolean; auto_fix_available: boolean }
interface ChatMsg { role: 'user'|'assistant'; content: string; params?: Partial<Macros>; thinking?: string; timestamp: number }
type GenrePreset = 'ccm'|'gospel'|'club'|'worship'|'vinyl'|'broadcast'|'hiphop'|'rnb'
interface AlbumTrack { id: string; title: string; artist: string; isrc: string; duration: number; lufs?: number; true_peak?: number; status: 'pending'|'processing'|'done'|'error'; filePath?: string }
type ExportFormat = 'wav_24_48'|'wav_16_44'|'flac_24'|'mp3_320'|'atmos_adm'|'atmos_mp4'|'ddp'|'stem_pack'|'vinyl'
interface VinylConfig { riaa: boolean; monoFoldHz: 80|100|120|150; sibilanceLimitDb: -3|-6; sideAMins: number; sideBMins: number }
interface TrackMetadata { title: string; artist: string; album: string; year: string; genre: string; isrc: string; label: string; publisher: string; coverArt?: string }

// ─── useSessionState ──────────────────────────────────────────────────────────
function useSessionState<T>(key: string, init: T): [T, React.Dispatch<React.SetStateAction<T>>] {
  const [val, setVal] = useState<T>(() => {
    try {
      const s = localStorage.getItem(`aurora_v3_${key}`)
      return s ? JSON.parse(s) as T : init
    } catch { return init }
  })
  const setter: React.Dispatch<React.SetStateAction<T>> = useCallback((action) => {
    setVal(prev => {
      const next = typeof action === 'function' ? (action as (p: T) => T)(prev) : action
      try { localStorage.setItem(`aurora_v3_${key}`, JSON.stringify(next)) } catch {}
      return next
    })
  }, [key])
  return [val, setter]
}

// ─── API CLIENT ───────────────────────────────────────────────────────────────
const api = {
  async post<T>(path: string, body: unknown): Promise<T> {
    const r = await fetch(`/api${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    if (!r.ok) { const e = await r.json().catch(() => ({ error: r.statusText })); throw new Error((e as {error:string}).error || r.statusText) }
    return r.json() as Promise<T>
  },
  async upload<T>(path: string, file: File, fields?: Record<string, string>): Promise<T> {
    const fd = new FormData(); fd.append('file', file)
    if (fields) Object.entries(fields).forEach(([k, v]) => fd.append(k, v))
    const r = await fetch(`/api${path}`, { method: 'POST', body: fd })
    if (!r.ok) { const e = await r.json().catch(() => ({ error: r.statusText })); throw new Error((e as {error:string}).error || r.statusText) }
    return r.json() as Promise<T>
  },
  async get<T>(path: string): Promise<T> {
    const r = await fetch(`/api${path}`)
    if (!r.ok) throw new Error(r.statusText)
    return r.json() as Promise<T>
  },
  async pollJob(jobId: string, onProgress: (pct: number, msg: string) => void, intervalMs = 800): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const iv = setInterval(async () => {
        try {
          const d = await api.get<{ progress: number; status: string; result?: unknown; error?: string; message?: string }>(`/job/${jobId}`)
          onProgress(d.progress, d.message || d.status)
          if (d.status === 'error') { clearInterval(iv); reject(new Error(d.error || 'Job failed')) }
          if (d.progress >= 100 || d.status === 'done') { clearInterval(iv); resolve(d.result) }
        } catch (e) { clearInterval(iv); reject(e) }
      }, intervalMs)
    })
  },
  streamChat(sessionId: string, message: string, params: Partial<Macros>,
    onThinking: (d: string) => void, onText: (d: string) => void,
    onDone: (p: Partial<Macros> | null) => void, onError: (e: string) => void): () => void {
    const ctrl = new AbortController()
    ;(async () => {
      try {
        const r = await fetch('/api/chat/stream', {
          method: 'POST', signal: ctrl.signal,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, message, params })
        })
        if (!r.ok) { onError(`HTTP ${r.status}`); return }
        const reader = r.body!.getReader(); const dec = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          const lines = buf.split('\n'); buf = lines.pop() || ''
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const ev = JSON.parse(line.slice(6)) as { type: string; delta?: string; params?: Partial<Macros> | null }
              if (ev.type === 'thinking' && ev.delta) onThinking(ev.delta)
              else if (ev.type === 'text' && ev.delta) onText(ev.delta)
              else if (ev.type === 'done') onDone(ev.params ?? null)
              else if (ev.type === 'error') onError(ev.delta || 'Stream error')
            } catch {}
          }
        }
      } catch (e) { if ((e as Error).name !== 'AbortError') onError(String(e)) }
    })()
    return () => ctrl.abort()
  }
}

// ─── GENRE PRESETS ────────────────────────────────────────────────────────────
const GENRE_PRESETS: Record<GenrePreset, Macros> = {
  ccm:       { loudness:80, warmth:55, brighten:60, punch:65, glue:60 },
  gospel:    { loudness:78, warmth:65, brighten:55, punch:70, glue:58 },
  club:      { loudness:90, warmth:45, brighten:70, punch:85, glue:75 },
  worship:   { loudness:70, warmth:60, brighten:50, punch:45, glue:50 },
  vinyl:     { loudness:65, warmth:80, brighten:40, punch:55, glue:45 },
  broadcast: { loudness:72, warmth:58, brighten:52, punch:50, glue:55 },
  hiphop:    { loudness:88, warmth:60, brighten:55, punch:80, glue:70 },
  rnb:       { loudness:82, warmth:70, brighten:58, punch:65, glue:62 },
}
const GENRE_LABELS: Record<GenrePreset, string> = {
  ccm:'CCM', gospel:'Gospel', club:'Club / Electronic', worship:'Worship',
  vinyl:'Vinyl / Analog', broadcast:'Broadcast', hiphop:'Hip-Hop', rnb:'R&B / Soul'
}

// ─── ATOM COMPONENTS ─────────────────────────────────────────────────────────
function Pnl({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: T.rM, padding: 16, ...style }}>{children}</div>
}
function Hd({ children, size = 11 }: { children: React.ReactNode; size?: number }) {
  return <div style={{ fontFamily: T.mono, fontSize: size, color: T.sub, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 10 }}>{children}</div>
}
function Lbl({ children }: { children: React.ReactNode }) {
  return <span style={{ fontFamily: T.mono, fontSize: 10, color: T.sub, letterSpacing: '0.08em' }}>{children}</span>
}
function Val({ children, color }: { children: React.ReactNode; color?: string }) {
  return <span style={{ fontFamily: T.mono, fontSize: 13, color: color || T.accent, fontWeight: 600 }}>{children}</span>
}
function LED({ on, color }: { on: boolean; color?: string }) {
  const c = color || T.cyan
  return <div style={{ width: 8, height: 8, borderRadius: '50%', background: on ? c : T.dim, boxShadow: on ? `0 0 6px ${c}` : 'none', flexShrink: 0 }} />
}
function Divider({ style }: { style?: React.CSSProperties }) {
  return <div style={{ width: '100%', height: 1, background: T.border, ...style }} />
}
function Row({ children, gap = 8, style }: { children: React.ReactNode; gap?: number; style?: React.CSSProperties }) {
  return <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap, ...style }}>{children}</div>
}
function Grid({ children, cols = 2, gap = 12, style }: { children: React.ReactNode; cols?: number; gap?: number; style?: React.CSSProperties }) {
  return <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap, ...style }}>{children}</div>
}
function InfoRow({ label, value, color }: { label: string; value: React.ReactNode; color?: string }) {
  return (
    <Row style={{ justifyContent: 'space-between', padding: '4px 0' }}>
      <Lbl>{label}</Lbl>
      <Val color={color}>{value}</Val>
    </Row>
  )
}
function Badge({ children, status }: { children: React.ReactNode; status?: QCStatus | 'ok' | 'warn' }) {
  const colors: Record<string, string> = { PASS: T.cyan, FAIL: T.red, WARN: T.orange, FIX: T.purple, ok: T.cyan, warn: T.orange }
  const c = status ? colors[status] || T.sub : T.sub
  return (
    <span style={{ fontFamily: T.mono, fontSize: 10, letterSpacing: '0.1em', padding: '2px 7px', borderRadius: T.r, border: `1px solid ${c}`, color: c, whiteSpace: 'nowrap' }}>
      {children}
    </span>
  )
}
function Tog({ value, onChange, label }: { value: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <Row gap={8} style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => onChange(!value)}>
      <div style={{ width: 36, height: 20, borderRadius: 10, background: value ? T.accent : T.border, position: 'relative', transition: 'background 0.2s', flexShrink: 0 }}>
        <div style={{ position: 'absolute', top: 3, left: value ? 19 : 3, width: 14, height: 14, borderRadius: '50%', background: value ? T.bg : T.sub, transition: 'left 0.2s' }} />
      </div>
      {label && <Lbl>{label}</Lbl>}
    </Row>
  )
}
function Btn({ children, onClick, variant = 'default', disabled = false, style }: {
  children: React.ReactNode; onClick?: () => void; variant?: 'default'|'primary'|'danger'|'ghost'; disabled?: boolean; style?: React.CSSProperties
}) {
  const variants = {
    default: { background: T.panel, border: `1px solid ${T.border}`, color: T.text },
    primary: { background: T.accent, border: `1px solid ${T.accent}`, color: T.bg },
    danger:  { background: 'transparent', border: `1px solid ${T.red}`, color: T.red },
    ghost:   { background: 'transparent', border: `1px solid ${T.border}`, color: T.sub },
  }
  return (
    <button onClick={onClick} disabled={disabled} style={{
      fontFamily: T.mono, fontSize: 11, letterSpacing: '0.08em', padding: '6px 14px',
      borderRadius: T.r, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1,
      transition: 'all 0.15s', whiteSpace: 'nowrap', ...variants[variant], ...style
    }}>{children}</button>
  )
}

// ─── KNOB ─────────────────────────────────────────────────────────────────────
interface KnobProps { value: number; onChange: (v: number) => void; min?: number; max?: number; default?: number; label: string; size?: number; color?: string; unit?: string }
function Knob({ value, onChange, min = 0, max = 100, default: def, label, size = 72, color = T.accent, unit }: KnobProps) {
  const dragRef = useRef<{ active: boolean; startY: number; startVal: number }>({ active: false, startY: 0, startVal: 0 })
  const pct = (value - min) / (max - min)
  const startAngle = -135, sweepAngle = 270
  const angle = startAngle + pct * sweepAngle
  const r = size / 2 - 8
  const cx = size / 2, cy = size / 2
  const toRad = (a: number) => (a * Math.PI) / 180
  const arcPath = (from: number, to: number) => {
    const f = toRad(from), t = toRad(to)
    const x1 = cx + r * Math.cos(f), y1 = cy + r * Math.sin(f)
    const x2 = cx + r * Math.cos(t), y2 = cy + r * Math.sin(t)
    const large = Math.abs(to - from) > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`
  }
  const dotX = cx + (r - 2) * Math.cos(toRad(angle)), dotY = cy + (r - 2) * Math.sin(toRad(angle))

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current.active) return
      const dy = dragRef.current.startY - e.clientY
      const delta = (dy / 150) * (max - min)
      onChange(Math.max(min, Math.min(max, dragRef.current.startVal + delta)))
    }
    const onUp = () => { dragRef.current.active = false }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [min, max, onChange])

  const glowing = pct > 0.6
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, userSelect: 'none' }}>
      <svg width={size} height={size} style={{ cursor: 'ns-resize', overflow: 'visible' }}
        onMouseDown={e => { dragRef.current = { active: true, startY: e.clientY, startVal: value }; e.preventDefault() }}
        onDoubleClick={() => onChange(def ?? (min + max) / 2)}>
        {glowing && (
          <defs>
            <filter id={`glow-${label}`}>
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0.9  0 1 0 0 1  0 0 0 0 0.4  0 0 0 0.8 0" result="glow" />
              <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
        )}
        <path d={arcPath(-135, 135)} fill="none" stroke={T.border} strokeWidth={4} strokeLinecap="round" />
        {pct > 0 && <path d={arcPath(-135, -135 + pct * 270)} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" filter={glowing ? `url(#glow-${label})` : undefined} />}
        <circle cx={dotX} cy={dotY} r={4} fill={color} />
      </svg>
      <span style={{ fontFamily: T.mono, fontSize: 11, color: T.accent, fontWeight: 600 }}>{Math.round(value)}{unit || ''}</span>
      <span style={{ fontFamily: T.mono, fontSize: 9, color: T.sub, letterSpacing: '0.1em', textTransform: 'uppercase' }}>{label}</span>
    </div>
  )
}

// ─── SPECTRUM ─────────────────────────────────────────────────────────────────
function Spectrum({ active, bars = 32, height = 56, color = T.cyan }: { active: boolean; bars?: number; height?: number; color?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const stateRef = useRef<{ vals: Float32Array; targets: Float32Array; iv: ReturnType<typeof setInterval> | null }>({ vals: new Float32Array(bars), targets: new Float32Array(bars), iv: null })

  useEffect(() => {
    const s = stateRef.current
    if (active) {
      s.iv = setInterval(() => {
        for (let i = 0; i < bars; i++) {
          s.targets[i] = Math.random() * (1 - (i / bars) * 0.65)
          s.vals[i] = s.vals[i] * 0.72 + s.targets[i] * 0.28
        }
        const cv = canvasRef.current; if (!cv) return
        const ctx = cv.getContext('2d')!
        ctx.clearRect(0, 0, cv.width, cv.height)
        const w = cv.width / bars
        for (let i = 0; i < bars; i++) {
          const h = s.vals[i] * cv.height
          const g = ctx.createLinearGradient(0, cv.height - h, 0, cv.height)
          g.addColorStop(0, T.accent); g.addColorStop(1, color)
          ctx.fillStyle = g
          ctx.fillRect(i * w + 1, cv.height - h, w - 2, h)
        }
      }, 16)
    } else {
      if (s.iv) { clearInterval(s.iv); s.iv = null }
      const decay = setInterval(() => {
        let allZero = true
        for (let i = 0; i < bars; i++) { s.vals[i] *= 0.88; if (s.vals[i] > 0.001) allZero = false }
        const cv = canvasRef.current; if (!cv) return
        const ctx = cv.getContext('2d')!
        ctx.clearRect(0, 0, cv.width, cv.height)
        const w = cv.width / bars
        for (let i = 0; i < bars; i++) {
          const h = s.vals[i] * cv.height
          ctx.fillStyle = color + '60'
          ctx.fillRect(i * w + 1, cv.height - h, w - 2, h)
        }
        if (allZero) clearInterval(decay)
      }, 16)
    }
    return () => { if (s.iv) { clearInterval(s.iv); s.iv = null } }
  }, [active, bars, color])

  return <canvas ref={canvasRef} width={bars * 6} height={height} style={{ width: '100%', height }} />
}

// ─── WAVEFORM ─────────────────────────────────────────────────────────────────
function Waveform({ buffer, playbackPos, processing, height = 80 }: { buffer: AudioBuffer | null; playbackPos: number; processing: boolean; height?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  useEffect(() => {
    const cv = canvasRef.current; if (!cv) return
    const ctx = cv.getContext('2d')!
    cancelAnimationFrame(animRef.current)
    const draw = (ts: number) => {
      const w = cv.width, h = cv.height
      ctx.clearRect(0, 0, w, h)
      ctx.fillStyle = T.bg
      ctx.fillRect(0, 0, w, h)
      if (buffer) {
        const data = buffer.getChannelData(0)
        const step = Math.ceil(data.length / w)
        ctx.beginPath()
        ctx.fillStyle = T.cyan + '38'
        for (let x = 0; x < w; x++) {
          let min = 1, max = -1
          for (let j = 0; j < step; j++) { const s = data[x * step + j] || 0; if (s < min) min = s; if (s > max) max = s }
          const yMin = (1 - (min + 1) / 2) * h, yMax = (1 - (max + 1) / 2) * h
          ctx.fillRect(x, yMax, 1, Math.max(1, yMin - yMax))
        }
        ctx.beginPath()
        ctx.strokeStyle = T.cyan + 'CC'; ctx.lineWidth = 1
        for (let x = 0; x < w; x++) {
          const s = data[Math.floor((x / w) * data.length)] || 0
          const y = (1 - (s + 1) / 2) * h
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        }
        ctx.stroke()
        const cx2 = playbackPos * w
        ctx.strokeStyle = T.accent; ctx.lineWidth = 2
        ctx.beginPath(); ctx.moveTo(cx2, 0); ctx.lineTo(cx2, h); ctx.stroke()
      } else if (processing) {
        const scanX = ((ts / 2000) % 1) * w
        ctx.fillStyle = T.border + '80'
        ctx.fillRect(0, 0, w, h)
        const g = ctx.createLinearGradient(scanX - 40, 0, scanX + 3, 0)
        g.addColorStop(0, 'transparent'); g.addColorStop(1, T.accent)
        ctx.fillStyle = g
        ctx.fillRect(scanX - 40, 0, 43, h)
        ctx.fillStyle = T.accent; ctx.fillRect(scanX, 0, 2, h)
        animRef.current = requestAnimationFrame(draw)
        return
      } else {
        ctx.strokeStyle = T.dim; ctx.lineWidth = 1; ctx.setLineDash([4, 6])
        ctx.beginPath(); ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2); ctx.stroke()
        ctx.setLineDash([])
      }
    }
    animRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(animRef.current)
  }, [buffer, playbackPos, processing, height])

  return <canvas ref={canvasRef} width={800} height={height} style={{ width: '100%', height, borderRadius: T.r }} />
}

// ─── RING ─────────────────────────────────────────────────────────────────────
function Ring({ value, label, size = 80, color = T.accent, sublabel }: { value: number; label: string; size?: number; color?: string; sublabel?: string }) {
  const r = size / 2 - 6, cx = size / 2, cy = size / 2
  const circ = 2 * Math.PI * r
  const dash = (value / 100) * circ
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={size} height={size}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={T.border} strokeWidth={5} />
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={5}
          strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`} style={{ transition: 'stroke-dasharray 0.5s ease' }} />
        <text x={cx} y={cy + size * 0.1} textAnchor="middle" fill={T.text} fontFamily={T.display} fontSize={size * 0.24}>{Math.round(value)}</text>
      </svg>
      <span style={{ fontFamily: T.mono, fontSize: 9, color: T.sub, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{label}</span>
      {sublabel && <span style={{ fontFamily: T.mono, fontSize: 8, color: T.dim }}>{sublabel}</span>}
    </div>
  )
}

// ─── VU METER ─────────────────────────────────────────────────────────────────
function VUMeter({ left, right, peakL, peakR, height = 120 }: { left: number; right: number; peakL: number; peakR: number; height?: number }) {
  const Bar = ({ val, peak, label }: { val: number; peak: number; label: string }) => {
    const pct = Math.min(1, val)
    const pkPct = Math.min(1, peak)
    const getColor = (p: number) => p > 0.85 ? T.red : p > 0.70 ? T.orange : T.cyan
    const h = pct * (height - 24)
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
        <Lbl>{label}</Lbl>
        <div style={{ width: 10, height: height - 24, background: T.border, borderRadius: 2, position: 'relative', overflow: 'visible' }}>
          <div style={{ position: 'absolute', bottom: 0, width: '100%', height: h, background: getColor(pct), borderRadius: 2, transition: 'height 0.05s' }} />
          <div style={{ position: 'absolute', bottom: pkPct * (height - 24) - 1, width: '100%', height: 2, background: T.accent }} />
        </div>
      </div>
    )
  }
  const labels = [' 0', '-3', '-6', '-12', '-18', '-∞']
  return (
    <Row gap={4} style={{ alignItems: 'flex-start' }}>
      <Bar val={left} peak={peakL} label="L" />
      <Bar val={right} peak={peakR} label="R" />
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: height - 24, paddingLeft: 2 }}>
        {labels.map(l => <span key={l} style={{ fontFamily: T.mono, fontSize: 8, color: T.dim }}>{l}</span>)}
      </div>
    </Row>
  )
}

// ─── SPATIAL PANNER ───────────────────────────────────────────────────────────
const STEM_COLORS: Record<string, string> = {
  vocals: T.accent, lead_vox: T.accent, harmonies: T.accent + 'CC',
  bass: T.cyan, kick: T.cyan,
  drums: T.purple, snare: T.purple, cymbals: T.purple,
  guitar: T.orange, piano: T.orange, strings: T.orange,
  other: T.sub,
}
const BED_LABELS = [
  { label: 'L', x: 0.08, y: 0.5 }, { label: 'R', x: 0.92, y: 0.5 },
  { label: 'C', x: 0.5, y: 0.08 }, { label: 'LFE', x: 0.5, y: 0.92 },
  { label: 'Ls', x: 0.1, y: 0.85 }, { label: 'Rs', x: 0.9, y: 0.85 },
  { label: 'Ltf', x: 0.08, y: 0.2 }, { label: 'Rtf', x: 0.92, y: 0.2 },
  { label: 'Ltr', x: 0.12, y: 0.65 }, { label: 'Rtr', x: 0.88, y: 0.65 },
]
function SpatialPanner({ stems, positions, onChange, size = 380 }: { stems: StemData[]; positions: SpatialPosition[]; onChange: (p: SpatialPosition[]) => void; size?: number }) {
  const [dragging, setDragging] = useState<string | null>(null)
  const [tooltip, setTooltip] = useState<{ stem: string; x: number; y: number } | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const getPos = (stem: StemName): SpatialPosition =>
    positions.find(p => p.stem === stem) ?? { stem, x: 0, y: 0, elevation: 0.5, distance: 0.5 }

  const svgToWorld = (svgX: number, svgY: number) => ({
    x: ((svgX / size) * 2 - 1),
    y: ((svgY / size) * 2 - 1)
  })

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging || !svgRef.current) return
      const rect = svgRef.current.getBoundingClientRect()
      const sx = (e.clientX - rect.left) * (size / rect.width)
      const sy = (e.clientY - rect.top) * (size / rect.height)
      const { x, y } = svgToWorld(sx, sy)
      const clamped = { x: Math.max(-1, Math.min(1, x)), y: Math.max(-1, Math.min(1, y)) }
      const existing = getPos(dragging as StemName)
      onChange(positions.filter(p => p.stem !== dragging).concat([{ ...existing, stem: dragging as StemName, ...clamped }]))
    }
    const onUp = () => setDragging(null)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [dragging, positions, onChange, size])

  return (
    <div style={{ position: 'relative' }}>
      <svg ref={svgRef} width={size} height={size} style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: T.rM, display: 'block' }}>
        {[0.25, 0.5, 0.75].map(r => (
          <circle key={r} cx={size/2} cy={size/2} r={r * size/2} fill="none" stroke={T.border} strokeWidth={1} strokeDasharray="4 6" />
        ))}
        <line x1={size/2} y1={0} x2={size/2} y2={size} stroke={T.border} strokeWidth={1} />
        <line x1={0} y1={size/2} x2={size} y2={size/2} stroke={T.border} strokeWidth={1} />
        {BED_LABELS.map(bl => (
          <text key={bl.label} x={bl.x * size} y={bl.y * size} textAnchor="middle" dominantBaseline="middle"
            fill={T.dim} fontFamily={T.mono} fontSize={10}>{bl.label}</text>
        ))}
        {stems.map(stem => {
          const pos = getPos(stem.name)
          const sx = ((pos.x + 1) / 2) * size
          const sy = ((pos.y + 1) / 2) * size
          const col = STEM_COLORS[stem.name] || T.sub
          return (
            <g key={stem.name}>
              <circle cx={sx} cy={sy} r={10} fill={col + '30'} stroke={col} strokeWidth={1.5}
                style={{ cursor: 'grab' }}
                onMouseDown={e => { setDragging(stem.name); e.preventDefault() }}
                onMouseEnter={() => setTooltip({ stem: stem.name, x: sx, y: sy })}
                onMouseLeave={() => setTooltip(null)} />
              <text x={sx} y={sy + 1} textAnchor="middle" dominantBaseline="middle"
                fill={col} fontFamily={T.mono} fontSize={7} style={{ pointerEvents: 'none' }}>
                {stem.name.slice(0, 3).toUpperCase()}
              </text>
            </g>
          )
        })}
        {tooltip && (
          <g>
            <rect x={tooltip.x + 12} y={tooltip.y - 20} width={110} height={36} rx={4} fill={T.panelAlt} stroke={T.border} strokeWidth={1} />
            <text x={tooltip.x + 17} y={tooltip.y - 7} fill={T.text} fontFamily={T.mono} fontSize={9}>{tooltip.stem}</text>
            <text x={tooltip.x + 17} y={tooltip.y + 7} fill={T.sub} fontFamily={T.mono} fontSize={8}>
              {`X:${getPos(tooltip.stem as StemName).x.toFixed(2)} Y:${getPos(tooltip.stem as StemName).y.toFixed(2)}`}
            </text>
          </g>
        )}
      </svg>
    </div>
  )
}

// ─── WEB AUDIO — renderMaster ─────────────────────────────────────────────────
async function renderMaster(source: AudioBuffer, macros: Macros, msEnabled: boolean): Promise<AudioBuffer> {
  const sr = source.sampleRate, len = source.length, nCh = source.numberOfChannels
  const ctx = new OfflineAudioContext(nCh, len, sr)
  const src = ctx.createBufferSource(); src.buffer = source

  const highShelf = ctx.createBiquadFilter()
  highShelf.type = 'highshelf'; highShelf.frequency.value = 10000
  highShelf.gain.value = (macros.brighten / 100) * 4

  const lowShelf = ctx.createBiquadFilter()
  lowShelf.type = 'lowshelf'; lowShelf.frequency.value = 200
  lowShelf.gain.value = (macros.warmth / 100) * 4

  const compressor = ctx.createDynamicsCompressor()
  compressor.ratio.value = 1.5 + (macros.glue / 100) * 2.5
  compressor.threshold.value = -18 + (macros.glue / 100) * 12
  compressor.knee.value = 6; compressor.attack.value = 0.03; compressor.release.value = 0.12

  const k = (macros.punch / 100) * 3.0
  const wsCurve = new Float32Array(1024)
  for (let i = 0; i < 1024; i++) {
    const x = (i / 512) - 1
    wsCurve[i] = k > 0 ? x / (1 + Math.abs(x) * k) : x
  }
  const waveshaper = ctx.createWaveShaper(); waveshaper.curve = wsCurve

  const limiter = ctx.createDynamicsCompressor()
  limiter.threshold.value = -0.3; limiter.ratio.value = 20
  limiter.knee.value = 0; limiter.attack.value = 0.001; limiter.release.value = 0.05

  const loudnessGain = ctx.createGain()
  loudnessGain.gain.value = Math.pow(10, ((macros.loudness - 75) / 100) * 6 / 20)

  src.connect(lowShelf)
  lowShelf.connect(highShelf)
  highShelf.connect(compressor)
  compressor.connect(waveshaper)
  waveshaper.connect(loudnessGain)
  loudnessGain.connect(limiter)
  limiter.connect(ctx.destination)
  src.start(0)
  return ctx.startRendering()
}

function encodeWAV(buffer: AudioBuffer, bitDepth: 16 | 24 = 24): ArrayBuffer {
  const sr = buffer.sampleRate, nCh = buffer.numberOfChannels, nSamples = buffer.length
  const bytesPerSample = bitDepth / 8
  const dataSize = nSamples * nCh * bytesPerSample
  const ab = new ArrayBuffer(44 + dataSize)
  const view = new DataView(ab)
  const writeStr = (off: number, s: string) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)) }
  writeStr(0, 'RIFF'); view.setUint32(4, 36 + dataSize, true); writeStr(8, 'WAVE')
  writeStr(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true)
  view.setUint16(22, nCh, true); view.setUint32(24, sr, true)
  view.setUint32(28, sr * nCh * bytesPerSample, true)
  view.setUint16(32, nCh * bytesPerSample, true); view.setUint16(34, bitDepth, true)
  writeStr(36, 'data'); view.setUint32(40, dataSize, true)
  const channels = Array.from({ length: nCh }, (_, i) => buffer.getChannelData(i))
  let offset = 44
  for (let i = 0; i < nSamples; i++) {
    for (let c = 0; c < nCh; c++) {
      const s = Math.max(-1, Math.min(1, channels[c][i]))
      if (bitDepth === 24) {
        const v = Math.round(s * 8388607)
        view.setUint8(offset, v & 0xFF); view.setUint8(offset + 1, (v >> 8) & 0xFF); view.setUint8(offset + 2, (v >> 16) & 0xFF)
        offset += 3
      } else {
        const dither = (Math.random() - Math.random()) * (1 / 32768)
        view.setInt16(offset, Math.round((s + dither) * 32767), true); offset += 2
      }
    }
  }
  return ab
}

// ─── MAIN AURORA COMPONENT ────────────────────────────────────────────────────
const DEFAULT_META: TrackMetadata = { title: '', artist: '', album: '', year: new Date().getFullYear().toString(), genre: '', isrc: '', label: 'ThatGuy Productions', publisher: 'SAMRO', coverArt: undefined }
const DEFAULT_VINYL: VinylConfig = { riaa: true, monoFoldHz: 120, sibilanceLimitDb: -3, sideAMins: 18, sideBMins: 18 }

export default function Aurora() {
  // ── Audio
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [audioBuffer, setAudioBuffer] = useState<AudioBuffer | null>(null)
  const [masterBuffer, setMasterBuffer] = useState<AudioBuffer | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackPos, setPlaybackPos] = useState(0)
  const [processing, setProcessing] = useState(false)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const sourceNodeRef = useRef<AudioBufferSourceNode | null>(null)
  const posTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const vuTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Macros
  const [macros, setMacros] = useSessionState<Macros>('macros', { loudness: 75, warmth: 50, brighten: 50, punch: 60, glue: 55 })
  const setMacro = (k: keyof Macros) => (v: number) => setMacros(m => ({ ...m, [k]: v }))

  // ── Signal chain
  const [hardwareModel, setHardwareModel] = useSessionState<HardwareModel>('hw', 'ssl_g')
  const [msEnabled, setMsEnabled] = useSessionState('ms', true)
  const [microDrift, setMicroDrift] = useSessionState('drift', false)

  // ── Stems
  const [stems, setStems] = useState<StemData[]>([])
  const [stemGains, setStemGains] = useSessionState<Partial<Record<StemName, number>>>('stemGains', {})
  const [conflicts, setConflicts] = useState<ConflictMatrix>({})
  const [stemJobId, setStemJobId] = useState<string | null>(null)
  const [stemProgress, setStemProgress] = useState(0)
  const [stemStatus, setStemStatus] = useState('')
  const [demucsModel, setDemucsModel] = useSessionState('demucsModel', 'htdemucs_ft')

  // ── Spatial
  const [atmosEnabled, setAtmosEnabled] = useSessionState('atmos', false)
  const [spatialPositions, setSpatialPositions] = useSessionState<SpatialPosition[]>('spatial', [])

  // ── QC
  const [qcResults, setQcResults] = useState<QCResult[]>([])

  // ── Collab
  const [chatHistory, setChatHistory] = useState<ChatMsg[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [thinkingText, setThinkingText] = useState('')
  const [sessionNotes, setSessionNotes] = useSessionState('notes', '')
  const [sessionId] = useState(() => crypto.randomUUID())
  const chatEndRef = useRef<HTMLDivElement>(null)

  // ── Album
  const [albumTracks, setAlbumTracks] = useSessionState<AlbumTrack[]>('album', [])
  const [batchJobId, setBatchJobId] = useState<string | null>(null)
  const [batchProgress, setBatchProgress] = useState(0)
  const [batchLog, setBatchLog] = useState<string[]>([])
  const [coherenceReport, setCoherenceReport] = useState<Record<string, unknown> | null>(null)
  const batchLogRef = useRef<HTMLDivElement>(null)

  // ── Export
  const [exportFormats, setExportFormats] = useSessionState<ExportFormat[]>('formats', ['wav_24_48'])
  const [vinylConfig, setVinylConfig] = useSessionState<VinylConfig>('vinyl', DEFAULT_VINYL)
  const [metadata, setMetadata] = useSessionState<TrackMetadata>('meta', DEFAULT_META)
  const [exportLinks, setExportLinks] = useState<Record<string, string>>({})
  const [exporting, setExporting] = useState(false)

  // ── UI
  const [tab, setTab] = useSessionState<string>('tab', 'master')
  const [backendOnline, setBackendOnline] = useState(false)
  const [capabilities, setCapabilities] = useState<Record<string, boolean>>({})
  const [vuLeft, setVuLeft] = useState(0)
  const [vuRight, setVuRight] = useState(0)
  const [vuPeakL, setVuPeakL] = useState(0)
  const [vuPeakR, setVuPeakR] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [diagTime, setDiagTime] = useState<string | null>(null)
  const dropRef = useRef<HTMLDivElement>(null)
  const [dragOver, setDragOver] = useState(false)

  // ── Health check
  useEffect(() => {
    const check = async () => {
      try {
        const h = await api.get<{ status: string; capabilities: Record<string, boolean> }>('/health')
        setBackendOnline(h.status === 'ok')
        setCapabilities(h.capabilities || {})
        setDiagTime(new Date().toLocaleTimeString())
      } catch { setBackendOnline(false) }
    }
    check()
    const iv = setInterval(check, 30000)
    return () => clearInterval(iv)
  }, [])

  // ── Load audio file
  const loadAudio = useCallback(async (file: File) => {
    setAudioFile(file)
    setError(null)
    try {
      const ab = await file.arrayBuffer()
      const ctx = new AudioContext()
      const buf = await ctx.decodeAudioData(ab)
      ctx.close()
      setAudioBuffer(buf)
      setMasterBuffer(null)
      setAnalysis(null)
      setQcResults([])
      if (backendOnline) {
        try {
          const result = await api.upload<AnalysisResult>('/analyze-audio', file)
          setAnalysis(result)
          if (result.platform_scores) {
            // Analysis loaded
          }
        } catch {}
      }
    } catch (e) { setError(`Failed to load audio: ${e}`) }
  }, [backendOnline])

  // ── Drop zone
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f && f.type.startsWith('audio/')) loadAudio(f)
  }, [loadAudio])

  // ── Playback
  const togglePlay = useCallback(() => {
    const buf = masterBuffer || audioBuffer
    if (!buf) return
    if (isPlaying) {
      sourceNodeRef.current?.stop()
      if (posTimerRef.current) clearInterval(posTimerRef.current)
      if (vuTimerRef.current) clearInterval(vuTimerRef.current)
      setIsPlaying(false)
    } else {
      if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') audioCtxRef.current = new AudioContext()
      const ctx = audioCtxRef.current
      const src = ctx.createBufferSource(); src.buffer = buf
      const analyser = ctx.createAnalyser(); analyser.fftSize = 1024
      analyserRef.current = analyser
      src.connect(analyser); analyser.connect(ctx.destination)
      sourceNodeRef.current = src
      const startTime = ctx.currentTime
      src.start(0)
      src.onended = () => { setIsPlaying(false); setPlaybackPos(0); if (posTimerRef.current) clearInterval(posTimerRef.current) }
      setIsPlaying(true)
      posTimerRef.current = setInterval(() => setPlaybackPos((ctx.currentTime - startTime) / buf.duration), 50)
      const dataL = new Uint8Array(analyser.frequencyBinCount)
      vuTimerRef.current = setInterval(() => {
        analyser.getByteTimeDomainData(dataL)
        let maxL = 0
        for (let i = 0; i < dataL.length; i++) { const v = Math.abs(dataL[i] - 128) / 128; if (v > maxL) maxL = v }
        setVuLeft(prev => Math.max(prev * 0.9, maxL))
        setVuRight(prev => Math.max(prev * 0.9, maxL * 0.95))
        setVuPeakL(prev => Math.max(prev * 0.998, maxL))
        setVuPeakR(prev => Math.max(prev * 0.998, maxL * 0.95))
      }, 32)
    }
  }, [isPlaying, masterBuffer, audioBuffer])

  // ── Run Aurora
  const runAurora = useCallback(async () => {
    if (!audioBuffer) return
    setProcessing(true); setError(null)
    try {
      if (backendOnline) {
        const formData = new FormData()
        if (audioFile) formData.append('file', audioFile)
        formData.append('macros', JSON.stringify(macros))
        formData.append('hardware_model', hardwareModel)
        formData.append('ms_enabled', String(msEnabled))
        formData.append('micro_drift', String(microDrift))
        try {
          const res = await api.upload<AnalysisResult>('/master', audioFile!, { macros: JSON.stringify(macros), hardware_model: hardwareModel, ms_enabled: String(msEnabled), micro_drift: String(microDrift) })
          setAnalysis(res)
          if (res.platform_scores) {
            // pss handled via analysis
          }
        } catch {}
      }
      const processed = await renderMaster(audioBuffer, macros, msEnabled)
      setMasterBuffer(processed)
    } catch (e) { setError(String(e)) }
    finally { setProcessing(false) }
  }, [audioBuffer, audioFile, backendOnline, macros, hardwareModel, msEnabled, microDrift])

  // ── Extract stems
  const extractStems = useCallback(async () => {
    if (!audioFile) return
    setStemProgress(0); setStemStatus('Starting...')
    try {
      const { job_id } = await api.upload<{ job_id: string }>('/extract-stems', audioFile, { model: demucsModel })
      setStemJobId(job_id)
      const result = await api.pollJob(job_id, (p, msg) => { setStemProgress(p); setStemStatus(msg) }) as { stems: StemData[]; conflicts: ConflictMatrix }
      if (result.stems) setStems(result.stems)
      if (result.conflicts) setConflicts(result.conflicts)
      setStemStatus('Done')
    } catch (e) { setStemStatus(`Error: ${e}`); setStemJobId(null) }
  }, [audioFile, demucsModel])

  // ── Send chat
  const sendChat = useCallback(() => {
    if (!chatInput.trim() || chatLoading) return
    const msg = chatInput.trim(); setChatInput('')
    const userMsg: ChatMsg = { role: 'user', content: msg, timestamp: Date.now() }
    setChatHistory(h => [...h, userMsg])
    setChatLoading(true); setThinkingText('')
    let aiContent = ''
    const aiMsg: ChatMsg = { role: 'assistant', content: '', timestamp: Date.now() }
    setChatHistory(h => [...h, aiMsg])
    if (backendOnline) {
      api.streamChat(sessionId, msg, macros,
        (d) => setThinkingText(t => t + d),
        (d) => {
          aiContent += d
          setChatHistory(h => h.map((m, i) => i === h.length - 1 ? { ...m, content: aiContent } : m))
        },
        (params) => {
          setChatLoading(false); setThinkingText('')
          if (params) setChatHistory(h => h.map((m, i) => i === h.length - 1 ? { ...m, params, thinking: thinkingText || undefined } : m))
        },
        (e) => { setChatLoading(false); setChatHistory(h => h.map((m, i) => i === h.length - 1 ? { ...m, content: `Error: ${e}` } : m)) }
      )
    } else {
      setTimeout(() => {
        const words = msg.toLowerCase()
        const p: Partial<Macros> = {}
        if (words.includes('warm')) p.warmth = 70
        if (words.includes('bright') || words.includes('crisp')) p.brighten = 70
        if (words.includes('loud')) p.loudness = 85
        if (words.includes('punch')) p.punch = 80
        if (words.includes('glue') || words.includes('tight')) p.glue = 75
        const reply = `[Offline mode] Based on your request, I suggest: ${Object.entries(p).map(([k, v]) => `${k}→${v}`).join(', ') || 'no changes detected'}.`
        setChatHistory(h => h.map((m, i) => i === h.length - 1 ? { ...m, content: reply, params: Object.keys(p).length ? p : undefined } : m))
        setChatLoading(false)
      }, 600)
    }
  }, [chatInput, chatLoading, backendOnline, sessionId, macros, thinkingText])

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatHistory])
  useEffect(() => { if (batchLogRef.current) batchLogRef.current.scrollTop = batchLogRef.current.scrollHeight }, [batchLog])

  const pss = analysis?.platform_scores || {}
  const lufsTarget = -20 + (macros.loudness / 100) * 14
  const hwLabels: Record<HardwareModel, string> = { ssl_g: 'SSL G-Bus', api_2500: 'API 2500', neve_8078: 'Neve 8078', chandler_tg1: 'Chandler TG1', tube_tech: 'Tube-Tech CL 1B' }

  // ─── TAB: MASTER ─────────────────────────────────────────────────────────────
  const TabMaster = () => (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, height: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl style={{ padding: 0 }}>
          <div ref={dropRef} onDrop={handleDrop} onDragOver={e => { e.preventDefault(); setDragOver(true) }} onDragLeave={() => setDragOver(false)}
            onClick={() => { const i = document.createElement('input'); i.type = 'file'; i.accept = 'audio/*'; i.onchange = e => { const f = (e.target as HTMLInputElement).files?.[0]; if (f) loadAudio(f) }; i.click() }}
            style={{ padding: 20, border: `2px dashed ${dragOver ? T.accent : T.border}`, borderRadius: T.rM, cursor: 'pointer', textAlign: 'center', transition: 'border-color 0.2s', minHeight: 90 }}>
            {audioFile ? (
              <div>
                <div style={{ fontFamily: T.mono, fontSize: 12, color: T.accent }}>{audioFile.name}</div>
                <div style={{ fontFamily: T.mono, fontSize: 10, color: T.sub, marginTop: 4 }}>{audioBuffer ? `${audioBuffer.numberOfChannels}ch · ${(audioBuffer.sampleRate / 1000).toFixed(1)}kHz · ${audioBuffer.duration.toFixed(1)}s` : ''}</div>
              </div>
            ) : (
              <div>
                <div style={{ fontFamily: T.display, fontSize: 22, color: T.dim, letterSpacing: '0.1em' }}>DROP AUDIO FILE</div>
                <div style={{ fontFamily: T.mono, fontSize: 10, color: T.dim, marginTop: 4 }}>or click to browse · WAV / AIFF / MP3 / FLAC</div>
              </div>
            )}
          </div>
          <div style={{ padding: '0 12px 12px' }}>
            <Waveform buffer={audioBuffer} playbackPos={playbackPos} processing={processing} height={72} />
          </div>
        </Pnl>
        <Pnl>
          <Row style={{ justifyContent: 'space-between', marginBottom: 10 }}>
            <Hd style={{ marginBottom: 0 }}>Levels</Hd>
            <Row gap={8}>
              <Btn onClick={togglePlay} disabled={!audioBuffer} style={{ minWidth: 70 }}>
                {isPlaying ? '⏹ STOP' : '▶ PLAY'}
              </Btn>
            </Row>
          </Row>
          <Row gap={16} style={{ justifyContent: 'space-between' }}>
            <VUMeter left={vuLeft} right={vuRight} peakL={vuPeakL} peakR={vuPeakR} height={100} />
            <div style={{ flex: 1 }}>
              {analysis ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <InfoRow label="LUFS INT" value={`${analysis.lufs_integrated?.toFixed(1)} LU`} color={Math.abs(analysis.lufs_integrated + 14) < 2 ? T.cyan : T.orange} />
                  <InfoRow label="TRUE PEAK" value={`${analysis.true_peak?.toFixed(1)} dBTP`} color={analysis.true_peak > -0.5 ? T.red : T.cyan} />
                  <InfoRow label="DYN RANGE" value={`DR${Math.round(analysis.dynamic_range || 0)}`} />
                  <InfoRow label="LRA" value={`${analysis.lra?.toFixed(1)} LU`} />
                  <InfoRow label="PHASE" value={analysis.phase_correlation?.toFixed(2)} color={analysis.phase_correlation < 0.1 ? T.orange : T.cyan} />
                </div>
              ) : (
                <div style={{ fontFamily: T.mono, fontSize: 10, color: T.dim, textAlign: 'center', paddingTop: 20 }}>Run Aurora to see analysis</div>
              )}
            </div>
          </Row>
        </Pnl>
        <Pnl>
          <Hd>Platform Survival Score</Hd>
          <Row gap={8} style={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
            {(['spotify', 'apple_music', 'youtube', 'tiktok', 'club_system'] as const).map(p => (
              <Ring key={p} value={pss[p] || 0} label={p === 'apple_music' ? 'Apple' : p === 'club_system' ? 'Club' : p.charAt(0).toUpperCase() + p.slice(1)} size={72} color={pss[p] > 75 ? T.cyan : pss[p] > 50 ? T.orange : T.red} />
            ))}
          </Row>
        </Pnl>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl>
          <Row style={{ justifyContent: 'space-between', marginBottom: 12 }}>
            <Hd style={{ marginBottom: 0 }}>Macros</Hd>
            <Row gap={6}>
              <LED on={backendOnline} color={T.cyan} />
              <span style={{ fontFamily: T.mono, fontSize: 9, color: backendOnline ? T.cyan : T.dim }}>{backendOnline ? 'BACKEND ONLINE' : 'WEB AUDIO FALLBACK'}</span>
            </Row>
          </Row>
          <Row gap={16} style={{ justifyContent: 'space-around', flexWrap: 'wrap' }}>
            <Knob value={macros.loudness} onChange={setMacro('loudness')} label="Loudness" color={T.accent} />
            <Knob value={macros.warmth} onChange={setMacro('warmth')} label="Warmth" color={T.cyan} />
            <Knob value={macros.brighten} onChange={setMacro('brighten')} label="Brighten" color={T.accent} />
            <Knob value={macros.punch} onChange={setMacro('punch')} label="Punch" color={T.orange} />
            <Knob value={macros.glue} onChange={setMacro('glue')} label="Glue" color={T.purple} />
          </Row>
          <Divider style={{ margin: '12px 0' }} />
          <Row style={{ justifyContent: 'space-between' }}>
            <Lbl>LUFS TARGET</Lbl>
            <Val>{lufsTarget.toFixed(1)} LUFS</Val>
          </Row>
        </Pnl>
        <Pnl>
          <Hd>Signal Chain</Hd>
          <div style={{ marginBottom: 12 }}>
            <Lbl>HARDWARE MODEL</Lbl>
            <Row gap={6} style={{ marginTop: 6, flexWrap: 'wrap' }}>
              {(Object.keys(hwLabels) as HardwareModel[]).map(hw => (
                <button key={hw} onClick={() => setHardwareModel(hw)} style={{
                  fontFamily: T.mono, fontSize: 10, padding: '4px 10px', borderRadius: T.r,
                  background: hardwareModel === hw ? T.accent : T.panelAlt, color: hardwareModel === hw ? T.bg : T.sub,
                  border: `1px solid ${hardwareModel === hw ? T.accent : T.border}`, cursor: 'pointer'
                }}>{hwLabels[hw]}</button>
              ))}
            </Row>
          </div>
          <Row style={{ justifyContent: 'space-between', marginBottom: 8 }}>
            <Tog value={msEnabled} onChange={setMsEnabled} label="Mid/Side Processing" />
          </Row>
          <Row style={{ justifyContent: 'space-between' }}>
            <Tog value={microDrift} onChange={setMicroDrift} label="Analog Micro-drift" />
          </Row>
        </Pnl>
        {error && (
          <div style={{ background: T.red + '20', border: `1px solid ${T.red}`, borderRadius: T.r, padding: '8px 12px', fontFamily: T.mono, fontSize: 11, color: T.red }}>{error}</div>
        )}
        <button onClick={runAurora} disabled={!audioBuffer || processing} style={{
          fontFamily: T.display, fontSize: 22, letterSpacing: '0.15em', padding: '14px 0', width: '100%',
          background: processing ? T.border : T.accent, color: T.bg, border: 'none', borderRadius: T.rM,
          cursor: audioBuffer && !processing ? 'pointer' : 'not-allowed', opacity: audioBuffer ? 1 : 0.4,
          transition: 'all 0.2s',
        }}>
          {processing ? '⟳ PROCESSING...' : '▶ RUN AURORA'}
        </button>
        {masterBuffer && (
          <Btn onClick={() => {
            const wav = encodeWAV(masterBuffer, 24)
            const url = URL.createObjectURL(new Blob([wav], { type: 'audio/wav' }))
            const a = document.createElement('a'); a.href = url; a.download = `${metadata.title || 'aurora_master'}_MASTER.wav`; a.click()
          }} variant="primary">⬇ DOWNLOAD MASTER WAV</Btn>
        )}
      </div>
    </div>
  )

  // ─── TAB: STEMS ─────────────────────────────────────────────────────────────
  const ALL_STEMS: StemName[] = ['vocals', 'lead_vox', 'harmonies', 'bass', 'kick', 'snare', 'cymbals', 'drums', 'guitar', 'piano', 'strings', 'other']
  const TabStems = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Pnl>
        <Row style={{ justifyContent: 'space-between' }}>
          <Row gap={12}>
            <Hd style={{ marginBottom: 0 }}>Stem Extraction</Hd>
            <select value={demucsModel} onChange={e => setDemucsModel(e.target.value)} style={{ fontFamily: T.mono, fontSize: 11, background: T.panelAlt, color: T.text, border: `1px solid ${T.border}`, borderRadius: T.r, padding: '4px 8px' }}>
              <option value="htdemucs_ft">htdemucs_ft (recommended)</option>
              <option value="htdemucs_6s">htdemucs_6s</option>
              <option value="htdemucs">htdemucs</option>
              <option value="mdx_extra">mdx_extra</option>
            </select>
          </Row>
          <Btn onClick={extractStems} disabled={!audioFile || !backendOnline || !!stemJobId} variant="primary">EXTRACT STEMS</Btn>
        </Row>
        {stemJobId && (
          <div style={{ marginTop: 10 }}>
            <Row style={{ justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontFamily: T.mono, fontSize: 10, color: T.sub }}>{stemStatus}</span>
              <span style={{ fontFamily: T.mono, fontSize: 10, color: T.accent }}>{stemProgress}%</span>
            </Row>
            <div style={{ height: 4, background: T.border, borderRadius: 2 }}>
              <div style={{ height: '100%', width: `${stemProgress}%`, background: T.accent, borderRadius: 2, transition: 'width 0.3s' }} />
            </div>
          </div>
        )}
      </Pnl>
      <Grid cols={3} gap={10}>
        {ALL_STEMS.map(name => {
          const s = stems.find(st => st.name === name)
          const gain = stemGains[name] ?? 0
          const color = STEM_COLORS[name] || T.sub
          return (
            <Pnl key={name} style={{ padding: 12 }}>
              <Row style={{ justifyContent: 'space-between', marginBottom: 6 }}>
                <Row gap={6}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                  <span style={{ fontFamily: T.mono, fontSize: 11, color: T.text, textTransform: 'uppercase' }}>{name.replace('_', ' ')}</span>
                </Row>
                {s && <Badge>{s.confidence}%</Badge>}
              </Row>
              {s && (
                <div style={{ marginBottom: 6 }}>
                  <div style={{ height: 3, background: T.border, borderRadius: 1, marginBottom: 4 }}>
                    <div style={{ height: '100%', width: `${s.confidence}%`, background: color, borderRadius: 1 }} />
                  </div>
                </div>
              )}
              <Spectrum active={processing} bars={16} height={32} color={color} />
              <div style={{ marginTop: 8 }}>
                <InfoRow label="GAIN" value={`${gain > 0 ? '+' : ''}${gain.toFixed(1)} dB`} />
                <input type="range" min={-12} max={12} step={0.5} value={gain}
                  onChange={e => setStemGains(g => ({ ...g, [name]: parseFloat(e.target.value) }))}
                  style={{ width: '100%', accentColor: color, marginTop: 4 }} />
              </div>
              {s?.downloadUrl && (
                <a href={s.downloadUrl} download style={{ fontFamily: T.mono, fontSize: 10, color: T.accent, textDecoration: 'underline', display: 'block', marginTop: 6 }}>⬇ Download</a>
              )}
            </Pnl>
          )
        })}
      </Grid>
      {Object.keys(conflicts).length > 0 && (
        <Pnl>
          <Hd>Conflict Matrix</Hd>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', fontFamily: T.mono, fontSize: 9 }}>
              <thead>
                <tr>
                  <td style={{ padding: '2px 6px', color: T.dim }} />
                  {ALL_STEMS.map(n => <th key={n} style={{ padding: '2px 4px', color: T.sub, fontWeight: 400, writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: 50 }}>{n.replace('_', ' ')}</th>)}
                </tr>
              </thead>
              <tbody>
                {ALL_STEMS.map(a => (
                  <tr key={a}>
                    <td style={{ padding: '2px 6px', color: T.sub, whiteSpace: 'nowrap' }}>{a.replace('_', ' ')}</td>
                    {ALL_STEMS.map(b => {
                      const score = conflicts[a]?.[b] || 0
                      return <td key={b} style={{ width: 20, height: 20, background: `rgba(255,77,107,${score})`, border: `1px solid ${T.border}` }} title={`${score.toFixed(2)}`} />
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Pnl>
      )}
    </div>
  )

  // ─── TAB: SPATIAL ────────────────────────────────────────────────────────────
  const TabSpatial = () => {
    const atmosChecks = [
      { label: '7.1.4 bed assigned', ok: stems.length >= 4 },
      { label: '48 kHz / 24-bit', ok: audioBuffer?.sampleRate === 48000 },
      { label: 'Target −18 LUFS (TuneCore)', ok: analysis ? Math.abs(analysis.lufs_integrated + 18) < 2 : false },
      { label: '−1.0 dBTP ceiling', ok: analysis ? analysis.true_peak <= -1.0 : false },
      { label: 'ADM XML (BS.2076-2)', ok: false },
      { label: 'chna chunk valid', ok: false },
    ]
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Pnl>
            <Row style={{ justifyContent: 'space-between', marginBottom: 12 }}>
              <Hd style={{ marginBottom: 0 }}>Dolby Atmos</Hd>
              <Tog value={atmosEnabled} onChange={setAtmosEnabled} label="Enable Dolby Atmos" />
            </Row>
            {stems.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 300, overflowY: 'auto' }}>
                {stems.map(stem => {
                  const pos = spatialPositions.find(p => p.stem === stem.name) ?? { stem: stem.name, x: 0, y: 0, elevation: 0.5, distance: 0.5 }
                  const update = (field: 'elevation' | 'distance', val: number) => {
                    setSpatialPositions(ps => ps.filter(p => p.stem !== stem.name).concat([{ ...pos, [field]: val }]))
                  }
                  return (
                    <div key={stem.name} style={{ background: T.panelAlt, borderRadius: T.r, padding: '8px 12px' }}>
                      <Row style={{ justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontFamily: T.mono, fontSize: 11, color: STEM_COLORS[stem.name] || T.text }}>{stem.name.replace('_', ' ').toUpperCase()}</span>
                      </Row>
                      <Row gap={12}>
                        <div style={{ flex: 1 }}><Lbl>ELEVATION</Lbl><input type="range" min={0} max={1} step={0.01} value={pos.elevation} onChange={e => update('elevation', parseFloat(e.target.value))} style={{ width: '100%', accentColor: T.cyan, marginTop: 2 }} /></div>
                        <div style={{ flex: 1 }}><Lbl>DISTANCE</Lbl><input type="range" min={0} max={1} step={0.01} value={pos.distance} onChange={e => update('distance', parseFloat(e.target.value))} style={{ width: '100%', accentColor: T.purple, marginTop: 2 }} /></div>
                      </Row>
                    </div>
                  )
                })}
              </div>
            ) : <div style={{ fontFamily: T.mono, fontSize: 10, color: T.dim, textAlign: 'center', padding: 20 }}>Extract stems first to configure spatial routing</div>}
          </Pnl>
          <Pnl>
            <Hd>ADM BWF QC Checklist</Hd>
            {atmosChecks.map(c => (
              <Row key={c.label} gap={8} style={{ padding: '5px 0' }}>
                <span style={{ color: c.ok ? T.cyan : T.dim, fontSize: 14 }}>{c.ok ? '☑' : '☐'}</span>
                <span style={{ fontFamily: T.mono, fontSize: 11, color: c.ok ? T.text : T.sub }}>{c.label}</span>
              </Row>
            ))}
            <div style={{ marginTop: 10, fontFamily: T.mono, fontSize: 10, color: T.orange }}>⚠ DistroKid does not accept ADM BWF. Use TuneCore for Atmos delivery.</div>
            <div style={{ marginTop: 10 }}>
              <Btn disabled={!atmosEnabled || stems.length === 0} variant="primary" onClick={async () => {
                try {
                  const r = await api.post<{ download_url: string }>('/render-atmos', { positions: spatialPositions, session_id: sessionId })
                  if (r.download_url) window.open(r.download_url)
                } catch (e) { setError(String(e)) }
              }}>RENDER ATMOS ADM BWF</Btn>
            </div>
          </Pnl>
        </div>
        <div>
          <Pnl style={{ padding: 12 }}>
            <Hd>Overhead View</Hd>
            <SpatialPanner stems={stems.length > 0 ? stems : ALL_STEMS.slice(0, 6).map(n => ({ name: n, confidence: 0, rms: -40, peak: -30 }))} positions={spatialPositions} onChange={setSpatialPositions} size={356} />
          </Pnl>
        </div>
      </div>
    )
  }

  // ─── TAB: QC ─────────────────────────────────────────────────────────────────
  const QC_DEFS = [
    { id: 'clip',       label: 'Digital Clipping',        auto_fix: true },
    { id: 'intersample',label: 'Inter-sample Peaks',       auto_fix: true },
    { id: 'phase',      label: 'Phase Cancellation',       auto_fix: true },
    { id: 'codec_ring', label: 'Codec Pre-ring (OGG/AAC)', auto_fix: false },
    { id: 'pops',       label: 'Pops & Clicks',           auto_fix: false },
    { id: 'edits',      label: 'Bad Edits / Glitches',    auto_fix: false },
    { id: 'dc',         label: 'DC Offset',               auto_fix: true },
    { id: 'silence',    label: 'Silence Detection',       auto_fix: false },
    { id: 'samplerate', label: 'Sample Rate',             auto_fix: false },
    { id: 'bitdepth',   label: 'Bit Depth',               auto_fix: false },
  ]
  const TabQC = () => {
    const passed = qcResults.filter(r => r.status === 'PASS').length
    const failed = qcResults.filter(r => r.status === 'FAIL').length
    const warns  = qcResults.filter(r => r.status === 'WARN').length
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl>
          <Row style={{ justifyContent: 'space-between' }}>
            <Row gap={10}>
              <Hd style={{ marginBottom: 0 }}>QC Report</Hd>
              {qcResults.length > 0 && (
                <Row gap={8}>
                  <Badge status="PASS">PASS {passed}</Badge>
                  {failed > 0 && <Badge status="FAIL">FAIL {failed}</Badge>}
                  {warns > 0 && <Badge status="WARN">WARN {warns}</Badge>}
                </Row>
              )}
            </Row>
            <Btn onClick={async () => {
              if (!audioFile) return
              try {
                const r = await api.upload<{ results: QCResult[] }>('/analyze-audio', audioFile)
                if ((r as Record<string,unknown>).qc_results) setQcResults((r as {qc_results: QCResult[]}).qc_results)
              } catch { setError('QC analysis requires backend') }
            }} disabled={!audioFile || !backendOnline}>RUN QC</Btn>
          </Row>
        </Pnl>
        <Grid cols={2} gap={10}>
          {QC_DEFS.map(def => {
            const result = qcResults.find(r => r.id === def.id)
            const status = result?.status || 'PASS'
            const statusColor: Record<QCStatus, string> = { PASS: T.cyan, FAIL: T.red, WARN: T.orange, FIX: T.purple }
            return (
              <Pnl key={def.id} style={{ padding: 12, borderLeft: `3px solid ${statusColor[status]}` }}>
                <Row style={{ justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontFamily: T.mono, fontSize: 12, color: T.text }}>{def.label}</span>
                  <Badge status={status}>{status}</Badge>
                </Row>
                {result ? (
                  <>
                    <div style={{ fontFamily: T.mono, fontSize: 10, color: T.sub, marginBottom: 4 }}>{result.detail}</div>
                    {result.value !== undefined && <Val color={statusColor[status]}>{result.value.toFixed(2)}</Val>}
                    {result.auto_fix_available && result.status !== 'PASS' && (
                      <Btn style={{ marginTop: 8 }} onClick={async () => {
                        try {
                          await api.post('/qc-fix', { issue_id: def.id, session_id: sessionId })
                          setQcResults(rs => rs.map(r => r.id === def.id ? { ...r, remediated: true, status: 'PASS' } : r))
                        } catch {}
                      }}>AUTO-FIX</Btn>
                    )}
                  </>
                ) : <div style={{ fontFamily: T.mono, fontSize: 10, color: T.dim }}>Run QC to analyze</div>}
              </Pnl>
            )
          })}
        </Grid>
      </div>
    )
  }

  // ─── TAB: COLLAB ─────────────────────────────────────────────────────────────
  const TabCollab = () => (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 16, height: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
        <Pnl>
          <Hd>Genre Presets</Hd>
          <Row gap={6} style={{ flexWrap: 'wrap' }}>
            {(Object.keys(GENRE_PRESETS) as GenrePreset[]).map(g => (
              <button key={g} onClick={() => setMacros(GENRE_PRESETS[g])} style={{
                fontFamily: T.mono, fontSize: 10, padding: '5px 12px', borderRadius: T.r,
                background: T.panelAlt, border: `1px solid ${T.borderHi}`, color: T.sub,
                cursor: 'pointer', letterSpacing: '0.06em'
              }}>{GENRE_LABELS[g]}</button>
            ))}
          </Row>
        </Pnl>
        <Pnl style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <Hd>AI Mastering Assistant</Hd>
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10, paddingRight: 4, marginBottom: 12, minHeight: 200 }}>
            {chatHistory.length === 0 && (
              <div style={{ textAlign: 'center', padding: '30px 0', fontFamily: T.mono, fontSize: 11, color: T.dim }}>
                Describe what you want — "make it warmer", "radio ready", "needs more punch"
              </div>
            )}
            {chatHistory.map((msg, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                {msg.thinking && (
                  <div style={{ maxWidth: '80%', background: T.panelAlt, border: `1px solid ${T.dim}`, borderRadius: T.r, padding: '6px 10px', marginBottom: 4, fontFamily: T.mono, fontSize: 9, color: T.sub, fontStyle: 'italic' }}>
                    🧠 {msg.thinking.slice(0, 120)}...
                  </div>
                )}
                <div style={{
                  maxWidth: '80%', background: msg.role === 'user' ? T.panel : T.panelAlt,
                  borderLeft: `3px solid ${msg.role === 'user' ? T.accent : T.purple}`,
                  borderRadius: T.r, padding: '8px 12px',
                  fontFamily: T.mono, fontSize: 11, color: T.text, lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}>{msg.content}</div>
                {msg.params && Object.keys(msg.params).length > 0 && (
                  <div style={{ maxWidth: '80%', background: T.bg, border: `1px solid ${T.purple}`, borderRadius: T.r, padding: 10, marginTop: 4 }}>
                    <Row style={{ justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontFamily: T.mono, fontSize: 10, color: T.purple, letterSpacing: '0.1em' }}>SUGGESTED CHANGES</span>
                      <Btn style={{ fontSize: 9, padding: '2px 8px' }} onClick={() => setMacros(m => ({ ...m, ...msg.params }))}>APPLY ALL</Btn>
                    </Row>
                    {(Object.entries(msg.params) as [keyof Macros, number][]).map(([k, v]) => (
                      <Row key={k} style={{ justifyContent: 'space-between', padding: '2px 0' }}>
                        <Lbl>{k.toUpperCase()}</Lbl>
                        <Row gap={6}>
                          <Val color={T.sub}>{macros[k]}</Val>
                          <span style={{ color: T.dim }}>→</span>
                          <Val color={T.accent}>{v}</Val>
                          <Btn style={{ fontSize: 9, padding: '1px 6px' }} onClick={() => setMacros(m => ({ ...m, [k]: v }))}>↑</Btn>
                        </Row>
                      </Row>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {chatLoading && thinkingText && (
              <div style={{ fontFamily: T.mono, fontSize: 10, color: T.purple, fontStyle: 'italic', padding: '4px 8px' }}>
                🧠 Thinking... {thinkingText.slice(0, 80)}{thinkingText.length > 80 ? '...' : ''}
              </div>
            )}
            {chatLoading && !thinkingText && (
              <div style={{ fontFamily: T.mono, fontSize: 10, color: T.sub, padding: '4px 8px' }}>Aurora is thinking...</div>
            )}
            <div ref={chatEndRef} />
          </div>
          <Row gap={8}>
            <textarea value={chatInput} onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat() } }}
              placeholder="Describe what you need... (Enter to send)" rows={2}
              style={{ flex: 1, fontFamily: T.mono, fontSize: 11, background: T.panelAlt, border: `1px solid ${T.border}`, borderRadius: T.r, color: T.text, padding: '8px 10px', resize: 'none', outline: 'none' }} />
            <Btn onClick={sendChat} disabled={!chatInput.trim() || chatLoading} variant="primary" style={{ alignSelf: 'flex-end', padding: '8px 16px' }}>SEND</Btn>
          </Row>
        </Pnl>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl>
          <Hd>Session Notes</Hd>
          <textarea value={sessionNotes} onChange={e => setSessionNotes(e.target.value)} placeholder="Track notes, client feedback, revision history..."
            style={{ width: '100%', minHeight: 140, fontFamily: T.mono, fontSize: 11, background: T.panelAlt, border: `1px solid ${T.border}`, borderRadius: T.r, color: T.text, padding: '8px 10px', resize: 'vertical', outline: 'none', lineHeight: 1.6 }} />
        </Pnl>
        <Pnl>
          <Hd>Current Macros</Hd>
          {(Object.entries(macros) as [keyof Macros, number][]).map(([k, v]) => (
            <InfoRow key={k} label={k.toUpperCase()} value={v} />
          ))}
        </Pnl>
      </div>
    </div>
  )

  // ─── TAB: ALBUM ──────────────────────────────────────────────────────────────
  const TabAlbum = () => {
    const addTrack = () => {
      const i = document.createElement('input'); i.type = 'file'; i.accept = 'audio/*'
      i.onchange = async (e) => {
        const f = (e.target as HTMLInputElement).files?.[0]; if (!f) return
        const ctx = new AudioContext()
        const ab = await f.arrayBuffer()
        const buf = await ctx.decodeAudioData(ab); ctx.close()
        const track: AlbumTrack = { id: crypto.randomUUID(), title: f.name.replace(/\.[^.]+$/, ''), artist: metadata.artist, isrc: metadata.isrc, duration: buf.duration, status: 'pending' }
        setAlbumTracks(ts => [...ts, track])
      }; i.click()
    }
    const runBatch = async () => {
      if (albumTracks.length === 0) return
      setBatchProgress(0); setBatchLog([])
      const ts = new Date().toLocaleTimeString
      try {
        const { job_id } = await api.post<{ job_id: string }>('/batch', { tracks: albumTracks, formats: exportFormats, session_id: sessionId })
        setBatchJobId(job_id)
        const result = await api.pollJob(job_id, (p, msg) => {
          setBatchProgress(p)
          setBatchLog(l => [...l, `[${new Date().toLocaleTimeString()}] ${msg}`])
          setAlbumTracks(ts2 => ts2.map(t => p > 50 ? { ...t, status: 'processing' } : t))
        }) as { coherence_report?: Record<string, unknown> }
        if (result.coherence_report) setCoherenceReport(result.coherence_report)
        setAlbumTracks(ts2 => ts2.map(t => ({ ...t, status: 'done' })))
        setBatchLog(l => [...l, `[${new Date().toLocaleTimeString()}] Batch complete!`])
        setBatchJobId(null)
      } catch (e) { setBatchLog(l => [...l, `ERROR: ${e}`]); setBatchJobId(null) }
    }
    const statusColor: Record<AlbumTrack['status'], string> = { pending: T.dim, processing: T.orange, done: T.cyan, error: T.red }
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl>
          <Row style={{ justifyContent: 'space-between', marginBottom: 12 }}>
            <Hd style={{ marginBottom: 0 }}>Album Tracks</Hd>
            <Row gap={8}>
              <Btn onClick={addTrack}>+ ADD TRACK</Btn>
              <Btn onClick={runBatch} disabled={albumTracks.length === 0 || !!batchJobId || !backendOnline} variant="primary">RUN BATCH</Btn>
            </Row>
          </Row>
          {albumTracks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '20px 0', fontFamily: T.mono, fontSize: 11, color: T.dim }}>No tracks added yet. Click + ADD TRACK to begin.</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: T.mono, fontSize: 11 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                    {['#', 'Title', 'Artist', 'ISRC', 'Duration', 'LUFS', 'Status', ''].map(h => (
                      <th key={h} style={{ padding: '6px 8px', color: T.sub, fontWeight: 400, textAlign: 'left', fontSize: 10, letterSpacing: '0.08em' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {albumTracks.map((t, i) => (
                    <tr key={t.id} style={{ borderBottom: `1px solid ${T.border}20` }}>
                      <td style={{ padding: '6px 8px', color: T.dim }}>{i + 1}</td>
                      <td style={{ padding: '6px 8px', color: T.text }}>{t.title}</td>
                      <td style={{ padding: '6px 8px', color: T.sub }}>{t.artist}</td>
                      <td style={{ padding: '6px 8px' }}>
                        <input value={t.isrc} onChange={e => setAlbumTracks(ts => ts.map(x => x.id === t.id ? { ...x, isrc: e.target.value } : x))}
                          placeholder="ZA-TGP-26-NNNNN" style={{ fontFamily: T.mono, fontSize: 10, background: 'transparent', border: `1px solid ${T.border}`, borderRadius: 2, color: T.text, padding: '2px 6px', width: 130 }} />
                      </td>
                      <td style={{ padding: '6px 8px', color: T.sub }}>{t.duration ? `${Math.floor(t.duration / 60)}:${String(Math.floor(t.duration % 60)).padStart(2, '0')}` : '—'}</td>
                      <td style={{ padding: '6px 8px' }}>{t.lufs ? <Val color={T.cyan}>{t.lufs.toFixed(1)}</Val> : <span style={{ color: T.dim }}>—</span>}</td>
                      <td style={{ padding: '6px 8px' }}><Badge>{t.status.toUpperCase()}</Badge></td>
                      <td style={{ padding: '6px 8px' }}><button onClick={() => setAlbumTracks(ts => ts.filter(x => x.id !== t.id))} style={{ background: 'none', border: 'none', color: T.red, cursor: 'pointer', fontFamily: T.mono, fontSize: 12 }}>×</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {batchJobId && (
            <div style={{ marginTop: 12 }}>
              <Row style={{ justifyContent: 'space-between', marginBottom: 4 }}>
                <Lbl>BATCH PROGRESS</Lbl>
                <Val>{batchProgress}%</Val>
              </Row>
              <div style={{ height: 4, background: T.border, borderRadius: 2 }}>
                <div style={{ height: '100%', width: `${batchProgress}%`, background: T.accent, borderRadius: 2, transition: 'width 0.3s' }} />
              </div>
            </div>
          )}
        </Pnl>
        {batchLog.length > 0 && (
          <Pnl>
            <Hd>Batch Log</Hd>
            <div ref={batchLogRef} style={{ background: T.bg, borderRadius: T.r, padding: '10px 12px', height: 160, overflowY: 'auto', fontFamily: T.mono, fontSize: 10, color: T.accent, lineHeight: 1.8 }}>
              {batchLog.map((l, i) => <div key={i}>{l}</div>)}
            </div>
          </Pnl>
        )}
        {coherenceReport && (
          <Pnl>
            <Hd>Album Coherence Report</Hd>
            <InfoRow label="LUFS STD DEV" value={`${(coherenceReport.lufs_std as number)?.toFixed(2) || '—'} LU`} />
            <InfoRow label="LUFS RANGE" value={`${(coherenceReport.lufs_range as number)?.toFixed(1) || '—'} LU`} />
            <InfoRow label="COHERENCE SCORE" value={`${coherenceReport.coherence_score || '—'}/100`} color={((coherenceReport.coherence_score as number) || 0) > 70 ? T.cyan : T.orange} />
            {(coherenceReport.recommendations as string[])?.map((r, i) => (
              <div key={i} style={{ fontFamily: T.mono, fontSize: 10, color: T.orange, marginTop: 4 }}>⚠ {r}</div>
            ))}
          </Pnl>
        )}
      </div>
    )
  }

  // ─── TAB: EXPORT ─────────────────────────────────────────────────────────────
  const FORMAT_LABELS: Record<ExportFormat, string> = {
    wav_24_48: 'WAV 24/48', wav_16_44: 'WAV 16/44', flac_24: 'FLAC 24-bit',
    mp3_320: 'MP3 320kbps', atmos_adm: 'Dolby Atmos ADM', atmos_mp4: 'Atmos MP4',
    ddp: 'DDP 2.0', stem_pack: 'Stem Pack', vinyl: 'Vinyl Pre-master'
  }
  const toggleFormat = (f: ExportFormat) => setExportFormats(fs => fs.includes(f) ? fs.filter(x => x !== f) : [...fs, f])
  const TabExport = () => (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl>
          <Hd>Export Formats</Hd>
          <Grid cols={3} gap={6}>
            {(Object.keys(FORMAT_LABELS) as ExportFormat[]).map(f => (
              <button key={f} onClick={() => toggleFormat(f)} style={{
                fontFamily: T.mono, fontSize: 10, padding: '7px 6px', borderRadius: T.r, textAlign: 'center',
                background: exportFormats.includes(f) ? T.accent : T.panelAlt,
                color: exportFormats.includes(f) ? T.bg : T.sub,
                border: `1px solid ${exportFormats.includes(f) ? T.accent : T.border}`,
                cursor: 'pointer', letterSpacing: '0.04em', lineHeight: 1.4
              }}>{FORMAT_LABELS[f]}</button>
            ))}
          </Grid>
        </Pnl>
        {exportFormats.includes('vinyl') && (
          <Pnl>
            <Hd>Vinyl Chain Config</Hd>
            <Row style={{ justifyContent: 'space-between', marginBottom: 8 }}>
              <Tog value={vinylConfig.riaa} onChange={r => setVinylConfig(c => ({ ...c, riaa: r })) } label="RIAA Curve (IEC 60098)" />
            </Row>
            <div style={{ marginBottom: 8 }}>
              <Lbl>MONO FOLD FREQUENCY</Lbl>
              <Row gap={4} style={{ marginTop: 6 }}>
                {([80, 100, 120, 150] as const).map(f => (
                  <button key={f} onClick={() => setVinylConfig(c => ({ ...c, monoFoldHz: f }))} style={{
                    fontFamily: T.mono, fontSize: 10, padding: '4px 10px', borderRadius: T.r,
                    background: vinylConfig.monoFoldHz === f ? T.accent : T.panelAlt,
                    color: vinylConfig.monoFoldHz === f ? T.bg : T.sub,
                    border: `1px solid ${vinylConfig.monoFoldHz === f ? T.accent : T.border}`, cursor: 'pointer'
                  }}>{f} Hz</button>
                ))}
              </Row>
            </div>
            <div style={{ marginBottom: 8 }}>
              <Lbl>SIBILANCE LIMIT</Lbl>
              <Row gap={6} style={{ marginTop: 6 }}>
                {([-3, -6] as const).map(v => (
                  <button key={v} onClick={() => setVinylConfig(c => ({ ...c, sibilanceLimitDb: v }))} style={{
                    fontFamily: T.mono, fontSize: 10, padding: '4px 10px', borderRadius: T.r,
                    background: vinylConfig.sibilanceLimitDb === v ? T.accent : T.panelAlt,
                    color: vinylConfig.sibilanceLimitDb === v ? T.bg : T.sub,
                    border: `1px solid ${vinylConfig.sibilanceLimitDb === v ? T.accent : T.border}`, cursor: 'pointer'
                  }}>{v} dB</button>
                ))}
              </Row>
            </div>
            <Grid cols={2} gap={10}>
              <div><Lbl>SIDE A (MIN)</Lbl><input type="number" value={vinylConfig.sideAMins} onChange={e => setVinylConfig(c => ({ ...c, sideAMins: parseFloat(e.target.value) }))} style={{ width: '100%', marginTop: 4, fontFamily: T.mono, fontSize: 12, background: T.panelAlt, border: `1px solid ${T.border}`, color: T.text, padding: '4px 8px', borderRadius: T.r }} /></div>
              <div><Lbl>SIDE B (MIN)</Lbl><input type="number" value={vinylConfig.sideBMins} onChange={e => setVinylConfig(c => ({ ...c, sideBMins: parseFloat(e.target.value) }))} style={{ width: '100%', marginTop: 4, fontFamily: T.mono, fontSize: 12, background: T.panelAlt, border: `1px solid ${T.border}`, color: T.text, padding: '4px 8px', borderRadius: T.r }} /></div>
            </Grid>
            {(vinylConfig.sideAMins > 18 || vinylConfig.sideBMins > 18) && (
              <div style={{ fontFamily: T.mono, fontSize: 10, color: T.orange, marginTop: 8 }}>⚠ Exceeds recommended 18 min/side for optimal audio quality</div>
            )}
          </Pnl>
        )}
        <button onClick={async () => {
          if (!masterBuffer && !audioBuffer) return
          setExporting(true)
          const buf = masterBuffer || audioBuffer!
          const links: Record<string, string> = {}
          if (exportFormats.includes('wav_24_48')) {
            const wav = encodeWAV(buf, 24)
            links['wav_24_48'] = URL.createObjectURL(new Blob([wav], { type: 'audio/wav' }))
          }
          if (exportFormats.includes('wav_16_44')) {
            const wav = encodeWAV(buf, 16)
            links['wav_16_44'] = URL.createObjectURL(new Blob([wav], { type: 'audio/wav' }))
          }
          setExportLinks(links)
          setExporting(false)
        }} disabled={!audioBuffer || exporting} style={{
          fontFamily: T.display, fontSize: 20, letterSpacing: '0.15em', padding: '14px 0', width: '100%',
          background: exporting ? T.border : T.accent, color: T.bg, border: 'none', borderRadius: T.rM,
          cursor: audioBuffer ? 'pointer' : 'not-allowed', opacity: audioBuffer ? 1 : 0.4,
        }}>
          {exporting ? '⟳ EXPORTING...' : '⬇ EXPORT ALL'}
        </button>
        {Object.keys(exportLinks).length > 0 && (
          <Pnl>
            <Hd>Downloads</Hd>
            {Object.entries(exportLinks).map(([fmt, url]) => (
              <Row key={fmt} style={{ justifyContent: 'space-between', padding: '4px 0' }}>
                <Lbl>{FORMAT_LABELS[fmt as ExportFormat]}</Lbl>
                <a href={url} download={`${metadata.title || 'aurora'}_${fmt}.wav`} style={{ fontFamily: T.mono, fontSize: 10, color: T.accent }}>⬇ DOWNLOAD</a>
              </Row>
            ))}
          </Pnl>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl>
          <Hd>Metadata</Hd>
          <Grid cols={2} gap={8}>
            {([['title', 'Title'], ['artist', 'Artist'], ['album', 'Album'], ['year', 'Year'], ['genre', 'Genre'], ['isrc', 'ISRC'], ['label', 'Label'], ['publisher', 'Publisher']] as [keyof TrackMetadata, string][]).map(([k, lbl]) => (
              <div key={k}>
                <Lbl>{lbl}</Lbl>
                <input value={metadata[k] as string || ''} onChange={e => setMetadata(m => ({ ...m, [k]: e.target.value }))}
                  placeholder={k === 'isrc' ? 'ZA-TGP-26-NNNNN' : lbl}
                  style={{ width: '100%', marginTop: 3, fontFamily: T.mono, fontSize: 11, background: T.panelAlt, border: `1px solid ${T.border}`, color: T.text, padding: '5px 8px', borderRadius: T.r, outline: 'none' }} />
              </div>
            ))}
          </Grid>
          <div style={{ marginTop: 12 }}>
            <Lbl>COVER ART</Lbl>
            <Row gap={10} style={{ marginTop: 6 }}>
              {metadata.coverArt && <img src={metadata.coverArt} alt="cover" style={{ width: 64, height: 64, borderRadius: T.r, objectFit: 'cover', border: `1px solid ${T.border}` }} />}
              <Btn onClick={() => {
                const i = document.createElement('input'); i.type = 'file'; i.accept = 'image/*'
                i.onchange = e => {
                  const f = (e.target as HTMLInputElement).files?.[0]; if (!f) return
                  const r = new FileReader(); r.onload = ev => setMetadata(m => ({ ...m, coverArt: ev.target?.result as string })); r.readAsDataURL(f)
                }; i.click()
              }}>UPLOAD COVER ART</Btn>
            </Row>
          </div>
        </Pnl>
      </div>
    </div>
  )

  // ─── TAB: ROADMAP ────────────────────────────────────────────────────────────
  const PHASES = [
    { n: 1, status: 'COMPLETE',     label: 'Core DSP Chain + Web Audio API Fallback',         color: T.cyan },
    { n: 2, status: 'COMPLETE',     label: '4-Pass Demucs Stem Extraction (12 stems)',          color: T.cyan },
    { n: 3, status: 'COMPLETE',     label: 'Dolby Atmos ADM BWF + Spatial Panner',             color: T.cyan },
    { n: 4, status: 'IN PROGRESS',  label: 'AU3.0 AI Collab (Adaptive Thinking + SSE)',        color: T.accent },
    { n: 5, status: 'PLANNED',      label: 'Mobile PWA + WASM DSP (offline, no server)',       color: T.dim },
  ]
  const TabRoadmap = () => (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl>
          <Hd>Development Phases</Hd>
          <div style={{ position: 'relative', paddingLeft: 24 }}>
            <div style={{ position: 'absolute', left: 7, top: 8, bottom: 8, width: 1, background: T.border }} />
            {PHASES.map(p => (
              <div key={p.n} style={{ position: 'relative', marginBottom: 20 }}>
                <div style={{ position: 'absolute', left: -24, top: 2, width: 14, height: 14, borderRadius: '50%', background: p.color, border: `2px solid ${T.bg}` }} />
                <Row gap={8} style={{ marginBottom: 4 }}>
                  <Badge status={p.status === 'COMPLETE' ? 'PASS' : p.status === 'IN PROGRESS' ? 'WARN' : undefined}>{p.status}</Badge>
                </Row>
                <div style={{ fontFamily: T.mono, fontSize: 11, color: T.text, lineHeight: 1.5 }}>Phase {p.n} — {p.label}</div>
              </div>
            ))}
          </div>
        </Pnl>
        <Pnl>
          <Hd>System Architecture</Hd>
          <pre style={{ fontFamily: T.mono, fontSize: 9, color: T.sub, lineHeight: 1.7, overflow: 'auto' }}>{`┌─────────────────────────────────────────┐
│       AURORA v3.0 ARCHITECTURE          │
├──────────────────┬──────────────────────┤
│  React 18 / TS   │   Python Flask 3.0   │
│  Aurora.tsx UI   │ server.py (19 routes)│
│  Web Audio API   │ dsp_chain.py         │
│  OfflineACtx     │ stem_extractor.py    │
│  encodeWAV()     │ atmos_renderer.py    │
│                  │ ddp_export.py        │
│                  │ collab_module.py     │
└──────────────────┴──────────────────────┘
   ↑ /api proxy (Vite :3000 → Flask :5000)`}</pre>
        </Pnl>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Pnl>
          <Row style={{ justifyContent: 'space-between', marginBottom: 12 }}>
            <Hd style={{ marginBottom: 0 }}>Diagnostics</Hd>
            <Btn onClick={async () => {
              try {
                const h = await api.get<{ status: string; capabilities: Record<string, boolean> }>('/health')
                setBackendOnline(h.status === 'ok'); setCapabilities(h.capabilities || {})
                setDiagTime(new Date().toLocaleTimeString())
              } catch { setBackendOnline(false) }
            }}>RUN DIAGNOSTICS</Btn>
          </Row>
          <InfoRow label="BACKEND" value={backendOnline ? 'ONLINE' : 'OFFLINE'} color={backendOnline ? T.cyan : T.red} />
          {diagTime && <InfoRow label="LAST CHECK" value={diagTime} />}
          <Divider style={{ margin: '8px 0' }} />
          <Hd>Capabilities</Hd>
          {(['numpy', 'scipy', 'soundfile', 'pyloudnorm', 'anthropic', 'torch', 'demucs', 'mutagen', 'ffmpeg'] as const).map(cap => (
            <Row key={cap} style={{ justifyContent: 'space-between', padding: '3px 0' }}>
              <Lbl>{cap}</Lbl>
              <Row gap={6}>
                <LED on={capabilities[cap] === true} color={capabilities[cap] ? T.cyan : T.red} />
                <span style={{ fontFamily: T.mono, fontSize: 10, color: capabilities[cap] ? T.cyan : T.dim }}>{capabilities[cap] ? 'OK' : 'MISSING'}</span>
              </Row>
            </Row>
          ))}
        </Pnl>
        <Pnl>
          <Hd>Platform Delivery Specs</Hd>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: T.mono, fontSize: 9 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                {['Platform', 'LUFS', 'True Peak', 'Format'].map(h => (
                  <th key={h} style={{ padding: '4px 6px', color: T.sub, fontWeight: 400, textAlign: 'left' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ['Spotify',       '−14', '−1.0 dBTP', 'OGG/AAC'],
                ['Apple Music',   '−16', '−1.0 dBTP', 'AAC/ALAC'],
                ['YouTube',       '−14', '−1.0 dBTP', 'AAC 128'],
                ['TikTok',        '−14', '−1.0 dBTP', 'AAC'],
                ['Club System',   '−6',  '−0.3 dBTP', 'WAV 24-bit'],
                ['TuneCore Atmos','−18', '−1.0 dBTP', 'ADM BWF 7.1.4'],
              ].map(([p, l, t, f]) => (
                <tr key={p} style={{ borderBottom: `1px solid ${T.border}20` }}>
                  {[p, l, t, f].map((v, i) => (
                    <td key={i} style={{ padding: '5px 6px', color: i === 0 ? T.text : T.sub }}>{v}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 8, fontFamily: T.mono, fontSize: 9, color: T.orange }}>⚠ DistroKid does not support ADM BWF. Atmos → TuneCore only.</div>
          <div style={{ marginTop: 4, fontFamily: T.mono, fontSize: 9, color: T.dim }}>ISRC: ZA-TGP-26-NNNNN · ThatGuy Productions · SAMRO</div>
        </Pnl>
      </div>
    </div>
  )

  // ─── TABS CONFIG ─────────────────────────────────────────────────────────────
  const TABS = [
    { id: 'master',  label: 'MASTER'  },
    { id: 'stems',   label: 'STEMS'   },
    { id: 'spatial', label: 'SPATIAL' },
    { id: 'qc',      label: 'QC'      },
    { id: 'collab',  label: 'COLLAB'  },
    { id: 'album',   label: 'ALBUM'   },
    { id: 'export',  label: 'EXPORT'  },
    { id: 'roadmap', label: 'ROADMAP' },
  ]

  // ─── RENDER ──────────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text, fontFamily: T.ui }}>
      {/* Header */}
      <div style={{ borderBottom: `1px solid ${T.border}`, padding: '0 24px', background: T.panel }}>
        <Row style={{ justifyContent: 'space-between', height: 52 }}>
          <Row gap={12}>
            <span style={{ fontFamily: T.display, fontSize: 26, letterSpacing: '0.2em', color: T.accent }}>AURORA</span>
            <span style={{ fontFamily: T.mono, fontSize: 10, color: T.dim, letterSpacing: '0.1em' }}>AI MASTERING ENGINE v3.0</span>
          </Row>
          <Row gap={6}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                fontFamily: T.mono, fontSize: 10, letterSpacing: '0.1em', padding: '4px 14px', height: 32,
                background: tab === t.id ? T.accent : 'transparent', color: tab === t.id ? T.bg : T.sub,
                border: `1px solid ${tab === t.id ? T.accent : 'transparent'}`, borderRadius: T.r, cursor: 'pointer',
                transition: 'all 0.15s',
              }}>{t.label}</button>
            ))}
          </Row>
          <Row gap={8}>
            <LED on={backendOnline} />
            <span style={{ fontFamily: T.mono, fontSize: 9, color: backendOnline ? T.sub : T.dim }}>{backendOnline ? 'BACKEND' : 'OFFLINE'}</span>
          </Row>
        </Row>
      </div>

      {/* Content */}
      <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
        {tab === 'master'  && <TabMaster />}
        {tab === 'stems'   && <TabStems />}
        {tab === 'spatial' && <TabSpatial />}
        {tab === 'qc'      && <TabQC />}
        {tab === 'collab'  && <TabCollab />}
        {tab === 'album'   && <TabAlbum />}
        {tab === 'export'  && <TabExport />}
        {tab === 'roadmap' && <TabRoadmap />}
      </div>
    </div>
  )
}
