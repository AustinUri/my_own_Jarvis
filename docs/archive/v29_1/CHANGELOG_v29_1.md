# JARVIS v29.1 changelog

## Phone
- Added `Phone Center` desktop workspace.
- Added recent call-history widget and phone command.
- Added Android call-log bridge with graceful JARVIS-call-only fallback.
- Added Israeli phone-number canonicalization and duplicate contact collapse.
- Calling a named contact now resolves duplicates internally and prefers a single mobile number where appropriate.
- Spoken call requests are explicitly supported by the agent policy/prompt.
- Removed separate Calendar / Contacts permission buttons from Android UI.
- Added first-run Android permission onboarding.

## Mobile voice
- Removed Google `RecognizerIntent` speech path.
- Added native microphone capture in the JARVIS companion.
- Added signed `/api/phone/voice` endpoint.
- Audio is transcribed by the existing local PC Whisper engine, then processed by normal JARVIS.

## Call memory groundwork
- Phone Center can display call metadata and a conversation-summary panel.
- V29.1 does not fabricate a summary if no call audio/transcript exists.
- Ordinary third-party Android apps cannot reliably capture both sides of a normal SIM call through public APIs; Samsung/system recordings or a future JARVIS VoIP path will feed the summary pipeline later.

## Coding JARVIS
- Search now expands natural code-search phrases into useful implementation terms and known symbols.

## Cleanup
- Removed the obsolete V28 Surface Dock widget from default layouts/widget catalog.
- Archived old V28 validation/start/build clutter under `docs/archive`.
