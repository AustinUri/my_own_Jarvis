# JARVIS v23 — Workspace System

v23 replaces the fixed desktop window with a modular local workspace while keeping the Python JARVIS core.

## What changed

- Draggable and resizable widgets
- Hide/show widgets at runtime
- Pop widgets into separate windows
- Fullscreen any widget
- Multiple saved workspaces: Normal, Research, Developer, Vision, Minimal
- Local layout persistence in the browser profile
- Command palette (`Ctrl+K`)
- Theme switching (Amber / FRIDAY / Mono)
- Animated state-reactive JARVIS core
- Conversation, sources, activity, system monitor, context, camera, and settings widgets
- Explicit browser camera permission; camera is off by default
- Python core and UI communicate over a local WebSocket
- JARVIS can control its own interface through safe `ui_*` agent tools
- Old PySide GUI retained as `--legacy`
- Workspace runtime stays alive in the Windows system tray

The UI is a client. Wake word, STT, TTS, AI, tools, memory, and web research remain in Python.

See `START_HERE.md`.
