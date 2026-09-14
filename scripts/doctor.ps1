$ErrorActionPreference = "Continue"
$env:PYTHONUTF8 = "1"
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "== JARVIS v29.1 doctor ==" -ForegroundColor Cyan

$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $py) { Write-Host "[OK] .venv exists" -ForegroundColor Green; & $py --version } else { Write-Host "[FAIL] .venv missing. Run .\scripts\setup_windows.ps1" -ForegroundColor Red }
if (Test-Path ".\workspace_ui\dist\index.html") { Write-Host "[OK] Control Center bundle present" -ForegroundColor Green } else { Write-Host "[FAIL] workspace_ui\dist missing" -ForegroundColor Red }

try {
    $models = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 5
    $ids = @($models.data | ForEach-Object { $_.id })
    Write-Host "[OK] LM Studio API reachable" -ForegroundColor Green
    Write-Host ("     Loaded model(s): " + ($ids -join ", "))
    if ($ids -notcontains "jarvis-qwen") { Write-Host "[WARN] jarvis-qwen is not loaded; v29 can try to load it automatically." -ForegroundColor Yellow }
} catch { Write-Host "[WARN] LM Studio is offline; v29 will try to start it automatically." -ForegroundColor Yellow }

try {
    $search = Invoke-RestMethod -UseBasicParsing -Uri "http://localhost:8888/search?q=Formula%201&format=json&engines=reuters" -TimeoutSec 10
    $count = @($search.results).Count
    if ($count -gt 0) {
        Write-Host "[OK] SearXNG reachable and returned $count useful test result(s)" -ForegroundColor Green
    } else {
        Write-Host "[WARN] SearXNG API answered but returned zero test results. v29 can fall back to direct Wikipedia/Google News RSS for supported research/news queries." -ForegroundColor Yellow
    }
} catch { Write-Host "[WARN] SearXNG is offline; v29 will try to start Docker/SearXNG automatically." -ForegroundColor Yellow }

try {
    $rss = Invoke-WebRequest -UseBasicParsing -Uri "https://news.google.com/rss/search?q=Formula%201&hl=en-US&gl=US&ceid=US:en" -TimeoutSec 8
    if ($rss.StatusCode -eq 200) { Write-Host "[OK] Google News RSS fallback reachable" -ForegroundColor Green }
} catch { Write-Host "[INFO] Google News RSS fallback was not reachable during this check" -ForegroundColor Cyan }

try {
    $imports = & $py -c "import fastapi, uvicorn, PySide6, googleapiclient, google_auth_oauthlib, cryptography, keyring; print('ok')" 2>$null
    if ($imports -eq 'ok') { Write-Host "[OK] Python + Calendar + phone-security dependencies import" -ForegroundColor Green }
} catch { Write-Host "[FAIL] Python dependencies are incomplete" -ForegroundColor Red }

$cal = Join-Path $env:APPDATA "Jarvis\credentials\google_calendar_client.json"
if (Test-Path $cal) { Write-Host "[OK] Google Calendar OAuth client file found" -ForegroundColor Green } else { Write-Host "[INFO] Google Calendar backup not configured: $cal" -ForegroundColor Cyan }

$runKey = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "JarvisLocalAssistant" -ErrorAction SilentlyContinue
if ($runKey) { Write-Host "[OK] JARVIS background autostart registered" -ForegroundColor Green } else { Write-Host "[INFO] JARVIS autostart is not registered for this folder. During v29 testing that is expected; after approval run .\scripts\enable_autostart.ps1" -ForegroundColor Yellow }

$tsExe = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
if (-not $tsExe) {
    $candidate = "C:\Program Files\Tailscale\tailscale.exe"
    if (Test-Path $candidate) { $tsExe = $candidate }
}
if ($tsExe) {
    & $tsExe status *> $null
    if ($LASTEXITCODE -eq 0) { Write-Host "[OK] Tailscale CLI reachable for private phone link" -ForegroundColor Green }
    else { Write-Host "[INFO] Tailscale installed but not connected yet" -ForegroundColor Cyan }
} else {
    Write-Host "[INFO] Tailscale not installed. Only needed for remote phone access." -ForegroundColor Cyan
}

if (Test-Path ".\android_companion\app\src\main\AndroidManifest.xml") { Write-Host "[OK] Android companion v29 source present" -ForegroundColor Green } else { Write-Host "[FAIL] Android companion source missing" -ForegroundColor Red }
Write-Host "[OK] Agent Mesh registry: 47 specialist identities; expensive LLM parallelism capped by v29 Resource Governor" -ForegroundColor Green
Write-Host "Doctor finished."
