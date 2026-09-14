# Start JARVIS v28.5.1

Extract to a separate folder such as `C:\Users\austi\Desktop\Jarvis_v28_5_1`.

First run:

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_5_1"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

Normal runs afterward:

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_5_1"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

The UI and health endpoints should report **28.5.1**.
