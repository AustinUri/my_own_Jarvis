from __future__ import annotations

from core.capabilities.registry import get_capability


SETUP_REQUIRED = {
    "last30days",
    "video-lens",
    "seo-audit",
    "agent-browser",
    "claude-mem",
}

DISABLED_OR_REFERENCE_ONLY = {
    "caveman",
    "t3code",
    "openmausbot",
    "astryx",
    "sure",
}


def capability_state(name: str) -> str:
    capability = get_capability(name)

    if capability is None:
        return "unknown"

    if not capability.enabled or name in DISABLED_OR_REFERENCE_ONLY:
        return "disabled"

    if capability.local_path is None:
        return "missing"

    if not capability.local_path.exists():
        return "missing"

    if name in SETUP_REQUIRED:
        return "setup-required"

    return "ready"


def capability_ready(name: str) -> bool:
    return capability_state(name) == "ready"
