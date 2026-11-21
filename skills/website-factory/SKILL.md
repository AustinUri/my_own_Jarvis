---
name: website-factory
description: JARVIS first-party business website research, factual verification, React draft creation and review workflow. No automatic outreach or publication.
---
# Website Factory — JARVIS First-Party Skill

## Status and scope
Project-owned in Git. Reuses existing `core/capabilities/website_factory.py`,
`verified_website.py`, `creative_website.py`, `lead_discovery.py`,
`business_evidence.py` and `verified_facts.py`. Do NOT clone a second factory.

## Natural-language triggers
- "Build a website for this local business"
- "Create a verified React demo website"
- "בנה אתר לעסק בנתניה"

## Preconditions and workflow
1. Find candidate local businesses using public business data only.
2. Verify the public identity and official website status across more than one source.
   Absence of a website field in one directory is NOT proof that no official site exists.
3. Prepare and review structured factual claims; record source evidence.
4. Produce a **private** React site draft using the approved facts and creative plan.
5. Require mobile, visual, accessibility, source and security review.
6. Never publish a business website or contact owners without explicit approval.

CLI is existing JARVIS source code; read help before execution:

```powershell
python -m core.capabilities.website_factory --help
python -m core.capabilities.workflows website-factory
```

Do not use `--unverified-draft` by default. The verified/creative pipeline requires
approved structured facts and design. Asset rights, SEO claims and attribution
must be checked. Code generation completion does NOT mean the React site built,
ran, passed QA or was published.

## Tool invocation boundary
JARVIS capability registry/router only identify this skill. Automatic direct
execution from natural language in the desktop dashboard still requires wiring
its tool dispatcher in the live app; do NOT imply that routing equals execution.
