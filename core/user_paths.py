from __future__ import annotations

import os
from pathlib import Path


def jarvis_data_dir() -> Path:
    root = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA') or str(Path.home())
    path = Path(root) / 'Jarvis'
    path.mkdir(parents=True, exist_ok=True)
    return path


def profiles_dir() -> Path:
    path = jarvis_data_dir() / 'profiles'
    path.mkdir(parents=True, exist_ok=True)
    return path


def credentials_dir() -> Path:
    path = jarvis_data_dir() / 'credentials'
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = jarvis_data_dir() / 'cache'
    path.mkdir(parents=True, exist_ok=True)
    return path
