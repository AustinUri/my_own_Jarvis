# JARVIS v28.3 — START HERE

V28.3 is the Living Core / reliability build.

## First run
Open PowerShell in this folder and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

The top bar must show **JARVIS v28.3 · HOLO CORE**.

## Later runs

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

or double-click `START_JARVIS_V28_3.cmd`.

## Android companion
Build the new companion with:

```powershell
.\scripts\build_android_v28_3.ps1
```

The expected APK copy is `JARVIS_Companion_v28_3-debug.apk`.

## What changed
- Restored the missing Core renderer.
- New Living Neutrino Core particle visualization.
- Fixed the Android multiline source bug.
- Normalized v28.3 build identity.
- Preserved secure `.ts.net` + Tailscale-IP fallback.
- Preserved English-first STT and speech-completion protections.

## Call Agent
Full JARVIS-conducted calls are planned for V29 through a controllable VoIP/SIP audio path. See `CALL_AGENT_V29_PLAN.md`.
