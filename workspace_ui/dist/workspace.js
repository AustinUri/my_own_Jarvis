const app = document.getElementById('app')
const COLS = 12, ROW = 54, GAP = 12
const WIDGETS = {
  orb:'JARVIS Core', conversation:'Conversation', briefing:'Daily Briefing', weather:'Weather', calendar:'Calendar', sports:'Champions League', learning:'F1 Learning', services:'Runtime Services', phone:'Phone Link',
  activity:'Agent Activity', sources:'Sources', system:'System Monitor', context:'Context', camera:'Camera / Vision', settings:'Settings'
}
const SIZE = {
  orb:{w:6,h:9,minW:4,minH:6}, conversation:{w:6,h:10,minW:4,minH:6}, briefing:{w:6,h:10,minW:4,minH:6}, weather:{w:3,h:5,minW:3,minH:4}, calendar:{w:4,h:7,minW:3,minH:5}, sports:{w:5,h:8,minW:3,minH:5}, learning:{w:4,h:6,minW:3,minH:4}, services:{w:3,h:5,minW:3,minH:4}, phone:{w:4,h:7,minW:3,minH:5}, activity:{w:5,h:8,minW:4,minH:5},
  sources:{w:5,h:9,minW:3,minH:5}, system:{w:3,h:5,minW:3,minH:4}, context:{w:4,h:5,minW:3,minH:4},
  camera:{w:4,h:7,minW:3,minH:5}, settings:{w:5,h:8,minW:3,minH:5}
}
const DEFAULT = {
  'Command Center':[p('system',0,0,3,5,3,4),p('orb',3,0,6,10,4,6),p('services',9,0,3,5,3,4),p('weather',0,5,3,5,3,4),p('context',9,5,3,5,3,4),p('conversation',3,10,6,7,4,5),p('calendar',0,10,3,7,3,5),p('briefing',9,10,3,7,3,5)],
  Normal:[p('orb',0,0,6,8,4,6),p('conversation',6,0,6,10,4,6),p('activity',0,8,6,7,4,5),p('context',6,10,6,5,3,4)],
  Morning:[p('briefing',0,0,6,11,4,6),p('orb',6,0,6,8,4,6),p('weather',6,8,3,5,3,4),p('calendar',9,8,3,7,3,5)],
  Research:[p('conversation',0,0,7,10,4,6),p('sources',7,0,5,10,3,5),p('activity',0,10,5,5,3,4),p('orb',5,10,3,5,3,4),p('context',8,10,4,5,3,4)],
  Sports:[p('sports',0,0,7,10,4,6),p('orb',7,0,5,8,4,6),p('briefing',7,8,5,7,3,5),p('conversation',0,10,7,6,4,5)],
  F1:[p('learning',0,0,4,7,3,4),p('orb',4,0,8,9,4,6),p('briefing',0,7,4,8,3,5),p('conversation',4,9,8,6,4,5)],
  Developer:[p('activity',0,0,6,11,4,6),p('conversation',6,0,6,8,4,6),p('system',6,8,3,5,3,4),p('services',9,8,3,5,3,4)],
  Vision:[p('camera',0,0,7,11,4,6),p('orb',7,0,5,7,3,5),p('conversation',7,7,5,7,4,5)],
  Mobile:[p('phone',0,0,4,8,3,5),p('calendar',0,8,4,7,3,5),p('orb',4,0,8,9,4,6),p('conversation',4,9,8,6,4,5)],
  Minimal:[p('orb',2,0,8,9,4,6),p('conversation',2,9,8,6,4,5)]
}
function p(id,x,y,w,h,minW=2,minH=3){return{id,x,y,w,h,minW,minH}}
function oldOrNew(key){return localStorage.getItem(`jarvis26.${key}`) ?? localStorage.getItem(`jarvis25.${key}`) ?? localStorage.getItem(`jarvis24.${key}`) ?? localStorage.getItem(`jarvis23.${key}`)}
const hadV24Layouts = !!localStorage.getItem('jarvis24.layouts')
const hadV25Layouts = !!localStorage.getItem('jarvis25.layouts')
const hadV26Layouts = !!localStorage.getItem('jarvis26.layouts')
const oldLayouts = loadJSONMulti(['jarvis23.layouts'], {})
const migratedLayouts = hadV26Layouts ? loadJSONMulti(['jarvis26.layouts'], structuredClone(DEFAULT)) : hadV25Layouts ? {...structuredClone(DEFAULT), ...loadJSONMulti(['jarvis25.layouts'], {})} : hadV24Layouts ? {...structuredClone(DEFAULT), ...loadJSONMulti(['jarvis24.layouts'], {})} : {
  ...structuredClone(DEFAULT),
  ...Object.fromEntries(Object.entries(oldLayouts).filter(([name])=>!Object.prototype.hasOwnProperty.call(DEFAULT,name)))
}
const state = {
  workspace: oldOrNew('workspace') || 'Command Center',
  layouts: migratedLayouts,
  hidden: hadV26Layouts ? loadJSONMulti(['jarvis26.hidden'], {}) : hadV25Layouts ? loadJSONMulti(['jarvis25.hidden'], {}) : hadV24Layouts ? loadJSONMulti(['jarvis24.hidden'], {}) : {},
  theme: oldOrNew('theme') || 'stark', editing:true, connected:false, profileMeta:{},
  runtime:{assistantState:'Idle',transcript:'',response:'',responseLanguage:'en',spoken:'',logs:[],activity:[],error:'',history:[]},
  config:{}, aiStatus:'Connecting…', capabilities:[], metrics:{cpu:0,ram:0,battery:null}, ws:null,
  cameraStream:null, cameraTimer:null, cameraHasFrame:false, dailyBriefing:{}, weather:{}, calendarStatus:{}, calendarEvents:[], f1Lesson:{}, serviceStatus:{}, phoneStatus:{}, phonePairing:{}, phoneTransport:{},
}
document.documentElement.dataset.theme = state.theme

