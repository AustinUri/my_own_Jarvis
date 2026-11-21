"""Original English preschool stories. No copyrighted characters or borrowed scripts."""
from __future__ import annotations
import json
from pathlib import Path

EPISODES = [
    {
        'id': 'nori-tiny-seed', 'title': 'Nori & Blink: The Tiny Seed',
        'description': 'Nori the little garden robot and Blink the firefly discover how a seed grows. An original gentle English story for young children.',
        'scenes': [
            {'kind':'hello','caption':'A little surprise!','narration':'Hello, friends! I am Nori. And this is Blink. We found a tiny seed!'},
            {'kind':'look','caption':'What could it be?','narration':'It is so small. Do you think something wonderful can grow from it?'},
            {'kind':'plant','caption':'A cozy home','narration':'Let us give our seed a cozy home in the soft brown soil.'},
            {'kind':'rain','caption':'A little water','narration':'Blink brings a little rain. Drip, drop! The seed has a drink.'},
            {'kind':'sprout','caption':'Look! A sprout!','narration':'We wait, and wait. Oh! A bright green sprout peeks out to say hello!'},
            {'kind':'celebrate','caption':'We helped it grow!','narration':'A little care can help big things grow. See you next time!'},
        ],
    },
    {
        'id': 'nori-blue-butterfly','title':'Nori & Blink: The Blue Butterfly',
        'description':'A kind little robot and glowing firefly help a butterfly find its way home. Original English preschool cartoon.',
        'scenes': [
            {'kind':'hello','caption':'A fluttering visitor','narration':'Good morning! Nori and Blink hear a gentle flutter in the garden.'},
            {'kind':'butterfly','caption':'Where is your flower?','narration':'A blue butterfly is looking for a flower. Can we help our new friend?'},
            {'kind':'look','caption':'Look high and low','narration':'They look by the stones. They look by the tree. Not here!'},
            {'kind':'flower','caption':'A blue blossom!','narration':'Blink spots something blue. It is a beautiful blossom beside the pond!'},
            {'kind':'butterfly','caption':'You found it!','narration':'The butterfly dances happily above its flower. Flutter, flutter!'},
            {'kind':'celebrate','caption':'Kindness makes us smile','narration':'Helping someone feels wonderful. Goodbye, little butterfly!'},
        ],
    },
    {
        'id':'nori-rainbow-puddle','title':'Nori & Blink: The Rainbow Puddle',
        'description':'Nori and Blink explore colors after a gentle rain. A calm original English cartoon for preschool children.',
        'scenes': [
            {'kind':'hello','caption':'After the rain','narration':'Hello again! The rain has stopped. Nori finds a shiny puddle.'},
            {'kind':'rain','caption':'Splish, splash!','narration':'A tiny splash makes circles in the water. One, two, three!'},
            {'kind':'look','caption':'A colorful surprise','narration':'Blink sees red, yellow, green, and blue inside the puddle.'},
            {'kind':'rainbow','caption':'A rainbow above','narration':'Look up, Nori! A rainbow stretches over the garden.'},
            {'kind':'celebrate','caption':'Colors everywhere','narration':'What a wonderful colorful day! The garden is full of surprises.'},
            {'kind':'goodbye','caption':'See you soon!','narration':'Let us explore another wonder together next time. Goodbye!'},
        ],
    },
]

def save_examples(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for ep in EPISODES:
        (out_dir/f"{ep['id']}.json").write_text(json.dumps(ep, ensure_ascii=False, indent=2), encoding='utf-8')


def validate_episode(ep: dict) -> None:
    assert isinstance(ep,dict) and isinstance(ep.get('id'),str) and ep['id']
    assert 3 <= len(ep.get('scenes', [])) <= 12, '3-12 scenes required'
    for s in ep['scenes']:
        assert s.get('kind') in {'hello','look','plant','rain','sprout','celebrate','butterfly','flower','rainbow','goodbye'}
        assert 4 <= len(s.get('narration','')) <= 250
        assert 2 <= len(s.get('caption','')) <= 60
    assert 6 <= len(ep.get('title','')) <= 95
    assert 'peppa' not in json.dumps(ep).lower(), 'Original characters and titles only'
