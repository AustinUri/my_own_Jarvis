"""Per-desktop-user provider preferences and protected rotating credentials."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import uuid
from contextlib import closing, contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class BrainError(RuntimeError):
    """A message suitable for the native dashboard."""


def user_directory() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / "JARVIS" / "private-ai"
    return Path.home() / ".local" / "share" / "jarvis" / "private-ai"


def vault_key(create: bool) -> bytes:
    try:
        if sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring
            vault = WinVaultKeyring()
            vault.persist = "local machine"
        elif sys.platform == "darwin":
            from keyring.backends.macOS import Keyring
            vault = Keyring()
        else:
            from keyring.backends.SecretService import Keyring
            vault = Keyring()
        service = "JARVIS private AI encryption"
        key = vault.get_password(service, "local")
        if key is None and create:
            key = Fernet.generate_key().decode("ascii")
            vault.set_password(service, "local", key)
        if key is None:
            raise ValueError("missing key")
        return key.encode("ascii")
    except Exception:
        raise BrainError("Unlock the operating system's credential vault to use the ChatGPT connection.") from None


class PlanStore:
    def __init__(self, path=None, key=vault_key):
        self.path = Path(path) if path else user_directory() / "provider.sqlite3"
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.key = key

    @contextmanager
    def edit(self):
        # A database transaction also serializes key creation and rotating refresh across processes.
        with closing(sqlite3.connect(self.path, timeout=70)) as db:
            with db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("CREATE TABLE IF NOT EXISTS provider (id INTEGER PRIMARY KEY, state TEXT NOT NULL)")
                row = db.execute("SELECT state FROM provider WHERE id=1").fetchone()
                state = json.loads(row[0]) if row else {
                    "host": uuid.uuid4().urn, "sealed": "", "connected": False, "enabled": False,
                    "fallback": True, "remember": False, "models": [], "model": "", "plan_type": "",
                    "blocked": "", "error": "", "active": "None",
                }
                yield state
                raw = json.dumps(state)
                if not row or row[0] != raw:
                    db.execute("INSERT OR REPLACE INTO provider VALUES (1, ?)", (raw,))

    def read_session(self, state) -> dict:
        if not state["sealed"]:
            return {}
        try:
            data = Fernet(self.key(False)).decrypt(state["sealed"].encode())
            return json.loads(data)
        except (InvalidToken, ValueError, TypeError):
            raise BrainError("The stored ChatGPT registration could not be unlocked.") from None

    def write_session(self, state, session: dict):
        cipher = Fernet(self.key(not state["sealed"]))
        state["sealed"] = cipher.encrypt(json.dumps(session).encode()).decode()
