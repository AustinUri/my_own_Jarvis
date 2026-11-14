# Israel Site Scout — JARVIS Skill

## Purpose
Find active local businesses in Israel that appear to have no official website,
verify that this is really true, score the best leads, and prepare a lightweight
Hebrew demo website that can be offered to the business for a modest fee.

## Natural-language triggers
- "מצא לי עסקים בנתניה בלי אתר"
- "תמצא מספרות בחיפה בלי אתר"
- "site scout תל אביב מסעדות"
- "find Israeli businesses without a website"
- "תכין דמו לאתר לעסק הזה"

## Lead discovery workflow
1. Search by city + category.
2. Prefer public business directories and normal web search.
3. Useful sources: B144, THE INDEX, IsraeliYP, other public directories.
4. Missing website field in one directory is NOT proof that no official site exists.
5. Verify promising leads with at least two independent searches:
   - business name + city
   - business name + phone
   - business name + address
6. Reject a lead if a credible official website exists.
7. Social-only presence can count as SOCIAL_ONLY, not NO_ONLINE_PRESENCE.
8. Prefer active businesses with public business phone/WhatsApp.

## Lead score (0-100)
- +30 verified no official website
- +15 active public listing / recent activity
- +15 public phone or WhatsApp
- +15 social presence but no site
- +10 category benefits from a simple conversion-focused site
- +10 services can be described from reliable public information
- +5 clear address/service area

Recommended demo threshold: 65.

## Privacy and outreach
- Use only public BUSINESS contact information.
- Do not collect unrelated private personal information.
- Do not bulk-message or auto-send outreach.
- Uri approves outreach.
- Respect opt-outs immediately.
- Never claim authorization or partnership.
- Demo must say: "אתר הדגמה — לא אתר רשמי עד אישור בעל העסק".
- Do not copy copyrighted photos/logos/text without permission.

## Demo design
Default is LIGHT:
- white/off-white/sand background
- teal/blue-green primary accent
- warm orange/terracotta secondary accent
- no black or near-black page background
- Hebrew RTL, responsive/mobile-first
- clear call + WhatsApp actions

## Output
- business_name
- category
- city
- address
- public_phone
- public_whatsapp
- sources
- website_status: VERIFIED_NO_SITE | SOCIAL_ONLY | HAS_SITE | UNCERTAIN
- verification_notes
- lead_score
- suggested_offer
- demo_ready

Generate demo:
`python -m revenue.site_scout_il.generate_demo <business-json>`

## Revenue approach
Start with a working demo, then quote a modest one-time setup price.
Keep domain/hosting/maintenance separate and transparent.
Do not promise SEO rankings.
Uri decides final pricing before outreach.


## Israel production-site requirements

A qualified client site is not complete until the production checklist is reviewed.

### Accessibility baseline
Build all new sites to the stricter baseline by default even if a particular small
business may later qualify for an exemption:
- Israeli Standard 5568, Level AA baseline.
- Semantic landmarks and heading order.
- Full keyboard navigation and visible focus.
- Skip-to-content link.
- Meaningful alt text for content images; decorative images use empty alt.
- Form labels and accessible validation/errors.
- Sufficient color contrast.
- No information conveyed only by color.
- Respect reduced-motion preference.
- RTL/Hebrew support and responsive layout.
- Accessibility statement page and clear accessibility contact path.
- Test before launch with keyboard and at least one screen reader workflow.

Do not claim legal accessibility compliance merely because an accessibility widget
was installed. Widgets are not a substitute for accessible implementation and testing.

### Privacy baseline
For forms, analytics, CRM, newsletter, WhatsApp handoff, checkout or any other
personal-information collection:
- collect only what is needed;
- explain the purpose of collection;
- explain whether providing the information is voluntary/required and consequences;
- identify relevant recipients/uses where required;
- use HTTPS;
- protect admin/API credentials;
- publish a privacy notice appropriate to the actual data flows;
- account for Israel Privacy Protection Law Amendment 13 and information-security duties.

Do not ship a generic privacy policy that lies about cookies, analytics, processors
or data retention. Generate policy text from the site's actual configuration.

### Consumer / e-commerce baseline
If the site sells goods or services remotely, the site specification must include
the disclosures relevant to the actual transaction, including business identity,
main characteristics, total price and payment terms, delivery/performance details,
offer validity where relevant, warranty information where relevant, and cancellation
information. Final wording must match the client's business and current Israeli law.

### Payment / credit-card architecture
Never store or process raw card number/CVV in JARVIS Site Scout.

Preferred architecture:
Browser -> checkout -> Israeli PSP hosted payment page / supported iframe ->
PSP -> signed/server callback -> site order status.

Supported adapter targets:
- CardCom Low Profile JSON payment page
- PayPlus Payment Pages GenerateLink
- Tranzila DirectNG
- additional Israeli PSPs only after their current API/security docs are verified

Each client opens and owns their merchant account/terminal. JARVIS receives only
the integration credentials needed for that merchant and stores them server-side,
never in browser JavaScript or public source.

Production checkout must validate callbacks/webhooks server-side before marking an
order as paid.

### Production launch checklist
A site cannot be labeled READY_TO_SELL until:
- owner approved business details and copy;
- domain and HTTPS are active;
- accessibility checklist completed;
- accessibility statement completed with real contact details;
- privacy notice reflects actual data flows;
- terms/cancellation/disclosures fit the actual business if relevant;
- payment provider is configured in sandbox/test first;
- webhook verification tested;
- no secret/API key appears in frontend files or Git;
- backup/restore and update ownership are agreed;
- final owner acceptance recorded.


## Mandatory v0.3 Human Design Gate

Before building, create a completed BUSINESS_DESIGN_BRIEF_TEMPLATE.md.
After building, run `python -m revenue.site_scout_il.anti_slop <index.html>`.
Score must be <=14 for PASS. A PASS is necessary but not sufficient.
Claude critique is optional and paid; it must never run automatically.
Use `claude_design_review.py` only with explicit `--execute`.
Never use one visual template for unrelated business categories.


## v0.4 — CLIENT DESIGN DNA + React-first engine

### Mandatory order
1. Research the client/business.
2. Write Client Design DNA JSON.
3. Validate DNA.
4. Build/scaffold with React + Next.js by default.
5. Prefer static output when server runtime is unnecessary.
6. Run project anti-slop audit.
7. Create a design-review packet for a human/free LLM/Claude.
8. Revise.
9. Run accessibility/Israel production QA.
10. Owner approval before LIVE.

### React-first, not React-only
Most sites should use React/Next.js, but do not force a heavy client-side SPA when static rendering is sufficient.

### No universal template
The DNA owns page architecture, component vocabulary, visual references, imagery, type direction, shape language, content rhythm, and explicit clichés to avoid.

### Cross-category rule
Football retail and basketball retail are test fixtures. If they converge to the same page blueprint/component vocabulary, the test must fail.

### Development AI
Local/free models may assist during research, coding and critique. No client production site may depend on an experimental free LLM service to remain functional.
