from datetime import datetime, timezone
import hmac
import os
import platform
import socket

from pydantic import BaseModel, Field

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Path,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from .device_bus import device_manager
from .phone_pairing import (
    router as phone_pairing_router,
    validate_device_token,
)

from .reasoning import (
    ReasoningError,
    cloud_reasoning_chat,
    cloud_reasoning_health,
)


app = FastAPI(
    title="JARVIS Cloud Core",
    version="30.0-alpha"
)


def token_is_valid(authorization: str | None) -> bool:
    expected = os.getenv("JARVIS_BOOTSTRAP_TOKEN")

    if not expected:
        return False

    prefix = "Bearer "

    if not authorization or not authorization.startswith(prefix):
        return False

    supplied = authorization[len(prefix):]
    return hmac.compare_digest(supplied, expected)


def require_auth(authorization: str | None = Header(default=None)):
    if not os.getenv("JARVIS_BOOTSTRAP_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JARVIS authentication is not configured",
        )

    if not token_is_valid(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return True


class ReasoningRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    system: str | None = Field(default=None, max_length=6000)
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)
    max_tokens: int = Field(default=500, ge=64, le=1500)
    deep: bool = False


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


@app.get("/api/v1/devices")
def connected_devices(_: bool = Depends(require_auth)):
    devices = device_manager.list_devices()

    return {
        "count": len(devices),
        "devices": devices,
    }


@app.get("/api/v1/reasoning/health")
async def reasoning_health(_: bool = Depends(require_auth)):
    try:
        upstream = await cloud_reasoning_health()
    except ReasoningError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {
        "ok": True,
        "provider": "oracle-qwen",
        "upstream": upstream,
    }


@app.post("/api/v1/reasoning/chat")
async def reasoning_chat(
    body: ReasoningRequest,
    _: bool = Depends(require_auth),
):
    try:
        return await cloud_reasoning_chat(
            text=body.text,
            system_prompt=body.system,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            deep=body.deep,
        )
    except ReasoningError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.websocket("/api/v1/ws/{device_id}")
async def device_socket(
    websocket: WebSocket,
    device_id: str = Path(
        ...,
        pattern=r"^[A-Za-z0-9._-]{1,64}$",
    ),
    device_type: str = Query(default="unknown", max_length=32),
):
    authorization = websocket.headers.get("authorization")

    if not validate_device_token(device_id, authorization):
        await websocket.close(code=1008)
        return

    await device_manager.connect(device_id, device_type, websocket)

    try:
        await websocket.send_json({
            "type": "welcome",
            "device_id": device_id,
            "device_type": device_type,
            "message": "JARVIS V30 Device Bus connected",
        })

        while True:
            message = await websocket.receive_text()

            if message.strip().lower() == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "device_id": device_id,
                    "time_utc": datetime.now(timezone.utc).isoformat(),
                })
            else:
                await websocket.send_json({
                    "type": "received",
                    "device_id": device_id,
                    "message": message,
                })

    except WebSocketDisconnect:
        device_manager.disconnect(device_id)

    except Exception:
        device_manager.disconnect(device_id)
        raise


app.include_router(phone_pairing_router)
