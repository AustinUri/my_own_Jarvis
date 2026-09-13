# Start JARVIS v28.2

Extract to `C:\Users\austi\Desktop\Jarvis_v28_2`.

PowerShell:
```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_2"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

If `.venv` does not exist, run `.\scripts\setup_windows.ps1` first.

Build the phone app with `BUILD_PHONE_V28_2.cmd`.
