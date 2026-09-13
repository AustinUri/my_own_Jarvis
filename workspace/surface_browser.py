from __future__ import annotations

import webbrowser
from urllib.parse import urlparse

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QMainWindow

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception:
    QWebEngineView = None


def normalize_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return raw


class SurfaceBrowser:
    """Real Chromium surface for sites that reject iframe embedding.

    We do not strip X-Frame-Options or CSP. If Qt WebEngine is not available,
    the system browser is used instead.
    """
    def __init__(self) -> None:
        self.window: QMainWindow | None = None
        self.view = None

    def open(self, target: str) -> dict:
        url = normalize_url(target)
        if not url:
            return {"ok": False, "mode": "none", "error": "Invalid web address."}
        host = urlparse(url).netloc
        if QWebEngineView is None:
            webbrowser.open(url)
            return {"ok": True, "mode": "system-browser", "url": url,
                    "message": "Qt WebEngine is unavailable; opened in your default browser."}
        if self.window is None:
            self.window = QMainWindow()
            self.window.resize(1280, 820)
            self.view = QWebEngineView(self.window)
            self.window.setCentralWidget(self.view)
        self.window.setWindowTitle(f"JARVIS Surface Browser — {host}")
        self.view.setUrl(QUrl(url))
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        return {"ok": True, "mode": "jarvis-surface-browser", "url": url,
                "message": f"Opened {host} in the JARVIS Surface Browser."}
