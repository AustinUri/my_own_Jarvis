from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass(slots=True)
class CameraSnapshot:
    data_url: str
    captured_at: float
    width: int = 0
    height: int = 0


class CameraState:
    """Thread-safe latest-frame store for the workspace camera.

    The browser owns camera permission.  It sends a modest JPEG preview frame to
    the local Jarvis runtime while the camera widget is explicitly enabled.
    Nothing is written to disk.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: CameraSnapshot | None = None
        self._enabled = False

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = bool(enabled)
            if not enabled:
                self._snapshot = None

    def update(self, data_url: str, width: int = 0, height: int = 0) -> bool:
        if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
            return False
        # Local WebSocket messages should stay small.  A 640x480 JPEG is usually
        # well below this ceiling; reject accidental full-resolution dumps.
        if len(data_url) > 2_500_000:
            return False
        with self._lock:
            self._enabled = True
            self._snapshot = CameraSnapshot(
                data_url=data_url,
                captured_at=time.time(),
                width=max(0, int(width or 0)),
                height=max(0, int(height or 0)),
            )
        return True

    def latest(self, max_age_seconds: float = 8.0) -> CameraSnapshot | None:
        with self._lock:
            snap = self._snapshot
            enabled = self._enabled
        if not enabled or snap is None:
            return None
        if time.time() - snap.captured_at > max(1.0, float(max_age_seconds)):
            return None
        return snap

    def status(self) -> dict[str, object]:
        with self._lock:
            snap = self._snapshot
            enabled = self._enabled
        return {
            "enabled": enabled,
            "hasFrame": snap is not None,
            "capturedAt": None if snap is None else snap.captured_at,
            "width": 0 if snap is None else snap.width,
            "height": 0 if snap is None else snap.height,
        }