function loadJSONMulti(keys,fallback){for(const key of keys){try{const raw=localStorage.getItem(key);if(raw)return JSON.parse(raw)}catch{}}return fallback}
let profileSaveTimer=null
function save(){localStorage.setItem('jarvis26.workspace',state.workspace);localStorage.setItem('jarvis26.layouts',JSON.stringify(state.layouts));localStorage.setItem('jarvis26.hidden',JSON.stringify(state.hidden));localStorage.setItem('jarvis26.theme',state.theme);clearTimeout(profileSaveTimer);profileSaveTimer=setTimeout(persistCurrentProfile,250)}
async function loadProfiles(){try{const r=await fetch('/api/profiles');const profiles=await r.json();for(const [name,p] of Object.entries(profiles||{})){if(Array.isArray(p.layout))state.layouts[name]=p.layout;if(Array.isArray(p.hidden))state.hidden[name]=p.hidden;state.profileMeta[name]=p}if(!state.layouts[state.workspace])state.workspace='Command Center';const active=state.profileMeta[state.workspace];if(active?.theme){state.theme=active.theme;document.documentElement.dataset.theme=state.theme}renderAll()}catch{}}
async function persistCurrentProfile(){try{await fetch(`/api/profiles/${encodeURIComponent(state.workspace)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:state.workspace,layout:activeLayout(),hidden:activeHidden(),theme:state.theme,updatedAt:new Date().toISOString()})})}catch{}}
async function deleteProfileServer(name){try{await fetch(`/api/profiles/${encodeURIComponent(name)}`,{method:'DELETE'})}catch{}}
if(!hadV26Layouts){if(!state.layouts[state.workspace])state.workspace='Command Center';save()}
setTimeout(loadProfiles,250)
function send(action,payload={}){if(state.ws?.readyState===1)state.ws.send(JSON.stringify({action,payload}))}

function connect(){
  const proto=location.protocol==='https:'?'wss':'ws'; const ws=new WebSocket(`${proto}://${location.host}/ws`); state.ws=ws
  ws.onopen=()=>{state.connected=true;renderTop()}
  ws.onclose=()=>{state.connected=false;renderTop();setTimeout(connect,1200)}
  ws.onmessage=e=>{try{handleMessage(JSON.parse(e.data))}catch{}}
}
function handleMessage(m){const t=m.type,v=m.payload
  if(t==='snapshot'){Object.assign(state,v);state.runtime=v.runtime||state.runtime;state.runtime.activity=v.activity||state.runtime.activity||[];state.config=v.config||{};state.dailyBriefing=v.dailyBriefing||state.dailyBriefing;state.weather=v.weather||state.weather;state.calendarStatus=v.calendarStatus||state.calendarStatus;state.calendarEvents=v.calendarEvents||state.calendarEvents;state.f1Lesson=v.f1Lesson||state.f1Lesson;state.serviceStatus=v.serviceStatus||state.serviceStatus;state.phoneStatus=v.phoneStatus||state.phoneStatus;state.phonePairing=v.phonePairing||state.phonePairing;state.phoneTransport=v.phoneTransport||state.phoneTransport;renderAll()}
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
  else if(t==='service_status'){state.serviceStatus=v||{};renderWidget('services');renderTop()}
  else if(t==='phone_status'){state.phoneStatus=v||{};renderWidget('phone');renderWidget('calendar')}
  else if(t==='phone_pairing'){state.phonePairing=v||{};renderWidget('phone')}
  else if(t==='phone_transport'){state.phoneTransport=v||{};renderWidget('phone')}
  else if(t==='system_metrics'){state.metrics=v||state.metrics;renderWidget('system')}
  else if(t==='conversation_history'){state.runtime.history=Array.isArray(v)?v:[];renderWidget('conversation')}
  else if(t==='camera_status'){state.cameraHasFrame=!!v?.hasFrame;renderTop();renderWidget('context')}
  else if(t==='ui_command'){handleUiCommand(v)}
}
function handleUiCommand(v){const a=v?.action,payload=v?.payload||{}
  if(a==='ui_show_panel')showWidget(String(payload.panel||''))
  if(a==='ui_hide_panel')hideWidget(String(payload.panel||''))
  if(a==='ui_switch_workspace'){const w=String(payload.workspace||'');if(state.layouts[w])applyWorkspace(w)}
  if(a==='ui_create_workspace'){const w=String(payload.workspace||'').trim();if(w){state.layouts[w]=structuredClone(activeLayout());state.hidden[w]=structuredClone(activeHidden());state.profileMeta[w]={theme:state.theme};applyWorkspace(w)}}
}

function renderAll(){
  const pop=new URLSearchParams(location.search).get('popout')
  if(pop&&WIDGETS[pop])return renderPopout(pop)
  app.innerHTML=`<div class="app"><div id="top"></div><div id="toolbar"></div><div class="workspace-wrap"><div id="workspace" class="workspace ${state.editing?'editing':''}"></div></div></div>`
  renderTop();renderToolbar();renderWorkspace();bindGlobalKeys()
}
function renderTop(){const el=document.getElementById('top');if(!el)return
  el.className='topbar';el.innerHTML=`<div class="brand"><span class="brand-dot"></span>JARVIS <small>v26</small></div><div class="statusline"><span class="${state.connected?'link-ok':'link-bad'}">${state.connected?'LINKED':'OFFLINE'}</span><span>${esc(state.runtime.assistantState)}</span><span>${esc(state.config.ai_model_name||'jarvis-qwen')}</span>${state.cameraHasFrame?'<span class="vision-top">VISION</span>':''}<span class="service-mini">WEB:${esc((state.serviceStatus?.searxng||'').toUpperCase()||'—')}</span></div><div class="top-actions"><select id="workspaceSelect">${Object.keys(state.layouts).map(w=>`<option ${w===state.workspace?'selected':''}>${w}</option>`).join('')}</select><button id="editToggle">${state.editing?'Lock layout':'Edit layout'}</button><button id="paletteBtn" title="Ctrl+K">⌘K</button></div>`
  qs('#workspaceSelect',el).onchange=e=>applyWorkspace(e.target.value)
  qs('#editToggle',el).onclick=()=>{state.editing=!state.editing;renderTop();renderWorkspace()}
  qs('#paletteBtn',el).onclick=showPalette
}
function renderToolbar(){const el=document.getElementById('toolbar');if(!el)return;el.className='toolbar'
  const visible=new Set(activeLayout().filter(x=>!activeHidden().includes(x.id)).map(x=>x.id)); const missing=Object.keys(WIDGETS).filter(id=>!visible.has(id))
  el.innerHTML=`<div class="widget-buttons"><span class="label">ADD WIDGET</span>${missing.map(id=>`<button data-add="${id}">+ ${WIDGETS[id]}</button>`).join('')}</div><div class="theme-buttons"><button data-theme="stark" class="${state.theme==='stark'?'active':''}">Stark</button><button data-theme="blue" class="${state.theme==='blue'?'active':''}">FRIDAY</button><button data-theme="mono" class="${state.theme==='mono'?'active':''}">Mono</button><button id="saveAsLayout">Save As…</button><button id="deleteLayout">Delete</button><button id="resetLayout">Reset</button></div>`
  el.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>showWidget(b.dataset.add))
  el.querySelectorAll('[data-theme]').forEach(b=>b.onclick=()=>{state.theme=b.dataset.theme;state.profileMeta[state.workspace]={...(state.profileMeta[state.workspace]||{}),theme:state.theme};document.documentElement.dataset.theme=state.theme;save();renderToolbar()})
  qs('#saveAsLayout',el).onclick=()=>{const name=(prompt('Name this workspace:',`${state.workspace} Copy`)||'').trim();if(!name)return;state.layouts[name]=structuredClone(activeLayout());state.hidden[name]=structuredClone(activeHidden());state.profileMeta[name]={theme:state.theme};state.workspace=name;save();renderAll()}
  qs('#deleteLayout',el).onclick=()=>{if(DEFAULT[state.workspace])return alert('Built-in workspaces cannot be deleted.');if(!confirm(`Delete workspace “${state.workspace}”?`))return;const doomed=state.workspace;delete state.layouts[doomed];delete state.hidden[doomed];delete state.profileMeta[doomed];deleteProfileServer(doomed);state.workspace='Command Center';save();renderAll()}
  qs('#resetLayout',el).onclick=()=>{const base=DEFAULT[state.workspace]||DEFAULT.Normal;state.layouts[state.workspace]=structuredClone(base);state.hidden[state.workspace]=[];save();renderToolbar();renderWorkspace()}
}
function activeLayout(){return state.layouts[state.workspace]||structuredClone(DEFAULT[state.workspace])}
function activeHidden(){return state.hidden[state.workspace]||[]}
function applyWorkspace(name){if(!state.layouts[name])return;state.workspace=name;const meta=state.profileMeta[name]||{};if(meta.theme){state.theme=meta.theme;document.documentElement.dataset.theme=state.theme}save();renderAll()}
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
  ws.querySelectorAll('.widget').forEach(el=>{const item=activeLayout().find(x=>x.id===el.dataset.id);if(!item)return;el.style.left=`${Math.round(item.x*cw)+GAP/2}px`;el.style.top=`${item.y*ROW+GAP/2}px`;el.style.width=`${Math.max(180,item.w*cw-GAP)}px`;el.style.height=`${Math.max(180,item.h*ROW-GAP)}px`})
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
  else if(id==='activity')renderActivity(body)
  else if(id==='sources')renderSources(body)
  else if(id==='system')renderSystem(body)
  else if(id==='context')renderContext(body)
  else if(id==='camera')renderCamera(body)
  else if(id==='settings')renderSettings(body)
}

