"""Nori & Blink v0.3 — animated original preschool-cartoon renderer.

Pillow/vector animation, 100% offline. API-compatible with v0.1 render() and
cartoon_frame(). No paid models; narration is still supplied by the voice module.
"""
from __future__ import annotations
import json
import math
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .episodes import validate_episode

FONTS = [
    'C:/Windows/Fonts/arialbd.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
]
@lru_cache(maxsize=32)
def font(size):
    for name in FONTS:
        if Path(name).is_file():return ImageFont.truetype(name,max(8,int(size)))
    return ImageFont.load_default()

def clamp(x,a=0.,b=1.):return max(a,min(b,x))
def ease(x):
    x=clamp(x)
    return x*x*(3-2*x)
def lerp(a,b,x):return a+(b-a)*x

def ellipse(d,box,fill,outline=None,width=1):
    d.ellipse(tuple(int(q) for q in box),fill=fill,outline=outline,width=width)
def rect(d,box,fill,radius=0,outline=None,width=1):
    b=tuple(int(q) for q in box)
    if radius:d.rounded_rectangle(b,radius=int(radius),fill=fill,outline=outline,width=width)
    else:d.rectangle(b,fill=fill,outline=outline,width=width)

def line(d,pts,color,width=2,joint='curve'):
    d.line([(int(a),int(b)) for a,b in pts],fill=color,width=max(1,int(width)),joint=joint)

@lru_cache(maxsize=16)
def sky(w,h,evening=False):
    # Pre-render static sky gradient to keep the animation inexpensive.
    img=Image.new('RGB',(w,h));p=img.load()
    a=(103,193,237) if not evening else (161,156,239)
    b=(249,250,224) if not evening else (253,210,187)
    for y in range(h):
        f=y/h
        f=f**.82
        c=tuple(int(lerp(a[k],b[k],f)) for k in range(3))
        for x in range(w):p[x,y]=c
    return img

def cloud(d,x,y,sc):
    c='#FFF9EE'
    for xo,yo,rx,ry in [(-40,7,41,22),(-9,-4,47,29),(25,5,42,23),(3,16,66,19)]:
        ellipse(d,(x+(xo-rx)*sc,y+(yo-ry)*sc,x+(xo+rx)*sc,y+(yo+ry)*sc),c)

def leaf(d,x,y,sc,color='#67BA82',angle=0):
    ellipse(d,(x-25*sc,y-9*sc,x+25*sc,y+9*sc),color)
    line(d,[(x-20*sc,y),(x+20*sc,y)],'#409B72',1.2*sc)

def tree(d,x,y,sc,t):
    # x,y refer to trunk bottom
    line(d,[(x,y),(x-2*sc,y-220*sc)],'#AA7051',29*sc)
    for bx,by,rr,col in [(-58,-205,91,'#64B98A'),(45,-238,104,'#84CC97'),(0,-280,94,'#93D6A1')]:
        xx=x+bx*sc; yy=y+by*sc
        ellipse(d,(xx-rr*sc,yy-rr*.64*sc,xx+rr*sc,yy+rr*.64*sc),col)
    for i in range(5):
        ang=(i+1)*2.4
        fx=x+(math.cos(ang)*85+math.sin(t*.5+i)*3)*sc
        fy=y-(240+math.sin(ang)*44)*sc
        ellipse(d,(fx-4*sc,fy-4*sc,fx+4*sc,fy+4*sc),'#F6D779')

