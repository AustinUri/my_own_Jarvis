from __future__ import annotations

import urllib.parse
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal


class NativeSurfaceController(QObject):
    """Qt-signal bridge for the V29 native Surface pane.

    Unlike the V28 screenshot streamer, this controller does not own a browser
    process or perform network I/O itself. The actual QWebEngineView lives as a
    sibling widget in the JARVIS window, so renderer failures stay isolated from
    the Control Center page.
    """

    open_requested = Signal(str, str)
    close_requested = Signal()
    back_requested = Signal()
    forward_requested = Signal()
    reload_requested = Signal()

    def __init__(self, publish: Callable[[str, Any], None] | None = None) -> None:
        super().__init__()
        self.publish = publish or (lambda *_: None)
        self._status: dict[str, Any] = {
            'ok': True,
            'mode': 'native-pane',
            'active': False,
            'url': '',
            'title': '',
            'message': 'Native Surface is idle.',
        }

    @staticmethod
    def normalize_url(value: str) -> str:
        raw = (value or '').strip()
        if not raw or raw.lower() == 'about:blank':
            return ''
        if '://' not in raw:
            if '.' not in raw or ' ' in raw:
                return 'https://www.google.com/search?q=' + urllib.parse.quote_plus(raw)
            raw = 'https://' + raw
        parsed = urllib.parse.urlparse(raw)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            return ''
        return raw

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def _emit_status(self, **updates: Any) -> dict[str, Any]:
        self._status.update(updates)
        payload = dict(self._status)
        self.publish('surface_status', payload)
        return payload

    def open(self, value: str, title: str = '') -> dict[str, Any]:
        url = self.normalize_url(value)
        if not url:
            return self._emit_status(ok=False, message='Surface URL is invalid or blank.')
        host = urllib.parse.urlparse(url).netloc
        self.open_requested.emit(url, title or host)
        return self._emit_status(ok=True, active=True, url=url, title=title or host,
                                 message='Opened in the isolated native Surface pane.')

    def close(self) -> dict[str, Any]:
        self.close_requested.emit()
        return self._emit_status(ok=True, active=False, message='Surface pane closed.')

    def back(self) -> dict[str, Any]:
        self.back_requested.emit()
        return self.status()

    def forward(self) -> dict[str, Any]:
        self.forward_requested.emit()
        return self.status()

    def reload(self) -> dict[str, Any]:
        self.reload_requested.emit()
        return self.status()

    def update_from_shell(self, *, url: str | None = None, title: str | None = None,
                          active: bool | None = None, ok: bool | None = None,
                          message: str | None = None) -> None:
        updates: dict[str, Any] = {}
        if url is not None and url.lower() != 'about:blank':
            updates['url'] = url
        if title is not None:
            updates['title'] = title
        if active is not None:
            updates['active'] = active
        if ok is not None:
            updates['ok'] = ok
        if message is not None:
            updates['message'] = message
        if updates:
            self._emit_status(**updates)
