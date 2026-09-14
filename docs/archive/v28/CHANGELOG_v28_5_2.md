# JARVIS v28.5.2 — Surface Crash Shield

## Fixed
- Surface browser control no longer runs blocking Chromium DevTools calls on the Qt GUI thread.
- Surface control commands are serialized through a dedicated worker so a slow/busy website cannot freeze the Control Center event loop.
- ResizeObserver traffic is debounced and mouse-drag/wheel traffic is throttled to stop command-queue floods.
- Surface streaming pauses when the user leaves the current workspace instead of continuing to burn CPU/GPU in the background.
- Surface Chromium now launches in a lower-resource software-rendered mode and no longer forces background rendering/autoplay behavior.
- Screenshot capture rate and viewport are capped more aggressively, especially for video-heavy pages.
- Added a crash shield: after repeated Chromium recoveries, Surface pauses itself rather than entering a restart loop that can destabilize JARVIS.

## Important limitation
V28.5.2 Surface is a compatibility browser stream. It is suitable for browsing and interaction, but it is not intended to provide smooth full-motion YouTube playback. V29 should replace it with an isolated native browser subsystem so browser/video crashes cannot take down the assistant.

## Engineering Tutor
Unchanged from v28.5. It remains a usable baseline and is intentionally deferred for deeper improvement later.
