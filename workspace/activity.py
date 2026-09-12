from __future__ import annotations

import re
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class ActivityEvent:
    seq: int
    timestamp: str
    category: str
    status: str
    title: str
    detail: str = ""
    source: str = "runtime"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ActivityTimeline:
    """Ordered, structured activity feed for the Control Center.

    Raw runtime log text is still retained separately for diagnostics.  This
    timeline is the human-readable execution trace: input -> reasoning -> tool
    -> source/research -> output, with stable sequence numbers and timestamps.
    """

    def __init__(self, max_events: int = 400) -> None:
        self.max_events = max(50, int(max_events))
        self._seq = 0
        self._events: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def add(
        self,
        category: str,
        title: str,
        detail: str = "",
        *,
        status: str = "info",
        source: str = "runtime",
    ) -> dict[str, Any]:
        with self._lock:
            self._seq += 1
            event = ActivityEvent(
                seq=self._seq,
                timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
                category=(category or "system").lower(),
                status=(status or "info").lower(),
                title=(title or "Activity").strip()[:180],
                detail=(detail or "").strip()[:1800],
                source=(source or "runtime").strip()[:48],
            ).to_dict()
            self._events.append(event)
            self._events = self._events[-self.max_events :]
            return dict(event)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(x) for x in self._events]

    def from_log(self, message: str) -> dict[str, Any]:
        text = str(message or "").strip()
        low = text.lower()
        if not text:
            return self.add("system", "Runtime event")

        if low.startswith("tool denied:"):
            name, _, reason = text.partition("—")
            return self.add("tool", name.strip(), reason.strip(), status="denied", source="policy")
        if low.startswith("tool requested:"):
            return self.add("tool", "Tool requested", text.split(":", 1)[1].strip(), status="start", source="agent")
        if low.startswith("tool complete:") or low.startswith("tool completed:"):
            return self.add("tool", "Tool completed", text.split(":", 1)[1].strip(), status="success", source="agent")
        if low.startswith("tool:"):
            return self.add("tool", "Tool completed", text.split(":", 1)[1].strip(), status="success", source="agent")
        if low.startswith("agent:"):
            return self.add("reasoning", "Agent", text.split(":", 1)[1].strip(), status="working", source="agent")
        if "daily briefing:" in low:
            return self.add("research", "Daily briefing", text.split(":", 1)[1].strip(), status="working", source="briefing")
        if "searxng" in low or "web search" in low or "web research" in low:
            status = "success" if any(x in low for x in ("online", "ready", "complete", "result")) else "working"
            if any(x in low for x in ("warning", "failed", "unavailable", "error")):
                status = "warning"
            return self.add("web", "Web research", text, status=status, source="web")
        if "phone" in low or "tailscale" in low:
            status = "success" if any(x in low for x in ("paired", "connected", "ready", "serve configured")) else "info"
            if any(x in low for x in ("revoked", "failed", "error", "warning")):
                status = "warning"
            return self.add("phone", "Phone link", text, status=status, source="phone")
        if "camera" in low or "vision" in low:
            status = "warning" if any(x in low for x in ("failed", "error", "warning")) else "info"
            return self.add("vision", "Vision", text, status=status, source="vision")
        if "lm studio" in low or "docker" in low or "service manager" in low or "wake runtime" in low:
            status = "warning" if any(x in low for x in ("warning", "failed", "not installed", "unavailable")) else "info"
            if any(x in low for x in ("online", "armed", "loaded", "started")):
                status = "success"
            return self.add("system", "Runtime service", text, status=status, source="system")
        if "error" in low or "failed" in low:
            return self.add("error", "Runtime error", text, status="error", source="runtime")
        if "warning" in low:
            return self.add("system", "Runtime warning", text, status="warning", source="runtime")
        return self.add("system", "Runtime", text, status="info", source="runtime")

    def input(self, text: str, source: str = "user") -> dict[str, Any]:
        return self.add("input", "User request", text, status="received", source=source)

    def output(self, text: str) -> dict[str, Any]:
        compact = re.sub(r"\s+", " ", str(text or "")).strip()
        return self.add("output", "Jarvis response", compact[:1000], status="success", source="agent")

    def state(self, value: str) -> dict[str, Any] | None:
        state = str(value or "").strip()
        if not state:
            return None
        mapping = {
            "Listening": ("input", "Listening", "working"),
            "Transcribing": ("input", "Transcribing speech", "working"),
            "Thinking": ("reasoning", "Reasoning", "working"),
            "Speaking": ("output", "Speaking", "working"),
            "Error": ("error", "Assistant error state", "error"),
        }
        item = mapping.get(state)
        if item is None:
            return None
        category, title, status = item
        return self.add(category, title, status=status, source="runtime")
