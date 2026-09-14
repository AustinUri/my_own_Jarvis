$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Set-Location (Split-Path -Parent $PSScriptRoot)

$existing = Get-NetTCPConnection -State Listen -LocalPort 8765 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existing) {
    $version = $null
    try { $version = (Invoke-RestMethod "http://127.0.0.1:8765/api/health" -TimeoutSec 2).version } catch {}
    if ($version -eq 28) {
        Write-Host "JARVIS v29.1 Core is already running; no second background instance was started." -ForegroundColor Cyan
        exit 0
    }
    throw "Port 8765 is already in use by JARVIS v$version (or another process). Exit it before starting v29."
}

$pythonw = Join-Path (Get-Location) ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) { throw "Missing .venv. Run setup_windows.ps1 first." }
Start-Process -FilePath $pythonw -ArgumentList @("main.py","--background") -WorkingDirectory (Get-Location)
Write-Host "JARVIS v29.1 Core started in the background. Use the tray icon to open the Control Center."
