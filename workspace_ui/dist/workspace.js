const app = document.getElementById('app')
const COLS = 12, ROW = 54, GAP = 12
const WIDGETS = {
  orb:'JARVIS Core', conversation:'Conversation', activity:'Agent Activity', sources:'Sources',
  system:'System Monitor', context:'Context', camera:'Camera', settings:'Settings'
}
const DEFAULT = {
  Normal:[p('orb',0,0,6,7),p('conversation',6,0,6,10),p('activity',0,7,3,6),p('context',3,7,3,6)],
  Research:[p('conversation',0,0,7,10),p('sources',7,0,5,10),p('activity',0,10,5,5),p('orb',5,10,3,5),p('context',8,10,4,5)],
  Developer:[p('activity',0,0,6,11),p('conversation',6,0,6,8),p('system',6,8,3,5),p('context',9,8,3,5)],
  Vision:[p('camera',0,0,7,11),p('orb',7,0,5,7),p('conversation',7,7,5,7)],
  Minimal:[p('orb',2,0,8,9),p('conversation',2,9,8,6)]
}
function p(id,x,y,w,h){return{id,x,y,w,h}}
const state = {
  workspace: localStorage.getItem('jarvis23.workspace') || 'Normal',
  layouts: loadJSON('jarvis23.layouts', structuredClone(DEFAULT)),
  hidden: loadJSON('jarvis23.hidden', {}),
  theme: localStorage.getItem('jarvis23.theme') || 'amber', editing: true, connected:false,
  runtime:{assistantState:'Idle',transcript:'',response:'',responseLanguage:'en',spoken:'',logs:[],error:'',history:[]},
  config:{}, aiStatus:'Connecting…', capabilities:[], metrics:{cpu:0,ram:0,battery:null}, ws:null, cameraStream:null,
}
document.documentElement.dataset.theme = state.theme

function loadJSON(key,fallback){try{return JSON.parse(localStorage.getItem(key))||fallback}catch{return fallback}}
function save(){localStorage.setItem('jarvis23.workspace',state.workspace);localStorage.setItem('jarvis23.layouts',JSON.stringify(state.layouts));localStorage.setItem('jarvis23.hidden',JSON.stringify(state.hidden));localStorage.setItem('jarvis23.theme',state.theme)}
function send(action,payload={}){if(state.ws?.readyState===1)state.ws.send(JSON.stringify({action,payload}))}

function connect(){
  const proto = location.protocol==='https:'?'wss':'ws'; const ws=new WebSocket(`${proto}://${location.host}/ws`); state.ws=ws
  ws.onopen=()=>{state.connected=true;renderTop()}
  ws.onclose=()=>{state.connected=false;renderTop();setTimeout(connect,1200)}
  ws.onmessage=e=>{try{handleMessage(JSON.parse(e.data))}catch{}}
}
function handleMessage(m){const t=m.type,v=m.payload
  if(t==='snapshot'){Object.assign(state,v);state.runtime=v.runtime||state.runtime;state.config=v.config||{};renderAll()}
  else if(t==='state'){state.runtime.assistantState=v;renderTop();renderWidget('orb')}
  else if(t==='transcript'){state.runtime.transcript=v.text||'';state.runtime.responseLanguage=v.language||'en';renderWidget('conversation')}
  else if(t==='response'){state.runtime.response=v.text||'';state.runtime.responseLanguage=v.language||'en';renderWidget('conversation');renderWidget('sources')}
  else if(t==='spoken'){state.runtime.spoken=v||''}
  else if(t==='log'){state.runtime.logs=[...state.runtime.logs,String(v)].slice(-300);renderWidget('activity')}
  else if(t==='error'){state.runtime.error=String(v||'');renderWidget('context')}
  else if(t==='config'){state.config=v||{};renderTop();renderWidget('context');renderWidget('settings')}
  else if(t==='ai_status'){state.aiStatus=String(v||'');renderWidget('context')}
  else if(t==='system_metrics'){state.metrics=v||state.metrics;renderWidget('system')}
  else if(t==='conversation_history'){state.runtime.history=Array.isArray(v)?v:[];renderWidget('conversation')}
  else if(t==='ui_command'){handleUiCommand(v)}
}
function handleUiCommand(v){const a=v?.action,payload=v?.payload||{}
  if(a==='ui_show_panel')showWidget(String(payload.panel||''))
  if(a==='ui_hide_panel')hideWidget(String(payload.panel||''))
  if(a==='ui_switch_workspace'){const w=String(payload.workspace||'');if(state.layouts[w]){state.workspace=w;save();renderAll()}}
}

