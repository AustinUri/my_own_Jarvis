# JARVIS v28.5.1

## Surface stability
- Surface Dock no longer changes the user's selected workspace automatically.
- A requested site expands as a focused Surface widget inside the current workspace.
- Manually switching to Command Center/another workspace suspends Surface focus; background layout hints cannot switch it back.
- `about:blank` is ignored as an internal/transient Chromium state and can no longer overwrite the address bar or become a Google search.
- Chromium page-target recovery was rewritten: the same active page is reused for GitHub -> YouTube -> Google navigation, and CDP reconnects if the target is detached.
- Site-aware Surface sizing remains, but applies to the focused widget rather than changing workspace modes.

## Mechanical Engineering Tutor
- Adds an **Engineering Tutor** widget and an optional **Engineering** workspace.
- Integrates `https://github.com/AustinUri/home-mech-engin` as a local-first course source.
- Uses ordinary Git clone/pull; no commercial AI API keys are required.
- JARVIS scans readable course/source files, tracks progress locally, and can teach, quiz or review a requested topic through the existing LM Studio model.
- The repository is treated as learning material; JARVIS does not automatically execute repository code.

## Build
- Build identity updated to 28.5.1 across the desktop workspace and phone bridge.
