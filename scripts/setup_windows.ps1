param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "== JARVIS v26 Windows setup ==" -ForegroundColor Cyan
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

# Register the background core in HKCU so Jarvis starts silently with Windows.
if (Test-Path $pythonw) {
    $main = Join-Path (Get-Location) "main.py"
    $cmd = '"' + $pythonw + '" "' + $main + '" --background'
    New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Force | Out-Null
    New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "JarvisLocalAssistant" -PropertyType String -Value $cmd -Force | Out-Null
    Write-Host "[OK] Registered JARVIS Core to start with Windows." -ForegroundColor Green
    & $py -c "from pathlib import Path; from core.config import AppConfig; p=Path('config.json'); c=AppConfig.load(p); c.start_with_windows=True; c.save(p)"
}

Write-Host ""
Write-Host "JARVIS v26 environment is ready." -ForegroundColor Green
Write-Host "You normally only need to run: .\scripts\run_jarvis.ps1"
Write-Host "After the next Windows login, Jarvis Core should start silently in the tray."