def scenery(img,scene,t,local,w,h):
    d=ImageDraw.Draw(img)
    sc=w/360
    # Clouds move independently for gentle environmental life.
    cloud(d,w*.22+math.sin(t*.19)*12*sc,h*.15,sc*.66)
    cloud(d,w*.85-math.sin(t*.15)*17*sc,h*.24,sc*.51)
    ellipse(d,(w*.72,h*.085,w*.88,h*.175),'#FFE6A1')
    # Parallax hills
    d.ellipse((-w*.53,h*.50,w*.79,h*.96),fill='#BDE6B2')
    d.ellipse((w*.24,h*.49,w*1.65,h*.97),fill='#99D89F')
    d.ellipse((-w*.4,h*.64,w*1.35,h*1.14),fill='#74C79E')
    rect(d,(0,h*.82,w,h),'#F7DDA7')
    # Ground paths and grass
    d.ellipse((w*.13,h*.8,w*.87,h*1.18),fill='#F9E5BC')
    for i in range(16):
        gx=(i*.119+.055)*w%w
        gy=(.78+(i%3)*.035)*h
        line(d,[(gx-4*sc,gy),(gx-6*sc,gy-9*sc)],'#57AD78',2*sc)
        line(d,[(gx,gy),(gx+5*sc,gy-10*sc)],'#57AD78',2*sc)
    if scene in ('hello','butterfly'):
        tree(d,w*.08,h*.76,sc*.55,t)
    if scene=='look':
        tree(d,w*.79,h*.78,sc*.8,t)
        for i,(x,y) in enumerate([(.63,.78),(.73,.8),(.91,.79)]):
            ellipse(d,(w*x-22*sc,h*y-15*sc,w*x+22*sc,h*y+13*sc),['#9DB5AF','#7DA4A5','#B3B8A1'][i])
            ellipse(d,(w*x-12*sc,h*y-11*sc,w*x-4*sc,h*y-6*sc),'#D8D8C2')
    if scene=='flower':
        ellipse(d,(w*.46,h*.69,w*1.2,h*.91),'#86D5D9')
        for i in range(3):
            cx=w*(.66+i*.13)+math.sin(t*2+i)*4*sc
            yy=h*(.78+i*.025)
            d.arc((cx-32*sc,yy-5*sc,cx+32*sc,yy+7*sc),0,180,fill='#E8FCFF',width=max(2,int(2*sc)))
    if scene=='celebrate':
        for i in range(24):
            x=((.133*i+.04+math.sin(i*1.37)*.12)%1)*w
            y=((t*(.025+i%4*.006)+i*.15)%1)*h*.8
            col=['#FFB3C5','#FFE091','#A8D3FF','#BBA5FA'][i%4]
            r=3*sc+(i%2)*sc
            d.polygon([(x-r,y-r),(x+r,y-r*.5),(x,y+r)],fill=col)
    # Tiny foreground blossoms to keep layers alive
    for i in range(7):
        x=w*((i*.191+.08)%1); y=h*(.84+(i%2)*.046)
        stem=17*sc
        line(d,[(x,y),(x+math.sin(t*.8+i)*2*sc,y-stem)],'#56A66B',2*sc)
        ellipse(d,(x-4*sc,y-stem-4*sc,x+4*sc,y-stem+4*sc),'#FAF4FF')


