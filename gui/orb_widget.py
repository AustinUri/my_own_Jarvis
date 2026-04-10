from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QConicalGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget


STATE_COLORS = {
    "Idle": QColor(255, 163, 77),
    "Listening": QColor(255, 188, 92),
    "Transcribing": QColor(255, 196, 112),
    "Thinking": QColor(255, 174, 70),
    "Speaking": QColor(255, 214, 122),
    "Error": QColor(255, 95, 78),
    "Disabled": QColor(110, 118, 130),
}


class OrbWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.state = "Idle"
        self.phase = 0.0
        self.rotation = 0.0
        self.audio_level = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def set_state(self, state: str) -> None:
        self.state = state
        self.update()

    def set_audio_level(self, level: float) -> None:
        self.audio_level = max(0.0, min(1.0, level))
        self.update()

    def _tick(self) -> None:
        self.phase += 0.05
        speed = 1.9 if self.state in {"Thinking", "Transcribing"} else 0.55
        self.rotation += speed
        if self.state == "Listening":
            self.audio_level = 0.18 + (math.sin(self.phase * 3.6) + 1.0) / 3.5
        elif self.state == "Speaking":
            self.audio_level = 0.25 + (math.sin(self.phase * 5.4) + 1.0) / 3.1
        elif self.state in {"Idle", "Disabled"}:
            self.audio_level = 0.08
        elif self.state == "Error":
            self.audio_level = 0.22 + 0.06 * math.sin(self.phase * 9.0)
        else:
            self.audio_level = 0.15 + 0.08 * math.sin(self.phase * 2.2)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        size = min(self.width(), self.height())
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = size * 0.19
        base = STATE_COLORS.get(self.state, STATE_COLORS["Idle"])

        pulse = 1.0 + 0.05 * math.sin(self.phase * 2.0) + self.audio_level * 0.14
        halo_radius = radius * 2.85 * pulse

        halo = QRadialGradient(center_x, center_y, halo_radius)
        halo.setColorAt(0.0, QColor(base.red(), base.green(), base.blue(), 112))
        halo.setColorAt(0.28, QColor(base.red(), base.green(), base.blue(), 52))
        halo.setColorAt(0.68, QColor(base.red(), base.green(), base.blue(), 18))
        halo.setColorAt(1.0, QColor(base.red(), base.green(), base.blue(), 0))
        painter.setBrush(halo)
        painter.drawEllipse(int(center_x - halo_radius), int(center_y - halo_radius), int(halo_radius * 2), int(halo_radius * 2))

        ring_radius = radius * 1.7
        soft_pen = QPen(QColor(base.red(), base.green(), base.blue(), 44), 2)
        painter.setPen(soft_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(center_x - ring_radius), int(center_y - ring_radius), int(ring_radius * 2), int(ring_radius * 2))

        bright_pen = QPen(QColor(base.red(), base.green(), base.blue(), 210), 7)
        bright_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bright_pen)
        painter.drawArc(
            int(center_x - ring_radius),
            int(center_y - ring_radius),
            int(ring_radius * 2),
            int(ring_radius * 2),
            int((-self.rotation + 20) * 16),
            112 * 16,
        )
        painter.drawArc(
            int(center_x - ring_radius * 0.84),
            int(center_y - ring_radius * 0.84),
            int(ring_radius * 1.68),
            int(ring_radius * 1.68),
            int((self.rotation * 1.4 + 160) * 16),
            72 * 16,
        )

        inner_gradient = QRadialGradient(center_x, center_y, radius * 1.25)
        inner_gradient.setColorAt(0.0, QColor(255, 252, 244, 250))
        inner_gradient.setColorAt(0.18, QColor(255, 214, 145, 244))
        inner_gradient.setColorAt(0.48, QColor(base.red(), base.green(), base.blue(), 216))
        inner_gradient.setColorAt(0.78, QColor(140, 78, 28, 84))
        inner_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(inner_gradient)
        core_radius = radius * pulse
        painter.drawEllipse(int(center_x - core_radius), int(center_y - core_radius), int(core_radius * 2), int(core_radius * 2))

        shimmer = QConicalGradient(center_x, center_y, self.rotation)
        shimmer.setColorAt(0.0, QColor(255, 255, 255, 164))
        shimmer.setColorAt(0.18, QColor(base.red(), base.green(), base.blue(), 0))
        shimmer.setColorAt(0.56, QColor(base.red(), base.green(), base.blue(), 120))
        shimmer.setColorAt(0.84, QColor(base.red(), base.green(), base.blue(), 0))
        shimmer.setColorAt(1.0, QColor(255, 255, 255, 164))
        painter.setBrush(shimmer)
        painter.drawEllipse(
            int(center_x - radius * 0.78),
            int(center_y - radius * 0.78),
            int(radius * 1.56),
            int(radius * 1.56),
        )

        if self.state in {"Listening", "Speaking"}:
            wave_pen = QPen(QColor(base.red(), base.green(), base.blue(), 140), 3)
            painter.setPen(wave_pen)
            spread = radius * (1.95 + self.audio_level * 0.55)
            painter.drawEllipse(int(center_x - spread), int(center_y - spread), int(spread * 2), int(spread * 2))
