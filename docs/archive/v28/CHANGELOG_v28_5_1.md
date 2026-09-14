# JARVIS v28.5.1 — Final V28 Surface Stability Hotfix

- Keeps the V28.5 Engineering Tutor exactly as the current baseline; deeper curriculum/tutor improvements are deferred to V29+.
- Makes Surface screenshot streaming conservative instead of trying to behave like a video codec.
- Caps the Chromium Surface viewport to 1440×900, reduces JPEG quality, and throttles capture to 2 FPS for normal pages and 1 FPS for video-heavy pages.
- Avoids resending identical frames and samples page metadata less often to reduce CPU/GPU/WebSocket load.
- Adds automatic Chromium/CDP recovery after repeated Surface failures while preserving the current URL.
- Adds explicit Chromium restart handling if the Surface process crashes.
- Removes the remaining page-level grid/aurora/backdrop-filter effects. Motion is now confined to the Neutrino Core.
- Preserves the V28.5 rule that Surface stays inside the user's chosen workspace and does not hijack Command Center.

This is intended as the last V28 stabilization patch before V29 development.