def nori(d,w,h,t,local,scene):
    sc=w/360
    # Large, readable expressions and scene-dependent locomotion.
    if scene=='hello':
        x=lerp(-w*.16,w*.32,ease(local/2.6));jump=0
    elif scene=='look':
        x=w*(.28+.12*ease(local/5));jump=0
    elif scene=='flower':
        x=w*.26;jump=0
    elif scene=='celebrate':
        x=w*.34;jump=abs(math.sin(local*3.6))*19*sc
    else:
        x=w*.29;jump=abs(math.sin(t*1.8))*2*sc
    y=h*.63-jump+math.sin(t*3.1)*1.6*sc
    moving=(scene=='hello' and local<2.7) or (scene=='look' and local<5)
    walk=math.sin(t*9)*9*sc if moving else 0
    # Shadow, independently moving feet, antenna, arms.
    ellipse(d,(x-47*sc,h*.734,x+51*sc,h*.745),'#4B9B80')
    for s in (-1,1):
        xx=x+s*23*sc
        yy=y+72*sc+(walk if s>0 else -walk)
        rect(d,(xx-15*sc,yy,xx+16*sc,yy+11*sc),'#2D939A',5*sc)
    rect(d,(x-44*sc,y+11*sc,x+44*sc,y+71*sc),'#2D9DA9',19*sc)
    rect(d,(x-35*sc,y+27*sc,x+33*sc,y+56*sc),'#45B9B7',11*sc)
    # Waving hand: visual motion rather than only moving body.
    wave= (math.sin(local*9)*31 if scene in ('hello','celebrate') else 4*math.sin(t*2))
    ly=y+48*sc
    line(d,[(x-43*sc,y+27*sc),(x-69*sc,ly)],'#2498A1',12*sc)
    ellipse(d,(x-77*sc,ly-8*sc,x-60*sc,ly+9*sc),'#FFE0A8')
    rightx=x+68*sc
    righty=y+(12-wave)*sc
    line(d,[(x+43*sc,y+27*sc),(rightx,righty)],'#2498A1',12*sc)
    ellipse(d,(rightx-9*sc,righty-9*sc,rightx+9*sc,righty+9*sc),'#FFE0A8')
    # Head, ears, face. Eye gaze follows the action.
    tilt=math.sin(t*2.7)*1.4*sc
    rect(d,(x-55*sc,y-81*sc+tilt,x+55*sc,y+19*sc+tilt),'#F0FFF5',23*sc,'#297F91',max(2,int(3*sc)))
    rect(d,(x-47*sc,y-75*sc,x+47*sc,y+11*sc),'#E5FBF1',20*sc)
    line(d,[(x,y-81*sc),(x+math.sin(t*2)*2*sc,y-101*sc)],'#2E8B99',3*sc)
    ellipse(d,(x-6*sc,y-108*sc,x+6*sc,y-97*sc),'#FFC95E')
    look= (8 if scene in ('butterfly','flower') else -2 if scene=='look' else 0)*sc
    blinking=(t%4.1)<.13
    for side in (-1,1):
        ex=x+side*22*sc+look;ey=y-35*sc
        if blinking:line(d,[(ex-7*sc,ey),(ex+7*sc,ey)],'#1B546E',3*sc)
        else:
            ellipse(d,(ex-7*sc,ey-10*sc,ex+7*sc,ey+8*sc),'#214C63')
            ellipse(d,(ex-3*sc,ey-7*sc,ex+2*sc,ey-2*sc),'#F9FCF7')
    for side in (-1,1):
        ex=x+side*40*sc
        ellipse(d,(ex-10*sc,y-12*sc,ex+7*sc,y-3*sc),'#F5AEAD')
    if scene=='look':
        ellipse(d,(x-6*sc,y-14*sc,x+6*sc,y-1*sc),'#25596F')
    else:
        d.arc((int(x-17*sc),int(y-23*sc),int(x+17*sc),int(y-6*sc)),0,180,fill='#24586E',width=max(2,int(3*sc)))
    return x,y


def blink(d,w,h,t,local,scene,focus=None):
    sc=w/360
    if scene=='hello':x=lerp(w*1.18,w*.73,ease(local/2.5))
    elif scene=='look':x=w*(.60+.20*math.sin(t*.58))
    elif scene=='flower':x=w*(.71+.09*math.sin(local*.6))
    elif scene=='celebrate':x=w*(.62+.07*math.sin(local*2.6))
    else:x=w*(.70+.11*math.sin(local*.85))
    y=h*.43+math.sin(t*4.7)*17*sc
    # Outer glow / tiny light trail
    for i in range(3):
        r=(34+i*8)*sc
        ellipse(d,(x-r,y-r*.88,x+r,y+r*.88),None,outline=['#FFF9D3','#FFF1AF','#F5DF89'][i],width=max(1,int(sc)))
    wing=abs(math.sin(t*16))*16*sc
    ellipse(d,(x-40*sc,y-22*sc-wing,x-1*sc,y+13*sc),'#C7F4F0')
    ellipse(d,(x+1*sc,y-24*sc-wing,x+41*sc,y+13*sc),'#DCF9F0')
    ellipse(d,(x-19*sc,y-21*sc,x+19*sc,y+25*sc),'#FBE57D',outline='#DDAF60',width=max(1,int(2*sc)))
    for dx in (-7,8):
        ellipse(d,(x+(dx-3)*sc,y-4*sc,x+(dx+2)*sc,y+3*sc),'#36546A')
    d.arc((int(x-5*sc),int(y+3*sc),int(x+6*sc),int(y+13*sc)),0,180,fill='#36546A',width=max(1,int(2*sc)))
    return x,y

