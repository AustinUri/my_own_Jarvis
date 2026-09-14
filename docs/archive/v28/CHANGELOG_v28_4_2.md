# JARVIS v28.4.2 — Surface Dock In-Place Hotfix

- Replaces the side QDockWidget browser with an in-place Chromium surface.
- Remote sites render exactly inside the Surface Dock card's web viewport.
- The native Chromium child follows the card when it moves, resizes, scrolls, or changes workspace.
- Keeps top-level page loading, so GitHub/Google/YouTube are not blocked by iframe CSP/X-Frame-Options.
- Adds Surface Dock back, forward, and reload controls.
- Keeps persistent browser cookies/profile.
- Fixes stale build identity: workspace snapshot, health endpoints, tray, and run script now agree on v28.4.2.
- Fixes stale-instance detection so multi-part v28.x build numbers are recognized.
