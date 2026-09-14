from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import psutil

from core.resource_governor import ResourceGovernor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


class WorkspaceConnectionManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        message = json.dumps(payload, ensure_ascii=False, default=str)
        with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_text(message)
            except Exception:
                dead.append(client)
        if dead:
            with self._lock:
                for client in dead:
                    self._clients.discard(client)

    def publish_from_thread(self, payload: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(payload), loop)


class WorkspaceServer:
    def __init__(
        self,
        base_dir: Path,
        config,
        command_handler: Callable[[dict[str, Any]], None],
        snapshot_provider: Callable[[], dict[str, Any]],
        profile_store=None,
        on_client_connected: Callable[[], None] | None = None,
    ) -> None:
        self.base_dir = base_dir
        self.config = config
        self.command_handler = command_handler
        self.snapshot_provider = snapshot_provider
        self.profile_store = profile_store
        self.on_client_connected = on_client_connected
        self.manager = WorkspaceConnectionManager()
        self.resource_governor = ResourceGovernor(config)
        self.app = FastAPI(title="JARVIS Workspace API", version="29.1")
        self._configure_routes()

    def _configure_routes(self) -> None:
        app = self.app
        manager = self.manager
        dist = self.base_dir / "workspace_ui" / "dist"
        assets = dist / "assets"

        @app.on_event("startup")
        async def _startup() -> None:
            manager.bind_loop(asyncio.get_running_loop())
            asyncio.create_task(self._metrics_loop())

        @app.get("/api/health")
        async def health() -> dict[str, Any]:
            return {"ok": True, "version": 29, "build": "29.1"}

        @app.get("/api/profiles")
        async def profiles() -> JSONResponse:
            return JSONResponse(self.profile_store.list() if self.profile_store is not None else {})

        @app.post("/api/profiles/{name}")
        async def save_profile(name: str, payload: dict[str, Any]) -> JSONResponse:
            if self.profile_store is None:
                return JSONResponse({"ok": False, "error": "Profile store unavailable"}, status_code=503)
            saved = self.profile_store.save(name, payload)
            return JSONResponse({"ok": True, "profile": saved})

        @app.delete("/api/profiles/{name}")
        async def delete_profile(name: str) -> JSONResponse:
            if self.profile_store is None:
                return JSONResponse({"ok": False}, status_code=503)
            return JSONResponse({"ok": self.profile_store.delete(name)})

        @app.get("/api/snapshot")
        async def snapshot() -> JSONResponse:
            return JSONResponse(self.snapshot_provider())

        @app.get("/api/widgets")
        async def widgets() -> JSONResponse:
            manifest = self.base_dir / "workspace_ui" / "widget_manifest.json"
            try:
                return JSONResponse(json.loads(manifest.read_text(encoding="utf-8")))
            except Exception:
                return JSONResponse([])

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            await manager.connect(websocket)
            try:
                await websocket.send_text(json.dumps({"type": "snapshot", "payload": self.snapshot_provider()}, ensure_ascii=False, default=str))
                if self.on_client_connected is not None:
                    try:
                        self.on_client_connected()
                    except Exception:
                        pass
                while True:
                    raw = await websocket.receive_text()
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    self.command_handler(payload if isinstance(payload, dict) else {})
            except WebSocketDisconnect:
                pass
            finally:
                await manager.disconnect(websocket)

        if assets.exists():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/")
        async def index() -> FileResponse:
            index_file = dist / "index.html"
            if not index_file.exists():
                raise RuntimeError("Workspace UI has not been built. Run scripts/rebuild_workspace.ps1")
            return FileResponse(index_file, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"})

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            candidate = dist / full_path
            if candidate.exists() and candidate.is_file():
                return FileResponse(candidate, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"})
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"})

    async def _metrics_loop(self) -> None:
        while True:
            try:
                battery = psutil.sensors_battery()
                metrics = self.resource_governor.snapshot().to_dict()
                metrics["battery"] = None if battery is None else round(float(battery.percent), 1)
                payload = {
                    "type": "system_metrics",
                    "payload": metrics,
                }
                await self.manager.broadcast(payload)
            except Exception:
                pass
            await asyncio.sleep(2.0)

    def publish(self, event_type: str, payload: Any) -> None:
        self.manager.publish_from_thread({"type": event_type, "payload": payload})
