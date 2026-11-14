from __future__ import annotations

import os

from .device_bus import device_manager

WINDOWS_DEVICE_ID = os.getenv("JARVIS_WINDOWS_DEVICE_ID", "uri-windows")

KEYWORDS = (
    "claude", "קלוד",
    "code review", "code tutor",
    "בדוק את הקוד", "תבדוק את הקוד",
    "למד אותי את הקוד", "תלמד אותי את הקוד",
    "ארכיטקטורת הקוד", "מבנה הקוד",
)

def _explicit(text: str) -> bool:
    low = (text or "").strip().lower()
    return any(k.lower() in low for k in KEYWORDS)

def _mode(text: str) -> str:
    low = (text or "").lower()
    if any(x in low for x in ("למד", "תלמד", "תסביר", "explain", "teach", "tutor")):
        return "tutor"
    if any(x in low for x in ("ארכיטקט", "מבנה", "architecture", "map the code")):
        return "architecture"
    if any(x in low for x in ("תתקן", "שנה את הקוד", "fix", "refactor", "implement")):
        return "fix"
    if any(x in low for x in ("בדיקות", "tests", "verify")):
        return "test"
    return "review"

async def try_handle_claude_skill(text: str, source_device: str) -> dict | None:
    if not _explicit(text):
        return None

    if not device_manager.is_connected(WINDOWS_DEVICE_ID):
        return {
            "ok": False,
            "provider": "claude-code-local",
            "route": "windows",
            "text": (
                "Claude Code Local needs the Windows JARVIS worker and LM Studio online. "
                "Normal Oracle JARVIS is still available."
            ),
            "skill": _mode(text),
            "source_device": source_device,
        }

    try:
        result = await device_manager.request(
            WINDOWS_DEVICE_ID,
            "claude_code",
            {
                "text": text,
                "mode": _mode(text),
                "remote": source_device != WINDOWS_DEVICE_ID,
                "source_device": source_device,
                "model": "dual" if any(x in text.lower() for x in ("עם שניהם", "both models", "dual")) else ("gemma" if any(x in text.lower() for x in ("gemma", "גמה")) else ("qwen" if any(x in text.lower() for x in ("qwen", "קוון", "קווין")) else "auto")),
            },
            timeout=420.0,
        )
    except Exception as exc:
        return {
            "ok": False,
            "provider": "claude-code-local",
            "route": "windows",
            "text": f"Claude Code Local failed: {exc}",
            "skill": _mode(text),
            "source_device": source_device,
        }

    answer = str(result.get("text") or result.get("error") or "").strip()
    return {
        "ok": bool(result.get("ok")),
        "provider": "claude-code-local",
        "model": result.get("model"),
        "route": "windows",
        "text": answer or "Claude Code Local returned no text.",
        "skill": result.get("skill") or _mode(text),
        "source_device": source_device,
    }
