@echo off
cd /d "%~dp0"
title JARVIS v28.1
echo.
echo ========================================
echo       STARTING JARVIS v28.1
echo ========================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo First run detected. Creating the V28.1 Python environment...
  powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\setup_windows.ps1"
  if errorlevel 1 (
    echo.
    echo SETUP FAILED. Send a screenshot of this window.
    pause
    exit /b 1
  )
)
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\run_jarvis.ps1"
if errorlevel 1 (
  echo.
  echo JARVIS returned an error. Send a screenshot of this window.
  pause
)
