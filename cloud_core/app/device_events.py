from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import threading
import uuid


class DeviceEventStore:
    """Volatile event buffer for live device telemetry.

    Phone call state is operational state, not long-term user memory.
    """

    def __init__(self, max_events_per_device: int = 100):
        self.max_events_per_device = max(10, int(max_events_per_device))
        self._events: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_events_per_device)
        )
        self._lock = threading.RLock()

    def record(
        self,
        *,
        device_id: str,
        event_type: str,
        payload: dict | None = None,
        event_id: str | None = None,
        occurred_at: str | None = None,
    ) -> dict:
        event = {
            "event_id": event_id or uuid.uuid4().hex,
            "device_id": device_id,
            "event_type": event_type,
            "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
            "payload": dict(payload or {}),
        }
        with self._lock:
            self._events[device_id].append(event)
        return event

    def recent(self, device_id: str, limit: int = 20) -> list[dict]:
        safe_limit = max(1, min(int(limit), self.max_events_per_device))
        with self._lock:
            rows = list(self._events.get(device_id, ()))
        return rows[-safe_limit:][::-1]


device_event_store = DeviceEventStore()
