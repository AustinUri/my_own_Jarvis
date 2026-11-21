"""JARVIS Nori & Blink Creative Factory v0.4.

A repeatable local-only story, storyboard and MP4 draft generator.
No uploads, no OAuth, no paid APIs, no changes to JARVIS's existing queue.
Installed as core.capabilities.youtube_autopilot.creative_factory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import shutil
import socket
from urllib.parse import urlsplit
import subprocess
import sys
import tempfile
import urllib.request
from difflib import SequenceMatcher
import time
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .manager import setup, root_dir, config, dump, read
from .episodes import validate_episode
from .quality import inspect_story, inspect_render
from .voice import piper_narrate
from .renderer import cartoon_frame

# The fallback is finite and honest: if no local AI is available, it chooses
# genuinely different story arcs, and stops rather than disguising duplicates.
# Each entry is a distinct six-beat plot with child-friendly original narration.
STORIES = [
    ("The Wobbly Leaf Boat", "A leaf boat travels down a small stream.", [
        ("hello", "A floating idea", "Nori finds a big leaf by the stream. Could it become a little boat?"),
        ("look", "Let's make a boat", "Blink watches as Nori folds the leaf gently. The boat is ready to sail."),
        ("rain", "Off it goes!", "A soft breeze pushes the boat. It wobbles across the sparkling water."),
        ("look", "Oh no, a rock!", "The little boat bumps a pebble and stops. How can they help it?"),
        ("flower", "A clever idea", "Blink blows carefully beside the boat. It floats around the pebble at last!"),
        ("celebrate", "Happy sailing", "Hooray! Their leaf boat sails on. Even tiny ideas can become adventures.")]),
    ("A Sleepy Little Snail", "Two friends find a quiet home for a sleepy snail.", [
        ("hello", "A tiny visitor", "A little snail is resting in the middle of the busy garden path."),
        ("look", "Too much noise", "Nori hears footsteps nearby. The snail needs somewhere peaceful to have a nap."),
        ("flower", "Find a safe spot", "Blink spots a shady flower with soft leaves. That looks like a cozy place!"),
        ("plant", "Slow and gentle", "Nori moves a fallen twig away and gives the snail a clear, safe path."),
        ("look", "One little step", "The snail glides slowly into the shade. Its tiny feelers wave happily."),
        ("celebrate", "Sweet dreams", "They whisper goodbye so the snail can rest. Being kind can be quiet.")]),
    ("The Missing Red Apple", "Nori and Blink solve a playful garden mystery.", [
        ("hello", "Where is the apple?", "Nori brought a red apple for a picnic. But the apple has disappeared!"),
        ("look", "Follow those clues", "They find a shiny red dot beside the tree. Is that their apple?"),
        ("butterfly", "Just a ladybug", "No, it is a tiny ladybug! It waves as the friends walk past."),
        ("look", "Listen carefully", "Something rolls softly behind the hill. Nori and Blink follow the funny sound."),
        ("flower", "Found it!", "There is the apple, resting beside a flower. The gentle breeze rolled it away."),
        ("celebrate", "Picnic time", "Nori laughs and shares a lovely picnic with Blink. Mystery solved together!")]),
    ("The Kite That Wouldn't Fly", "A gentle story about patience and the wind.", [
        ("hello", "A colorful kite", "Nori has made a kite with bright blue paper. It looks wonderful!"),
        ("look", "Up, up, up", "Nori runs with the kite, but it droops down into the soft grass."),
        ("rain", "Wait for the breeze", "Blink notices the leaves are still. Maybe the wind is taking a little break."),
        ("look", "Here comes the wind", "The tree branches sway and the grass dances. The breeze has finally arrived!"),
        ("butterfly", "Flying at last", "Nori lifts the kite carefully. The colorful tail swishes across the sky."),
        ("celebrate", "Patience can help", "Sometimes waiting is the cleverest thing to do. Their kite flies high!")]),
    ("A Bubble for Everyone", "An original story about sharing little joys.", [
        ("hello", "Bubbles everywhere", "Blink finds a bowl of bubbles. Tiny shiny circles float into the sunny sky."),
        ("look", "Just one more", "Nori catches one bubble, then another. Blink wants to join the fun too."),
        ("rainbow", "So many colors", "The bubbles shine pink and green and blue. They sparkle like little rainbows."),
        ("look", "A thoughtful pause", "Nori notices Blink waiting nearby. Games are more fun when friends play together."),
        ("flower", "Let's take turns", "First Blink blows a bubble. Then Nori blows one. Pop, pop, pop!"),
        ("celebrate", "Double the giggles", "They laugh as the bubbles drift away. Sharing can make a small joy bigger.")]),
    ("The Night Lantern", "A cozy evening adventure with a gentle firefly.", [
        ("hello", "The sun says goodbye", "The garden grows quiet as the sky turns purple. Nori hears a tiny rustle."),
        ("look", "Who's hiding there?", "A little moth has lost the path to its favorite evening flower."),
        ("rainbow", "Blink has an idea", "Blink glows a little brighter. Its soft golden light makes the pathway easy to see."),
        ("look", "This way, little moth", "Nori walks slowly while Blink lights the way. They pass a sleepy tree."),
        ("flower", "Home at last", "The moth finds its gentle purple flower and settles down for the night."),
        ("goodbye", "Good night, garden", "Nori whispers good night. Blink twinkles once more, like a tiny friendly lantern.")]),
    ("The Three Pebble Parade", "Two friends make a little pattern from pebbles.", [
        ("hello", "One little pebble", "Nori finds a smooth pebble that looks like a tiny moon on the path."),
        ("look", "Let's count together", "Blink finds two more. One, two, three little pebbles in a row!"),
        ("plant", "Make a pattern", "Nori puts a round pebble beside a long one. What shape should come next?"),
        ("look", "Oops, it rolled!", "One pebble rolls downhill. Blink follows it with a soft golden glow."),
        ("flower", "Back in its place", "Nori gently brings it back. Now the pattern is complete and beautiful."),
        ("celebrate", "Our pebble parade", "Round, long, round! They made a tiny parade by working together.")]),
    ("The Little Cloud's Shadow", "Nori and Blink discover how shadows move.", [
        ("hello", "Hello, little shadow", "Nori sees a funny shape on the grass. It looks just like a cloud!"),
        ("look", "Where did it go?", "The dark shape slides across the path. Nori tries to follow it."),
        ("rain", "Look up high", "Blink points toward a fluffy cloud traveling slowly through the bright blue sky."),
        ("look", "Shadow chase", "They take a few steps as the shadow moves. It seems to be playing chase!"),
        ("rainbow", "Sunshine peeks through", "The cloud moves away and the sunshine returns. The funny shadow disappears."),
        ("celebrate", "A sunny discovery", "Nori smiles. Clouds can make shadows, and the wind can move them.")]),
    ("A Tiny Acorn Surprise", "An acorn starts a big new idea.", [
        ("hello", "Something fell", "Plop! A tiny acorn lands beside Nori's feet under the tall tree."),
        ("look", "What is this?", "Blink circles the little acorn. It has a funny cap and a smooth brown shell."),
        ("plant", "A place to grow", "Nori chooses soft soil and makes a tiny hole. They plant the acorn carefully."),
        ("rain", "A gentle drink", "Blink finds a watering can. Drip, drop! The soil gets a little drink."),
        ("sprout", "Imagine the future", "One day the acorn might grow into a big tree with lovely green leaves."),
        ("celebrate", "Small beginnings", "Nori and Blink smile at their little planting spot. Big things can start small.")]),
    ("The Friendly Blue Balloon", "A balloon needs help finding its way out of a tree.", [
        ("hello", "Up in the branches", "A blue balloon wiggles among the leaves. It cannot float past the tree."),
        ("look", "A little too high", "Nori looks up and scratches its head. The branches are much too tall."),
        ("butterfly", "Ask a tiny friend", "Blink flies around the tree and sees the string caught on a soft twig."),
        ("look", "Easy does it", "A breeze gently lifts the balloon, and the loose string slips off the twig."),
        ("rainbow", "Free to float", "The balloon bobs slowly above the garden, drifting past the fluffy clouds."),
        ("celebrate", "Wave goodbye", "Nori and Blink wave to the balloon. They are glad the balloon is free.")]),
    ("The Pond's Tiny Ripples", "Friends discover patterns in a pond.", [
        ("hello", "Still as a mirror", "The pond is shiny and quiet. Nori can see the clouds reflected in it."),
        ("look", "A gentle plop", "A little leaf falls onto the water. Plop! Tiny circles appear all around."),
        ("rain", "Round and round", "The rings grow bigger and bigger. Blink watches them spread across the pond."),
        ("butterfly", "A dancing dragonfly", "A colorful dragonfly hovers above the ripples. Its wings move very fast."),
        ("flower", "The pond grows still", "Soon the circles disappear. The pond looks like a shiny mirror again."),
        ("celebrate", "Nature's little patterns", "Nori and Blink love the pond's gentle secrets. Every day brings a discovery.")]),
    ("Who Painted the Rainbow?", "A playful weather mystery with a happy answer.", [
        ("hello", "A rainy morning", "Nori hears the last drops falling from the leaves. The rain is almost over."),
        ("look", "A stripe of red", "Blink spots something colorful above the hill. It has a bright red stripe."),
        ("rainbow", "Colors in the sky", "Orange, yellow, green, blue! More colors spread in a great big arch."),
        ("look", "A rainbow mystery", "Nori wonders who painted those colors. Blink notices sunshine behind the rain."),
        ("flower", "Rain and sunshine", "Together they watch the rainbow shine. The sunny rain made this wonderful sight!"),
        ("celebrate", "Colors for everyone", "The garden sparkles in the light. Nori and Blink enjoy the colorful sky.")]),
]

PROPS = ('leaf','snail','apple','kite','bubble','moon','pebble','cloud','acorn','balloon','ripple','rainbow')
SETTINGS = ('woodland','stream','meadow','orchard','pond','sunset','flower-field','hill')
ACTIONS = ('enter','search','point','hop','follow','discover','carry','watch','cheer','wave')
SHOTS = ('wide','medium','close','tracking')

# Map themes to consistent visual objects and settings so the story, not a dice
# roll, decides what appears in each shot. The camera and movement still vary.
THEMES = [
    ('leaf',('stream','meadow','stream','stream','stream','stream')),
    ('snail',('garden','woodland','flower-field','woodland','flower-field','flower-field')),
    ('apple',('orchard','orchard','meadow','hill','orchard','orchard')),
    ('kite',('meadow','hill','meadow','hill','hill','hill')),
    ('bubble',('flower-field','meadow','meadow','meadow','flower-field','flower-field')),
    ('moon',('sunset','sunset','sunset','woodland','flower-field','sunset')),
    ('pebble',('meadow','meadow','meadow','hill','flower-field','meadow')),
    ('cloud',('hill','meadow','hill','hill','hill','meadow')),
    ('acorn',('woodland','woodland','woodland','woodland','flower-field','woodland')),
    ('balloon',('woodland','woodland','woodland','meadow','hill','meadow')),
    ('ripple',('pond','pond','pond','pond','pond','pond')),
    ('rainbow',('meadow','hill','hill','hill','flower-field','flower-field')),
]


def _normalized(s):
    return re.sub(r'[^a-z0-9 ]+', ' ', s.lower()).strip()


def _signature(ep):
    return hashlib.sha256('|'.join(_normalized(s['narration']) for s in ep['scenes']).encode('utf8')).hexdigest()


def _existing(root):
    found=[]
    for directory in (root/'stories',root/'creative_drafts'):
        for path in directory.glob('*.json') if directory.is_dir() else []:
            try:
                e=json.loads(path.read_text(encoding='utf8'))
                if isinstance(e,dict) and isinstance(e.get('scenes'),list):found.append(e)
            except (ValueError, OSError):continue
    return found


def _decorate(ep, rng, theme=0):
    ep=json.loads(json.dumps(ep))
    prop,locations=THEMES[theme%len(THEMES)]
    order=[0,2,1,3,0,2]
    shots=['wide','medium','close','tracking']
    shot_shift=rng.randrange(4)
    for i,sc in enumerate(ep['scenes']):
        sc['setting']=locations[i]
        sc['prop']=prop
        sc['shot']=shots[(order[i]+shot_shift)%4]
        sc['action']=['enter','search','point','follow','discover','cheer'][i]
        sc['motion_variant']=rng.randrange(1,100000)
        sc['camera_speed']=round(rng.uniform(.5,1.4),2)
    return ep


def offline_story(root,existing, rng):
    used_titles={_normalized(e.get('title','')) for e in existing}
    candidates=[(i,story) for i,story in enumerate(STORIES) if _normalized('Nori & Blink: '+story[0]) not in used_titles]
    if not candidates:
        raise RuntimeError('Offline story library exhausted. Enable LM Studio for genuinely new scripts; refusing to recycle plots.')
    idx,(title,description,beats)=rng.choice(candidates)
    ep={'id':'nori-'+rng.randbytes(6).hex(), 'title':'Nori & Blink: '+title,
        'description':description+' Original English preschool animation.',
        'scenes':[{'kind':k,'caption':cap,'narration':narr} for k,cap,narr in beats],
        'creative':{'backend':'offline_curated','plot_id':idx,'version':4}}
    return _decorate(ep,rng,idx)


AI_INSPIRATIONS = (
    'a funny echo among the hills', 'a squirrel searching for a tiny lost mitten',
    'finding the softest place for a feather', 'a little frog learning to hop',
    'the garden with too many umbrellas', 'a wonderful day of unusual shapes',
    'the day the wind played hide and seek', 'a tiny lantern and a shy moth',
    'a little bridge made with care', 'making a path for a lost ladybug',
    'a friendly bird building a nest', 'a dandelion seed taking its first flight',
    'the sleepy sunflower at dawn', 'a surprise in a puddle after the rain',
    'a game of three different sounds', 'helping a beetle across a small stream',
    'a rolling pine cone with a big adventure', 'a little snowflake in spring',
    "the garden's quietest musical instrument", 'a kite that dances with the breeze',
    'an acorn with a big dream', 'a butterfly choosing a colorful flower',
    'a shy snail learning to say hello', 'a cloud shadow that loves to move',
)

def _json_from_reply(text):
    text=re.sub(r'<think>.*?</think>','',text,flags=re.S|re.I).strip()
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
    left=text.find('{');right=text.rfind('}')
    if left<0 or right<=left:raise ValueError('Model did not return JSON object')
    return json.loads(text[left:right+1])


def ai_story(root,existing,rng):
    c=config(root)
    if not _local_model_reachable(c):raise RuntimeError('LM Studio local endpoint is unavailable')
    recent=[e.get('title','') for e in existing][-40:]
    inspiration=rng.choice(AI_INSPIRATIONS)
    kinds='hello, look, plant, rain, sprout, celebrate, butterfly, flower, rainbow, goodbye'
    prompt=(
        'Create ONE genuinely new ORIGINAL English preschool story for ages 3–6 featuring Nori, '
        'a friendly little garden robot, and Blink, a tiny glowing firefly. '
        f'The story inspiration is: {inspiration}. Do not recycle plots or repeat the example stories. '
        'Use a clear beginning, amusing harmless complication, visible character actions, clever resolution, warm ending. '
        f'Avoid the titles of all earlier episodes: {json.dumps(recent,ensure_ascii=False)}. '
        'No famous TV show imitation, commercial messages, dangerous behavior, or copyrighted characters. '
        'Return ONLY valid JSON: {"title":..., "description":..., "scenes":[...]} with exactly 6 scenes. '
        'Each scene MUST contain "kind", "caption", "narration", "setting", "action", "shot", "prop". '
        f'Allowed kind: {kinds}. Allowed setting: garden, woodland, stream, meadow, orchard, pond, '
        'sunset, flower-field, hill. Allowed action: enter, search, point, hop, follow, discover, '
        'carry, watch, cheer, wave. Allowed shot: wide, medium, close, tracking. '
        f'Allowed prop: {", ".join(PROPS)}. Choose a prop appropriate to the story. '
        'Captions: 2–5 simple English words; narration: 8–16 easy spoken English words per scene, '
        'with lively dialogue and at least three distinct actions. 6 coherent beats, not six repeated descriptions.'
    )
    body={'model':c['lmstudio_model'],
          'messages':[{'role':'system','content':'You are a careful original preschool scriptwriter and storyboard director. Return JSON only.'},
                      {'role':'user','content':prompt}],
          'temperature':.95,'max_tokens':2300,'stream':False,
          'response_format':{'type':'json_object'}}
    last=None
    for attempt in range(2):
        try:
            req=urllib.request.Request(c['lmstudio_url'],data=json.dumps(body).encode('utf-8'),
                                       headers={'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(req,timeout=100) as response:reply=json.load(response)
            except Exception as ex:
                # Retry without optional JSON mode if a local backend rejects it.
                if attempt==0:
                    body.pop('response_format',None);last=ex;continue
                raise
            ep=_json_from_reply(reply['choices'][0]['message']['content'])
            ep['id']='nori-'+rng.randbytes(6).hex()
            ep.setdefault('title','')
            if not ep['title'].startswith('Nori & Blink: '):ep['title']='Nori & Blink: '+ep['title']
            validate_episode(ep)
            a=' '.join(x['narration'] for x in ep['scenes']).lower()
            for old in existing:
                b=' '.join(x.get('narration','') for x in old.get('scenes',[])).lower()
                if (_normalized(ep['title'])==_normalized(old.get('title','')) or
                    SequenceMatcher(None,a,b).ratio()>.58):
                    raise ValueError('Too similar to an earlier episode')
            ep.setdefault('creative',{})
            ep['creative'].update({'backend':'lmstudio_qwen','version':4,'inspiration':inspiration})
            # Keep valid AI storyboards; replace unsupported labels with safe,
            # character-coherent drawing actions from the procedural layer.
            prop=next((p for p in PROPS if p in a),rng.choice(PROPS))
            idx=PROPS.index(prop)
            for sc in ep['scenes']:
                for field in ('setting','action','shot','prop'):
                    sc['_ai_'+field]=sc.get(field)
            ep=_decorate(ep,rng,idx)
            for i,sc in enumerate(ep['scenes']):
                for field,allowed in [('setting',(*SETTINGS,'garden')),('action',ACTIONS),('shot',SHOTS),('prop',PROPS)]:
                    candidate=sc.get('_ai_'+field)
                    if candidate in allowed:sc[field]=candidate
                    sc.pop('_ai_'+field,None)
            return ep
        except Exception as exc:
            last=exc
            body.pop('response_format',None)
    raise RuntimeError(f'Qwen produced no valid original story: {last}')

def _local_model_reachable(c):
    """Only probe loopback. Never silently invoke a paid/external endpoint."""
    parsed=urlsplit(c.get('lmstudio_url',''))
    if parsed.hostname not in ('127.0.0.1','localhost','::1'):return False
    try:
        with socket.create_connection((parsed.hostname,parsed.port or 80),timeout=.35):
            return True
    except OSError:
        return False


def create_story(root,backend='auto',seed=None):
    rng=random.Random(seed) if seed is not None else random.SystemRandom()
    previous=_existing(root)
    if backend not in ('auto','offline','local-ai'):raise ValueError('Invalid backend')
    use_ai=(backend=='local-ai') or (backend=='auto' and (config(root).get('lmstudio_enabled',False) or _local_model_reachable(config(root))))
    last_err=None
    ep=None
    if use_ai:
        try:ep=ai_story(root,previous,rng)
        except Exception as exc:
            last_err=str(exc)
            if backend=='local-ai':raise RuntimeError('Local AI story generation failed: '+last_err) from exc
    if ep is None:
        ep=offline_story(root,previous,rng)
        if last_err:ep['creative']['ai_fallback_reason']=last_err[:200]
    inspect_story(ep)
    sig=_signature(ep)
    if any(_signature(old)==sig for old in previous):raise RuntimeError('Duplicate episode text rejected')
    if any(_normalized(e.get('title',''))==_normalized(ep['title']) for e in previous):
        raise RuntimeError('Duplicate episode title rejected')
    ep['creative']['signature']=sig
    ep['creative']['created_at']=datetime.now(timezone.utc).isoformat()
    ep['creative']['manual_approval_required']=True
    out=root/'creative_drafts'/(ep['id']+'.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf8') as f:json.dump(ep,f,ensure_ascii=False,indent=2)
    return ep,out


def _font(sz):
    paths=['C:/Windows/Fonts/arialbd.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
    for path in paths:
        if Path(path).exists():return ImageFont.truetype(path,max(10,int(sz)))
    return ImageFont.load_default()


def _prop(draw,scene,t,w,h):
    """Animated story-specific visual props (not repeated random decorations)."""
    key=scene.get('prop','leaf'); scale=w/360
    local=scene.get('_local',0)
    duration=max(.01,scene.get('_scene_duration',7.0))
    beat=min(1.0,local/duration)
    ease_in=beat*beat*(3-2*beat)
    action=scene.get('action','watch')
    x=w*(.60 + .08*math.sin(t*.5+scene.get('motion_variant',0)%17))
    y=h*(.72 - .02*math.sin(t*2.2))
    if action=='enter':x=w*(1.07-.45*ease_in)
    elif action=='follow':x=w*(.27+.55*ease_in)
    elif action=='carry':x=w*(.47+.06*math.sin(beat*math.tau))
    elif action=='hop':y-=abs(math.sin(local*3))*h*.085
    elif action=='search':x=w*(.43+.18*math.sin(local*.9))
    elif action=='discover':
        x=w*(.61+.06*ease_in);y-=h*.06*ease_in
    elif action=='cheer':y-=abs(math.sin(local*4))*h*.045
    elif action=='wave':x+=w*.08*math.sin(local*2)
    color={'leaf':'#3CBA74','snail':'#B27AD8','apple':'#F36A69','kite':'#FF9C5A','bubble':'#A1E3FB',
           'moon':'#F8D87B','pebble':'#9DB6BA','cloud':'#FFFFFF','acorn':'#A97147','balloon':'#7BB6FF',
           'ripple':'#81D6F4','rainbow':'#F5AB72'}.get(key,'#E5A5B0')
    r=23*scale
    def el(a,b,c,d,fill):draw.ellipse((x+a*scale,y+b*scale,x+c*scale,y+d*scale),fill=fill)
    if key=='snail':
        el(-28,-13,26,20,'#C6A0D7');el(-26,-36,9,6,color)
        draw.arc((x-15*scale,y-26*scale,x+2*scale,y-10*scale),0,320,fill='#73518C',width=max(1,int(3*scale)))
        for dx in (14,22):draw.line([(x+dx*scale,y-10*scale),(x+dx*scale,y-26*scale)],fill='#7C5B9B',width=max(1,int(2*scale)))
    elif key=='kite':
        y-=h*.20+math.sin(t*3)*9*scale
        draw.polygon([(x,y-45*scale),(x+33*scale,y),(x,y+45*scale),(x-33*scale,y)],fill=color)
        draw.line([(x,y+45*scale),(x-17*scale,y+80*scale),(x+4*scale,y+108*scale)],fill='#FFFFFF',width=max(2,int(scale*3)))
    elif key in ('bubble','balloon'):
        y-=h*.19+math.sin(t*.8)*15*scale
        draw.ellipse((x-r,y-r,x+r,y+r),fill=color,outline='#FFFFFF',width=max(2,int(2*scale)))
        el(-13,-14,-5,-6,'#FFFFFF')
        if key=='balloon':draw.line([(x,y+r),(x-11*scale,y+r+55*scale)],fill='#E3F0FD',width=max(1,int(scale*2)))
    elif key=='apple':
        el(-20,-25,20,20,color)
        draw.line([(x,y-22*scale),(x+5*scale,y-36*scale)],fill='#674A2D',width=max(2,int(scale*3)))
        el(5,-36,19,-25,'#75BB78')
    elif key=='leaf':
        draw.polygon([(x-35*scale,y),(x,y-17*scale),(x+34*scale,y),(x,y+14*scale)],fill=color)
        draw.line([(x-30*scale,y),(x+31*scale,y)],fill='#318B59',width=max(1,int(2*scale)))
    elif key=='pebble':
        for i in range(3):el(-25+i*25,-12+(i%2)*8,0+i*25,9+(i%2)*8,color)
    elif key=='acorn':
        el(-15,-12,15,26,color);draw.pieslice((x-20*scale,y-25*scale,x+20*scale,y+3*scale),180,360,fill='#694A3B')
    elif key=='moon':
        y-=h*.27
        draw.ellipse((x-r*1.5,y-r*1.5,x+r*1.5,y+r*1.5),fill=color)
        draw.ellipse((x-r*.5,y-r*1.6,x+r*1.8,y+r*.5),fill='#B4A7D1')
    elif key=='cloud':
        y-=h*.27
        for dx,dy,rr in [(-20,3,25),(10,-7,30),(36,3,22)]:
            draw.ellipse((x+(dx-rr)*scale,y+(dy-rr)*scale,x+(dx+rr)*scale,y+(dy+rr)*scale),fill=color)
    elif key=='ripple':
        y=h*.79
        for i in range(3):
            rr=(20+i*20+abs(math.sin(t*1.2))*15)*scale
            draw.arc((x-rr,y-rr*.3,x+rr,y+rr*.3),0,180,fill=color,width=max(2,int(scale*3)))
    elif key=='rainbow':
        y=h*.44
        for i,c in enumerate(['#F06E78','#F3B261','#F7E27B','#82CA9E','#78BCE6']):
            rr=(60-i*8)*scale
            draw.arc((x-rr,y-rr,x+rr,y+rr),180,360,fill=c,width=max(2,int(scale*6)))


def _ambient(img,scene,t):
    setting=scene.get('setting','garden');w,h=img.size
    d=ImageDraw.Draw(img,'RGBA')
    if setting in ('pond','stream'):
        d.ellipse((w*.34,h*.69,w*.99,h*.84),fill=(91,196,220,142))
        for i in range(3):
            x=w*(.47+.16*i)+math.sin(t+i)*w*.012
            d.arc((x-w*.09,h*.76,x+w*.09,h*.79),0,170,fill=(248,253,252,220),width=max(2,w//160))
    elif setting in ('sunset','woodland'):
        tint=Image.new('RGBA',(w,h),(128,82,181,28 if setting=='sunset' else 13))
        img.paste(tint,(0,0),tint)
        d=ImageDraw.Draw(img,'RGBA')
        for i in range(6):
            x=w*(i+.5)/6;y=h*(.24+.02*math.sin(t+i))
            d.ellipse((x-2,y-2,x+2,y+2),fill=(255,243,162,130))
    elif setting in ('orchard','flower-field'):
        for i in range(7):
            x=w*(i+.5)/7;y=h*.77
            for k in range(5):
                a=k*math.tau/5
                xx=x+math.cos(a)*w*.016;yy=y+math.sin(a)*w*.016
                d.ellipse((xx-4,yy-4,xx+4,yy+4),fill=(252,154,185,210))
    elif setting=='hill':
        d.polygon([(0,h*.72),(w*.25,h*.65),(w*.55,h*.72),(w,h*.61),(w,h*.77)],fill=(168,216,165,90))


def _camera(img,scene,local,seconds):
    shot=scene.get('shot','wide')
    w,h=img.size
    if shot=='wide':return img
    frac=min(1,local/max(.01,seconds));phase=.5-.5*math.cos(math.pi*frac)
    zoom={'medium':1.08,'tracking':1.11,'close':1.19}[shot]
    cw=int(w/zoom);ch=int(h/zoom)
    xcenter=w*(.49 + (.055*math.sin(phase*math.pi*1.2) if shot=='tracking' else .025*(phase-.5)))
    ycenter=h*(.49+.015*math.sin(phase*math.pi))
    left=max(0,min(w-cw,int(xcenter-cw/2)));top=max(0,min(h-ch,int(ycenter-ch/2)))
    return img.crop((left,top,left+cw,top+ch)).resize((w,h),Image.Resampling.BICUBIC)


def _caption(img,caption):
    d=ImageDraw.Draw(img);w,h=img.size;sc=w/360
    y=h*.86
    d.rounded_rectangle((w*.035,y,w*.965,y+62*sc),radius=18*sc,fill='#FFF9ED',outline='#DDBB98',width=max(1,int(2*sc)))
    size=max(12,int(19*sc));max_width=w*.85
    while size>10 and d.textbbox((0,0),caption,font=_font(size))[2]>max_width:size-=1
    font=_font(size)
    bb=d.textbbox((0,0),caption,font=font)
    d.text(((w-(bb[2]-bb[0]))/2,y+17*sc),caption,font=font,fill='#345768')


def frame(t,episode,secs=7.0,w=360,h=640):
    idx=min(len(episode['scenes'])-1,int(t//secs));scene=episode['scenes'][idx]
    local=max(0,t-idx*secs)
    # Continue to reuse the installed JARVIS character art so upgrades to
    # Nori/Blink propagate automatically, while storyboards add shot variety.
    img=cartoon_frame(t,episode,secs=secs,w=w,h=h).convert('RGB')
    _ambient(img,scene,t)
    d=ImageDraw.Draw(img)
    scene_local=dict(scene, _local=local, _scene_duration=secs)
    _prop(d,scene_local,t,w,h)
    img=_camera(img,scene,local,secs)
    _caption(img,scene['caption'])
    return img


def render_draft(episode,root, *,width=360,height=640,fps=10,scene_seconds=7.0):
    conf=config(root)
    uid=episode['id'];drafts=root/'creative_drafts';renders=drafts/'renders';renders.mkdir(parents=True,exist_ok=True)
    output=renders/f'{uid}.mp4';wave=renders/f'{uid}.wav'
    model=conf.get('piper_model','');piper=conf.get('piper_bin','piper')
    if not model or not Path(model).is_file() or not shutil.which(piper):
        raise RuntimeError('Piper voice is not configured. Draft JSON saved, but no video was rendered.')
    piper_narrate(episode,wave,model=model,piper_bin=piper,scene_seconds=scene_seconds)
    duration=scene_seconds*len(episode['scenes'])
    temp=output.with_name(output.stem+'.rendering.mp4')
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24',
         '-video_size',f'{width}x{height}','-framerate',str(fps),'-i','pipe:0',
         '-i',str(wave),'-map','0:v:0','-map','1:a:0','-af','apad','-c:a','aac','-b:a','128k',
         '-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',
         '-movflags','+faststart',str(temp)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for j in range(round(duration*fps)):
            p.stdin.write(frame(j/fps,episode,secs=scene_seconds,w=width,h=height).tobytes())
        p.stdin.close();err=p.stderr.read().decode('utf-8','replace')
        if p.wait():raise RuntimeError('Video render failed: '+err[-1000:])
        temp.replace(output)
    except BaseException:
        if p.stdin and not p.stdin.closed:p.stdin.close()
        p.kill();p.wait();temp.unlink(missing_ok=True);raise
    finally:
        if p.stderr:p.stderr.close()
    # Mechanical checks cannot guarantee artistic quality.
    review={'video':str(output),'audio':str(wave),'automatic_upload_allowed':False,
            'human_review_required':True,'story_id':uid}
    try:review['mechanical_qa']=inspect_render(output,min_seconds=20)
    except Exception as exc:review['mechanical_qa_error']=str(exc)
    dump(renders/f'{uid}.review.json',review)
    return review


def main(argv=None):
    ap=argparse.ArgumentParser(description='JARVIS varied English kids video creator — drafts only')
    ap.add_argument('command',choices=['create','status','worker'])
    ap.add_argument('--root',type=Path,default=None)
    ap.add_argument('--count',type=int,default=1)
    ap.add_argument('--backend',choices=['auto','offline','local-ai'],default='auto')
    ap.add_argument('--render',action='store_true',help='Render new English-narrated MP4 previews; never upload')
    ap.add_argument('--width',type=int,default=720)
    ap.add_argument('--height',type=int,default=1280)
    ap.add_argument('--fps',type=int,default=20)
    ap.add_argument('--seconds',type=float,default=7.0)
    ap.add_argument('--interval-hours',type=float,default=24.0,help='Worker generation interval; no publication')
    ap.add_argument('--max-cycles',type=int,default=0,help='0 means run until interrupted')
    args=ap.parse_args(argv)
    root=setup(args.root or root_dir())
    if args.command=='status':
        paths=sorted((root/'creative_drafts').glob('*.json')) if (root/'creative_drafts').exists() else []
        print(json.dumps({'drafts':len(paths),'latest':[p.stem for p in paths[-5:]],'autopublish_enabled':config(root).get('autopublish_enabled'),
                          'message':'Creative drafts are separate from the publication queue.'},indent=2));return
    if args.command=='worker':
        if not args.render:ap.error('worker requires --render to prevent accumulating empty story drafts')
        if args.interval_hours<1:ap.error('worker interval must be >=1 hour')
        cycles=0
        print('Creative worker started: LOCAL DRAFTS ONLY; NO uploads or YouTube scheduling.',flush=True)
        while True:
            cycles+=1
            try:
                create_args=['create','--count',str(args.count),'--backend',args.backend,'--render',
                             '--width',str(args.width),'--height',str(args.height),'--fps',str(args.fps),
                             '--seconds',str(args.seconds),'--root',str(root)]
                main(create_args)
            except Exception as exc:
                print(json.dumps({'cycle_error':str(exc),'upload':False}),flush=True)
            if args.max_cycles and cycles>=args.max_cycles:return
            time.sleep(args.interval_hours*3600)
    if not 1<=args.count<=5:ap.error('count must be between 1 and 5 per run')
    if args.width<240 or args.height<400 or args.fps<4 or args.fps>30:ap.error('Invalid preview size or FPS')
    results=[]
    for _ in range(args.count):
        ep,path=create_story(root,backend=args.backend)
        result={'id':ep['id'],'title':ep['title'],'backend':ep['creative']['backend'],
                'story_path':str(path),'storyboard':[{'setting':s['setting'],'action':s['action'],'shot':s['shot'],'prop':s['prop']} for s in ep['scenes']],
                'state':'draft_waiting_for_render','upload':False}
        if args.render:
            try:
                rendered=render_draft(ep,root,width=args.width,height=args.height,fps=args.fps,scene_seconds=args.seconds)
                result.update({'state':'rendered_for_review','video_path':rendered['video'],
                               'qa':rendered.get('mechanical_qa'), 'qa_error':rendered.get('mechanical_qa_error')})
            except Exception as exc:
                result.update({'state':'render_failed','error':str(exc)})
        results.append(result)
    print(json.dumps({'created':len(results),'drafts':results,'autopublish_enabled':config(root).get('autopublish_enabled'),
                      'notice':'NO upload or scheduling performed. Human creative review required.'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr);sys.exit(2)
