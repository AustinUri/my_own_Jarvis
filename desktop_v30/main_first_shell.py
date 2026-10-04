import json
import math
import os
import threading
import urllib.request

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


CLOUD = "https://uri-jarvis.duckdns.org"


class StatusBridge(QObject):
    updated = Signal(str)


class CoreWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.angle = 0.0
        self.setMinimumSize(440, 440)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(40)

    def animate(self):
        self.angle += 1.4
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        cx = w / 2
        cy = h / 2

        gradient = QRadialGradient(cx, cy, 145)
        gradient.setColorAt(0.0, QColor(80, 235, 255, 175))
        gradient.setColorAt(0.25, QColor(20, 120, 170, 110))
        gradient.setColorAt(0.70, QColor(5, 30, 45, 30))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(cx - 145),
            int(cy - 145),
            290,
            290
        )

        for radius, alpha in [
            (70, 180),
            (105, 120),
            (145, 70),
        ]:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(
                QPen(
                    QColor(90, 225, 255, alpha),
                    1.4
                )
            )

            painter.drawEllipse(
                int(cx - radius),
                int(cy - radius),
                radius * 2,
                radius * 2
            )

        for i in range(30):
            a = math.radians(
                self.angle * (1 if i % 2 == 0 else -0.7)
                + i * 12
            )

            radius = 85 + ((i * 17) % 75)

            x = cx + math.cos(a) * radius
            y = cy + math.sin(a) * radius

            size = 3 + (i % 4)

            painter.setBrush(
                QColor(
                    120,
                    235,
                    255,
                    190
                )
            )

            painter.setPen(Qt.NoPen)

            painter.drawEllipse(
                int(x - size / 2),
                int(y - size / 2),
                size,
                size
            )

        painter.setPen(QColor(210, 250, 255))
        painter.drawText(
            self.rect(),
            Qt.AlignCenter,
            "JARVIS\nV30"
        )


class JarvisWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("JARVIS V30")
        self.resize(1280, 780)

        self.bridge = StatusBridge()
        self.bridge.updated.connect(self.set_cloud_status)

        root = QWidget()
        root.setStyleSheet("""
            QWidget {
                background: #07131d;
                color: #dffaff;
                font-family: Segoe UI;
            }

            QPushButton {
                background: #0c2332;
                border: 1px solid #1b5168;
                border-radius: 8px;
                padding: 12px;
                text-align: left;
                font-size: 14px;
            }

            QPushButton:hover {
                background: #12364a;
                border: 1px solid #53dff5;
            }
        """)

        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(225)
        sidebar.setStyleSheet(
            "background:#081a25;"
            "border-right:1px solid #174054;"
        )

        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(16, 22, 16, 22)

        title = QLabel("J.A.R.V.I.S.")
        title.setStyleSheet(
            "font-size:24px;"
            "font-weight:700;"
            "color:#8fefff;"
        )

        nav.addWidget(title)

        version = QLabel("V30 · CLOUD NATIVE")
        version.setStyleSheet(
            "color:#6fa6b9;"
            "margin-bottom:18px;"
        )

        nav.addWidget(version)

        names = [
            "COMMAND CENTER",
            "PHONE CENTER",
            "BUSINESS / eBAY",
            "AGENT CENTER",
            "HOLOLAB",
            "CODING JARVIS",
            "MEMORY",
            "MUSIC",
            "SETTINGS",
        ]

        for name in names:
            button = QPushButton(name)
            button.clicked.connect(
                lambda checked=False, n=name:
                self.select_section(n)
            )
            nav.addWidget(button)

        nav.addStretch()

        self.connection = QLabel("Checking cloud…")
        self.connection.setWordWrap(True)
        self.connection.setStyleSheet(
            "color:#76dba8;"
            "font-size:12px;"
        )

        nav.addWidget(self.connection)

        outer.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(35, 28, 35, 28)

        self.section_title = QLabel("COMMAND CENTER")
        self.section_title.setStyleSheet(
            "font-size:24px;"
            "font-weight:600;"
        )

        main.addWidget(self.section_title)

        subtitle = QLabel(
            "Native Windows Command Interface · Oracle Cloud Core"
        )

        subtitle.setStyleSheet(
            "color:#7696a5;"
        )

        main.addWidget(subtitle)

        core = CoreWidget()
        core.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        main.addWidget(core, 1)

        footer = QLabel(
            "Windows Worker · Samsung Companion · "
            "Cloud Memory · Agents · Business Center"
        )

        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(
            "color:#698896;"
            "padding:10px;"
        )

        main.addWidget(footer)

        outer.addWidget(content, 1)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(
            self.refresh_cloud
        )
        self.status_timer.start(10000)

        self.refresh_cloud()

    def select_section(self, name):
        self.section_title.setText(name)

    def set_cloud_status(self, text):
        self.connection.setText(text)

    def refresh_cloud(self):
        threading.Thread(
            target=self.check_cloud,
            daemon=True
        ).start()

    def check_cloud(self):
        try:
            with urllib.request.urlopen(
                CLOUD + "/api/v1/health",
                timeout=4
            ) as response:
                health = json.loads(
                    response.read().decode()
                )

            text = (
                "● CLOUD ONLINE\n"
                + health.get("version", "V30")
            )

            token_path = os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Jarvis",
                "cloud.token",
            )

            if os.path.exists(token_path):
                token = open(
                    token_path,
                    encoding="utf-8"
                ).read().strip()

                req = urllib.request.Request(
                    CLOUD + "/api/v1/devices",
                    headers={
                        "Authorization":
                            "Bearer " + token
                    },
                )

                with urllib.request.urlopen(
                    req,
                    timeout=4
                ) as response:
                    devices = json.loads(
                        response.read().decode()
                    )

                text += (
                    "\nDevices online: "
                    + str(devices.get("count", 0))
                )

            self.bridge.updated.emit(text)

        except Exception:
            self.bridge.updated.emit(
                "● CLOUD OFFLINE"
            )


if __name__ == "__main__":
    app = QApplication([])
    window = JarvisWindow()
    window.show()
    app.exec()
