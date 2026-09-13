# JARVIS v27 — Arc Command / Agent Mesh

v27 is an **additive test release**. Keep v26 intact in its own folder until v27 has been tested. Both versions use ports `8765` and `8766`, so only one JARVIS Core can run at a time.

## 1. New Arc Command interface

- Refreshed the default **Stark Glass** look: brighter navy/cyan glass, stronger depth and glow, a more prominent central JARVIS core and less flat/black dashboard styling.
- New **Agent Mesh** widget visualizes a registry of **47 specialist identities** around one shared JARVIS brain.
- New **Surface Dock** can bring explicitly requested normal websites into the JARVIS workspace. If a site blocks embedding, open it externally. Games, UAC/DRM-sensitive software and ordinary native apps are not force-embedded.
- Refreshed built-in Command Center / Research / Developer / Mobile layouts. Existing custom workspace names are preserved during the v26 -> v27 browser-storage migration.
- Agent Activity remains the ordered Mission-Control execution trace.

## 2. 47-agent foundation without 47 model copies

v27 registers 47 lightweight specialist profiles (research, verification, news, Israel, football, Champions League, Formula 1, travel, calendar, phone, Windows, vision, coding, security, memory, Surface Manager, and more).

**Important:** v27 does not start 47 Qwen processes and does not run 47 LLM generations at once. The profiles are routing identities. A request lights up only a small relevant subset while all specialists share the single LM Studio model `jarvis-qwen`.

v27 provides the registry, routing, visualization and safety foundation. It does **not yet** spawn a fully independent LLM worker for every specialist. That is deliberate until resource behavior is measured on the target PC.

## 3. Resource Governor / PC protection

- New Resource Governor monitors CPU, system RAM, NVIDIA GPU utilization, VRAM and GPU temperature when `nvidia-smi` is available.
- Conservative default thresholds reduce the visible active-agent budget and future fan-out when RAM/VRAM/temperature becomes high.
- Hard process-wide local-model semaphore: **no more than two LM Studio chat generations at once**, even if future specialist execution becomes parallel.
- Default active specialist budget is six; the governor can lower it to four or two.
- UI System Monitor displays governor state and current LLM/agent limits.
- If the governor reaches its configured `pause` state, the main Orchestrator refuses to start another heavy local-model response until resources settle.

This is intended to prevent runaway fan-out, memory exhaustion and excessive heat. It is not a substitute for normal hardware thermal protection.

## 4. Web research reliability

- SearXNG remains the private local discovery service.
- Search evidence now filters obvious irrelevant upstream results.
- Current-news requests can fall back to **Google News RSS** without an API key.
- Background/reference questions can fall back to the direct **Wikipedia API**.
- Doctor now performs a real SearXNG quality probe (Reuters) and separately checks the free Google News RSS fallback instead of declaring success merely because the JSON endpoint answered.
- No paid search/AI API is required.

## 5. Phone Link v27

PC side:
- Tailscale CLI resolution now checks PATH **and** the normal Windows Program Files location, fixing the v26 false “Tailscale missing” state.
- New Phone Link diagnostics verify localhost bridge health, Tailscale CLI, Serve route and pairing/connection state.
- Runtime Services now shows Tailscale and the phone bridge.

Android companion source:
- New **TEST PRIVATE CONNECTION** button tests `/api/phone/health` before pairing.
- A Tailscale HTTP 502 is explained correctly: Tailscale Serve was reached, but JARVIS Core/phone bridge is not running on the PC.
- Pairing performs the health check first, so network errors are easier to understand.
- When Secure Companion has been enabled and a device is paired, a boot receiver attempts to resume the foreground service after a normal phone reboot.
- The service continues retrying across temporary Wi-Fi/mobile/Tailscale interruptions.

Security remains deliberately narrow: calendar **read** + basic device information only. No microphone, camera, SMS, contacts, Accessibility, storage, device-admin, app-control or calendar-write permission was added.

Remote phone access still requires the home PC to be online, Tailscale running, and JARVIS Core/phone bridge running. If the PC is asleep/offline, the phone cannot reach the home brain until the PC is available again.

## 6. Windows/runtime fixes

- UTF-8 subprocess decoding is hardened in the service/Tailscale paths to avoid the Windows `cp1252` reader crash seen in v26.
- `run_jarvis.ps1` and `run_background.ps1` detect an existing listener and refuse to start a second/different JARVIS version on port 8765, preventing duplicate `WinError 10048` launches.
- Background launcher remains compatible with Windows PowerShell 5.1 (no `Start-Process -Environment` dependency).
- New `enable_autostart.ps1` makes switching Windows autostart to v27 explicit.
- `setup_windows.ps1` now defaults to **safe test mode** and does not replace the existing v26 autostart entry unless `-RegisterAutostart` is specified.

## 7. Surface Manager groundwork

- New `ui_open_surface` tool is allowed only for an explicit user request to change the interface.
- Normal HTTP(S) websites can be opened in Surface Dock.
- Native app/window capture and managed WebView2 surfaces are future work; v27 does not pretend every desktop program can safely live inside an iframe.
- Future versions can learn per-target display rules such as “open compact”, “dock large”, “always external”, etc.

## 8. Validation limits

The Python runtime and zero-build JavaScript can be statically validated in the build environment. The Android source is included but an APK must still be built/tested in Android Studio on the Windows PC because the build environment does not contain the user's Android SDK/signing setup.

## Recommended v27 test order

1. Keep v26 folder untouched.
2. Extract v27 to a new folder, e.g. `C:\Users\austi\Desktop\my_own_Jarvis_v27`.
3. Exit v26 completely.
4. Run `scripts\setup_windows.ps1` **without** `-RegisterAutostart`.
5. Run `scripts\doctor.ps1` and then `scripts\run_jarvis.ps1`.
6. Check the new Arc Command interface, Agent Mesh and web fallback behavior.
7. Rebuild/install the v27 Android Companion, run **TEST PRIVATE CONNECTION**, then pair with a fresh 8-digit code.
8. Only after v27 is accepted, run `scripts\enable_autostart.ps1` to make v27 the Windows startup version.
