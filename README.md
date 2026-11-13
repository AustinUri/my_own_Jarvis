# JARVIS V30

**Personal AI assistant for Windows + Android, connected through Oracle Cloud**

JARVIS is a personal assistant project built around a Windows desktop client, a Samsung Android companion, and an Oracle-hosted cloud core. The goal is to keep the assistant available across devices while preserving local control of AI, voice, tools, memory, and phone actions.

Current development branch: `cloud-v30`

Repository: `AustinUri/my_own_Jarvis`

---

## Current Status

JARVIS V30 has completed its cloud foundation and the first stage of phone intelligence.

### Phase 1 — Cloud Foundation ✅

The V30 architecture is operational.

Verified capabilities:

- Windows and Android connect independently to Oracle Cloud.
- The Samsung companion continues to work when the Windows PC is offline.
- Oracle is the canonical shared-memory layer.
- Windows and Android can access the same remembered information.
- Android no longer depends on Tailscale for normal JARVIS runtime communication.
- Android reconnects after reboot.
- Windows Device Agent reconnects independently.
- The Windows assistant can use shared Oracle memory during normal conversation.
- OpenWakeWord is running through ONNX on Windows.
- The V30 workspace remains the primary desktop interface.

### Phase 2.1 — Incoming Call Awareness ✅

JARVIS can now detect real incoming cellular calls on the Samsung device and forward structured call-state events to Oracle.

Verified on a real incoming call:

- `ringing` detection
- `idle` detection after the call ends
- incoming direction detection
- caller phone-number detection
- contact-name lookup
- Android → Oracle Device Bus delivery
- Oracle recent-device-events endpoint

Example:

```json
{
  "event_type": "phone.call_state",
  "payload": {
    "state": "ringing",
    "direction": "incoming",
    "number": "054xxxxxxx",
    "caller_name": "Mom"
  }
}
```

This provides the foundation for caller announcements, missed-call intelligence, call control, and AI-assisted call handling.

---

## Architecture

```text
                         ┌───────────────────────┐
                         │      Oracle Cloud     │
                         │                       │
                         │  Cloud Core           │
                         │  Device Bus           │
                         │  Shared Memory        │
                         │  Reasoning Router     │
                         │  Device Events        │
                         └───────────┬───────────┘
                                     │
                         HTTPS / WebSocket
                    ┌────────────────┴────────────────┐
                    │                                 │
        ┌───────────▼───────────┐         ┌───────────▼───────────┐
        │      Windows PC       │         │    Samsung Android    │
        │                       │         │                       │
        │ Workspace / GUI       │         │ JARVIS Companion      │
        │ Local AI / LM Studio  │         │ Contacts              │
        │ Wake Word             │         │ Calendar              │
        │ Voice / Tools         │         │ Call History          │
        │ Camera / Vision       │         │ Cellular Calls        │
        │ Device Agent          │         │ WhatsApp Compose      │
        │                       │         │ Incoming Call Events  │
        └───────────────────────┘         └───────────────────────┘
```

The phone and PC are peers connected through Oracle. The phone does **not** need the PC to be online in order to remain connected to JARVIS Cloud.

---

## Windows JARVIS

Current Windows capabilities include:

- V30 workspace / command interface
- local-model support through LM Studio
- Qwen-family local model workflow
- Oracle reasoning routing
- persistent shared memory
- conversation mode
- voice replies
- OpenWakeWord wake-word detection through ONNX
- web research support
- local tools and OS actions
- camera / vision foundation
- phone Device Bus commands
- configurable JARVIS persona and behavior

The Windows assistant is intended to remain locally capable while using Oracle for shared state, device coordination, and remote availability.

---

## Android Companion

The Samsung companion currently supports:

- independent Oracle connection
- secure device pairing
- automatic background connection
- reboot persistence
- calendar access
- contacts search
- call-history access
- cellular call initiation
- WhatsApp compose
- microphone access for voice features
- shared JARVIS memory
- incoming cellular call awareness

Current phone command examples include:

```text
phone.capabilities
phone.calendar_upcoming
phone.contacts_search
phone.call_history
phone.call
phone.whatsapp_compose
```

WhatsApp compose can open the intended conversation with prepared text. Automatic sending is intentionally not treated as generally available because Android/WhatsApp restrictions may apply.

---

## Shared Memory

V30 uses Oracle as the canonical shared-memory layer.

Memory behavior is intentionally conservative:

- explicit "remember this" requests can be stored persistently
- stable preferences and facts can be retained
- temporary conversation turns are not treated as permanent facts
- sensitive information should not be persisted unless explicitly requested
- secrets should not be stored
- corrections and forgetting are supported
- recent conversational context can expire independently of permanent memory

