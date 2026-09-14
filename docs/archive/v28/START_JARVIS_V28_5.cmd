@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (!(Test-Path '.\.venv\Scripts\Activate.ps1')) { .\scripts\setup_windows.ps1 }; & .\.venv\Scripts\Activate.ps1; .\scripts\run_jarvis.ps1"
pause