function renderAll(){
  const pop = new URLSearchParams(location.search).get('popout')
  if(pop && WIDGETS[pop]) return renderPopout(pop)
  app.innerHTML=`<div class="app"><div id="top"></div><div id="toolbar"></div><div class="workspace-wrap"><div id="workspace" class="workspace ${state.editing?'editing':''}"></div></div></div>`
  renderTop();renderToolbar();renderWorkspace();bindGlobalKeys()
}
function renderTop(){const el=document.getElementById('top');if(!el)return
  el.className='topbar';el.innerHTML=`<div class="brand"><span class="brand-dot"></span>JARVIS <small>v23</small></div><div class="statusline"><span class="${state.connected?'link-ok':'link-bad'}">${state.connected?'LINKED':'OFFLINE'}</span><span>${esc(state.runtime.assistantState)}</span><span>${esc(state.config.ai_model_name||'jarvis-qwen')}</span></div><div class="top-actions"><select id="workspaceSelect">${Object.keys(state.layouts).map(w=>`<option ${w===state.workspace?'selected':''}>${w}</option>`).join('')}</select><button id="editToggle">${state.editing?'Lock layout':'Edit layout'}</button><button id="paletteBtn" title="Ctrl+K">⌘K</button></div>`
  qs('#workspaceSelect',el).onchange=e=>{state.workspace=e.target.value;save();renderToolbar();renderWorkspace()}
  qs('#editToggle',el).onclick=()=>{state.editing=!state.editing;renderTop();renderWorkspace()}
  qs('#paletteBtn',el).onclick=showPalette
}
function renderToolbar(){const el=document.getElementById('toolbar');if(!el)return;el.className='toolbar'
  const visible=new Set(activeLayout().filter(x=>!activeHidden().includes(x.id)).map(x=>x.id)); const missing=Object.keys(WIDGETS).filter(id=>!visible.has(id))
  el.innerHTML=`<div class="widget-buttons"><span class="label">ADD WIDGET</span>${missing.map(id=>`<button data-add="${id}">+ ${WIDGETS[id]}</button>`).join('')}</div><div class="theme-buttons"><button data-theme="amber" class="${state.theme==='amber'?'active':''}">Amber</button><button data-theme="blue" class="${state.theme==='blue'?'active':''}">FRIDAY</button><button data-theme="mono" class="${state.theme==='mono'?'active':''}">Mono</button><button id="saveAsLayout">Save As…</button><button id="deleteLayout">Delete</button><button id="resetLayout">Reset</button></div>`
  el.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>showWidget(b.dataset.add))
  el.querySelectorAll('[data-theme]').forEach(b=>b.onclick=()=>{state.theme=b.dataset.theme;document.documentElement.dataset.theme=state.theme;save();renderToolbar()})
  qs('#saveAsLayout',el).onclick=()=>{const name=(prompt('Name this workspace:',`${state.workspace} Copy`)||'').trim();if(!name)return;state.layouts[name]=structuredClone(activeLayout());state.hidden[name]=structuredClone(activeHidden());state.workspace=name;save();renderAll()}
  qs('#deleteLayout',el).onclick=()=>{if(DEFAULT[state.workspace])return alert('Built-in workspaces cannot be deleted.');if(!confirm(`Delete workspace “${state.workspace}”?`))return;delete state.layouts[state.workspace];delete state.hidden[state.workspace];state.workspace='Normal';save();renderAll()}
  qs('#resetLayout',el).onclick=()=>{const base=DEFAULT[state.workspace]||DEFAULT.Normal;state.layouts[state.workspace]=structuredClone(base);state.hidden[state.workspace]=[];save();renderToolbar();renderWorkspace()}
}
function activeLayout(){return state.layouts[state.workspace]||structuredClone(DEFAULT[state.workspace])}
function activeHidden(){return state.hidden[state.workspace]||[]}
function renderWorkspace(){const ws=document.getElementById('workspace');if(!ws)return;ws.className=`workspace ${state.editing?'editing':''}`;ws.innerHTML=''
  const items=activeLayout().filter(i=>!activeHidden().includes(i.id)); items.forEach(item=>ws.appendChild(makeWidget(item)))
  positionAll();const maxY=Math.max(12,...items.map(i=>i.y+i.h));ws.style.minHeight=`${maxY*ROW+GAP}px`
}
function makeWidget(item){const el=document.createElement('section');el.className='widget';el.dataset.id=item.id
  el.innerHTML=`<header class="widget-header"><span>${WIDGETS[item.id]}</span><div class="widget-actions"><button data-full title="Fullscreen">⛶</button><button data-pop title="Pop out">↗</button><button data-hide title="Hide">×</button></div></header><div class="widget-body"></div><div class="resize-handle"></div>`
  qs('[data-hide]',el).onclick=()=>hideWidget(item.id);qs('[data-pop]',el).onclick=()=>window.open(`${location.origin}/?popout=${item.id}`,`jarvis-${item.id}`,'width=780,height=700');qs('[data-full]',el).onclick=()=>el.classList.toggle('fullscreen-widget')
  if(state.editing){makeDraggable(el,item);makeResizable(el,item)} renderWidgetInto(el,item.id);return el
}
function positionAll(){const ws=document.getElementById('workspace');if(!ws)return;const width=ws.clientWidth;const cw=width/COLS
  ws.querySelectorAll('.widget').forEach(el=>{const item=activeLayout().find(x=>x.id===el.dataset.id);if(!item)return;el.style.left=`${Math.round(item.x*cw)+GAP/2}px`;el.style.top=`${item.y*ROW+GAP/2}px`;el.style.width=`${Math.max(180,item.w*cw-GAP)}px`;el.style.height=`${Math.max(180,item.h*ROW-GAP)}px`})
}
function makeDraggable(el,item){const h=qs('.widget-header',el);h.onpointerdown=e=>{if(e.target.closest('button'))return;h.setPointerCapture(e.pointerId);const ws=document.getElementById('workspace'),cw=ws.clientWidth/COLS,sx=e.clientX,sy=e.clientY,ox=item.x,oy=item.y
  const move=ev=>{item.x=clamp(Math.round(ox+(ev.clientX-sx)/cw),0,COLS-item.w);item.y=Math.max(0,Math.round(oy+(ev.clientY-sy)/ROW));positionAll()};const up=()=>{h.onpointermove=null;h.onpointerup=null;save()};h.onpointermove=move;h.onpointerup=up}}
