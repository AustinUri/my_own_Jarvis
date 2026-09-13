@echo off
cd /d "%~dp0"
title Build JARVIS Companion v28.1
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\build_android_v28_1.ps1"
echo.
pause
