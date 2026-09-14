# JARVIS v28 — Holo Core

## What changed

### Speech completion
- TTS is now serialized sentence-by-sentence.
- A normal interruption request is deferred until the current sentence finishes.
- Long replies no longer intentionally terminate mid-sentence merely because a new input arrives.
- TTS retries one failed sentence once before reporting an error.

### Resource governor
- High VRAM/RAM/temperature still reduces background specialist fan-out.
- The foreground JARVIS conversation is no longer rejected just because VRAM crossed the old severe threshold.
- Protected mode logs the resource condition while allowing the user request to continue.

### Phone Companion 2.0
- The Android URL remains the secure `https://...ts.net` hostname.
- V28 adds an optional PC Tailscale IPv4 fallback field.
- Android uses OkHttp custom DNS routing: it can connect the `.ts.net` hostname to the known `100.x` address without changing the request hostname, TLS SNI, or certificate verification.
- JARVIS Phone Link now publishes both the `.ts.net` URL and the PC Tailscale IPv4.
- `scripts/setup_phone_link.ps1` prints both values.

### HoloLab Alpha
- Camera/Vision now includes an **Enter HoloLab** mode.
- A holographic cube/sphere/ring can be placed over the live camera feed.
- MediaPipe Hands is loaded on demand for palm anchoring and pinch interaction when internet access is available.
- Mouse/touch dragging remains a fallback when hand tracking is unavailable.
- A lightweight visual-test backend reports geometry/palm/scale checks and explicitly marks structural/thermal analysis as not run until a real CAD/solver pipeline is attached.

### Interface
- New v28 glass/aurora visual system with a brighter command-center layout.
- Developer-heavy Agent Activity/Agent Mesh are removed from the default Command Center and remain available in developer workspaces.
- New **HoloLab** workspace.
- V28 uses new `jarvis28.*` UI storage keys so stale V27 built-in layouts do not overwrite the new defaults.

## Important limits
- HoloLab Alpha is not CAD or FEA. It must not invent structural, thermal, fatigue, tolerance, or manufacturability results.
- MediaPipe hand tracking currently loads its runtime on demand from jsDelivr. Manual mouse/touch manipulation still works if that runtime cannot load.
- The Android companion source is included; build the v28 APK on the Windows machine with the installed Android SDK.
