from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def tailscale_executable() -> str | None:
    """Resolve the Tailscale CLI reliably on Windows even when PATH is stale.

    v26 relied only on PATH.  Windows GUI applications often inherit an older
    environment, which made JARVIS falsely report that Tailscale was missing.
    """
    found = shutil.which("tailscale") or shutil.which("tailscale.exe")
    if found:
        return found

    candidates: list[Path] = []
    program_files = os.environ.get("ProgramFiles")
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    local_app = os.environ.get("LOCALAPPDATA")
    if program_files:
        candidates.append(Path(program_files) / "Tailscale" / "tailscale.exe")
    if program_files_x86:
        candidates.append(Path(program_files_x86) / "Tailscale" / "tailscale.exe")
    if local_app:
        candidates.append(Path(local_app) / "Tailscale" / "tailscale.exe")

    # Standard fallback used by current Windows Tailscale installers.
    candidates.append(Path(r"C:\Program Files\Tailscale\tailscale.exe"))

    for candidate in candidates:
        try:
            if candidate.exists():
                return str(candidate)
        except OSError:
            continue
    return None


def run_tailscale(args: Iterable[str], timeout: float = 12.0) -> subprocess.CompletedProcess[str]:
    exe = tailscale_executable()
    if not exe:
        raise FileNotFoundError("Tailscale CLI was not found.")
    return subprocess.run(
        [exe, *list(args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )
