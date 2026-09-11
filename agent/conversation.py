from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    """Small rolling conversational memory for pronouns/follow-ups.

    This deliberately keeps only recent turns in RAM. It is not a long-term
    profile database and it does not save private conversations to disk.
    """

    max_turns: int = 12
    _messages: list[dict[str, str]] = field(default_factory=list)

    def set_max_turns(self, max_turns: int) -> None:
        self.max_turns = max(2, int(max_turns))
        self._trim()

    def snapshot(self) -> list[dict[str, str]]:
        return [dict(item) for item in self._messages]

    def add_turn(self, user_text: str, assistant_text: str) -> None:
        self._messages.append({"role": "user", "content": user_text})
        self._messages.append({"role": "assistant", "content": assistant_text})
        self._trim()

    def clear(self) -> None:
        self._messages.clear()

    def _trim(self) -> None:
        keep_messages = self.max_turns * 2
        if len(self._messages) > keep_messages:
            self._messages = self._messages[-keep_messages:]
