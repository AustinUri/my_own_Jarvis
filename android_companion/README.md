# JARVIS Android Companion v29.2

The companion is the Samsung-side client for private JARVIS access over Tailscale HTTPS.

## v29.2
- Remote text chat with the home JARVIS core.
- `TAP TO TALK` uses the phone microphone directly and sends signed WAV audio to the PC for local Whisper transcription. Google speech recognition is not used.
- Runtime permission onboarding replaces dedicated permission buttons.
- Native calendar read, contacts, normal cellular dialing/handoff, battery/device info.
- Contact results deduplicate equivalent `+972...` / `05...` Israeli numbers.
- Recent call metadata is available when Android grants call-log access; otherwise JARVIS keeps a smaller journal of calls that JARVIS itself initiated.

Ordinary SIM-call uplink/downlink recording is not claimed by this app. Full conversation summaries require an available recording/transcript source, such as a later Samsung/system-recording importer or the planned JARVIS VoIP call path.
