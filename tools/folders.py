from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


FOLDER_ALIASES = {
    "desktop": Path.home() / "Desktop",
    "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "pictures": Path.home() / "Pictures",
    "music": Path.home() / "Music",
    "videos": Path.home() / "Videos",
}


def open_folder(folder: str) -> str:
    key = folder.lower().strip()
    path = FOLDER_ALIASES.get(key)
    if not path:
        return f"I do not know the folder '{folder}' yet."
    if not path.exists():
        return f"The folder '{path}' does not exist on this PC."

    system = platform.system().lower()
    try:
        if system == "windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif system == "darwin":
            subprocess.Popen(["open", str(path)], shell=False)
        else:
            subprocess.Popen(["xdg-open", str(path)], shell=False)
        return f"Opened the {key} folder."
    except OSError as exc:
        return f"Could not open the {key} folder: {exc}"
