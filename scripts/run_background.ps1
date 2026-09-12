$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$pythonw = Join-Path (Get-Location) ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) { throw "Missing .venv. Run setup_windows.ps1 first." }
Start-Process -FilePath $pythonw -ArgumentList @("main.py","--background") -WorkingDirectory (Get-Location)
Write-Host "JARVIS Core started in the background. Use the tray icon to open the Control Center."
