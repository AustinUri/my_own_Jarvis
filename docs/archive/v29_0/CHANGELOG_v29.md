# JARVIS v29.0 changelog

## Surface
- Replaced V28 headless Chromium screenshot streaming with a native sibling `QWebEngineView`.
- Surface stays inside the same JARVIS Qt window.
- Opening a site does not switch Command Center/Research/etc. automatically.
- GitHub -> YouTube -> Google uses normal browser navigation in one persistent Surface profile.
- `about:blank` is rejected by the controller and is never treated as a user search.
- Site-aware pane sizing: video gets more room, GitHub/docs and search use smaller ratios.
- Surface renderer termination is handled independently from the Control Center.

## Coding JARVIS
- Added isolated local Git dev workspace under `%APPDATA%\\Jarvis\\coding`.
- Added tools: status, prepare/refresh, search, read file, apply unified diff, diff, checks, local commit.
- Coding changes are restricted to `jarvis-v29-dev`; stable running code is not touched.
- Developer workspace now includes a Coding JARVIS widget.

## Phone / Call Agent
- Added Android contacts permission and contact lookup.
- Added `CALL_PHONE` permission and Android Telecom dial/handoff command.
- Emergency-number automation is blocked.
- Added phone tools for contact search, contact call and explicit-number call.
- Added call-agent preparation tool with disclosure/message/handoff semantics.
- Remote JARVIS text/voice client, calendar, battery and device functions are retained.

## Keyless architecture
- LM Studio/local model remains default.
- SearXNG remains default internet research path.
- Tailscale remains the private phone transport.
- Aperture config is present as optional groundwork but disabled by default.