The important architectural goal is that Windows and Android see the same JARVIS memory rather than maintaining separate device-specific memories.

---

## Device Bus

The Device Bus is the communication layer between Oracle and connected JARVIS devices.

It currently supports:

- authenticated Windows connection
- authenticated Android connection
- device presence
- request / result jobs
- phone commands
- Windows reasoning jobs
- transient device events
- incoming call-state events

Transient events such as call state are intentionally kept separate from long-term shared memory.

---

## Phase 2 Roadmap — Phone Intelligence

### Phase 2.2 — Real-Time Call Reaction

Next target:

- JARVIS reacts immediately when a call arrives
- spoken caller announcement
- example: **"Sir, Mom is calling."**
- richer caller context
- missed-call intelligence
- duplicate call-event cleanup

### Phase 2.3 — Call Control

Investigate and implement the correct Android architecture for:

- answer
- reject
- call screening
- default-dialer integration where required
- `CallScreeningService`
- `InCallService`

Android security restrictions mean call control must be implemented through supported system roles rather than assuming an ordinary background app can control every carrier call.

### Phase 2.4 — AI-Assisted Calls

Longer-term goals:

- call transcription
- call summaries
- caller history/context
- JARVIS-assisted responses
- JARVIS handling selected calls

Carrier-call audio access is restricted on modern Android, so full two-way AI call handling may require a supported telephony, default-dialer, SIP, or VoIP path.

---

## Future Roadmap

### Phase 3 — Command Center + Engineering + Vision

Planned:

- unified dashboard / Command Center
- improved camera vision
- object and component identification
- engineering workspace
- mechanical reasoning and calculations
- measurement workflows where technically practical
- HoloLab restoration and expansion
- future CAD / model-generation workflows

### Phase 4 — eBay Low-Touch Business

Planned:

- listing assistance
- pricing research
- inventory support
- low-touch selling workflow
- automation where safe and permitted

### Phase 5 — Stocks + Coding JARVIS

Planned:

- stock research workspace
- company / management analysis
- watchlists and alerts
- rebuild Coding JARVIS
- codebase search and reasoning
- stronger development workspace integration

---

## Current Known Issues

- Android may emit more than one `ringing` broadcast for the same incoming call.
- One event may arrive without caller details followed immediately by a richer event containing number/contact information.
- Call-event deduplication should prefer the richer event.
- Special characters or emoji in Android contact names may display incorrectly in some PowerShell terminals even when the underlying contact lookup is correct.
- Advanced answer/reject and carrier-call audio features are still under investigation because of Android platform restrictions.

---

## Main Project Areas

```text
agent/                 AI provider and agent logic
android_companion/     Samsung / Android JARVIS client
cloud_client/          Windows cloud-device client
cloud_core/            Oracle cloud service
core/                  orchestration, configuration and runtime
tools/                 local tools and OS actions
tts/                   voice output
wakeword/              OpenWakeWord / ONNX wake-word support
workspace/             desktop workspace/runtime
workspace_ui/          JARVIS web-based workspace interface
```

---

## Development Principles

JARVIS V30 follows several project rules:

- cloud-connected, but not cloud-dependent for every local action
- phone and PC should operate independently
- one shared memory rather than conflicting device memories
- local AI remains important
- permissions are explicit
- device actions should be observable and testable
- transient device state should not pollute permanent memory
- platform restrictions should be respected rather than bypassed
- new features should be proven with real-device tests before being marked complete

---

## Current Milestone

```text
Phase 1   Cloud Foundation            COMPLETE
Phase 2.1 Incoming Call Awareness     COMPLETE
Phase 2.2 Real-Time Call Reaction     NEXT
Phase 3   Engineering + Vision        PLANNED
Phase 4   eBay Workflow               PLANNED
Phase 5   Stocks + Coding JARVIS      PLANNED
```

---

## Project Direction

The long-term goal is not a command-only assistant.

JARVIS is being developed as an always-available personal AI system that can understand natural requests, remember useful context, work across the PC and phone, interact with tools and devices, observe through camera/voice inputs, and gradually take on more complex engineering, communication, research, and automation tasks.

V30 is the transition from a mostly PC-centered assistant to a multi-device JARVIS platform.

<!-- JARVIS_PHASE2_STATUS_START -->
## Phase 2 — Android Phone / Call Control Status

Last verified milestone: **JARVIS Phone v1.4 — Multi-Call Fix**

### VERIFIED on real Samsung device

The following functions were tested on the real Android device and passed:

