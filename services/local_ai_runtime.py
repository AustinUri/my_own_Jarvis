from __future__ import annotations

import os
import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BASE_URL = os.getenv("JARVIS_LOCAL_AI_BASE_URL", "http://127.0.0.1:1234").rstrip("/")
PORT = int(os.getenv("JARVIS_LOCAL_AI_PORT", "1234"))
DEFAULT_TTL = int(os.getenv("JARVIS_LOCAL_AI_TTL", "300"))
DEFAULT_CONTEXT = int(os.getenv("JARVIS_LOCAL_AI_CONTEXT", "28672"))

MODEL_KEYS = {
    "qwen": os.getenv("JARVIS_QWEN_MODEL", "qwen/qwen3.5-9b"),
    "gemma": os.getenv("JARVIS_GEMMA_MODEL", "google/gemma-4-e4b"),
}

def _lms() -> str:
    found = shutil.which("lms") or shutil.which("lms.exe")
    if found:
        return found
    fallback = Path.home() / ".lmstudio" / "bin" / "lms.exe"
    if fallback.exists():
        return str(fallback)
    raise RuntimeError("LM Studio CLI 'lms' was not found.")

def _run(args: list[str], timeout: float = 90) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )

def server_online(timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(BASE_URL + "/v1/models", timeout=timeout) as r:
            return 200 <= getattr(r, "status", 200) < 300
    except Exception:
        return False

def wait_online(seconds: float = 15.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if server_online():
            return True
        time.sleep(0.35)
    return False

def start_server() -> bool:
    """Return True only if JARVIS started the server in this call."""
    if server_online():
        return False
    cp = _run([_lms(), "server", "start", "--port", str(PORT)], timeout=30)
    if cp.returncode != 0 and not server_online():
        raise RuntimeError(
            "Could not start LM Studio server: "
            + (cp.stderr or cp.stdout or "unknown error").strip()
        )
    if not wait_online():
        raise RuntimeError("LM Studio server did not become ready on port 1234.")
    return True

def stop_server_if_owned(started_by_us: bool) -> None:
    # Never kill a server the user already had running.
    if not started_by_us:
        return
    try:
        _run([_lms(), "server", "stop"], timeout=20)
    except Exception:
        pass

def loaded_models() -> list[str]:
    import json

    cp = _run([_lms(), "ps", "--json"], timeout=15)
    if cp.returncode != 0:
        raise RuntimeError(
            "Could not query loaded LM Studio models: "
            + (cp.stderr or cp.stdout or "unknown error").strip()
        )

    try:
        data = json.loads(cp.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "LM Studio returned invalid JSON from `lms ps --json`."
        ) from exc

    if not isinstance(data, list):
        return []

    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ident = (
            item.get("identifier")
            or item.get("modelKey")
            or item.get("indexedModelIdentifier")
        )
        if ident:
            out.append(str(ident))
    return out

def ensure_model(kind: str, *, ttl: int = DEFAULT_TTL, context: int = DEFAULT_CONTEXT) -> str:
    kind = (kind or "qwen").strip().lower()
    if kind not in MODEL_KEYS:
        raise ValueError(f"Unsupported local model kind: {kind}")
    key = MODEL_KEYS[kind]
    if key in loaded_models():
        return key

    cmd = [
        _lms(), "load", key,
        "--identifier", key,
        "--context-length", str(context),
        "--ttl", str(ttl),
    ]
    cp = _run(cmd, timeout=180)
    if cp.returncode != 0:
        raise RuntimeError(
            f"Could not load {key}: "
            + (cp.stderr or cp.stdout or "unknown error").strip()
        )
    if key not in loaded_models():
        raise RuntimeError(f"LM Studio did not expose loaded model {key}.")
    return key

@dataclass
class RuntimeLease:
    model: str
    started_server: bool

def acquire(kind: str) -> RuntimeLease:
    started = start_server()
    try:
        model = ensure_model(kind)
        return RuntimeLease(model=model, started_server=started)
    except Exception:
        stop_server_if_owned(started)
        raise

def release(lease: RuntimeLease) -> None:
    # Model TTL handles VRAM/RAM cleanup. The API server is stopped only when
    # this invocation started it; an already-running user server is preserved.
    stop_server_if_owned(lease.started_server)
