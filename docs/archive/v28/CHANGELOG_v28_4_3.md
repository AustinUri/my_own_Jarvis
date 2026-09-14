# JARVIS v28.4.3 — Surface Stream Hotfix

- Removed the unreliable second-QWebEngineView overlay used by v28.4.2.
- Surface Dock now runs a private headless Edge/Chrome session through Chromium DevTools Protocol.
- The browser is captured and streamed into the exact Surface Dock card as pixels, so X-Frame-Options / CSP iframe blocking is irrelevant.
- Added click, drag, wheel, printable-text, Enter, Backspace, Tab, Escape, arrow-key, and Delete forwarding.
- Added persistent Chromium profile storage under `%APPDATA%\\Jarvis\\surface_chromium_profile`.
- Kept the Control Center as a single stable Qt WebEngine view.

This is an architectural correction, not another native-overlay tweak. Qt/Chromium native view stacking was the reason GitHub/Google could load internally while remaining invisible in the card.
