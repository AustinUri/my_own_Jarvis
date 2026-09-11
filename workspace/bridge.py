from __future__ import annotations

from dataclasses import asdict
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from core.autostart import set_autostart


class WorkspaceBridge(QObject):
    submit_text = Signal(str)
    push_to_talk = Signal()
    test_microphone = Signal()
    test_voice = Signal()
    set_assistant_enabled = Signal(bool)
    toggle_voice = Signal()
    toggle_wake_word = Signal()
    clear_memory = Signal()
    reload_config = Signal()

    def __init__(self, orchestrator, config, config_path, publish):
        super().__init__()
        self.orchestrator = orchestrator
        self.config = config
        self.config_path = config_path
        self.app_dir = config_path.parent
        self.publish = publish

        self.submit_text.connect(orchestrator.process_user_text)
        self.push_to_talk.connect(orchestrator.process_push_to_talk)
        self.test_microphone.connect(orchestrator.test_microphone)
        self.test_voice.connect(orchestrator.test_voice)
        self.set_assistant_enabled.connect(orchestrator.set_enabled)
        self.toggle_voice.connect(orchestrator.toggle_voice)
        self.toggle_wake_word.connect(orchestrator.toggle_wake_word)
        self.clear_memory.connect(orchestrator.clear_conversation_memory)
        self.reload_config.connect(orchestrator.reload_runtime_config)

    @Slot(dict)
    def apply_config_patch(self, patch: dict[str, Any]) -> None:
        changed = False
        for key, value in patch.items():
            if key in self.config.__dataclass_fields__:
                setattr(self.config, key, value)
                changed = True
        if changed:
            self.config.save(self.config_path)
            if "start_with_windows" in patch:
                ok, message = set_autostart(bool(self.config.start_with_windows), self.app_dir)
                self.publish("log", message)
            self.orchestrator.reload_runtime_config()
            self.publish("config", asdict(self.config))
