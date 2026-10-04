@echo off
setlocal
cd /d "%~dp0"

title JARVIS V30

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [JARVIS] Python environment not found.
    pause
    exit /b 1
)

echo [JARVIS V30] Starting current JARVIS interface...
"%PYTHON%" "%~dp0main.py"

if errorlevel 1 (
    echo.
    echo [JARVIS] JARVIS exited with an error.
    pause
)

endlocal
