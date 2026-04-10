from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Iterable

import psutil


APP_PROCESS_NAMES = {
    "chrome": ["chrome.exe", "chrome"],
    "spotify": ["spotify.exe", "spotify"],
    "notepad": ["notepad.exe", "notepad"],
    "calculator": ["calculatorapp.exe", "calc.exe", "gnome-calculator"],
    "discord": ["discord.exe", "discord"],
    "edge": ["msedge.exe", "microsoft edge", "msedge"],
    "vscode": ["code.exe", "code", "visual studio code"],
}


def _matching_processes(app: str) -> Iterable[psutil.Process]:
    wanted = {name.lower() for name in APP_PROCESS_NAMES.get(app, [app])}
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info.get("name") or "").lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if name in wanted:
            yield proc


def close_app(app: str) -> str:
    key = app.lower().strip()
    closed = 0
    for proc in _matching_processes(key):
        try:
            proc.terminate()
            closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if closed:
        return f"Closed {closed} process{'es' if closed != 1 else ''} for {key}."
    return f"I could not find a running app named '{app}'."


def lock_computer() -> str:
    system = platform.system().lower()
    try:
        if system == "windows":
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"], shell=False)
            return "Locked the computer."
        if system == "darwin":
            subprocess.Popen([
                "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
                "-suspend",
            ], shell=False)
            return "Locked the computer."
        subprocess.Popen(["loginctl", "lock-session"], shell=False)
        return "Locked the computer."
    except OSError as exc:
        return f"Could not lock the computer: {exc}"


def get_system_status() -> str:
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.2)
    battery = None
    try:
        battery = psutil.sensors_battery()
    except Exception:
        battery = None

    summary = (
        f"CPU usage is {cpu:.0f} percent. "
        f"Memory usage is {memory.percent:.0f} percent, with {memory.available / (1024**3):.1f} gigabytes available."
    )
    if battery is not None:
        plugged = "plugged in" if battery.power_plugged else "on battery"
        summary += f" Battery is at {battery.percent:.0f} percent and the system is {plugged}."
    return summary