def butterfly(d,w,h,t,local,scene):
    sc=w/360
    if scene=='hello':return
    if scene=='butterfly':
        # The second encounter flies toward the blossom.
        x=lerp(w*.99,w*.48,ease(local/6)) if t<28 else lerp(w*.43,w*.78,ease(local/7))
    elif scene=='flower':x=w*.93
    else:x=w*(.5+.24*math.sin(t*.64))
    y=h*(.37+.045*math.sin(local*1.5))
    if scene=='look':y=h*.30+math.sin(t*2)*h*.04
    flap=.5+.5*math.sin(t*19)
    wide=24*sc*(.4+.6*flap)
    ellipse(d,(x-7*sc-wide,y-28*sc,x-5*sc,y+13*sc),'#78A9F8')
    ellipse(d,(x+5*sc,y-28*sc,x+7*sc+wide,y+13*sc),'#91BDFB')
    ellipse(d,(x-5*sc-wide*.8,y+3*sc,x-2*sc,y+22*sc),'#C0CEFC')
    ellipse(d,(x+2*sc,y+3*sc,x+5*sc+wide*.8,y+22*sc),'#C4D9FF')
    ellipse(d,(x-4*sc,y-18*sc,x+4*sc,y+27*sc),'#345E92')
    line(d,[(x-1*sc,y-16*sc),(x-9*sc,y-29*sc)],'#345E92',1.5*sc)
    line(d,[(x+1*sc,y-16*sc),(x+9*sc,y-29*sc)],'#345E92',1.5*sc)


def blossom(d,w,h,local,scene,t):
    sc=w/360
    # Only visible during the reveal and the flight home.
    if scene not in ('flower','butterfly','celebrate'):return
    # In early butterfly scene don't spoil the flower reveal.
    if scene=='butterfly' and t<28:return
    x=w*.80 if scene!='celebrate' else w*.8
    gy=h*.79
    reveal=ease(local/3) if scene=='flower' else 1.
    yh=lerp(7*sc,145*sc,reveal)
    line(d,[(x,gy),(x+math.sin(t*1.5)*5*sc,gy-yh)],'#419978',7*sc)
    ellipse(d,(x-55*sc,gy-yh*.46,x+2*sc,gy-yh*.23),'#77C77E')
    ellipse(d,(x+1*sc,gy-yh*.69,x+49*sc,gy-yh*.5),'#84CE83')
    yy=gy-yh;radius=25*sc*max(.15,reveal)
    for i in range(6):
        ang=math.tau*i/6+math.sin(t*.65)*.04
        cx=x+math.cos(ang)*radius
        cy=yy+math.sin(ang)*radius
        ellipse(d,(cx-20*sc*reveal,cy-20*sc*reveal,cx+20*sc*reveal,cy+20*sc*reveal),'#759EE9')
    ellipse(d,(x-15*sc*reveal,yy-15*sc*reveal,x+15*sc*reveal,yy+15*sc*reveal),'#FFE09A')


def speech(d,w,h,words,t,local,start=2.2,duration=2.1,anchor=.65):
    if local<start or local>start+duration:return
    sc=w/360
    appear=ease((local-start)/.18)
    x=w*anchor;y=h*.29-(1-appear)*20*sc
    f=font(19*sc)
    b=d.textbbox((0,0),words,font=f)
    width=(b[2]-b[0])+34*sc
    rect(d,(x-width/2,y-16*sc,x+width/2,y+24*sc),'#FFFFFF',14*sc,'#D3DFD7',max(1,int(sc)))
    d.polygon([(x-9*sc,y+23*sc),(x+4*sc,y+36*sc),(x+12*sc,y+23*sc)],fill='#FFFFFF')
    d.text((int(x-(b[2]-b[0])/2),int(y-10*sc)),words,font=f,fill='#335465')


