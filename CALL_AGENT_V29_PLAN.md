# JARVIS Call Agent — V29 plan

Goal: "Jarvis, call Alex and tell him I will be 20 minutes late."

## Two distinct features
1. **Phone Dial / Handoff** — Android companion resolves an approved contact and starts the call; the user speaks normally.
2. **JARVIS-Conducted Call** — a VoIP/SIP path owned by JARVIS carries two-way audio so STT/TTS can participate in the actual call.

## Required behavior
- Always identify itself as JARVIS calling on the user's behalf.
- Show/confirm recipient + intended message before outbound calls unless the user has explicitly enabled a trusted-contact shortcut.
- No emergency-number automation.
- Record/summarize only when legally appropriate and with any required notice/consent.
- Support Message Call, Interactive Call, and Handoff Call modes.
- Store call transcripts locally by default and allow history deletion.

## Why VoIP/SIP for full agent calls
Normal Android third-party apps can place calls, but Android intentionally restricts capture/injection of ordinary cellular-call uplink/downlink audio. A JARVIS-conducted conversation therefore needs a controllable VoIP/SIP media path rather than pretending the companion can freely inject TTS into SIM call audio.
