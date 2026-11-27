"""Transport for the isolated Conversation frame in the native Control Center."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject, QUrl, Signal, Slot
from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineScript, QWebEngineUrlRequestJob,
    QWebEngineUrlScheme, QWebEngineUrlSchemeHandler,
)
from shiboken6 import isValid


SCHEME = b"jarvis-chat"
FRAME = "jarvis-chat://desktop/conversation"
DIST = Path(__file__).resolve().parents[1] / "workspace_ui" / "dist"


def register_scheme():
    if QWebEngineUrlScheme.schemeByName(SCHEME).name():
        return
    scheme = QWebEngineUrlScheme(SCHEME)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme | QWebEngineUrlScheme.Flag.FetchApiAllowed)
    QWebEngineUrlScheme.registerScheme(scheme)


class DashboardPage(QWebEnginePage):
    def __init__(self, profile, url, parent):
        super().__init__(profile, parent)
        self.home = QUrl(url)
        self.pinned = (self.home.scheme() == "http" and self.home.host() == "127.0.0.1"
                       and self.home.port() > 0 and self.home.path() in ("", "/")
                       and not self.home.userInfo() and not self.home.hasFragment())
        self.origin = f"http://127.0.0.1:{self.home.port()}"
        if self.pinned:
            hint = QWebEngineScript()
            hint.setName("JARVIS desktop conversation available")
            hint.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            hint.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            hint.setRunsOnSubFrames(False)
            hint.setSourceCode("Object.defineProperty(window, 'jarvisDesktopChat', {value:true})")
            self.scripts().insert(hint)

    def at_dashboard(self):
        return self.pinned and self.url() == self.home

    def acceptNavigationRequest(self, url, kind, is_main):
        if not self.pinned:
            return is_main and url == self.home
        if is_main:
            return url == self.home
        return self.at_dashboard() and url.toString() == FRAME


class ConversationHandler(QWebEngineUrlSchemeHandler):
    finished = Signal(object, object)
    settings_requested = Signal(str, str)

    def __init__(self, page, brain_factory, ask_private):
        super().__init__(page)
        self.page = page
        self.brain_factory = brain_factory
        self.ask_private = ask_private
        self.busy = False
        self.finished.connect(self._finish)

    @staticmethod
    def _reply(job, mime, data):
        buffer = QBuffer(job)
        buffer.setData(QByteArray(data))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        job.setAdditionalResponseHeaders({
            QByteArray(b"Cache-Control"): QByteArray(b"no-store"),
            QByteArray(b"Referrer-Policy"): QByteArray(b"no-referrer"),
        })
        job.reply(mime, buffer)

    def requestStarted(self, job):
        url = job.requestUrl()
        initiator = job.initiator().toString().rstrip("/")
        method = bytes(job.requestMethod())
        private_origin = "jarvis-chat://desktop"
        if (not self.page.at_dashboard() or url.host() != "desktop" or url.hasQuery()
                or url.hasFragment() or url.userInfo() or url.port() != -1):
            return job.fail(QWebEngineUrlRequestJob.Error.RequestDenied)
        route = url.path()
        if route == "/conversation" and method == b"GET" and initiator == self.page.origin:
            return self._reply(job, b"text/html", (DIST / "private-conversation.html").read_bytes())
        if initiator != private_origin:
            return job.fail(QWebEngineUrlRequestJob.Error.RequestDenied)
        assets = {"/workspace.css": b"text/css", "/private-conversation.js": b"text/javascript"}
        if route in assets and method == b"GET":
            return self._reply(job, assets[route], (DIST / route[1:]).read_bytes())
        if method != b"POST" or route not in ("/state", "/ask", "/providers", "/memory"):
            return job.fail(QWebEngineUrlRequestJob.Error.RequestDenied)
        try:
            device = job.requestBody()
            if device is None or (not device.isOpen() and not device.open(QIODevice.OpenModeFlag.ReadOnly)):
                raise ValueError
            raw = bytes(device.read(100_001))
            if len(raw) > 100_000:
                raise ValueError
            data = json.loads(raw)
            project = data.get("project", "")
            if not isinstance(project, str) or len(project) > 256 or (project and not project.isprintable()):
                raise ValueError
            question = data.get("question", "")
            if not isinstance(question, str) or len(question) > 16000 or (route == "/ask" and not question.strip()):
                raise ValueError
        except (ValueError, AttributeError, TypeError, RecursionError):
            return job.fail(QWebEngineUrlRequestJob.Error.RequestDenied)
        if route in ("/providers", "/memory"):
            self.settings_requested.emit(route[1:], project)
            return self._reply(job, b"application/json", b"{}")
        if self.busy:
            return self._reply(job, b"application/json", b'{"error":"A private request is in progress."}')
        self.busy = True

        def work():
            try:
                brain = self.brain_factory()
                if route == "/ask":
                    result = {"answer": (self.ask_private or brain.ask)(project, question)}
                else:
                    result = {"collections": brain.memory.collections()}
                status = brain.status()
                result.update(active=status["active"], error=status["error"])
            except Exception as exc:
                from workspace.private_ai_dialog import _safe_error
                result = {"error": _safe_error(exc)}
            try:
                self.finished.emit(job, result)
            except RuntimeError:
                pass

        threading.Thread(target=work, daemon=True, name="jarvis-dashboard-chat").start()

    @Slot(object, object)
    def _finish(self, job, result):
        self.busy = False
        if isValid(job) and self.page.at_dashboard():
            self._reply(job, b"application/json", json.dumps(result).encode())
