# JARVIS v29.2 â€” Mobile Communications

V29.2 builds on the stable V29 native Surface, Coding JARVIS and Phone Center. It focuses on reliable wake-word recovery and keyless WhatsApp composition through the Samsung companion.

## Highlights
- self-healing OpenWakeWord model recovery for damaged ONNX assets
- WhatsApp contact resolution using the same duplicate-safe Israeli phone normalization as calling
- WhatsApp message composition from PC voice, PC chat, or phone Tap-to-Talk
- local Whisper remains the phone speech-to-text path; Google speech recognition is not used
- final WhatsApp Send remains a deliberate user tap in V29.2
- no OpenAI/Anthropic/Gemini/Tavily/WhatsApp Business API key requirement
- cleaned project root with old V28 documentation retained only under `docs/archive`

See `START_HERE.md` and `CHANGELOG_v29_2.md`.

## Phase 2.1 — Incoming Call Awareness — COMPLETE

Status: Working and verified on a real Samsung incoming call.

Implemented:
- Android `PHONE_STATE` receiver.
- Runtime `READ_PHONE_STATE` permission.
- Incoming call state detection:
  - `ringing`
  - `idle`
  - `offhook` where Android reports it.
- Caller number lookup when Android exposes the number.
- Contact-name lookup from Samsung Contacts.
- Structured `phone.call_state` events sent through the Oracle Device Bus.
- Oracle recent-device-events endpoint:
  - `GET /api/v1/devices/{device_id}/events`
- Small Android event queue for temporary connectivity loss.
- Phone continues to use Oracle independently of the Windows PC.

Verified end-to-end:

    Incoming cellular call
        -> Samsung call-state receiver
        -> caller/contact lookup
        -> JARVIS Android foreground service
        -> Oracle Device Bus
        -> phone.call_state event

Real test successfully produced:

    state: ringing
    direction: incoming
    caller number: detected
    caller contact name: detected

followed by:

    state: idle

Known Phase 2.1 cleanup:
- Android may emit duplicate `ringing` broadcasts; the richer event containing
  caller information should be preferred/deduplicated.
- Contact names containing emoji/special Unicode characters may display
  incorrectly in some PowerShell output even though contact lookup succeeds.

### Next — Phase 2.2

Planned work:
- Real-time JARVIS reaction to incoming calls.
- Example: "Sir, Mom is calling."
- Missed-call intelligence.
- Call answer/reject architecture where Android permits it.
- Evaluate `CallScreeningService` / `InCallService` and default-dialer
  requirements before implementing call control.
- Later: call transcription, summaries, and JARVIS-assisted call handling.

