from __future__ import annotations

import base64
import hashlib
import json
import queue
import secrets
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from core.user_paths import jarvis_data_dir

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utcnow().isoformat()


@dataclass
class PendingCommand:
    command_id: str
    command: str
    args: dict[str, Any]
    created_at: float = field(default_factory=time.time)


class DeviceStore:
    """Stores paired public keys only. No bearer secret is stored on the PC."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (jarvis_data_dir() / "phone_devices.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {"devices": {}}
        except Exception:
            return {"devices": {}}

    def _save(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def all(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            data = self._load()
            devices = data.get("devices") or {}
            return {str(k): dict(v) for k, v in devices.items() if isinstance(v, dict)}

    def get(self, device_id: str) -> dict[str, Any] | None:
        return self.all().get(device_id)

    def put(self, device_id: str, record: dict[str, Any]) -> None:
        with self._lock:
            data = self._load()
            devices = data.setdefault("devices", {})
            devices[device_id] = dict(record)
            self._save(data)

    def revoke_all(self) -> int:
        with self._lock:
            data = self._load()
            count = len(data.get("devices") or {})
            data["devices"] = {}
            self._save(data)
            return count


class CompanionHub:
    """Security and command queue for the Android companion.

    The HTTP server remains localhost-only. Remote transport is expected to be
    Tailscale Serve (tailnet-only HTTPS). Requests are additionally authenticated
    with an ECDSA key generated inside Android Keystore.
    """

    def __init__(self, config, log: Callable[[str], None] | None = None, status_callback: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.config = config
        self.log = log or (lambda _m: None)
        self.status_callback = status_callback or (lambda _s: None)
        self.store = DeviceStore()
        self._pair_code: str | None = None
        self._pair_expires = 0.0
        self._pair_used = False
        self._queues: dict[str, queue.Queue[PendingCommand]] = {}
        self._pending: dict[str, tuple[threading.Event, dict[str, Any]]] = {}
        self._last_seen: dict[str, float] = {}
        self._recent_nonces: dict[str, dict[str, float]] = {}
        self._lock = threading.RLock()

    # ---------- transport / pairing ----------
    def tailscale_url(self) -> str:
        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True, text=True, timeout=5, creationflags=CREATE_NO_WINDOW,
            )
            if result.returncode != 0:
                return ""
            data = json.loads(result.stdout or "{}")
            dns = str(((data.get("Self") or {}).get("DNSName")) or "").strip().rstrip(".")
            if dns:
                return f"https://{dns}"
        except Exception:
            pass
        return ""


    def prepare_private_transport(self) -> dict[str, Any]:
        """Configure tailnet-only HTTPS proxy to the localhost phone bridge.

        This never enables Funnel/public exposure. The user must already have
        Tailscale installed and signed in. If the tailnet requires one-time
        HTTPS approval, the returned message tells the user what to do.
        """
        port = int(getattr(self.config, "phone_bridge_port", 8766))
        url = self.tailscale_url()
        if not url:
            return {
                "ok": False,
                "server_url": "",
                "message": "Tailscale is not installed, not signed in, or not on PATH. Install/sign in to Tailscale on the PC first.",
            }
        try:
            result = subprocess.run(
                ["tailscale", "serve", "--bg", f"localhost:{port}"],
                capture_output=True, text=True, timeout=20, creationflags=CREATE_NO_WINDOW,
            )
            output = (result.stdout or "") + (result.stderr or "")
            output = output.strip()
            if result.returncode == 0:
                self.log("Phone link: Tailscale Serve configured for private tailnet HTTPS.")
                self.status_callback(self.status())
                return {
                    "ok": True,
                    "server_url": url,
                    "message": "Private phone transport is ready. Tailscale Serve is tailnet-only; JARVIS did not enable Funnel/public access.",
                    "detail": output[-1200:],
                }
            return {
                "ok": False,
                "server_url": url,
                "message": "Tailscale Serve could not be configured automatically. Open Tailscale once and approve HTTPS/Serve if prompted, then try again.",
                "detail": output[-1200:],
            }
        except FileNotFoundError:
            return {"ok": False, "server_url": "", "message": "Tailscale CLI was not found on this PC."}
        except Exception as exc:
            return {"ok": False, "server_url": url, "message": f"Could not prepare the private phone link: {exc}"}

    def begin_pairing(self) -> dict[str, Any]:
        with self._lock:
            self._pair_code = f"{secrets.randbelow(100_000_000):08d}"
            minutes = max(2, min(15, int(getattr(self.config, "phone_pairing_minutes", 5))))
            self._pair_expires = time.time() + minutes * 60
            self._pair_used = False
            expires = _utcnow() + timedelta(minutes=minutes)
            payload = {
                "code": self._pair_code,
                "expires_at": expires.isoformat(),
                "server_url": self.tailscale_url(),
                "minutes": minutes,
            }
        self.status_callback(self.status())
        return payload

    def pair(self, code: str, device_name: str, public_key_b64: str, platform: str = "android") -> dict[str, Any]:
        with self._lock:
            if not self._pair_code or self._pair_used or time.time() > self._pair_expires:
                raise ValueError("Pairing is not active or has expired.")
            if not secrets.compare_digest(str(code).strip(), self._pair_code):
                raise ValueError("Pairing code is incorrect.")
            public_key = self._load_public_key(public_key_b64)
            if not isinstance(public_key, ec.EllipticCurvePublicKey):
                raise ValueError("Unsupported phone identity key.")
            if not isinstance(public_key.curve, ec.SECP256R1):
                raise ValueError("Phone identity key must use P-256.")
            device_id = "phone-" + uuid.uuid4().hex[:18]
            record = {
                "name": (device_name or "Phone")[:80],
                "platform": (platform or "android")[:32],
                "public_key_b64": public_key_b64,
                "paired_at": _iso_now(),
            }
            self.store.put(device_id, record)
            self._queues.setdefault(device_id, queue.Queue())
            self._pair_used = True
            self._pair_code = None
            self._pair_expires = 0.0
        self.log(f"Phone paired: {record['name']}")
        self.status_callback(self.status())
        return {"ok": True, "device_id": device_id, "name": record["name"]}

    # ---------- request authentication ----------
    @staticmethod
    def canonical_message(method: str, path: str, timestamp: str, nonce: str, body: bytes) -> bytes:
        digest = hashlib.sha256(body).hexdigest()
        text = "\n".join([method.upper(), path, timestamp, nonce, digest])
        return text.encode("utf-8")

    @staticmethod
    def _load_public_key(public_key_b64: str):
        try:
            der = base64.b64decode(public_key_b64.encode("ascii"), validate=True)
            return serialization.load_der_public_key(der)
        except Exception as exc:
            raise ValueError("Invalid public key.") from exc

    def verify_request(self, device_id: str, method: str, path: str, timestamp: str, nonce: str, signature_b64: str, body: bytes) -> None:
        record = self.store.get(device_id)
        if not record:
            raise PermissionError("Unknown or revoked phone.")
        try:
            ts = float(timestamp)
        except Exception as exc:
            raise PermissionError("Invalid request timestamp.") from exc
        if abs(time.time() - ts) > 180:
            raise PermissionError("Request timestamp is outside the allowed window.")
        if not nonce or len(nonce) > 128:
            raise PermissionError("Invalid request nonce.")
        with self._lock:
            bucket = self._recent_nonces.setdefault(device_id, {})
            cutoff = time.time() - 300
            for key, seen in list(bucket.items()):
                if seen < cutoff:
                    bucket.pop(key, None)
            if nonce in bucket:
                raise PermissionError("Replay detected.")
            bucket[nonce] = time.time()
        try:
            signature = base64.b64decode(signature_b64.encode("ascii"), validate=True)
            public_key = self._load_public_key(str(record.get("public_key_b64") or ""))
            public_key.verify(
                signature,
                self.canonical_message(method, path, timestamp, nonce, body),
                ec.ECDSA(hashes.SHA256()),
            )
        except InvalidSignature as exc:
            raise PermissionError("Phone signature is invalid.") from exc
        except PermissionError:
            raise
        except Exception as exc:
            raise PermissionError("Phone authentication failed.") from exc
        self.mark_seen(device_id)

    # ---------- command queue ----------
    def mark_seen(self, device_id: str) -> None:
        with self._lock:
            self._last_seen[device_id] = time.time()
        self.status_callback(self.status())

    def poll(self, device_id: str, timeout: float | None = None) -> dict[str, Any]:
        self.mark_seen(device_id)
        with self._lock:
            q = self._queues.setdefault(device_id, queue.Queue())
        wait = timeout if timeout is not None else float(getattr(self.config, "phone_poll_timeout_seconds", 22.0))
        wait = max(1.0, min(25.0, float(wait)))
        try:
            cmd = q.get(timeout=wait)
        except queue.Empty:
            return {"command": "noop", "command_id": None, "args": {}}
        return {"command": cmd.command, "command_id": cmd.command_id, "args": cmd.args}

    def submit_result(self, device_id: str, command_id: str, payload: dict[str, Any]) -> None:
        self.mark_seen(device_id)
        with self._lock:
            item = self._pending.get(command_id)
            if not item:
                return
            event, holder = item
            holder.clear()
            holder.update(payload if isinstance(payload, dict) else {"result": payload})
            event.set()

    def request(self, command: str, args: dict[str, Any] | None = None, timeout: float | None = None, device_id: str | None = None) -> dict[str, Any]:
        target = device_id or self.first_connected_device()
        if not target:
            raise RuntimeError("No trusted phone companion is connected.")
        command_id = uuid.uuid4().hex
        event = threading.Event()
        holder: dict[str, Any] = {}
        pending = PendingCommand(command_id=command_id, command=command, args=args or {})
        with self._lock:
            self._pending[command_id] = (event, holder)
            self._queues.setdefault(target, queue.Queue()).put(pending)
        try:
            wait = timeout if timeout is not None else float(getattr(self.config, "phone_command_timeout_seconds", 30.0))
            if not event.wait(max(3.0, min(60.0, float(wait)))):
                raise TimeoutError("The phone did not respond in time.")
            if holder.get("ok") is False:
                raise RuntimeError(str(holder.get("error") or "Phone command failed."))
            return dict(holder)
        finally:
            with self._lock:
                self._pending.pop(command_id, None)

    # ---------- status / revocation ----------
    def first_connected_device(self) -> str | None:
        now = time.time()
        for device_id in self.store.all():
            if now - self._last_seen.get(device_id, 0) < 70:
                return device_id
        return None

    def status(self) -> dict[str, Any]:
        devices = self.store.all()
        now = time.time()
        rows = []
        for device_id, record in devices.items():
            last = self._last_seen.get(device_id, 0)
            rows.append({
                "device_id": device_id,
                "name": record.get("name") or "Phone",
                "platform": record.get("platform") or "android",
                "paired_at": record.get("paired_at"),
                "connected": bool(last and now - last < 70),
                "last_seen_seconds": None if not last else round(now - last, 1),
            })
        return {
            "enabled": bool(getattr(self.config, "phone_bridge_enabled", True)),
            "paired": bool(rows),
            "connected": any(row["connected"] for row in rows),
            "devices": rows,
            "server_url": self.tailscale_url(),
            "transport": "Tailscale Serve HTTPS",
            "security": "ECDSA P-256 device identity + replay protection",
        }

    def revoke_all(self) -> int:
        with self._lock:
            count = self.store.revoke_all()
            self._queues.clear()
            self._pending.clear()
            self._last_seen.clear()
            self._recent_nonces.clear()
        self.log(f"Revoked {count} paired phone(s).")
        self.status_callback(self.status())
        return count
