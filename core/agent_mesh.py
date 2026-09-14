from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentProfile:
    id: str
    name: str
    domain: str
    keywords: tuple[str, ...] = ()
    heavy: bool = False


# 47 specialist identities.  They DO NOT mean 47 model copies.  v27 routes a
# request to a small subset of these profiles while all of them share the same
# local LM Studio model and controlled tool boundary.
_PROFILES = [
    AgentProfile("orchestrator", "Orchestrator", "core"),
    AgentProfile("research", "Research", "research", ("research", "investigate", "compare", "find", "sources"), True),
    AgentProfile("verification", "Verifier", "research", ("verify", "fact check", "source", "evidence")),
    AgentProfile("news", "News", "intelligence", ("news", "today", "latest", "breaking")),
    AgentProfile("israel", "Israel", "intelligence", ("israel", "idf", "tel aviv", "jerusalem")),
    AgentProfile("world", "World", "intelligence", ("world", "global", "international")),
    AgentProfile("football", "Football", "sports", ("football", "soccer", "premier league", "laliga", "serie a")),
    AgentProfile("champions", "Champions League", "sports", ("champions league", "uefa")),
    AgentProfile("f1", "Formula 1", "sports", ("formula 1", "formula one", "f1", "grand prix")),
    AgentProfile("travel", "Travel", "personal", ("travel", "trip", "hotel", "flight", "train", "tour")),
    AgentProfile("calendar", "Calendar", "personal", ("calendar", "schedule", "appointment", "meeting")),
    AgentProfile("phone", "Phone / Call Agent", "device", ("phone", "android", "samsung", "tailscale", "call", "dial", "contact")),
    AgentProfile("windows", "Windows", "device", ("windows", "desktop", "pc", "computer")),
    AgentProfile("surface", "Surface Manager", "ui", ("layout", "panel", "workspace", "bring up", "show me", "dock")),
    AgentProfile("vision", "Vision", "perception", ("camera", "see", "image", "photo", "look at"), True),
    AgentProfile("voice", "Voice", "perception", ("voice", "microphone", "wake word", "speech")),
    AgentProfile("files", "Files", "productivity", ("file", "folder", "document")),
    AgentProfile("coding", "Coding JARVIS", "engineering", ("code", "coding", "python", "javascript", "github", "programming", "repo", "patch", "commit"), True),
    AgentProfile("debug", "Debugger", "engineering", ("error", "bug", "traceback", "failed", "fix"), True),
    AgentProfile("security", "Security", "engineering", ("security", "permission", "privacy", "safe")),
    AgentProfile("memory", "Memory", "core", ("remember", "memory", "preference")),
    AgentProfile("planning", "Planner", "core", ("plan", "roadmap", "steps", "project")),
    AgentProfile("weather", "Weather", "intelligence", ("weather", "rain", "temperature", "forecast")),
    AgentProfile("shopping", "Shopping", "personal", ("buy", "price", "shop", "purchase", "product")),
    AgentProfile("finance", "Finance", "personal", ("market", "stock", "finance", "money")),
    AgentProfile("health", "Health", "personal", ("health", "medical", "doctor", "medicine")),
    AgentProfile("music", "Music", "culture", ("music", "instrument", "song")),
    AgentProfile("film", "Film", "culture", ("movie", "film", "cinema")),
    AgentProfile("learning", "Learning", "education", ("teach", "learn", "explain", "lesson")),
    AgentProfile("math", "Math", "education", ("calculate", "math", "equation")),
    AgentProfile("science", "Science", "education", ("science", "physics", "chemistry", "biology")),
    AgentProfile("history", "History", "education", ("history", "historical", "since", "timeline")),
    AgentProfile("translation", "Translation", "language", ("translate", "hebrew", "english")),
    AgentProfile("writing", "Writing", "language", ("write", "rewrite", "email", "letter")),
    AgentProfile("summary", "Summarizer", "language", ("summarize", "summary", "brief")),
    AgentProfile("automation", "Automation", "productivity", ("automate", "remind", "recurring", "monitor")),
    AgentProfile("browser", "Browser", "web", ("website", "browser", "web", ".com")),
    AgentProfile("web_reader", "Web Reader", "web", ("article", "page", "read this")),
    AgentProfile("source_ranker", "Source Ranker", "web", ("reliable", "credible", "best source")),
    AgentProfile("performance", "Performance", "system", ("performance", "ram", "cpu", "gpu", "vram")),
    AgentProfile("resource_guard", "Resource Guard", "system", ("overheat", "temperature", "crash", "burn")),
    AgentProfile("services", "Runtime Services", "system", ("docker", "lm studio", "searxng", "service")),
    AgentProfile("network", "Network", "system", ("network", "internet", "wifi", "dns", "vpn")),
    AgentProfile("phone_calendar", "Phone Calendar", "device", ("native calendar", "samsung calendar")),
    AgentProfile("presentation", "Presentation", "ui", ("present", "visualize", "display", "interface")),
    AgentProfile("critic", "Critic", "core", ("critique", "review", "improve")),
    AgentProfile("safety", "Safety", "core", ("risk", "danger", "permission")),
]

assert len(_PROFILES) == 47


class AgentMesh:
    def __init__(self, config) -> None:
        self.config = config
        self._active: list[str] = []
        self._last_query = ""

    @property
    def profiles(self) -> tuple[AgentProfile, ...]:
        return tuple(_PROFILES)

    def route(self, text: str, resource: dict[str, Any] | None = None) -> dict[str, Any]:
        lowered = (text or "").lower()
        limit = max(2, min(8, int(getattr(self.config, "agent_max_active_specialists", 6))))
        if resource:
            limit = min(limit, int(resource.get("active_agent_limit") or limit))

        scores: list[tuple[int, AgentProfile]] = []
        for profile in _PROFILES[1:]:
            score = sum(2 if " " in kw else 1 for kw in profile.keywords if kw in lowered)
            if score:
                scores.append((score, profile))
        scores.sort(key=lambda item: (-item[0], item[1].name))

        chosen = ["orchestrator"]
        for _, profile in scores:
            if profile.id not in chosen:
                chosen.append(profile.id)
            if len(chosen) >= limit:
                break
        if len(chosen) == 1:
            chosen.extend(["planning"] if len(text.split()) > 12 else [])
        self._active = chosen
        self._last_query = text[:240]
        return self.snapshot(resource=resource, phase="routing")

    def complete(self, resource: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = self.snapshot(resource=resource, phase="complete")
        self._active = []
        return payload

    def snapshot(self, resource: dict[str, Any] | None = None, phase: str = "idle") -> dict[str, Any]:
        active_set = set(self._active)
        return {
            "registered": len(_PROFILES),
            "active": list(self._active),
            "phase": phase,
            "last_query": self._last_query,
            "shared_model": str(getattr(self.config, "ai_model_name", "jarvis-qwen")),
            "max_parallel_llm": max(1, min(2, int(getattr(self.config, "agent_max_parallel_llm", 2)))),
            "profiles": [
                {**asdict(p), "status": "active" if p.id in active_set else "standby"}
                for p in _PROFILES
            ],
            "resource": resource or {},
        }
