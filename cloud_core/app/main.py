from datetime import datetime, timezone
import hmac
import json
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
from .device_events import device_event_store
from .phone_pairing import (
    router as phone_pairing_router,
    validate_device_token,
)

from .reasoning import (
    DEFAULT_SYSTEM_PROMPT,
    ReasoningError,
    cloud_reasoning_health,
)
from .reasoning_router import (
    ReasoningRouteError,
    route_reasoning,
)
from .shared_memory import DEFAULT_SCOPE, memory_store


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


class DeviceJobRequest(BaseModel):
    job_type: str = Field(
        pattern=r"^[A-Za-z0-9._-]{1,64}$",
    )
    payload: dict = Field(
        default_factory=dict,
    )
    timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
    )


class ReasoningRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    system: str | None = Field(default=None, max_length=6000)
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)
    max_tokens: int = Field(default=500, ge=64, le=1500)
    deep: bool = False
    route: str = Field(
        default="auto",
        pattern=r"^(auto|oracle|windows)$",
    )


class AssistantChatRequest(ReasoningRequest):
    source_device: str = Field(
        default="uri-windows",
        pattern=r"^[A-Za-z0-9._-]{1,64}$",
    )
    memory_scope: str = Field(default=DEFAULT_SCOPE, min_length=1, max_length=64)
    use_memory: bool = True


class MemoryTurnRequest(BaseModel):
    role: str = Field(pattern=r"^(user|assistant|system)$")
    content: str = Field(min_length=1, max_length=12000)
    source_device: str = Field(
        default="uri-windows",
        pattern=r"^[A-Za-z0-9._-]{1,64}$",
    )
    memory_scope: str = Field(default=DEFAULT_SCOPE, min_length=1, max_length=64)


class RememberRequest(BaseModel):
    value: str = Field(min_length=1, max_length=4000)
    key: str | None = Field(default=None, max_length=160)
    source_device: str = Field(
        default="uri-windows",
        pattern=r"^[A-Za-z0-9._-]{1,64}$",
    )
    memory_scope: str = Field(default=DEFAULT_SCOPE, min_length=1, max_length=64)


class MemoryContextRequest(BaseModel):
    query: str = Field(min_length=1, max_length=12000)
    memory_scope: str = Field(default=DEFAULT_SCOPE, min_length=1, max_length=64)
    fact_limit: int = Field(default=16, ge=1, le=50)
    turn_limit: int = Field(default=8, ge=1, le=20)


def _device_auth_or_401(device_id: str, authorization: str | None) -> None:
    if not validate_device_token(device_id, authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device authentication required",
        )


def _system_with_memory(base: str | None, memory_prompt: str) -> str:
    system_prompt = (base or DEFAULT_SYSTEM_PROMPT).strip()
    if not memory_prompt:
        return system_prompt

    return (
        system_prompt
        + "\n\nJARVIS SHARED MEMORY (canonical Oracle context):\n"
        + memory_prompt
        + "\n\nUse this memory only when relevant. If it conflicts with the user's current "
          "request, follow the current request. Do not claim a memory is newer than it is."
    )


async def _assistant_chat(
    body: AssistantChatRequest,
    *,
    source_device: str,
) -> dict:
    gate = memory_store.process_user_text(
        body.text,
        source_device=source_device,
        scope=body.memory_scope,
        allow_auto=True,
    )

    # Hard secrets are not even copied into recent cross-device conversation.
    # This prevents a password/PIN/API key from leaking into the SQLite history
    # merely because the user accidentally phrased it as a memory request.
    if gate.get("store_turn", True):
        memory_store.record_turn(
            "user",
            body.text,
            source_device=source_device,
            scope=body.memory_scope,
        )

    direct_response = str(gate.get("direct_response") or "").strip()
    if direct_response:
        memory_store.record_turn(
            "assistant",
            direct_response,
            source_device=source_device,
            scope=body.memory_scope,
        )
        return {
            "ok": True,
            "provider": "memory-gate",
            "model": "deterministic",
            "text": direct_response,
            "finish_reason": "stop",
            "route": "memory",
            "memory": {
                "scope": body.memory_scope,
                "gate": gate,
                "facts_used": 0,
                "turns_used": 0,
            },
            "source_device": source_device,
        }

    context = (
        memory_store.context_for(
            body.text,
            scope=body.memory_scope,
        )
        if body.use_memory
        else {"prompt": "", "facts": [], "turns": []}
    )

    try:
        result = await route_reasoning(
            text=body.text,
            system_prompt=_system_with_memory(
                body.system,
                str(context.get("prompt") or ""),
            ),
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            deep=body.deep,
            route=body.route,
        )
    except (ReasoningError, ReasoningRouteError):
        raise

    answer = str(result.get("text") or "").strip()
    if answer:
        memory_store.record_turn(
            "assistant",
            answer,
            source_device=source_device,
            scope=body.memory_scope,
        )

    result["memory"] = {
        "scope": body.memory_scope,
        "gate": gate,
        "facts_used": len(context.get("facts") or []),
        "turns_used": len(context.get("turns") or []),
    }
    result["source_device"] = source_device
    return result


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


