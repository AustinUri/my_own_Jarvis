from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.user_paths import jarvis_data_dir

REPO_URL = "https://github.com/AustinUri/home-mech-engin.git"
REPO_NAME = "home-mech-engin"
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".py", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".html", ".css", ".toml", ".ini", ".xml", ".tex", ".rst"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", ".gradle", "__pycache__", ".idea"}
MAX_FILE_BYTES = 750_000
MAX_CONTEXT_CHARS = 7000


@dataclass
class LessonSource:
    title: str
    path: str
    text: str
    score: float = 0.0


class MechanicalEngineeringLearningService:
    """Local-first teaching bridge for AustinUri/home-mech-engin.

    The course repository is public, so synchronization uses normal Git and no
    cloud AI/API keys. JARVIS only hands selected repository context to its
    existing local LM Studio model for teaching, review and quizzes.
    """

    def __init__(self) -> None:
        self.data_root = jarvis_data_dir() / "learning"
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.managed_repo = self.data_root / REPO_NAME
        self.progress_path = self.data_root / "mechanical_engineering_progress.json"

    def _desktop_candidate(self) -> Path:
        return Path.home() / "Desktop" / REPO_NAME

    def repo_path(self) -> Path:
        local = self._desktop_candidate()
        if (local / ".git").exists() or (local / "README.md").exists():
            return local
        return self.managed_repo

    def _git(self, args: list[str], cwd: Path | None = None, timeout: int = 90) -> str:
        git = shutil.which("git")
        if not git:
            raise RuntimeError("Git is not installed or not available on PATH.")
        cp = subprocess.run(
            [git, *args], cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if cp.returncode != 0:
            raise RuntimeError(cp.stdout.strip() or f"git {' '.join(args)} failed")
        return cp.stdout.strip()

    def sync(self) -> dict[str, Any]:
        path = self.repo_path()
        try:
            if (path / ".git").exists():
                output = self._git(["pull", "--ff-only"], cwd=path)
                action = "updated"
            else:
                if path.exists() and any(path.iterdir()):
                    raise RuntimeError(f"Learning folder exists but is not a Git repository: {path}")
                path.parent.mkdir(parents=True, exist_ok=True)
                self._git(["clone", "--depth", "1", REPO_URL, str(path)], timeout=150)
                output = "Repository cloned."
                action = "cloned"
            status = self.status()
            status.update({"ok": True, "action": action, "detail": output[-1000:]})
            return status
        except Exception as exc:
            return {"ok": False, "repo_url": REPO_URL, "repo_path": str(path), "error": str(exc)}

    def _iter_source_files(self, path: Path):
        if not path.exists():
            return
        for file in path.rglob("*"):
            if not file.is_file() or file.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            try:
                rel_parts = file.relative_to(path).parts
            except Exception:
                rel_parts = file.parts
            if any(part in SKIP_DIRS for part in rel_parts):
                continue
            try:
                if file.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield file

    @staticmethod
    def _clean_text(raw: str) -> str:
        raw = re.sub(r"```[^\n]*\n", "", raw)
        raw = raw.replace("```", "")
        raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
        raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = re.sub(r"\r\n?", "\n", raw)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

    @staticmethod
    def _title_for(file: Path, text: str, root: Path) -> str:
        for line in text.splitlines()[:80]:
            m = re.match(r"^#{1,3}\s+(.+?)\s*$", line.strip())
            if m:
                return m.group(1).strip()[:120]
        stem = file.stem.replace("_", " ").replace("-", " ").strip()
        if stem.lower() in {"readme", "index", "home", "main"}:
            try:
                parent = file.parent.relative_to(root).name
                if parent:
                    stem = parent.replace("_", " ").replace("-", " ")
            except Exception:
                pass
        return stem.title()[:120] or "Mechanical Engineering"

    def _sources(self) -> list[LessonSource]:
        root = self.repo_path()
        out: list[LessonSource] = []
        for file in self._iter_source_files(root) or []:
            try:
                raw = file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            text = self._clean_text(raw)
            if len(text) < 60:
                continue
            rel = str(file.relative_to(root)).replace("\\", "/")
            out.append(LessonSource(self._title_for(file, raw, root), rel, text))
        return out

    def _load_progress(self) -> dict[str, Any]:
        try:
            data = json.loads(self.progress_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {"cursor": 0, "completed": [], "history": []}

    def _save_progress(self, data: dict[str, Any]) -> None:
        self.progress_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        path = self.repo_path()
        available = path.exists()
        files = self._sources() if available else []
        progress = self._load_progress()
        return {
            "ok": True,
            "available": available and bool(files),
            "repo_url": REPO_URL,
            "repo_path": str(path),
            "source_files": len(files),
            "topics": [s.title for s in files[:12]],
            "completed": len(progress.get("completed") or []),
            "message": "Engineering course is ready." if files else "Sync the home-mech-engin course repository to begin.",
        }

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {x for x in re.findall(r"[a-z0-9][a-z0-9+.#_-]{1,}", value.lower()) if len(x) > 2}

    def _rank(self, topic: str, sources: list[LessonSource]) -> list[LessonSource]:
        q = self._tokens(topic)
        if not q:
            return sources
        ranked: list[LessonSource] = []
        for src in sources:
            title_tokens = self._tokens(src.title + " " + src.path)
            body = src.text.lower()[:20000]
            src.score = sum(5 for t in q if t in title_tokens) + sum(min(3, body.count(t)) for t in q)
            ranked.append(src)
        return sorted(ranked, key=lambda s: s.score, reverse=True)

    def lesson(self, topic: str = "", mode: str = "teach") -> dict[str, Any]:
        sources = self._sources()
        if not sources:
            synced = self.sync()
            if not synced.get("ok"):
                return synced
            sources = self._sources()
        if not sources:
            return {"ok": False, "error": "The engineering repository contains no readable lesson sources yet."}

        progress = self._load_progress()
        mode = (mode or "teach").strip().lower()
        if topic.strip():
            ranked = self._rank(topic, sources)
            selected = ranked[:3]
            title = topic.strip()
        else:
            cursor = int(progress.get("cursor") or 0) % len(sources)
            selected = [sources[cursor]]
            title = selected[0].title
            if mode in {"teach", "next"}:
                progress["cursor"] = (cursor + 1) % len(sources)
                completed = list(progress.get("completed") or [])
                if selected[0].path not in completed:
                    completed.append(selected[0].path)
                progress["completed"] = completed[-500:]
                self._save_progress(progress)

        context_parts: list[str] = []
        used = 0
        refs: list[dict[str, str]] = []
        for src in selected:
            allowance = max(800, MAX_CONTEXT_CHARS - used)
            excerpt = src.text[:allowance]
            context_parts.append(f"SOURCE: {src.path}\nTITLE: {src.title}\n{excerpt}")
            refs.append({"title": src.title, "path": src.path})
            used += len(excerpt)
            if used >= MAX_CONTEXT_CHARS:
                break

        instruction = {
            "teach": "Teach this as a mechanical-engineering instructor. Start from first principles, derive the important equations, define units, give one worked example, point out common mistakes, then ask one check-for-understanding question.",
            "next": "Teach this as the next lesson in the user's mechanical-engineering course. Start from first principles, include equations/units and one practical worked example, then ask one short question.",
            "quiz": "Create a short engineering quiz from this material: 4 questions from easy to challenging. Do not reveal answers until the user attempts them.",
            "review": "Give a concise review sheet: concepts, equations, units, assumptions, and two likely exam mistakes.",
        }.get(mode, "Teach this clearly as a mechanical-engineering instructor with equations, units and a practical example.")

        return {
            "ok": True,
            "mode": mode,
            "topic": title,
            "sources": refs,
            "context": "\n\n---\n\n".join(context_parts),
            "instruction": instruction,
            "repo_url": REPO_URL,
            "progress": {"completed": len(progress.get("completed") or []), "cursor": int(progress.get("cursor") or 0)},
        }
