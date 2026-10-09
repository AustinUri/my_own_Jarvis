import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/api/v1/pairing", tags=["pairing"])

PAIRING_TTL = 600
PAIRING_CODES = {}
LOCK = threading.Lock()

DATA_DIR = Path("/opt/jarvis/data")
DEVICES_FILE = DATA_DIR / "paired_devices.json"


class PairRequest(BaseModel):
    code: str
    device_id: str
    device_name: str
    platform: str
    public_key: str


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _bootstrap_token() -> str:
    return os.getenv("JARVIS_BOOTSTRAP_TOKEN", "")


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return ""
    return authorization[7:]


def bootstrap_ok(authorization: str | None) -> bool:
    expected = _bootstrap_token()
    supplied = _extract_bearer(authorization)

    return bool(
        expected
        and supplied
        and secrets.compare_digest(supplied, expected)
    )


def load_devices() -> dict:
    if not DEVICES_FILE.exists():
        return {}

    try:
        return json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_devices(devices: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp = DEVICES_FILE.with_suffix(".tmp")
    temp.write_text(
        json.dumps(devices, indent=2),
        encoding="utf-8",
    )

    os.chmod(temp, 0o600)
    temp.replace(DEVICES_FILE)
    os.chmod(DEVICES_FILE, 0o600)


def validate_device_token(
    device_id: str,
    authorization: str | None,
) -> bool:

    supplied = _extract_bearer(authorization)

    if not supplied:
        return False

    # During V30-alpha the Windows client may still use the bootstrap token.
    bootstrap = _bootstrap_token()

    if bootstrap and secrets.compare_digest(supplied, bootstrap):
        return True

    devices = load_devices()
    device = devices.get(device_id)

    if not device:
        return False

    expected_hash = device.get("token_sha256", "")

    if not expected_hash:
        return False

    return secrets.compare_digest(
        _token_hash(supplied),
        expected_hash,
    )


@router.post("/create")
def create_pairing_code(
    authorization: str | None = Header(default=None),
):
    if not bootstrap_ok(authorization):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"

    with LOCK:
        PAIRING_CODES.clear()
        PAIRING_CODES[code] = time.time() + PAIRING_TTL

    return {
        "ok": True,
        "code": code,
        "expires_in_seconds": PAIRING_TTL,
    }


@router.get("/devices")
def paired_devices(
    authorization: str | None = Header(default=None),
):
    if not bootstrap_ok(authorization):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    devices = load_devices()
    rows = []

    for device_id, record in devices.items():
        if not isinstance(record, dict):
            continue
        rows.append({
            "device_id": device_id,
            "device_name": record.get("device_name") or device_id,
            "platform": record.get("platform") or "unknown",
            "paired_at": record.get("paired_at"),
        })

    return {
        "count": len(rows),
        "devices": rows,
    }


@router.post("/claim")
def claim_pairing(request: PairRequest):

    if not re.fullmatch(
        r"[A-Za-z0-9._-]{1,64}",
        request.device_id,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid device id",
        )

    now = time.time()

    with LOCK:
        expires = PAIRING_CODES.get(request.code)

        if expires is None or expires < now:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired pairing code",
            )

        del PAIRING_CODES[request.code]

    try:
        decoded = base64.b64decode(
            request.public_key,
            validate=True,
        )

        if len(decoded) < 64:
            raise ValueError()

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid public key",
        )

    device_token = secrets.token_urlsafe(48)

    devices = load_devices()

    devices[request.device_id] = {
        "device_id": request.device_id,
        "device_name": request.device_name,
        "platform": request.platform,
        "public_key": request.public_key,
        "token_sha256": _token_hash(device_token),
        "paired_at": int(now),
    }

    save_devices(devices)

    return {
        "ok": True,
        "device_id": request.device_id,
        "name": request.device_name,
        "platform": request.platform,
        "device_token": device_token,
        "paired": True,
    }