function renderActivity(body){
  const rows=Array.isArray(state.runtime.activity)?state.runtime.activity:[]
  const recent=rows.slice(-140)
  const last=recent.length?recent[recent.length-1].seq:0
  body.innerHTML=`<div class="activity-head"><div><b>ORDERED EXECUTION TRACE</b><small>${recent.length} events · latest #${last||'—'}</small></div><span class="activity-live">LIVE</span></div><div class="activity-list">${recent.length?recent.map(e=>{const time=e.timestamp?new Date(e.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}):'';return `<div class="activity-row status-${attr(e.status||'info')}"><div class="activity-seq">#${String(e.seq||0).padStart(3,'0')}</div><div class="activity-time">${esc(time)}</div><div class="activity-main"><div><span class="activity-cat">${esc(String(e.category||'system').toUpperCase())}</span><span class="activity-status">${esc(String(e.status||'info').toUpperCase())}</span><b>${esc(e.title||'Activity')}</b></div>${e.detail?`<p>${esc(e.detail)}</p>`:''}</div></div>`}).join(''):'<div class="empty">No agent activity yet. The next request will appear here in execution order.</div>'}</div>`
  const list=qs('.activity-list',body);if(list)list.scrollTop=list.scrollHeight
}
function renderPhone(body){
  const st=state.phoneStatus||{},pair=state.phonePairing||{},transport=state.phoneTransport||{},devices=Array.isArray(st.devices)?st.devices:[]
  const device=devices[0]||{}
  const connected=!!st.connected,paired=!!st.paired
  const pairActive=!!pair.code
  body.innerHTML=`<div class="phone-card"><div class="phone-status"><span class="${connected?'ok':paired?'warn':'off'}"></span><div><b>${connected?'PHONE CONNECTED':paired?'PAIRED — WAITING FOR PHONE':'NO TRUSTED PHONE'}</b><small>${esc(device.name||'Android companion not linked')}</small></div></div><div class="phone-grid"><span>Transport<b>${esc(st.transport||'Tailscale Serve HTTPS')}</b></span><span>Security<b>${esc(st.security||'ECDSA device identity')}</b></span><span>Server<b>${esc(st.server_url||transport.server_url||'Not ready')}</b></span><span>Calendar<b>${connected?'Native phone calendar available':'Not available'}</b></span></div>${transport.message?`<div class="phone-note ${transport.ok?'ok-note':'warn-note'}">${esc(transport.message)}</div>`:''}${pairActive?`<div class="pair-box"><small>PAIRING CODE · ${esc(String(pair.minutes||5))} MINUTES</small><strong>${esc(pair.code)}</strong><span>${esc(pair.server_url||st.server_url||'Prepare private link first')}</span></div>`:''}<div class="phone-actions"><button data-phone="prepare">Prepare private link</button><button class="primary" data-phone="pair">Create pairing code</button><button data-phone="refresh">Refresh</button>${paired?'<button class="danger" data-phone="revoke">Revoke phone</button>':''}</div><div class="phone-foot">v26 exposes only native calendar READ and basic device status. No Accessibility, SMS, contacts, microphone, camera, storage, device-admin, or calendar-write permission.</div></div>`
  body.querySelectorAll('[data-phone]').forEach(btn=>btn.onclick=()=>{const a=btn.dataset.phone;if(a==='prepare')send('phone_prepare');else if(a==='pair')send('phone_pair');else if(a==='refresh')send('phone_status');else if(a==='revoke'&&confirm('Revoke every paired JARVIS phone?'))send('phone_revoke_all')})
}

