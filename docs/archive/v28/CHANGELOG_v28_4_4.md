# JARVIS v28.5.1 — Adaptive Surface + Stable Backdrop

## Surface Dock
- JARVIS now treats Surface Dock as the default destination for websites opened by the AI.
- `open_website` and explicit browser-search actions route into Surface Dock while the workspace UI is connected.
- Added an adaptive `Surface` workspace so websites receive useful screen space automatically.
- Initial sizing is site-aware (search, code/docs, web apps, video/general web).
- Chromium reports page features back to the UI and can refine the Surface widget height.
- The Chromium viewport now follows the actual Surface card size, preventing stretched screenshots and making responsive sites lay out correctly.
- Closing Surface returns to the workspace that was active before the site was opened.

## Background stability
- Removed the giant animated page-level aurora.
- Stopped animated fixed grid drift.
- Removed page-level backdrop-filter stacking from the primary UI panels.
- Kept the animated Living Neutrino Core; the rest of the Control Center background is now static/GPU-stable.

## Notes
- Surface Stream is still a streamed Chromium surface. It is intended for interactive web work inside JARVIS.
- High-frame-rate video playback is not the goal of the screenshot-stream transport; the browser remains fully navigable and interactive.
