from __future__ import annotations

import re
from dataclasses import dataclass


EXPLICIT_ACTION_RE = re.compile(
    r"\b(open|launch|run|start|close|quit|kill|show|hide|switch|bring\s+up|navigate|go\s+to|lock|shutdown|turn\s+off|create|write|save|search\s+for|find)\b"
    r"|(?:פתח|תפתח|תפעיל|תריץ|סגור|תסגור|תציג|תראה|תביא|נעל|כבה|כתוב|תרשום|שמור|חפש|מצא)",
    re.IGNORECASE,
)

PERSONAL_PRIVATE_RE = re.compile(
    r"\b(my\s+(schedule|calendar|inbox|email|messages|reminders)|what\s+do\s+i\s+have\s+(today|tonight|tomorrow)|what'?s\s+on\s+my\s+(schedule|calendar))\b"
    r"|(?:היומן\s+שלי|לוח\s+הזמנים\s+שלי|מה\s+יש\s+לי\s+(היום|מחר|הלילה)|המייל\s+שלי|ההודעות\s+שלי|התזכורות\s+שלי)",
    re.IGNORECASE,
)

UI_MUTATING_TOOLS = {
    "open_app",
    "close_app",
    "open_website",
    "search_web",
    "open_folder",
    "lock_computer",
    "shutdown_request",
    "ui_show_panel",
    "ui_hide_panel",
    "ui_switch_workspace",
}

PRIVATE_WEB_BLOCK_TOOLS = {"answer_web_question", "search_web"}


@dataclass(slots=True)
class RequestPolicy:
    explicit_action: bool
    personal_private: bool

    @classmethod
    def from_text(cls, text: str) -> "RequestPolicy":
        return cls(
            explicit_action=bool(EXPLICIT_ACTION_RE.search(text)),
            personal_private=bool(PERSONAL_PRIVATE_RE.search(text)),
        )

    def authorize(self, tool_name: str, auto_open_explicit_only: bool = True) -> tuple[bool, str]:
        if self.personal_private and tool_name in PRIVATE_WEB_BLOCK_TOOLS:
            return False, "This request concerns the user's private/personal data, so public web search is not an appropriate substitute."
        if auto_open_explicit_only and tool_name in UI_MUTATING_TOOLS and tool_name not in {"answer_web_question"}:
            if not self.explicit_action:
                return False, "The user did not explicitly ask Jarvis to open/close/change something. Suggest it instead of executing it."
        return True, ""