def titles(d,w,h,scene,caption,local,t):
    sc=w/360
    if t<2.2:
        # Title is an intro, not a permanently pinned HUD.
        f=font(26*sc)
        label='NORI & BLINK'
        bb=d.textbbox((0,0),label,font=f)
        x=(w-(bb[2]-bb[0]))/2
        rect(d,(x-13*sc,25*sc,x+(bb[2]-bb[0])+13*sc,70*sc),'#FFF8E7',15*sc)
        d.text((int(x),int(35*sc)),label,font=f,fill='#247783')
    # Accessible subtitles: bottom third, with enough room for the action.
    y=h*.866
    rect(d,(w*.06,y,w*.94,y+58*sc),'#FFF9EB',19*sc,'#E7CEAD',max(1,int(2*sc)))
    fs=int(18*sc)
    while fs>=10 and d.textbbox((0,0),caption,font=font(fs))[2]>w*.77:fs-=1
    bb=d.textbbox((0,0),caption,font=font(fs))
    d.text((int((w-(bb[2]-bb[0]))/2),int(y+17*sc)),caption,font=font(fs),fill='#355B70')


def cartoon_frame(t,episode,secs=7.0,w=360,h=640):
    scene_idx=min(int(t//secs),len(episode['scenes'])-1)
    scene=episode['scenes'][scene_idx]
    local=t-scene_idx*secs
    kind=scene['kind']
    # For the second butterfly scene, the artwork shows the butterfly reaching the flower.
    img=sky(w,h).copy();scenery(img,kind,t,local,w,h)
    d=ImageDraw.Draw(img)
    if kind=='flower':
        blossom(d,w,h,local,kind,t)
    elif kind in ('butterfly','celebrate'):blossom(d,w,h,local,kind,t)
    nori(d,w,h,t,local,kind)
    blink(d,w,h,t,local,kind)
    butterfly(d,w,h,t,local,kind)
    if kind=='hello':speech(d,w,h,'Hello!',t,local,start=3.3,anchor=.66)
    elif kind=='butterfly' and scene_idx<3:speech(d,w,h,'Can we help?',t,local,start=2.5,anchor=.55)
    elif kind=='look':speech(d,w,h,'Not here!',t,local,start=4.,anchor=.54)
    elif kind=='flower':speech(d,w,h,'There it is!',t,local,start=3.,anchor=.56)
    elif kind=='celebrate':speech(d,w,h,'Hooray!',t,local,start=2.8,anchor=.59)
    titles(d,w,h,kind,scene['caption'],local,t)
    return img


def render(episode_path:Path,out_path:Path,voice_path:Path|None=None,*,width:int=720,height:int=1280,fps:int=20,scene_seconds:float=7):
    episode=json.loads(Path(episode_path).read_text(encoding='utf-8'));validate_episode(episode)
    if not shutil.which('ffmpeg'):raise RuntimeError('FFmpeg not in PATH')
    duration=len(episode['scenes'])*scene_seconds
    out_path=Path(out_path);out_path.parent.mkdir(parents=True,exist_ok=True)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{width}x{height}','-framerate',str(fps),'-i','pipe:0']
    if voice_path:
        voice_path=Path(voice_path)
        if not voice_path.is_file():raise FileNotFoundError(voice_path)
        cmd+=['-i',str(voice_path),'-map','0:v:0','-map','1:a:0','-af','apad','-c:a','aac','-b:a','160k']
    cmd+=['-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(out_path)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for k in range(int(duration*fps)):
            im=cartoon_frame(k/fps,episode,scene_seconds,width,height)
            p.stdin.write(im.tobytes())
        p.stdin.close();err=p.stderr.read().decode('utf-8','replace')
        if p.wait():raise RuntimeError('FFmpeg failed: '+err)
        p.stderr.close()
    except BaseException:
        if p.stdin and not p.stdin.closed:p.stdin.close()
        p.kill();p.wait();raise
    return out_path
