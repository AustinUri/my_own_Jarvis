$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "== JARVIS v26 doctor ==" -ForegroundColor Cyan

$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $py) { Write-Host "[OK] .venv exists" -ForegroundColor Green; & $py --version } else { Write-Host "[FAIL] .venv missing. Run .\scripts\setup_windows.ps1" -ForegroundColor Red }
if (Test-Path ".\workspace_ui\dist\index.html") { Write-Host "[OK] Control Center bundle present" -ForegroundColor Green } else { Write-Host "[FAIL] workspace_ui\dist missing" -ForegroundColor Red }

try {
    $models = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 5
    $ids = @($models.data | ForEach-Object { $_.id })
    Write-Host "[OK] LM Studio API reachable" -ForegroundColor Green
    Write-Host ("     Loaded model(s): " + ($ids -join ", "))
    if ($ids -notcontains "jarvis-qwen") { Write-Host "[WARN] jarvis-qwen is not loaded; v26 can try to load it automatically." -ForegroundColor Yellow }
} catch { Write-Host "[WARN] LM Studio is offline; v26 will try to start it automatically." -ForegroundColor Yellow }

try {
    Invoke-RestMethod -UseBasicParsing -Uri "http://localhost:8888/search?q=moon&format=json" -TimeoutSec 6 | Out-Null
    Write-Host "[OK] SearXNG JSON API reachable" -ForegroundColor Green
} catch { Write-Host "[WARN] SearXNG is offline; v26 will try to start Docker/SearXNG automatically." -ForegroundColor Yellow }

try {
    $imports = & $py -c "import fastapi, uvicorn, PySide6, googleapiclient, google_auth_oauthlib, cryptography, keyring; print('ok')" 2>$null
    if ($imports -eq 'ok') { Write-Host "[OK] Python + Calendar + phone-security dependencies import" -ForegroundColor Green }
} catch { Write-Host "[FAIL] Python dependencies are incomplete" -ForegroundColor Red }

$cal = Join-Path $env:APPDATA "Jarvis\credentials\google_calendar_client.json"
if (Test-Path $cal) { Write-Host "[OK] Google Calendar OAuth client file found" -ForegroundColor Green } else { Write-Host "[INFO] Google Calendar not configured yet: $cal" -ForegroundColor Cyan }

$runKey = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "JarvisLocalAssistant" -ErrorAction SilentlyContinue
if ($runKey) { Write-Host "[OK] JARVIS background autostart registered" -ForegroundColor Green } else { Write-Host "[WARN] JARVIS autostart not registered; rerun setup_windows.ps1" -ForegroundColor Yellow }


try {
    $ts = Get-Command tailscale -ErrorAction Stop
    $tsStatus = & tailscale status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Tailscale CLI reachable for private phone link" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Tailscale installed but not connected yet" -ForegroundColor Cyan
    }
} catch {
    Write-Host "[INFO] Tailscale not installed. Only needed when you are ready to test the remote phone companion." -ForegroundColor Cyan
}

if (Test-Path ".\android_companion\app\src\main\AndroidManifest.xml") {
    Write-Host "[OK] Android companion source present" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Android companion source missing" -ForegroundColor Red
}

Write-Host "Doctor finished."