@app.get("/api/v1/memory/health")
def memory_health(_: bool = Depends(require_auth)):
    return memory_store.health()


@app.get("/api/v1/memory/snapshot")
def memory_snapshot(
    scope: str = Query(default=DEFAULT_SCOPE, min_length=1, max_length=64),
    _: bool = Depends(require_auth),
):
    return memory_store.snapshot(scope=scope)


@app.post("/api/v1/memory/remember")
def memory_remember(
    body: RememberRequest,
    _: bool = Depends(require_auth),
):
    try:
        remembered = memory_store.remember(
            body.value,
            source_device=body.source_device,
            scope=body.memory_scope,
            key=body.key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return {"ok": True, "memory": remembered}


@app.post("/api/v1/memory/context")
def memory_context(
    body: MemoryContextRequest,
    _: bool = Depends(require_auth),
):
    context = memory_store.context_for(
        body.query,
        scope=body.memory_scope,
        fact_limit=body.fact_limit,
        turn_limit=body.turn_limit,
    )
    return {
        "ok": True,
        "scope": body.memory_scope,
        "prompt": str(context.get("prompt") or ""),
        "facts": context.get("facts") or [],
        "turns": context.get("turns") or [],
    }


@app.post("/api/v1/memory/turn")
def memory_turn(
    body: MemoryTurnRequest,
    _: bool = Depends(require_auth),
):
    gate = {"action": "none", "reason": "assistant_turn"}
    if body.role == "user":
        gate = memory_store.process_user_text(
            body.content,
            source_device=body.source_device,
            scope=body.memory_scope,
            allow_auto=True,
        )

    turn = None
    if not (body.role == "user" and not gate.get("store_turn", True)):
        turn = memory_store.record_turn(
            body.role,
            body.content,
            source_device=body.source_device,
            scope=body.memory_scope,
        )

    return {
        "ok": True,
        "turn": turn,
        "gate": gate,
    }


@app.post("/api/v1/assistant/chat")
async def assistant_chat(
    body: AssistantChatRequest,
    _: bool = Depends(require_auth),
):
    try:
        return await _assistant_chat(
            body,
            source_device=body.source_device,
        )
    except (ReasoningError, ReasoningRouteError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/api/v1/device/{device_id}/assistant/chat")
async def device_assistant_chat(
    body: AssistantChatRequest,
    device_id: str = Path(..., pattern=r"^[A-Za-z0-9._-]{1,64}$"),
    authorization: str | None = Header(default=None),
):
    _device_auth_or_401(device_id, authorization)
    try:
        return await _assistant_chat(
            body,
            source_device=device_id,
        )
    except (ReasoningError, ReasoningRouteError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


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
        return await route_reasoning(
            text=body.text,
            system_prompt=body.system,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            deep=body.deep,
            route=body.route,
        )
    except (ReasoningError, ReasoningRouteError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/api/v1/devices/{device_id}/jobs")
async def run_device_job(
    body: DeviceJobRequest,
    device_id: str = Path(
        ...,
        pattern=r"^[A-Za-z0-9._-]{1,64}$",
    ),
    _: bool = Depends(require_auth),
):
    if not device_manager.is_connected(device_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device '{device_id}' is not connected",
        )

    try:
        return await device_manager.request(
            device_id=device_id,
            job_type=body.job_type,
            payload=body.payload,
            timeout=body.timeout_seconds,
        )

    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Device '{device_id}' did not respond in time",
        ) from exc

    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/api/v1/devices/{device_id}/events")
async def recent_device_events(
    device_id: str,
    limit: int = 20,
    _: bool = Depends(require_auth),
):
    safe_limit = max(1, min(int(limit), 100))

    return {
        "device_id": device_id,
        "events": device_event_store.recent(
            device_id,
            limit=safe_limit,
        ),
    }


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
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    payload = None

                if (
                    isinstance(payload, dict)
                    and payload.get("type") == "device_event"
                ):
                    event_type = str(
                        payload.get("event_type") or ""
                    ).strip()

                    if event_type:
                        event_payload = payload.get("payload")

                        if not isinstance(event_payload, dict):
                            event_payload = {}

                        device_event_store.record(
                            device_id=device_id,
                            event_type=event_type,
                            payload=event_payload,
                            event_id=str(
                                payload.get("event_id") or ""
                            ).strip() or None,
                            occurred_at=str(
                                payload.get("occurred_at") or ""
                            ).strip() or None,
                        )

                    continue

                if (
                    isinstance(payload, dict)
                    and payload.get("type") == "job_result"
                ):
                    device_manager.resolve_job_result(
                        device_id,
                        payload,
                    )
                else:
                    await websocket.send_json({
                        "type": "received",
                        "device_id": device_id,
                        "message": message,
                    })

    except WebSocketDisconnect:
        device_manager.disconnect(device_id, websocket)

    except Exception:
        device_manager.disconnect(device_id, websocket)
        raise


app.include_router(phone_pairing_router)
