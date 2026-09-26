const app = document.getElementById('app')
const COLS = 12, ROW = 54, GAP = 12
const WIDGETS = {
  orb:'JARVIS Core', conversation:'Conversation', briefing:'Daily Briefing', weather:'Weather', calendar:'Calendar', sports:'Champions League', learning:'F1 Learning', services:'Runtime Services', phone:'Phone Link', calls:'Call History',
  activity:'Agent Activity', sources:'Sources', system:'System Monitor', context:'Context', camera:'Camera / Vision', agentmesh:'Agent Mesh', engineering:'Engineering Tutor', coding:'Coding JARVIS', settings:'Settings'
}
const SIZE = {
  orb:{w:6,h:9,minW:4,minH:6}, conversation:{w:6,h:10,minW:4,minH:6}, briefing:{w:6,h:10,minW:4,minH:6}, weather:{w:3,h:5,minW:3,minH:4}, calendar:{w:4,h:7,minW:3,minH:5}, sports:{w:5,h:8,minW:3,minH:5}, learning:{w:4,h:6,minW:3,minH:4}, services:{w:3,h:5,minW:3,minH:4}, phone:{w:4,h:7,minW:3,minH:5}, calls:{w:5,h:9,minW:4,minH:6}, activity:{w:5,h:8,minW:4,minH:5},
  sources:{w:5,h:9,minW:3,minH:5}, system:{w:3,h:5,minW:3,minH:4}, context:{w:4,h:5,minW:3,minH:4},
  camera:{w:4,h:7,minW:3,minH:5}, agentmesh:{w:4,h:8,minW:3,minH:5}, engineering:{w:5,h:8,minW:4,minH:6}, coding:{w:5,h:9,minW:4,minH:6}, settings:{w:5,h:8,minW:3,minH:5}
}
const DEFAULT = {
  'Command Center':[p('weather',0,0,3,5,3,4),p('calendar',0,5,3,6,3,5),p('services',0,11,3,5,3,4),p('orb',3,0,6,9,4,6),p('conversation',3,9,6,7,4,5),p('phone',9,0,3,7,3,5),p('briefing',9,7,3,9,3,6)],
  Normal:[p('orb',0,0,6,8,4,6),p('conversation',6,0,6,10,4,6),p('agentmesh',0,8,3,7,3,5),p('activity',3,10,5,5,3,4),p('context',8,10,4,5,3,4)],
  Morning:[p('briefing',0,0,6,11,4,6),p('orb',6,0,6,8,4,6),p('weather',6,8,3,5,3,4),p('calendar',9,8,3,7,3,5)],
  Research:[p('conversation',0,0,6,10,4,6),p('sources',6,0,3,10,3,5),p('activity',9,0,3,10,3,5),p('agentmesh',0,10,4,5,3,4),p('context',4,10,4,5,3,4),p('system',8,10,4,5,3,4)],
  Sports:[p('sports',0,0,7,10,4,6),p('orb',7,0,5,8,4,6),p('briefing',7,8,5,7,3,5),p('conversation',0,10,7,6,4,5)],
  F1:[p('learning',0,0,4,7,3,4),p('orb',4,0,8,9,4,6),p('briefing',0,7,4,8,3,5),p('conversation',4,9,8,6,4,5)],
  Engineering:[p('engineering',0,0,5,11,4,6),p('conversation',5,0,7,8,4,6),p('orb',5,8,4,6,3,4),p('context',9,8,3,6,3,4)],
  Developer:[p('coding',0,0,5,11,4,6),p('conversation',5,0,7,8,4,6),p('agentmesh',5,8,4,5,3,4),p('system',9,8,3,5,3,4)],
  Vision:[p('camera',0,0,8,12,5,7),p('orb',8,0,4,6,3,5),p('conversation',8,6,4,6,3,5)],
  HoloLab:[p('camera',0,0,9,14,6,8),p('conversation',9,0,3,8,3,5),p('orb',9,8,3,6,3,5)],
  'Phone Center':[p('phone',0,0,4,8,3,5),p('calls',4,0,5,10,4,6),p('calendar',9,0,3,10,3,5),p('conversation',0,10,8,6,4,5),p('orb',8,10,4,6,3,4)],
  Mobile:[p('phone',0,0,4,8,3,5),p('calls',0,8,4,8,3,5),p('orb',4,0,8,8,4,6),p('conversation',4,8,8,8,4,5)],
  Minimal:[p('orb',2,0,8,9,4,6),p('conversation',2,9,8,6,4,5)]
}
function p(id,x,y,w,h,minW=2,minH=3){return{id,x,y,w,h,minW,minH}}
function oldOrNew(key){return localStorage.getItem(`jarvis28.${key}`) ?? localStorage.getItem(`jarvis27.${key}`) ?? localStorage.getItem(`jarvis26.${key}`) ?? localStorage.getItem(`jarvis25.${key}`) ?? localStorage.getItem(`jarvis24.${key}`) ?? localStorage.getItem(`jarvis23.${key}`)}
const hadV24Layouts = !!localStorage.getItem('jarvis24.layouts')
const hadV25Layouts = !!localStorage.getItem('jarvis25.layouts')
const hadV26Layouts = !!localStorage.getItem('jarvis26.layouts')
const hadV27Layouts = !!localStorage.getItem('jarvis27.layouts')
const hadV28Layouts = !!localStorage.getItem('jarvis28.layouts')
const oldLayouts = loadJSONMulti(['jarvis23.layouts'], {})
const v26Layouts = loadJSONMulti(['jarvis26.layouts'], {})
const v27Layouts = loadJSONMulti(['jarvis27.layouts'], {})
const migratedLayouts = hadV28Layouts ? loadJSONMulti(['jarvis28.layouts'], structuredClone(DEFAULT)) : {
  ...structuredClone(DEFAULT),
  ...Object.fromEntries(Object.entries(v27Layouts).filter(([name])=>!Object.prototype.hasOwnProperty.call(DEFAULT,name))),
  ...Object.fromEntries(Object.entries(v26Layouts).filter(([name])=>!Object.prototype.hasOwnProperty.call(DEFAULT,name))),
  ...Object.fromEntries(Object.entries(oldLayouts).filter(([name])=>!Object.prototype.hasOwnProperty.call(DEFAULT,name)))
}
for(const [name,layout] of Object.entries(DEFAULT)){if(!migratedLayouts[name])migratedLayouts[name]=structuredClone(layout)}
// v29.2 removes the obsolete V28 Surface Dock card. Native Surface is now a real sibling pane.
delete migratedLayouts.Surface
for(const [name,layout] of Object.entries(migratedLayouts)){if(Array.isArray(layout))migratedLayouts[name]=layout.filter(item=>item?.id!=='surface')}
const state = {
  workspace: oldOrNew('workspace') || 'Command Center',
  layouts: migratedLayouts,
  hidden: hadV28Layouts ? loadJSONMulti(['jarvis28.hidden'], {}) : {},
  theme: oldOrNew('theme') || 'stark', editing:true, connected:false, profileMeta:{},
  runtime:{assistantState:'Idle',transcript:'',response:'',responseLanguage:'en',spoken:'',logs:[],activity:[],error:'',history:[]},
  build:'29.2', config:{}, aiStatus:'Connecting…', capabilities:[], metrics:{cpu:0,ram:0,battery:null}, ws:null,
  cameraStream:null, cameraTimer:null, cameraHasFrame:false, dailyBriefing:{}, weather:{}, calendarStatus:{}, calendarEvents:[], f1Lesson:{}, engineeringStatus:{}, codingStatus:{}, serviceStatus:{}, phoneStatus:{}, phonePairing:{}, phoneTransport:{}, phoneDiagnostics:{}, phoneCallHistory:{ok:false,calls:[]}, selectedCallId:null, agentMesh:{}, surface:loadJSONMulti(['jarvis28.surface','jarvis27.surface'],{url:'',title:'',status:'',frame:'',frameWidth:1100,frameHeight:680,focused:false,suspendedByUser:false,hostWorkspace:''}),
  holo:{enabled:false,shape:'cube',material:'aluminium',widthMm:100,heightMm:100,depthMm:60,x:.5,y:.52,scale:1,angle:0,tilt:0,handDetected:false,twoHands:false,pinch:false,frozen:false,hands:null,handsBusy:false,handsTimer:null,anim:null,dragging:false,lastTest:''},
}
document.documentElement.dataset.theme = state.theme

