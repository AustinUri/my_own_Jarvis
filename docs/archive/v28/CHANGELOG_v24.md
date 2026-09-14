# JARVIS v24 — Research, Vision & Stark UI

## Why this release exists
v23 proved the modular workspace/agent architecture. v24 focuses on four concrete failures found during real use: long spoken requests were clipped, deep historical web research was shallow, new widgets could spawn far below the active workspace, and the Camera widget was only a preview rather than JARVIS vision.

## Changes

### Voice capture
- Longer default turn window: 14 seconds.
- Longer end-of-speech tolerance: 2.2 seconds.
- More speech padding in faster-whisper VAD.
- Replaced the old command-heavy Whisper prompt with natural conversational dictation guidance.
- Research questions are no longer fuzzy-rewritten toward the small app-command vocabulary.
- Years, scores, proper nouns and domains are explicitly preserved in the STT prompt.

### Deep web research
- Broad/list/history/range questions automatically use multi-query SearXNG research.
- Requests such as “all finals back to 1991” preserve the full range instead of being collapsed to a two-sentence fact answer.
- Multiple sources can be fetched and supplied to Qwen as structured evidence.
- HTML extraction now runs before dirty-page rejection, fixing the v23 issue where normal modern pages were discarded merely because their raw HTML contained scripts.
- Table/line structure is preserved for year-by-year historical data.
- UEFA/FIFA are preferred domains for football history, alongside the existing trusted factual sources.

### Camera becomes JARVIS vision
- Camera permission remains explicit and browser-controlled.
- While the Camera / Vision widget is enabled, a small JPEG preview frame is sent over the local WebSocket to the local Python runtime approximately every 1.5 seconds.
- Only the most recent frame is retained in RAM; frames are not written to disk.
- The `analyze_camera` tool lets Qwen inspect the most recent frame when the user explicitly asks JARVIS what it can see.
- Camera state is visible in the workspace as `VISION` / `CAMERA LINKED`.

### Workspace placement
- New widgets are inserted into an available space in the current viewport when possible.
- If there is no free rectangle, the workspace splits a sufficiently large existing panel to place the new widget beside it.
- The old “append at the bottom forever” behavior is only a last resort.
- Built-in v23 layouts are reset once when migrating to v24 so a previously saved off-screen Camera location does not poison the new layout. Custom named workspaces are preserved.

### Visual redesign
- New default `Stark` theme: black/navy workspace with amber/gold holographic accents and small cyan status highlights.
- JARVIS Core rewritten as an original layered holographic sphere with luminous core, spherical lattice, asymmetric data arcs, orbiting nodes and HUD ticks.
- This is an original cinematic-tech interpretation; no Marvel artwork/assets are included.
- FRIDAY-blue and Mono themes remain available.

## Deferred
- Phone client / remote phone control remains intentionally out of v24.
- MediaPipe gesture control remains a later vision layer.
- Remote access outside the LAN is not enabled in this release.
