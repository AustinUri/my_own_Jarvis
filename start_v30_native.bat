@echo off
setlocal
cd /d "%~dp0"

title JARVIS V30

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo.
    echo [JARVIS] Python environment not found:
    echo %PYTHON%
    echo.
    pause
    exit /b 1
)

echo [JARVIS V30] Starting native Windows interface...
echo [JARVIS V30] Oracle background connection remains independent.
echo.

"%PYTHON%" "%~dp0main.py" --legacy

if errorlevel 1 (
    echo.
    echo [JARVIS] Native interface exited with an error.
    pause
)

endlocal
