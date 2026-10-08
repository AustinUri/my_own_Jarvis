from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket


class DeviceManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}
        self.metadata: dict[str, dict] = {}
        self.pending_jobs: dict[str, tuple[str, asyncio.Future]] = {}

    async def connect(
        self,
        device_id: str,
        device_type: str,
        websocket: WebSocket,
    ):
        await websocket.accept()

        old = self.connections.get(device_id)

        self.connections[device_id] = websocket
        self.metadata[device_id] = {
            "device_id": device_id,
            "device_type": device_type,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        if old is not None and old is not websocket:
            try:
                await old.close(code=1000)
            except Exception:
                pass

    def disconnect(
        self,
        device_id: str,
        websocket: WebSocket | None = None,
    ):
        current = self.connections.get(device_id)

        # An older socket may finish closing after a replacement socket has
        # already connected. Do not let the old socket remove the new one.
        if websocket is not None and current is not websocket:
            return

        self.connections.pop(device_id, None)
        self.metadata.pop(device_id, None)

        for job_id, (target_device, future) in list(self.pending_jobs.items()):
            if target_device != device_id:
                continue

            self.pending_jobs.pop(job_id, None)

            if not future.done():
                future.set_exception(
                    ConnectionError(
                        f"Device '{device_id}' disconnected while job was running"
                    )
                )

    def is_connected(self, device_id: str) -> bool:
        return device_id in self.connections

    async def send_json(self, device_id: str, payload: dict) -> bool:
        ws = self.connections.get(device_id)

        if ws is None:
            return False

        await ws.send_json(payload)
        return True

    async def request(
        self,
        device_id: str,
        job_type: str,
        payload: dict,
        timeout: float = 240.0,
    ) -> dict:
        ws = self.connections.get(device_id)

        if ws is None:
            raise ConnectionError(
                f"Device '{device_id}' is not connected"
            )

        job_id = uuid.uuid4().hex
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        self.pending_jobs[job_id] = (device_id, future)

        try:
            await ws.send_json({
                "type": "job",
                "job_id": job_id,
                "job_type": job_type,
                "payload": payload,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            result = await asyncio.wait_for(
                future,
                timeout=timeout,
            )

            if not isinstance(result, dict):
                raise RuntimeError(
                    "Device returned an invalid job result"
                )

            return result

        finally:
            self.pending_jobs.pop(job_id, None)

    def resolve_job_result(
        self,
        device_id: str,
        payload: dict,
    ) -> bool:
        job_id = str(payload.get("job_id") or "")
        pending = self.pending_jobs.get(job_id)

        if pending is None:
            return False

        target_device, future = pending

        if target_device != device_id:
            return False

        if not future.done():
            future.set_result(payload)

        return True

    def list_devices(self):
        return list(self.metadata.values())


device_manager = DeviceManager()
