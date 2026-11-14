from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CapabilityRoute:
    domain: str
    capabilities: tuple[str, ...]
    reason: str


ROUTES = {
    "coding": (
        "superpowers",
        "ponytail",
        "grill-me",
    ),
    "ui": (
        "ui-ux-pro-max",
        "impeccable",
        "anti-slop",
        "diagram-design",
    ),
    "research": (
        "last30days",
        "agent-browser",
        "video-lens",
    ),
    "marketing": (
        "marketing-skills",
        "pricing-strategy",
        "seo-audit",
        "humanizer",
    ),
    "writing": (
        "humanizer",
        "anti-slop",
    ),
    "architecture": (
        "superpowers",
        "grill-me",
        "diagram-design",
        "ponytail",
    ),
}


KEYWORDS = {
    "coding": {
        "code",
        "python",
        "javascript",
        "typescript",
        "bug",
        "fix",
        "debug",
        "refactor",
        "test",
        "implement",
        "function",
        "class",
    },
    "ui": {
        "ui",
        "ux",
        "dashboard",
        "design",
        "interface",
        "screen",
        "layout",
        "frontend",
        "react",
        "android ui",
    },
    "research": {
        "research",
        "find",
        "latest",
        "browser",
        "website",
        "youtube",
        "reddit",
        "compare",
    },
    "marketing": {
        "marketing",
        "seo",
        "pricing",
        "conversion",
        "landing page",
        "growth",
        "campaign",
        "content strategy",
    },
    "writing": {
        "rewrite",
        "humanize",
        "copy",
        "email",
        "article",
        "post",
        "description",
    },
    "architecture": {
        "architecture",
        "system design",
        "orchestration",
        "agent",
        "runtime",
        "service",
        "integration",
    },
}


def _score(text: str, keywords: Iterable[str]) -> int:
    text = text.lower()
    return sum(1 for keyword in keywords if keyword in text)


def route_capabilities(
    request: str,
    *,
    max_capabilities: int = 4,
) -> CapabilityRoute:
    scores = {
        domain: _score(request, keywords)
        for domain, keywords in KEYWORDS.items()
    }

    domain = max(scores, key=scores.get)

    if scores[domain] == 0:
        return CapabilityRoute(
            domain="general",
            capabilities=(),
            reason="No specialist capability matched strongly enough.",
        )

    capabilities = ROUTES[domain][:max_capabilities]

    return CapabilityRoute(
        domain=domain,
        capabilities=capabilities,
        reason=f"Matched {scores[domain]} keyword signal(s) for {domain}.",
    )


def available_capabilities(
    route: CapabilityRoute,
) -> tuple[str, ...]:
    from core.capabilities.registry import capability_available

    return tuple(
        name
        for name in route.capabilities
        if capability_available(name)
    )