- JARVIS operates as the Android default dialer.
- Incoming carrier calls display caller identity and can be answered or rejected.
- Outgoing carrier calls work from JARVIS Phone.
- Hang up works.
- Mute / Unmute works.
- Speaker on / off works.
- Hold / Resume works.
- Add Call works.
- During two simultaneous calls, JARVIS displays which caller is **ACTIVE** and which caller is **ON HOLD**.
- Switch between active and held calls works.
- Merge works for two carrier calls.
- Conference-call mode works.
- Conference UI displays the conference participants instead of only a generic conference label.
- Ending one call while another remains does not incorrectly terminate the remaining call.
- Call-waiting / multi-call behavior passed the current real-device test.

### UNTESTED

- In-call DTMF keypad is implemented but has **not yet been verified against a real IVR / touch-tone system**.

### OPEN Phase 2 work

#### Contacts / caller UI

**Verified milestone: JARVIS Phone v1.5.2 — Contacts Cleanup**

Verified on the real Samsung device:

- Contact photos appear in the JARVIS contact experience.
- Favorites are handled inside JARVIS.
- Contact groups/categories are shown inside JARVIS.
- Duplicate group names across accounts are merged in the JARVIS UI.
- Legacy/noise groups such as ICE, My Contacts, Starred in Android and restored-device groups are hidden from the normal JARVIS category bar.
- Add Contact and Contact Details/Edit stay inside JARVIS instead of launching Samsung Contacts.
- New groups can be created inside JARVIS.
- Groups can be deleted inside JARVIS with confirmation.
- Group deletion was repeatedly tested and does **not** delete the contacts that belonged to the group.
- Android Contacts Provider remains the address-book source of truth so normal device/account synchronization can continue.
- Oracle is reserved for AI/person memory, aliases, history, call summaries and intelligence rather than acting as a second competing address book.

Deferred UI polish:

- The Account selector is currently functional and cleaned up, but it should eventually be removed from the normal user-facing flow and replaced with a sensible default/account policy behind the scenes.


- Show profile photos directly in the Contacts list.
- Build a JARVIS-owned contact editor for:
  - add contact,
  - edit contact,
  - delete contact,
  - add / change profile photo,
  - manage multiple phone numbers.
- JARVIS should use Android Contacts Provider underneath so Google/Samsung account synchronization remains intact, but contact management should happen inside the JARVIS UI rather than launching Samsung Contacts.

- Add **Favorites** support while keeping starred contacts synchronized with the Android/account contact store.
- Add contact **Groups / Categories** such as Favorites, Family, Friends, Work and user-created groups.
- Store group membership through Android Contacts Provider rather than creating a disconnected JARVIS-only contact database.
- Replace the current `MANAGE` action, which opens the system/Samsung Contacts UI, with a JARVIS-owned contact details/editor screen.
- Investigate `MANAGE_CONTACTS` special access for the JARVIS default-dialer/contact-manager role, with a compatible fallback for Android versions that do not support it.
- Add Favorites support using the Android Contacts Provider so starred
  contacts remain synchronized with the device/account contact store.
- Add contact Groups / Categories such as Favorites, Family, Friends,
  Work and user-created groups.
- Read and write group membership through the Android Contacts Provider
  rather than maintaining a disconnected JARVIS-only contact database.
- Replace the current MANAGE action, which launches the system Contacts
  application, with a JARVIS-owned contact details/editor UI.
- Investigate and adopt Android MANAGE_CONTACTS special access where
  appropriate for the JARVIS default-dialer/contact-manager role,
  with a compatible fallback for Android versions that do not support it.

#### Voice / natural-language call control

- Commands such as **"Call Mom"** must resolve the contact and route through `JarvisPhoneActions` / Android Telecom.
- JARVIS must report real device execution status rather than announcing success before Android confirms the action.
- Voice Answer / Reject / Hang Up integration remains part of Phase 2.

#### Garmin / wearable integration

- Garmin currently identifies some incoming calls as if **JARVIS** is calling instead of showing the real caller.
- Correct caller identity exposed through Android Telecom / call notifications so connected wearables receive the real caller.
- Test and integrate Answer / Reject from the Garmin watch with the JARVIS default-dialer path.

#### Android / Oracle reliability

A long message sent from the phone previously returned a timeout / response-time error.

Add observability before changing timeout values:

- request payload size,
- Android -> Oracle latency,
- Oracle processing time,
- model/provider latency,
- total response time,
- HTTP / Device Bus result,
- structured error reason.

Do not simply increase timeouts without locating the failing stage.

#### Call recording and AI call intelligence

Call recording remains a **critical Phase 2.4 requirement**.

Target flow:

```text
Carrier / JARVIS call
        |
        v
Supported recording path
        |
        v
Transcript
        |
        v
Oracle
        |
        v
AI call summary
        |
        v
Searchable call intelligence / memory
```

Android does not expose unrestricted carrier-call audio capture to ordinary third-party apps, so recording must use a technically supported path. Do not add a fake Record button before an actual recording backend exists.

Paths to investigate:

