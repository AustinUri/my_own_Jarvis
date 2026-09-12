import { useEffect, useMemo, useRef, useState } from 'react'
import { Responsive, WidthProvider, type Layout } from 'react-grid-layout'
import OrbCanvas from './components/OrbCanvas'
import { useJarvisSocket } from './lib/useJarvisSocket'
import type { CameraStatus } from './lib/types'

const ResponsiveGridLayout = WidthProvider(Responsive)

type WidgetId = 'orb' | 'conversation' | 'activity' | 'sources' | 'system' | 'context' | 'camera' | 'settings'
type WorkspaceName = 'Normal' | 'Research' | 'Developer' | 'Vision' | 'Minimal'

const widgetTitles: Record<WidgetId, string> = {
  orb: 'JARVIS Core', conversation: 'Conversation', activity: 'Agent Activity', sources: 'Sources',
  system: 'System Monitor', context: 'Context', camera: 'Camera / Vision', settings: 'Settings',
}

const widgetDefaults: Record<WidgetId, { w:number, h:number, minW:number, minH:number }> = {
  orb:{w:4,h:7,minW:3,minH:5}, conversation:{w:6,h:10,minW:4,minH:6}, activity:{w:4,h:6,minW:3,minH:4},
  sources:{w:5,h:9,minW:3,minH:5}, system:{w:3,h:5,minW:3,minH:4}, context:{w:4,h:5,minW:3,minH:4},
  camera:{w:4,h:7,minW:3,minH:5}, settings:{w:5,h:7,minW:3,minH:5},
}

const defaultLayouts: Record<WorkspaceName, Layout[]> = {
  Normal: [
    { i:'orb', x:0,y:0,w:6,h:7,minW:3,minH:5 }, { i:'conversation',x:6,y:0,w:6,h:10,minW:4,minH:6 },
    { i:'activity',x:0,y:7,w:3,h:6,minW:3,minH:4 }, { i:'context',x:3,y:7,w:3,h:6,minW:3,minH:4 },
  ],
  Research: [
    { i:'conversation',x:0,y:0,w:7,h:10,minW:4,minH:6 }, { i:'sources',x:7,y:0,w:5,h:10,minW:3,minH:5 },
    { i:'activity',x:0,y:10,w:5,h:5,minW:3,minH:4 }, { i:'orb',x:5,y:10,w:3,h:5,minW:3,minH:4 }, { i:'context',x:8,y:10,w:4,h:5,minW:3,minH:4 },
  ],
  Developer: [
    { i:'activity',x:0,y:0,w:6,h:11,minW:4,minH:6 }, { i:'conversation',x:6,y:0,w:6,h:8,minW:4,minH:6 },
    { i:'system',x:6,y:8,w:3,h:5,minW:3,minH:4 }, { i:'context',x:9,y:8,w:3,h:5,minW:3,minH:4 },
  ],
  Vision: [
    { i:'camera',x:0,y:0,w:7,h:11,minW:4,minH:6 }, { i:'orb',x:7,y:0,w:5,h:7,minW:3,minH:5 },
    { i:'conversation',x:7,y:7,w:5,h:7,minW:4,minH:5 },
  ],
  Minimal: [{ i:'orb',x:2,y:0,w:8,h:9,minW:4,minH:6 }, { i:'conversation',x:2,y:9,w:8,h:6,minW:4,minH:5 }],
}

function storedLayouts(): Record<WorkspaceName, Layout[]> {
  try {
    const v24 = localStorage.getItem('jarvis-v24-layouts')
    if (v24) return { ...defaultLayouts, ...JSON.parse(v24) }
    const old = localStorage.getItem('jarvis-v23-layouts')
    if (old) {
      const parsed = JSON.parse(old) as Record<string, Layout[]>
      const custom = Object.fromEntries(Object.entries(parsed).filter(([name]) => !(name in defaultLayouts)))
      return { ...defaultLayouts, ...custom } as Record<WorkspaceName, Layout[]>
    }
  } catch {}
  return defaultLayouts
}

function parseSources(text: string) {
  const lines = text.split(/\r?\n/)
  return lines.flatMap((line) => {
    const m = line.match(/(?:^|\s)(https?:\/\/\S+)/)
    if (!m) return []
    return [{ label: line.replace(m[1], '').replace(/^\s*\d+[.)]\s*/, '').replace(/[—–-]\s*$/, '').trim() || m[1], url: m[1].replace(/[),.;]+$/, '') }]
  })
}

