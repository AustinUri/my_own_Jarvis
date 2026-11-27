"""Named skill combinations. Planning only; nothing is activated or executed."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Stage:
    name: str
    skills: tuple[str, ...]
    gate: str


WEBSITE_FACTORY = (
    Stage("discovery", ("israel-site-scout", "agent-browser", "marketing-skills/prospecting"),
          "Two independent public sources; no website found is not proof of absence; owner outreach requires approval."),
    Stage("strategy", ("marketing-skills/competitor-profiling", "marketing-skills/marketing-psychology"),
          "Verified business details and a specific commercial goal. For an owner automation review, open "
          "skills/website-factory/references/automation-review.html and use the owner's answers."),
    Stage("design", ("ui-ux-pro-max/ui-ux-pro-max", "ui-ux-pro-max/brand", "ui-ux-pro-max/design-system", "impeccable"),
          "Unique client design brief; no generic shared template."),
    Stage("content", ("marketing-skills/copywriting", "humanizer", "anti-slop/antislop-copywriting"),
          "Accurate, natural Hebrew copy without invented claims."),
    Stage("development", ("ponytail", "anti-slop/antislop-code"),
          "Claude builds the approved site; no extra worktree, paid tools or backend without approval."),
    Stage("quality", ("impeccable", "anti-slop/antislop-ui", "anti-slop/antislop-layoutmobile", "agent-browser/dogfood", "marketing-skills/seo-audit"),
          "Browser, mobile, accessibility and quality checks; owner approval before publication."),
)

WORKFLOWS = {"website-factory": WEBSITE_FACTORY,
             "lead-discovery": WEBSITE_FACTORY[:2],
             "website-audit": WEBSITE_FACTORY[-1:]}


def compose(name: str) -> tuple[Stage, ...]:
    return WORKFLOWS[name]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", choices=WORKFLOWS)
    parser.add_argument("--stage", choices=tuple(s.name for s in WEBSITE_FACTORY))
    args = parser.parse_args()
    stages = compose(args.workflow)
    if args.stage:
        stages = tuple(s for s in stages if s.name == args.stage)
        if not stages:
            parser.error("Stage is not part of this workflow")
    print(json.dumps({"workflow": args.workflow, "mode": "plan-only",
                      "stages": [asdict(s) for s in stages]}, indent=2))


if __name__ == "__main__":
    main()
