@echo off
title Verify JARVIS v28.1
echo.
echo JARVIS workspace:
powershell -NoProfile -Command "try { Invoke-RestMethod http://127.0.0.1:8765/api/health | Format-List } catch { Write-Host $_.Exception.Message -ForegroundColor Red }"
echo.
echo JARVIS phone bridge:
powershell -NoProfile -Command "try { Invoke-RestMethod http://127.0.0.1:8766/api/phone/health | Format-List } catch { Write-Host $_.Exception.Message -ForegroundColor Red }"
echo.
echo Expected workspace build: 28.1
echo Expected phone bridge build: 28.1
echo.
pause
