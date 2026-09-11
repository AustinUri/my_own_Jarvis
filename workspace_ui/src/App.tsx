import { useEffect, useMemo, useState } from 'react'
import { Responsive, WidthProvider, type Layout, type Layouts } from 'react-grid-layout'
import OrbCanvas from './components/OrbCanvas'
import { useJarvisSocket } from './lib/useJarvisSocket'

const ResponsiveGridLayout = WidthProvider(Responsive)

type WidgetId = 'orb' | 'conversation' | 'activity' | 'sources' | 'system' | 'context' | 'camera' | 'settings'
type WorkspaceName = 'Normal' | 'Research' | 'Developer' | 'Vision' | 'Minimal'

const widgetTitles: Record<WidgetId, string> = {
  orb: 'JARVIS Core', conversation: 'Conversation', activity: 'Agent Activity', sources: 'Sources',
  system: 'System Monitor', context: 'Context', camera: 'Camera', settings: 'Settings',
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
    const raw = localStorage.getItem('jarvis-v23-layouts')
    if (raw) return { ...defaultLayouts, ...JSON.parse(raw) }
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

function Panel({ id, title, onHide, children }: { id: WidgetId, title: string, onHide: (id: WidgetId)=>void, children: React.ReactNode }) {
  const popout = () => window.open(`${location.origin}/?popout=${id}`, `jarvis-${id}`, 'width=720,height=650')
  return <section className="panel">
    <header className="panel-header drag-handle"><span>{title}</span><div className="panel-actions"><button onClick={popout} title="Pop out">↗</button><button onClick={()=>onHide(id)} title="Hide">×</button></div></header>
    <div className="panel-body">{children}</div>
  </section>
}

function CameraWidget() {
  const [active, setActive] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    const video = document.getElementById('camera-video') as HTMLVideoElement | null
    let stream: MediaStream | undefined
    if (active && video) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: false }).then(s => { stream = s; video.srcObject = s }).catch(e => { setError(String(e)); setActive(false) })
    }
    return () => stream?.getTracks().forEach(t => t.stop())
  }, [active])
  return <div className="camera-widget">
    {active ? <video id="camera-video" autoPlay playsInline muted /> : <div className="camera-off">Camera is off<br/><small>Explicit permission only.</small></div>}
    {error && <div className="error-text">{error}</div>}
    <button className="primary" onClick={()=>setActive(v=>!v)}>{active ? 'Disable camera' : 'Enable camera'}</button>
  </div>
}

