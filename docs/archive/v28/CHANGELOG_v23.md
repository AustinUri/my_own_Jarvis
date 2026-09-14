# v23 changelog

## New architecture

- Added `workspace/` local API + WebSocket runtime.
- Added `workspace_ui/` modular workspace.
- `python main.py` now launches the workspace runtime by default.
- `python main.py --legacy` launches the previous PySide GUI.

## Workspace

- Drag/resize, hide/show, popout, fullscreen widgets.
- Multiple persisted workspace layouts.
- Command palette and themes.
- Conversation, activity, sources, system, context, camera, settings, and orb widgets.
- Browser camera preview is explicit opt-in.

## Agent/UI integration

- New safe tools: `ui_show_panel`, `ui_hide_panel`, `ui_switch_workspace`.
- The AI can change its UI only when the user explicitly requests it.

## Runtime

- FastAPI + WebSocket local server on `127.0.0.1:8765`.
- Tray controller opens the workspace in Edge/Chrome app mode when available.
- Legacy UI remains available for rollback/testing.

## Reliability

- faster-whisper now automatically falls back to CPU if CUDA/cuBLAS/cuDNN fails at transcription time, avoiding the `cublas64_12.dll` dead-end on Windows.
- The working workspace runtime is prebuilt under `workspace_ui/dist` and does not require Node.js to run.
- React/TypeScript/Three.js source is included as the development path for future UI work.
