from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CapabilityRoute:
    domain: str
    capabilities: tuple[str, ...]
    reason: str


ROUTES = {
    "video-production": (
        "youtube-video-factory",
        "video-lens",
    ),
    "website-production": (
        "website-factory",
        "ui-ux-pro-max",
        "anti-slop",
    ),
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
    "video-production": {
        "youtube video", "youtube shorts", "cartoon", "animation", "animated video",
        "video factory", "video autopilot", "create a video", "generate video",
        "produce a video", "nori", "blink", "אנימציה", "סרטון", "סרטונים",
        "יוטיוב", "פרק מצויר", "סרטוני ילדים",
    },
    "website-production": {
        "build a website", "create a website", "make a website", "website factory",
        "business website", "react website", "website demo", "generate website",
        "lead discovery", "אתר לעסק", "אתר אינטרנט", "בניית אתר", "תבנה אתר",
        "בנה אתר", "צור אתר", "דמו לאתר",
    },
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

    # Explicit creation intents beat generic matches like 'website' (research)
    # and 'design' (UI). This only SELECTS a capability; it does NOT execute it.
    specialist_domains = ("video-production", "website-production")
    domain = next(
        (key for key in specialist_domains if scores[key] > 0),
        max(scores, key=scores.get),
    )

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
