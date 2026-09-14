$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Set-Location (Split-Path -Parent $PSScriptRoot)

$ExpectedBuild = (Get-Content (Join-Path (Get-Location) "VERSION") -Raw).Trim()

function Stop-KnownOlderJarvisOnPort {
    param(
        [int]$Port,
        [string]$HealthUrl
    )
    $existing = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $existing) { return }

    $health = $null
    try { $health = Invoke-RestMethod $HealthUrl -TimeoutSec 2 } catch {}

    $build = if ($health -and $health.build) { [string]$health.build } else { "" }
    $version = if ($health -and $health.version) { [string]$health.version } else { "" }

    if ($build -eq $ExpectedBuild) {
        if ($Port -eq 8765) {
            Write-Host "JARVIS v$ExpectedBuild is already running. Opening it." -ForegroundColor Cyan
            Start-Process "http://127.0.0.1:8765/?build=$ExpectedBuild"
            exit 0
        }
        return
    }

    $knownJarvis = $version -match '^2[2-9](?:\.\d+){0,3}$' -or $build -match '^2[2-9](?:\.\d+){0,3}$'
    if (-not $knownJarvis) {
        throw "Port $Port is in use by an unknown process (PID $($existing.OwningProcess)). I will not kill an unknown process automatically."
    }

    Write-Host "Older JARVIS detected on port $Port (version=$version build=$build). Stopping PID $($existing.OwningProcess) so v$ExpectedBuild cannot accidentally show the old UI..." -ForegroundColor Yellow
    Stop-Process -Id $existing.OwningProcess -Force -ErrorAction Stop
    Start-Sleep -Milliseconds 800
}

Stop-KnownOlderJarvisOnPort -Port 8765 -HealthUrl "http://127.0.0.1:8765/api/health"
Stop-KnownOlderJarvisOnPort -Port 8766 -HealthUrl "http://127.0.0.1:8766/api/phone/health"

$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing .venv. Run .\scripts\setup_windows.ps1 first." }

Write-Host "Starting JARVIS v$ExpectedBuild from: $(Get-Location)" -ForegroundColor Green
& $py main.py
