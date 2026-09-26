from datetime import datetime, timezone
import hmac
import os
import platform
import socket

from fastapi import Depends, FastAPI, Header, HTTPException, status

app = FastAPI(
    title="JARVIS Cloud Core",
    version="30.0-alpha"
)


def require_auth(authorization: str | None = Header(default=None)):
    expected = os.getenv("JARVIS_BOOTSTRAP_TOKEN")

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JARVIS authentication is not configured",
        )

    prefix = "Bearer "

    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    supplied = authorization[len(prefix):]

    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return True


@app.get("/")
def root():
    return {
        "name": "JARVIS",
        "generation": "V30",
        "service": "Cloud Core",
        "status": "online",
    }


@app.get("/api/v1/health")
def health():
    return {
        "ok": True,
        "service": "jarvis-cloud-core",
        "version": "30.0-alpha",
        "hostname": socket.gethostname(),
        "architecture": platform.machine(),
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/private/ping")
def private_ping(_: bool = Depends(require_auth)):
    return {
        "ok": True,
        "authenticated": True,
        "message": "Welcome back, sir.",
    }
