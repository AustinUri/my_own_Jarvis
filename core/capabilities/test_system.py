from __future__ import annotations

import json
import sys
from pathlib import Path

from core.capabilities.registry import CAPABILITIES
from core.capabilities.router import route_capabilities
from core.capabilities.status import capability_state


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / ".jarvis" / "skill-fabric" / "packs" / "_skill-index.json"

failures = []


def check(condition: bool, message: str):
    if condition:
        print(f"PASS  {message}")
    else:
        print(f"FAIL  {message}")
        failures.append(message)


print("=" * 72)
print("JARVIS CAPABILITY FABRIC SMOKE TEST")
print("=" * 72)

print("\n[1] Registry")

check(len(CAPABILITIES) >= 15, f"registry contains {len(CAPABILITIES)} capabilities")

for name in (
    "superpowers",
    "ponytail",
    "grill-me",
    "ui-ux-pro-max",
    "impeccable",
    "anti-slop",
    "diagram-design",
    "marketing-skills",
    "humanizer",
    "agent-browser",
    "claude-mem",
    "caveman",
):
    check(name in CAPABILITIES, f"{name} registered")


print("\n[2] Capability states")

expected_states = {
    "superpowers": "ready",
    "ponytail": "ready",
    "grill-me": "ready",
    "ui-ux-pro-max": "ready",
    "impeccable": "ready",
    "anti-slop": "ready",
    "diagram-design": "ready",
    "marketing-skills": "ready",
    "pricing-strategy": "ready",
    "humanizer": "ready",

    "last30days": "setup-required",
    "agent-browser": "setup-required",
    "video-lens": "setup-required",
    "seo-audit": "setup-required",
    "claude-mem": "setup-required",

    "caveman": "disabled",
    "t3code": "disabled",
    "openmausbot": "disabled",
    "astryx": "disabled",
    "sure": "disabled",
}

for name, expected in expected_states.items():
    actual = capability_state(name)
    check(
        actual == expected,
        f"{name}: expected={expected}, actual={actual}",
    )


print("\n[3] Routing")

routing_tests = [
    (
        "Debug this Python service and fix the failing test",
        "coding",
        "superpowers",
    ),
    (
        "Redesign the Jarvis dashboard UI",
        "ui",
        "ui-ux-pro-max",
    ),
    (
        "Research the latest AI coding tools",
        "research",
        "last30days",
    ),
    (
        "Create an SEO and pricing strategy",
        "marketing",
        "marketing-skills",
    ),
    (
        "Review the agent runtime architecture",
        "architecture",
        "superpowers",
    ),
    (
        "Rewrite this article so it sounds natural",
        "writing",
        "humanizer",
    ),
]

for prompt, expected_domain, expected_capability in routing_tests:
    route = route_capabilities(prompt)

    check(
        route.domain == expected_domain,
        f'route "{prompt}" -> {route.domain}',
    )

    check(
        expected_capability in route.capabilities,
        f"{expected_capability} selected for {expected_domain}",
    )


print("\n[4] Skill harvest")

check(INDEX.exists(), "_skill-index.json exists")

if INDEX.exists():
    try:
        data = json.loads(INDEX.read_text(encoding="utf-8"))

        check(
            isinstance(data, list),
            "skill index is a JSON list",
        )

        check(
            len(data) >= 100,
            f"skill index contains {len(data)} harvested skills",
        )

        sources = {
            item.get("source")
            for item in data
            if isinstance(item, dict)
        }

        for source in (
            "superpowers",
            "marketing-skills",
            "ui-ux-pro-max",
            "anti-slop",
            "impeccable",
        ):
            check(
                source in sources,
                f"{source} present in harvested index",
            )

    except Exception as exc:
        check(False, f"skill index readable: {exc}")


print("\n[5] Local pack integrity")

for name, capability in CAPABILITIES.items():
    if capability.local_path is None:
        continue

    if capability_state(name) == "disabled":
        continue

    check(
        capability.local_path.exists(),
        f"{name} local pack exists",
    )


print("\n" + "=" * 72)

if failures:
    print(f"RESULT: FAIL ({len(failures)} problem(s))")
    print("=" * 72)

    for item in failures:
        print(f"- {item}")

    sys.exit(1)

print("RESULT: PASS")
print("Capability Fabric foundation is healthy.")
print("=" * 72)
