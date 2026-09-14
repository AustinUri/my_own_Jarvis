# JARVIS v28.3 — Living Core / Reliability Pass

- Restored the missing JARVIS Core renderer.
- Rebuilt the Core as a status-reactive particle/neutrino field.
- Core now changes behavior for idle, listening, thinking, speaking, error and disabled states.
- Active specialist agents appear as orbiting nodes around the Core.
- Fixed the Android MainActivity status string that was accidentally split across source lines.
- Normalized build identity to 28.3 across desktop workspace and phone bridge.
- Kept English-first STT and sentence-completion protections from 28.1/28.2.
- Added .gitattributes for predictable Git line endings on Windows.
- Added V28.3 Android and desktop helper launchers.

## Intentionally not faked
An AI agent cannot reliably inject speech into an ordinary Android cellular call as a normal third-party app. V29 Call Agent should use a VoIP/SIP calling path for genuine JARVIS-conducted calls, with normal Android dialing available separately for handoff calls.
