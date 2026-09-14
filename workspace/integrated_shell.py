from __future__ import annotations

from pathlib import Path
import urllib.parse

from PySide6.QtCore import QUrl, QStandardPaths, Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QLabel
)

try:
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception:  # pragma: no cover
    QWebEnginePage = QWebEngineProfile = QWebEngineSettings = QWebEngineView = None


class JarvisIntegratedShell(QMainWindow):
    """V29 native Control Center + isolated Surface browser.

    The Control Center and remote site are sibling QWebEngineViews inside one Qt
    window. Nothing is iframe-embedded and no screenshot streaming is used. This
    avoids V28's browser-stream crashes while keeping websites inside JARVIS.
    """

    def __init__(self, workspace_url: str, build: str = '29.1', surface_controller=None) -> None:
        if QWebEngineView is None:
            raise RuntimeError('Qt WebEngine is not available')
        super().__init__()
        self.workspace_url = workspace_url
        self.build = build
        self.surface_controller = surface_controller
        self._surface_recovery_count = 0
        self._manual_split = False

        self.setWindowTitle(f'JARVIS v{build} · HOLO CORE')
        self.resize(1660, 980)
        self.setMinimumSize(1120, 720)

        app_root = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        app_root.mkdir(parents=True, exist_ok=True)

        self.control_profile = QWebEngineProfile('JarvisControl', self)
        self.control_profile.setPersistentStoragePath(str(app_root / 'control_profile' / 'storage'))
        self.control_profile.setCachePath(str(app_root / 'control_profile' / 'cache'))
        self.surface_profile = QWebEngineProfile('JarvisSurface', self)
        self.surface_profile.setPersistentStoragePath(str(app_root / 'surface_profile' / 'storage'))
        self.surface_profile.setCachePath(str(app_root / 'surface_profile' / 'cache'))
        for profile in (self.control_profile, self.surface_profile):
            try:
                profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            except Exception:
                pass

        self.control_view = QWebEngineView(self)
        self.control_view.setPage(QWebEnginePage(self.control_profile, self.control_view))
        self.control_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.control_view.setUrl(QUrl(self.workspace_url))

        self.surface_view = QWebEngineView(self)
        self.surface_view.setPage(QWebEnginePage(self.surface_profile, self.surface_view))
        self.surface_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        try:
            self.surface_view.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        except Exception:
            pass

        self.surface_address = QLineEdit(self)
        self.surface_address.setPlaceholderText('Surface URL')
        self.surface_title = QLabel('SURFACE · NATIVE', self)
        self.surface_back = QPushButton('←', self)
        self.surface_forward = QPushButton('→', self)
        self.surface_reload = QPushButton('↻', self)
        self.surface_close = QPushButton('×', self)
        self.surface_go = QPushButton('Go', self)

        bar = QHBoxLayout()
        bar.setContentsMargins(8, 6, 8, 6)
        bar.setSpacing(5)
        bar.addWidget(self.surface_title)
        bar.addWidget(self.surface_back)
        bar.addWidget(self.surface_forward)
        bar.addWidget(self.surface_reload)
        bar.addWidget(self.surface_address, 1)
        bar.addWidget(self.surface_go)
        bar.addWidget(self.surface_close)

        self.surface_widget = QWidget(self)
        self.surface_widget.setStyleSheet('''
            QWidget { background: #07111a; color: #d9f7ff; }
            QLineEdit { background: #0b1b28; color: #e9fbff; border: 1px solid #23485d; border-radius: 6px; padding: 7px; }
            QPushButton { background: #102a39; color: #bfefff; border: 1px solid #28556c; border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background: #15384b; }
            QLabel { color: #8fefff; font-weight: 700; padding-left: 4px; }
        ''')
        surface_layout = QVBoxLayout(self.surface_widget)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)
        surface_layout.addLayout(bar)
        surface_layout.addWidget(self.surface_view, 1)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.control_view)
        self.splitter.addWidget(self.surface_widget)
        self.setCentralWidget(self.splitter)
        self.surface_widget.hide()

        self.surface_back.clicked.connect(self.surface_view.back)
        self.surface_forward.clicked.connect(self.surface_view.forward)
        self.surface_reload.clicked.connect(self.surface_view.reload)
        self.surface_close.clicked.connect(self.close_surface)
        self.surface_go.clicked.connect(lambda: self.open_surface(self.surface_address.text()))
        self.surface_address.returnPressed.connect(lambda: self.open_surface(self.surface_address.text()))
        self.surface_view.urlChanged.connect(self._surface_url_changed)
        self.surface_view.titleChanged.connect(self._surface_title_changed)
        self.surface_view.loadFinished.connect(self._surface_load_finished)
        self.splitter.splitterMoved.connect(lambda *_: setattr(self, '_manual_split', True))
        try:
            self.surface_view.page().renderProcessTerminated.connect(self._surface_renderer_terminated)
        except Exception:
            pass

        if self.surface_controller is not None:
            self.surface_controller.open_requested.connect(self.open_surface)
            self.surface_controller.close_requested.connect(self.close_surface)
            self.surface_controller.back_requested.connect(self.surface_view.back)
            self.surface_controller.forward_requested.connect(self.surface_view.forward)
            self.surface_controller.reload_requested.connect(self.surface_view.reload)

    def _site_ratio(self, url: str) -> float:
        host = (urllib.parse.urlparse(url).netloc or '').lower()
        if any(x in host for x in ('youtube.com', 'youtu.be', 'netflix.com', 'vimeo.com')):
            return 0.76
        if any(x in host for x in ('github.com', 'gitlab.com', 'docs.', 'developer.')):
            return 0.68
        if any(x in host for x in ('google.com', 'bing.com', 'duckduckgo.com')):
            return 0.62
        return 0.66

    def _apply_surface_ratio(self, url: str) -> None:
        if self._manual_split:
            return
        total = max(1000, self.width() - 20)
        ratio = self._site_ratio(url)
        surface = int(total * ratio)
        control = max(360, total - surface)
        self.splitter.setSizes([control, surface])

    def open_surface(self, value: str, title: str = '') -> None:
        url = str(value or '').strip()
        if not url or url.lower() == 'about:blank':
            return
        if '://' not in url:
            url = 'https://' + url
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            return
        self._surface_recovery_count = 0
        self._manual_split = False
        self.surface_widget.show()
        self.surface_title.setText((title or parsed.netloc or 'SURFACE').upper()[:48])
        self.surface_address.setText(url)
        self._apply_surface_ratio(url)
        self.surface_view.setUrl(QUrl(url))
        if self.surface_controller is not None:
            self.surface_controller.update_from_shell(url=url, title=title or parsed.netloc, active=True, ok=True,
                                                      message='Native Surface loading…')

    def close_surface(self) -> None:
        try:
            self.surface_view.stop()
            self.surface_view.setUrl(QUrl('about:blank'))
        except Exception:
            pass
        self.surface_widget.hide()
        self._manual_split = False
        if self.surface_controller is not None:
            self.surface_controller.update_from_shell(active=False, ok=True, message='Native Surface closed.')

    def _surface_url_changed(self, qurl: QUrl) -> None:
        url = qurl.toString()
        if not url or url.lower() == 'about:blank':
            return
        self.surface_address.setText(url)
        self._apply_surface_ratio(url)
        if self.surface_controller is not None:
            self.surface_controller.update_from_shell(url=url, active=True)

    def _surface_title_changed(self, title: str) -> None:
        if title:
            self.surface_title.setText(title[:52])
            if self.surface_controller is not None:
                self.surface_controller.update_from_shell(title=title)

    def _surface_load_finished(self, ok: bool) -> None:
        if self.surface_controller is not None:
            self.surface_controller.update_from_shell(
                ok=bool(ok), active=True,
                message='Native Surface ready.' if ok else 'Surface page failed to load.'
            )

    def _surface_renderer_terminated(self, *_args) -> None:
        self._surface_recovery_count += 1
        url = self.surface_address.text().strip()
        if self.surface_controller is not None:
            self.surface_controller.update_from_shell(
                ok=False, active=True,
                message='Surface renderer restarted after a page crash.'
            )
        # Renderer is separate from JARVIS. Try one controlled reload; after that
        # leave the pane visible with the failure state instead of looping.
        if self._surface_recovery_count <= 1 and url:
            QTimer.singleShot(900, lambda: self.surface_view.setUrl(QUrl(url)))

    def open_workspace(self) -> None:
        if self.control_view.url().toString().split('?')[0] != self.workspace_url.split('?')[0]:
            self.control_view.setUrl(QUrl(self.workspace_url))
        self.showMaximized()
        self.raise_()
        self.activateWindow()
