"""Idempotent persistent local queue, preview, and publication scheduler."""
from __future__ import annotations
import json
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .episodes import EPISODES,save_examples
from .quality import inspect_story, inspect_render
from .renderer import render
from .voice import piper_narrate
from .planner import new_story
from .youtube_api import upload


def root_dir():return Path.cwd()/'var'/'youtube_autopilot'

def dump(path:Path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    tmp.replace(path)

def read(path:Path,default=None):return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def setup(root:Path):
    root.mkdir(parents=True,exist_ok=True)
    if not (root/'config.json').exists():
        dump(root/'config.json',{
            'channel_nickname':'Nori & Blink',
            'series_approved':False,
            'autopublish_enabled':False,
            'frequency_days':3,
            'queue_ahead':3,
            'publish_local_time':'16:00',
            'timezone':'Asia/Jerusalem',
            'width':720,'height':1280,'fps':20,'scene_seconds':7.0,
            'piper_bin':'piper','piper_model':'',
            'lmstudio_enabled':False,
            'lmstudio_model':'qwen/qwen3.5-9b',
            'lmstudio_url':'http://127.0.0.1:1234/v1/chat/completions',
            'client_secrets':str(root/'client_secrets.json'),
            'token_file':str(root/'token.json'),
        })
    if not (root/'jobs.json').exists():dump(root/'jobs.json',[])
    stories=root/'stories'
    if not stories.exists():save_examples(stories)
    (root/'renders').mkdir(exist_ok=True)
    return root

def config(root):return read(root/'config.json')

def all_stories(root):
    episodes=[]
    for path in sorted((root/'stories').glob('*.json')):
        ep=read(path)
        inspect_story(ep)
        episodes.append((ep,path))
    return episodes

def slots(config, jobs):
    zone=ZoneInfo(config['timezone'])
    now=datetime.now(zone)
    hh,mm=map(int,config['publish_local_time'].split(':'))
    existing=[datetime.fromisoformat(j['publish_at']).astimezone(zone) for j in jobs]
    if existing:
        latest=max(existing)
        candidate=latest+timedelta(days=int(config['frequency_days']))
    else:candidate=(now+timedelta(days=2)).replace(hour=hh,minute=mm,second=0,microsecond=0)
    if candidate<=now+timedelta(hours=4):candidate=(now+timedelta(days=2)).replace(hour=hh,minute=mm,second=0,microsecond=0)
    return candidate

def plan(root:Path,generate:bool=False):
    setup(root)
    c=config(root);jobs=read(root/'jobs.json',[])
    stories=all_stories(root)
    used={j['episode_id'] for j in jobs}
    active=sum(1 for j in jobs if j['state'] in ('queued','needs_voice','uploading','ready') or (j['state']=='scheduled' and datetime.fromisoformat(j['publish_at'])>datetime.now(timezone.utc)))
    target=max(0,min(8,int(c['queue_ahead'])))
    added=[]
    while active<target:
        unused=[(ep,p) for ep,p in stories if ep['id'] not in used]
        if not unused:
            if not generate or not c['lmstudio_enabled']:break
            existing=[ep for ep,_ in stories]
            ep=new_story(c,existing)
            p=root/'stories'/(ep['id']+'.json');dump(p,ep)
            stories.append((ep,p));unused=[(ep,p)]
        ep,path=unused[0]
        when=slots(c,jobs)
        job={'id':ep['id'],'episode_id':ep['id'],'episode_path':str(path),'publish_at':when.isoformat(),
             'state':'queued','video_path':str(root/'renders'/(ep['id']+'.mp4')),'youtube_id':None,'error':None}
        jobs.append(job);used.add(ep['id']);added.append(job);active+=1
    dump(root/'jobs.json',jobs)
    return added

def run_one(root:Path, *, preview=False):
    setup(root)
    c=config(root); jobs=read(root/'jobs.json',[])
    candidates=[j for j in jobs if j['state'] in ('queued','needs_voice','ready')]
    if not candidates:return {'state':'nothing_to_do'}
    job=candidates[0]
    ep=read(Path(job['episode_path']));inspect_story(ep)
    video=Path(job['video_path']); voice=root/'renders'/(ep['id']+'.wav')
    if job['state']=='needs_voice' and not c['piper_model'] and video.exists():
        return {'state':'needs_voice','video_path':str(video),'note':'No Piper voice configured; upload is blocked'}
    if job['state'] in ('queued','needs_voice') or not video.exists():
        # A silent preview may be rendered for inspection, but it will NEVER pass upload QA.
        voice_file=None
        if c['piper_model']:
            voice_file=piper_narrate(ep,voice,model=c['piper_model'],piper_bin=c['piper_bin'],scene_seconds=float(c['scene_seconds']))
        render(Path(job['episode_path']),video,voice_file,width=int(c['width']),height=int(c['height']),fps=int(c['fps']),scene_seconds=float(c['scene_seconds']))
        job['state']='ready' if voice_file else 'needs_voice'
        job['error']=None if voice_file else 'No narrated audio. Silent preview generated; upload blocked.'
        dump(root/'jobs.json',jobs)
    if preview or job['state']=='needs_voice':
        return {'state':job['state'],'video_path':str(video),'note':'Local-only preview, no upload'}
    # Hard publication gates. No web request before these checks.
    if not c['autopublish_enabled'] or not c['series_approved']:
        return {'state':'ready','video_path':str(video),'note':'Auto publication disabled; video ready for review'}
    qa=inspect_render(video,min_seconds=20)
    if not Path(c['token_file']).is_file():
        return {'state':'ready','note':'YouTube OAuth token missing; run authorize first','qa':qa}
    scheduled=datetime.fromisoformat(job['publish_at'])
    if scheduled<=datetime.now(timezone.utc)+timedelta(minutes=15):
        job['state']='manual_review';job['error']='Scheduled time passed or too close. Resolve before upload.'
        dump(root/'jobs.json',jobs)
        return {'state':'manual_review','error':job['error']}
    # Commit reservation *before* contacting YouTube. Unknown upload results never retried automatically.
    job['state']='uploading';dump(root/'jobs.json',jobs)
    try:
        result=upload(video,ep,scheduled,{'token_file':c['token_file'],'client_secrets':c['client_secrets']})
    except Exception as exc:
        job['state']='manual_review'
        job['error']=str(exc)
        dump(root/'jobs.json',jobs)
        raise
    job['state']='scheduled';job['youtube_id']=result['id'];job['error']=None
    dump(root/'jobs.json',jobs)
    return {'state':'scheduled','video_path':str(video),'youtube':result,'qa':qa}

def readiness(root:Path):
    """Non-destructive system diagnostic: no network calls, uploads, or renders."""
    setup(root)
    c=config(root)
    jobs=read(root/'jobs.json',[])
    model=Path(str(c.get('piper_model',''))) if c.get('piper_model') else None
    voice_ok=bool(model and model.is_file() and Path(str(model)+'.json').is_file())
    piper_bin=str(c.get('piper_bin') or 'piper')
    checks={
        'ffmpeg':bool(shutil.which('ffmpeg')),
        'ffprobe':bool(shutil.which('ffprobe')),
        'piper_executable':bool(shutil.which(piper_bin)),
        'piper_voice_model_and_config':voice_ok,
        'youtube_oauth_client_file':Path(c['client_secrets']).is_file(),
        'youtube_token_file':Path(c['token_file']).is_file(),
    }
    render_checks=[]
    for j in jobs:
        if j.get('state') in ('ready','needs_voice') and Path(j['video_path']).is_file():
            try: inspect_render(Path(j['video_path']),min_seconds=20)
            except Exception as ex:
                render_checks.append({'id':j['id'],'qa_passed':False,'issue':str(ex)})
            else: render_checks.append({'id':j['id'],'qa_passed':True})
    checks['at_least_one_qa_passed_video']=any(r['qa_passed'] for r in render_checks)
    return {
        'ready_to_enable':all(checks.values()),
        'autopublish_enabled':bool(c.get('autopublish_enabled',False)),
        'series_approved':bool(c.get('series_approved',False)),
        'checks':checks,
        'render_checks':render_checks,
        'queued':sum(j.get('state')=='queued' for j in jobs),
        'note':'Diagnostic only. Visual, audio and originality review must be completed by a human before enable.'
    }

def switch(root,enable:bool,phrase:str=''):
    setup(root)
    c=config(root)
    if enable:
        if phrase!='I APPROVE NORI AND BLINK AUTOPUBLISH':
            raise ValueError('Explicit one-time approval phrase is required.')
        report=readiness(root)
        if not report['ready_to_enable']:
            failed=[k for k,v in report['checks'].items() if not v]
            raise RuntimeError('Autopublish blocked: '+', '.join(failed)+'. Run doctor and inspect a narrated preview first.')
        c['series_approved']=True
        c['autopublish_enabled']=True
    else:
        # Explicit pause revokes the premature approval left by v0.1.
        c['series_approved']=False
        c['autopublish_enabled']=False
    dump(root/'config.json',c)
    return c['autopublish_enabled']

class FileLock:
    def __init__(self,path):self.path=path;self.fd=None
    def __enter__(self):
        try:self.fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError:raise RuntimeError('Worker already running, or stale lock; check process before removing lock')
        os.write(self.fd,str(os.getpid()).encode());return self
    def __exit__(self,*args):
        if self.fd is not None:os.close(self.fd)
        try:self.path.unlink()
        except FileNotFoundError:pass

def tick(root:Path, *, generate:bool=False, count:int=1):
    setup(root)
    with FileLock(root/'worker.lock'):
        new=plan(root,generate=generate)
        results=[]
        for _ in range(max(1,min(int(count),8))):
            result=run_one(root)
            results.append(result)
            if result['state'] in ('nothing_to_do','needs_voice','ready','manual_review'):break
        return {'new_jobs':len(new),'results':results}
