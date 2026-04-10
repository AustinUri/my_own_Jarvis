from __future__ import annotations

import os
import platform
import subprocess
import webbrowser


APP_MAP = {
    "chrome": {
        "windows": [
            r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        ],
        "fallback_url": "https://www.google.com",
    },
    "spotify": {
        "windows": [r"C:\\Users\\%USERNAME%\\AppData\\Roaming\\Spotify\\Spotify.exe"],
        "fallback_url": "spotify:",
    },
    "notepad": {"windows": ["notepad.exe"]},
    "calculator": {"windows": ["calc.exe"]},
    "explorer": {"windows": ["explorer.exe"]},
    "edge": {"windows": [r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"]},
    "discord": {"windows": [r"C:\\Users\\%USERNAME%\\AppData\\Local\\Discord\\Update.exe"]},
    "vscode": {
        "windows": [
            r"C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "code.exe",
        ]
    },
}


def _expand(path: str) -> str:
    return os.path.expandvars(path)


def open_app(app: str) -> str:
    app = app.lower().strip()
    config = APP_MAP.get(app)
    if not config:
        return f"I do not know how to open '{app}' yet."

    system = platform.system().lower()
    if system == "windows":
        for candidate in config.get("windows", []):
            path = _expand(candidate)
            try:
                basename = os.path.basename(path).lower()
                if basename in {"notepad.exe", "calc.exe", "explorer.exe", "code.exe"}:
                    subprocess.Popen([path], shell=False)
                    return f"Opened {app}."
                if os.path.exists(path):
                    if app == "discord" and path.lower().endswith("update.exe"):
                        subprocess.Popen([path, "--processStart", "Discord.exe"], shell=False)
                    else:
                        subprocess.Popen([path], shell=False)
                    return f"Opened {app}."
            except OSError:
                continue

    fallback_url = config.get("fallback_url")
    if fallback_url:
        webbrowser.open(fallback_url)
        return f"Opened fallback for {app}."

    return f"Could not open {app}."
