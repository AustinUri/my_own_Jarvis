@echo off
cd /d "%~dp0"
title JARVIS v29.0
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (!(Test-Path '.\.venv\Scripts\python.exe')) { & '.\scripts\setup_windows.ps1' }; & '.\scripts\run_jarvis.ps1'"
pause
