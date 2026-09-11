param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "== JARVIS v23 Windows setup ==" -ForegroundColor Cyan
& $PythonCommand --version

if (-not (Test-Path ".venv")) {
    Write-Host "Creating .venv..."
    & $PythonCommand -m venv .venv
}

$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    throw "Virtual environment Python was not created at $py"
}

Write-Host "Upgrading pip..."
& $py -m pip install --upgrade pip

Write-Host "Installing JARVIS dependencies..."
& $py -m pip install -r requirements.txt

Write-Host "Syntax-checking Python project..."
& $py -m compileall -q .

if (-not (Test-Path ".\workspace_ui\dist\index.html")) {
    throw "workspace_ui\dist is missing. The v23 workspace cannot start."
}

Write-Host ""
Write-Host "JARVIS v23 environment is ready." -ForegroundColor Green
Write-Host "Run: .\scripts\doctor.ps1"
Write-Host "Then: .\scripts\run_jarvis.ps1"
