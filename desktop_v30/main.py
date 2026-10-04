import json
import math
import os
import threading
import urllib.request

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSettings
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


CLOUD = "https://uri-jarvis.duckdns.org"


class CloudBridge(QObject):
    updated = Signal(str)


class StarkCore(QWidget):
    def __init__(self):
        super().__init__()
        self.phase = 0.0
        self.setMinimumSize(480, 480)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(35)

    def animate(self):
        self.phase += 1.1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2 - 5

        pulse = (math.sin(math.radians(self.phase * 2.3)) + 1) / 2

        # Soft outer holographic glow
        glow = QRadialGradient(cx, cy, 205)
        glow.setColorAt(0.00, QColor(255, 174, 55, 115))
        glow.setColorAt(0.20, QColor(255, 126, 20, 65))
        glow.setColorAt(0.48, QColor(42, 206, 232, 30))
        glow.setColorAt(1.00, QColor(0, 0, 0, 0))

        p.setBrush(glow)
        p.setPen(Qt.NoPen)
        p.drawEllipse(
            int(cx - 205),
            int(cy - 205),
            410,
            410,
        )

        # Main sphere rings
        for r, alpha, width in [
            (82, 220, 2.2),
            (112, 165, 1.6),
            (148, 105, 1.2),
            (176, 55, 1.0),
        ]:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 181, 67, alpha), width))
            p.drawEllipse(
                int(cx - r),
                int(cy - r),
                r * 2,
                r * 2,
            )

        # Cyan spherical lattice
        p.setPen(QPen(QColor(86, 224, 245, 115), 1.1))

        for squash in [0.34, 0.60]:
            h = int(290 * squash)
            p.drawEllipse(
                int(cx - 145),
                int(cy - h / 2),
                290,
                h,
            )

        # Data arcs
        arcs = [
            (124, self.phase * 4, 85),
            (154, -self.phase * 2.7 + 80, 62),
            (187, self.phase * 1.8 + 160, 40),
        ]

        for radius, start, span in arcs:
            p.setPen(QPen(QColor(255, 169, 58, 190), 2.0))
            p.drawArc(
                int(cx - radius),
                int(cy - radius),
                radius * 2,
                radius * 2,
                int(start * 16),
                int(span * 16),
            )

        # Orbiting neutrino/data nodes
        for i in range(34):
            direction = 1 if i % 2 == 0 else -1

            angle = math.radians(
                self.phase * direction * (1.1 + (i % 5) * 0.06)
                + i * 27
            )

            radius = 92 + ((i * 31) % 92)

            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius * (0.67 + (i % 3) * 0.08)

            size = 2.5 + (i % 4)

            if i % 5 == 0:
                color = QColor(104, 235, 255, 230)
            else:
                color = QColor(255, 184, 69, 205)

            p.setBrush(color)
            p.setPen(Qt.NoPen)

            p.drawEllipse(
                int(x - size / 2),
                int(y - size / 2),
                int(size),
                int(size),
            )

        # HUD ticks
        p.setPen(QPen(QColor(110, 225, 242, 105), 1))

        for i in range(48):
            a = math.radians(i * 7.5 + self.phase * 0.12)

            r1 = 193
            r2 = 199 if i % 4 else 204

            x1 = cx + math.cos(a) * r1
            y1 = cy + math.sin(a) * r1
            x2 = cx + math.cos(a) * r2
            y2 = cy + math.sin(a) * r2

            p.drawLine(
                int(x1),
                int(y1),
                int(x2),
                int(y2),
            )

        # Inner reactor/core
        inner_r = 45 + int(pulse * 5)

        core = QRadialGradient(cx, cy, inner_r)
        core.setColorAt(0.0, QColor(255, 244, 205, 245))
        core.setColorAt(0.18, QColor(255, 190, 72, 235))
        core.setColorAt(0.55, QColor(255, 114, 24, 145))
        core.setColorAt(1.0, QColor(255, 80, 10, 0))

        p.setBrush(core)
        p.setPen(Qt.NoPen)

        p.drawEllipse(
            int(cx - inner_r),
            int(cy - inner_r),
            inner_r * 2,
            inner_r * 2,
        )

        p.setPen(QColor(229, 251, 255))
        font = QFont("Segoe UI", 11)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        p.setFont(font)

        p.drawText(
            int(cx - 80),
            int(cy - 10),
            160,
            20,
            Qt.AlignCenter,
            "J A R V I S",
        )

        p.setPen(QColor(114, 227, 243))
        p.setFont(QFont("Segoe UI", 8))

        p.drawText(
            int(cx - 80),
            int(cy + 14),
            160,
            18,
            Qt.AlignCenter,
            "V30 CORE",
        )


def placeholder(title, body):
    w = QWidget()
    layout = QVBoxLayout(w)

    heading = QLabel(title)
    heading.setStyleSheet(
        "font-size:22px;"
        "font-weight:600;"
        "color:#f2bd62;"
    )

    text = QLabel(body)
    text.setWordWrap(True)
    text.setStyleSheet(
        "color:#9ab2be;"
        "font-size:14px;"
    )

    layout.addWidget(heading)
    layout.addWidget(text)
    layout.addStretch()

    return w


class JarvisWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = QSettings("AustinUri", "JARVIS-V30")

        self.setWindowTitle("JARVIS V30")
        self.resize(1450, 900)

        self.setDockNestingEnabled(True)

        self.setDockOptions(
            QMainWindow.AllowNestedDocks
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.AnimatedDocks
        )

        self.cloud_bridge = CloudBridge()
        self.cloud_bridge.updated.connect(self.set_cloud_text)

        self.build_ui()
        self.build_docks()
        self.restore_user_layout()

        self.cloud_timer = QTimer(self)
        self.cloud_timer.timeout.connect(self.refresh_cloud)
        self.cloud_timer.start(10000)

        self.refresh_cloud()

    def build_ui(self):
        root = QWidget()

        root.setStyleSheet("""
            QWidget {
                background:#050c12;
                color:#e5f8ff;
                font-family:"Segoe UI";
            }

            QPushButton {
                background:#0a1822;
                color:#dbeef5;
                border:1px solid #173644;
                border-radius:7px;
                padding:10px;
                text-align:left;
                font-size:13px;
            }

            QPushButton:hover {
                border:1px solid #d59b42;
                background:#10202b;
                color:#ffd58b;
            }

            QPushButton:pressed {
                background:#182d39;
            }

            QDockWidget {
                color:#f2bd62;
                font-weight:600;
            }

            QDockWidget::title {
                background:#0b1a24;
                padding:8px;
                border-bottom:1px solid #284655;
            }

            QTextEdit {
                background:#08141d;
                border:1px solid #173644;
                border-radius:5px;
                color:#d7eef5;
                padding:8px;
            }
        """)

        container = QHBoxLayout(root)
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(220)

        sidebar.setStyleSheet(
            "background:#07151f;"
            "border-right:1px solid #203b48;"
        )

        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 18, 14, 18)

        logo = QLabel("J.A.R.V.I.S.")
        logo.setStyleSheet(
            "font-size:23px;"
            "font-weight:700;"
            "color:#f0b85d;"
        )

        side.addWidget(logo)

        version = QLabel("V30 · CLOUD NATIVE")
        version.setStyleSheet(
            "color:#71d9e9;"
            "font-size:11px;"
            "margin-bottom:12px;"
        )

        side.addWidget(version)

        navigation = [
            ("COMMAND CENTER", lambda: self.pages.setCurrentIndex(0)),
            ("SURFACE", lambda: self.pages.setCurrentIndex(1)),
            ("PHONE CENTER", lambda: self.show_dock("phone")),
            ("BUSINESS / eBAY", lambda: self.show_dock("business")),
            ("AGENT CENTER", lambda: self.show_dock("agents")),
            ("HOLOLAB", lambda: self.show_dock("hololab")),
            ("CODING JARVIS", lambda: self.show_dock("coding")),
            ("MEMORY", lambda: self.show_dock("memory")),
            ("MUSIC", lambda: self.show_dock("music")),
        ]

        for text, callback in navigation:
            b = QPushButton(text)
            b.clicked.connect(callback)
            side.addWidget(b)

        side.addStretch()

        library = QLabel("LAYOUT")
        library.setStyleSheet(
            "color:#7293a3;"
            "font-size:11px;"
            "font-weight:600;"
        )
        side.addWidget(library)

        b = QPushButton("SHOW ALL WIDGETS")
        b.clicked.connect(self.show_all_docks)
        side.addWidget(b)

        b = QPushButton("SAVE LAYOUT")
        b.clicked.connect(self.save_user_layout)
        side.addWidget(b)

        b = QPushButton("RESET LAYOUT")
        b.clicked.connect(self.reset_layout)
        side.addWidget(b)

        self.cloud_label = QLabel("● CONNECTING…")
        self.cloud_label.setWordWrap(True)

        self.cloud_label.setStyleSheet(
            "color:#65d9e9;"
            "font-size:11px;"
            "padding-top:10px;"
        )

        side.addWidget(self.cloud_label)

        container.addWidget(sidebar)

        self.pages = QStackedWidget()

        command = QWidget()
        command_layout = QVBoxLayout(command)
        command_layout.setContentsMargins(28, 20, 28, 20)

        title = QLabel("COMMAND CENTER")
        title.setStyleSheet(
            "font-size:21px;"
            "font-weight:600;"
            "color:#efc26f;"
        )

        command_layout.addWidget(title)

        subtitle = QLabel(
            "Native JARVIS workspace · Oracle Core · Device Bus"
        )

        subtitle.setStyleSheet(
            "color:#6b8997;"
        )

        command_layout.addWidget(subtitle)

        self.core = StarkCore()
        command_layout.addWidget(self.core, 1)

        self.pages.addWidget(command)

        surface = placeholder(
            "SURFACE",
            "Embedded JARVIS Surface workspace. "
            "The browser/content surface will live inside this native "
            "workspace — it will not replace the JARVIS GUI."
        )

        self.pages.addWidget(surface)

        container.addWidget(self.pages, 1)

        self.setCentralWidget(root)

    def make_dock(self, key, title, body):
        dock = QDockWidget(title, self)
        dock.setObjectName("jarvis_" + key)

        dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )

        content = QWidget()
        layout = QVBoxLayout(content)

        label = QLabel(body)
        label.setWordWrap(True)
        label.setStyleSheet("color:#8faab7;")

        layout.addWidget(label)

        text = QTextEdit()
        text.setPlaceholderText(
            title + " workspace..."
        )

        layout.addWidget(text, 1)

        dock.setWidget(content)

        self.docks[key] = dock

        return dock

    def build_docks(self):
        self.docks = {}

        conversation = self.make_dock(
            "conversation",
            "Conversation",
            "Live JARVIS conversation and activity stream."
        )

        phone = self.make_dock(
            "phone",
            "Phone Center",
            "Samsung V30 status, calls, contacts, calendar and WhatsApp."
        )

        business = self.make_dock(
            "business",
            "Business / eBay Center",
            "Listings, product research, inventory, margins, orders and automation."
        )

        agents = self.make_dock(
            "agents",
            "Agent Center",
            "Cloud agents, scheduled tasks and automation activity."
        )

        system = self.make_dock(
            "system",
            "System Monitor",
            "Oracle, Windows and Samsung connection status."
        )

        hololab = self.make_dock(
            "hololab",
            "HoloLab / Workbench",
            "Mechanical workspace, camera vision and future overhead-table view."
        )

        coding = self.make_dock(
            "coding",
            "Coding JARVIS",
            "Repository, development branch, diffs and coding-agent activity."
        )

        memory = self.make_dock(
            "memory",
            "Memory",
            "JARVIS long-term memory, project memory and retrieval."
        )

        music = self.make_dock(
            "music",
            "Music",
            "Playback, now-playing and device media control."
        )

        self.addDockWidget(Qt.RightDockWidgetArea, conversation)
        self.addDockWidget(Qt.RightDockWidgetArea, phone)

        self.tabifyDockWidget(conversation, phone)

        self.addDockWidget(Qt.BottomDockWidgetArea, system)

        for d in [
            business,
            agents,
            hololab,
            coding,
            memory,
            music,
        ]:
            self.addDockWidget(Qt.RightDockWidgetArea, d)
            d.hide()

        phone.hide()

    def show_dock(self, key):
        dock = self.docks[key]
        dock.show()
        dock.raise_()

    def show_all_docks(self):
        for dock in self.docks.values():
            dock.show()

    def save_user_layout(self):
        self.settings.setValue(
            "geometry",
            self.saveGeometry()
        )

        self.settings.setValue(
            "dockState",
            self.saveState()
        )

        self.cloud_label.setText(
            self.cloud_label.text()
            + "\nLayout saved."
        )

    def restore_user_layout(self):
        geometry = self.settings.value("geometry")
        state = self.settings.value("dockState")

        if geometry is not None:
            self.restoreGeometry(geometry)

        if state is not None:
            self.restoreState(state)

    def reset_layout(self):
        self.settings.remove("geometry")
        self.settings.remove("dockState")

        for dock in self.docks.values():
            dock.hide()

        conversation = self.docks["conversation"]
        system = self.docks["system"]

        self.addDockWidget(
            Qt.RightDockWidgetArea,
            conversation
        )

        self.addDockWidget(
            Qt.BottomDockWidgetArea,
            system
        )

        conversation.show()
        system.show()

        self.pages.setCurrentIndex(0)

    def refresh_cloud(self):
        threading.Thread(
            target=self.check_cloud,
            daemon=True,
        ).start()

    def check_cloud(self):
        try:
            with urllib.request.urlopen(
                CLOUD + "/api/v1/health",
                timeout=5,
            ) as r:
                health = json.loads(
                    r.read().decode()
                )

            text = (
                "● CLOUD ONLINE\n"
                + health.get("version", "V30")
            )

            token_file = os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Jarvis",
                "cloud.token",
            )

            if os.path.exists(token_file):
                with open(
                    token_file,
                    encoding="utf-8",
                ) as f:
                    token = f.read().strip()

                req = urllib.request.Request(
                    CLOUD + "/api/v1/devices",
                    headers={
                        "Authorization":
                        "Bearer " + token
                    },
                )

                with urllib.request.urlopen(
                    req,
                    timeout=5,
                ) as r:
                    devices = json.loads(
                        r.read().decode()
                    )

                text += (
                    "\nDevices: "
                    + str(devices.get("count", 0))
                )

            self.cloud_bridge.updated.emit(text)

        except Exception:
            self.cloud_bridge.updated.emit(
                "● CLOUD OFFLINE"
            )

    def set_cloud_text(self, text):
        self.cloud_label.setText(text)

    def closeEvent(self, event):
        self.settings.setValue(
            "geometry",
            self.saveGeometry()
        )

        self.settings.setValue(
            "dockState",
            self.saveState()
        )

        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("JARVIS V30")

    window = JarvisWindow()
    window.show()

    app.exec()