function renderOrb(body){body.innerHTML=`<div class="orb-box"><canvas></canvas><div class="orb-label">${esc(state.runtime.assistantState)}</div><div class="orb-link">${state.connected?'J.A.R.V.I.S. CORE LINKED':'CORE OFFLINE'}</div></div>`;startOrb(body.querySelector('canvas'))}
function startOrb(canvas){if(!canvas)return;const ctx=canvas.getContext('2d');const ro=new ResizeObserver(()=>{const r=canvas.getBoundingClientRect(),d=Math.min(devicePixelRatio,2);canvas.width=Math.max(20,r.width*d);canvas.height=Math.max(20,r.height*d);ctx.setTransform(d,0,0,d,0,0)});ro.observe(canvas);let t0=performance.now()
  function frame(now){if(!document.body.contains(canvas)){ro.disconnect();return}const r=canvas.getBoundingClientRect(),w=r.width,h=r.height,cx=w/2,cy=h/2,s=Math.min(w,h),t=(now-t0)/1000,mode=state.runtime.assistantState;const speed=mode==='Thinking'?1.7:mode==='Listening'?1.1:mode==='Speaking'?1.35:mode==='Disabled'?.12:.52;const accent=mode==='Error'?'#ff5c70':mode==='Listening'?'#8af5ff':'#2dd6ff',gold='#c7fbff';ctx.clearRect(0,0,w,h);ctx.save();ctx.translate(cx,cy);ctx.globalCompositeOperation='lighter'
    const pulse=1+Math.sin(t*(1.4+speed*2.4))*(mode==='Idle'?.018:.05),rad=s*.115*pulse;let g=ctx.createRadialGradient(-rad*.18,-rad*.2,rad*.03,0,0,rad*2.6);g.addColorStop(0,'rgba(245,255,255,1)');g.addColorStop(.12,'rgba(179,248,255,.98)');g.addColorStop(.34,'rgba(38,210,255,.72)');g.addColorStop(.68,'rgba(9,101,210,.16)');g.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=g;ctx.beginPath();ctx.arc(0,0,rad*2.6,0,Math.PI*2);ctx.fill()
    // layered spherical lattice
    for(let shell=0;shell<4;shell++){const rr=s*(.17+shell*.032);ctx.strokeStyle=shell===0?gold:accent;ctx.globalAlpha=.22-shell*.035;ctx.lineWidth=1.05;ctx.beginPath();ctx.arc(0,0,rr,0,Math.PI*2);ctx.stroke();ctx.save();ctx.scale(1,.42+.12*shell);ctx.beginPath();ctx.arc(0,0,rr,0,Math.PI*2);ctx.stroke();ctx.restore()}
    // asymmetric rotating data arcs
    const arcs=[.245,.285,.325,.365,.405];for(let k=0;k<arcs.length;k++){const rr=s*arcs[k],a=t*(.18+.05*k)*speed*(k%2?1:-1)+k*1.7,len=Math.PI*(.5+(k%3)*.22);ctx.strokeStyle=k%3===0?gold:accent;ctx.globalAlpha=.58-k*.07;ctx.lineWidth=1.8-k*.18;ctx.beginPath();ctx.arc(0,0,rr,a,a+len);ctx.stroke();ctx.globalAlpha=.16;ctx.beginPath();ctx.arc(0,0,rr,a+len+.18,a+Math.PI*1.65);ctx.stroke()}
    // orbiting data nodes
    for(let i=0;i<54;i++){const a=i*.71+t*.035*speed,rr=s*(.25+(i%13)/95),x=Math.cos(a)*rr,y=Math.sin(a)*rr*.76;ctx.globalAlpha=i%8===0?.88:.30;ctx.fillStyle=i%9===0?gold:accent;ctx.beginPath();ctx.arc(x,y,i%9===0?1.7:1,0,Math.PI*2);ctx.fill()}
    // crosshair / technical ticks
    ctx.globalAlpha=.16;ctx.strokeStyle=gold;for(let i=0;i<24;i++){const a=i*Math.PI/12,rin=s*.42,rout=rin+(i%3===0?9:4);ctx.beginPath();ctx.moveTo(Math.cos(a)*rin,Math.sin(a)*rin);ctx.lineTo(Math.cos(a)*rout,Math.sin(a)*rout);ctx.stroke()}
    ctx.restore();requestAnimationFrame(frame)}requestAnimationFrame(frame)
}

