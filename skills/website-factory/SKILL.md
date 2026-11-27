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

During strategy, use the [private Hebrew automation worksheet](references/automation-review.html)
when an owner wants to review lead handling. Open the file locally in a browser.
Its ten questions follow Hila Ganani’s checklist and its priorities follow her accompanying email.
Ask the owner which processes run today. Leave uncertain answers open until confirmed.
The page calculates guidance locally and keeps answers in the current page.
Keep this worksheet outside the public business website.

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

## Static commercial demo

The commercial renderer uses the existing verified-facts contract. The reviewed Elias Motors record and its sources are in `examples/elias-motors/`. A verified phone number enables calling. WhatsApp requires its own verified number. The original brake-disc illustration is generated locally and depicts a component.

```powershell
python -m core.capabilities.website_factory --commercial --slug elias-motors-review --facts-file skills/website-factory/examples/elias-motors/facts.json --approve-design --approve-facts
Set-Location .jarvis/website-demos/elias-motors-review/commercial-preview
npm.cmd install --no-audit --no-fund
npm.cmd run build
```

Open `dist/index.html` locally. The build prerenders the React components and structured data from the reviewed JSON. The public package consists of static HTML, CSS and local assets. It carries a private-demo notice and a search-engine exclusion. Review changes to the evidence before regenerating into a new slug. Existing source edits are protected.

From the repository root, run the browser checks with `python -m core.capabilities.website_review --dist .jarvis/website-demos/elias-motors-review/commercial-preview/dist --facts skills/website-factory/examples/elias-motors/facts.json --out .jarvis/website-demos/elias-motors-review/review`. Choose a fresh output directory on each run. The report covers phone and desktop layouts, verified service and contact values, keyboard navigation, SEO metadata and local loading measurements.
