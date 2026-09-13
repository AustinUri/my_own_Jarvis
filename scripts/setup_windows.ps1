param(
    [string]$PythonCommand = "python",
    [switch]$RegisterAutostart
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "== JARVIS v28.1 Windows setup ==" -ForegroundColor Cyan
& $PythonCommand --version

if (-not (Test-Path ".venv")) {
    Write-Host "Creating .venv..."
    & $PythonCommand -m venv .venv
}

$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$pythonw = Join-Path (Get-Location) ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) { throw "Virtual environment Python was not created at $py" }

Write-Host "Upgrading pip..."
& $py -m pip install --upgrade pip
Write-Host "Installing JARVIS dependencies..."
& $py -m pip install -r requirements.txt
Write-Host "Syntax-checking Python project..."
& $py -m compileall -q .

if (-not (Test-Path ".\workspace_ui\dist\index.html")) { throw "workspace_ui\dist is missing." }

# Keep older builds intact while v28.1 is being evaluated. Autostart changes are opt-in.
if ($RegisterAutostart -and (Test-Path $pythonw)) {
    $main = Join-Path (Get-Location) "main.py"
    $cmd = '"' + $pythonw + '" "' + $main + '" --background'
    New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Force | Out-Null
    New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "JarvisLocalAssistant" -PropertyType String -Value $cmd -Force | Out-Null
    Write-Host "[OK] JARVIS v28.1 registered to start with Windows." -ForegroundColor Green
    & $py -c "from pathlib import Path; from core.config import AppConfig; p=Path('config.json'); c=AppConfig.load(p); c.start_with_windows=True; c.save(p)"
} elseif ($RegisterAutostart) {
    Write-Warning "pythonw.exe was not found; autostart was not changed."
} else {
    Write-Host "[SAFE TEST MODE] Existing Windows autostart entry was left unchanged." -ForegroundColor Yellow
    & $py -c "from pathlib import Path; from core.config import AppConfig; p=Path('config.json'); c=AppConfig.load(p); c.start_with_windows=False; c.save(p)"
    Write-Host "v28.1 Settings will show Start with Windows = Off while you test it."
    Write-Host "After v28.1 is approved, run: .\scripts\enable_autostart.ps1"
}

Write-Host ""
Write-Host "JARVIS v28.1 environment is ready." -ForegroundColor Green
Write-Host "You normally only need to run: .\scripts\run_jarvis.ps1"
Write-Host "The v28.1 launcher detects and closes known older JARVIS instances on ports 8765/8766 so you do not accidentally open the v26/v27 UI."
