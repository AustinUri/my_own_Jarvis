from __future__ import annotations

import subprocess
import webbrowser
import threading
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

try:
    from workspace.integrated_shell import JarvisIntegratedShell
except Exception:
    JarvisIntegratedShell = None


class WorkspaceTray:
    def __init__(self, app: QApplication, orchestrator, url: str, quit_callback, service_manager=None, surface_controller=None):
        self.app = app
        self.orchestrator = orchestrator
        self.url = url.rstrip('/') + '/?build=29.2'
        self.quit_callback = quit_callback
        self.service_manager = service_manager
        self.workspace_window = None
        if JarvisIntegratedShell is not None:
            try:
                self.workspace_window = JarvisIntegratedShell(self.url, build='29.2', surface_controller=surface_controller)
            except Exception:
                self.workspace_window = None
        self.icon = QSystemTrayIcon(self._make_icon(), app)
        self.icon.setToolTip('JARVIS v29.2 — background runtime active')
        self.menu = QMenu()

        open_action = QAction('Open JARVIS Control Center', self.menu)
        open_action.triggered.connect(self.open_workspace)
        self.menu.addAction(open_action)

        listen_action = QAction('Push-to-talk', self.menu)
        listen_action.triggered.connect(orchestrator.process_push_to_talk)
        self.menu.addAction(listen_action)

        wake_action = QAction('Toggle wake word', self.menu)
        wake_action.triggered.connect(orchestrator.toggle_wake_word)
        self.menu.addAction(wake_action)

        voice_action = QAction('Mute / unmute voice', self.menu)
        voice_action.triggered.connect(orchestrator.toggle_voice)
        self.menu.addAction(voice_action)

        if service_manager is not None:
            services_action = QAction('Check / restart local services', self.menu)
            services_action.triggered.connect(lambda: threading.Thread(target=service_manager.ensure_all, name='jarvis-service-check', daemon=True).start())
            self.menu.addAction(services_action)

        self.menu.addSeparator()
        quit_action = QAction('Quit JARVIS Completely', self.menu)
        quit_action.triggered.connect(self.quit_callback)
        self.menu.addAction(quit_action)

        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)
        self.icon.show()

    def _activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            self.open_workspace()

    def open_workspace(self) -> None:
        # Preferred V29 path: the Control Center itself is a native Qt
        # Chromium shell, allowing Surface Dock pages to remain inside the
        # same JARVIS window even when a site rejects iframe embedding.
        if self.workspace_window is not None:
            self.workspace_window.open_workspace()
            return

        # Compatibility fallback only when Qt WebEngine cannot initialize.
        candidates = [
            Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'),
            Path(r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'),
            Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
            Path(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'),
        ]
        for exe in candidates:
            if exe.exists():
                try:
                    subprocess.Popen([str(exe), f'--app={self.url}', '--start-maximized'], close_fds=True)
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
        p.setBrush(QColor('#42d8ff'))
        p.setPen(QColor('#b6f4ff'))
        p.drawEllipse(10, 10, 44, 44)
        p.end()
        return QIcon(pix)
