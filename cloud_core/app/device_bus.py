from datetime import datetime, timezone
from fastapi import WebSocket


class DeviceManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}
        self.metadata: dict[str, dict] = {}

    async def connect(self, device_id: str, device_type: str, websocket: WebSocket):
        await websocket.accept()

        old = self.connections.get(device_id)
        if old is not None:
            try:
                await old.close(code=1000)
            except Exception:
                pass

        self.connections[device_id] = websocket
        self.metadata[device_id] = {
            "device_id": device_id,
            "device_type": device_type,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

    def disconnect(self, device_id: str):
        self.connections.pop(device_id, None)
        self.metadata.pop(device_id, None)

    async def send_json(self, device_id: str, payload: dict):
        ws = self.connections.get(device_id)
        if ws is None:
            return False

        await ws.send_json(payload)
        return True

    def list_devices(self):
        return list(self.metadata.values())


device_manager = DeviceManager()
