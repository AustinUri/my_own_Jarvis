# Start JARVIS v28.4.2

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_4_2"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

If this is a fresh extracted folder with no `.venv` yet, run `./scripts/setup_windows.ps1` first.

## Surface Dock test

Open Surface Dock, enter `google.com` or `github.com/AustinUri/my_own_Jarvis`, and press **Load**. The live page should appear inside the Surface Dock card itself, not in a right-side pane.
