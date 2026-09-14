$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Set-Location (Split-Path -Parent $PSScriptRoot)
$pythonw = Join-Path (Get-Location) ".venv\Scripts\pythonw.exe"
$main = Join-Path (Get-Location) "main.py"
if (-not (Test-Path $pythonw)) { throw "Missing .venv. Run .\scripts\setup_windows.ps1 first." }
$cmd = '"' + $pythonw + '" "' + $main + '" --background'
New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Force | Out-Null
New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "JarvisLocalAssistant" -PropertyType String -Value $cmd -Force | Out-Null
& $pythonw -c "from pathlib import Path; from core.config import AppConfig; p=Path('config.json'); c=AppConfig.load(p); c.start_with_windows=True; c.save(p)"
Write-Host "[OK] Windows autostart now points to JARVIS v29.1 in this folder." -ForegroundColor Green
