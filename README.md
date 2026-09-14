# JARVIS v29.1 — Phone Center + Local Mobile Voice

V29.1 is the first phone-focused refinement of V29.

## Headline changes

- **Phone Center workspace** — dedicated desktop layout with Phone Link, recent calls, native calendar, Conversation and the Neutrino Core.
- **Contact deduplication** — equivalent Israeli numbers such as `+97254...` and `054...` collapse to one contact result. Local Israeli numbers display as `05...` by default.
- **Voice calling fixes** — spoken `call <contact>` requests are treated the same as typed requests; the call tool performs its own deduplicated contact lookup.
- **Local mobile voice** — the Android app no longer launches Google speech recognition. `TAP TO TALK` records the phone microphone and sends a signed WAV over the private JARVIS link. The home PC transcribes it with the existing local Whisper stack and sends the request through normal JARVIS.
- **Permission onboarding** — Calendar, Contacts, Calling, Microphone, Notifications and optional Call History use ordinary Android runtime permission dialogs. Dedicated permission buttons were removed.
- **Recent call history** — when Android grants call-log access, Phone Center can show all recent call metadata. If Android restricts it, JARVIS still shows calls that JARVIS itself started.
- **Call-summary slot** — selecting a call opens the summary area. V29.1 deliberately does not invent a conversation summary without audio/transcript input. Samsung/system recording import and JARVIS VoIP transcripts are the planned audio sources.
- **Coding JARVIS search improvement** — natural phrases such as `Surface browser implementation` fan out to useful code symbols/filenames instead of exact-phrase matching only.
- **UI cleanup** — obsolete V28 Surface Dock widget removed from normal layouts. Native Surface remains the browser pane. Legacy V28 build/validation files were moved under `docs/archive`.

JARVIS remains local-first: LM Studio + SearXNG + Tailscale, with no cloud AI API key requirement.
