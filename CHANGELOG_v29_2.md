# JARVIS v29.2 — Mobile Communications

## Wake word resilience
- Detects OpenWakeWord ONNX `INVALID_PROTOBUF` / protobuf parse failures.
- Removes only the damaged packaged ONNX model under OpenWakeWord resources, re-downloads model assets once, and retries the listener.
- If repair still fails, JARVIS continues running and phone/desktop push-to-talk remains available.

## WhatsApp
- Added duplicate-safe `phone_whatsapp_contact` agent tool.
- Uses the paired Android companion to open WhatsApp for the resolved contact with the requested message pre-filled.
- Supports standard WhatsApp and WhatsApp Business, with `wa.me` fallback.
- No WhatsApp Business API, cloud AI API key, or Google voice transcription is required.
- V29.2 intentionally leaves the final WhatsApp Send tap to the user; it never claims a prepared message was delivered.

## Phone voice
- Phone Tap-to-Talk continues to record inside JARVIS Companion and use the PC's local Whisper pipeline.
- Spoken and typed commands use the same call/contact/WhatsApp tools.

## Cleanup
- Removed duplicate V22-V28 start/changelog files from the project root; historical copies remain under `docs/archive`.
- Retained current V29 architecture/docs only.
- Removed transient Python bytecode caches from the package.
