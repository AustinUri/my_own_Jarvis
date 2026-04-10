from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QStyle,
)

from core.audio_utils import list_input_devices
from core.autostart import set_autostart
from core.config import AppConfig
from gui.orb_widget import OrbWidget
from gui.styles import STYLE_SHEET


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle('Jarvis Settings')
        self.setModal(True)
        self.resize(760, 860)
        self.config = config
        self.setStyleSheet(STYLE_SHEET)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        header = QFrame(objectName='SettingsHeader')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel('Settings')
        title.setProperty('class', 'settingsTitle')
        subtitle = QLabel('Make Jarvis feel like your assistant, not a pile of buttons.')
        subtitle.setProperty('class', 'settingsSubtitle')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        self.model_combo = QComboBox()
        self.model_combo.addItems(['gemma3:4b', 'llama3.1:8b', 'qwen2.5:7b'])
        self.model_combo.setCurrentText(config.model_name)

        self.language_combo = QComboBox()
        self.language_combo.addItems(['Auto', 'Hebrew', 'English'])
        self.language_combo.setCurrentText(config.language_mode)

        self.stt_combo = QComboBox()
        self.stt_combo.addItems(['tiny', 'base', 'small', 'medium'])
        self.stt_combo.setCurrentText(config.stt_model_name)

        self.stt_backend_combo = QComboBox()
        self.stt_backend_combo.addItems(['Auto', 'faster-whisper', 'whisper.cpp'])
        self.stt_backend_combo.setCurrentText(config.stt_backend if config.stt_backend in ['Auto', 'faster-whisper', 'whisper.cpp'] else 'Auto')

        self.mic_combo = QComboBox()
        device_names = [name for name, _ in list_input_devices()]
        if not device_names:
            device_names = ['Default']
        elif 'Default' not in device_names:
            device_names.insert(0, 'Default')
        self.mic_combo.addItems(device_names)
        self.mic_combo.setCurrentText(config.mic_name if config.mic_name in device_names else 'Default')

        self.voice_checkbox = QCheckBox('Enable voice replies')
        self.voice_checkbox.setChecked(config.voice_enabled)

        self.wake_checkbox = QCheckBox('Enable wake word listener')
        self.wake_checkbox.setChecked(config.wake_word_enabled)

        self.confirm_checkbox = QCheckBox('Require confirmation for dangerous actions')
        self.confirm_checkbox.setChecked(config.require_confirmation)

        self.accent_checkbox = QCheckBox('Accent assist and command bias')
        self.accent_checkbox.setChecked(config.accent_assist_enabled)

        self.piper_input = QLineEdit(config.piper_model_path)
        self.piper_input.setPlaceholderText('Optional: path to Piper model (.onnx)')
        self.whisper_cpp_input = QLineEdit(config.whisper_cpp_path)
        self.whisper_cpp_input.setPlaceholderText('Optional: path to whisper-cli.exe')

        self.searxng_url_input = QLineEdit(config.searxng_base_url)
        self.searxng_url_input.setPlaceholderText('Default: http://localhost:8888')
        self.web_results_spin = QSpinBox()
        self.web_results_spin.setRange(2, 8)
        self.web_results_spin.setValue(max(2, min(8, int(config.web_max_results))))

        self.wake_threshold_input = QLineEdit(f'{config.wake_word_threshold:.2f}')
        self.wake_vad_input = QLineEdit(f'{config.wake_vad_threshold:.2f}')
        self.wake_phrases_input = QLineEdit(config.wake_phrases)
        self.wake_phrases_input.setPlaceholderText('Hey Jarvis, Jarvis, Wake up Jarvis')

        self.tone_combo = QComboBox()
        self.tone_combo.addItems(['Respectful', 'Neutral', 'Casual'])
        self.tone_combo.setCurrentText(config.tone_mode)
        self.address_input = QLineEdit(config.address_name)
        self.address_input.setPlaceholderText('sir')
        self.verbosity_combo = QComboBox()
        self.verbosity_combo.addItems(['Brief', 'Balanced', 'Detailed'])
        self.verbosity_combo.setCurrentText(config.verbosity_mode)
        self.ask_related_checkbox = QCheckBox('Ask before opening related apps')
        self.ask_related_checkbox.setChecked(config.ask_before_open_related_apps)
        self.explicit_only_checkbox = QCheckBox('Auto-open only on explicit request')
        self.explicit_only_checkbox.setChecked(config.auto_open_explicit_only)

        self.tray_on_close_checkbox = QCheckBox('Keep running in tray when window closes')
        self.tray_on_close_checkbox.setChecked(config.minimize_to_tray_on_close)
        self.start_with_windows_checkbox = QCheckBox('Start with Windows')
        self.start_with_windows_checkbox.setChecked(config.start_with_windows)
        self.start_minimized_checkbox = QCheckBox('Start hidden in tray')
        self.start_minimized_checkbox.setChecked(config.start_minimized)
        self.background_checkbox = QCheckBox('Keep assistant runtime active in background')
        self.background_checkbox.setChecked(config.keep_assistant_running_in_tray)

        self.conversation_checkbox = QCheckBox('Enable conversation mode after wake')
        self.conversation_checkbox.setChecked(config.conversation_mode_enabled)
        self.conversation_timeout_spin = QSpinBox()
        self.conversation_timeout_spin.setRange(10, 90)
        self.conversation_timeout_spin.setValue(int(round(config.conversation_timeout_seconds)))
        self.conversation_turns_spin = QSpinBox()
        self.conversation_turns_spin.setRange(1, 8)
        self.conversation_turns_spin.setValue(int(config.conversation_followup_max_turns))
        self.interruption_checkbox = QCheckBox('Allow interruption while Jarvis is speaking')
        self.interruption_checkbox.setChecked(config.interruption_enabled)
        self.command_window_spin = QSpinBox()
        self.command_window_spin.setRange(4, 15)
        self.command_window_spin.setValue(int(round(config.command_max_seconds)))
        self.command_min_spin = QSpinBox()
        self.command_min_spin.setRange(1, 5)
        self.command_min_spin.setValue(int(round(config.command_min_seconds)))

        content_layout.addWidget(self._make_general_section())
        content_layout.addWidget(self._make_personality_section())
        content_layout.addWidget(self._make_background_section())
        content_layout.addWidget(self._make_conversation_section())
        content_layout.addWidget(self._make_audio_section())
        content_layout.addWidget(self._make_web_section())
        content_layout.addWidget(self._make_wake_section())
        content_layout.addWidget(self._make_safety_section())
        content_layout.addStretch(1)

        scroll.setWidget(scroll_content)
        outer.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = buttons.button(QDialogButtonBox.Save)
        if save_button is not None:
            save_button.setProperty('accent', 'true')
            save_button.style().unpolish(save_button)
            save_button.style().polish(save_button)
            save_button.setText('Save changes')
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        if cancel_button is not None:
            cancel_button.setText('Cancel')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _make_general_section(self) -> QGroupBox:
        section = QGroupBox('General')
        layout = QFormLayout(section)
        layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.setFormAlignment(Qt.AlignTop)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(12)
        layout.addRow(self._label('Model'), self.model_combo)
        layout.addRow(self._label('Language mode'), self.language_combo)
        layout.addRow(self._label('Speech-to-text backend'), self.stt_backend_combo)
        layout.addRow(self._label('Speech-to-text model'), self.stt_combo)
        return section

    def _make_personality_section(self) -> QGroupBox:
        section = QGroupBox('Personality')
        layout = QVBoxLayout(section)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow(self._label('Tone'), self.tone_combo)
        form.addRow(self._label('Address me as'), self.address_input)
        form.addRow(self._label('Verbosity'), self.verbosity_combo)
        layout.addLayout(form)
        layout.addWidget(self.ask_related_checkbox)
        layout.addWidget(self.explicit_only_checkbox)
        layout.addWidget(self._hint('Respectful mode is where Jarvis starts calling you sir consistently.'))
        layout.addWidget(self._hint('Suggestion mode keeps Jarvis from opening random apps just because you mentioned a topic.'))
        return section

    def _make_background_section(self) -> QGroupBox:
        section = QGroupBox('Background runtime')
        layout = QVBoxLayout(section)
        layout.setSpacing(12)
        layout.addWidget(self.background_checkbox)
        layout.addWidget(self.tray_on_close_checkbox)
        layout.addWidget(self.start_with_windows_checkbox)
        layout.addWidget(self.start_minimized_checkbox)
        layout.addWidget(self._hint('Closing the main window can hide Jarvis to the tray while the wake runtime stays alive.'))
        layout.addWidget(self._hint('Start with Windows writes a user-level startup entry. It is easy to disable later.'))
        return section

    def _make_conversation_section(self) -> QGroupBox:
        section = QGroupBox('Conversation mode')
        layout = QVBoxLayout(section)
        layout.setSpacing(12)
        layout.addWidget(self.conversation_checkbox)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow(self._label('Timeout after silence (seconds)'), self.conversation_timeout_spin)
        form.addRow(self._label('Max follow-up turns'), self.conversation_turns_spin)
        layout.addLayout(form)
        layout.addWidget(self.interruption_checkbox)
        layout.addWidget(self._hint('After you wake Jarvis once, he can keep listening for follow-up questions without the wake phrase again.'))
        layout.addWidget(self._hint('Say stop listening or goodbye to end the session early.'))
        layout.addWidget(self._hint('Interruption lets push-to-talk cut Jarvis off mid-reply so you can keep the conversation flowing.'))
        return section

    def _make_audio_section(self) -> QGroupBox:
        section = QGroupBox('Audio')
        layout = QVBoxLayout(section)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow(self._label('Microphone'), self.mic_combo)
        form.addRow(self._label('Command capture window (seconds)'), self.command_window_spin)
        form.addRow(self._label('Minimum command length (seconds)'), self.command_min_spin)
        form.addRow(self._label('Piper model path'), self.piper_input)
        form.addRow(self._label('whisper.cpp executable'), self.whisper_cpp_input)
        layout.addLayout(form)
        layout.addWidget(self.voice_checkbox)
        layout.addWidget(self._hint('A longer capture window makes Jarvis less likely to chop off the start or end of what you said.'))
        layout.addWidget(self._hint('Use Piper only if you actually have a local voice model. Otherwise Jarvis falls back to Windows speech.'))
        return section

    def _make_web_section(self) -> QGroupBox:
        section = QGroupBox('Web')
        layout = QVBoxLayout(section)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow(self._label('SearXNG instance URL'), self.searxng_url_input)
        form.addRow(self._label('Max sources'), self.web_results_spin)
        layout.addLayout(form)
        layout.addWidget(self._hint('Jarvis can use SearXNG for real web answers without a paid API. Wikipedia is still the fallback.'))
        return section

    def _make_wake_section(self) -> QGroupBox:
        section = QGroupBox('Wake word')
        layout = QVBoxLayout(section)
        layout.addWidget(self.wake_checkbox)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow(self._label('Wake phrases'), self.wake_phrases_input)
        form.addRow(self._label('Wake sensitivity threshold'), self.wake_threshold_input)
        form.addRow(self._label('Wake VAD threshold'), self.wake_vad_input)
        layout.addLayout(form)
        layout.addWidget(self._hint('The current listener is still strongest on “Hey Jarvis”. Extra phrases are saved for future tuning and prefix cleanup.'))
        return section

    def _make_safety_section(self) -> QGroupBox:
        section = QGroupBox('Behavior and safety')
        layout = QVBoxLayout(section)
        layout.setSpacing(12)
        layout.addWidget(self.confirm_checkbox)
        layout.addWidget(self.accent_checkbox)
        layout.addWidget(self._hint('Accent assist biases speech recognition toward desktop commands and repairs common misheard app names.'))
        return section

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty('class', 'fieldLabel')
        return label

    def _hint(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setProperty('class', 'hint')
        return label

    def apply(self) -> None:
        self.config.model_name = self.model_combo.currentText()
        self.config.language_mode = self.language_combo.currentText()
        self.config.mic_name = self.mic_combo.currentText()
        self.config.stt_backend = self.stt_backend_combo.currentText()
        self.config.stt_model_name = self.stt_combo.currentText()
        self.config.voice_enabled = self.voice_checkbox.isChecked()
        self.config.wake_word_enabled = self.wake_checkbox.isChecked()
        self.config.require_confirmation = self.confirm_checkbox.isChecked()
        self.config.accent_assist_enabled = self.accent_checkbox.isChecked()
        self.config.piper_model_path = self.piper_input.text().strip()
        self.config.whisper_cpp_path = self.whisper_cpp_input.text().strip()
        self.config.searxng_base_url = self.searxng_url_input.text().strip()
        self.config.web_max_results = int(self.web_results_spin.value())
        self.config.tone_mode = self.tone_combo.currentText()
        self.config.address_name = self.address_input.text().strip() or 'sir'
        self.config.verbosity_mode = self.verbosity_combo.currentText()
        self.config.ask_before_open_related_apps = self.ask_related_checkbox.isChecked()
        self.config.auto_open_explicit_only = self.explicit_only_checkbox.isChecked()
        self.config.minimize_to_tray_on_close = self.tray_on_close_checkbox.isChecked()
        self.config.start_with_windows = self.start_with_windows_checkbox.isChecked()
        self.config.start_minimized = self.start_minimized_checkbox.isChecked()
        self.config.keep_assistant_running_in_tray = self.background_checkbox.isChecked()
        self.config.conversation_mode_enabled = self.conversation_checkbox.isChecked()
        self.config.conversation_timeout_seconds = float(self.conversation_timeout_spin.value())
        self.config.conversation_followup_max_turns = int(self.conversation_turns_spin.value())
        self.config.interruption_enabled = self.interruption_checkbox.isChecked()
        self.config.command_max_seconds = float(self.command_window_spin.value())
        self.config.command_min_seconds = float(self.command_min_spin.value())
        self.config.wake_phrases = self.wake_phrases_input.text().strip() or 'Hey Jarvis'
        try:
            self.config.wake_word_threshold = max(0.10, min(0.90, float(self.wake_threshold_input.text().strip())))
        except ValueError:
            pass
        try:
            self.config.wake_vad_threshold = max(0.0, min(1.0, float(self.wake_vad_input.text().strip())))
        except ValueError:
            pass


class MainWindow(QMainWindow):
    def __init__(self, orchestrator, config: AppConfig, app_dir: Path):
        super().__init__()
        self.orchestrator = orchestrator
        self.config = config
        self.app_dir = app_dir
        self._tray_hint_shown = False
        self.tray_icon: QSystemTrayIcon | None = None

        self.setWindowTitle('JARVIS')
        self.resize(1180, 760)
        self.setStyleSheet(STYLE_SHEET)

        self._build_ui()
        self._connect_events()
        self._update_header_state('Idle')
        self._setup_tray_icon()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(12)
        self.setCentralWidget(root)

        title = QFrame(objectName='TitleBar')
        title_layout = QHBoxLayout(title)
        title_layout.setContentsMargins(16, 12, 16, 12)
        title_layout.setSpacing(16)

        self.app_label = QLabel('JARVIS')
        self.app_label.setProperty('class', 'status')
        self.header_state = QLabel('Idle')
        self.header_state.setProperty('class', 'status')
        self.header_meta = QLabel(self._header_meta_text())
        self.header_meta.setProperty('class', 'meta')

        title_layout.addWidget(self.app_label)
        title_layout.addStretch(1)
        title_layout.addWidget(self.header_state)
        title_layout.addSpacing(10)
        title_layout.addWidget(self.header_meta)
        root_layout.addWidget(title)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)
        root_layout.addLayout(body_layout, 1)

        sidebar = QFrame(objectName='Sidebar')
        sidebar.setFixedWidth(225)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 16, 14, 16)
        sidebar_layout.setSpacing(12)

        self.status_dot = QLabel('●')
        self.status_dot.setAlignment(Qt.AlignCenter)
        self.status_dot.setStyleSheet('font-size: 24px; color: #ffa34d;')
        self.status_text = QLabel('Idle')
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setProperty('class', 'status')
        self.personality_text = QLabel(self._personality_text())
        self.personality_text.setAlignment(Qt.AlignCenter)
        self.personality_text.setProperty('class', 'meta')
        self.personality_text.setWordWrap(True)

        self.toggle_button = QPushButton('Stop Assistant' if self.config.assistant_enabled else 'Start Assistant')
        self.voice_button = QPushButton('Mute Voice' if self.config.voice_enabled else 'Unmute Voice')
        self.voice_test_button = QPushButton('Test Voice')
        self.mic_test_button = QPushButton('Test Mic')
        self.wake_button = QPushButton('Disable Wake Word' if self.config.wake_word_enabled else 'Enable Wake Word')
        self.ptt_button = QPushButton('Push-to-talk')
        self.hide_button = QPushButton('Hide to Tray')
        self.history_button = QPushButton('Clear History')
        self.settings_button = QPushButton('Settings')

        sidebar_layout.addWidget(self.status_dot)
        sidebar_layout.addWidget(self.status_text)
        sidebar_layout.addWidget(self.personality_text)
        sidebar_layout.addSpacing(8)
        for button in [self.toggle_button, self.voice_button, self.voice_test_button, self.mic_test_button, self.wake_button, self.ptt_button, self.hide_button, self.history_button, self.settings_button]:
            sidebar_layout.addWidget(button)
        sidebar_layout.addStretch(1)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setSpacing(12)

        orb_card = QFrame(objectName='OrbCard')
        orb_layout = QVBoxLayout(orb_card)
        orb_layout.setContentsMargins(20, 18, 20, 18)
        orb_layout.setSpacing(8)
        self.orb = OrbWidget()
        self.orb.setFixedHeight(280)
        self.orb_status = QLabel('Idle')
        self.orb_status.setAlignment(Qt.AlignCenter)
        self.orb_status.setProperty('class', 'status')
        self.orb_status.setStyleSheet('font-size: 18px; font-weight: 700;')
        self.orb_subtitle = QLabel(self._orb_subtitle_text())
        self.orb_subtitle.setAlignment(Qt.AlignCenter)
        self.orb_subtitle.setProperty('class', 'meta')
        self.orb_subtitle.setWordWrap(True)
        orb_layout.addWidget(self.orb, alignment=Qt.AlignCenter)
        orb_layout.addWidget(self.orb_status)
        orb_layout.addWidget(self.orb_subtitle)
        center_layout.addWidget(orb_card)

        self.transcript_box = self._make_card(center_layout, 'Heard / Transcript')
        self.response_box = self._make_card(center_layout, 'Jarvis Response')
        self.spoken_box = self._make_card(center_layout, 'Spoken Reply')

        log_panel = QFrame(objectName='LogPanel')
        log_panel.setFixedWidth(330)
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(14, 16, 14, 16)
        log_layout.setSpacing(10)
        heading = QLabel('Action Log')
        heading.setProperty('class', 'heading')
        self.log_list = QListWidget()
        log_layout.addWidget(heading)
        log_layout.addWidget(self.log_list, 1)

        body_layout.addWidget(sidebar)
        body_layout.addWidget(center, 1)
        body_layout.addWidget(log_panel)

        bottom = QFrame(objectName='Card')
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(12, 12, 12, 12)
        bottom_layout.setSpacing(10)
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText('Type a command here...')
        self.send_button = QPushButton('Send')
        bottom_layout.addWidget(self.command_input, 1)
        bottom_layout.addWidget(self.send_button)
        root_layout.addWidget(bottom)

        send_action = QAction(self)
        send_action.setShortcut(Qt.Key_Return)
        send_action.triggered.connect(self._submit_command)
        self.addAction(send_action)

    def _setup_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        try:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        except Exception:
            try:
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
            except Exception:
                icon = QIcon()
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip('Jarvis')
        menu = QMenu(self)
        open_action = menu.addAction('Open Jarvis')
        open_action.triggered.connect(self.show_from_tray)
        toggle_action = menu.addAction('Start/Stop Assistant')
        toggle_action.triggered.connect(self._toggle_assistant)
        wake_action = menu.addAction('Toggle Wake Word')
        wake_action.triggered.connect(self._toggle_wake_word)
        mute_action = menu.addAction('Mute/Unmute Voice')
        mute_action.triggered.connect(self._toggle_voice)
        menu.addSeparator()
        quit_action = menu.addAction('Quit')
        quit_action.triggered.connect(self._quit_application)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._handle_tray_activated)
        self.tray_icon.show()

    def _handle_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_from_tray()

    def _header_meta_text(self) -> str:
        wake = 'On' if self.config.wake_word_enabled else 'Off'
        web_mode = 'SearXNG' if self.config.searxng_base_url else ('Tavily' if self.config.tavily_api_key else 'Wikipedia fallback')
        bg = 'Tray' if self.config.keep_assistant_running_in_tray else 'Window only'
        convo = f'Convo: {"On" if self.config.conversation_mode_enabled else "Off"} ({int(self.config.conversation_timeout_seconds)}s)'
        return (
            f'Model: {self.config.model_name}   |   Mic: {self.config.mic_name}   |   '
            f'Lang: {self.config.language_mode}   |   Tone: {self.config.tone_mode}   |   '
            f'Web: {web_mode}   |   Wake: {wake} ({self.config.wake_word_threshold:.2f})   |   Runtime: {bg}   |   {convo}'
        )

    def _personality_text(self) -> str:
        return f'{self.config.tone_mode} • address: {self.config.address_name or "sir"}'

    def _orb_subtitle_text(self) -> str:
        phrases = self.config.wake_phrases or 'Hey Jarvis'
        convo = 'Conversation mode on' if self.config.conversation_mode_enabled else 'Conversation mode off'
        return f'Preferred wake phrases: {phrases}\n{convo}'

    def _make_card(self, parent_layout: QVBoxLayout, title: str) -> QTextEdit:
        card = QFrame(objectName='Card')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setProperty('class', 'heading')
        box = QTextEdit()
        box.setReadOnly(True)
        box.setMinimumHeight(95)
        box.setPlaceholderText('Waiting for input...')
        layout.addWidget(heading)
        layout.addWidget(box)
        parent_layout.addWidget(card)
        return box

    def _connect_events(self) -> None:
        self.send_button.clicked.connect(self._submit_command)
        self.command_input.returnPressed.connect(self._submit_command)
        self.toggle_button.clicked.connect(self._toggle_assistant)
        self.voice_button.clicked.connect(self._toggle_voice)
        self.voice_test_button.clicked.connect(self._test_voice)
        self.mic_test_button.clicked.connect(self._test_mic)
        self.wake_button.clicked.connect(self._toggle_wake_word)
        self.hide_button.clicked.connect(self.hide_to_tray)
        self.history_button.clicked.connect(self._clear_history)
        self.settings_button.clicked.connect(self._open_settings)
        self.ptt_button.clicked.connect(self._push_to_talk)

        self.orchestrator.state_changed.connect(self._update_header_state)
        self.orchestrator.transcript_ready.connect(self._update_transcript)
        self.orchestrator.response_ready.connect(self._update_response)
        self.orchestrator.spoken_text_ready.connect(self._update_spoken)
        self.orchestrator.log_ready.connect(self._log)
        self.orchestrator.error_raised.connect(self._show_error)

    def _submit_command(self) -> None:
        text = self.command_input.text().strip()
        if not text:
            return
        self.command_input.clear()
        self.orchestrator.process_user_text(text)

    def _toggle_assistant(self) -> None:
        enabled = not self.orchestrator.enabled
        self.orchestrator.set_enabled(enabled)
        self.toggle_button.setText('Stop Assistant' if enabled else 'Start Assistant')

    def _toggle_voice(self) -> None:
        self.orchestrator.toggle_voice()
        self.voice_button.setText('Mute Voice' if self.config.voice_enabled else 'Unmute Voice')

    def _test_voice(self) -> None:
        text = f'{self.config.address_name.capitalize()}, voice test. Audio output is working.' if self.config.tone_mode == 'Respectful' else 'Jarvis voice test. Audio output is working.'
        self.orchestrator.test_voice(text)

    def _test_mic(self) -> None:
        self.orchestrator.test_microphone()

    def _toggle_wake_word(self) -> None:
        self.orchestrator.toggle_wake_word()
        self.wake_button.setText('Disable Wake Word' if self.config.wake_word_enabled else 'Enable Wake Word')
        self.header_meta.setText(self._header_meta_text())

    def _push_to_talk(self) -> None:
        self.orchestrator.process_push_to_talk()

    def _clear_history(self) -> None:
        self.log_list.clear()
        self.transcript_box.clear()
        self.response_box.clear()
        self.spoken_box.clear()
        self._log('History cleared.')

    def _open_settings(self) -> None:
        previous_autostart = self.config.start_with_windows
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.Accepted:
            dialog.apply()
            self.orchestrator.reload_runtime_config()
            self.header_meta.setText(self._header_meta_text())
            self.personality_text.setText(self._personality_text())
            self.orb_subtitle.setText(self._orb_subtitle_text())
            self.voice_button.setText('Mute Voice' if self.config.voice_enabled else 'Unmute Voice')
            self.wake_button.setText('Disable Wake Word' if self.config.wake_word_enabled else 'Enable Wake Word')
            if previous_autostart != self.config.start_with_windows:
                success, message = set_autostart(self.config.start_with_windows, self.app_dir)
                self._log(message)
                if not success:
                    self._show_error(message)
            self._log('Settings updated.')

    def _update_header_state(self, state: str) -> None:
        color_map = {
            'Idle': '#ffa34d',
            'Listening': '#ffbf6c',
            'Transcribing': '#ffd08e',
            'Thinking': '#ffc257',
            'Speaking': '#ffe39e',
            'Error': '#ff6b57',
            'Disabled': '#7d8590',
        }
        color = color_map.get(state, '#ffa34d')
        self.header_state.setText(state)
        self.status_text.setText(state)
        self.orb_status.setText(state)
        self.status_dot.setStyleSheet(f'font-size: 24px; color: {color};')
        self.orb.set_state(state)
        self.ptt_button.setText('Interrupt & Talk' if state == 'Speaking' and self.config.interruption_enabled else 'Push-to-talk')
        if self.tray_icon is not None:
            self.tray_icon.setToolTip(f'Jarvis — {state}')

    def _update_transcript(self, text: str, language: str) -> None:
        self._set_bidi_text(self.transcript_box, text, language)

    def _update_response(self, text: str, language: str) -> None:
        self._set_bidi_text(self.response_box, text, language)

    def _update_spoken(self, text: str) -> None:
        self.spoken_box.setLayoutDirection(Qt.LeftToRight)
        self.spoken_box.setAlignment(Qt.AlignLeft)
        self.spoken_box.setPlainText(text)

    def _set_bidi_text(self, widget: QTextEdit, text: str, language: str) -> None:
        widget.setLayoutDirection(Qt.RightToLeft if language == 'he' else Qt.LeftToRight)
        widget.setAlignment(Qt.AlignRight if language == 'he' else Qt.AlignLeft)
        widget.setPlainText(text)

    def _log(self, message: str) -> None:
        self.log_list.insertItem(0, message)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, 'Jarvis Error', message)

    def hide_to_tray(self) -> None:
        if self.tray_icon is None:
            self.showMinimized()
            return
        self.hide()
        if not self._tray_hint_shown:
            self.tray_icon.showMessage('Jarvis', 'Jarvis is still running in the tray, sir.', QSystemTrayIcon.Information, 2500)
            self._tray_hint_shown = True
        self._log('Window hidden to tray. Runtime still active.')

    def show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.config.minimize_to_tray_on_close and self.config.keep_assistant_running_in_tray and self.tray_icon is not None:
            event.ignore()
            self.hide_to_tray()
            return
        super().closeEvent(event)

    def _quit_application(self) -> None:
        if self.tray_icon is not None:
            self.tray_icon.hide()
        QApplication.instance().quit()
