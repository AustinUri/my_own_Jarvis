# Start JARVIS v28.5.1

## First run
```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_5"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

## Normal start
```powershell
cd "C:\Users\austi\Desktop\Jarvis_v28_5"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

The UI and health endpoints should report **28.5.1**.

## Surface test
1. Stay in **Command Center**.
2. Ask: `Jarvis, open GitHub.`
3. The Surface widget may expand, but the workspace selector must remain **Command Center**.
4. In the same Surface address bar load YouTube, then Google.
5. `about:blank` must never replace the address field.
6. Manually switch to another workspace while Surface is active. JARVIS must not switch you back.

## Engineering Tutor
Open **Engineering Tutor** from Add Widget, or choose the optional **Engineering** workspace.
Press **Sync course** once, or ask:

- `Jarvis, sync my mechanical engineering course.`
- `Jarvis, teach me the next lesson from home-mech-engin.`
- `Jarvis, teach me statics from my engineering course.`
- `Jarvis, quiz me on thermodynamics from my engineering course.`

The public repository is cloned/updated with Git and the existing local LM Studio model does the teaching. No cloud AI API key is required.
