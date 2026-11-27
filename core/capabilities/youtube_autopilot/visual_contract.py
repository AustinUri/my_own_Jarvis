"""Story-to-screen audit for JARVIS Kids Video Factory.

Mechanical checks only: the result is never an artistic approval.
No network, no uploads, and no writes. Standard library only.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
import re

VERSION = "0.6.0"

PROPS = ("leaf", "snail", "apple", "kite", "bubble", "moon", "pebble", "cloud",
         "acorn", "balloon", "ripple", "rainbow")
SETTINGS = ("garden", "woodland", "stream", "meadow", "orchard", "pond", "sunset",
            "flower-field", "hill")
SHOTS = ("wide", "medium", "close", "tracking")
ACTION_WORDS = {
    "enter": "enter enters entering come comes coming arrive arrives walk walks walking step steps",
    "search": "search searches searching look looks looking peek peeks where hunt hunts",
    "point": "point points pointing there this that",
    "hop": "hop hops hopping jump jumps bounce bounces",
    "follow": "follow follows following chase chases alongside behind",
    "discover": "find finds found discover discovers discovering spot spots notice notices see sees",
    "carry": "carry carries carrying hold holds holding bring brings take takes",
    "drop": "drop drops dropping release releases",
    "watch": "watch watches watching look looks wait waits listen listens see sees",
    "cheer": "cheer cheers hooray hurrah yay bravo hurray",
    "wave": "wave waves waving goodbye goodnight hello",
}
ACTIONS = tuple(ACTION_WORDS)
CARRYABLE = ("leaf", "snail", "apple", "kite", "pebble", "acorn", "balloon")
DROPPABLE = ("apple", "pebble", "acorn")
STATIONARY = ("moon", "rainbow", "ripple")

# Compound actions such as "waves and puts it down" need two distinct beats.
# Infinitives in dialogue ("I want to hop") are intentions, not performances.
_PERFORMED = {
    "enters":"enter", "walks":"enter", "searches":"search", "points":"point",
    "hops":"hop", "jumps":"hop", "follows":"follow", "discovers":"discover",
    "carries":"carry", "holds":"carry", "watches":"watch", "cheers":"cheer", "waves":"wave",
    "drops":"drop", "releases":"drop",
    **dict.fromkeys(("places", "puts", "throws", "juggles", "folds", "pushes",
                     "kicks", "catches", "opens", "digs", "paints", "flies"), "unstaged"),
}
_ALSO_PERFORMED = {"carry":{"enter"}, "follow":{"enter"}, "cheer":{"hop"}}


def _extra_performance(narration, action):
    for sentence in re.split(r"[.!?;]", narration.lower()):
        if not re.match(r"^\s*nori\s", sentence):
            continue
        nori = re.split(r"\b(?:(?:and|as|but)\s+blink|who|when|while|if|because)\b",
                        sentence, maxsplit=1)[0]
        for verb in re.findall(r"\b(?:nori|and|then)\s+([a-z]+)", nori):
            performed = _PERFORMED.get(verb)
            if performed and performed != action and performed not in _ALSO_PERFORMED.get(action, ()):
                return verb
    return None

# Known plot nouns include objects mentioned in earlier drafts that have no art.
# Only the primary prop goes on stage. Free-form model declarations aren't assets.
OBJECT_WORDS = {prop: {prop, prop + "s"} for prop in PROPS}
OBJECT_WORDS["leaf"] = {"leaf", "leaves"}
for name in ("lantern", "moth", "boat", "dragonfly", "frog", "butterfly",
             "ladybug", "twig", "mitten", "squirrel", "umbrella", "bridge",
             "feather", "beetle", "bird", "bowl", "snowflake", "dragon", "unicorn"):
    OBJECT_WORDS[name] = {name, name + "s"}
OBJECT_WORDS["butterfly"].add("butterflies")
OBJECT_WORDS["dragonfly"].add("dragonflies")


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", str(value).lower()))


def _objects(text: str) -> set[str]:
    words = _words(text)
    return {name for name, spellings in OBJECT_WORDS.items() if words & spellings}


def audit_storyboard(episode: dict[str, Any]) -> dict[str, Any]:
    """Check the physical vocabulary and English cue for each staged action."""
    issues: list[str] = []
    notes: list[str] = []
    scenes = episode.get("scenes", [])
    valid = []
    if not isinstance(scenes, list) or len(scenes) != 6:
        issues.append("Creative drafts require exactly six storyboard scenes")
    for i, scene in enumerate(scenes if isinstance(scenes, list) else [], 1):
        if not isinstance(scene, dict):
            issues.append(f"scene {i}: invalid scene object")
            continue
        if scene.get("direction", "right") not in ("right", "left"):
            issues.append(f"scene {i}: screen direction must be left or right")
        if not isinstance(scene.get("caption"), str) or not scene["caption"].strip():
            issues.append(f"scene {i}: missing caption")
        for field, options in (("setting", SETTINGS), ("shot", SHOTS), ("action", ACTIONS), ("prop", PROPS)):
            if scene.get(field) not in options:
                issues.append(f"scene {i}: unsupported {field} {scene.get(field)!r}")
        prop, action = scene.get("prop"), scene.get("action")
        narration = scene.get("narration")
        if not isinstance(narration, str) or not narration.strip():
            issues.append(f"scene {i}: missing narration")
            continue
        if not isinstance(prop, str) or prop not in PROPS or action not in ACTIONS:
            continue
        declared = scene.get("visible_objects", [])
        if not isinstance(declared, list) or any(item != prop for item in declared):
            issues.append(f"scene {i}: renderer can stage only its featured prop {prop!r}")
        if (action == "carry" and prop not in CARRYABLE or action == "follow" and prop in STATIONARY
                or action == "drop" and prop not in DROPPABLE):
            issues.append(f"scene {i}: {action} is unavailable for {prop}")
        if prop == "ripple" and scene.get("setting") != "pond":
            issues.append(f"scene {i}: a ripple needs the pond set")
        if not _words(narration).intersection(ACTION_WORDS[action].split()):
            issues.append(f"scene {i}: narration has no cue for {action!r}")
        first_actor = re.match(r"\s*Blink\s+([A-Za-z]+)\b", narration, re.I)
        if first_actor and first_actor[1].lower() in ACTION_WORDS[action].split():
            issues.append(f"scene {i}: Nori performs {action!r}. Replace this line with a sentence "
                          f"beginning 'Nori {first_actor[1].lower()}'. Give Blink a separate line of dialogue if needed.")
        extra = _extra_performance(narration, action)
        if extra:
            issues.append(f"scene {i}: Nori only performs {action!r}. Remove the additional "
                          f"movement {extra!r} from the line.")
        for obj in sorted(_objects(narration + " " + str(scene.get("caption", ""))) - {prop}):
            issues.append(f"scene {i}: {obj!r} is absent. Remove that word and its plurals from "
                          f"the caption and narration. Only {prop!r} can be the featured object.")
        if all(isinstance(scene.get(k), str) for k in ("setting", "action", "shot", "prop")):
            valid.append(scene)

    actions = {s["action"] for s in valid}
    shots = {s["shot"] for s in valid}
    settings = {s["setting"] for s in valid}
    if len(actions) < 3:
        issues.append("Fewer than 3 distinct character actions")
    if len(shots) < 2:
        issues.append("Camera composition is repeated throughout the episode")
    if len(settings) == 1:
        notes.append("One continuous setting")
    compositions = Counter((s["setting"], s["shot"]) for s in valid)
    if valid and max(compositions.values()) > len(valid) // 2:
        issues.append("The majority of scenes repeat an identical camera composition")
    full_plot = str(episode.get("title", "")) + " " + str(episode.get("description", ""))
    for obj in sorted(_objects(full_plot) - {s["prop"] for s in valid}):
        issues.append(f"Title/plot object {obj!r} has no visual representation. Remove that object "
                      "from the title and description and center the plot on its staged prop.")

    return {"ok": not issues, "issues": issues, "notes": notes,
            "distinct_actions": len(actions), "distinct_shots": len(shots),
            "distinct_settings": len(settings), "publication_approved": False,
            "artistic_quality_verified": False}


def publication_gate(*, mechanical_passed: bool, visual_contract_passed: bool,
                     assets_approved: bool, human_review_signed: bool,
                     provenance_checked: bool, animation_method: str) -> dict[str, Any]:
    """Conservative release recommendation, not an upload call."""
    missing = []
    for ok, label in [
        (mechanical_passed, "mechanical QA"),
        (visual_contract_passed, "storyboard/visual correspondence"),
        (assets_approved, "licensed character/background assets"),
        (human_review_signed, "explicit human creative approval"),
        (provenance_checked, "originality and asset provenance")
    ]:
        if not ok:
            missing.append(label)
    if animation_method != "approved_character_rig":
        missing.append("approved rig-based animation renderer (not legacy procedural clip-art)")
    return {"ready_for_manual_publication_review": not missing, "missing": missing,
            "automatically_uploaded": False}
