from __future__ import annotations

import subprocess
import webbrowser
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class WorkspaceTray:
    def __init__(self, app: QApplication, orchestrator, url: str, quit_callback):
        self.app = app
        self.orchestrator = orchestrator
        self.url = url
        self.quit_callback = quit_callback
        self.icon = QSystemTrayIcon(self._make_icon(), app)
        self.icon.setToolTip("JARVIS v23")
        self.menu = QMenu()

        open_action = QAction("Open JARVIS Workspace", self.menu)
        open_action.triggered.connect(self.open_workspace)
        self.menu.addAction(open_action)

        listen_action = QAction("Push-to-talk", self.menu)
        listen_action.triggered.connect(orchestrator.process_push_to_talk)
        self.menu.addAction(listen_action)

        wake_action = QAction("Toggle wake word", self.menu)
        wake_action.triggered.connect(orchestrator.toggle_wake_word)
        self.menu.addAction(wake_action)

        voice_action = QAction("Mute / unmute voice", self.menu)
        voice_action.triggered.connect(orchestrator.toggle_voice)
        self.menu.addAction(voice_action)

        self.menu.addSeparator()
        quit_action = QAction("Quit JARVIS", self.menu)
        quit_action.triggered.connect(self.quit_callback)
        self.menu.addAction(quit_action)

        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)
        self.icon.show()

    def _activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            self.open_workspace()

    def open_workspace(self) -> None:
        # Prefer an app-style Edge/Chrome window; fall back to the default browser.
        candidates = [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ]
        for exe in candidates:
            if exe.exists():
                try:
                    subprocess.Popen([str(exe), f"--app={self.url}", "--start-maximized"], close_fds=True)
                    return
                except OSError:
                    pass
        if not QDesktopServices.openUrl(QUrl(self.url)):
            webbrowser.open(self.url)

    @staticmethod
    def _make_icon() -> QIcon:
        pix = QPixmap(64, 64)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#f7a53b"))
        p.setPen(QColor("#ffd486"))
        p.drawEllipse(10, 10, 44, 44)
        p.end()
        return QIcon(pix)
