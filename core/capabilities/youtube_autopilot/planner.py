"""Optional local-story generator via LM Studio (no paid API)."""
from __future__ import annotations
import json
import re
import urllib.request
import uuid
from difflib import SequenceMatcher
from .episodes import validate_episode

KINDS='hello, look, plant, rain, sprout, celebrate, butterfly, flower, rainbow, goodbye'
TOPICS=['help a shy cloud smile','learn to share a watering can','find a cozy spot for a snail','learn how shadows move','make a leaf boat','help a sleepy flower wake up','discover why a star twinkles','help a lost ladybug find its leaf','find three different shapes','learn to wait patiently']

def new_story(config, existing:list[dict]):
    topic=TOPICS[len(existing)%len(TOPICS)]
    prompt=(f'Create ONE original charming preschool episode in simple spoken English for a gentle original cartoon about Nori (a friendly little garden robot) and Blink (a glowing firefly). Topic: {topic}. '
            f'Never imitate any famous children TV show or copyrighted character. Kids age 3-6. A clear beginning, a small harmless problem, a thoughtful solution, an uplifting ending. '
            f'Output ONLY JSON with keys id,title,description,scenes. Exactly 6 scenes; each scene uses kind (one of {KINDS}), caption (2-5 words), narration (9-17 child-friendly words). '
            f'Every visual action must use one of those kinds; no mention of real brands, commercial offers, politics, violence, scary scenes, or unsafe actions. '
            f'Description must be 1 factual sentence. Do not use a title already seen: {[e["title"] for e in existing]}.')
    body={'model':config['lmstudio_model'],'messages':[{'role':'system','content':'You write unique gentle stories for preschool children. Return strict JSON only.'},{'role':'user','content':prompt}], 'temperature':0.75,'max_tokens':1200,'stream':False}
    req=urllib.request.Request(config['lmstudio_url'],data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=85) as res:
        response=json.load(res)
    s=response['choices'][0]['message']['content']
    s=re.sub(r'<think>.*?</think>','',s,flags=re.S).strip()
    s=re.sub(r'^```(?:json)?\s*|\s*```$','',s)
    if not s.startswith('{'):s=s[s.index('{'):s.rindex('}')+1]
    ep=json.loads(s)
    ep['id']='nori-'+uuid.uuid4().hex[:12]
    validate_episode(ep)
    for prev in existing:
        a=' '.join(x['narration'] for x in ep['scenes'])
        b=' '.join(x['narration'] for x in prev['scenes'])
        if ep['title'].casefold()==prev['title'].casefold() or SequenceMatcher(None,a.casefold(),b.casefold()).ratio()>.55:
            raise ValueError('Generated story too similar to an existing episode; rejected')
    return ep
