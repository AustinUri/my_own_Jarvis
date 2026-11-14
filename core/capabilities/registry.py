from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


CapabilityType = Literal[
    "skill",
    "runtime",
    "service",
    "architecture",
]

LoadMode = Literal[
    "always",
    "on-demand",
    "manual",
]

TrustLevel = Literal[
    "trusted",
    "reviewed",
    "quarantined",
]


@dataclass(frozen=True)
class Capability:
    name: str
    kind: CapabilityType
    source: str
    local_path: Path | None
    load_mode: LoadMode
    trust: TrustLevel
    enabled: bool = True
    dependencies: tuple[str, ...] = ()


ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / ".jarvis" / "skill-fabric" / "packs"


CAPABILITIES: dict[str, Capability] = {
    "superpowers": Capability(
        name="superpowers",
        kind="skill",
        source="obra/superpowers-skills",
        local_path=PACKS / "superpowers",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "ponytail": Capability(
        name="ponytail",
        kind="skill",
        source="DietrichGebert/ponytail",
        local_path=PACKS / "ponytail",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "grill-me": Capability(
        name="grill-me",
        kind="skill",
        source="RobMitt/grill-me-skill",
        local_path=PACKS / "grill-me",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "ui-ux-pro-max": Capability(
        name="ui-ux-pro-max",
        kind="skill",
        source="nextlevelbuilder/ui-ux-pro-max-skill",
        local_path=PACKS / "ui-ux-pro-max",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "impeccable": Capability(
        name="impeccable",
        kind="skill",
        source="pbakaus/impeccable",
        local_path=PACKS / "impeccable",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "anti-slop": Capability(
        name="anti-slop",
        kind="skill",
        source="miqdadbadjuber/anti-slop",
        local_path=PACKS / "anti-slop",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "diagram-design": Capability(
        name="diagram-design",
        kind="skill",
        source="cathrynlavery/diagram-design",
        local_path=PACKS / "diagram-design",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "last30days": Capability(
        name="last30days",
        kind="skill",
        source="mvanhorn/last30days-skill",
        local_path=PACKS / "last30days",
        load_mode="manual",
        trust="reviewed",
    ),

    "video-lens": Capability(
        name="video-lens",
        kind="skill",
        source="kar2phi/video-lens",
        local_path=PACKS / "video-lens",
        load_mode="manual",
        trust="reviewed",
    ),

    "marketing-skills": Capability(
        name="marketing-skills",
        kind="skill",
        source="coreyhaines31/marketingskills",
        local_path=PACKS / "marketing-skills",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "pricing-strategy": Capability(
        name="pricing-strategy",
        kind="skill",
        source="mohitagw15856/pm-claude-skills",
        local_path=PACKS / "pricing-strategy",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "seo-audit": Capability(
        name="seo-audit",
        kind="runtime",
        source="seo-skills/seo-audit-skill",
        local_path=PACKS / "seo-audit",
        load_mode="manual",
        trust="reviewed",
    ),

    "humanizer": Capability(
        name="humanizer",
        kind="skill",
        source="blader/humanizer",
        local_path=PACKS / "humanizer",
        load_mode="on-demand",
        trust="reviewed",
    ),

    "agent-browser": Capability(
        name="agent-browser",
        kind="runtime",
        source="vercel-labs/agent-browser",
        local_path=PACKS / "agent-browser",
        load_mode="manual",
        trust="reviewed",
    ),

    "claude-mem": Capability(
        name="claude-mem",
        kind="runtime",
        source="thedotmack/claude-mem",
        local_path=PACKS / "claude-mem",
        load_mode="manual",
        trust="reviewed",
    ),

    "caveman": Capability(
        name="caveman",
        kind="runtime",
        source="JuliusBrussee/caveman",
        local_path=PACKS / "caveman-skills",
        load_mode="manual",
        trust="reviewed",
        enabled=False,
    ),

    "t3code": Capability(
        name="t3code",
        kind="runtime",
        source="pingdotgg/t3code",
        local_path=None,
        load_mode="manual",
        trust="quarantined",
        enabled=False,
    ),

    "openmausbot": Capability(
        name="openmausbot",
        kind="architecture",
        source="milind-soni/OpenMausBot",
        local_path=None,
        load_mode="manual",
        trust="quarantined",
        enabled=False,
    ),

    "astryx": Capability(
        name="astryx",
        kind="architecture",
        source="meta/astryx",
        local_path=None,
        load_mode="manual",
        trust="quarantined",
        enabled=False,
    ),

    "sure": Capability(
        name="sure",
        kind="service",
        source="we-promise/sure",
        local_path=None,
        load_mode="manual",
        trust="quarantined",
        enabled=False,
    ),
}


def get_capability(name: str) -> Capability | None:
    return CAPABILITIES.get(name)


def capability_available(name: str) -> bool:
    capability = get_capability(name)

    if capability is None or not capability.enabled:
        return False

    if capability.local_path is None:
        return False

    return capability.local_path.exists()