function App() {
  const { snapshot, metrics, connected, send, patchConfig } = useJarvisSocket()
  const [workspace, setWorkspace] = useState<WorkspaceName>(() => (localStorage.getItem('jarvis-v23-workspace') as WorkspaceName) || 'Normal')
  const [allLayouts, setAllLayouts] = useState<Record<WorkspaceName, Layout[]>>(storedLayouts)
  const [hidden, setHidden] = useState<Record<WorkspaceName, WidgetId[]>>(() => {
    try { return JSON.parse(localStorage.getItem('jarvis-v23-hidden') || '{}') } catch { return {} }
  })
  const [palette, setPalette] = useState(false)
  const [input, setInput] = useState('')
  const [theme, setTheme] = useState(localStorage.getItem('jarvis-v23-theme') || 'amber')
  const [editMode, setEditMode] = useState(true)
  const popout = new URLSearchParams(location.search).get('popout') as WidgetId | null

  useEffect(() => { localStorage.setItem('jarvis-v23-workspace', workspace) }, [workspace])
  useEffect(() => { localStorage.setItem('jarvis-v23-layouts', JSON.stringify(allLayouts)) }, [allLayouts])
  useEffect(() => { localStorage.setItem('jarvis-v23-hidden', JSON.stringify(hidden)) }, [hidden])
  useEffect(() => { localStorage.setItem('jarvis-v23-theme', theme); document.documentElement.dataset.theme = theme }, [theme])
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
    if (!allLayouts[workspace].some(l=>l.i===id)) setAllLayouts(a => ({ ...a, [workspace]: [...a[workspace], { i:id,x:0,y:Infinity,w:4,h:6,minW:3,minH:4 }] }))
  }
  const submit = () => { const text=input.trim(); if (!text) return; send('submit_text',{text}); setInput('') }

  const widget = (id: WidgetId) => {
    if (id === 'orb') return <div className="orb-widget"><OrbCanvas state={snapshot.runtime.assistantState}/><div className="orb-status">{snapshot.runtime.assistantState}</div><div className="orb-sub">{connected ? 'CORE LINKED' : 'CORE OFFLINE'}</div></div>
    if (id === 'conversation') return <div className="conversation-widget">
      <div className="conversation-scroll">
        {snapshot.runtime.transcript && <div className="bubble user"><div className="bubble-label">YOU</div>{snapshot.runtime.transcript}</div>}
        {snapshot.runtime.response && <div className={`bubble jarvis ${snapshot.runtime.responseLanguage==='he'?'rtl':''}`}><div className="bubble-label">JARVIS</div>{snapshot.runtime.response}</div>}
        {!snapshot.runtime.transcript && !snapshot.runtime.response && <div className="empty-copy">Say “Hey Jarvis” or type below.</div>}
      </div>
      <div className="composer"><button className="mic" onClick={()=>send('push_to_talk')}>◉</button><input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&submit()} placeholder="Type or speak to Jarvis…"/><button className="primary" onClick={submit}>Send</button></div>
    </div>
    if (id === 'activity') return <div className="log-list">{logLines.map((l,i)=><div className="log-row" key={i}>{l}</div>)}{!logLines.length&&<div className="empty-copy">No agent activity yet.</div>}</div>
    if (id === 'sources') return <div className="source-list">{sources.map((s,i)=><a href={s.url} target="_blank" key={i}><span>{i+1}</span><div><b>{s.label}</b><small>{s.url}</small></div></a>)}{!sources.length&&<div className="empty-copy">Sources appear here after researched answers.</div>}</div>
    if (id === 'system') return <div className="metric-grid"><Metric name="CPU" value={metrics.cpu}/><Metric name="RAM" value={metrics.ram}/><Metric name="BAT" value={metrics.battery}/></div>
    if (id === 'context') return <div className="context-list"><Info k="AI" v={String(snapshot.config.ai_model_name||'jarvis-qwen')}/><Info k="Provider" v={String(snapshot.config.ai_provider||'LM Studio')}/><Info k="Mic" v={String(snapshot.config.mic_name||'Default')}/><Info k="Wake" v={snapshot.config.wake_word_enabled?'ON':'OFF'}/><Info k="Voice" v={snapshot.config.voice_enabled?'ON':'MUTED'}/><Info k="Web" v={String(snapshot.config.searxng_base_url||'local')}/><Info k="AI status" v={snapshot.aiStatus}/></div>
    if (id === 'camera') return <CameraWidget/>
    if (id === 'settings') return <div className="settings-grid">
      <label>Address me as<input defaultValue={String(snapshot.config.address_name||'sir')} onBlur={e=>patchConfig({address_name:e.target.value})}/></label>
      <label>Tone<select value={String(snapshot.config.tone_mode||'Respectful')} onChange={e=>patchConfig({tone_mode:e.target.value})}><option>Respectful</option><option>Neutral</option><option>Casual</option></select></label>
      <label>Language<select value={String(snapshot.config.language_mode||'Auto')} onChange={e=>patchConfig({language_mode:e.target.value})}><option>Auto</option><option>English</option><option>Hebrew</option></select></label>
      <label>Wake threshold<input type="number" step="0.01" min="0.05" max="0.9" value={Number(snapshot.config.wake_word_threshold||0.15)} onChange={e=>patchConfig({wake_word_threshold:Number(e.target.value)})}/></label>
      <div className="settings-buttons"><button onClick={()=>send('toggle_wake_word')}>Toggle wake word</button><button onClick={()=>send('toggle_voice')}>Mute / unmute</button><button onClick={()=>send('test_microphone')}>Test mic</button><button onClick={()=>send('test_voice')}>Test voice</button><button onClick={()=>send('clear_memory')}>Clear conversation memory</button></div>
    </div>
    return null
  }

  if (popout && widgetTitles[popout]) return <div className="popout-shell"><Panel id={popout} title={widgetTitles[popout]} onHide={()=>window.close()}>{widget(popout)}</Panel></div>

  const items = Array.from(visible)
  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-dot"/>JARVIS <small>v23</small></div>
      <div className="top-status"><span className={`connection ${connected?'ok':'bad'}`}>{connected?'LINKED':'OFFLINE'}</span><span>{snapshot.runtime.assistantState}</span><span>{String(snapshot.config.ai_model_name||'jarvis-qwen')}</span></div>
      <div className="top-actions">
        <select value={workspace} onChange={e=>setWorkspace(e.target.value as WorkspaceName)}>{Object.keys(defaultLayouts).map(w=><option key={w}>{w}</option>)}</select>
        <button onClick={()=>setEditMode(v=>!v)}>{editMode?'Lock layout':'Edit layout'}</button>
        <button onClick={()=>setPalette(true)}>⌘</button>
      </div>
    </header>

    <div className="workspace-toolbar">
      <div className="widget-add"><span>Add widget:</span>{(Object.keys(widgetTitles) as WidgetId[]).filter(id=>!items.includes(id)).map(id=><button key={id} onClick={()=>showWidget(id)}>+ {widgetTitles[id]}</button>)}</div>
      <div className="themes"><button className={theme==='amber'?'active':''} onClick={()=>setTheme('amber')}>Amber</button><button className={theme==='blue'?'active':''} onClick={()=>setTheme('blue')}>FRIDAY</button><button className={theme==='mono'?'active':''} onClick={()=>setTheme('mono')}>Mono</button></div>
    </div>

    <main className={`grid-shell ${editMode?'editing':'locked'}`}>
      <ResponsiveGridLayout
        className="layout" layouts={{lg: allLayouts[workspace]}} breakpoints={{lg:1200,md:900,sm:600,xs:0}} cols={{lg:12,md:10,sm:6,xs:2}}
        rowHeight={42} margin={[12,12]} draggableHandle=".drag-handle" isDraggable={editMode} isResizable={editMode}
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
      <button onClick={()=>{showWidget('camera');setPalette(false)}}>Show Camera</button>
    </div></div>}
  </div>
}

function Metric({name,value}:{name:string,value:number|null}) { const v=value==null?0:value; return <div className="metric"><div className="metric-name">{name}</div><div className="metric-value">{value==null?'—':`${v}%`}</div><div className="meter"><span style={{width:`${Math.min(100,v)}%`}}/></div></div> }
function Info({k,v}:{k:string,v:string}) { return <div className="info-row"><span>{k}</span><b>{v}</b></div> }

export default App
