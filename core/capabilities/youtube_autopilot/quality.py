"""Mechanical QA for original children's shorts. Does NOT replace human review."""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from .episodes import validate_episode

BLOCKED=re.compile(r'\b(peppa|piggy|disney|cocomelon|paw patrol|violent|weapon|blood|scary|kill|poison|subscribe|click here|buy now)\b', re.I)

def inspect_story(ep):
    validate_episode(ep)
    data=json.dumps(ep,ensure_ascii=False)
    if BLOCKED.search(data):raise ValueError('Story requires human review: sensitive, marketing, or copyrighted reference')
    if any(len(s['narration'].split())>23 for s in ep['scenes']):raise ValueError('Narration sentence too long for scene')
    if len(set(s['caption'].casefold() for s in ep['scenes']))<len(ep['scenes']):raise ValueError('Repeated captions')
    return True

def motion_audit(video:Path,length:float):
    """Find near-static scenes; intentionally a BLOCKING lower bound, not artistic approval.

    Measures differences between samples *inside* scenes to avoid giving hard
    scene cuts free credit. Frame differences are only a crude motion proxy.
    """
    if not shutil.which('ffmpeg'):raise RuntimeError('ffmpeg required for motion QA')
    pairs=[]
    # Within-scene offsets for a 6-scene video; avoid checking only cuts.
    for fraction in [0.,1/6,2/6,3/6,4/6,5/6]:
        st=length*fraction
        pairs.append((st+length/42.,st+length/14.))
    differences=[]
    for ta,tb in pairs:
        imgs=[]
        for t in (ta,tb):
            p=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(round(t,3)),'-i',str(video),'-frames:v','1','-vf','scale=160:284','-f','image2pipe','-vcodec','mjpeg','-'],capture_output=True,timeout=15)
            if p.returncode or not p.stdout:raise ValueError('Failed to sample animation frames')
            imgs.append(Image.open(BytesIO(p.stdout)).convert('RGB'))
        s=ImageStat.Stat(ImageChops.difference(imgs[0],imgs[1]))
        differences.append(sum(s.mean)/3)
    score=sum(differences)/len(differences)
    lively=sum(v>=3.0 for v in differences)
    if score<3.0 or lively<3:
        raise ValueError(f'Insufficient animated motion: motion_score={score:.2f}; animated_scenes={lively}/6. Manual creative review required.')
    return {'motion_score':round(score,2),'animated_scenes':lively,'frames_compared':12}

def inspect_render(video:Path,min_seconds:float=20):
    if not shutil.which('ffprobe'):raise RuntimeError('ffprobe is required')
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)],text=True))
    streams=data['streams'];v=next((s for s in streams if s.get('codec_type')=='video'),None)
    a=next((s for s in streams if s.get('codec_type')=='audio'),None)
    if not v or not a:raise ValueError('Video needs BOTH animated video and voiced English narration for auto-upload')
    if int(v['width'])<360 or int(v['height'])<640:raise ValueError('Rendered size too low')
    length=float(data['format']['duration'])
    if not min_seconds<=length<=180:raise ValueError('Invalid video duration')
    if Path(video).stat().st_size<50_000:raise ValueError('Suspiciously small video file')
    motion=motion_audit(Path(video),length)
    return {'seconds':round(length,1),'resolution':f"{v['width']}x{v['height']}",'audio':True,'size_bytes':Path(video).stat().st_size,'motion_audit':motion,'human_approval_required':True}
