from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from .local_ai_runtime import BASE_URL, acquire, release

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DEFAULT_TIMEOUT = float(os.getenv("JARVIS_CLAUDE_TIMEOUT", "420"))

def find_claude() -> str | None:
    for name in ("claude", "claude.exe", "claude.cmd"):
        found = shutil.which(name)
        if found:
            return found
    # WinGet native fallback.
    p = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links/claude.exe"
    return str(p) if p.exists() else None

def local_env(model: str) -> dict[str, str]:
    env = dict(os.environ)
    env["ANTHROPIC_BASE_URL"] = BASE_URL
    env["ANTHROPIC_AUTH_TOKEN"] = env.get("LM_API_TOKEN", "lmstudio")
    env["CLAUDE_CODE_ATTRIBUTION_HEADER"] = "0"
    env["ANTHROPIC_MODEL"] = model
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
    # The local path must never silently spend Anthropic API money.
    env.pop("ANTHROPIC_API_KEY", None)
    return env

def health() -> dict:
    exe = find_claude()
    return {
        "ok": bool(exe),
        "claude": exe,
        "runtime_mode": "on-demand",
        "server_required_per_task": True,
        "qwen": "qwen/qwen3.5-9b",
        "gemma": "google/gemma-4-e4b",
        "base_url": BASE_URL,
    }

def run_claude(
    prompt: str,
    *,
    cwd: str | Path,
    mode: str = "plan",
    model_kind: str = "qwen",
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    exe = find_claude()
    if not exe:
        raise RuntimeError("Claude Code CLI not found.")

    lease = acquire(model_kind)
    try:
        cmd = [
            exe,
            "-p", prompt,
            "--model", lease.model,
            "--output-format", "json",
        ]
        if mode == "plan":
            cmd += ["--permission-mode", "plan"]
        elif mode == "edit":
            cmd += ["--permission-mode", "acceptEdits"]
        elif mode != "default":
            raise ValueError(f"Unknown Claude mode: {mode}")

        cp = subprocess.run(
            cmd,
            cwd=str(Path(cwd).resolve()),
            env=local_env(lease.model),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    finally:
        release(lease)

    raw = (cp.stdout or "").strip()
    parsed = None
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        pass

    text = ""
    if isinstance(parsed, dict):
        for k in ("result", "text", "message"):
            v = parsed.get(k)
            if isinstance(v, str) and v.strip():
                text = v.strip()
                break
    if not text:
        text = raw

    return {
        "ok": cp.returncode == 0,
        "provider": "claude-code-local",
        "model": lease.model,
        "model_kind": model_kind,
        "text": text,
        "stderr": (cp.stderr or "").strip(),
        "returncode": cp.returncode,
        "mode": mode,
        "runtime_mode": "on-demand",
    }
