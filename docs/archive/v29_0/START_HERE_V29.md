# Start JARVIS v29.0

Extract to a separate folder, for example:

`C:\Users\austi\Desktop\Jarvis_v29`

## First run

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v29"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

The native title and Control Center should both report **29.0**.

## Later starts

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v29"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

## Test Native Surface

Stay on **Command Center** and ask:

- `Jarvis, open GitHub.`
- then navigate to `youtube.com`
- then `google.com`

The selected workspace must stay Command Center. The website should appear in the native Surface pane inside the same JARVIS window. It should not open a separate browser and there is no screenshot stream.

## Coding JARVIS

Switch to **Developer** or add the **Coding JARVIS** widget. Press **Prepare dev clone**, or say:

- `Coding Jarvis, prepare your development workspace.`
- `Coding Jarvis, find where the phone bridge health endpoint is defined.`
- `Coding Jarvis, inspect the Surface code.`

Code modifications stay in the isolated `jarvis-v29-dev` clone. Do not promote them to stable without reviewing the diff/checks.

## Build the V29 phone companion

```powershell
.\scripts\build_android_v29.ps1
```

Install `JARVIS_Companion_v29-debug.apk` on the Samsung. Grant **Contacts + Calling** only if you want phone-call control.

Examples after the background phone link is connected:

- `Jarvis, find Mum in my phone contacts.`
- `Jarvis, call Mum.`

V29.0 starts the normal cellular call and hands the live call to you. Full AI-conducted audio is not implemented in the SIM path.
