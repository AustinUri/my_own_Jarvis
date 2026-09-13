# JARVIS v28.1 Hotfix

## Fixed

- **English-first speech recognition:** V28 defaulted to multilingual `Auto`, which could classify accented English as Hebrew. V28.1 defaults to `English`. Auto and Hebrew remain selectable.
- **Speech completion:** normal typed/PTT follow-ups are queued instead of cancelling TTS. Long sentences are safely split into TTS-sized chunks and every chunk is awaited.
- **Wrong v26 Control Center:** the launcher detects known older JARVIS instances occupying ports 8765/8766 and closes them before V28.1 starts. Workspace files are served with no-cache headers and the UI reads its build label from the running backend.
- **HoloLab launch:** workspace switching is case-insensitive and recognizes `HoloLab`, `holo lab`, `hologram`, and `spatial fabricator`. HoloLab always enters visual/manual mode even if hand tracking fails.
- **Hand tracking:** moved from the fragile legacy MediaPipe Hands loader to current MediaPipe Tasks Vision Hand Landmarker. Manual mouse/touch control remains available as a fallback.
- **Phone functionality:** paired companion now exposes native calendar read, device information, and battery/charging status. Phone Link panel includes test buttons for device info and battery.

## Important

Install/rebuild the **V28.1 Android companion** to use the battery function. Existing V28 pairing data may remain, but reinstalling the APK is recommended while testing this hotfix.
