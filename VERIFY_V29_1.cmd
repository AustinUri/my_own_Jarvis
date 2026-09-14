@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Write-Host 'JARVIS VERSION:' (Get-Content .\VERSION); Invoke-RestMethod http://127.0.0.1:8765/api/health -ErrorAction SilentlyContinue | Format-List"
endlocal