function overlaps(a: Layout, b: {x:number,y:number,w:number,h:number}) {
  return !(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y)
}

function smartInsert(layout: Layout[], id: WidgetId, cols=12): Layout[] {
  if (layout.some(item => item.i === id)) return layout
  const d = widgetDefaults[id]
  const currentBottom = layout.reduce((m, item) => Math.max(m, item.y + item.h), 0)

  // First use any genuine free space that already exists within the current canvas.
  for (let y=0; y<=currentBottom; y++) {
    for (let x=0; x<=cols-d.w; x++) {
      const candidate = { x, y, w:d.w, h:d.h }
      if (y + d.h <= currentBottom && !layout.some(item => overlaps(item, candidate))) {
        return [...layout, { i:id, ...candidate, minW:d.minW, minH:d.minH }]
      }
    }
  }

  // No free rectangle: split a large existing panel in-place instead of throwing
  // the new widget far below the visible workspace. This is the behavior wanted
  // for Camera, Sources, etc. when summoned on an already full dashboard.
  const candidates = [...layout]
    .filter(item => item.w - Number(item.minW || 1) >= d.minW && item.h >= d.minH)
    .sort((a,b) => (b.w*b.h) - (a.w*a.h))
  const target = candidates[0]
  if (target) {
    const targetMin = Number(target.minW || 1)
    const newW = Math.max(d.minW, Math.floor(target.w / 2))
    const leftW = target.w - newW
    if (leftW >= targetMin) {
      const updated = layout.map(item => item.i === target.i ? { ...item, w:leftW } : item)
      return [...updated, { i:id, x:target.x+leftW, y:target.y, w:newW, h:Math.max(d.minH, target.h), minW:d.minW, minH:d.minH }]
    }
  }

  // Last resort: append directly beneath the shallowest column, not at Infinity.
  let bestX = 0, bestY = Number.MAX_SAFE_INTEGER
  for (let x=0; x<=cols-d.w; x++) {
    const y = layout.filter(item => !(item.x + item.w <= x || x + d.w <= item.x)).reduce((m,item)=>Math.max(m,item.y+item.h),0)
    if (y < bestY) { bestX=x; bestY=y }
  }
  return [...layout, { i:id,x:bestX,y:bestY,w:d.w,h:d.h,minW:d.minW,minH:d.minH }]
}

function Panel({ id, title, onHide, children }: { id: WidgetId, title: string, onHide: (id: WidgetId)=>void, children: React.ReactNode }) {
  const [full, setFull] = useState(false)
  const popout = () => window.open(`${location.origin}/?popout=${id}`, `jarvis-${id}`, 'width=820,height=700')
  return <section className={`panel ${full?'panel-fullscreen':''}`}>
    <header className="panel-header drag-handle"><span>{title}</span><div className="panel-actions"><button onClick={()=>setFull(v=>!v)} title="Fullscreen">⛶</button><button onClick={popout} title="Pop out">↗</button><button onClick={()=>onHide(id)} title="Hide">×</button></div></header>
    <div className="panel-body">{children}</div>
  </section>
}

