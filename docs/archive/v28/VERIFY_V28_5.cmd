@echo off
cd /d "%~dp0"
echo JARVIS expected version:
type VERSION
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod http://127.0.0.1:8765/api/health | Format-List } catch { Write-Host 'Workspace API is not running on 8765.' }"
pause
