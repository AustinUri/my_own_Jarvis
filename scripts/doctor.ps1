$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "== JARVIS v23 doctor ==" -ForegroundColor Cyan

$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $py) { Write-Host "[OK] .venv exists" -ForegroundColor Green; & $py --version } else { Write-Host "[FAIL] .venv missing. Run .\scripts\setup_windows.ps1" -ForegroundColor Red }

if (Test-Path ".\workspace_ui\dist\index.html") { Write-Host "[OK] Workspace UI bundle present" -ForegroundColor Green } else { Write-Host "[FAIL] workspace_ui\dist missing" -ForegroundColor Red }

try {
    $models = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 5
    $ids = @($models.data | ForEach-Object { $_.id })
    Write-Host "[OK] LM Studio API reachable" -ForegroundColor Green
    Write-Host ("     Loaded model(s): " + ($ids -join ", "))
    if ($ids -notcontains "jarvis-qwen") { Write-Host "[WARN] identifier 'jarvis-qwen' is not currently loaded." -ForegroundColor Yellow }
} catch {
    Write-Host "[FAIL] LM Studio API not reachable at http://127.0.0.1:1234/v1" -ForegroundColor Red
    Write-Host "       Run: lms server start"
}

try {
    Invoke-RestMethod -UseBasicParsing -Uri "http://localhost:8888/search?q=moon&format=json" -TimeoutSec 6 | Out-Null
    Write-Host "[OK] SearXNG JSON API reachable" -ForegroundColor Green
} catch {
    Write-Host "[WARN] SearXNG not reachable at http://localhost:8888" -ForegroundColor Yellow
}

try {
    $imports = & $py -c "import fastapi, uvicorn, PySide6; print('ok')" 2>$null
    if ($imports -eq 'ok') { Write-Host "[OK] Workspace Python dependencies import" -ForegroundColor Green }
} catch { Write-Host "[FAIL] Workspace Python dependencies are incomplete" -ForegroundColor Red }

Write-Host ""
Write-Host "Doctor finished."
