# JARVIS v28.4 — Surface Dock 3

## Surface Dock is finally part of JARVIS

- Removed iframe-first browsing from Surface Dock.
- Removed the separate JARVIS Surface Browser window as the normal path.
- The Control Center now prefers a native Qt WebEngine shell.
- Surface pages are rendered in a resizable Chromium dock **inside the same JARVIS window**.
- Sites that set `X-Frame-Options` or CSP `frame-ancestors` (GitHub, YouTube, etc.) work because they are top-level pages in their own browser view rather than iframes.
- Surface Dock keeps its own persistent JARVIS browser profile so sign-ins/cookies can survive restart.
- The web pane can be resized, moved to either side, floated temporarily, or closed.
- Search terms typed into Surface Dock are sent to web search automatically.

## Why this design

Trying to bypass a site's iframe protections would be brittle and wrong. A second Chromium view gives JARVIS a real browser surface without leaving the Control Center layout.
