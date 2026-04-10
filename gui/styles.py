from __future__ import annotations

STYLE_SHEET = """
QMainWindow, QDialog {
    background-color: #0b0f14;
}

QWidget {
    color: #e8eef7;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 14px;
}

QLabel {
    background: transparent;
    border: none;
}

#TitleBar {
    background-color: #111823;
    border: 1px solid #1d2a3a;
    border-radius: 14px;
}

#Sidebar, #LogPanel, #Card, #SettingsSection {
    background-color: #111823;
    border: 1px solid #1d2a3a;
    border-radius: 16px;
}

#OrbCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111823, stop:1 #0f1723);
    border: 1px solid #29405c;
    border-radius: 20px;
}

#SettingsHeader {
    background-color: transparent;
    border: none;
}

QGroupBox {
    background-color: #111823;
    border: 1px solid #1d2a3a;
    border-radius: 16px;
    margin-top: 12px;
    padding: 14px 14px 12px 14px;
    font-weight: 700;
    color: #ffbe6a;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QPushButton {
    background-color: #182231;
    border: 1px solid #27415b;
    border-radius: 10px;
    padding: 10px 14px;
    color: #e8eef7;
}

QPushButton:hover {
    background-color: #1e2d41;
}

QPushButton:pressed {
    background-color: #213650;
}

QPushButton[accent="true"] {
    background-color: #24476d;
    border: 1px solid #4d7eb0;
    color: #f6fbff;
    font-weight: 700;
}

QPushButton[accent="true"]:hover {
    background-color: #2c5682;
}

QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QComboBox, QScrollArea {
    background-color: #0e1520;
    border: 1px solid #24384f;
    border-radius: 12px;
    padding: 8px;
}

QScrollArea {
    background: transparent;
    border: none;
    padding: 0;
}

QCheckBox {
    background: transparent;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QCheckBox::indicator:unchecked {
    border: 1px solid #51657d;
    border-radius: 4px;
    background: #0e1520;
}

QCheckBox::indicator:checked {
    border: 1px solid #4d7eb0;
    border-radius: 4px;
    background: #24476d;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background-color: #0e1520;
    border: 1px solid #24384f;
    selection-background-color: #1e3550;
}

QTextEdit, QListWidget {
    selection-background-color: #2a4770;
}

QDialogButtonBox {
    background: transparent;
}

QDialogButtonBox QPushButton {
    min-width: 120px;
}

QLabel[class="heading"] {
    font-size: 13px;
    color: #8fb9d6;
    font-weight: 600;
    letter-spacing: 0.4px;
}

QLabel[class="status"] {
    font-size: 15px;
    font-weight: 700;
    color: #ffbe6a;
}

QLabel[class="meta"] {
    color: #9eb0c1;
}

QLabel[class="settingsTitle"] {
    font-size: 22px;
    font-weight: 800;
    color: #ffbe6a;
}

QLabel[class="settingsSubtitle"] {
    color: #9eb0c1;
    font-size: 13px;
}

QLabel[class="fieldLabel"] {
    color: #b9cad9;
    font-size: 13px;
    font-weight: 600;
    padding-bottom: 2px;
}

QLabel[class="hint"] {
    color: #7f95a8;
    font-size: 12px;
}

QListWidget::item {
    padding: 6px 4px;
    border-bottom: 1px solid #1a2635;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px;
}

QScrollBar::handle:vertical {
    background: #28415b;
    border-radius: 5px;
}
"""
