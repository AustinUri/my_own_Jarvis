# JARVIS v28.4.1

Hotfix for V28.4 UI regression.

- Restored all renderer functions accidentally removed from `workspace.js`.
- Fixes repeated `renderConversation is not defined` errors.
- Restores Conversation, Weather, Calendar, Briefing, Camera/HoloLab, Sources, System Monitor, Context, Settings and related UI functions.
- Retains the integrated Chromium Surface Dock from V28.4.
- The TFLite-to-ONNX message remains a non-fatal vision fallback warning.
