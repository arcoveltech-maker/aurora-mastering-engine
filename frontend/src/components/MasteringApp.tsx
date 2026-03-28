import { useState, useRef, useCallback, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

// ─── Types ─────────────────────────────────────────────────────────────────

interface Macro {
  id: string;
  label: string;
  value: number;        // 0–10
  color: string;        // CSS colour for ring
  subParams: string[];
}

interface SignalStage {
  num: number;
  label: string;
}

interface AnalogModel {
  name: string;
  type: string;
  active: boolean;
}

// ─── Constants ─────────────────────────────────────────────────────────────

const SIGNAL_STAGES: SignalStage[] = [
  { num: 1,  label: 'INPUT 24/96'      },
  { num: 2,  label: 'DAW Metadata'     },
  { num: 3,  label: 'Source Sep.'      },
  { num: 4,  label: 'Confidence'       },
  { num: 5,  label: 'Conflict Detect'  },
  { num: 6,  label: 'Per-Stem Proc.'   },
  { num: 7,  label: 'Phase Reassembly' },
  { num: 8,  label: 'THD Engine'       },
  { num: 9,  label: 'M/S Processing'   },
  { num: 10, label: 'Master Bus'       },
  { num: 11, label: 'Limiter'          },
  { num: 12, label: 'Export'           },
];

const NAV_TABS = ['MASTER','STEMS','SPATIAL','QC','COLLAB','ALBUM','EXPORT','DISTRIBUTE','DATASET','TEST','MARKET','ROADMAP'];

const INITIAL_MACROS: Macro[] = [
  { id:'brighter', label:'BRIGHTER', value:5.0, color:'#9dff7c',
    subParams:['Air band (12–16kHz)','Air band (12–16kHz)','Slide high shelf','Transient preserve'] },
  { id:'glue',     label:'GLUE',     value:4.2, color:'#4de8d4',
    subParams:['Bus comp ratio','Knee width','Attack','Release','R/S tightening'] },
  { id:'width',    label:'WIDTH',    value:3.8, color:'#b57bff',
    subParams:['Side channel gain','Side HPF cutoff','Stereo decorrelation','Bass mono-delay'] },
  { id:'punch',    label:'PUNCH',    value:6.1, color:'#ff9f40',
    subParams:['Transient enhance','Kick transient boost','Drum isolation','Low-end tightening'] },
  { id:'warmth',   label:'WARMTH',   value:5.5, color:'#ff5f87',
    subParams:['THD amount','Low-mid harmonic','HF roll-off','Micro-drift amount'] },
];

const ANALOG_MODELS: AnalogModel[] = [
  { name:'Manley Massive Passive', type:'EQ',   active:true  },
  { name:'Shadow Hills Compressor', type:'COMP', active:false },
  { name:'Neve 1023',               type:'PRE',  active:false },
  { name:'SSL 6-Bus Compressor',    type:'COMP', active:false },
];

// ─── Sub-components ─────────────────────────────────────────────────────────

/** SVG circular knob */
function MacroKnob({ macro, onChange }: { macro: Macro; onChange: (id: string, v: number) => void }) {
  const size = 80;
  const r = 32;
  const cx = size / 2;
  const cy = size / 2;
  const strokeW = 4;
  const circumference = 2 * Math.PI * r;
  // Arc from 135° to 405° (270° sweep)
  const minAngle = -225;  // deg from top (12 o'clock)
  const maxAngle =  45;
  const pct = macro.value / 10;
  const sweepDeg = 270 * pct;
  const startRad = (minAngle - 90) * (Math.PI / 180);
  const endRad   = (minAngle - 90 + sweepDeg) * (Math.PI / 180);

  const dragging = useRef(false);
  const lastY    = useRef(0);

  const onMouseDown = (e: React.MouseEvent) => {
    dragging.current = true;
    lastY.current = e.clientY;
    const onMove = (me: MouseEvent) => {
      if (!dragging.current) return;
      const delta = (lastY.current - me.clientY) / 100;
      lastY.current = me.clientY;
      onChange(macro.id, Math.max(0, Math.min(10, macro.value + delta * 10)));
    };
    const onUp = () => { dragging.current = false; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  // Build arc path
  const arcPath = (rad: number) => ({
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  });
  const start = arcPath(startRad);
  const end   = arcPath(endRad);
  const largeArc = sweepDeg > 180 ? 1 : 0;

  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:6 }}>
      <svg width={size} height={size} style={{ cursor:'ns-resize', userSelect:'none' }} onMouseDown={onMouseDown}>
        {/* Track */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e2130" strokeWidth={strokeW} strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`} strokeDashoffset={circumference * 0.125} strokeLinecap="round" />
        {/* Value arc */}
        {sweepDeg > 0 && (
          <path
            d={`M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`}
            fill="none"
            stroke={macro.color}
            strokeWidth={strokeW}
            strokeLinecap="round"
            style={{ filter:`drop-shadow(0 0 4px ${macro.color}80)` }}
          />
        )}
        {/* Center value */}
        <text x={cx} y={cy + 5} textAnchor="middle" fontSize="14" fontFamily="Share Tech Mono, monospace" fill={macro.color} fontWeight="600">
          {macro.value.toFixed(1)}
        </text>
      </svg>
      <span style={{ fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.1em', color:'var(--text-bright)', textTransform:'uppercase' }}>{macro.label}</span>
    </div>
  );
}

/** Vertical level meter bar */
function LevelBar({ level, color = '#9dff7c' }: { level: number; color?: string }) {
  return (
    <div style={{ width:12, height:120, background:'#0d0f14', border:'1px solid #1e2130', borderRadius:2, position:'relative', overflow:'hidden' }}>
      <div style={{ position:'absolute', bottom:0, left:0, right:0, height:`${level * 100}%`, background:color, transition:'height 0.05s', borderRadius:2 }} />
    </div>
  );
}

/** Single range parameter row */
function ParamRow({ label, value, onChange, unit = 'Hz', color = 'var(--green)' }: {
  label: string; value: number; onChange: (v: number) => void;
  unit?: string; color?: string;
}) {
  return (
    <div style={{ display:'flex', alignItems:'center', gap:12, padding:'6px 0', borderBottom:'1px solid #1e2130' }}>
      <span style={{ flex:1, color:'var(--text-base)', fontSize:12 }}>{label}</span>
      <input type="range" min={20} max={20000} value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ flex:2, accentColor:color }} />
      <span style={{ fontFamily:'var(--mono)', fontSize:11, color:'var(--text-bright)', minWidth:52, textAlign:'right' }}>
        {value} {unit}
      </span>
    </div>
  );
}

// ─── Main App ────────────────────────────────────────────────────────────────

export function MasteringApp() {
  const { user } = useAuth();

  const [activeTab, setActiveTab]     = useState('MASTER');
  const [activeStage, setActiveStage] = useState(8);
  const [macros, setMacros]           = useState<Macro[]>(INITIAL_MACROS);
  const [platformScore]               = useState(82);
  const [analogEra, setAnalogEra]     = useState('MOORE-GLASSBERG 2007');
  const [activeModel, setActiveModel] = useState(0);
  const [lrCrossover, setLrCrossover] = useState(120);
  const [sideHpf, setSideHpf]         = useState(200);
  const [isPlaying, setIsPlaying]     = useState(false);
  const [audioFile, setAudioFile]     = useState<File | null>(null);
  const [masterLevels]                = useState([0.45, 0.52, 0.38, 0.61, 0.49]);
  const [isMastering, setIsMastering] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateMacro = useCallback((id: string, v: number) => {
    setMacros(ms => ms.map(m => m.id === id ? { ...m, value: parseFloat(v.toFixed(1)) } : m));
  }, []);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) setAudioFile(f);
  };

  const handleMasterNow = async () => {
    if (!audioFile) return;
    setIsMastering(true);
    // TODO: POST to /api/render
    await new Promise(r => setTimeout(r, 2000));
    setIsMastering(false);
  };

  const s = (style: React.CSSProperties): React.CSSProperties => style;

  return (
    <div style={s({ background:'var(--bg)', minHeight:'100vh', color:'var(--text-base)', fontFamily:'var(--sans)', fontSize:13 })}>

      {/* ── Header ────────────────────────────────────────────────── */}
      <header style={s({ display:'flex', alignItems:'center', gap:12, padding:'8px 16px', borderBottom:'1px solid var(--border)', background:'var(--bg-panel)' })}>
        {/* Logo */}
        <div style={s({ display:'flex', alignItems:'center', gap:10 })}>
          <div style={s({ width:28, height:28, border:'1px solid var(--green)', borderRadius:3, display:'grid', gridTemplateColumns:'1fr 1fr', gap:2, padding:4 })}>
            {[0,1,2,3].map(i => <div key={i} style={{ background: i===0?'var(--green)':'#1e2130', borderRadius:1 }} />)}
          </div>
          <div>
            <div style={s({ fontFamily:'var(--mono)', fontSize:14, letterSpacing:'0.15em', color:'var(--text-white)', fontWeight:600 })}>AURORA</div>
            <div style={s({ fontFamily:'var(--mono)', fontSize:8, letterSpacing:'0.1em', color:'var(--text-muted)' })}>AI MASTERING ENGINE v2.0</div>
          </div>
        </div>

        <button className="btn" style={{ color:'var(--red)', borderColor:'var(--red)33' }}>OFFLINE</button>

        <div style={s({ flex:1 })} />

        {/* AI badges */}
        <div style={s({ display:'flex', gap:8 })}>
          <span style={s({ background:'#1a1d2a', border:'1px solid #3a3f5c', borderRadius:3, padding:'3px 10px', fontFamily:'var(--mono)', fontSize:10, color:'#8892b0' })}>
            CLAUDE OPUS 4.6
          </span>
          <span style={s({ background:'#1a2a1a', border:'1px solid #2a4a2a', borderRadius:3, padding:'3px 10px', fontFamily:'var(--mono)', fontSize:10, color:'var(--green)' })}>
            {user?.display_name ?? 'DEMOS INTONICS_FT'}
          </span>
        </div>

        <div style={s({ display:'flex', gap:6, alignItems:'center' })}>
          <button className="btn" style={{ padding:'4px 8px' }}>?</button>
          <button className="btn" style={{ padding:'4px 8px', color:'var(--green)', borderColor:'var(--green)44' }}>M</button>
          <button className="btn">AURORA</button>
          <button className="btn">LOAD</button>
          <button className="btn btn-green">SAVE</button>
          <button className="btn" style={{ padding:'4px 8px' }}>↺</button>
        </div>
      </header>

      {/* ── Nav Tabs ──────────────────────────────────────────────── */}
      <nav style={s({ display:'flex', gap:0, borderBottom:'1px solid var(--border)', background:'var(--bg-panel)', overflowX:'auto' })}>
        {NAV_TABS.map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            style={s({
              padding:'10px 14px',
              border:'none',
              borderBottom: tab === activeTab ? '2px solid var(--green)' : '2px solid transparent',
              background:'transparent',
              color: tab === activeTab ? 'var(--text-white)' : 'var(--text-muted)',
              fontFamily:'var(--mono)',
              fontSize:10,
              letterSpacing:'0.08em',
              cursor:'pointer',
              whiteSpace:'nowrap',
              display:'flex', alignItems:'center', gap:5,
            })}>
            {tab === 'QC' && <span style={{ color:'var(--green)', fontSize:10 }}>✓</span>}
            {tab}
          </button>
        ))}
      </nav>

      {/* ── Transport Bar ─────────────────────────────────────────── */}
      <div style={s({ display:'flex', alignItems:'center', gap:12, padding:'10px 16px', borderBottom:'1px solid var(--border)', background:'#0e1014' })}>
        {/* Controls */}
        <div style={s({ display:'flex', gap:6 })}>
          {['⏮','⏸','⏭','⏹'].map((icon, i) => (
            <button key={i} onClick={i===1?()=>setIsPlaying(!isPlaying):undefined}
              className="btn" style={{ padding:'4px 8px', fontSize:12 }}>
              {i===1 && isPlaying ? '⏸' : icon}
            </button>
          ))}
        </div>

        {/* Waveform drop zone */}
        <div
          onDrop={handleFileDrop}
          onDragOver={e => e.preventDefault()}
          onClick={() => fileInputRef.current?.click()}
          style={s({
            flex:1, height:40, border:'1px solid var(--border-med)', borderRadius:3,
            background:'#0b0d10', cursor:'pointer', display:'flex', alignItems:'center',
            justifyContent: audioFile ? 'flex-start' : 'center', padding:'0 12px',
            position:'relative', overflow:'hidden',
          })}>
          {audioFile ? (
            <>
              {/* Fake waveform */}
              <svg width="100%" height="40" style={{ position:'absolute', inset:0, opacity:0.6 }}>
                {Array.from({length:80}).map((_,i) => {
                  const h = 4 + Math.random() * 24;
                  return <rect key={i} x={i*(100/80)+'%'} y={(40-h)/2} width="0.8%" height={h} fill="#e8c840" rx="1" />;
                })}
              </svg>
              <span style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--text-bright)', zIndex:1 }}>{audioFile.name}</span>
            </>
          ) : (
            <span style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--text-dim)', letterSpacing:'0.05em' }}>
              Drop audio or click to browse · WAV · MP3 · FLAC · OGG · AAC
            </span>
          )}
        </div>
        <input ref={fileInputRef} type="file" accept=".wav,.mp3,.flac,.ogg,.aac" style={{ display:'none' }}
          onChange={e => { const f = e.target.files?.[0]; if (f) setAudioFile(f); }} />

        <span style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--text-dim)' }}>0:00</span>
        <span style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--text-dim)' }}>0:00</span>

        {/* Volume */}
        <div style={s({ display:'flex', alignItems:'center', gap:6 })}>
          <span style={{ fontSize:12 }}>🔊</span>
          <input type="range" min={0} max={100} defaultValue={75} style={{ width:80, accentColor:'var(--yellow)' }} />
        </div>
      </div>

      {/* ── Master label ──────────────────────────────────────────── */}
      <div style={s({ padding:'6px 16px', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', gap:8 })}>
        <div style={{ width:8, height:8, borderRadius:'50%', background:'var(--green)', boxShadow:'0 0 6px var(--green)' }} />
        <span style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--text-muted)' }}>■</span>
        <span style={{ fontFamily:'var(--mono)', fontSize:11, letterSpacing:'0.12em', color:'var(--text-bright)' }}>MASTER</span>
      </div>

      {/* ── Main content ──────────────────────────────────────────── */}
      <div style={s({ padding:16, display:'flex', flexDirection:'column', gap:12 })}>

        {/* Mastering Engine header bar */}
        <div style={s({ background:'var(--bg-panel)', border:'1px solid var(--border)', borderRadius:4, padding:'14px 20px', display:'flex', alignItems:'center', justifyContent:'space-between' })}>
          <div>
            <div style={s({ fontFamily:'var(--mono)', fontSize:13, letterSpacing:'0.1em', color:'var(--text-bright)', marginBottom:4 })}>MASTERING ENGINE</div>
            <div style={s({ fontSize:11, color:'var(--text-dim)' })}>↑ Load an audio file in the transport bar above, then click MASTER NOW to begin processing</div>
          </div>
          <div style={s({ display:'flex', gap:8 })}>
            <button className="btn btn-green" onClick={handleMasterNow} disabled={isMastering || !audioFile}
              style={{ opacity: (!audioFile || isMastering) ? 0.5 : 1, gap:6 }}>
              {isMastering ? '⏳' : '+'} MASTER NOW
            </button>
            <button className="btn">↺ RESET</button>
          </div>
        </div>

        {/* ── Signal Chain ────────────────────────────────────────── */}
        <div style={s({ background:'var(--bg-panel)', border:'1px solid var(--border)', borderRadius:4, padding:16 })}>
          <div className="section-heading" style={{ marginBottom:12 }}>12-STAGE SIGNAL CHAIN</div>
          <div style={s({ display:'flex', gap:4, overflowX:'auto' })}>
            {SIGNAL_STAGES.map(stage => (
              <button key={stage.num} onClick={() => setActiveStage(stage.num)}
                style={s({
                  flex:'0 0 auto',
                  padding:'8px 10px',
                  border:`1px solid ${activeStage===stage.num ? 'var(--yellow)' : 'var(--border)'}`,
                  borderRadius:3,
                  background: activeStage===stage.num ? '#1a1800' : 'var(--bg-card)',
                  color: activeStage===stage.num ? 'var(--yellow)' : 'var(--text-muted)',
                  fontFamily:'var(--mono)',
                  fontSize:9,
                  letterSpacing:'0.06em',
                  cursor:'pointer',
                  minWidth:72,
                  textAlign:'left',
                  boxShadow: activeStage===stage.num ? '0 0 8px #e8c84040' : 'none',
                })}>
                <div style={{ color:'var(--text-dim)', fontSize:8, marginBottom:2 }}>{stage.num}</div>
                <div style={{ textTransform:'uppercase', lineHeight:1.3 }}>{stage.label}</div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Middle row: Macros + Metering ───────────────────────── */}
        <div style={s({ display:'grid', gridTemplateColumns:'1fr 280px', gap:12 })}>

          {/* Creative Macro System */}
          <div style={s({ background:'var(--bg-panel)', border:'1px solid var(--border)', borderRadius:4, padding:16 })}>
            <div className="section-heading" style={{ marginBottom:16 }}>CREATIVE MACRO SYSTEM</div>
            <div style={s({ display:'flex', gap:20, flexWrap:'wrap' })}>
              {macros.map(m => (
                <div key={m.id} style={s({ flex:'0 0 auto' })}>
                  <MacroKnob macro={m} onChange={updateMacro} />
                  <div style={s({ marginTop:8, minWidth:100 })}>
                    {m.subParams.map((p, i) => (
                      <div key={i} style={s({ fontSize:10, color:'var(--text-dim)', lineHeight:1.8, paddingLeft:8, borderLeft:`1px solid ${m.color}33` })}>
                        · {p}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Metering */}
          <div style={s({ background:'var(--bg-panel)', border:'1px solid var(--border)', borderRadius:4, padding:16 })}>
            <div className="section-heading" style={{ marginBottom:12 }}>METERING</div>
            <div style={s({ display:'flex', gap:8, justifyContent:'center', marginBottom:16 })}>
              {masterLevels.map((lv, i) => (
                <LevelBar key={i} level={lv} color={lv > 0.9 ? '#ff4d4d' : lv > 0.7 ? '#e8c840' : '#9dff7c'} />
              ))}
            </div>
            <div style={s({ display:'flex', justifyContent:'space-between', fontSize:10, color:'var(--text-dim)', fontFamily:'var(--mono)', marginBottom:16 })}>
              <span>L</span><span>S</span><span>R</span>
            </div>

            {/* Platform Survival Score */}
            <div style={s({ textAlign:'center' })}>
              <div style={s({ fontSize:10, fontFamily:'var(--mono)', color:'var(--text-muted)', marginBottom:8, letterSpacing:'0.08em' })}>PLATFORM SURVIVAL SCORE</div>
              <div style={s({ position:'relative', width:80, height:80, margin:'0 auto' })}>
                <svg width={80} height={80} viewBox="0 0 80 80">
                  <circle cx={40} cy={40} r={32} fill="none" stroke="#1e2130" strokeWidth={5} />
                  <circle cx={40} cy={40} r={32} fill="none" stroke="#9dff7c" strokeWidth={5}
                    strokeDasharray={`${2*Math.PI*32*platformScore/100} ${2*Math.PI*32}`}
                    strokeDashoffset={2*Math.PI*32*0.25}
                    strokeLinecap="round"
                    style={{ filter:'drop-shadow(0 0 6px #9dff7c80)', transform:'rotate(-90deg)', transformOrigin:'50% 50%' }}
                  />
                  <text x={40} y={38} textAnchor="middle" fontSize={20} fontFamily="Share Tech Mono, monospace" fill="#9dff7c" fontWeight="600">{platformScore}</text>
                  <text x={40} y={52} textAnchor="middle" fontSize={8} fontFamily="Share Tech Mono, monospace" fill="#4a5068">PSS</text>
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* ── Bottom row: Analog Soul + M/S Processing ─────────────── */}
        <div style={s({ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 })}>

          {/* Analog Soul Modeling */}
          <div style={s({ background:'var(--bg-panel)', border:'1px solid var(--border)', borderRadius:4, padding:16 })}>
            <div style={s({ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12 })}>
              <div className="section-heading">ANALOG SOUL MODELING</div>
              <button className="btn" style={{ fontSize:9 }}>{analogEra}</button>
            </div>
            <div style={s({ display:'flex', flexDirection:'column', gap:4 })}>
              {ANALOG_MODELS.map((model, i) => (
                <button key={i} onClick={() => setActiveModel(i)}
                  style={s({
                    display:'flex', alignItems:'center', gap:10,
                    padding:'8px 12px',
                    border:`1px solid ${i===activeModel ? '#9dff7c44' : 'var(--border)'}`,
                    borderRadius:3,
                    background: i===activeModel ? '#0d1a0d' : 'var(--bg-card)',
                    cursor:'pointer', textAlign:'left',
                  })}>
                  <div style={{ width:8, height:8, borderRadius:'50%', background: i===activeModel ? 'var(--green)' : '#1e2130', boxShadow: i===activeModel ? '0 0 4px var(--green)' : 'none' }} />
                  <div style={s({ flex:1 })}>
                    <div style={s({ fontSize:12, color: i===activeModel ? 'var(--text-bright)' : 'var(--text-base)' })}>{model.name}</div>
                    <div style={s({ fontSize:10, color:'var(--text-dim)', fontFamily:'var(--mono)' })}>{model.type}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* M/S Processing */}
          <div style={s({ background:'var(--bg-panel)', border:'1px solid var(--border)', borderRadius:4, padding:16 })}>
            <div className="section-heading" style={{ marginBottom:16 }}>M/S PROCESSING</div>
            <ParamRow label="LR Crossover (Mono Below)" value={lrCrossover} onChange={setLrCrossover} unit="Hz" />
            <ParamRow label="Side HPF Cutoff" value={sideHpf} onChange={setSideHpf} unit="Hz" />
            <ParamRow label="Side Gain" value={200} onChange={() => {}} unit="dB" color="var(--blue-accent)" />
            <ParamRow label="Mid Saturation" value={100} onChange={() => {}} unit="%" color="var(--knob-warmth)" />
          </div>
        </div>

      </div>
    </div>
  );
}
