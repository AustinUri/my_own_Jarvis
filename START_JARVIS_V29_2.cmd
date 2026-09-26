@echo off
setlocal
title JARVIS v29.2
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '.\scripts\run_jarvis.ps1'"
endlocal
