$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "== JARVIS v28.3 VERIFY ==" -ForegroundColor Cyan
Write-Host "Folder: $(Get-Location)"
Write-Host "VERSION: $(Get-Content .\VERSION -Raw)"
try {
  $health = Invoke-RestMethod http://127.0.0.1:8765/api/health -TimeoutSec 3
  Write-Host "Desktop health: version=$($health.version) build=$($health.build)" -ForegroundColor Green
} catch { Write-Host "Desktop health: not running" -ForegroundColor Yellow }
try {
  $phone = Invoke-RestMethod http://127.0.0.1:8766/api/phone/health -TimeoutSec 3
  Write-Host "Phone bridge: version=$($phone.version) build=$($phone.build)" -ForegroundColor Green
} catch { Write-Host "Phone bridge: not running" -ForegroundColor Yellow }
if (Select-String -Path .\workspace_ui\dist\workspace.js -Pattern 'function renderOrb' -Quiet) { Write-Host "Living Core renderer: PRESENT" -ForegroundColor Green } else { Write-Host "Living Core renderer: MISSING" -ForegroundColor Red }
