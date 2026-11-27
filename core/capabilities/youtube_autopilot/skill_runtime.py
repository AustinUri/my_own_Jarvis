"""First-class JARVIS skill adapter for video creation; DRAFTS ONLY.

Runtime entrypoint: core.capabilities.youtube_autopilot.skill_runtime:execute
Existing youtube_autopilot modules, queue and OAuth records stay untouched.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .manager import root_dir, setup, config, read, dump
from .visual_contract import audit_storyboard, publication_gate

SKILL_ID = "youtube-video-factory"
SKILL_VERSION = "0.6.0"
_ALLOWED_BACKENDS = {"auto", "offline", "local-ai"}


def _existing_draft(root: Path, draft_id: str) -> tuple[dict[str, Any], Path]:
    if not re.fullmatch(r"nori-[0-9a-f]{12}", draft_id):
        raise ValueError("Invalid draft ID")
    path = root / "creative_drafts" / (draft_id + ".json")
    if not path.is_file():
        raise FileNotFoundError(f"Draft not found: {draft_id}")
    return read(path), path


def execute(action: str = "status", *, root: str | Path | None = None,
            backend: str = "auto", render: bool = False,
            draft_id: str | None = None, width: int = 720,
            height: int = 1280, fps: int = 20) -> dict[str, Any]:
    """Invoke from JARVIS router or CLI. No action in this module can publish.

    The module intentionally doesn't import Youtube API or publication queue.
    """
    if action not in {"capabilities", "status", "create-draft", "audit-draft"}:
        raise ValueError("Unknown or disallowed skill action")
    if action == "capabilities":
        return {"id": SKILL_ID, "version": SKILL_VERSION,
                "actions": ["capabilities", "status", "create-draft", "audit-draft"],
                "uploads_allowed": False, "human_approval_required": True}
    home = setup(Path(root) if root else root_dir())
    c = config(home)
    if action == "status":
        drafts = list((home / "creative_drafts").glob("nori-*.json"))
        return {"skill": SKILL_ID, "version": SKILL_VERSION, "draft_count": len(drafts),
                "legacy_autopublish_enabled": bool(c.get("autopublish_enabled")),
                "skill_uploads_enabled": False,
                "local_ai_configured": bool(c.get("lmstudio_model")),
                "next": "create-draft, then audit-draft, then human creative review"}
    if action == "create-draft":
        if backend not in _ALLOWED_BACKENDS:
            raise ValueError("Invalid story backend")
        if width < 240 or height < 420 or width % 2 or height % 2 or fps not in range(5, 31):
            raise ValueError("Unsupported render dimensions/FPS")
        from .creative_factory import create_story, render_draft
        ep, path = create_story(home, backend=backend)
        contract = audit_storyboard(ep)
        result: dict[str, Any] = {"skill": SKILL_ID, "id": ep["id"],
                                 "title": ep["title"], "story": str(path),
                                 "backend": ep.get("creative", {}).get("backend"),
                                 "storyboard_audit": contract, "uploaded": False,
                                 "state": "draft_needs_visual_review"}
        if render:
            # Production-stage visuals remain drafts even if render succeeds.
            rendered = render_draft(ep, home, width=width, height=height, fps=fps)
            result["render"] = {key: value for key, value in rendered.items() if key != "timeline"}
            result["state"] = "render_rejected" if rendered.get("mechanical_qa_error") else "rendered_for_review"
        return result
    if not draft_id:
        raise ValueError("audit-draft requires draft_id")
    ep, _ = _existing_draft(home, draft_id)
    storyboard = audit_storyboard(ep)
    renders = home / "creative_drafts" / "renders"
    review = read(renders / f"{draft_id}.review.json", {}) or {}
    movie = renders / f"{draft_id}.mp4"
    if review.get("animation_method") == "storybook_rig":
        from .quality import inspect_draft_render
        from .creative_factory import story_digest
        from subprocess import SubprocessError
        try:
            if story_digest(ep) != review.get("story_digest"):
                raise ValueError("Storyboard changed since this movie was rendered")
            review["mechanical_qa"] = inspect_draft_render(movie, ep, review["timeline"], review["fps"])
            review.pop("mechanical_qa_error", None)
        except (KeyError, ValueError, RuntimeError, OSError, SubprocessError) as exc:
            review.pop("mechanical_qa", None)
            review["mechanical_qa_error"] = str(exc)
    gate = publication_gate(
        mechanical_passed=movie.is_file() and "mechanical_qa" in review and not review.get("mechanical_qa_error"),
        visual_contract_passed=bool(storyboard["ok"]),
        assets_approved=False, human_review_signed=False,
        provenance_checked=False, animation_method=review.get("animation_method", "legacy_procedural"))
    review.pop("timeline", None)
    report = {"skill": SKILL_ID, "draft_id": draft_id, "storyboard": storyboard,
              "render_report": review, "release_gate": gate, "uploaded": False}
    dump(home / "creative_drafts" / "reports" / f"{draft_id}.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="JARVIS local animated episode drafts")
    parser.add_argument("action", choices=["capabilities", "status", "create-draft", "audit-draft"])
    parser.add_argument("--root", type=Path)
    parser.add_argument("--backend", choices=sorted(_ALLOWED_BACKENDS), default="auto")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--draft-id")
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    parser.add_argument("--fps", type=int, default=20)
    args = parser.parse_args(argv)
    data = execute(args.action, root=args.root, backend=args.backend,
                   render=args.render, draft_id=args.draft_id,
                   width=args.width, height=args.height, fps=args.fps)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if args.action == "audit-draft":
        return int(not data["storyboard"]["ok"] or bool(data["render_report"].get("mechanical_qa_error")))
    return int(data.get("state") == "render_rejected")


if __name__ == "__main__":
    raise SystemExit(main())