function CameraWidget({ send, cameraStatus, intervalSeconds }: { send:(action:string,payload?:Record<string,unknown>)=>void, cameraStatus:CameraStatus, intervalSeconds:number }) {
  const [active, setActive] = useState(false)
  const [error, setError] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    let stream: MediaStream | undefined
    let timer: number | undefined
    let disposed = false
    const video = videoRef.current
    if (!active || !video) return

    const capture = () => {
      if (!video.videoWidth || !video.videoHeight || video.readyState < 2) return
      const maxW = 640
      const scale = Math.min(1, maxW / video.videoWidth)
      const w = Math.max(2, Math.round(video.videoWidth * scale))
      const h = Math.max(2, Math.round(video.videoHeight * scale))
      const canvas = document.createElement('canvas')
      canvas.width = w; canvas.height = h
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.drawImage(video, 0, 0, w, h)
      const dataUrl = canvas.toDataURL('image/jpeg', 0.72)
      send('camera_frame', { data_url:dataUrl, width:w, height:h })
    }

    navigator.mediaDevices.getUserMedia({ video: { width:{ideal:1280}, height:{ideal:720} }, audio:false })
      .then(s => {
        if (disposed) { s.getTracks().forEach(t=>t.stop()); return }
        stream = s
        video.srcObject = s
        send('camera_enabled')
        const interval = Math.max(750, Number(intervalSeconds || 1.5) * 1000)
        timer = window.setInterval(capture, interval)
        window.setTimeout(capture, 600)
      })
      .catch(e => { setError(String(e)); setActive(false); send('camera_disabled') })

    return () => {
      disposed = true
      if (timer) window.clearInterval(timer)
      stream?.getTracks().forEach(t=>t.stop())
      send('camera_disabled')
    }
  }, [active, send, intervalSeconds])

  return <div className="camera-widget">
    <div className="camera-frame-wrap">
      {active ? <video ref={videoRef} autoPlay playsInline muted /> : <div className="camera-off">Camera is off<br/><small>Nothing is shared until you enable it.</small></div>}
      {active && <div className={`vision-badge ${cameraStatus.hasFrame?'live':''}`}>{cameraStatus.hasFrame?'JARVIS VISION LINKED':'CAMERA LIVE — LINKING…'}</div>}
    </div>
    {error && <div className="error-text">{error}</div>}
    <div className="camera-controls"><button className="primary" onClick={()=>{setError('');setActive(v=>!v)}}>{active ? 'Disable camera' : 'Enable camera'}</button><span>{active ? 'Ask: “Jarvis, what can you see?”' : 'Explicit permission only'}</span></div>
  </div>
}