function linkifySources(lines){return (lines||[]).map((line,i)=>{const m=String(line).match(/https?:\/\/\S+/);if(!m)return'';const url=m[0].replace(/[),.;]+$/,'');const label=String(line).replace(m[0],'').replace(/^\s*\d+[.)]\s*/,'').replace(/[—–-]\s*$/,'').trim()||url;return `<a class="brief-source" href="${attr(url)}" target="_blank">${i+1}. ${esc(label)}</a>`}).join('')}
function renderBriefing(body){const b=state.dailyBriefing||{},sections=Array.isArray(b.sections)?b.sections:[];body.innerHTML=`<div class="briefing-head"><div><b>${b.date?`Briefing · ${esc(b.date)}`:'Daily Intelligence'}</b><small>${b.generated_at?'Updated '+new Date(b.generated_at).toLocaleTimeString():'Not generated yet'}</small></div><button class="primary">Refresh</button></div><div class="briefing-list">${sections.length?sections.map(s=>`<article class="brief-card"><h4>${esc(s.title||'Update')}</h4><div class="brief-text">${esc(s.summary||'')}</div><div class="brief-sources">${linkifySources(s.sources)}</div></article>`).join(''):'<div class="empty">Jarvis will prepare the daily briefing when the Control Center opens.</div>'}</div>`;qs('button',body).onclick=()=>send('refresh_briefing')}
function renderWeather(body){const w=state.weather||{};if(w.error){body.innerHTML=`<div class="empty">${esc(w.error)}</div><button class="primary weather-refresh">Refresh</button>`}else{body.innerHTML=`<div class="weather-card"><div class="weather-temp">${w.temperature_c==null?'—':Math.round(w.temperature_c)+'°'}</div><div><b>${esc(w.condition||'Weather')}</b><small>${esc(w.location||state.config.weather_location||'Set location in Settings')}</small></div></div><div class="weather-grid"><span>Feels <b>${w.feels_like_c==null?'—':Math.round(w.feels_like_c)+'°'}</b></span><span>High <b>${w.today_high_c==null?'—':Math.round(w.today_high_c)+'°'}</b></span><span>Low <b>${w.today_low_c==null?'—':Math.round(w.today_low_c)+'°'}</b></span><span>Rain <b>${w.rain_probability_pct==null?'—':Math.round(w.rain_probability_pct)+'%'}</b></span></div><button class="primary weather-refresh">Refresh</button>`}const b=qs('.weather-refresh',body);if(b)b.onclick=()=>send('refresh_weather')}
function renderCalendar(body){const st=state.calendarStatus||{},events=Array.isArray(state.calendarEvents)?state.calendarEvents:[];body.innerHTML=`<div class="calendar-head"><span class="${st.connected?'ok':'warn'}">${st.connected?'CONNECTED':'NOT CONNECTED'}</span><div><button data-cal-refresh>Refresh</button><button class="primary" data-cal-connect>Google backup</button></div></div><small>${esc(st.message||'')}</small><div class="event-list">${events.length?events.map(e=>`<a class="event" href="${attr(e.htmlLink||'#')}" target="_blank"><b>${esc(e.summary||'Event')}</b><span>${esc(formatWhen(e.start))}${e.location?' · '+esc(e.location):''}</span></a>`).join(''):'<div class="empty">No upcoming events loaded.</div>'}</div>`;qs('[data-cal-refresh]',body).onclick=()=>send('refresh_calendar',{days:3});qs('[data-cal-connect]',body).onclick=()=>send('calendar_connect')}
function formatWhen(v){if(!v)return'';try{return new Date(v).toLocaleString()}catch{return v}}
function briefingSection(title){return (state.dailyBriefing?.sections||[]).find(s=>String(s.title||'').toLowerCase().includes(title))}
function renderSports(body){const s=briefingSection('champions')||{};body.innerHTML=`<div class="sports-title"><b>UEFA Champions League</b><button class="primary">Refresh briefing</button></div>${s.summary?`<div class="sports-copy">${esc(s.summary)}</div><div class="brief-sources">${linkifySources(s.sources)}</div>`:'<div class="empty">No Champions League briefing loaded yet.</div>'}`;qs('button',body).onclick=()=>send('refresh_briefing')}
function renderLearning(body){const l=state.f1Lesson||state.dailyBriefing?.f1_learning||{};body.innerHTML=`<div class="lesson"><div class="lesson-kicker">FORMULA 1 · DAILY LEARNING</div><h3>${esc(l.topic||'Ready for a new lesson?')}</h3><p>${esc(l.seed||'Jarvis can build your F1 knowledge one topic at a time and remember where you are.')}</p><div class="lesson-actions"><button class="primary" data-teach>Teach me this</button><button data-next>Next topic</button></div></div>`;qs('[data-next]',body).onclick=()=>send('next_f1_lesson');qs('[data-teach]',body).onclick=()=>send('submit_text',{text:`Teach me about ${l.topic||'Formula 1'} in a clear way, with a practical race example.`})}
function renderServices(body){const s=state.serviceStatus||{};const rows=[['AI server',s.lm_studio],['Qwen',s.model],['Docker',s.docker],['Web search',s.searxng]];body.innerHTML=`<div class="service-list">${rows.map(([k,v])=>`<div class="service-row"><span>${k}</span><b class="${v==='online'||v==='loaded'?'ok':'warn'}">${esc(String(v||'checking'))}</b></div>`).join('')}</div><small>Jarvis manages these services in the background.</small>`}

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
function renderSystem(body){const m=state.metrics;body.innerHTML=`<div class="metrics">${metric('CPU',m.cpu)}${metric('RAM',m.ram)}${metric('BAT',m.battery)}</div>`}
function metric(n,v){const x=v==null?0:v;return`<div class="metric"><div class="metric-name">${n}</div><div class="metric-value">${v==null?'—':`${x}%`}</div><div class="meter"><span style="width:${Math.min(100,x)}%"></span></div></div>`}
function renderContext(body){const rows=[['AI',state.config.ai_model_name||'jarvis-qwen'],['Provider',state.config.ai_provider||'LM Studio'],['Mic',state.config.mic_name||'Default'],['Wake',state.config.wake_word_enabled?'ON':'OFF'],['Voice',state.config.voice_enabled?'ON':'MUTED'],['Web',state.config.searxng_base_url||'local'],['Vision',state.cameraHasFrame?'CAMERA LINKED':'OFF'],['AI status',state.aiStatus],['Last error',state.runtime.error||'—']];body.innerHTML=`<div class="context">${rows.map(([k,v])=>`<div class="info"><span>${esc(String(k))}</span><b>${esc(String(v))}</b></div>`).join('')}</div>`}

function stopCamera(){if(state.cameraTimer){clearInterval(state.cameraTimer);state.cameraTimer=null}if(state.cameraStream){state.cameraStream.getTracks().forEach(t=>t.stop());state.cameraStream=null}state.cameraHasFrame=false;send('camera_disabled')}
function captureCameraFrame(video){if(!video?.videoWidth||!video?.videoHeight||video.readyState<2)return;const maxW=640,scale=Math.min(1,maxW/video.videoWidth),w=Math.max(2,Math.round(video.videoWidth*scale)),h=Math.max(2,Math.round(video.videoHeight*scale)),c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d');if(!x)return;x.drawImage(video,0,0,w,h);send('camera_frame',{data_url:c.toDataURL('image/jpeg',.72),width:w,height:h})}
function renderCamera(body){const active=!!state.cameraStream;body.innerHTML=`<div class="camera"><div class="camera-frame">${active?'<video autoplay playsinline muted></video>':'<div class="camera-off">Camera is off<br><small>Nothing is shared until you enable it.</small></div>'}${active?`<div class="vision-badge ${state.cameraHasFrame?'live':''}">${state.cameraHasFrame?'JARVIS VISION LINKED':'CAMERA LIVE — LINKING…'}</div>`:''}</div><div class="error"></div><div class="camera-controls"><button class="primary">${active?'Disable camera':'Enable camera'}</button><span>${active?'Ask: “Jarvis, what can you see?”':'Explicit permission only'}</span></div></div>`
  const btn=qs('button',body),err=qs('.error',body);if(active){const v=qs('video',body);v.srcObject=state.cameraStream}
  btn.onclick=async()=>{if(state.cameraStream){stopCamera();renderCamera(body);renderTop();renderContextIfVisible();return}try{const stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720}},audio:false});state.cameraStream=stream;send('camera_enabled');renderCamera(body);const video=qs('video',body);if(video){video.srcObject=stream;const ms=Math.max(750,Number(state.config.camera_frame_interval_seconds||1.5)*1000);state.cameraTimer=setInterval(()=>captureCameraFrame(video),ms);setTimeout(()=>captureCameraFrame(video),650)}}catch(e){err.textContent=String(e);send('camera_disabled')}}
}
function renderContextIfVisible(){renderWidget('context')}
function renderSettings(body){body.innerHTML=`<div class="settings"><label>Address me as<input data-k="address_name" value="${attr(state.config.address_name||'sir')}"></label><label>Tone<select data-k="tone_mode"><option>Respectful</option><option>Neutral</option><option>Casual</option></select></label><label>Language<select data-k="language_mode"><option>Auto</option><option>English</option><option>Hebrew</option></select></label><label>Weather location<input data-k="weather_location" placeholder="e.g. Netanya, Israel" value="${attr(state.config.weather_location||'')}"></label><label>Wake threshold<input type="number" step="0.01" min="0.05" max="0.9" data-k="wake_word_threshold" value="${Number(state.config.wake_word_threshold||.15)}"></label><label>Command silence (sec)<input type="number" step="0.1" min="0.8" max="4" data-k="command_silence_seconds" value="${Number(state.config.command_silence_seconds||2.2)}"></label><label>Max voice turn (sec)<input type="number" step="1" min="5" max="30" data-k="command_max_seconds" value="${Number(state.config.command_max_seconds||14)}"></label><label>Start with Windows<select data-k="start_with_windows"><option value="true">On</option><option value="false">Off</option></select></label><label>Manage LM Studio + SearXNG automatically<select data-k="auto_manage_services"><option value="true">On</option><option value="false">Off</option></select></label><label>Daily briefing<select data-k="briefing_enabled"><option value="true">On</option><option value="false">Off</option></select></label><label>Israel news<select data-k="briefing_include_israel"><option value="true">On</option><option value="false">Off</option></select></label><label>IDF / security<select data-k="briefing_include_idf"><option value="true">On</option><option value="false">Off</option></select></label><label>Champions League<select data-k="briefing_include_champions_league"><option value="true">On</option><option value="false">Off</option></select></label><label>Formula 1<select data-k="briefing_include_f1"><option value="true">On</option><option value="false">Off</option></select></label><label>AI / tech<select data-k="briefing_include_ai"><option value="true">On</option><option value="false">Off</option></select></label><label>General football<select data-k="briefing_include_football"><option value="true">On</option><option value="false">Off</option></select></label><label>Major world news<select data-k="briefing_include_world"><option value="true">On</option><option value="false">Off</option></select></label><label>Prefer native phone calendar<select data-k="prefer_phone_calendar"><option value="true">On</option><option value="false">Off</option></select></label><label>Google Calendar fallback<select data-k="google_calendar_fallback_enabled"><option value="true">On</option><option value="false">Off</option></select></label><label>Weather in briefing<select data-k="briefing_include_weather"><option value="true">On</option><option value="false">Off</option></select></label><label>Calendar in briefing<select data-k="briefing_include_calendar"><option value="true">On</option><option value="false">Off</option></select></label><div class="settings-actions"><button data-a="toggle_wake_word">Toggle wake word</button><button data-a="toggle_voice">Mute / unmute</button><button data-a="test_microphone">Test mic</button><button data-a="test_voice">Test voice</button><button data-a="clear_memory">Clear memory</button><button data-a="refresh_briefing">Refresh briefing</button></div></div>`;const tone=body.querySelector('[data-k="tone_mode"]'),lang=body.querySelector('[data-k="language_mode"]'),startup=body.querySelector('[data-k="start_with_windows"]'),manage=body.querySelector('[data-k="auto_manage_services"]'),brief=body.querySelector('[data-k="briefing_enabled"]');tone.value=state.config.tone_mode||'Respectful';lang.value=state.config.language_mode||'Auto';startup.value=state.config.start_with_windows?'true':'false';manage.value=state.config.auto_manage_services!==false?'true':'false';brief.value=state.config.briefing_enabled!==false?'true':'false';['briefing_include_israel','briefing_include_idf','briefing_include_champions_league','briefing_include_f1','briefing_include_ai','briefing_include_football','briefing_include_world','prefer_phone_calendar','google_calendar_fallback_enabled','briefing_include_weather','briefing_include_calendar'].forEach(k=>{const e=body.querySelector(`[data-k="${k}"]`);if(e)e.value=state.config[k]!==false?'true':'false'});body.querySelectorAll('[data-k]').forEach(x=>{x.onchange=()=>{let value=x.type==='number'?Number(x.value):x.value;if(['start_with_windows','auto_manage_services','briefing_enabled','briefing_include_israel','briefing_include_idf','briefing_include_champions_league','briefing_include_f1','briefing_include_ai','briefing_include_football','briefing_include_world','prefer_phone_calendar','google_calendar_fallback_enabled','briefing_include_weather','briefing_include_calendar'].includes(x.dataset.k))value=x.value==='true';send('config_patch',{[x.dataset.k]:value})}});body.querySelectorAll('[data-a]').forEach(x=>x.onclick=()=>send(x.dataset.a))}
function renderPopout(id){app.innerHTML=`<div class="popout"></div>`;const item=p(id,0,0,12,12),el=makeWidget(item);el.classList.remove('fullscreen-widget');qs('.popout').appendChild(el);qs('[data-hide]',el).onclick=()=>window.close()}
function showPalette(){if(document.querySelector('.palette-backdrop'))return;const div=document.createElement('div');div.className='palette-backdrop';div.innerHTML=`<div class="palette"><h3>Command Palette</h3><input autofocus placeholder="Type a command…"><div class="palette-results"></div></div>`;document.body.appendChild(div);div.onclick=e=>{if(e.target===div)div.remove()};const inp=qs('input',div),res=qs('.palette-results',div),commands=[...Object.keys(state.layouts).map(w=>({label:`Switch to ${w}`,run:()=>applyWorkspace(w)})),{label:'Push-to-talk',run:()=>send('push_to_talk')},{label:'Show Settings',run:()=>showWidget('settings')},{label:'Show Agent Activity',run:()=>showWidget('activity')},{label:'Show Camera / Vision',run:()=>showWidget('camera')},{label:'Show Sources',run:()=>showWidget('sources')},{label:'Show Daily Briefing',run:()=>showWidget('briefing')},{label:'Show Calendar',run:()=>showWidget('calendar')},{label:'Show Phone Link',run:()=>showWidget('phone')},{label:'Show Weather',run:()=>showWidget('weather')},{label:'Show Champions League',run:()=>showWidget('sports')},{label:'Show F1 Learning',run:()=>showWidget('learning')}];const draw=()=>{const q=inp.value.toLowerCase(),filtered=commands.filter(c=>c.label.toLowerCase().includes(q));res.innerHTML=filtered.map((c,i)=>`<button data-i="${i}">${esc(c.label)}</button>`).join('');res.querySelectorAll('button').forEach((b,i)=>b.onclick=()=>{filtered[i].run();div.remove()})};inp.oninput=draw;draw();setTimeout(()=>inp.focus(),0)}
function bindGlobalKeys(){window.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();showPalette()}}}
window.onresize=()=>positionAll()
window.addEventListener('beforeunload',()=>{if(state.cameraStream)stopCamera()})
function clamp(n,a,b){return Math.max(a,Math.min(b,n))}function qs(s,r=document){return r.querySelector(s)}function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function attr(v){return esc(v)}
connect();renderAll()
