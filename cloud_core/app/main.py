from datetime import datetime, timezone
import platform
import socket

from fastapi import FastAPI

app = FastAPI(
    title="JARVIS Cloud Core",
    version="30.0-alpha"
)

@app.get("/")
def root():
    return {
        "name": "JARVIS",
        "generation": "V30",
        "service": "Cloud Core",
        "status": "online"
    }

@app.get("/api/v1/health")
def health():
    return {
        "ok": True,
        "service": "jarvis-cloud-core",
        "version": "30.0-alpha",
        "hostname": socket.gethostname(),
        "architecture": platform.machine(),
        "time_utc": datetime.now(timezone.utc).isoformat()
    }
