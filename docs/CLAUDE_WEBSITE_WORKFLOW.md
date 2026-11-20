# Claude-led website delivery (business-specific, not a template generator)

JARVIS plans and tracks work. Claude Code implements each customer site in a separate repository/workspace, using reviewed skills and permitted tools. No sample site or booking engine is installed into the personal assistant. Keep customer data separate from personal Oracle memory. Native Claude Code subscription login is for the owner's permitted interactive development, not a customer-facing inference API or unattended subscription proxy.

## Before starting

1. Choose a real business or a consenting test business. Collect only necessary public business facts and owner-provided assets; verify accuracy and image usage rights. Use Google Maps through permitted APIs/manual research; do not scrape or mass-export restricted data or send unsolicited automated messages.
2. Inspect the harvested inventory (`python -m scripts.audit_skill_inventory`), then review desired individual skills, scripts, dependencies, licenses and permissions. Inventory does not confer trust. Use the existing activator only after review. Copy only the approved skill directories (including required references) into the separate customer repo `.claude/skills/`. Check that Claude sees them. Do not copy personal settings/memory or tokens.
3. Confirm Claude account and model with `/status` and integrations with `/mcp`. Use the native CLI interactively for paid Claude if explicitly chosen. Local Qwen/Gemma continues separately. Do not expose a customer's data to any unapproved provider.
4. Higgsfield: official connector/CLI instructions https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent . Verify authentication, credits, asset rights and availability of Website Building in Claude. Do not assume ChatGPT plugin access transfers to Claude.

## Give Claude this brief, then approve the plan before editing

Business: [name, location, category, verified services, opening hours, contact details]
Goal: [calls / inquiries / reservations / sales]
Audience and language: [including RTL when appropriate]
Current website: [URL or none], owner-approved brand and assets, scope and budget: [details].
Use approved relevant skills (Impeccable, UI/UX Pro Max, Anti-Slop, marketing, SEO, humanizer, pricing, etc.); report actual skill names and what each contributed. Use Higgsfield when connected and approved, not as a mandatory dependency. Analyze current-site usability, accessibility, broken links, mobile layout, performance and metadata where applicable. Provide a distinctive design direction based on the actual business, not a generic template. Do not invent reviews, credentials, prices or business facts.

Design and build in this customer workspace only. Validate responsiveness, RTL, keyboard access, forms, mobile performance, SEO and clear calls to action. Test actual behavior with browser automation if available. Give a preview and test evidence; do not publish, contact customers, purchase services, or add live credentials without approval.

If a booking/WhatsApp backend is included in scope, use reviewed Kapso skills and a sandbox. Verify webhook authenticity, idempotency, concurrent booking, timezone, cancellations, customer consent and human handoff. Never claim a booking without server confirmation. Keep per-business data and credentials isolated. See https://github.com/gokapso/agent-skills and https://kapso.com/whatsapp-claude-code .

If analytics is approved, implement PostHog separately for that client: a client-owned project, project token and configured region; use official SDK https://posthog.com/docs/libraries/js . Disable autocapture, automatic pageview/pageleave and session recording by default; collect explicit approved events only after required consent. Start with sanitized `cta_clicked`, `lead_submitted` and `booking_confirmed` (only after confirmed success). Never send phone numbers, names, messages, form values, URLs containing customer data, or sensitive identifiers. Verify event payloads and consent opt-out in a test project before enabling production. Do not add analytics to personal JARVIS or contact memory.

Deliver: source, responsive preview, feature list, verification evidence, unresolved limits, estimated maintenance/hosting/provider costs, and a proposal for website-only vs optional recurring backend/support package. Obtain approval before going live.
