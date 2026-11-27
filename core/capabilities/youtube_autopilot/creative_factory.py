"""JARVIS Nori & Blink local animation factory.

A repeatable local-only story, storyboard and MP4 draft generator.
No uploads, no OAuth, no paid APIs, no changes to JARVIS's existing queue.
Installed as core.capabilities.youtube_autopilot.creative_factory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import socket
import sqlite3
from contextlib import closing
from urllib.parse import urlsplit
import subprocess
import sys
import tempfile
import urllib.request
from difflib import SequenceMatcher
import time
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw
from .manager import FileLock, setup, root_dir, config, dump
from .backdrops import backdrop
from .foley import mix_soundtrack
from .quality import inspect_story, inspect_draft_render
from .voice import piper_draft_narrate
from .renderer import font
from .stage import draw_stage

from .visual_contract import ACTIONS, CARRYABLE, DROPPABLE, PROPS, SETTINGS, SHOTS, STATIONARY, audit_storyboard

# Plot IDs belong to this edition. Earlier scripts remain in the duplicate check.
# Each beat directs the action, set, framing and single featured object.
OFFLINE_EDITION = "storybook-1"
STORIES = [
    ("Post for Blink", "Nori delivers a leaf with a message nobody has written.", [
        ("discover", "stream", "close", "leaf", "A letter?", "Nori finds a leaf. It looks just the right size for a letter."),
        ("carry", "stream", "tracking", "leaf", "Special delivery", "Nori carries the leaf to Blink. Special delivery!"),
        ("watch", "garden", "medium", "leaf", "Nothing written", "They look at the leaf. There is no writing on it at all."),
        ("hop", "garden", "wide", "leaf", "A wordless clue", "Nori hops with excitement. Maybe a message can be a feeling."),
        ("point", "garden", "medium", "leaf", "Just for you", "Nori points to the leaf. This part means I thought of you."),
        ("cheer", "garden", "close", "leaf", "Message received", "Hooray! Blink understands. That was a very good letter after all.")]),
    ("At Snail Speed", "Blink learns how to join a very slow walk.", [
        ("enter", "garden", "wide", "snail", "A morning visitor", "Nori walks into the garden. A snail is taking a morning stroll."),
        ("point", "garden", "close", "snail", "Look down here", "Nori points to the tiny traveler. Blink wants to race."),
        ("follow", "garden", "tracking", "snail", "Too far ahead", "Nori follows the snail. Racing would leave their new friend behind."),
        ("watch", "flower-field", "medium", "snail", "A small pause", "Nori waits beside the snail. Blink can wait too."),
        ("discover", "flower-field", "close", "snail", "A quiet surprise", "Nori notices the curl in its shell. Slowing down has surprises."),
        ("wave", "flower-field", "wide", "snail", "See you soon", "They wave goodbye to the snail. What a lovely slow walk.")]),
    ("The Runaway Picnic", "An apple rolls away before the picnic can begin.", [
        ("enter", "orchard", "wide", "apple", "Picnic time", "Nori walks to the picnic spot. One red apple will do."),
        ("watch", "orchard", "close", "apple", "A little wobble", "Watch that apple, Blink. Round things can roll!"),
        ("follow", "hill", "tracking", "apple", "After it!", "Nori follows the apple down the hill. Wait for us, picnic!"),
        ("discover", "hill", "medium", "apple", "There you are", "Nori finds the apple at the bottom. There you are!"),
        ("carry", "orchard", "tracking", "apple", "Back together", "Nori holds the apple close all the way back.", "left"),
        ("cheer", "orchard", "wide", "apple", "Lunch at last", "Hooray! The picnic is back where it belongs.", "left")]),
    ("The Kite Inspector", "Blink has a job high above Nori's head.", [
        ("carry", "meadow", "medium", "kite", "A careful grip", "Nori holds the kite string. Blink has a job today."),
        ("watch", "meadow", "wide", "kite", "A wobble", "Nori watches the kite wobble. Is the little tail all right?"),
        ("point", "hill", "close", "kite", "Up there", "Nori points. Blink can see up close from the air."),
        ("follow", "hill", "tracking", "kite", "Along the hill", "They follow the kite together. The tail is still there."),
        ("hop", "hill", "medium", "kite", "One happy hop", "Nori hops. Good work, Inspector Blink!"),
        ("wave", "hill", "wide", "kite", "Off duty", "Nori waves. The kite inspector can enjoy the breeze now.")]),
    ("Blink's Bubble Turn", "Two friends invent a game they can share.", [
        ("discover", "flower-field", "medium", "bubble", "Something shiny", "Nori spots a bubble and invents a game. Follow the shine!"),
        ("follow", "flower-field", "tracking", "bubble", "Nori's turn", "Nori follows the bubble. Blink wants a turn at leading."),
        ("watch", "meadow", "close", "bubble", "Your turn", "Nori waits. Go ahead, Blink. You can be first this time.", "left"),
        ("point", "meadow", "medium", "bubble", "That way", "Nori points out the bubble as Blink leads the game.", "left"),
        ("hop", "meadow", "wide", "bubble", "New rule", "Nori hops. New rule! Whoever spots the shine picks the next game.", "left"),
        ("cheer", "meadow", "close", "bubble", "Both winners", "Hooray for both of us! A turn each was just right.", "left")]),
    ("Two Little Lights", "Blink wonders whether the moon needs a friend.", [
        ("search", "sunset", "wide", "moon", "Who's still awake?", "Nori looks around at dusk. Is anyone else still awake?"),
        ("discover", "sunset", "close", "moon", "Hello up there", "Nori spots the moon. Blink feels very small beside that light."),
        ("point", "sunset", "medium", "moon", "Far and near", "Nori points to the moon. Can it shine right here beside me?"),
        ("watch", "woodland", "close", "moon", "Stay with me", "Nori watches Blink glowing close by. Your light keeps me company."),
        ("enter", "sunset", "tracking", "moon", "Side by side", "Nori walks with Blink. One light is far, and one is near."),
        ("wave", "sunset", "wide", "moon", "Good night", "They wave goodnight to the moon. Every light has its place.")]),
    ("A Parade for One Pebble", "Nori starts a parade for an unlikely guest.", [
        ("point", "garden", "close", "pebble", "Guest of honor", "Nori points at a pebble. Today you can lead our parade."),
        ("watch", "garden", "medium", "pebble", "Ready, steady", "They wait. The pebble does not seem to know how parades work."),
        ("carry", "meadow", "tracking", "pebble", "A little help", "Nori carries the pebble. Now the guest of honor can come too."),
        ("hop", "meadow", "wide", "pebble", "The parade step", "Nori hops beside the pebble. Blink calls it the parade step."),
        ("wave", "meadow", "medium", "pebble", "Hello, everyone", "Nori waves to an imaginary crowd. What a splendid little parade!"),
        ("cheer", "meadow", "close", "pebble", "Three cheers", "Three cheers for our pebble! Even quiet guests belong.")]),
    ("The Cloud Guessing Game", "A cloud gives two friends quite different ideas.", [
        ("enter", "hill", "wide", "cloud", "Hilltop game", "Nori walks to the hilltop. Blink has a guessing game."),
        ("point", "hill", "medium", "cloud", "Which shape?", "Nori points at a cloud. Is it long or round?"),
        ("follow", "meadow", "tracking", "cloud", "Try this side", "They follow the cloud. From here, Nori thinks it looks round."),
        ("watch", "meadow", "close", "cloud", "Blink's guess", "Nori looks again. Blink thinks it looks long instead."),
        ("hop", "hill", "wide", "cloud", "Another look", "Nori hops for another look. Could both guesses be right?"),
        ("cheer", "hill", "medium", "cloud", "Two right answers", "Hooray for two guesses! Games are fun when everyone can imagine.")]),
    ("The Acorn's Tiny Hat", "Blink and Nori solve a woodland riddle.", [
        ("discover", "woodland", "close", "acorn", "A tiny hat?", "Nori spots an acorn. Is that a tiny hat on top?"),
        ("search", "woodland", "medium", "acorn", "Whose is it?", "Nori looks around. Did someone lose a very small hat?"),
        ("carry", "woodland", "tracking", "acorn", "Come with us", "Nori carries the acorn along. Blink has a better guess."),
        ("point", "garden", "close", "acorn", "Built right in", "Nori points to the cap. It fits this acorn perfectly."),
        ("watch", "garden", "medium", "acorn", "Mystery solved", "They look closely. The cap is part of the acorn itself!"),
        ("cheer", "garden", "wide", "acorn", "Keep your cap", "Nori cheers. Nobody lost anything. Keep your cap, little acorn!")]),
    ("The Balloon Guide", "A balloon makes Nori easy to find.", [
        ("carry", "garden", "medium", "balloon", "Easy to spot", "Nori holds the balloon string. Blink can always spot that bright shape."),
        ("enter", "flower-field", "wide", "balloon", "Through the flowers", "Nori walks on. From down here, the whole field looks very tall."),
        ("search", "flower-field", "close", "balloon", "Where is Blink?", "Nori looks around. Where did our little guide go?"),
        ("point", "flower-field", "medium", "balloon", "Look up", "Nori points up. Blink is right beside the balloon."),
        ("follow", "meadow", "tracking", "balloon", "Together again", "They follow the balloon across the meadow. Nobody is lost now."),
        ("wave", "meadow", "wide", "balloon", "Here we are", "Nori waves hello. It is easy to find a friend who waves back.")]),
    ("The Pond's Round Riddle", "Nori discovers what a ripple does.", [
        ("watch", "pond", "wide", "ripple", "A round riddle", "Nori watches a ripple. Is that a ring on the water?"),
        ("point", "pond", "close", "ripple", "Look at the edge", "Nori points to its edge. A ring usually stays the same size."),
        ("search", "pond", "medium", "ripple", "Find the middle", "Nori looks for the middle. Blink, can you see it too?"),
        ("hop", "pond", "wide", "ripple", "Little then big", "Nori hops on the bank. Little then big, just like the ripple!"),
        ("discover", "pond", "close", "ripple", "It spreads", "Nori sees the answer. A ripple is water moving outward."),
        ("wave", "pond", "medium", "ripple", "Bye, little ring", "They wave to the ripple. Goodbye, little round riddle.")]),
    ("Where Does a Rainbow End?", "Blink and Nori try to find the end of a rainbow.", [
        ("discover", "meadow", "wide", "rainbow", "An arch overhead", "Nori spots a rainbow. Where does its long curve end?"),
        ("point", "meadow", "medium", "rainbow", "Over there", "Nori points to one side. Blink thinks it ends over there."),
        ("enter", "hill", "tracking", "rainbow", "Up the hill", "Nori walks uphill for a better look. The colors still seem far away."),
        ("search", "hill", "close", "rainbow", "Still looking", "Nori looks for the very last bit. That is a tricky place to find."),
        ("watch", "hill", "wide", "rainbow", "Enjoy the view", "They watch the rainbow instead. It is lovely from here."),
        ("cheer", "hill", "medium", "rainbow", "A fine ending", "Hooray, says Nori. A good view is a fine ending for our walk.")]),
    ("The Quietest Tap", "A little acorn helps Nori and Blink find a sound small enough for bedtime.", [
        ("search", "woodland", "medium", "acorn", "Something quiet", "The garden is nearly asleep. Nori looks for a sound small enough for bedtime."),
        ("discover", "woodland", "close", "acorn", "This little fellow?", "Nori spots an acorn. Would something this small make a little sound?"),
        ("carry", "woodland", "tracking", "acorn", "A good listening spot", "Nori carries the acorn to a patch of bare earth. Listen closely, Blink."),
        ("drop", "woodland", "close", "acorn", "Tip, tap", "Nori drops the acorn. Tip, tap. Did you hear that?"),
        ("watch", "woodland", "wide", "acorn", "Two tiny taps", "They watch the acorn. I heard two taps, says Blink. The second one was so tiny!"),
        ("wave", "sunset", "medium", "acorn", "Goodnight, little acorn", "Nori waves goodnight. Now we know how a little acorn says hello.")]),
]

# Older story JSON readers still expect a kind. Staging uses the action.
_ACTION_KIND = dict(enter="hello", search="look", point="look", hop="celebrate",
                    follow="look", discover="look", carry="look", watch="look",
                    cheer="celebrate", wave="goodbye", drop="look")
_INFLECTED_ACTIONS = dict(enters="enter", searches="search", points="point", hops="hop",
                          follows="follow", discovers="discover", carries="carry",
                          watches="watch", cheers="cheer", waves="wave", drops="drop")


def _normalized(s):
    return " ".join(re.findall(r"[a-z0-9]+", s.casefold()))


def _signature(ep):
    return hashlib.sha256('|'.join(_normalized(s['narration']) for s in ep['scenes']).encode('utf8')).hexdigest()


def _existing(root):
    found=[]
    for directory in (root/'stories',root/'creative_drafts'):
        for path in directory.glob('*.json') if directory.is_dir() else []:
            try:
                e=json.loads(path.read_text(encoding='utf8'))
                if (isinstance(e, dict) and isinstance(e.get('title'), str)
                        and isinstance(e.get('scenes'), list) and e['scenes']
                        and all(isinstance(sc, dict) and isinstance(sc.get('narration'), str)
                                for sc in e['scenes'])):
                    found.append(e)
            except (ValueError, OSError):continue
    return found


def offline_story(root, existing, rng):
    used_titles = {_normalized(e.get("title", "")) for e in existing}
    used_plots = {e["creative"].get("plot_id") for e in existing
                  if isinstance(e.get("creative"), dict)
                  and e["creative"].get("edition") == OFFLINE_EDITION}
    candidates = [(i, story) for i, story in enumerate(STORIES)
                  if i not in used_plots and _normalized("Nori & Blink: " + story[0]) not in used_titles]
    if not candidates:
        raise RuntimeError("Offline story library exhausted. Start LM Studio for a new script.")
    opening_props = [e['scenes'][0].get('prop') for e in existing if e.get('scenes')]
    counts = [opening_props.count(story[2][0][3]) for _, story in candidates]
    least_used = min(counts)
    idx, (title, description, beats) = rng.choice(
        [candidate for candidate, count in zip(candidates, counts) if count == least_used])
    scenes = [
        dict(kind=_ACTION_KIND[action], action=action, setting=setting, shot=shot, prop=prop,
             caption=caption, narration=narration, motion_variant=rng.randrange(1, 100000),
             direction=direction[0] if direction else "right")
        for action, setting, shot, prop, caption, narration, *direction in beats
    ]
    return {"id": "nori-" + rng.randbytes(6).hex(), "title": "Nori & Blink: " + title,
            "description": description, "scenes": scenes,
            "creative": {"backend": "offline_curated", "edition": OFFLINE_EDITION,
                         "plot_id": idx, "version": 6}}


AI_INSPIRATIONS = (
    "a guessing game with two good answers", "a delivery that almost goes astray",
    "a friend who wants to join in", "a very small misunderstanding",
    "finding a way to take turns", "a clue everyone overlooked",
    "discovering a new rhythm", "a moment when the slower friend leads",
)


def _check_candidate(episode, existing):
    inspect_story(episode)
    contract = audit_storyboard(episode)
    if not contract["ok"]:
        raise ValueError("Unrenderable storyboard: " + " / ".join(contract["issues"]))
    title = _normalized(episode["title"])
    words = _normalized(" ".join(s["narration"] for s in episode["scenes"])).split()
    beats = [(s["action"], s["prop"]) for s in episode["scenes"]]
    for prior in existing:
        scenes = prior["scenes"]
        old_words = _normalized(" ".join(s.get("narration", "") for s in scenes)).split()
        if (title == _normalized(prior.get("title", "")) or
                beats == [(s.get("action"), s.get("prop")) for s in scenes] or
                SequenceMatcher(None, words, old_words, autojunk=False).ratio() > .62):
            raise ValueError("Duplicate episode title, narration, or staged plot")


def _json_from_reply(text):
    text=re.sub(r'<think>.*?</think>','',text,flags=re.S|re.I).strip()
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
    left=text.find('{');right=text.rfind('}')
    if left<0 or right<=left:raise ValueError('Model did not return JSON object')
    return json.loads(text[left:right+1])


def _spoken_beat(scene, index):
    """The narrator describes the staged action. The writer supplies the dialogue."""
    obj = scene["prop"]
    location = scene["setting"].replace("-", " ")
    leads = {
        "enter": ("Nori walks into view.", "Here comes Nori."),
        "search": ("Nori looks both ways.", "Nori searches for a clue."),
        "point": (f"Nori points to the {obj}.", "Nori points it out."),
        "hop": ("Up hops Nori!", "Nori takes a little hop."),
        "follow": (f"Nori follows the {obj}.", "Nori walks along behind it."),
        "discover": (f"Nori spots the {obj}.", f"There! Nori sees the {obj}."),
        "carry": (f"Nori carries the {obj}.", f"Nori holds the {obj} close."),
        "drop": (f"Nori drops the {obj}.", f"Nori releases the {obj}."),
        "watch": ("The friends watch together.", "Nori watches for a moment."),
        "cheer": ("Nori cheers!", "Hooray!"),
        "wave": ("Nori waves.", "One last wave from Nori."),
    }
    if scene["action"] == "enter" and location in ("garden","meadow","orchard","woodland"):
        lead = f"Nori walks into the {location}."
    else:
        lead = leads[scene["action"]][index % 2]
    dialogue = scene["dialogue"].strip().strip('"“”').strip()
    if not 2 <= len(dialogue.split()) <= 12:
        raise ValueError(f"Scene {index+1}: write 2–12 words of spoken dialogue")
    if re.match(r"^(Nori|Blink|They)\s+(?:says?|asks?|walks?|looks?|carries|holds?|points?|watches|waves?|hops?)\b",
                dialogue, re.I):
        raise ValueError(f"Scene {index+1}: write the character's actual words instead of a stage direction")
    return lead + ' ' + dialogue


def _episode_format(featured):
    def choice(values):
        return {"type":"string", "enum":list(values)}

    def record(fields):
        return {"type":"object", "properties":fields,
                "required":list(fields), "additionalProperties":False}

    string = {"type":"string"}
    actions = [a for a in ACTIONS if (a != "drop" or featured in DROPPABLE)
               and (a != "carry" or featured in CARRYABLE) and (a != "follow" or featured not in STATIONARY)]
    scene = record({"action":choice(actions), "prop":choice([featured]),
                    "setting":choice(["pond"] if featured == "ripple" else SETTINGS),
                    "shot":choice(SHOTS), "direction":choice(["left","right"]),
                    "caption":string, "dialogue":string})
    script = record({"title":string, "description":string,
                     "scenes":{"type":"array","minItems":6,"maxItems":6,"items":scene}})
    return {"type":"json_schema","json_schema":{"name":"episode","strict":True,"schema":script}}


def ai_story(root,existing,rng):
    c=config(root)
    if not _local_model_reachable(c):raise RuntimeError('LM Studio local endpoint is unavailable')
    recent=[e.get('title','') for e in existing][-40:]
    inspiration=rng.choice(AI_INSPIRATIONS)
    featured = rng.choice(PROPS)
    prompt = (
        "Write an original six-scene English preschool cartoon about Nori, a little robot, "
        "and Blink, a firefly. They are the only actors. Nori performs the main action in each shot. "
        "Blink hovers and reacts. Give them a small, concrete problem that one of those actions solves. "
        f"Try {inspiration}. Prior titles to avoid: {json.dumps(recent)}. "
        "Return one JSON object with title, description, scenes. Each of six scenes has "
        "caption (2-5 words), dialogue (2-12 English words), setting, action, shot, prop. "
        f"Settings: {', '.join(SETTINGS)}. Actions Nori can do: {', '.join(ACTIONS)}. "
        f"Shot sizes: {', '.join(SHOTS)}. Available featured objects: {', '.join(PROPS)}. "
        f"For this episode use {featured!r} as the featured prop in ALL six scenes. "
        "Nori and Blink can solve different problems using that object. Do not introduce a second "
        "object or animal in the title, description, narration or captions. The featured object "
        "is visible throughout, even when Nori is still looking for it. Tell the story through a "
        "change in what the friends think, feel or decide. Stage one physical action per line. "
        "A ripple belongs in the pond. "
        "Optional direction is right or left. Keep it consistent until the journey reverses. "
        "The renderer supplies a narrator sentence describing each action. Write only what "
        "a character says aloud in dialogue. Use first person or a question, e.g. 'Is it my turn?' "
        "No speaker labels, stage directions, colors, or extra physical events. Link the six "
        "lines like a real conversation and let the final line answer the opening problem. "
        f"Nori can carry only {', '.join(CARRYABLE)}. These stay in place: {', '.join(STATIONARY)}. "
        f"Nori can drop only {', '.join(DROPPABLE)}. "
        "Use at least three different actions and two different shots. No famous characters, brands "
        "or unsafe behavior. Original dialogue is welcome. Return JSON only."
    )
    body={'model':c['lmstudio_model'],
          'messages':[{'role':'system','content':'You are a careful original preschool scriptwriter and storyboard director. Return JSON only.'},
                      {'role':'user','content':prompt}],
          'temperature':.95,'max_tokens':2300,'stream':False,
          'response_format':_episode_format(featured)}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirects())
    last = None
    for attempt in range(4):
        candidate_text = None
        req = urllib.request.Request(c["lmstudio_url"], data=json.dumps(body).encode("utf8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=100) as response:
                reply = json.load(response)
            candidate_text = reply["choices"][0]["message"]["content"]
            generated = _json_from_reply(candidate_text)
            title = generated["title"]
            if not title.startswith("Nori & Blink: "):
                title = "Nori & Blink: " + title
            scenes = []
            for index, item in enumerate(generated["scenes"]):
                # Unsupported model actions must go back to the writer for revision.
                scene = {k: item[k] for k in ("setting", "action", "shot", "prop", "caption")}
                scene["action"] = _INFLECTED_ACTIONS.get(scene["action"], scene["action"])
                if "dialogue" in item and scene["action"] in ACTIONS:
                    scene["dialogue"] = item["dialogue"]
                    scene["narration"] = _spoken_beat(scene, index)
                else:
                    scene["narration"] = item.get("narration", "")
                if "visible_objects" in item:
                    scene["visible_objects"] = item["visible_objects"]
                if "direction" in item:
                    scene["direction"] = item["direction"]
                scene["kind"] = _ACTION_KIND.get(scene["action"], "look")
                scene["motion_variant"] = rng.randrange(1, 100000)
                scenes.append(scene)
            ep = dict(id="nori-" + rng.randbytes(6).hex(), title=title,
                      description=generated["description"], scenes=scenes,
                      creative={"backend": "lmstudio_qwen", "version": 6, "inspiration": inspiration})
            _check_candidate(ep, existing)
            return ep
        except (KeyError, TypeError, ValueError, AttributeError, IndexError, AssertionError) as exc:
            last = str(exc) or "invalid scene structure"
            if isinstance(candidate_text, str):
                body["messages"].append({"role":"assistant", "content":candidate_text[-6000:]})
            body["temperature"] = .45
            body["messages"].append({"role": "user", "content": "Return the corrected full episode JSON. "
                                     "Apply every edit below. When an object is absent, rewrite that "
                                     "sentence without mentioning it at all. Do not change the prop to fix it. "
                                     + last[:1500]})
        except OSError:
            # Older local servers accept plain chat but lack schema support.
            last = "local model request failed"
            body.pop("response_format", None)
    raise RuntimeError(f"Qwen produced no valid original story: {last}")


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _local_model_reachable(c):
    try:
        parsed = urlsplit(c.get("lmstudio_url", ""))
        if (parsed.scheme not in ("http", "https") or parsed.username is not None or
                parsed.hostname not in ("127.0.0.1", "localhost", "::1")):
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((parsed.hostname, port), timeout=.35):
            return True
    except (OSError, ValueError):
        return False


def create_story(root, backend="auto", seed=None):
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    if backend not in ("auto", "offline", "local-ai"):
        raise ValueError("Invalid backend")
    ep = None
    fallback_reason = None
    if backend == "local-ai" or backend == "auto" and _local_model_reachable(config(root)):
        try:
            ep = ai_story(root, _existing(root), rng)
        except (RuntimeError, OSError, ValueError) as exc:
            if backend == "local-ai":
                raise RuntimeError(f"Local AI story generation failed: {exc}") from exc
            fallback_reason = str(exc)[:200]

    directory = root / "creative_drafts"
    directory.mkdir(parents=True, exist_ok=True)
    # CLI, skill and worker may run together. SQLite releases this cross-platform
    # write lock even after a crash; inference stays outside the critical section.
    with closing(sqlite3.connect(directory / ".generation-lock.sqlite", timeout=30)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        previous = _existing(root)
        if ep is None:
            ep = offline_story(root, previous, rng)
            if fallback_reason:
                ep["creative"]["ai_fallback_reason"] = fallback_reason
        for scene in ep['scenes']:
            scene['cast_version'] = 2
        _check_candidate(ep, previous)
        ep["creative"].update(signature=_signature(ep), created_at=datetime.now(timezone.utc).isoformat(),
                              manual_approval_required=True)
        path = directory / (ep["id"] + ".json")
        if path.exists():
            raise FileExistsError(path)
        dump(path, ep)
    return ep, path


@lru_cache(maxsize=128)
def _caption_layout(caption, width, height):
    """Fit the complete ink bounds inside a two-line, phone-safe caption area."""
    scale = min(width / 360, height / 640)
    max_width = int(width * .80)
    for size in range(max(12, round(21 * scale)), max(10, round(14 * scale)) - 1, -1):
        face = font(size)
        lines = []
        for word in caption.split():
            if lines and face.getlength(lines[-1] + " " + word) <= max_width:
                lines[-1] += " " + word
            else:
                lines.append(word)
        if not 1 <= len(lines) <= 2:
            continue
        bounds = [face.getbbox(line) for line in lines]
        if max(right-left for left, top, right, bottom in bounds) > max_width:
            continue
        gap = max(2, round(4 * scale))
        ink_height = sum(bottom-top for left, top, right, bottom in bounds) + gap * (len(lines)-1)
        y = round(height * .925) - ink_height
        layout = []
        for line, (left, top, right, bottom) in zip(lines, bounds):
            x = (width - right + left) // 2
            layout.append((line, x-left, y-top))
            y += bottom-top+gap
        pad = round(11 * scale)
        half = max(right-left for left, top, right, bottom in bounds) / 2 + pad * 1.5
        box = (round(width/2-half), round(height*.925)-ink_height-pad,
               round(width/2+half), round(height*.925)+pad)
        if box[0] >= 0 and box[1] >= height*.80 and box[2] < width and box[3] < height:
            return face, layout, box
    raise ValueError(f"Caption cannot fit safely at {width}x{height}: {caption!r}")


def _draw_scene(scene, local_time, speech_seconds, width, height, *, include_prop=True):
    progress = max(0., local_time / speech_seconds)
    img = backdrop(scene['setting'], scene['shot'], min(1., progress), width, height)
    draw_stage(img, scene, progress, speech_seconds, include_prop=include_prop)
    if scene.get('cast_version') == 2 and scene['shot'] == 'close':
        p = min(1., progress / .78)
        zoom = 1 + .065*p*p*(3-2*p)
        dx, dy = width*(1-1/zoom), height*(1-1/zoom)
        img = img.resize((width,height), Image.Resampling.BICUBIC,
                         box=(dx*.48, dy*.49, width-dx*.52, height-dy*.51))
    if scene.get("direction") == "left":
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    face, layout, box = _caption_layout(scene['caption'], width, height)
    pen = ImageDraw.Draw(img)
    radius = max(3, width // 35)
    pen.rounded_rectangle(box, radius, fill='#fff1d7', outline='#c6aa85', width=max(1, width//360))
    for line, x, y in layout:
        pen.text((x,y), line, font=face, fill='#344c4d')
    return img


def frame(t, episode, secs=7.0, w=360, h=640):
    """Fixed-time storyboard preview. Encoded drafts use the recorded edit."""
    idx = max(0, min(len(episode['scenes'])-1, int(t//secs)))
    return _draw_scene(episode['scenes'][idx], t-idx*secs, secs, w, h)


def story_digest(episode):
    content = {field: episode[field] for field in ('id','title','description','scenes')}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode('utf8')).hexdigest()


def render_draft(episode, root, *, width=360, height=640, fps=10, scene_seconds=7.0):
    contract = audit_storyboard(episode)
    if not contract['ok']:
        raise ValueError('Storyboard rejected: ' + ', '.join(contract['issues']))
    if width < 240 or height < 420 or width % 2 or height % 2 or fps not in range(5,31):
        raise ValueError('Use even dimensions of at least 240x420 and 5–30 fps')
    for scene in episode['scenes']:
        _caption_layout(scene['caption'], width, height)
    conf = config(root)
    uid = episode['id']
    if not re.fullmatch(r'nori-[0-9a-f]{12}', uid):
        raise ValueError('Invalid creative draft ID')
    renders = root / 'creative_drafts' / 'renders'
    renders.mkdir(parents=True, exist_ok=True)
    output, wave = renders / f'{uid}.mp4', renders / f'{uid}.wav'
    report = renders / f'{uid}.review.json'
    with FileLock(renders / f'{uid}.lock'), tempfile.TemporaryDirectory(dir=renders) as tmp:
        if any(path.exists() for path in (output, wave, report)):
            raise FileExistsError(f'An earlier render for {uid} already exists')
        scratch = Path(tmp)
        track = scratch / 'voice.wav'
        timeline = piper_draft_narrate(episode, track, model=conf.get('piper_model',''),
                                      piper_bin=conf.get('piper_bin','piper'),
                                      fps=fps, scene_seconds=scene_seconds)
        soundtrack = scratch / 'soundtrack.wav'
        mix_soundtrack(track, soundtrack, episode['scenes'], timeline, fps)
        movie = scratch / 'episode.mp4'
        cmd = ['ffmpeg','-hide_banner','-loglevel','error','-nostdin',
               '-f','rawvideo','-pixel_format','rgb24','-video_size',f'{width}x{height}',
               '-framerate',str(fps),'-i','pipe:0','-i',str(soundtrack),'-map','0:v:0','-map','1:a:0',
               '-c:a','aac','-b:a','128k','-c:v','libx264','-preset','veryfast','-crf','20',
               '-pix_fmt','yuv420p','-movflags','+faststart',str(movie)]
        with tempfile.TemporaryFile() as errors, subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=errors) as process:
            try:
                for scene, cue in zip(episode['scenes'], timeline, strict=True):
                    for n in range(cue['frame_count']):
                        image = _draw_scene(scene, n/fps, cue['speech_seconds'], width, height)
                        process.stdin.write(image.tobytes())
                process.stdin.close()
                if process.wait():
                    errors.seek(0)
                    raise RuntimeError('FFmpeg failed: ' + errors.read().decode('utf8','replace')[-1200:])
            except BaseException:
                process.kill()
                process.wait()
                raise
        review = {'story_id':uid, 'story_digest':story_digest(episode),
                  'video':str(output.resolve()), 'audio':str(wave.resolve()),
                  'animation_method':'storybook_rig', 'fps':fps, 'timeline':timeline,
                  'automatic_upload_allowed':False, 'human_review_required':True}
        try:
            review['mechanical_qa'] = inspect_draft_render(movie, episode, timeline, fps)
        except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
            review['mechanical_qa_error'] = str(exc)
        movie.replace(output)
        track.replace(wave)
        dump(report, review)
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
        exit_code = 0
        print('Creative worker started: LOCAL DRAFTS ONLY; NO uploads or YouTube scheduling.',flush=True)
        while True:
            cycles+=1
            try:
                create_args=['create','--count',str(args.count),'--backend',args.backend,'--render',
                             '--width',str(args.width),'--height',str(args.height),'--fps',str(args.fps),
                             '--seconds',str(args.seconds),'--root',str(root)]
                exit_code = max(exit_code, main(create_args))
            except Exception as exc:
                exit_code = 1
                print(json.dumps({'cycle_error':str(exc),'upload':False}),flush=True)
            if args.max_cycles and cycles>=args.max_cycles:return exit_code
            time.sleep(args.interval_hours*3600)
    if not 1<=args.count<=5:ap.error('count must be between 1 and 5 per run')
    if args.width<240 or args.height<420 or args.width%2 or args.height%2 or args.fps not in range(5,31):ap.error('Invalid preview size or FPS')
    results=[]
    for _ in range(args.count):
        ep,path=create_story(root,backend=args.backend)
        result={'id':ep['id'],'title':ep['title'],'backend':ep['creative']['backend'],
                'story_path':str(path),'storyboard':[{'setting':s['setting'],'action':s['action'],'shot':s['shot'],'prop':s['prop']} for s in ep['scenes']],
                'state':'draft_waiting_for_render','upload':False}
        if args.render:
            try:
                rendered=render_draft(ep,root,width=args.width,height=args.height,fps=args.fps,scene_seconds=args.seconds)
                result.update({'state':'render_rejected' if rendered.get('mechanical_qa_error') else 'rendered_for_review','video_path':rendered['video'],
                               'qa':rendered.get('mechanical_qa'), 'qa_error':rendered.get('mechanical_qa_error')})
            except Exception as exc:
                result.update({'state':'render_failed','error':str(exc)})
        results.append(result)
    print(json.dumps({'created':len(results),'drafts':results,'autopublish_enabled':config(root).get('autopublish_enabled'),
                      'notice':'NO upload or scheduling performed. Human creative review required.'},ensure_ascii=False,indent=2))
    return int(any(draft['state'] in {'render_failed', 'render_rejected'} for draft in results))

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr);sys.exit(2)