function App() {
  const { snapshot, metrics, connected, uiCommand, cameraStatus, send, patchConfig } = useJarvisSocket()
  const [workspace, setWorkspace] = useState<WorkspaceName>(() => (localStorage.getItem('jarvis-v24-workspace') as WorkspaceName) || (localStorage.getItem('jarvis-v23-workspace') as WorkspaceName) || 'Normal')
  const [allLayouts, setAllLayouts] = useState<Record<WorkspaceName, Layout[]>>(storedLayouts)
  const [hidden, setHidden] = useState<Record<WorkspaceName, WidgetId[]>>(() => {
    try { return JSON.parse(localStorage.getItem('jarvis-v24-hidden') || '{}') } catch { return {} }
  })
  const [palette, setPalette] = useState(false)
  const [input, setInput] = useState('')
  const [theme, setTheme] = useState(localStorage.getItem('jarvis-v24-theme') || 'stark')
  const [editMode, setEditMode] = useState(true)
  const popout = new URLSearchParams(location.search).get('popout') as WidgetId | null

  useEffect(() => { localStorage.setItem('jarvis-v24-workspace', workspace) }, [workspace])
  useEffect(() => { localStorage.setItem('jarvis-v24-layouts', JSON.stringify(allLayouts)) }, [allLayouts])
  useEffect(() => { localStorage.setItem('jarvis-v24-hidden', JSON.stringify(hidden)) }, [hidden])
  useEffect(() => { localStorage.setItem('jarvis-v24-theme', theme); document.documentElement.dataset.theme = theme }, [theme])
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette(v=>!v) } }
    window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key)
  }, [])

  const activeHidden = hidden[workspace] || []
  const visible = useMemo(() => new Set(allLayouts[workspace].map(l => l.i as WidgetId).filter(id => !activeHidden.includes(id))), [allLayouts, workspace, activeHidden])
  const sources = parseSources(snapshot.runtime.response)
  const logLines = snapshot.runtime.logs.slice(-80).reverse()

  const hideWidget = (id: WidgetId) => setHidden(h => ({ ...h, [workspace]: Array.from(new Set([...(h[workspace]||[]), id])) }))
  const showWidget = (id: WidgetId) => {
    setHidden(h => ({ ...h, [workspace]: (h[workspace]||[]).filter(x=>x!==id) }))
    setAllLayouts(a => ({ ...a, [workspace]: smartInsert(a[workspace], id) }))
  }
  const submit = () => { const text=input.trim(); if (!text) return; send('submit_text',{text}); setInput('') }

  useEffect(() => {
    if (!uiCommand) return
    const action = uiCommand.action
    const payload = uiCommand.payload || {}
    if (action === 'ui_show_panel') {
      const panel = String(payload.panel || '') as WidgetId
      if (widgetTitles[panel]) showWidget(panel)
    } else if (action === 'ui_hide_panel') {
      const panel = String(payload.panel || '') as WidgetId
      if (widgetTitles[panel]) hideWidget(panel)
    } else if (action === 'ui_switch_workspace') {
      const requested = String(payload.workspace || '') as WorkspaceName
      if (defaultLayouts[requested]) setWorkspace(requested)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uiCommand?.nonce])

  const widget = (id: WidgetId) => {
    if (id === 'orb') return <div className="orb-widget"><OrbCanvas state={snapshot.runtime.assistantState}/><div className="orb-status">{snapshot.runtime.assistantState}</div><div className="orb-sub">{connected ? 'J.A.R.V.I.S. CORE LINKED' : 'CORE OFFLINE'}</div></div>
    if (id === 'conversation') return <div className="conversation-widget">
      <div className="conversation-scroll">
        {snapshot.runtime.transcript && <div className="bubble user"><div className="bubble-label">YOU</div>{snapshot.runtime.transcript}</div>}
        {snapshot.runtime.response && <div className={`bubble jarvis ${snapshot.runtime.responseLanguage==='he'?'rtl':''}`}><div className="bubble-label">JARVIS</div>{snapshot.runtime.response}</div>}
        {!snapshot.runtime.transcript && !snapshot.runtime.response && <div className="empty-copy">Say “Hey Jarvis” or type below.</div>}
      </div>
      <div className="composer"><button className="mic" onClick={()=>send('push_to_talk')}>◉</button><input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&submit()} placeholder="Type or speak to Jarvis…"/><button className="primary" onClick={submit}>Send</button></div>
    </div>
    if (id === 'activity') return <div className="log-list">{logLines.map((l,i)=><div className="log-row" key={i}>{l}</div>)}{!logLines.length&&<div className="empty-copy">No agent activity yet.</div>}</div>
    if (id === 'sources') return <div className="source-list">{sources.map((s,i)=><a href={s.url} target="_blank" rel="noreferrer" key={i}><span>{i+1}</span><div><b>{s.label}</b><small>{s.url}</small></div></a>)}{!sources.length&&<div className="empty-copy">Sources appear here after researched answers.</div>}</div>
    if (id === 'system') return <div className="metric-grid"><Metric name="CPU" value={metrics.cpu}/><Metric name="RAM" value={metrics.ram}/><Metric name="BAT" value={metrics.battery}/></div>
    if (id === 'context') return <div className="context-list"><Info k="AI" v={String(snapshot.config.ai_model_name||'jarvis-qwen')}/><Info k="Provider" v={String(snapshot.config.ai_provider||'LM Studio')}/><Info k="Mic" v={String(snapshot.config.mic_name||'Default')}/><Info k="Wake" v={snapshot.config.wake_word_enabled?'ON':'OFF'}/><Info k="Voice" v={snapshot.config.voice_enabled?'ON':'MUTED'}/><Info k="Web" v={String(snapshot.config.searxng_base_url||'local')}/><Info k="Vision" v={cameraStatus.hasFrame?'CAMERA LINKED':'OFF'}/><Info k="AI status" v={snapshot.aiStatus}/></div>
    if (id === 'camera') return <CameraWidget send={send} cameraStatus={cameraStatus} intervalSeconds={Number(snapshot.config.camera_frame_interval_seconds||1.5)}/>
    if (id === 'settings') return <div className="settings-grid">
      <label>Address me as<input defaultValue={String(snapshot.config.address_name||'sir')} onBlur={e=>patchConfig({address_name:e.target.value})}/></label>
      <label>Tone<select value={String(snapshot.config.tone_mode||'Respectful')} onChange={e=>patchConfig({tone_mode:e.target.value})}><option>Respectful</option><option>Neutral</option><option>Casual</option></select></label>
      <label>Language<select value={String(snapshot.config.language_mode||'Auto')} onChange={e=>patchConfig({language_mode:e.target.value})}><option>Auto</option><option>English</option><option>Hebrew</option></select></label>
      <label>Wake threshold<input type="number" step="0.01" min="0.05" max="0.9" value={Number(snapshot.config.wake_word_threshold||0.15)} onChange={e=>patchConfig({wake_word_threshold:Number(e.target.value)})}/></label>
      <label>Command silence (seconds)<input type="number" step="0.1" min="0.8" max="4" value={Number(snapshot.config.command_silence_seconds||2.2)} onChange={e=>patchConfig({command_silence_seconds:Number(e.target.value)})}/></label>
      <label>Max voice turn (seconds)<input type="number" step="1" min="5" max="30" value={Number(snapshot.config.command_max_seconds||14)} onChange={e=>patchConfig({command_max_seconds:Number(e.target.value)})}/></label>
      <div className="settings-buttons"><button onClick={()=>send('toggle_wake_word')}>Toggle wake word</button><button onClick={()=>send('toggle_voice')}>Mute / unmute</button><button onClick={()=>send('test_microphone')}>Test mic</button><button onClick={()=>send('test_voice')}>Test voice</button><button onClick={()=>send('clear_memory')}>Clear conversation memory</button></div>
    </div>
    return null
  }

  if (popout && widgetTitles[popout]) return <div className="popout-shell"><Panel id={popout} title={widgetTitles[popout]} onHide={()=>window.close()}>{widget(popout)}</Panel></div>

  const items = Array.from(visible)
  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-dot"/>JARVIS <small>v24</small></div>
      <div className="top-status"><span className={`connection ${connected?'ok':'bad'}`}>{connected?'LINKED':'OFFLINE'}</span><span>{snapshot.runtime.assistantState}</span><span>{String(snapshot.config.ai_model_name||'jarvis-qwen')}</span>{cameraStatus.hasFrame&&<span className="vision-top">VISION</span>}</div>
      <div className="top-actions">
        <select value={workspace} onChange={e=>setWorkspace(e.target.value as WorkspaceName)}>{Object.keys(defaultLayouts).map(w=><option key={w}>{w}</option>)}</select>
        <button onClick={()=>setEditMode(v=>!v)}>{editMode?'Lock layout':'Edit layout'}</button>
        <button onClick={()=>setPalette(true)}>⌘</button>
      </div>
    </header>

    <div className="workspace-toolbar">
      <div className="widget-add"><span>Add widget:</span>{(Object.keys(widgetTitles) as WidgetId[]).filter(id=>!items.includes(id)).map(id=><button key={id} onClick={()=>showWidget(id)}>+ {widgetTitles[id]}</button>)}</div>
      <div className="themes"><button className={theme==='stark'?'active':''} onClick={()=>setTheme('stark')}>Stark</button><button className={theme==='blue'?'active':''} onClick={()=>setTheme('blue')}>FRIDAY</button><button className={theme==='mono'?'active':''} onClick={()=>setTheme('mono')}>Mono</button></div>
    </div>

    <main className={`grid-shell ${editMode?'editing':'locked'}`}>
      <ResponsiveGridLayout
        className="layout" layouts={{lg: allLayouts[workspace]}} breakpoints={{lg:1200,md:900,sm:600,xs:0}} cols={{lg:12,md:10,sm:6,xs:2}}
        rowHeight={42} margin={[12,12]} draggableHandle=".drag-handle" isDraggable={editMode} isResizable={editMode}
        compactType="vertical" preventCollision={false}
        onLayoutChange={(layout)=>setAllLayouts(a=>({...a,[workspace]:layout}))}
      >
        {items.map(id=><div key={id}><Panel id={id} title={widgetTitles[id]} onHide={hideWidget}>{widget(id)}</Panel></div>)}
      </ResponsiveGridLayout>
    </main>

    {palette && <div className="palette-backdrop" onMouseDown={()=>setPalette(false)}><div className="palette" onMouseDown={e=>e.stopPropagation()}><h3>Command Palette</h3>
      {Object.keys(defaultLayouts).map(w=><button key={w} onClick={()=>{setWorkspace(w as WorkspaceName);setPalette(false)}}>Switch to {w}</button>)}
      <button onClick={()=>{send('push_to_talk');setPalette(false)}}>Push-to-talk</button>
      <button onClick={()=>{showWidget('settings');setPalette(false)}}>Show Settings</button>
      <button onClick={()=>{showWidget('activity');setPalette(false)}}>Show Agent Activity</button>
      <button onClick={()=>{showWidget('camera');setPalette(false)}}>Show Camera / Vision</button>
    </div></div>}
  </div>
}

function Metric({name,value}:{name:string,value:number|null}) { const v=value==null?0:value; return <div className="metric"><div className="metric-name">{name}</div><div className="metric-value">{value==null?'—':`${v}%`}</div><div className="meter"><span style={{width:`${Math.min(100,v)}%`}}/></div></div> }
function Info({k,v}:{k:string,v:string}) { return <div className="info-row"><span>{k}</span><b>{v}</b></div> }

export default App
