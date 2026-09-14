# Start JARVIS v28.4

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_4"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

On a fresh folder, run `scripts\setup_windows.ps1` before activation.

## Surface Dock 3 test

1. Open Surface Dock.
2. Enter `github.com/AustinUri/my_own_Jarvis` or `youtube.com`.
3. Press **Load inside JARVIS**.
4. A Chromium pane should appear docked to the right **inside the JARVIS Control Center window**.
5. Drag its divider to resize it.

If Qt WebEngine fails to initialize, JARVIS retains a compatibility fallback to the old external browser shell, but that is not the intended V28.4 path.
