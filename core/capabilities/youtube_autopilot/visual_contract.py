"""Story-to-screen audit for JARVIS Kids Video Factory.

Mechanical checks only: the result is never an artistic approval.
No network, no uploads, and no writes. Standard library only.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
import re

VERSION = "0.5.0"

# Objects critical enough that they must be visible when central to the plot.
# A future renderer can declare objects via scene['visible_objects'] as well as
# scene['prop']. Until then, unsupported assets create a review blocker.
PLOT_OBJECTS = {
    "lantern": {"lantern"}, "moth": {"moth"},
    "butterfly": {"butterfly"}, "kite": {"kite"},
    "snail": {"snail"}, "apple": {"apple"},
    "balloon": {"balloon"}, "acorn": {"acorn"},
    "boat": {"boat", "leaf-boat"}, "pebble": {"pebble"},
    "bubble": {"bubble"}, "rainbow": {"rainbow"},
    "dragonfly": {"dragonfly"}, "frog": {"frog"},
}


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", str(value).lower()))


def _visible(scene: dict[str, Any]) -> set[str]:
    props = {str(scene.get("prop", "")).lower()}
    declared = scene.get("visible_objects", [])
    if isinstance(declared, list):
        props |= {str(item).lower() for item in declared}
    return props


def audit_storyboard(episode: dict[str, Any]) -> dict[str, Any]:
    """Return blocking content/visual issues and non-blocking observations.

    This does not run an LLM, doesn't trust a numeric motion score, and never
    treats missing story objects as successfully animated.
    """
    issues: list[str] = []
    notes: list[str] = []
    scenes = episode.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 4:
        return {"ok": False, "issues": ["At least four storyboard scenes required"], "notes": []}
    for i, s in enumerate(scenes, 1):
        if not isinstance(s, dict):
            issues.append(f"scene {i}: invalid scene object")
            continue
        for field in ("narration", "setting", "shot", "action", "prop"):
            if not isinstance(s.get(field), str) or not s[field].strip():
                issues.append(f"scene {i}: missing {field}")
    if issues:
        return {"ok": False, "issues": issues, "notes": notes}

    distinct_actions = len(set(s["action"] for s in scenes))
    distinct_shots = len(set(s["shot"] for s in scenes))
    distinct_settings = len(set(s["setting"] for s in scenes))
    if distinct_actions < 3:
        issues.append("Fewer than 3 distinct character actions")
    if distinct_shots < 2:
        issues.append("Camera composition is repeated throughout the episode")
    if distinct_settings < 2:
        notes.append("Only one setting used; verify that this serves the story")
    signatures = Counter((s["setting"], s["action"], s["shot"], s["prop"]) for s in scenes)
    if max(signatures.values()) > len(scenes) // 2:
        issues.append("The majority of shots repeat an identical visual plan")

    full_plot = _words(str(episode.get("title", "")) + " " + str(episode.get("description", "")))
    critical = {name for name in PLOT_OBJECTS if name in full_plot}
    all_visible = set().union(*(_visible(s) for s in scenes))
    for noun in sorted(critical):
        if not (PLOT_OBJECTS[noun] & all_visible):
            issues.append(f"Title/plot object '{noun}' has no visual representation in storyboard")

    # Check scene-specific nouns so an episode can't mention a character or prop
    # without any indication how it will appear in the corresponding shot.
    for i, scene in enumerate(scenes, 1):
        nouns = _words(scene["narration"])
        missing = [noun for noun in PLOT_OBJECTS if noun in nouns and not (PLOT_OBJECTS[noun] & _visible(scene))]
        if missing:
            notes.append(f"scene {i}: narration mentions {', '.join(sorted(missing))}; verify object appears")

    return {
        "ok": not issues,
        "issues": issues,
        "notes": notes,
        "distinct_actions": distinct_actions,
        "distinct_shots": distinct_shots,
        "distinct_settings": distinct_settings,
        "publication_approved": False,
        "artistic_quality_verified": False,
    }


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
