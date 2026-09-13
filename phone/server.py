from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from phone.bridge import CompanionHub


class PhoneBridgeServer:
    def __init__(self, hub: CompanionHub, ask_callback: Callable[[str, str], dict[str, Any]] | None = None) -> None:
        self.hub = hub
        self.ask_callback = ask_callback
        self.app = FastAPI(title="JARVIS Phone Bridge", version="28")
        self._pair_attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._configure_routes()

    def _rate_limit_pair(self, host: str) -> None:
        now = time.time()
        with self._lock:
            q = self._pair_attempts[host]
            while q and q[0] < now - 300:
                q.popleft()
            if len(q) >= 6:
                raise HTTPException(status_code=429, detail="Too many pairing attempts. Wait a few minutes.")
            q.append(now)

    async def _auth(self, request: Request, body: bytes) -> str:
        device = request.headers.get("X-Jarvis-Device", "")
        timestamp = request.headers.get("X-Jarvis-Time", "")
        nonce = request.headers.get("X-Jarvis-Nonce", "")
        signature = request.headers.get("X-Jarvis-Signature", "")
        if not all([device, timestamp, nonce, signature]):
            raise HTTPException(status_code=401, detail="Missing phone authentication headers.")
        try:
            self.hub.verify_request(device, request.method, request.url.path, timestamp, nonce, signature, body)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return device

    def _configure_routes(self) -> None:
        app = self.app

        @app.get("/api/phone/health")
        async def health() -> dict[str, Any]:
            # Deliberately contains no personal data and does not expose pairing state.
            return {"ok": True, "version": 28, "build": "28.2", "service": "jarvis-phone-bridge"}

        @app.post("/api/phone/pair")
        async def pair(request: Request) -> JSONResponse:
            host = request.client.host if request.client else "unknown"
            self._rate_limit_pair(host)
            try:
                payload = json.loads((await request.body()).decode("utf-8"))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON.")
            try:
                out = self.hub.pair(
                    code=str(payload.get("code") or ""),
                    device_name=str(payload.get("device_name") or "Phone"),
                    public_key_b64=str(payload.get("public_key") or ""),
                    platform=str(payload.get("platform") or "android"),
                )
            except ValueError as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            return JSONResponse(out)

        @app.post("/api/phone/ask")
        async def ask(request: Request) -> JSONResponse:
            body = await request.body()
            device = await self._auth(request, body)
            if self.ask_callback is None:
                raise HTTPException(status_code=503, detail="Remote JARVIS chat is not connected.")
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON.")
            text = str(payload.get("text") or "").strip()
            if not text:
                raise HTTPException(status_code=400, detail="Question is empty.")
            if len(text) > 6000:
                raise HTTPException(status_code=400, detail="Question is too long.")
            result = await __import__("asyncio").to_thread(self.ask_callback, text, device)
            return JSONResponse(result)

        @app.post("/api/phone/poll")
        async def poll(request: Request) -> JSONResponse:
            body = await request.body()
            device = await self._auth(request, body)
            command = await __import__("asyncio").to_thread(self.hub.poll, device)
            return JSONResponse(command)

        @app.post("/api/phone/result/{command_id}")
        async def result(command_id: str, request: Request) -> JSONResponse:
            body = await request.body()
            device = await self._auth(request, body)
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON.")
            self.hub.submit_result(device, command_id, payload if isinstance(payload, dict) else {"result": payload})
            return JSONResponse({"ok": True})