function loadJSONMulti(keys,fallback){for(const key of keys){try{const raw=localStorage.getItem(key);if(raw)return JSON.parse(raw)}catch{}}return fallback}
let profileSaveTimer=null
function save(){localStorage.setItem('jarvis28.workspace',state.workspace);localStorage.setItem('jarvis28.layouts',JSON.stringify(state.layouts));localStorage.setItem('jarvis28.hidden',JSON.stringify(state.hidden));localStorage.setItem('jarvis28.theme',state.theme);localStorage.setItem('jarvis28.surface',JSON.stringify(state.surface||{}));clearTimeout(profileSaveTimer);profileSaveTimer=setTimeout(persistCurrentProfile,250)}
async function loadProfiles(){try{const r=await fetch('/api/profiles');const profiles=await r.json();for(const [name,p] of Object.entries(profiles||{})){const oldBuiltin=!hadV28Layouts&&!!DEFAULT[name];if(!oldBuiltin&&Array.isArray(p.layout))state.layouts[name]=p.layout;if(!oldBuiltin&&Array.isArray(p.hidden))state.hidden[name]=p.hidden;state.profileMeta[name]=oldBuiltin?{...p,layout:undefined,hidden:undefined}:p}if(!state.layouts[state.workspace])state.workspace='Command Center';const active=state.profileMeta[state.workspace];if(active?.theme){state.theme=active.theme;document.documentElement.dataset.theme=state.theme}renderAll()}catch{}}
async function persistCurrentProfile(){try{await fetch(`/api/profiles/${encodeURIComponent(state.workspace)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:state.workspace,layout:activeLayout(),hidden:activeHidden(),theme:state.theme,updatedAt:new Date().toISOString()})})}catch{}}
async function deleteProfileServer(name){try{await fetch(`/api/profiles/${encodeURIComponent(name)}`,{method:'DELETE'})}catch{}}
if(!hadV28Layouts){state.workspace='Command Center';if(!state.layouts[state.workspace])state.workspace='Normal';save()}
setTimeout(loadProfiles,250)
function send(action,payload={}){if(state.ws?.readyState===1)state.ws.send(JSON.stringify({action,payload}))}

function connect(){
  const proto=location.protocol==='https:'?'wss':'ws'; const ws=new WebSocket(`${proto}://${location.host}/ws`); state.ws=ws
  ws.onopen=()=>{state.connected=true;renderTop()}
  ws.onclose=()=>{state.connected=false;renderTop();setTimeout(connect,1200)}
  ws.onmessage=e=>{try{handleMessage(JSON.parse(e.data))}catch{}}
}
function handleMessage(m){const t=m.type,v=m.payload
  if(t==='snapshot'){Object.assign(state,v);document.title=`JARVIS Control Center v${v.build||v.version||'29.2'}`;state.runtime=v.runtime||state.runtime;state.runtime.activity=v.activity||state.runtime.activity||[];state.config=v.config||{};state.dailyBriefing=v.dailyBriefing||state.dailyBriefing;state.weather=v.weather||state.weather;state.calendarStatus=v.calendarStatus||state.calendarStatus;state.calendarEvents=v.calendarEvents||state.calendarEvents;state.f1Lesson=v.f1Lesson||state.f1Lesson;state.engineeringStatus=v.engineeringStatus||state.engineeringStatus;state.codingStatus=v.codingStatus||state.codingStatus;state.serviceStatus=v.serviceStatus||state.serviceStatus;state.phoneStatus=v.phoneStatus||state.phoneStatus;state.phonePairing=v.phonePairing||state.phonePairing;state.phoneTransport=v.phoneTransport||state.phoneTransport;state.phoneDiagnostics=v.phoneDiagnostics||state.phoneDiagnostics;state.phoneCallHistory=v.phoneCallHistory||state.phoneCallHistory;state.agentMesh=v.agentMesh||state.agentMesh;renderAll()}
  else if(t==='state'){state.runtime.assistantState=v;renderTop();renderWidget('orb')}
  else if(t==='transcript'){state.runtime.transcript=v.text||'';state.runtime.responseLanguage=v.language||'en';renderWidget('conversation')}
  else if(t==='response'){state.runtime.response=v.text||'';state.runtime.responseLanguage=v.language||'en';renderWidget('conversation');renderWidget('sources')}
  else if(t==='spoken'){state.runtime.spoken=v||''}
  else if(t==='log'){state.runtime.logs=[...state.runtime.logs,String(v)].slice(-300)}
  else if(t==='activity'){state.runtime.activity=[...(state.runtime.activity||[]),v].slice(-400);renderWidget('activity')}
  else if(t==='error'){state.runtime.error=String(v||'');renderWidget('context')}
  else if(t==='config'){state.config=v||{};renderTop();renderWidget('context');renderWidget('settings')}
  else if(t==='ai_status'){state.aiStatus=String(v||'');renderWidget('context')}
  else if(t==='daily_briefing'){state.dailyBriefing=v||{};renderWidget('briefing');renderWidget('sports')}
  else if(t==='weather'){state.weather=v||{};renderWidget('weather')}
  else if(t==='calendar_status'){state.calendarStatus=v||{};renderWidget('calendar')}
  else if(t==='calendar_events'){state.calendarEvents=Array.isArray(v)?v:[];renderWidget('calendar')}
  else if(t==='f1_lesson'){state.f1Lesson=v||{};renderWidget('learning')}
  else if(t==='engineering_status'){state.engineeringStatus=v||{};renderWidget('engineering')}
  else if(t==='coding_status'){state.codingStatus=v||{};renderWidget('coding')}
  else if(t==='service_status'){state.serviceStatus=v||{};renderWidget('services');renderTop()}
  else if(t==='phone_status'){state.phoneStatus=v||{};renderWidget('phone');renderWidget('calendar')}
  else if(t==='phone_pairing'){state.phonePairing=v||{};renderWidget('phone')}
  else if(t==='phone_transport'){state.phoneTransport=v||{};renderWidget('phone')}
  else if(t==='phone_diagnostics'){state.phoneDiagnostics=v||{};renderWidget('phone')}
  else if(t==='phone_call_history'){state.phoneCallHistory=v||{ok:false,calls:[]};renderWidget('calls')}
  else if(t==='agent_mesh'){state.agentMesh=v||{};renderWidget('agentmesh');renderWidget('orb');renderTop()}
  else if(t==='system_metrics'){state.metrics=v||state.metrics;renderWidget('system');renderWidget('agentmesh');renderTop()}
  else if(t==='conversation_history'){state.runtime.history=Array.isArray(v)?v:[];renderWidget('conversation')}
  else if(t==='camera_status'){state.cameraHasFrame=!!v?.hasFrame;renderTop();renderWidget('context')}
  else if(t==='surface_status'){if(v?.url&&/^https?:\/\//i.test(String(v.url)))state.surface.url=String(v.url);if(v?.title)state.surface.title=String(v.title);state.surface.status=String(v?.message||v?.error||'');renderWidget('surface')}
  else if(t==='surface_frame'){if(v?.url&&/^https?:\/\//i.test(String(v.url))){state.surface.url=String(v.url);const input=document.querySelector('[data-surface-url]');if(input)input.value=state.surface.url}if(v?.title)state.surface.title=String(v.title);if(v?.data_url){state.surface.frame=String(v.data_url);state.surface.frameWidth=Number(v.width||1100);state.surface.frameHeight=Number(v.height||680);const img=document.querySelector('[data-surface-frame]');if(img)img.src=state.surface.frame;const empty=document.querySelector('[data-surface-empty]');if(empty)empty.style.display='none'}if(v?.error){state.surface.status=String(v.error);const status=document.querySelector('[data-surface-status]');if(status)status.textContent=state.surface.status}}
  else if(t==='hololab_result'){const tests=Array.isArray(v?.tests)?v.tests:[];state.holo.lastTest=tests.map(x=>`${x.name}: ${String(x.status).toUpperCase()}`).join(' · ')+(v?.disclaimer?` · ${v.disclaimer}`:'');renderWidget('camera')}
  else if(t==='surface_layout_hint'){fitSurfaceWorkspace(v||{},false)}
  else if(t==='ui_command'){handleUiCommand(v)}
}
function handleUiCommand(v){const a=v?.action,payload=v?.payload||{}
  if(a==='ui_show_panel')showWidget(String(payload.panel||''))
  if(a==='ui_hide_panel')hideWidget(String(payload.panel||''))
  if(a==='ui_switch_workspace'){
    const requested=String(payload.workspace||'').trim()
    const normalized=requested.toLowerCase().replace(/[ _-]+/g,'')
    const alias=normalized==='hololab'||normalized==='hologram'||normalized==='spatialfabricator'?'HoloLab':null
    const match=alias||Object.keys(state.layouts).find(k=>k.toLowerCase()===requested.toLowerCase())
    if(match)applyWorkspace(match)
    else state.runtime.error=`Workspace not found: ${requested}`
  }
  if(a==='ui_create_workspace'){const w=String(payload.workspace||'').trim();if(w){state.layouts[w]=structuredClone(activeLayout());state.hidden[w]=structuredClone(activeHidden());state.profileMeta[w]={theme:state.theme};applyWorkspace(w)}}
  if(a==='ui_open_surface'){openSurface(String(payload.target||''),String(payload.title||''))}
  if(a==='ui_hololab_config'){
    applyWorkspace('HoloLab');state.holo.enabled=payload.enabled!==false
    if(payload.shape)state.holo.shape=String(payload.shape).toLowerCase()
    if(payload.material)state.holo.material=String(payload.material).toLowerCase()
    if(Number(payload.width_mm)>0)state.holo.widthMm=Number(payload.width_mm)
    if(Number(payload.height_mm)>0)state.holo.heightMm=Number(payload.height_mm)
    if(Number(payload.depth_mm)>0)state.holo.depthMm=Number(payload.depth_mm)
    renderWidget('camera')
  }
}

function renderAll(){
  const pop=new URLSearchParams(location.search).get('popout')
  if(pop&&WIDGETS[pop])return renderPopout(pop)
  app.innerHTML=`<div class="app"><div id="top"></div><div id="toolbar"></div><div class="workspace-wrap"><div id="workspace" class="workspace ${state.editing?'editing':''}"></div></div></div>`
  renderTop();renderToolbar();renderWorkspace();bindGlobalKeys()
}
function renderTop(){const el=document.getElementById('top');if(!el)return
  const mesh=state.agentMesh||{},active=Array.isArray(mesh.active)?mesh.active.length:0,gov=String(state.metrics?.state||'normal').toUpperCase()
  el.className='topbar';el.innerHTML=`<div class="brand"><span class="brand-dot"></span>JARVIS <small>v${esc(state.build||'29.2')} · HOLO CORE</small></div><div class="statusline"><span class="${state.connected?'link-ok':'link-bad'}">${state.connected?'CORE LINKED':'OFFLINE'}</span><span>${esc(state.runtime.assistantState)}</span><span>${esc(state.config.ai_model_name||'jarvis-qwen')}</span><span class="agent-mini">AGENTS ${active}/${mesh.registered||47}</span><span class="governor-mini gov-${String(state.metrics?.state||'normal')}">${esc(gov)}</span>${state.cameraHasFrame?'<span class="vision-top">VISION</span>':''}<span class="service-mini">WEB:${esc((state.serviceStatus?.searxng||'').toUpperCase()||'—')}</span></div><div class="top-actions"><select id="workspaceSelect">${Object.keys(state.layouts).map(w=>`<option ${w===state.workspace?'selected':''}>${w}</option>`).join('')}</select><button id="editToggle">${state.editing?'Lock layout':'Edit layout'}</button><button id="paletteBtn" title="Ctrl+K">⌘K</button></div>`
  qs('#workspaceSelect',el).onchange=e=>applyWorkspace(e.target.value)
  qs('#editToggle',el).onclick=()=>{state.editing=!state.editing;renderTop();renderWorkspace()}
  qs('#paletteBtn',el).onclick=showPalette
}
function renderToolbar(){const el=document.getElementById('toolbar');if(!el)return;el.className='toolbar'
  const visible=new Set(activeLayout().filter(x=>!activeHidden().includes(x.id)).map(x=>x.id)); const missing=Object.keys(WIDGETS).filter(id=>!visible.has(id))
  el.innerHTML=`<div class="widget-buttons"><span class="label">ADD WIDGET</span>${missing.map(id=>`<button data-add="${id}">+ ${WIDGETS[id]}</button>`).join('')}</div><div class="theme-buttons"><button data-theme="stark" class="${state.theme==='stark'?'active':''}">Stark Glass</button><button data-theme="blue" class="${state.theme==='blue'?'active':''}">FRIDAY</button><button data-theme="mono" class="${state.theme==='mono'?'active':''}">Mono</button><button id="saveAsLayout">Save As…</button><button id="deleteLayout">Delete</button><button id="resetLayout">Reset</button></div>`
  el.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>showWidget(b.dataset.add))
  el.querySelectorAll('[data-theme]').forEach(b=>b.onclick=()=>{state.theme=b.dataset.theme;state.profileMeta[state.workspace]={...(state.profileMeta[state.workspace]||{}),theme:state.theme};document.documentElement.dataset.theme=state.theme;save();renderToolbar()})
  qs('#saveAsLayout',el).onclick=()=>{const name=(prompt('Name this workspace:',`${state.workspace} Copy`)||'').trim();if(!name)return;state.layouts[name]=structuredClone(activeLayout());state.hidden[name]=structuredClone(activeHidden());state.profileMeta[name]={theme:state.theme};state.workspace=name;save();renderAll()}
  qs('#deleteLayout',el).onclick=()=>{if(DEFAULT[state.workspace])return alert('Built-in workspaces cannot be deleted.');if(!confirm(`Delete workspace “${state.workspace}”?`))return;const doomed=state.workspace;delete state.layouts[doomed];delete state.hidden[doomed];delete state.profileMeta[doomed];deleteProfileServer(doomed);state.workspace='Command Center';save();renderAll()}
  qs('#resetLayout',el).onclick=()=>{const base=DEFAULT[state.workspace]||DEFAULT.Normal;state.layouts[state.workspace]=structuredClone(base);state.hidden[state.workspace]=[];save();renderToolbar();renderWorkspace()}
}
function activeLayout(){return state.layouts[state.workspace]||structuredClone(DEFAULT[state.workspace])}
function activeHidden(){return state.hidden[state.workspace]||[]}
function applyWorkspace(name){if(!state.layouts[name])return;state.workspace=name;const meta=state.profileMeta[name]||{};if(meta.theme){state.theme=meta.theme;document.documentElement.dataset.theme=state.theme}save();renderAll();if(name==='Phone Center'){send('phone_status');send('phone_call_history',{limit:30});send('refresh_calendar',{days:7})}}
function renderWorkspace(){const ws=document.getElementById('workspace');if(!ws)return;ws.className=`workspace ${state.editing?'editing':''}`;ws.innerHTML=''
  const items=activeLayout().filter(i=>!activeHidden().includes(i.id));items.forEach(item=>ws.appendChild(makeWidget(item)))
  positionAll();const maxY=Math.max(12,...items.map(i=>i.y+i.h));ws.style.minHeight=`${maxY*ROW+GAP}px`
}
function makeWidget(item){const el=document.createElement('section');el.className='widget';el.dataset.id=item.id
  el.innerHTML=`<header class="widget-header"><span>${WIDGETS[item.id]}</span><div class="widget-actions"><button data-full title="Fullscreen">⛶</button><button data-pop title="Pop out">↗</button><button data-hide title="Hide">×</button></div></header><div class="widget-body"></div><div class="resize-handle"></div>`
  qs('[data-hide]',el).onclick=()=>hideWidget(item.id);qs('[data-pop]',el).onclick=()=>window.open(`${location.origin}/?popout=${item.id}`,`jarvis-${item.id}`,'width=820,height=700');qs('[data-full]',el).onclick=()=>el.classList.toggle('fullscreen-widget')
  if(state.editing){makeDraggable(el,item);makeResizable(el,item)}renderWidgetInto(el,item.id);return el
}
function positionAll(){const ws=document.getElementById('workspace');if(!ws)return;const width=ws.clientWidth,cw=width/COLS
  ws.querySelectorAll('.widget').forEach(el=>{const item=activeLayout().find(x=>x.id===el.dataset.id);if(!item)return;if(item.id==='surface'&&state.surface?.focused&&state.surface?.hostWorkspace===state.workspace){const cols=clamp(Number(state.surface.focusCols||10),7,11),rows=clamp(Number(state.surface.focusRows||11),8,14);el.style.left=`${GAP/2}px`;el.style.top=`${GAP/2}px`;el.style.width=`${Math.max(640,cols*cw-GAP)}px`;el.style.height=`${Math.max(480,rows*ROW-GAP)}px`;el.style.zIndex='40';el.classList.add('surface-focused-widget')}else{el.style.left=`${Math.round(item.x*cw)+GAP/2}px`;el.style.top=`${item.y*ROW+GAP/2}px`;el.style.width=`${Math.max(180,item.w*cw-GAP)}px`;el.style.height=`${Math.max(180,item.h*ROW-GAP)}px`;el.style.zIndex='';el.classList.remove('surface-focused-widget')}})
}
function makeDraggable(el,item){const h=qs('.widget-header',el);h.onpointerdown=e=>{if(e.target.closest('button'))return;h.setPointerCapture(e.pointerId);const ws=document.getElementById('workspace'),cw=ws.clientWidth/COLS,sx=e.clientX,sy=e.clientY,ox=item.x,oy=item.y
  const move=ev=>{item.x=clamp(Math.round(ox+(ev.clientX-sx)/cw),0,COLS-item.w);item.y=Math.max(0,Math.round(oy+(ev.clientY-sy)/ROW));positionAll()};const up=()=>{h.onpointermove=null;h.onpointerup=null;save()};h.onpointermove=move;h.onpointerup=up}}
function makeResizable(el,item){const r=qs('.resize-handle',el);r.onpointerdown=e=>{e.stopPropagation();r.setPointerCapture(e.pointerId);const ws=document.getElementById('workspace'),cw=ws.clientWidth/COLS,sx=e.clientX,sy=e.clientY,ow=item.w,oh=item.h
  r.onpointermove=ev=>{item.w=clamp(Math.round(ow+(ev.clientX-sx)/cw),2,COLS-item.x);item.h=Math.max(3,Math.round(oh+(ev.clientY-sy)/ROW));positionAll()};r.onpointerup=()=>{r.onpointermove=null;r.onpointerup=null;save()}}}
function rectsOverlap(a,b){return !(a.x+a.w<=b.x||b.x+b.w<=a.x||a.y+a.h<=b.y||b.y+b.h<=a.y)}
function smartInsert(id){const layout=activeLayout();if(layout.some(x=>x.id===id))return
  const d=SIZE[id]||{w:4,h:6,minW:3,minH:4},bottom=Math.max(1,...layout.map(x=>x.y+x.h))
  for(let y=0;y<=bottom;y++)for(let x=0;x<=COLS-d.w;x++){const c={x,y,w:d.w,h:d.h};if(y+d.h<=bottom&&!layout.some(item=>rectsOverlap(item,c))){layout.push(p(id,x,y,d.w,d.h,d.minW,d.minH));return}}
  const targets=[...layout].filter(x=>x.w-(x.minW||2)>=d.minW&&x.h>=d.minH).sort((a,b)=>(b.w*b.h)-(a.w*a.h));const t=targets[0]
  if(t){const right=Math.max(d.minW,Math.floor(t.w/2)),left=t.w-right;if(left>=(t.minW||2)){t.w=left;layout.push(p(id,t.x+left,t.y,right,Math.max(d.minH,t.h),d.minW,d.minH));return}}
  let bx=0,by=1e9;for(let x=0;x<=COLS-d.w;x++){const y=layout.filter(it=>!(it.x+it.w<=x||x+d.w<=it.x)).reduce((m,it)=>Math.max(m,it.y+it.h),0);if(y<by){bx=x;by=y}}layout.push(p(id,bx,by,d.w,d.h,d.minW,d.minH))
}
function showWidget(id){if(!WIDGETS[id])return;state.hidden[state.workspace]=activeHidden().filter(x=>x!==id);smartInsert(id);save();renderToolbar();renderWorkspace()}
function hideWidget(id){state.hidden[state.workspace]=[...new Set([...activeHidden(),id])];if(id==='camera'&&state.cameraStream)stopCamera();save();renderToolbar();renderWorkspace()}
function renderWidget(id){const el=document.querySelector(`.widget[data-id="${CSS.escape(id)}"]`);if(el)renderWidgetInto(el,id);const pop=document.querySelector(`.popout .widget[data-id="${CSS.escape(id)}"]`);if(pop)renderWidgetInto(pop,id)}
function renderWidgetInto(el,id){const body=qs('.widget-body',el);if(!body)return
  if(id==='orb')renderOrb(body)
  else if(id==='conversation')renderConversation(body)
  else if(id==='briefing')renderBriefing(body)
  else if(id==='weather')renderWeather(body)
  else if(id==='calendar')renderCalendar(body)
  else if(id==='sports')renderSports(body)
  else if(id==='learning')renderLearning(body)
  else if(id==='services')renderServices(body)
  else if(id==='phone')renderPhone(body)
  else if(id==='calls')renderCalls(body)
  else if(id==='activity')renderActivity(body)
  else if(id==='sources')renderSources(body)
  else if(id==='system')renderSystem(body)
  else if(id==='context')renderContext(body)
  else if(id==='camera')renderCamera(body)
  else if(id==='agentmesh')renderAgentMesh(body)
  else if(id==='surface')renderSurface(body)
  else if(id==='engineering')renderEngineering(body)
  else if(id==='coding')renderCoding(body)
  else if(id==='settings')renderSettings(body)
}

const _corePalette={idle:['#71e7ff','#ffbc62'],listening:['#7fffe1','#63ddff'],thinking:['#ffc76a','#79e7ff'],speaking:['#ffd07b','#73efff'],error:['#ff6f6f','#ffbe72'],disabled:['#607784','#8ba0a8']}
function _coreMode(){const raw=String(state.runtime?.assistantState||'idle').toLowerCase();if(raw.includes('listen'))return'listening';if(raw.includes('think')||raw.includes('transcrib'))return'thinking';if(raw.includes('speak'))return'speaking';if(raw.includes('error'))return'error';if(raw.includes('disable'))return'disabled';return'idle'}
function _hexToRgb(hex){const h=String(hex).replace('#','');return{r:parseInt(h.slice(0,2),16),g:parseInt(h.slice(2,4),16),b:parseInt(h.slice(4,6),16)}}
function renderOrb(body){
  const mode=_coreMode(),mesh=state.agentMesh||{},active=Array.isArray(mesh.active)?mesh.active.length:0,gov=String(state.metrics?.state||'normal').toUpperCase()
  body.innerHTML=`<div class="orb-box neutrino-core" data-core-mode="${attr(mode)}"><canvas class="neutrino-canvas"></canvas><div class="core-vignette"></div><div class="core-title">JARVIS · NEUTRINO CORE</div><div class="core-center-mark"><i></i><span></span><b></b></div><div class="core-readout"><strong>${esc(String(state.runtime?.assistantState||'Idle').toUpperCase())}</strong><small>${active} specialist${active===1?'':'s'} active · governor ${esc(gov)}</small></div><div class="core-caption">PARTICLE INTELLIGENCE FIELD · v${esc(state.build||'29.2')}</div></div>`
  const canvas=qs('.neutrino-canvas',body);if(canvas)startNeutrinoCore(canvas)
}
function startNeutrinoCore(canvas){
  const ctx=canvas.getContext('2d',{alpha:true});if(!ctx)return
  let w=0,h=0,dpr=1,raf=0,last=performance.now(),time=0
  const seeds=Array.from({length:260},(_,i)=>({i,u:(i+.5)/260,a:((i*2.399963229728653)%6.283185307),phase:Math.random()*Math.PI*2,band:i%11,kind:i%17===0?'satellite':i%5===0?'ring':'shell'}))
  const resize=()=>{const r=canvas.getBoundingClientRect();dpr=Math.min(2,window.devicePixelRatio||1);w=Math.max(1,r.width);h=Math.max(1,r.height);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0)}
  const drawRing=(cx,cy,rx,ry,rot,alpha,color)=>{ctx.save();ctx.translate(cx,cy);ctx.rotate(rot);ctx.strokeStyle=color;ctx.globalAlpha=alpha;ctx.lineWidth=1;ctx.setLineDash([2,7]);ctx.beginPath();ctx.ellipse(0,0,rx,ry,0,0,Math.PI*2);ctx.stroke();ctx.restore();ctx.globalAlpha=1;ctx.setLineDash([])}
  const frame=now=>{if(!canvas.isConnected){cancelAnimationFrame(raf);return}if(Math.abs(canvas.getBoundingClientRect().width-w)>1||Math.abs(canvas.getBoundingClientRect().height-h)>1)resize();const dt=Math.min(.05,(now-last)/1000);last=now;time+=dt
    const mode=_coreMode(),pal=_corePalette[mode]||_corePalette.idle,c1=_hexToRgb(pal[0]),c2=_hexToRgb(pal[1]),cx=w*.5,cy=h*.49,base=Math.min(w,h)*.28
    const speed=mode==='thinking'?1.8:mode==='listening'?1.18:mode==='speaking'?1.35:mode==='error'?1.65:.72
    const pulse=1+(mode==='speaking'?Math.sin(time*12)*.055:mode==='listening'?Math.sin(time*6)*.022:Math.sin(time*2.4)*.012)
    ctx.clearRect(0,0,w,h)
    const glow=ctx.createRadialGradient(cx,cy,0,cx,cy,base*1.75);glow.addColorStop(0,`rgba(${c2.r},${c2.g},${c2.b},.12)`);glow.addColorStop(.35,`rgba(${c1.r},${c1.g},${c1.b},.055)`);glow.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h)
    drawRing(cx,cy,base*1.06*pulse,base*.34, time*.11*speed,.22,pal[1]);drawRing(cx,cy,base*.82*pulse,base*.82, -time*.08*speed,.13,pal[0]);drawRing(cx,cy,base*1.28,base*.18,-time*.17*speed,.12,pal[1])
    const projected=[]
    for(const p of seeds){let x,y,z,alpha=1,size=1
      if(p.kind==='ring'){const aa=p.a+time*(.22+.03*(p.band%3))*speed, rr=base*(.78+.18*Math.sin(p.phase+p.band));x=Math.cos(aa)*rr;y=Math.sin(aa)*rr*.28;z=Math.sin(aa+p.phase)*base*.22;alpha=.45;size=1.05}
      else if(p.kind==='satellite'){const aa=p.a-time*(.34+.02*p.band)*speed,rr=base*(1.24+.12*Math.sin(p.phase+time*.7));x=Math.cos(aa)*rr;y=Math.sin(aa*1.13+p.phase)*base*.57;z=Math.sin(aa)*base*.5;alpha=.68;size=1.5}
      else{const zz=1-2*p.u,rad=Math.sqrt(Math.max(0,1-zz*zz)),aa=p.a+time*(.12+.008*p.band)*speed;x=rad*Math.cos(aa)*base*pulse;y=zz*base*pulse;z=rad*Math.sin(aa)*base*pulse;const warp=.12*Math.sin(time*1.3+p.phase+p.band);x*=1+warp;y*=1-warp*.35;alpha=.5+.42*((z/base+1)/2);size=.8+1.05*((z/base+1)/2)}
      const perspective=1+z/(base*3.3),sx=cx+x*perspective,sy=cy+y*perspective*.93
      projected.push({sx,sy,z,alpha,size,p})
    }
    projected.sort((a,b)=>a.z-b.z)
    for(let i=0;i<projected.length;i++){const q=projected[i],mix=(q.p.band%7)/6,r=Math.round(c1.r*(1-mix)+c2.r*mix),g=Math.round(c1.g*(1-mix)+c2.g*mix),b=Math.round(c1.b*(1-mix)+c2.b*mix),bright=mode==='thinking'&&q.p.band%9===0?1.7:mode==='speaking'&&q.p.band%6===0?1.45:1
      if(i%18===0){ctx.strokeStyle=`rgba(${r},${g},${b},${.05*q.alpha})`;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(q.sx,q.sy);ctx.stroke()}
      ctx.fillStyle=`rgba(${r},${g},${b},${Math.min(.95,q.alpha*bright)})`;ctx.shadowColor=`rgba(${r},${g},${b},.65)`;ctx.shadowBlur=mode==='thinking'?8:mode==='speaking'?7:5;ctx.beginPath();ctx.arc(q.sx,q.sy,q.size*bright,0,Math.PI*2);ctx.fill()
    }
    ctx.shadowBlur=0
    const active=Array.isArray(state.agentMesh?.active)?Math.min(8,state.agentMesh.active.length):0
    for(let i=0;i<active;i++){const a=time*(.42+.04*i)+(i/Math.max(1,active))*Math.PI*2,rr=base*(1.38+.04*(i%3)),x=cx+Math.cos(a)*rr,y=cy+Math.sin(a)*rr*.35;ctx.strokeStyle=`rgba(${c2.r},${c2.g},${c2.b},.2)`;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(x,y);ctx.stroke();ctx.fillStyle=`rgba(${c2.r},${c2.g},${c2.b},.92)`;ctx.beginPath();ctx.arc(x,y,2.2,0,Math.PI*2);ctx.fill()}
    raf=requestAnimationFrame(frame)
  }
  resize();raf=requestAnimationFrame(frame)
}

function renderActivity(body){
  const rows=Array.isArray(state.runtime.activity)?state.runtime.activity:[]
  const recent=rows.slice(-140)
  const last=recent.length?recent[recent.length-1].seq:0
  body.innerHTML=`<div class="activity-head"><div><b>ORDERED EXECUTION TRACE</b><small>${recent.length} events · latest #${last||'—'}</small></div><span class="activity-live">LIVE</span></div><div class="activity-list">${recent.length?recent.map(e=>{const time=e.timestamp?new Date(e.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}):'';return `<div class="activity-row status-${attr(e.status||'info')}"><div class="activity-seq">#${String(e.seq||0).padStart(3,'0')}</div><div class="activity-time">${esc(time)}</div><div class="activity-main"><div><span class="activity-cat">${esc(String(e.category||'system').toUpperCase())}</span><span class="activity-status">${esc(String(e.status||'info').toUpperCase())}</span><b>${esc(e.title||'Activity')}</b></div>${e.detail?`<p>${esc(e.detail)}</p>`:''}</div></div>`}).join(''):'<div class="empty">No agent activity yet. The next request will appear here in execution order.</div>'}</div>`
  const list=qs('.activity-list',body);if(list)list.scrollTop=list.scrollHeight
}
function renderPhone(body){
  const st=state.phoneStatus||{},pair=state.phonePairing||{},transport=state.phoneTransport||{},diag=state.phoneDiagnostics||{},devices=Array.isArray(st.devices)?st.devices:[]
  const device=devices[0]||{},connected=!!st.connected,paired=!!st.paired,pairActive=!!pair.code
  const diagBits=diag.phone_function?`<div class="phone-diagnostics"><div><span>Phone function</span><b class="${diag.error?'warn':'ok'}">${esc(diag.phone_function)}</b></div><small>${esc(diag.error||JSON.stringify(diag.result||{}))}</small></div>`:(Object.keys(diag).length?`<div class="phone-diagnostics"><div><span>PC bridge</span><b class="${diag.local_bridge_ok?'ok':'warn'}">${diag.local_bridge_ok?'READY':'OFFLINE'}</b></div><div><span>Tailscale Serve</span><b class="${diag.serve_ok?'ok':'warn'}">${diag.serve_ok?'READY':'CHECK'}</b></div><div><span>Private URL</span><b>${esc(diag.server_url||st.server_url||'—')}</b></div><div><span>DNS fallback IP</span><b>${esc(diag.tailscale_ipv4||st.tailscale_ipv4||transport.tailscale_ipv4||'—')}</b></div>${diag.local_bridge_detail?`<small>${esc(diag.local_bridge_detail)}</small>`:''}</div>`:'')
  body.innerHTML=`<div class="phone-card"><div class="phone-status"><span class="${connected?'ok':paired?'warn':'off'}"></span><div><b>${connected?'PHONE CONNECTED':paired?'PAIRED — WAITING FOR COMPANION':'NO TRUSTED PHONE'}</b><small>${esc(device.name||'Android companion not linked')}</small></div></div><div class="phone-grid"><span>Transport<b>${esc(st.transport||'Tailscale Serve HTTPS')}</b></span><span>Security<b>${esc(st.security||'ECDSA device identity')}</b></span><span>Server<b>${esc(st.server_url||transport.server_url||'Not ready')}</b></span><span>Fallback IP<b>${esc(st.tailscale_ipv4||transport.tailscale_ipv4||'—')}</b></span><span>Calendar<b>${connected?'Native phone calendar available':'Not available'}</b></span></div>${transport.message?`<div class="phone-note ${transport.ok?'ok-note':'warn-note'}">${esc(transport.message)}</div>`:''}${diagBits}${pairActive?`<div class="pair-box"><small>PAIRING CODE · ${esc(String(pair.minutes||5))} MINUTES</small><strong>${esc(pair.code)}</strong><span>${esc(pair.server_url||st.server_url||'Prepare private link first')}</span><span class="pair-ip">Fallback IP: ${esc(pair.tailscale_ipv4||st.tailscale_ipv4||transport.tailscale_ipv4||'—')}</span></div>`:''}<div class="phone-actions"><button data-phone="prepare">Prepare private link</button><button data-phone="diagnose">Test PC link</button><button class="primary" data-phone="pair">Create pairing code</button><button data-phone="refresh">Refresh</button>${connected?'<button data-phone="device">Read phone info</button><button data-phone="battery">Phone battery</button><button data-phone="history">Call history</button><button data-phone="find">Find contact</button><button data-phone="call">Call contact</button><button data-phone="whatsapp">WhatsApp</button>':''}${paired?'<button class="danger" data-phone="revoke">Revoke phone</button>':''}</div><div class="phone-foot">v29.2 keeps the secure .ts.net link, local Whisper phone voice, duplicate-safe contacts, call history, cellular dial/handoff and keyless WhatsApp message composition. Conversation summaries still require real audio/transcript data.</div></div>`
  body.querySelectorAll('[data-phone]').forEach(btn=>btn.onclick=()=>{const a=btn.dataset.phone;if(a==='prepare')send('phone_prepare');else if(a==='diagnose')send('phone_diagnose');else if(a==='pair')send('phone_pair');else if(a==='refresh')send('phone_status');else if(a==='device')send('phone_device_info');else if(a==='battery')send('phone_battery');else if(a==='history')send('phone_call_history',{limit:30});else if(a==='find'){const q=(prompt('Contact name to find:')||'').trim();if(q)send('submit_text',{text:`Find ${q} in my phone contacts.`})}else if(a==='call'){const q=(prompt('Contact name to call:')||'').trim();if(q)send('submit_text',{text:`Call ${q} on my phone.`})}else if(a==='whatsapp'){const q=(prompt('WhatsApp contact name:')||'').trim();if(!q)return;const m=(prompt(`Message for ${q}:`)||'').trim();if(m)send('submit_text',{text:`WhatsApp ${q} and say: ${m}`})}else if(a==='revoke'&&confirm('Revoke every paired JARVIS phone?'))send('phone_revoke_all')})
}

function renderAgentMesh(body){
  const mesh=state.agentMesh||{},profiles=Array.isArray(mesh.profiles)?mesh.profiles:[],active=new Set(Array.isArray(mesh.active)?mesh.active:[]),r=state.metrics||mesh.resource||{}
  const phase=String(mesh.phase||'idle').toUpperCase(),limit=Number(r.active_agent_limit||state.config.agent_max_active_specialists||6),parallel=Number(r.llm_parallel_limit||mesh.max_parallel_llm||2)
  body.innerHTML=`<div class="mesh-head"><div><b>${mesh.registered||47} SPECIALIST IDENTITIES</b><small>Shared model · only relevant specialists wake up</small></div><span class="mesh-phase">${esc(phase)}</span></div><div class="mesh-orbit">${profiles.map((p,i)=>`<div class="agent-node ${active.has(p.id)?'active':''}" title="${attr(p.domain||'')}" style="--i:${i};--n:${Math.max(1,profiles.length)}"><i></i><span>${esc(p.name)}</span></div>`).join('')}</div><div class="mesh-footer"><span>Active <b>${active.size}</b> / ${limit}</span><span>LLM parallel cap <b>${parallel}</b></span><span>Governor <b class="gov-${attr(String(r.state||'normal'))}">${esc(String(r.state||'normal').toUpperCase())}</b></span></div>`
}

function normalizeSurfaceTarget(raw){let v=String(raw||'').trim();if(!v||v.toLowerCase()==='about:blank')return'';if(!/^https?:\/\//i.test(v)){if(/^[a-z0-9.-]+\.[a-z]{2,}/i.test(v))v='https://'+v;else v='https://www.google.com/search?q='+encodeURIComponent(v)}try{const u=new URL(v);if(!/^https?:$/.test(u.protocol))return'';return u.href}catch{return''}}
function surfacePresetFromUrl(url){
  try{
    const h=new URL(url).hostname.toLowerCase()
    if(/youtube\.com|netflix\.com|twitch\.tv|vimeo\.com/.test(h))return{cols:10,rows:12,kind:'video',reason:'video site'}
    if(/github\.com|gitlab\.com|stackoverflow\.com|notion\.so/.test(h)||h.startsWith('docs.'))return{cols:10,rows:13,kind:'work',reason:'code/document workspace'}
    if(/mail\.google\.com|outlook\.|calendar\.google\.com/.test(h))return{cols:10,rows:12,kind:'app',reason:'web application'}
    if(/google\.|bing\.com|duckduckgo\.com/.test(h))return{cols:9,rows:10,kind:'search',reason:'search page'}
  }catch{}
  return{cols:10,rows:11,kind:'web',reason:'general website'}
}
function fitSurfaceWorkspace(hint={},force=true){
  const cols=clamp(Math.round(Number(hint.cols||10)),7,11),rows=clamp(Math.round(Number(hint.rows||11)),8,14)
  if(!force&&(state.surface?.suspendedByUser||state.surface?.hostWorkspace!==state.workspace))return
  const prev=state.surface?.layoutHint||{}
  if(!force&&state.surface?.focused&&Number(prev.cols)===cols&&Number(prev.rows)===rows){state.surface={...(state.surface||{}),layoutHint:{...hint,cols,rows}};return}
  state.surface={...(state.surface||{}),focused:true,suspendedByUser:false,hostWorkspace:state.workspace,layoutHint:{...hint,cols,rows},focusCols:cols,focusRows:rows}
  state.hidden[state.workspace]=(state.hidden[state.workspace]||[]).filter(id=>id!=='surface')
  smartInsert('surface')
  document.body.classList.add('surface-focus')
  save();renderToolbar();renderWorkspace()
  requestAnimationFrame(()=>document.querySelector('.widget[data-id="surface"]')?.scrollIntoView({block:'start',behavior:'smooth'}))
}
function restoreSurfaceWorkspace(){
  state.surface={...(state.surface||{}),focused:false,suspendedByUser:false,hostWorkspace:''}
  document.body.classList.remove('surface-focus')
  save();renderWorkspace()
}
function openSurfaceIntegrated(url){const u=normalizeSurfaceTarget(url);if(!u)return;state.surface={...(state.surface||{}),url:u,status:'Loading inside JARVIS…'};save();send('surface_open_integrated',{url:u});renderWidget('surface')}
function openSurface(target,title=''){
  const url=normalizeSurfaceTarget(target);if(!url)return
  state.surface={...(state.surface||{}),url,title:title||new URL(url).hostname,status:'Opening in native Surface pane…',suspendedByUser:false,hostWorkspace:state.workspace}
  save();openSurfaceIntegrated(url)
}
function jarvisSurfaceNativeNavigated(url){const u=normalizeSurfaceTarget(url);if(!u)return;state.surface={...(state.surface||{}),url:u,title:new URL(u).hostname};save()}
function renderSurface(body){
  const surf=state.surface||{},url=normalizeSurfaceTarget(surf.url||'')
  body.innerHTML=`<div class="surface-shell native-v29"><div class="surface-bar embedded"><button title="Back" data-surface-nav="back">←</button><button title="Forward" data-surface-nav="forward">→</button><button title="Reload" data-surface-nav="reload">↻</button><input data-surface-url placeholder="github.com, youtube.com, or search…" value="${attr(url||'')}"><button class="primary" data-surface-load>Load</button><button data-surface-close>×</button></div><div class="surface-native-placeholder"><div class="surface-native-orb">◉</div><b>SURFACE · NATIVE BROWSER</b><span>${url?esc(new URL(url).hostname):'No site open'}</span><small>The real webpage is rendered by an isolated Chromium pane inside this same JARVIS window. No iframe and no screenshot streaming.</small></div><div class="surface-status" data-surface-status>${esc(surf.status||'')}</div></div>`
  const input=qs('[data-surface-url]',body),load=qs('[data-surface-load]',body),close=qs('[data-surface-close]',body)
  load.onclick=()=>openSurface(input.value);input.onkeydown=e=>{if(e.key==='Enter'){openSurface(input.value);e.preventDefault()}}
  body.querySelectorAll('[data-surface-nav]').forEach(btn=>btn.onclick=()=>send('surface_'+btn.dataset.surfaceNav,{}))
  close.onclick=()=>{send('surface_close',{});state.surface.status='Surface closed.';renderWidget('surface')}
}
function renderEngineering(body){
  const st=state.engineeringStatus||{},ready=!!st.available,topics=Array.isArray(st.topics)?st.topics:[]
  body.innerHTML=`<div class="engineering-card"><div class="engineering-head"><div><b>MECHANICAL ENGINEERING · JARVIS TUTOR</b><small>Local-first course bridge · AustinUri/home-mech-engin</small></div><span class="${ready?'ok':'warn'}">${ready?'READY':'SYNC NEEDED'}</span></div><div class="engineering-grid"><span>Course source<b>${esc(st.repo_url||'github.com/AustinUri/home-mech-engin')}</b></span><span>Readable files<b>${Number(st.source_files||0)}</b></span><span>Completed<b>${Number(st.completed||0)}</b></span><span>AI<b>Local LM Studio · no API key</b></span></div><div class="engineering-topic-list">${topics.length?topics.slice(0,8).map(x=>`<span>${esc(x)}</span>`).join(''):'<div class="empty">Sync the course once. JARVIS will teach directly from the repository material.</div>'}</div><div class="engineering-actions"><button data-eng="status">Refresh</button><button data-eng="sync">Sync course</button><button class="primary" data-eng="next">Teach next lesson</button><button data-eng="quiz">Quiz me</button><button data-eng="review">Review a topic</button></div><div class="engineering-foot">${esc(st.message||'The repository is cloned/updated with normal Git and taught by your existing local JARVIS model.')}</div></div>`
  body.querySelectorAll('[data-eng]').forEach(btn=>btn.onclick=()=>{const a=btn.dataset.eng;if(a==='status')send('engineering_status');else if(a==='sync')send('engineering_sync');else if(a==='next')send('submit_text',{text:'Teach me the next mechanical engineering lesson from my home-mech-engin course.'});else if(a==='quiz')send('submit_text',{text:'Quiz me on my mechanical engineering course using home-mech-engin. Do not reveal the answers yet.'});else if(a==='review'){const topic=(prompt('Engineering topic to review:')||'').trim();if(topic)send('submit_text',{text:`Review ${topic} using my home-mech-engin mechanical engineering course.`})}})
}

function renderCoding(body){
  const st=state.codingStatus||{},ready=!!st.ready,dirty=!!st.dirty
  const diff=String(st.diff_preview||'').trim(),stat=String(st.diff_stat||'').trim()
  body.innerHTML=`<div class="coding-card"><div class="coding-head"><div><b>CODING JARVIS · ASSISTED DEV</b><small>Isolated Git clone · local LM Studio · stable JARVIS never edited</small></div><span class="${ready?'ok':'warn'}">${ready?'READY':'SETUP'}</span></div><div class="coding-grid"><span>Branch<b>${esc(st.branch||'—')}</b></span><span>Changed files<b>${Number(st.changed_files||0)}</b></span><span>Mode<b>${esc(st.mode||'assisted')}</b></span><span>Workspace<b>${esc(st.workspace||'Not prepared')}</b></span></div><div class="coding-actions"><button data-code="status">Refresh</button><button data-code="prepare" class="primary">Prepare dev clone</button><button data-code="checks">Run checks</button><button data-code="diff">Show diff</button><button data-code="ask">Ask Coding JARVIS</button></div>${stat?`<pre class="coding-stat">${esc(stat)}</pre>`:''}${diff?`<pre class="coding-diff">${esc(diff)}</pre>`:''}<div class="coding-foot">${esc(st.message||'Coding changes stay on jarvis-v29-dev until you deliberately promote them.')}</div></div>`
  body.querySelectorAll('[data-code]').forEach(btn=>btn.onclick=()=>{const a=btn.dataset.code;if(a==='status')send('coding_status');else if(a==='prepare')send('coding_prepare',{refresh:true});else if(a==='checks')send('coding_checks');else if(a==='diff')send('coding_diff');else if(a==='ask'){const q=(prompt('What should Coding JARVIS investigate or fix?')||'').trim();if(q)send('submit_text',{text:`Coding Jarvis: ${q}`})}})
}

function renderWeather(body){const w=state.weather||{};if(w.error){body.innerHTML=`<div class="empty">${esc(w.error)}</div><button class="primary weather-refresh">Refresh</button>`}else{body.innerHTML=`<div class="weather-card"><div class="weather-temp">${w.temperature_c==null?'—':Math.round(w.temperature_c)+'°'}</div><div><b>${esc(w.condition||'Weather')}</b><small>${esc(w.location||state.config.weather_location||'Set location in Settings')}</small></div></div><div class="weather-grid"><span>Feels <b>${w.feels_like_c==null?'—':Math.round(w.feels_like_c)+'°'}</b></span><span>High <b>${w.today_high_c==null?'—':Math.round(w.today_high_c)+'°'}</b></span><span>Low <b>${w.today_low_c==null?'—':Math.round(w.today_low_c)+'°'}</b></span><span>Rain <b>${w.rain_probability_pct==null?'—':Math.round(w.rain_probability_pct)+'%'}</b></span></div><button class="primary weather-refresh">Refresh</button>`}const b=qs('.weather-refresh',body);if(b)b.onclick=()=>send('refresh_weather')}
function formatCallDuration(seconds){const n=Math.max(0,Number(seconds||0));const m=Math.floor(n/60),s=Math.floor(n%60);return m?`${m}m ${String(s).padStart(2,'0')}s`:`${s}s`}
function renderCalls(body){
  const data=state.phoneCallHistory||{},calls=Array.isArray(data.calls)?data.calls:[]
  if(!data.ok&&data.error){body.innerHTML=`<div class="call-history-head"><div><b>RECENT CALLS</b><small>Phone metadata</small></div><button data-call-refresh>Refresh</button></div><div class="phone-note warn-note">${esc(data.error)}</div><div class="call-summary-note">Android may restrict full call-log access for a sideloaded non-dialer app. Calls started by JARVIS still work; full history may require a later dialer-role integration.</div>`;qs('[data-call-refresh]',body).onclick=()=>send('phone_call_history',{limit:30});return}
  const selected=calls.find(c=>String(c.id)===String(state.selectedCallId))||calls[0]||null
  body.innerHTML=`<div class="call-history-head"><div><b>RECENT CALLS</b><small>${calls.length} loaded · ${data.full_history?'full phone history':'JARVIS-started calls only'}</small></div><button data-call-refresh>Refresh</button></div><div class="call-list">${calls.length?calls.map(c=>`<button class="call-row ${selected&&String(c.id)===String(selected.id)?'selected':''}" data-call-id="${attr(String(c.id))}"><span class="call-direction ${attr(String(c.type||'other'))}">${esc(String(c.type||'call').toUpperCase())}</span><div><b>${esc(c.name||'Unknown')}</b><small>${esc(c.number||'')} · ${esc(new Date(Number(c.date_ms||0)).toLocaleString())}</small></div><em>${esc(formatCallDuration(c.duration_seconds))}</em></button>`).join(''):'<div class="empty">No call-history rows were returned.</div>'}</div>${selected?`<div class="call-detail"><b>${esc(selected.name||'Unknown')}</b><span>${esc(selected.number||'')}</span><span>${esc(String(selected.type||'call'))} · ${esc(formatCallDuration(selected.duration_seconds))}</span><div class="call-summary-note"><strong>CONVERSATION SUMMARY</strong><p>No conversation audio is attached to this cellular call yet. JARVIS will never invent a summary. V29.2 prepares the call-history UI; recorded-call import / JARVIS VoIP transcripts will plug into this panel later.</p></div></div>`:''}`
  qs('[data-call-refresh]',body).onclick=()=>send('phone_call_history',{limit:30})
  body.querySelectorAll('[data-call-id]').forEach(btn=>btn.onclick=()=>{state.selectedCallId=btn.dataset.callId;renderCalls(body)})
}

function renderCalendar(body){const st=state.calendarStatus||{},events=Array.isArray(state.calendarEvents)?state.calendarEvents:[];body.innerHTML=`<div class="calendar-head"><span class="${st.connected?'ok':'warn'}">${st.connected?'CONNECTED':'NOT CONNECTED'}</span><div><button data-cal-refresh>Refresh</button><button class="primary" data-cal-connect>Google backup</button></div></div><small>${esc(st.message||'')}</small><div class="event-list">${events.length?events.map(e=>`<a class="event" href="${attr(e.htmlLink||'#')}" target="_blank"><b>${esc(e.summary||'Event')}</b><span>${esc(formatWhen(e.start))}${e.location?' · '+esc(e.location):''}</span></a>`).join(''):'<div class="empty">No upcoming events loaded.</div>'}</div>`;qs('[data-cal-refresh]',body).onclick=()=>send('refresh_calendar',{days:3});qs('[data-cal-connect]',body).onclick=()=>send('calendar_connect')}
function formatWhen(v){if(!v)return'';try{return new Date(v).toLocaleString()}catch{return v}}
function briefingSection(title){return (state.dailyBriefing?.sections||[]).find(s=>String(s.title||'').toLowerCase().includes(title))}
function linkifySources(sources){
  const rows=Array.isArray(sources)?sources:[]
  if(!rows.length)return''
  return rows.map((raw,i)=>{const text=String(raw||'').trim(),m=text.match(/https?:\/\/\S+/);if(!m)return `<span class="brief-source">${esc(text)}</span>`;const url=m[0].replace(/[),.;]+$/,''),label=text.replace(m[0],'').replace(/^\s*\d+[.)]\s*/,'').replace(/[—–-]\s*$/,'').trim()||`Source ${i+1}`;return `<a class="brief-source" href="${attr(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`}).join('')
}
function renderBriefing(body){
  const b=state.dailyBriefing||{},sections=Array.isArray(b.sections)?b.sections:[],stamp=b.generated_at?new Date(b.generated_at).toLocaleString():'Not generated yet'
  body.innerHTML=`<div class="briefing-head"><div><b>DAILY BRIEFING</b><small>${esc(stamp)} · ${sections.length} item${sections.length===1?'':'s'}</small></div><button class="primary" data-brief-refresh>Refresh</button></div><div class="briefing-list">${sections.length?sections.map(s=>`<article class="brief-card"><h4>${esc(s.title||'Update')}</h4><div class="brief-text">${esc(s.summary||'')}</div>${Array.isArray(s.sources)&&s.sources.length?`<div class="brief-sources">${linkifySources(s.sources)}</div>`:''}</article>`).join(''):'<div class="empty">No briefing loaded yet. Press Refresh to build one from current sources.</div>'}</div>`
  const btn=qs('[data-brief-refresh]',body);if(btn)btn.onclick=()=>send('refresh_briefing')
}
function renderSports(body){const s=briefingSection('champions')||{};body.innerHTML=`<div class="sports-title"><b>UEFA Champions League</b><button class="primary">Refresh briefing</button></div>${s.summary?`<div class="sports-copy">${esc(s.summary)}</div><div class="brief-sources">${linkifySources(s.sources)}</div>`:'<div class="empty">No Champions League briefing loaded yet.</div>'}`;qs('button',body).onclick=()=>send('refresh_briefing')}
function renderLearning(body){const l=state.f1Lesson||state.dailyBriefing?.f1_learning||{};body.innerHTML=`<div class="lesson"><div class="lesson-kicker">FORMULA 1 · DAILY LEARNING</div><h3>${esc(l.topic||'Ready for a new lesson?')}</h3><p>${esc(l.seed||'Jarvis can build your F1 knowledge one topic at a time and remember where you are.')}</p><div class="lesson-actions"><button class="primary" data-teach>Teach me this</button><button data-next>Next topic</button></div></div>`;qs('[data-next]',body).onclick=()=>send('next_f1_lesson');qs('[data-teach]',body).onclick=()=>send('submit_text',{text:`Teach me about ${l.topic||'Formula 1'} in a clear way, with a practical race example.`})}
function renderServices(body){const s=state.serviceStatus||{};const rows=[['AI server',s.lm_studio],['Qwen',s.model],['Docker',s.docker],['SearXNG API',s.searxng],['Tailscale',s.tailscale],['Phone bridge',s.phone_bridge]];body.innerHTML=`<div class="service-list">${rows.map(([k,v])=>`<div class="service-row"><span>${k}</span><b class="${v==='online'||v==='loaded'?'ok':'warn'}">${esc(String(v||'checking'))}</b></div>`).join('')}</div><small>Core services stay local. Web research also has direct Wikipedia + Google News RSS fallbacks.</small>`}

function renderConversation(body){
  const hist=Array.isArray(state.runtime.history)?state.runtime.history:[]
  const bubbles=hist.map(m=>{const rtl=/[\u0590-\u05FF]/.test(m.content||'')?'rtl':'';return `<div class="bubble ${m.role==='user'?'you':'jarvis'} ${rtl}"><div class="bubble-title">${m.role==='user'?'YOU':'JARVIS'}</div>${esc(m.content||'')}</div>`}).join('')
  const lastUser=[...hist].reverse().find(m=>m.role==='user')?.content||''
  const pending=state.runtime.transcript&&state.runtime.transcript!==lastUser?`<div class="bubble you"><div class="bubble-title">YOU · PENDING</div>${esc(state.runtime.transcript)}</div>`:''
  const fallback=!hist.length?((state.runtime.transcript?`<div class="bubble you"><div class="bubble-title">YOU</div>${esc(state.runtime.transcript)}</div>`:'')+(state.runtime.response?`<div class="bubble jarvis ${state.runtime.responseLanguage==='he'?'rtl':''}"><div class="bubble-title">JARVIS</div>${esc(state.runtime.response)}</div>`:'')):''
  body.innerHTML=`<div class="conversation"><div class="conversation-scroll">${bubbles+pending||fallback||'<div class="empty">Say “Hey Jarvis” or type below.</div>'}</div><div class="composer"><button class="mic-button">◉</button><input placeholder="Type or speak to Jarvis…"><button class="primary">Send</button></div></div>`
  const input=qs('input',body),go=()=>{const text=input.value.trim();if(text){send('submit_text',{text});input.value=''}}
  qs('.primary',body).onclick=go;qs('.mic-button',body).onclick=()=>send('push_to_talk');input.onkeydown=e=>{if(e.key==='Enter')go()};requestAnimationFrame(()=>{const scroll=qs('.conversation-scroll',body);if(scroll)scroll.scrollTop=scroll.scrollHeight})
}
function parseSources(){return state.runtime.response.split(/\r?\n/).flatMap(line=>{const m=line.match(/https?:\/\/\S+/);if(!m)return[];return[{url:m[0].replace(/[),.;]+$/,''),label:line.replace(m[0],'').replace(/^\s*\d+[.)]\s*/,'').replace(/[—–-]\s*$/,'').trim()||m[0]}]})}
function renderSources(body){const src=parseSources();body.innerHTML=src.length?`<div class="source-list">${src.map((s,i)=>`<a href="${attr(s.url)}" target="_blank"><span class="n">${i+1}</span><div><b>${esc(s.label)}</b><small>${esc(s.url)}</small></div></a>`).join('')}</div>`:`<div class="empty">Sources appear here after researched answers.</div>`}
function renderSystem(body){const m=state.metrics||{},vram=m.vram_percent,gt=m.gpu_temp_c;body.innerHTML=`<div class="metrics metrics-v27">${metric('CPU',m.cpu)}${metric('RAM',m.ram)}${metric('GPU',m.gpu_util)}${metric('VRAM',vram)}${tempMetric('GPU TEMP',gt)}${metric('BAT',m.battery)}</div><div class="governor-card gov-${attr(String(m.state||'normal'))}"><div><b>RESOURCE GOVERNOR · ${esc(String(m.state||'normal').toUpperCase())}</b><small>${esc(m.reason||'Monitoring local resources.')}</small></div><div class="governor-limits"><span>LLM PARALLEL <b>${Number(m.llm_parallel_limit||state.config.agent_max_parallel_llm||2)}</b></span><span>AGENTS <b>${Number(m.active_agent_limit||state.config.agent_max_active_specialists||6)}</b></span></div></div>`}
function metric(n,v){const x=v==null?0:Number(v);return`<div class="metric"><div class="metric-name">${n}</div><div class="metric-value">${v==null?'—':`${Math.round(x)}%`}</div><div class="meter"><span style="width:${Math.min(100,Math.max(0,x))}%"></span></div></div>`}
function tempMetric(n,v){const x=v==null?0:Number(v),pct=Math.min(100,Math.max(0,x/90*100));return`<div class="metric"><div class="metric-name">${n}</div><div class="metric-value">${v==null?'—':`${Math.round(x)}°C`}</div><div class="meter"><span style="width:${pct}%"></span></div></div>`}
function renderContext(body){const rows=[['AI',state.config.ai_model_name||'jarvis-qwen'],['Provider',state.config.ai_provider||'LM Studio'],['Agent mesh',`${state.agentMesh?.registered||47} registered · ${(state.agentMesh?.active||[]).length||0} active`],['Governor',String(state.metrics?.state||'normal').toUpperCase()],['Mic',state.config.mic_name||'Default'],['Wake',state.config.wake_word_enabled?'ON':'OFF'],['Voice',state.config.voice_enabled?'ON':'MUTED'],['Web',state.config.searxng_base_url||'local'],['Vision',state.cameraHasFrame?'CAMERA LINKED':'OFF'],['AI status',state.aiStatus],['Last error',state.runtime.error||'—']];body.innerHTML=`<div class="context">${rows.map(([k,v])=>`<div class="info"><span>${esc(String(k))}</span><b>${esc(String(v))}</b></div>`).join('')}</div>`}

function stopHolo(){if(state.holo.handsTimer){clearInterval(state.holo.handsTimer);state.holo.handsTimer=null}if(state.holo.anim){cancelAnimationFrame(state.holo.anim);state.holo.anim=null}try{state.holo.hands?.close?.()}catch{}state.holo.hands=null;state.holo.handsBusy=false;state.holo.handDetected=false;state.holo.twoHands=false;state.holo.pinch=false}
function stopCamera(){if(state.cameraTimer){clearInterval(state.cameraTimer);state.cameraTimer=null}stopHolo();if(state.cameraStream){state.cameraStream.getTracks().forEach(t=>t.stop());state.cameraStream=null}state.cameraHasFrame=false;send('camera_disabled')}
function captureCameraFrame(video){if(!video?.videoWidth||!video?.videoHeight||video.readyState<2)return;const maxW=640,scale=Math.min(1,maxW/video.videoWidth),w=Math.max(2,Math.round(video.videoWidth*scale)),h=Math.max(2,Math.round(video.videoHeight*scale)),c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d');if(!x)return;x.drawImage(video,0,0,w,h);send('camera_frame',{data_url:c.toDataURL('image/jpeg',.72),width:w,height:h})}
function holoPoint(lm,i,w,h){return{x:(1-lm[i].x)*w,y:lm[i].y*h,z:lm[i].z||0}}
function holoDist(a,b){return Math.hypot(a.x-b.x,a.y-b.y)}
function project3(x,y,z,rx,ry,r,depth=3.4){const cy=Math.cos(ry),sy=Math.sin(ry),cx=Math.cos(rx),sx=Math.sin(rx);let x1=x*cy-z*sy,z1=x*sy+z*cy,y1=y*cx-z1*sx,z2=y*sx+z1*cx;const sc=1/(depth-z2*.38);return[x1*r*sc*1.7,y1*r*sc*1.7]}
function drawWireBox(ctx,w,h,d,r,rx,ry){const pts=[[-w,-h,-d],[w,-h,-d],[w,h,-d],[-w,h,-d],[-w,-h,d],[w,-h,d],[w,h,d],[-w,h,d]].map(p=>project3(...p,rx,ry,r)),e=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];ctx.beginPath();e.forEach(([a,b])=>{ctx.moveTo(...pts[a]);ctx.lineTo(...pts[b])});ctx.stroke()}
function drawHolo(canvas){if(!canvas)return;const rect=canvas.getBoundingClientRect(),dpr=Math.max(1,window.devicePixelRatio||1),W=Math.max(2,Math.round(rect.width*dpr)),H=Math.max(2,Math.round(rect.height*dpr));if(canvas.width!==W||canvas.height!==H){canvas.width=W;canvas.height=H}const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);const w=rect.width,h=rect.height;ctx.clearRect(0,0,w,h);if(!state.holo.enabled)return;const x=state.holo.x*w,y=state.holo.y*h,r=50*state.holo.scale,ry=state.holo.angle+performance.now()/5000,rx=state.holo.tilt;ctx.save();ctx.translate(x,y);ctx.shadowBlur=15;ctx.shadowColor=state.holo.pinch?'rgba(255,170,58,.95)':'rgba(74,220,255,.9)';ctx.strokeStyle=state.holo.pinch?'rgba(255,188,84,.98)':'rgba(101,231,255,.97)';ctx.fillStyle='rgba(55,177,221,.08)';ctx.lineWidth=1.6;if(state.holo.shape==='sphere'){ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.fill();ctx.stroke();for(let i=-3;i<=3;i++){ctx.beginPath();ctx.ellipse(0,i*r*.14,r*Math.sqrt(Math.max(.08,1-(i*.16)**2)),r*.19,ry,0,Math.PI*2);ctx.stroke()}for(let i=0;i<5;i++){ctx.beginPath();ctx.ellipse(0,0,r*.25,r,ry+i*Math.PI/5,0,Math.PI*2);ctx.stroke()}}else if(state.holo.shape==='ring'){for(let i=0;i<5;i++){ctx.beginPath();ctx.ellipse(0,0,r*(.54+i*.11),r*(.16+i*.025),ry+i*.38,0,Math.PI*2);ctx.stroke()}ctx.beginPath();ctx.arc(0,0,r*.22,0,Math.PI*2);ctx.stroke()}else if(state.holo.shape==='cylinder'){ctx.beginPath();ctx.ellipse(0,-r*.58,r*.62,r*.23,ry,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.ellipse(0,r*.58,r*.62,r*.23,ry,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.moveTo(-r*.62,-r*.58);ctx.lineTo(-r*.62,r*.58);ctx.moveTo(r*.62,-r*.58);ctx.lineTo(r*.62,r*.58);ctx.stroke()}else if(state.holo.shape==='gauntlet'){drawWireBox(ctx,.78,1.08,.40,r,rx,ry);ctx.save();ctx.translate(0,-r*.94);drawWireBox(ctx,.56,.28,.30,r,rx*.7,ry);ctx.restore();for(let i=-2;i<=2;i++){ctx.beginPath();ctx.moveTo(i*r*.20,-r*1.25);ctx.lineTo(i*r*.24,-r*1.62);ctx.stroke()}}else drawWireBox(ctx,1,1,1,r,rx,ry);ctx.shadowBlur=5;ctx.beginPath();ctx.arc(0,0,4.5,0,Math.PI*2);ctx.fillStyle='rgba(255,199,88,.98)';ctx.fill();ctx.restore();ctx.font='600 11px Segoe UI';ctx.fillStyle=state.holo.handDetected?'#9fffe8':'#8ba8b9';const gesture=state.holo.twoHands?'TWO-HAND TRANSFORM':state.holo.pinch?'PINCH LOCK · GRABBED':state.holo.handDetected?'PALM TRACKED':state.holo.frozen?'ANCHOR FROZEN':'SHOW HAND OR DRAG';ctx.fillText(`HoloLab Beta · ${gesture}`,14,22);ctx.font='500 10px Segoe UI';ctx.fillStyle='#77bed1';ctx.fillText(`${state.holo.shape.toUpperCase()} · ${state.holo.material.toUpperCase()} · ${Math.round(state.holo.widthMm)}×${Math.round(state.holo.heightMm)}×${Math.round(state.holo.depthMm)} mm`,14,39)}
function startHoloRenderer(canvas){if(state.holo.anim)cancelAnimationFrame(state.holo.anim);const loop=()=>{drawHolo(canvas);state.holo.anim=requestAnimationFrame(loop)};loop();canvas.onpointerdown=e=>{if(!state.holo.enabled)return;state.holo.dragging=true;canvas.setPointerCapture?.(e.pointerId);const r=canvas.getBoundingClientRect();state.holo.x=(e.clientX-r.left)/r.width;state.holo.y=(e.clientY-r.top)/r.height};canvas.onpointermove=e=>{if(!state.holo.dragging||state.holo.handDetected||state.holo.frozen)return;const r=canvas.getBoundingClientRect();state.holo.x=clamp((e.clientX-r.left)/r.width,.05,.95);state.holo.y=clamp((e.clientY-r.top)/r.height,.05,.95)};canvas.onpointerup=()=>state.holo.dragging=false;canvas.onwheel=e=>{if(!state.holo.enabled)return;e.preventDefault();state.holo.scale=clamp(state.holo.scale*(e.deltaY>0?.92:1.08),.25,3.5)}}
async function startHandTracking(video,status){if(!state.holo.enabled||!video)return;if(status)status.textContent='HoloLab Beta · loading two-hand tracker…';try{const visionTasks=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/vision_bundle.mjs'),{FilesetResolver,HandLandmarker}=visionTasks,vision=await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm');let handLandmarker;try{handLandmarker=await HandLandmarker.createFromOptions(vision,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'GPU'},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.5,minHandPresenceConfidence:.5,minTrackingConfidence:.5})}catch{handLandmarker=await HandLandmarker.createFromOptions(vision,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'CPU'},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.45,minHandPresenceConfidence:.45,minTrackingConfidence:.45})}state.holo.hands=handLandmarker;let lastVideoTime=-1,baseTwoDist=null,baseScale=state.holo.scale,baseTwoAngle=null,baseAngle=state.holo.angle;state.holo.handsTimer=setInterval(()=>{if(!state.holo.enabled||state.holo.handsBusy||video.readyState<2)return;if(video.currentTime===lastVideoTime)return;lastVideoTime=video.currentTime;state.holo.handsBusy=true;try{const res=handLandmarker.detectForVideo(video,performance.now()),list=res?.landmarks||[];state.holo.handDetected=list.length>0;state.holo.twoHands=list.length>1;if(list.length){const lm=list[0],p=holoPoint(lm,9,1,1),thumb=holoPoint(lm,4,1,1),index=holoPoint(lm,8,1,1),wrist=holoPoint(lm,0,1,1),pinch=holoDist(thumb,index)<.075;state.holo.pinch=pinch;if(!state.holo.frozen&&(pinch||!state.holo.dragging)){state.holo.x=clamp(p.x,.04,.96);state.holo.y=clamp(p.y-.08,.05,.95)}state.holo.tilt=Math.atan2(p.y-wrist.y,p.x-wrist.x)*.45;if(list.length>1){const p2=holoPoint(list[1],9,1,1),dist=holoDist(p,p2),ang=Math.atan2(p2.y-p.y,p2.x-p.x);if(baseTwoDist==null){baseTwoDist=dist;baseScale=state.holo.scale;baseTwoAngle=ang;baseAngle=state.holo.angle}state.holo.scale=clamp(baseScale*(dist/Math.max(.04,baseTwoDist)),.25,3.5);state.holo.angle=baseAngle+(ang-baseTwoAngle)}else{baseTwoDist=null;baseTwoAngle=null;if(!state.holo.frozen)state.holo.angle=Math.atan2(p.y-wrist.y,p.x-wrist.x)}}else{state.holo.pinch=false;state.holo.twoHands=false;baseTwoDist=null;baseTwoAngle=null}if(status)status.textContent=state.holo.twoHands?'TWO-HAND MODE · spread to scale · rotate hands to turn':state.holo.pinch?'PINCH LOCK · move your hand to carry the prototype':state.holo.handDetected?'PALM TRACKED · pinch to grab':'HoloLab Beta · show a hand or use mouse/touch'}catch(e){if(status)status.textContent='HoloLab visual mode active · hand tracker retrying'}finally{state.holo.handsBusy=false}},75)}catch(e){state.holo.handDetected=false;state.holo.twoHands=false;state.holo.pinch=false;if(status)status.textContent='HoloLab visual mode active · hand tracking unavailable; mouse/touch still works. '+String(e?.message||e)}}
function downloadHoloPrototype(){const data={format:'jarvis-hololab-v29.2',shape:state.holo.shape,material:state.holo.material,dimensions_mm:{width:state.holo.widthMm,height:state.holo.heightMm,depth:state.holo.depthMm},transform:{x:state.holo.x,y:state.holo.y,scale:state.holo.scale,angle:state.holo.angle,tilt:state.holo.tilt},created_at:new Date().toISOString()};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`jarvis_${state.holo.shape}_prototype.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function renderCamera(body){const active=!!state.cameraStream;body.innerHTML=`<div class="camera camera-v28 holo-beta"><div class="camera-frame">${active?'<video autoplay playsinline muted></video>':'<div class="camera-off">Camera is off<br><small>Nothing is shared until you enable it.</small></div>'}${active?`<canvas class="holo-overlay ${state.holo.enabled?'active':''}"></canvas><div class="vision-badge ${state.cameraHasFrame?'live':''}">${state.cameraHasFrame?'JARVIS VISION LINKED':'CAMERA LIVE — LINKING…'}</div><div class="holo-badge">${state.holo.enabled?'HOLOLAB BETA':'VISION MODE'}</div>`:''}</div><div class="error"></div><div class="camera-controls v28"><button class="primary" data-cam="toggle">${active?'Disable camera':'Enable camera'}</button>${active?`<button data-cam="holo">${state.holo.enabled?'Exit HoloLab':'Enter HoloLab'}</button>`:''}<span class="holo-status">${state.holo.enabled?'Two-hand manipulation available.':'Ask: “Jarvis, what can you see?”'}</span></div>${active&&state.holo.enabled?`<div class="holo-console"><label>Shape<select data-holo="shape">${['cube','sphere','ring','cylinder','gauntlet'].map(x=>`<option ${x===state.holo.shape?'selected':''}>${x}</option>`).join('')}</select></label><label>Material<select data-holo="material">${['aluminium','titanium','steel','ABS','PLA','polycarbonate'].map(x=>`<option ${x.toLowerCase()===state.holo.material.toLowerCase()?'selected':''}>${x}</option>`).join('')}</select></label><label>W / Ø mm<input type="number" min="1" max="5000" data-holo="width" value="${Number(state.holo.widthMm)}"></label><label>H mm<input type="number" min="1" max="5000" data-holo="height" value="${Number(state.holo.heightMm)}"></label><label>D / T mm<input type="number" min="1" max="5000" data-holo="depth" value="${Number(state.holo.depthMm)}"></label><button data-cam="freeze">${state.holo.frozen?'Unfreeze anchor':'Freeze anchor'}</button><button data-cam="reset">Reset pose</button><button class="primary" data-cam="test">Run prototype tests</button><button data-cam="save">Save prototype JSON</button></div>`:''}${state.holo.lastTest?`<div class="holo-test">${esc(state.holo.lastTest)}</div>`:''}</div>`;const err=qs('.error',body);if(active){const v=qs('video',body);v.srcObject=state.cameraStream;const canvas=qs('.holo-overlay',body);if(canvas){startHoloRenderer(canvas);if(state.holo.enabled)startHandTracking(v,qs('.holo-status',body))}}const toggle=body.querySelector('[data-cam="toggle"]');if(toggle)toggle.onclick=async()=>{if(state.cameraStream){stopCamera();renderCamera(body);renderTop();renderContextIfVisible();return}try{const stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},facingMode:'user'},audio:false});state.cameraStream=stream;send('camera_enabled');renderCamera(body);const video=qs('video',body);if(video){video.srcObject=stream;const ms=Math.max(750,Number(state.config.camera_frame_interval_seconds||1.5)*1000);state.cameraTimer=setInterval(()=>captureCameraFrame(video),ms);setTimeout(()=>captureCameraFrame(video),650)}}catch(e){err.textContent=String(e);send('camera_disabled')}};const holo=body.querySelector('[data-cam="holo"]');if(holo)holo.onclick=()=>{const next=!state.holo.enabled;stopHolo();state.holo.enabled=next;state.holo.lastTest=next?'HoloLab Beta ready. Two-hand manipulation will attach when tracking is available.':'';renderCamera(body)};body.querySelectorAll('[data-holo]').forEach(el=>el.onchange=()=>{const k=el.dataset.holo;if(k==='shape')state.holo.shape=el.value.toLowerCase();else if(k==='material')state.holo.material=el.value.toLowerCase();else if(k==='width')state.holo.widthMm=clamp(Number(el.value)||100,1,5000);else if(k==='height')state.holo.heightMm=clamp(Number(el.value)||100,1,5000);else if(k==='depth')state.holo.depthMm=clamp(Number(el.value)||60,1,5000)});const freeze=body.querySelector('[data-cam="freeze"]');if(freeze)freeze.onclick=()=>{state.holo.frozen=!state.holo.frozen;renderCamera(body)};const reset=body.querySelector('[data-cam="reset"]');if(reset)reset.onclick=()=>{state.holo.x=.5;state.holo.y=.52;state.holo.scale=1;state.holo.angle=0;state.holo.tilt=0;state.holo.frozen=false;renderCamera(body)};const saveBtn=body.querySelector('[data-cam="save"]');if(saveBtn)saveBtn.onclick=downloadHoloPrototype;const test=body.querySelector('[data-cam="test"]');if(test)test.onclick=()=>{state.holo.lastTest='Running HoloLab Beta geometry + interaction tests…';send('hololab_test',{shape:state.holo.shape,material:state.holo.material,width_mm:state.holo.widthMm,height_mm:state.holo.heightMm,depth_mm:state.holo.depthMm,scale:state.holo.scale,hand_detected:state.holo.handDetected,two_hands:state.holo.twoHands,pinch:state.holo.pinch});renderCamera(body)}}
function renderContextIfVisible(){renderWidget('context')}
function renderSettings(body){
  const boolKeys=['start_with_windows','auto_manage_services','briefing_enabled','briefing_include_israel','briefing_include_idf','briefing_include_champions_league','briefing_include_f1','briefing_include_ai','briefing_include_football','briefing_include_world','prefer_phone_calendar','google_calendar_fallback_enabled','briefing_include_weather','briefing_include_calendar','agent_mesh_enabled','resource_governor_enabled']
  body.innerHTML=`<div class="settings settings-v281">
    <label>Address me as<input data-k="address_name" value="${attr(state.config.address_name||'sir')}"></label>
    <label>Tone<select data-k="tone_mode"><option>Respectful</option><option>Neutral</option><option>Casual</option></select></label>
    <label>Language<select data-k="language_mode"><option>Auto</option><option>English</option><option>Hebrew</option></select></label>
    <label>Weather location<input data-k="weather_location" placeholder="e.g. Netanya, Israel" value="${attr(state.config.weather_location||'')}"></label>
    <label>Wake threshold<input type="number" step="0.01" min="0.05" max="0.9" data-k="wake_word_threshold" value="${Number(state.config.wake_word_threshold||.15)}"></label>
    <label>Command silence (sec)<input type="number" step="0.1" min="0.8" max="4" data-k="command_silence_seconds" value="${Number(state.config.command_silence_seconds||2.2)}"></label>
    <label>Max voice turn (sec)<input type="number" step="1" min="5" max="30" data-k="command_max_seconds" value="${Number(state.config.command_max_seconds||14)}"></label>
    <label>Start with Windows<select data-k="start_with_windows"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Manage local services<select data-k="auto_manage_services"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Agent Mesh<select data-k="agent_mesh_enabled"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Active specialist cap<input type="number" step="1" min="2" max="8" data-k="agent_max_active_specialists" value="${Number(state.config.agent_max_active_specialists||6)}"></label>
    <label>Parallel LLM cap<input type="number" step="1" min="1" max="2" data-k="agent_max_parallel_llm" value="${Number(state.config.agent_max_parallel_llm||2)}"></label>
    <label>Resource governor<select data-k="resource_governor_enabled"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Daily briefing<select data-k="briefing_enabled"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Israel news<select data-k="briefing_include_israel"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>IDF / security<select data-k="briefing_include_idf"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Champions League<select data-k="briefing_include_champions_league"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Formula 1<select data-k="briefing_include_f1"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>AI / tech<select data-k="briefing_include_ai"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>General football<select data-k="briefing_include_football"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Major world news<select data-k="briefing_include_world"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Prefer native phone calendar<select data-k="prefer_phone_calendar"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Google Calendar fallback<select data-k="google_calendar_fallback_enabled"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Weather in briefing<select data-k="briefing_include_weather"><option value="true">On</option><option value="false">Off</option></select></label>
    <label>Calendar in briefing<select data-k="briefing_include_calendar"><option value="true">On</option><option value="false">Off</option></select></label>
    <div class="settings-note">v28 keeps 47 specialist identities registered but does not run 47 model copies. The local Qwen model is shared and the governor caps expensive parallel work.</div>
    <div class="settings-actions"><button data-a="toggle_wake_word">Toggle wake word</button><button data-a="toggle_voice">Mute / unmute</button><button data-a="test_microphone">Test mic</button><button data-a="test_voice">Test voice</button><button data-a="clear_memory">Clear memory</button><button data-a="refresh_briefing">Refresh briefing</button></div>
  </div>`
  const selects=['tone_mode','language_mode',...boolKeys]
  selects.forEach(k=>{const e=body.querySelector(`[data-k="${k}"]`);if(!e)return;if(boolKeys.includes(k))e.value=state.config[k]!==false?'true':'false';else e.value=state.config[k]||e.value})
  body.querySelectorAll('[data-k]').forEach(x=>{x.onchange=()=>{let value=x.type==='number'?Number(x.value):x.value;if(boolKeys.includes(x.dataset.k))value=x.value==='true';send('config_patch',{[x.dataset.k]:value})}})
  body.querySelectorAll('[data-a]').forEach(x=>x.onclick=()=>send(x.dataset.a))
}
function renderPopout(id){app.innerHTML=`<div class="popout"></div>`;const item=p(id,0,0,12,12),el=makeWidget(item);el.classList.remove('fullscreen-widget');qs('.popout').appendChild(el);qs('[data-hide]',el).onclick=()=>window.close()}
function showPalette(){if(document.querySelector('.palette-backdrop'))return;const div=document.createElement('div');div.className='palette-backdrop';div.innerHTML=`<div class="palette"><h3>Command Palette</h3><input autofocus placeholder="Type a command…"><div class="palette-results"></div></div>`;document.body.appendChild(div);div.onclick=e=>{if(e.target===div)div.remove()};const inp=qs('input',div),res=qs('.palette-results',div),commands=[...Object.keys(state.layouts).map(w=>({label:`Switch to ${w}`,run:()=>applyWorkspace(w)})),{label:'Push-to-talk',run:()=>send('push_to_talk')},{label:'Show Settings',run:()=>showWidget('settings')},{label:'Show Agent Activity',run:()=>showWidget('activity')},{label:'Show Camera / Vision',run:()=>showWidget('camera')},{label:'Show Sources',run:()=>showWidget('sources')},{label:'Show Daily Briefing',run:()=>showWidget('briefing')},{label:'Show Calendar',run:()=>showWidget('calendar')},{label:'Show Phone Link',run:()=>showWidget('phone')},{label:'Show Weather',run:()=>showWidget('weather')},{label:'Show Champions League',run:()=>showWidget('sports')},{label:'Show F1 Learning',run:()=>showWidget('learning')},{label:'Show Engineering Tutor',run:()=>showWidget('engineering')},{label:'Show Coding JARVIS',run:()=>showWidget('coding')},{label:'Show Agent Mesh',run:()=>showWidget('agentmesh')},{label:'Show Call History',run:()=>showWidget('calls')}];const draw=()=>{const q=inp.value.toLowerCase(),filtered=commands.filter(c=>c.label.toLowerCase().includes(q));res.innerHTML=filtered.map((c,i)=>`<button data-i="${i}">${esc(c.label)}</button>`).join('');res.querySelectorAll('button').forEach((b,i)=>b.onclick=()=>{filtered[i].run();div.remove()})};inp.oninput=draw;draw();setTimeout(()=>inp.focus(),0)}
function bindGlobalKeys(){window.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();showPalette()}}}
window.onresize=()=>positionAll()
window.addEventListener('beforeunload',()=>{if(state.cameraStream)stopCamera()})
function clamp(n,a,b){return Math.max(a,Math.min(b,n))}function qs(s,r=document){return r.querySelector(s)}function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function attr(v){return esc(v)}
connect();renderAll()
