from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AssistantState(str, Enum):
    IDLE = "Idle"
    LISTENING = "Listening"
    TRANSCRIBING = "Transcribing"
    THINKING = "Thinking"
    SPEAKING = "Speaking"
    ERROR = "Error"
    DISABLED = "Disabled"


@dataclass(slots=True)
class ToolAction:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    result: str | None = None


@dataclass(slots=True)
class AssistantReply:
    user_language: str
    intent: str
    gui_text: str
    spoken_text: str
    tool: ToolAction | None = None
    raw_user_text: str = ""


@dataclass(slots=True)
class LogEntry:
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

    def format(self) -> str:
        return f"{self.timestamp:%H:%M:%S}  {self.message}"
