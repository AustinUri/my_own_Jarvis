# Start JARVIS v28.5.1

## First run

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_4_4"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

## Normal start

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_4_4"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

## Surface Dock test
Say: `Jarvis, open my GitHub.`

Expected behavior:
1. JARVIS switches to the adaptive Surface workspace.
2. Surface Dock opens the site inside the JARVIS layout.
3. The Surface card is automatically sized for the site.
4. Chromium's viewport is resized to the card.
5. Closing Surface returns to your previous workspace.