- Samsung / vendor recording interoperability or import.
- Supported telephony / VoIP / AI-phone provider path.
- Provider-independent JARVIS phone identity for AI-originated calls.
- Transcript ingestion into Oracle for summaries and memory.
- AgentPhone or an equivalent telephony provider as an optional JARVIS AI phone line, without locking JARVIS to Claude or any single model vendor.

### Phase 2 validation rule

A capability is marked **VERIFIED** only after it works on the real device.

Implemented-but-untested features remain explicitly marked **UNTESTED**.

Known failures remain **OPEN** until a real-device retest passes.
<!-- JARVIS_PHASE2_STATUS_END -->

<!-- JARVIS_TODAY_DECISIONS_START -->
## Newly Adopted Project Decisions

### Current / near-term work

These items are considered part of the active product roadmap rather than optional experiments.

#### Security and compliance gate

Before any public/commercial release of the Revenue product:

- perform a structured security review,
- verify authentication and authorization,
- remove or rotate exposed secrets,
- enforce HTTPS,
- restrict CORS,
- use parameterized queries,
- add server-side validation,
- add rate limiting,
- review uploads and file-size limits,
- disable debug mode,
- review dependencies and unused packages,
- scan Git history for secrets,
- review admin routes and payment verification,
- add security headers,
- review cookie / CSRF handling where applicable,
- log suspicious activity,
- produce a final PASS / FAIL / OPEN report.

The commercial website must also have a launch compliance review covering:

- Privacy Policy,
- Terms and Conditions,
- Cookie Policy / consent where legally required,
- Refund Policy,
- explicit and appropriate consent on forms,
- data minimization,
- analytics and third-party embeds,
- accessibility,
- alt text,
- color contrast,
- keyboard-only form usage,
- clear button labels,
- no fake reviews,
- no unsupported claims,
- business details,
- image / copyright rights,
- payment-installment disclosure before purchase,
- Israeli Privacy Protection Law / Amendment 13,
- GDPR where applicable,
- CCPA / CPRA where applicable.

This checklist is a release gate, not a substitute for professional legal advice.

#### UI quality gate

Adopt a repeatable UI quality process for JARVIS and Revenue surfaces:

```text
Functional Test
    ->
Security Review
    ->
Accessibility Audit
    ->
UX Critique
    ->
Harden
    ->
Polish
    ->
Real Device Test
```

Use a consistent design system / `DESIGN.md` so JARVIS does not drift into inconsistent "vibe-coded" UI.

Impeccable-style audit / harden / polish workflows and Google Stitch may be used as design-development tools, but functionality and real-device testing come first.

### Later — Phase 5 / Coding JARVIS

The following are intentionally deferred until the active Phone / Revenue work is stable.

#### Codebase quality and engineering tooling

- Run a structured JARVIS codebase untangling / cleanup pass before major Phase 5 expansion.
- Reduce duplicate utilities, obsolete patch artifacts and architectural drift from older V22-V30 iterations.
- Use a gated workflow similar to `codebase-untangler`:
  - baseline,
  - audit,
  - safety tests,
  - small refactors,
  - hardening,
  - handover.
- Evaluate `REA` as an engineering / reverse-engineering assistant for APKs, binaries, Electron/.NET/native software and interoperability research.
- Keep such tools external to the JARVIS runtime unless there is a clear reason to integrate them.

#### Skills and agent tooling

- Evaluate a small curated subset of **Skills IL** for Israel-specific capabilities such as Hebrew, government, finance, legal-tech and local workflows.
- Do not install an entire large skill catalog blindly.
- Every imported skill must be reviewed for security, necessity and overlap with existing JARVIS tools.

#### AI provider architecture

Maintain a provider abstraction rather than hard-coding one model vendor.

Planned evaluation:

- OpenAI as a primary provider where appropriate,
- Claude as an additional specialist / reviewer / coding provider,
- local Qwen / LM Studio for local or privacy-sensitive workflows,
- optional low-cost/free providers only for non-sensitive work and only after privacy / reliability review.

`FreeLLMAPI` may be evaluated as a development/fallback experiment, but must not receive sensitive personal, business or chat data without a deliberate security/privacy review.

#### Architecture / competitive research

Use projects such as:

- usejarvis.dev,
- Azaris,
- Strata,

as architecture and product-reference material.

Do not copy code from projects whose licenses or architecture do not fit JARVIS.

Useful patterns to study include:

- one shared brain with lightweight device agents,
- visible agent state,
- permission levels,
- approval before irreversible actions,
- scheduled routines,
- shared memory,
- provider-independent tool execution.

Phase 6 remains the home for deeper OS portability and Windows -> Linux adaptation work.
<!-- JARVIS_TODAY_DECISIONS_END -->
