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
