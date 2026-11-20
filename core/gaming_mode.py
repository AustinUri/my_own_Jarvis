"""Shared local-inference admission guard for desktop, cloud worker and CLI."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_GAMES = ("cs2.exe", "csgo.exe", "cs2", "csgo")


def flag_path() -> Path:
    root = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(root) / "Jarvis" / "gaming-mode.flag"


def active_game() -> str | None:
    import psutil

    names = {name.strip().casefold() for name in os.environ.get(
        "JARVIS_GAMING_PROCESSES", ",".join(DEFAULT_GAMES)
    ).split(",") if name.strip()}
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info.get("name") or ""
            if name.casefold() in names:
                return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def gaming_reason() -> str | None:
    if flag_path().exists():
        return "Gaming Mode is manually enabled."
    game = active_game()
    return f"Gaming Mode: {game} is running." if game else None


def is_local_endpoint(url: str) -> bool:
    return urlsplit(url).hostname in {"localhost", "127.0.0.1", "::1"}


def require_local_ai_available() -> None:
    reason = gaming_reason()
    if reason:
        raise RuntimeError(reason + " Local AI is paused; retry after gaming.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("on", "off", "status", "check"))
    args = parser.parse_args()
    flag = flag_path()
    if args.command == "on":
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.touch()
    elif args.command == "off":
        flag.unlink(missing_ok=True)
    reason = gaming_reason()
    print(reason or "Normal mode: local AI is available.")
    return 1 if args.command == "check" and reason else 0


if __name__ == "__main__":
    raise SystemExit(main())