function makeResizable(el,item){const r=qs('.resize-handle',el);r.onpointerdown=e=>{e.stopPropagation();r.setPointerCapture(e.pointerId);const ws=document.getElementById('workspace'),cw=ws.clientWidth/COLS,sx=e.clientX,sy=e.clientY,ow=item.w,oh=item.h
  r.onpointermove=ev=>{item.w=clamp(Math.round(ow+(ev.clientX-sx)/cw),2,COLS-item.x);item.h=Math.max(3,Math.round(oh+(ev.clientY-sy)/ROW));positionAll()};r.onpointerup=()=>{r.onpointermove=null;r.onpointerup=null;save()}}}
function showWidget(id){if(!WIDGETS[id])return;state.hidden[state.workspace]=activeHidden().filter(x=>x!==id);if(!activeLayout().some(x=>x.id===id))activeLayout().push(p(id,0,99,4,6));save();renderToolbar();renderWorkspace()}
function hideWidget(id){state.hidden[state.workspace]=[...new Set([...activeHidden(),id])];save();renderToolbar();renderWorkspace()}
function renderWidget(id){const el=document.querySelector(`.widget[data-id="${CSS.escape(id)}"]`);if(el)renderWidgetInto(el,id);const pop=document.querySelector(`.popout .widget[data-id="${CSS.escape(id)}"]`);if(pop)renderWidgetInto(pop,id)}
function renderWidgetInto(el,id){const body=qs('.widget-body',el);if(!body)return
  if(id==='orb')renderOrb(body)
  else if(id==='conversation')renderConversation(body)
  else if(id==='activity')body.innerHTML=state.runtime.logs.length?`<div class="log-list">${state.runtime.logs.slice(-90).reverse().map(x=>`<div class="log-row">${esc(x)}</div>`).join('')}</div>`:`<div class="empty">No agent activity yet.</div>`
  else if(id==='sources')renderSources(body)
  else if(id==='system')renderSystem(body)
  else if(id==='context')renderContext(body)
  else if(id==='camera')renderCamera(body)
  else if(id==='settings')renderSettings(body)
}
function renderOrb(body){body.innerHTML=`<div class="orb-box"><canvas></canvas><div class="orb-label">${esc(state.runtime.assistantState)}</div><div class="orb-link">${state.connected?'CORE LINKED':'CORE OFFLINE'}</div></div>`;startOrb(body.querySelector('canvas'))}
function startOrb(canvas){if(!canvas)return;const ctx=canvas.getContext('2d');let active=true;const ro=new ResizeObserver(()=>{const r=canvas.getBoundingClientRect(),d=Math.min(devicePixelRatio,2);canvas.width=Math.max(20,r.width*d);canvas.height=Math.max(20,r.height*d);ctx.setTransform(d,0,0,d,0,0)});ro.observe(canvas)
  const palette={Idle:['#f1a23b','#ffd688'],Listening:['#4fc9ff','#d5f5ff'],Transcribing:['#e5bd55','#fff0aa'],Thinking:['#b974ff','#eed4ff'],Speaking:['#70e5a2','#d8ffe8'],Error:['#ff6863','#ffc0bd'],Disabled:['#68727e','#bdc4ca']};let t0=performance.now();
  function frame(now){if(!active||!document.body.contains(canvas)){ro.disconnect();return}const r=canvas.getBoundingClientRect(),w=r.width,h=r.height,cx=w/2,cy=h/2,s=Math.min(w,h),t=(now-t0)/1000,[a,b]=palette[state.runtime.assistantState]||palette.Idle;ctx.clearRect(0,0,w,h);ctx.save();ctx.translate(cx,cy)
    const pulse=1+Math.sin(t*(state.runtime.assistantState==='Idle'?1.6:4.5))*.035;const rad=s*.16*pulse;let g=ctx.createRadialGradient(-rad*.2,-rad*.25,rad*.05,0,0,rad*1.4);g.addColorStop(0,'#fff');g.addColorStop(.25,b);g.addColorStop(.68,a);g.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=g;ctx.beginPath();ctx.arc(0,0,rad*1.4,0,Math.PI*2);ctx.fill();ctx.globalCompositeOperation='lighter';
    for(let k=0;k<3;k++){ctx.strokeStyle=k===0?a:b;ctx.globalAlpha=.52-k*.1;ctx.lineWidth=2-k*.35;ctx.beginPath();const rr=s*(.24+k*.055);ctx.arc(0,0,rr,t*(.22+k*.11)+k, t*(.22+k*.11)+k+Math.PI*(1.15+k*.12));ctx.stroke()}
    ctx.globalAlpha=.32;for(let i=0;i<70;i++){const ang=i*.91+t*.03,rr=s*(.31+(i%11)/80);ctx.fillStyle=i%3?a:b;ctx.fillRect(Math.cos(ang)*rr,Math.sin(ang)*rr,1.2,1.2)}ctx.restore();requestAnimationFrame(frame)}requestAnimationFrame(frame)
}
function renderConversation(body){
  const hist=Array.isArray(state.runtime.history)?state.runtime.history:[]
  const bubbles=hist.map(m=>{const rtl=/[\u0590-\u05FF]/.test(m.content||'')?'rtl':'';return `<div class="bubble ${m.role==='user'?'you':'jarvis'} ${rtl}"><div class="bubble-title">${m.role==='user'?'YOU':'JARVIS'}</div>${esc(m.content||'')}</div>`}).join('')
  const lastUser=[...hist].reverse().find(m=>m.role==='user')?.content||''
  const pending=state.runtime.transcript && state.runtime.transcript!==lastUser ? `<div class="bubble you"><div class="bubble-title">YOU · PENDING</div>${esc(state.runtime.transcript)}</div>` : ''
  const fallback=!hist.length?((state.runtime.transcript?`<div class="bubble you"><div class="bubble-title">YOU</div>${esc(state.runtime.transcript)}</div>`:'')+(state.runtime.response?`<div class="bubble jarvis ${state.runtime.responseLanguage==='he'?'rtl':''}"><div class="bubble-title">JARVIS</div>${esc(state.runtime.response)}</div>`:'')):''
  body.innerHTML=`<div class="conversation"><div class="conversation-scroll">${bubbles+pending||fallback||'<div class="empty">Say “Hey Jarvis” or type below.</div>'}</div><div class="composer"><button class="mic-button">◉</button><input placeholder="Type or speak to Jarvis…"><button class="primary">Send</button></div></div>`
  const input=qs('input',body),go=()=>{const text=input.value.trim();if(text){send('submit_text',{text});input.value=''}}
  qs('.primary',body).onclick=go;qs('.mic-button',body).onclick=()=>send('push_to_talk');input.onkeydown=e=>{if(e.key==='Enter')go()}
  requestAnimationFrame(()=>{const scroll=qs('.conversation-scroll',body);if(scroll)scroll.scrollTop=scroll.scrollHeight})
}
function parseSources(){return state.runtime.response.split(/\r?\n/).flatMap(line=>{const m=line.match(/https?:\/\/\S+/);if(!m)return[];return[{url:m[0].replace(/[),.;]+$/,''),label:line.replace(m[0],'').replace(/^\s*\d+[.)]\s*/,'').replace(/[—–-]\s*$/,'').trim()||m[0]}]})}
function renderSources(body){const src=parseSources();body.innerHTML=src.length?`<div class="source-list">${src.map((s,i)=>`<a href="${attr(s.url)}" target="_blank"><span class="n">${i+1}</span><div><b>${esc(s.label)}</b><small>${esc(s.url)}</small></div></a>`).join('')}</div>`:`<div class="empty">Sources appear here after researched answers.</div>`}
function renderSystem(body){const m=state.metrics;body.innerHTML=`<div class="metrics">${metric('CPU',m.cpu)}${metric('RAM',m.ram)}${metric('BAT',m.battery)}</div>`}
function metric(n,v){const x=v==null?0:v;return`<div class="metric"><div class="metric-name">${n}</div><div class="metric-value">${v==null?'—':`${x}%`}</div><div class="meter"><span style="width:${Math.min(100,x)}%"></span></div></div>`}
function renderContext(body){const rows=[['AI',state.config.ai_model_name||'jarvis-qwen'],['Provider',state.config.ai_provider||'LM Studio'],['Mic',state.config.mic_name||'Default'],['Wake',state.config.wake_word_enabled?'ON':'OFF'],['Voice',state.config.voice_enabled?'ON':'MUTED'],['Web',state.config.searxng_base_url||'local'],['AI status',state.aiStatus],['Last error',state.runtime.error||'—']];body.innerHTML=`<div class="context">${rows.map(([k,v])=>`<div class="info"><span>${esc(String(k))}</span><b>${esc(String(v))}</b></div>`).join('')}</div>`}
function renderCamera(body){body.innerHTML=`<div class="camera"><div class="camera-off">Camera is off<br><small>Explicit permission only.</small></div><div class="error"></div><button class="primary">Enable camera</button></div>`;const btn=qs('button',body),host=qs('.camera',body),err=qs('.error',body);btn.onclick=async()=>{if(state.cameraStream){state.cameraStream.getTracks().forEach(t=>t.stop());state.cameraStream=null;renderCamera(body);return}try{const stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});state.cameraStream=stream;const v=document.createElement('video');v.autoplay=true;v.playsInline=true;v.muted=true;v.srcObject=stream;qs('.camera-off',body).replaceWith(v);btn.textContent='Disable camera'}catch(e){err.textContent=String(e)}}}
function renderSettings(body){body.innerHTML=`<div class="settings"><label>Address me as<input data-k="address_name" value="${attr(state.config.address_name||'sir')}"></label><label>Tone<select data-k="tone_mode"><option>Respectful</option><option>Neutral</option><option>Casual</option></select></label><label>Language<select data-k="language_mode"><option>Auto</option><option>English</option><option>Hebrew</option></select></label><label>Wake threshold<input type="number" step="0.01" min="0.05" max="0.9" data-k="wake_word_threshold" value="${Number(state.config.wake_word_threshold||.15)}"></label><label>Start with Windows<select data-k="start_with_windows"><option value="true">On</option><option value="false">Off</option></select></label><div class="settings-actions"><button data-a="toggle_wake_word">Toggle wake word</button><button data-a="toggle_voice">Mute / unmute</button><button data-a="test_microphone">Test mic</button><button data-a="test_voice">Test voice</button><button data-a="clear_memory">Clear memory</button></div></div>`;const tone=body.querySelector('[data-k="tone_mode"]'),lang=body.querySelector('[data-k="language_mode"]'),startup=body.querySelector('[data-k="start_with_windows"]');tone.value=state.config.tone_mode||'Respectful';lang.value=state.config.language_mode||'Auto';startup.value=state.config.start_with_windows?'true':'false';body.querySelectorAll('[data-k]').forEach(x=>{x.onchange=()=>{let value=x.type==='number'?Number(x.value):x.value;if(x.dataset.k==='start_with_windows')value=x.value==='true';send('config_patch',{[x.dataset.k]:value})}});body.querySelectorAll('[data-a]').forEach(x=>x.onclick=()=>send(x.dataset.a))}
function renderPopout(id){app.innerHTML=`<div class="popout"></div>`;const item=p(id,0,0,12,12),el=makeWidget(item);el.classList.remove('fullscreen-widget');qs('.popout').appendChild(el);qs('[data-hide]',el).onclick=()=>window.close()}
function showPalette(){if(document.querySelector('.palette-backdrop'))return;const div=document.createElement('div');div.className='palette-backdrop';div.innerHTML=`<div class="palette"><h3>Command Palette</h3><input autofocus placeholder="Type a command…"><div class="palette-results"></div></div>`;document.body.appendChild(div);div.onclick=e=>{if(e.target===div)div.remove()};const inp=qs('input',div),res=qs('.palette-results',div);const commands=[...Object.keys(state.layouts).map(w=>({label:`Switch to ${w}`,run:()=>{state.workspace=w;save();renderAll()}})),{label:'Push-to-talk',run:()=>send('push_to_talk')},{label:'Show Settings',run:()=>showWidget('settings')},{label:'Show Agent Activity',run:()=>showWidget('activity')},{label:'Show Camera',run:()=>showWidget('camera')},{label:'Show Sources',run:()=>showWidget('sources')}];const draw=()=>{const q=inp.value.toLowerCase();res.innerHTML=commands.filter(c=>c.label.toLowerCase().includes(q)).map((c,i)=>`<button data-i="${i}">${esc(c.label)}</button>`).join('');const filtered=commands.filter(c=>c.label.toLowerCase().includes(q));res.querySelectorAll('button').forEach((b,i)=>b.onclick=()=>{filtered[i].run();div.remove()})};inp.oninput=draw;draw();setTimeout(()=>inp.focus(),0)}
function bindGlobalKeys(){window.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();showPalette()}}}
window.onresize=()=>positionAll()
function clamp(n,a,b){return Math.max(a,Math.min(b,n))}function qs(s,r=document){return r.querySelector(s)}function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function attr(v){return esc(v)}
connect();renderAll()
