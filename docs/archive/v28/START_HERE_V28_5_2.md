# Start JARVIS v28.5.2

## First run
```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_5_2"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

## Normal start
```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_5_2"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

The UI should report `JARVIS v28.5.2`.

## Surface crash-shield test
1. Stay in Command Center.
2. Open GitHub in Surface.
3. Switch to YouTube, then Google.
4. Change workspace manually and confirm JARVIS does not switch you back.
5. Return and press Load if you want to resume Surface.
6. If Chromium repeatedly fails, Surface should pause itself rather than taking down JARVIS.

For smooth video playback, wait for the V29 isolated native Surface architecture.
