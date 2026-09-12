from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = 'JarvisLocalAssistant'


def _build_command(app_dir: Path) -> str:
    python_exe = Path(sys.executable)
    pythonw = python_exe.with_name('pythonw.exe')
    runner = pythonw if pythonw.exists() else python_exe
    main_py = app_dir / 'main.py'
    return f'"{runner}" "{main_py}" --background'


def set_autostart(enabled: bool, app_dir: Path) -> tuple[bool, str]:
    try:
        import winreg
    except Exception:
        return False, 'Autostart can only be managed automatically on Windows.'

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _build_command(app_dir))
                return True, 'Start-with-Windows enabled. JARVIS Core will launch silently in the tray.'
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
            return True, 'Start-with-Windows disabled.'
    except OSError as exc:
        return False, f'Could not update Windows startup: {exc}'
