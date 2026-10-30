const $=id=>document.getElementById(id);
let CFG=null,SESSION=null,REPORT=null,lastRequest=null;
let languageMode="auto";
let effectiveLang=(navigator.language||"en").toLowerCase().startsWith("he")?"he":"en";

const T={
  he:{
    language:"שפה",kicker:"JARVIS / בין השורות",
    heroTitle:"מה באמת קורה בשיחה הזאת?",
    heroText:"מעלים ייצוא של WhatsApp, מסמנים מי אתם ומה סוג הקשר, ומתחילים מהעובדות שהשיחה עצמה מוכיחה.",
    uploadTitle:"העלאת השיחה",chooseFile:"בחרו ZIP או TXT",fileHint:"הצ׳אט הגולמי לא נשמר",
    read:"קריאת השיחה",reading:"קורא את השיחה…",
    setupTitle:"מי נמצא בשיחה?",setupCopy:"אפשר לשנות את השם שיופיע בדוח בלי לשנות את הייצוא המקורי.",
    alias:"שם שיופיע בדוח",self:"זה אני",rawName:"מהייצוא",other:"האדם המרכזי מולך",
    relationship:"סוג הקשר",desc:"תארו את הקשר",goal:"מה אתם רוצים להבין?",
    generate:"יצירת דוח 1 החינמי",building:"בונה את דוח 1…",
    reportLabel:"דוח 1 · חינם",numbersTitle:"המספרים",numbersIntro:"קודם העובדות. אחר כך הסיפור.",
    fullKicker:"השלב הבא",fullTitle:"הדוח המלא",
    fullText:"ניתוח מעמיק של הדינמיקה, נקודות המפנה והדפוסים שחוזרים לאורך הקשר.",
    soon:"בקרוב",privacy:"המידע שלכם נשאר בשליטתכם",
    msgs:"הודעות",starts:"מי פותח את השיחה",peak:"יום השיא",
    silence:"השתיקה הארוכה ביותר",streak:"רצף ימים פעילים",
    hour:"פעילות לפי שעה",after22:"אחרי 22:00",peakHour:"שעת השיא",days:"ימים",hours:"שעות",
    activityTitle:"מפת פעילות יומית",heatLow:"פחות",heatHigh:"יותר",
    peakBreakdown:"פירוט יום השיא",peakBusyHour:"השעה העמוסה בתוך יום השיא",peakWindow:"חלון הפעילות",peakHourOverall:"השעה הפעילה ביותר לאורך כל הצ׳אט",
    messagesWord:"הודעות",weekdays:["א","ב","ג","ד","ה","ו","ש"],
    needDesc:"בחרת 'אחר' — צריך לתאר את הקשר.",needSelf:"צריך לבחור מי אתם בשיחה."
  },
  en:{
    language:"Language",kicker:"JARVIS / BETWEEN THE LINES",
    heroTitle:"What is really happening in this conversation?",
    heroText:"Upload a WhatsApp export, identify yourself and the relationship, and start with what the chat itself can actually support.",
    uploadTitle:"Upload the conversation",chooseFile:"Choose ZIP or TXT",fileHint:"Raw chat is not stored",
    read:"Read conversation",reading:"Reading the conversation…",
    setupTitle:"Who is in the conversation?",setupCopy:"You can change the names used in the report without changing the original export.",
    alias:"Name in report",self:"This is me",rawName:"From export",other:"Main person opposite you",
    relationship:"Relationship type",desc:"Describe the relationship",goal:"What do you want to understand?",
    generate:"Generate free Report 1",building:"Building Report 1…",
    reportLabel:"REPORT 1 · FREE",numbersTitle:"The numbers",numbersIntro:"Facts first. Story second.",
    fullKicker:"NEXT",fullTitle:"Full report",
    fullText:"A deeper analysis of the dynamic, turning points and patterns that repeat across the relationship.",
    soon:"Coming soon",privacy:"Your information stays under your control",
    msgs:"messages",starts:"Who starts the conversation",peak:"Peak day",
    silence:"Longest silence",streak:"Active-day streak",
    hour:"Activity by hour",after22:"after 22:00",peakHour:"peak hour",days:"days",hours:"hours",
    activityTitle:"Daily activity map",heatLow:"Less",heatHigh:"More",
    peakBreakdown:"Peak-day detail",peakBusyHour:"Busiest hour within the peak day",peakWindow:"Activity window",peakHourOverall:"Most active hour across the whole chat",
    messagesWord:"messages",weekdays:["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],
    needDesc:"You chose Other — describe the relationship.",needSelf:"Choose which participant is you."
  }
};

function t(){return T[effectiveLang]}
function setDir(){
  document.documentElement.lang=effectiveLang;
  document.documentElement.dir=effectiveLang==="he"?"rtl":"ltr";
}
function resolveLang(){
  if(languageMode==="he"||languageMode==="en") return languageMode;
  if(SESSION?.language_guess==="he"||SESSION?.language_guess==="en") return SESSION.language_guess;
  return (navigator.language||"en").toLowerCase().startsWith("he")?"he":"en";
}
function fillLanguages(){
  const s=$("languageMode");
  s.innerHTML="";
  CFG.languages.forEach(x=>{
    const o=document.createElement("option");
    o.value=x.id;
    o.textContent=effectiveLang==="he"?x.label_he:x.label_en;
    s.appendChild(o);
  });
  s.value=languageMode;
}
function fillRelationships(){
  const s=$("relationshipType");
  const v=s.value;
  s.innerHTML="";
  const ph=document.createElement("option");
  ph.value="";
  ph.textContent=effectiveLang==="he"?"בחרו סוג קשר…":"Choose relationship type…";
  s.appendChild(ph);
  CFG.relationship_types.forEach(x=>{
    const o=document.createElement("option");
    o.value=x.id;
    o.textContent=effectiveLang==="he"?x.label_he:x.label_en;
    s.appendChild(o);
  });
  if(v&&[...s.options].some(o=>o.value===v)) s.value=v;
}
function applyLanguage(){
  effectiveLang=resolveLang();
  setDir();
  const x=t();
  $("languageLabel").textContent=x.language;
  $("kicker").textContent=x.kicker;
  $("heroTitle").textContent=x.heroTitle;
  $("heroText").textContent=x.heroText;
  $("uploadTitle").textContent=x.uploadTitle;
  $("chooseFile").textContent=$("file").files[0]?.name||x.chooseFile;
  $("fileHint").textContent=x.fileHint;
  $("uploadBtn").textContent=x.read;
  $("setupTitle").textContent=x.setupTitle;
  $("setupCopy").textContent=x.setupCopy;
  $("otherPersonLabel").textContent=x.other;
  $("relationshipLabel").textContent=x.relationship;
  $("relationshipDescriptionLabel").textContent=x.desc;
  $("goalLabel").textContent=x.goal;
  $("analyzeBtn").textContent=x.generate;
  $("reportLabel").textContent=x.reportLabel;
  $("numbersTitle").textContent=x.numbersTitle;
  $("numbersIntro").textContent=x.numbersIntro;
  $("fullKicker").textContent=x.fullKicker;
  $("fullTitle").textContent=x.fullTitle;
  $("fullText").textContent=x.fullText;
  $("fullBtn").textContent=x.soon;
  $("privacyFoot").textContent=x.privacy;
  $("hourTitle").textContent=x.hour;
  $("activityTitle").textContent=x.activityTitle;
  $("heatLow").textContent=x.heatLow;
  $("heatHigh").textContent=x.heatHigh;
  fillLanguages();
  fillRelationships();
  if(SESSION) renderParticipants();
  if(REPORT) renderReport(REPORT,false);
}
function show(id){$(id).classList.remove("hidden")}
function status(id,msg,bad=false){
  $(id).textContent=msg;
  $(id).className="status"+(bad?" bad":"");
}
function esc(s){
  return String(s??"").replace(/[&<>"']/g,c=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}
function renderParticipants(){
  const wrap=$("participants");
  if(!SESSION) return;

  const previous={};
  wrap.querySelectorAll(".participant").forEach(r=>{
    previous[r.dataset.raw]=r.querySelector("input[type=text]").value;
  });
  const checked=wrap.querySelector("input[type=radio]:checked")?.value;
  wrap.innerHTML="";

  SESSION.participants.forEach((p,i)=>{
    const row=document.createElement("div");
    row.className="participant";
    row.dataset.raw=p;
    const defaultAlias=previous[p]??(p.toLowerCase()==="you"?"":p);
    row.innerHTML=`
      <input class="self-radio" type="radio" name="self" value="${esc(p)}"
        ${checked===p||(!checked&&i===0)?"checked":""} title="${esc(t().self)}">
      <span class="raw">${esc(p)}<br><small>${esc(t().rawName)}</small></span>
      <input type="text" value="${esc(defaultAlias)}" placeholder="${esc(t().alias)}">
    `;
    wrap.appendChild(row);
  });
  fillOtherSelect();
}
function aliases(){
  const a={};
  document.querySelectorAll(".participant").forEach(r=>{
    a[r.dataset.raw]=r.querySelector("input[type=text]").value.trim();
  });
  return a;
}
function selfRaw(){
  return document.querySelector("input[name=self]:checked")?.value||"";
}
function fillOtherSelect(){
  const s=$("otherParticipant");
  const old=s.value;
  s.innerHTML='<option value="">—</option>';
  if(!SESSION) return;
  const a=aliases();
  SESSION.participants.forEach(p=>{
    if(p===selfRaw()) return;
    const o=document.createElement("option");
    o.value=p;
    o.textContent=a[p]||p;
    s.appendChild(o);
  });
  if(old&&[...s.options].some(o=>o.value===old)) s.value=old;
  else if(s.options.length===2) s.selectedIndex=1;
}
async function init(){
  CFG=await (await fetch("/api/config")).json();
  $("limitText").textContent=`Max ${CFG.max_upload_mb} MB`;
  applyLanguage();
  try{
    const h=await (await fetch("/api/semantic-health")).json();
    if($("semanticHint")) $("semanticHint").textContent=h.model_loaded ? (effectiveLang==="he"?"מנוע הניתוח הסמנטי מוכן":"Semantic analysis engine ready") : (effectiveLang==="he"?"מנוע הניתוח הסמנטי יופעל בעת יצירת הדוח":"Semantic engine will be started when Report 1 is generated");
  }catch(_){}
}
$("languageMode").onchange=async e=>{
  languageMode=e.target.value;
  applyLanguage();
  if(REPORT&&lastRequest) await analyze(true);
};
$("file").onchange=()=>{
  $("chooseFile").textContent=$("file").files[0]?.name||t().chooseFile;
};
$("participants").addEventListener("change",e=>{
  if(e.target.matches("input[type=radio]")) fillOtherSelect();
});
$("participants").addEventListener("input",e=>{
  if(e.target.matches("input[type=text]")) fillOtherSelect();
});
$("relationshipType").onchange=()=>{
  $("relationshipDescriptionWrap").classList.toggle("hidden",$("relationshipType").value!=="other");
};

$("uploadBtn").onclick=async()=>{
  const f=$("file").files[0];
  if(!f) return;
  if(f.size>CFG.max_upload_mb*1024*1024)
    return status("uploadStatus",`Max ${CFG.max_upload_mb} MB`,true);

  status("uploadStatus",t().reading);
  const fd=new FormData();
  fd.append("file",f);
  const r=await fetch("/api/upload",{method:"POST",body:fd});
  const j=await r.json();
  if(!r.ok) return status("uploadStatus",j.detail||"Upload failed",true);

  SESSION=j;
  REPORT=null;
  lastRequest=null;
  $("reportBody").innerHTML="";
  $("numberCards").innerHTML="";
  $("hours").innerHTML="";
  $("calendarHeat").innerHTML="";
  $("reportBlock").classList.add("hidden");
  $("relationshipType").value="";
  $("relationshipDescription").value="";
  $("relationshipDescriptionWrap").classList.add("hidden");
  $("goal").value="";
  effectiveLang=resolveLang();
  applyLanguage();
  $("relationshipType").value="";
  status("uploadStatus",`${j.message_count.toLocaleString()} ${t().msgs}`);
  show("setupBlock");
  $("setupBlock").scrollIntoView({behavior:"smooth"});
};

async function analyze(silent=false){
  if(!SESSION) return;
  const user=selfRaw();
  if(!user) return status("analyzeStatus",t().needSelf,true);
  if(!$("relationshipType").value) return status("analyzeStatus",effectiveLang==="he"?"צריך לבחור סוג קשר.":"Choose a relationship type.",true);
  if($("relationshipType").value==="other"&&!$("relationshipDescription").value.trim())
    return status("analyzeStatus",t().needDesc,true);

  if(!silent) status("analyzeStatus",t().building);
  lastRequest={
    session_id:SESSION.session_id,
    user_participant:user,
    other_participant:$("otherParticipant").value||null,
    aliases:aliases(),
    relationship_type:$("relationshipType").value,
    relationship_description:$("relationshipDescription").value,
    goal:$("goal").value,
    language:languageMode
  };
  const r=await fetch("/api/analyze",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(lastRequest)
  });
  const j=await r.json();
  if(!r.ok) return status("analyzeStatus",j.detail||"Analysis failed",true);

  REPORT=j;
  effectiveLang=j.language;
  setDir();
  applyLanguage();
  renderReport(j,true);
  status("analyzeStatus","");
  show("reportBlock");
  if(!silent) $("reportBlock").scrollIntoView({behavior:"smooth"});
}
$("analyzeBtn").onclick=()=>analyze(false);

function renderReport(r,withNumbers=true){
  $("reportTitle").textContent=r.title;
  $("reportSubtitle").textContent=r.subtitle;
  const intro=(r.paragraphs||[]).map(p=>`<p>${esc(p)}</p>`).join("");
  const sections=(r.sections||[]).map((s,i)=>{
    const ps=(s.paragraphs||[]).map(p=>`<p>${esc(p)}</p>`).join("");
    const quotes=(s.quotes||[]).map(q=>`<blockquote class="chat-quote"><div>${esc(q.text||"")}</div><footer>${esc(q.sender||"")}${q.date?` · ${esc(q.date)}`:""}</footer></blockquote>`).join("");
    const evidence=(s.evidence||[]).length?`<div class="evidence-strip">${s.evidence.map(x=>`<span>${esc(x)}</span>`).join("")}</div>`:"";
    const punch=s.punchline?`<div class="report-punch">${esc(s.punchline)}</div>`:"";
    const kind=["verdict","mirror","timeline","texture","context","lesson","data","goal"].includes(s.kind)?s.kind:"plain";
    return `<section class="report-section report-kind-${kind}"><div class="report-section-num">${String(i+1).padStart(2,"0")}</div><div><h3>${esc(s.title||"")}</h3>${punch}${ps}${quotes}${evidence}</div></section>`;
  }).join("");
  $("reportBody").innerHTML=`<div class="report-intro">${intro}</div>${sections}`;
  const h=$("highlights");
  h.className="highlights";
  h.innerHTML=(r.highlights||[]).map(x=>`<div class="highlight">${esc(x)}</div>`).join("");
  if(withNumbers) renderNumbers(r.numbers);
}
function renderNumbers(n){
  const p=n.participants||[];
  let html="";
  html+=`<div class="stat-card mint"><div style="width:100%"><div class="card-title">${esc(t().msgs)}</div>${
    p.map(x=>`<div class="bar-row"><span>${esc(x.name)}</span><div class="bar"><i style="width:${x.share}%"></i></div><b>${x.messages.toLocaleString()}</b></div>`).join("")
  }</div></div>`;
  html+=`<div class="stat-card lav"><div style="width:100%"><div class="card-title">${esc(t().starts)}</div>${
    p.map(x=>`<div class="bar-row"><span>${esc(x.name)}</span><div class="bar"><i style="width:${x.start_share}%"></i></div><b>${x.start_share}%</b></div>`).join("")
  }</div></div>`;
  const pd=n.peak_day_details||{};
  const peakDate=formatDateHuman(pd.date||n.peak_day);
  const participantDetail=(pd.participants||[]).map(x=>`${esc(x.name)}: <b>${x.messages.toLocaleString()}</b>`).join(" · ");
  const peakHourDetail=pd.peak_hour==null?"—":`${String(pd.peak_hour).padStart(2,"0")}:00 (${(pd.peak_hour_messages||0).toLocaleString()} ${esc(t().messagesWord)})`;
  const windowDetail=(pd.first_message_time&&pd.last_message_time)?`${pd.first_message_time}–${pd.last_message_time}`:"—";
  html+=`<div class="peak-card peach">
    <div class="peak-main"><div><div class="card-title">${esc(t().peak)}</div><strong>${esc(peakDate)}</strong></div><b class="peak-total">${(n.peak_day_messages||0).toLocaleString()}</b></div>
    <div class="peak-details">
      <div><span>${esc(t().peakBreakdown)}</span><p>${participantDetail||"—"}</p></div>
      <div><span>${esc(t().peakBusyHour)}</span><p>${peakHourDetail}</p></div>
      <div><span>${esc(t().peakWindow)}</span><p>${windowDetail}</p></div>
    </div>
  </div>`;
  const silence=n.longest_silence_hours==null?"—":
    n.longest_silence_hours>=24?
      `${(n.longest_silence_hours/24).toFixed(1)} ${t().days}`:
      `${n.longest_silence_hours.toFixed(1)} ${t().hours}`;
  html+=`<div class="stat-card rose"><div><div class="card-title">${esc(t().silence)}</div></div><b>${esc(silence)}</b></div>`;
  html+=`<div class="stat-card mint"><div><div class="card-title">${esc(t().streak)}</div></div><b>${n.longest_active_streak_days||0}</b></div>`;
  $("numberCards").innerHTML=html;

  const hourCounts=n.hourly_counts||[];
  const max=Math.max(...(hourCounts.length?hourCounts:[1]),1);
  $("hours").innerHTML=hourCounts.map((v,h)=>`<i title="${String(h).padStart(2,"0")}:00 — ${v.toLocaleString()} ${esc(t().messagesWord)}" style="height:${Math.max(2,v/max*100)}%"></i>`).join("");
  $("hourTicks").innerHTML=hourCounts.map((_,h)=>`<span class="${h%3===0||h===23?"show":""}">${String(h).padStart(2,"0")}</span>`).join("");
  $("hourFoot").textContent=`${n.after_22_percent}% ${t().after22} · ${t().peakHourOverall}: ${String(n.peak_hour??0).padStart(2,"0")}:00`;
  renderHeat(n.daily_activity||[]);
}
function formatDateHuman(iso){
  if(!iso) return "—";
  const d=new Date(iso+"T00:00:00");
  return new Intl.DateTimeFormat(effectiveLang==="he"?"he-IL":"en-GB",{weekday:"long",day:"numeric",month:"long",year:"numeric"}).format(d);
}
function renderHeat(days){
  const wrap=$("calendarHeat"), months=$("heatMonths"), weekdays=$("heatWeekdays");
  wrap.innerHTML=""; months.innerHTML=""; weekdays.innerHTML="";
  if(!days.length){ $("activityRange").textContent=""; return; }

  const data=days.slice(-364);
  const counts=data.map(x=>x.count).sort((a,b)=>a-b);
  const q=p=>counts[Math.min(counts.length-1,Math.floor(counts.length*p))]||1;
  const q1=q(.25),q2=q(.5),q3=q(.75);

  const first=new Date(data[0].date+"T00:00:00");
  const last=new Date(data[data.length-1].date+"T00:00:00");
  const origin=new Date(first); origin.setDate(origin.getDate()-origin.getDay());
  const msDay=86400000;
  const weekCount=Math.floor((last-origin)/msDay/7)+1;
  wrap.style.gridTemplateColumns=`repeat(${weekCount}, minmax(10px, 1fr))`;
  months.style.gridTemplateColumns=`repeat(${weekCount}, minmax(10px, 1fr))`;

  t().weekdays.forEach((name,i)=>{
    const x=document.createElement("span"); x.textContent=name; x.style.gridRow=String(i+1); weekdays.appendChild(x);
  });

  let lastMonth=-1;
  data.forEach(d=>{
    const dt=new Date(d.date+"T00:00:00");
    const week=Math.floor((dt-origin)/msDay/7);
    const weekday=dt.getDay();
    const c=document.createElement("i");
    const level=d.count===0?"zero":(d.count>=q3?"l4":d.count>=q2?"l3":d.count>=q1?"l2":"l1");
    c.className=`heat-cell ${level}`;
    c.style.gridColumn=String(week+1);
    c.style.gridRow=String(weekday+1);
    c.title=`${formatDateHuman(d.date)} — ${d.count.toLocaleString()} ${t().messagesWord}`;
    wrap.appendChild(c);

    if(dt.getMonth()!==lastMonth){
      lastMonth=dt.getMonth();
      const m=document.createElement("span");
      m.style.gridColumn=String(week+1);
      m.textContent=new Intl.DateTimeFormat(effectiveLang==="he"?"he-IL":"en-GB",{month:"short"}).format(dt);
      months.appendChild(m);
    }
  });
  $("activityRange").textContent=`${formatDateHuman(data[0].date)} — ${formatDateHuman(data[data.length-1].date)}`;
}
init().catch(e=>status("uploadStatus",String(e),true));
