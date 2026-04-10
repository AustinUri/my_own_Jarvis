from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from core.config import AppConfig
from core.events import AssistantReply, ToolAction


HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
CALC_SANITIZE_RE = re.compile(r"[^0-9\-+*/().%^ ]+")
EN_WEB_Q_RE = re.compile(r"^(who|what|when|where|why|how|which|is|are|can|could|did|does|do)\b", re.IGNORECASE)
HE_WEB_Q_RE = re.compile(r"^(מי|מה|מתי|איפה|למה|איך|איזה|האם|כמה|מיהו|מיהם|מהו|מהי)\b")
CURRENT_HINTS_RE = re.compile(r"\b(latest|current|today|news|update|now|recent)\b", re.IGNORECASE)
HE_CURRENT_HINTS_RE = re.compile(r"(היום|עכשיו|אחרון|עדכני|חדש|חדשות|כיום|נוכחי)")
PERSONAL_HINTS_RE = re.compile(r"\b(my|mine|me|today|tonight|tomorrow|this week|my schedule|my calendar|reminders|notes|downloads|documents|messages|email|inbox)\b", re.IGNORECASE)
HE_PERSONAL_HINTS_RE = re.compile(r"(שלי|אצלי|היום|הלילה|מחר|השבוע|היומן|הלוז|לוח זמנים|תזכורות|פתקים|הורדות|מסמכים|הודעות|מייל|דואר)")


class Brain:
    def __init__(self, config: AppConfig):
        self.config = config

    def detect_language(self, text: str) -> str:
        if self.config.language_mode in {"Hebrew", "English"}:
            return "he" if self.config.language_mode == "Hebrew" else "en"
        return "he" if HEBREW_RE.search(text) else "en"

    def _personal_domain_reply(self, user_text: str, language: str) -> AssistantReply | None:
        lowered = user_text.lower().strip()

        def make(gui: str, spoken: str, intent: str = "personal_unavailable") -> AssistantReply:
            return AssistantReply(language, intent, gui, spoken, tool=None, raw_user_text=user_text)

        schedule_tokens = ["schedule", "calendar", "my day", "today", "tonight", "tomorrow", "לוח זמנים", "יומן", "הלוז", "מה יש לי", "מה קורה לי", "היום", "הלילה", "מחר"]
        reminders_tokens = ["reminders", "reminder", "notes", "messages", "email", "inbox", "תזכורות", "פתקים", "הודעות", "מייל", "דואר"]
        personal_markers = ["my", "mine", "שלי", "אצלי"]

        has_schedule = any(token in lowered for token in schedule_tokens)
        has_private_bucket = any(token in lowered for token in reminders_tokens)
        has_personal_marker = any(token in lowered for token in personal_markers)

        if has_schedule and (has_personal_marker or any(token in lowered for token in ["today", "tonight", "tomorrow", "היום", "הלילה", "מחר", "what is on", "what do i have", "show me", "what's on"])):
            return make(
                "אני עדיין לא יכול לגשת ללוח הזמנים האישי שלך." if language == "he" else "I can't access your personal schedule yet.",
                "I can't access your personal schedule yet.",
            )

        if has_private_bucket and has_personal_marker:
            return make(
                "אני עדיין לא יכול לגשת למידע האישי הזה." if language == "he" else "I can't access that personal information yet.",
                "I can't access that personal information yet.",
            )

        return None

    def build_reply(self, user_text: str) -> AssistantReply:
        language = self.detect_language(user_text)
        personal_reply = self._personal_domain_reply(user_text, language)
        if personal_reply is not None:
            return self._apply_personality(personal_reply)
        ollama_reply = self._try_ollama(user_text, language)
        if ollama_reply is not None:
            if ollama_reply.intent == "answer_web_question" and self._personal_domain_reply(user_text, language) is not None:
                return self._apply_personality(self._personal_domain_reply(user_text, language))
            return self._apply_personality(ollama_reply)
        return self._apply_personality(self._fallback_reply(user_text, language))

    def _assistant_style_prompt(self) -> str:
        tone = self.config.tone_mode.lower()
        address = (self.config.address_name or "sir").strip()
        verbosity = self.config.verbosity_mode.lower()
        rules = [
            f"Tone should be {tone}.",
            f"Verbosity should be {verbosity}.",
            f"Address the user as '{address}' when it fits naturally.",
        ]
        if self.config.auto_open_explicit_only:
            rules.append("Do not open or launch apps unless the user explicitly asks to open, show, launch, bring up, or run them.")
        if self.config.ask_before_open_related_apps:
            rules.append("If opening a related app could help but was not explicitly requested, suggest it briefly instead of opening it automatically.")
        return " ".join(rules)

    def _try_ollama(self, user_text: str, language: str) -> AssistantReply | None:
        system_prompt = (
            "You are the brain of a local desktop assistant named Jarvis. "
            "Return strict JSON only with keys: user_language, intent, gui_text, spoken_text, tool. "
            "The user_language must be 'he' or 'en'. gui_text should match the user's language. "
            "spoken_text must be concise English. tool must be null or an object with keys name and args. "
            "Prefer these tools only when relevant: open_app, close_app, open_website, search_web, answer_web_question, open_folder, "
            "tell_time, tell_date, system_status, calculate, create_note, search_files, lock_computer, shutdown_request. "
            "For factual or current-event questions, prefer answer_web_question. Never use web search for the user's personal schedule, calendar, reminders, notes, messages, or inbox. For unsupported personal data requests, say you cannot access that personal information yet. "
            f"{self._assistant_style_prompt()} "
            "Never output markdown. Never invent unsupported tools."
        )
        payload: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "user_language": {"type": "string"},
                    "intent": {"type": "string"},
                    "gui_text": {"type": "string"},
                    "spoken_text": {"type": "string"},
                    "tool": {
                        "type": ["object", "null"],
                        "properties": {
                            "name": {"type": "string"},
                            "args": {"type": "object"},
                        },
                        "required": ["name", "args"],
                        "additionalProperties": False,
                    },
                },
                "required": ["user_language", "intent", "gui_text", "spoken_text", "tool"],
                "additionalProperties": False,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return None

        try:
            content = raw["message"]["content"]
            parsed = json.loads(content)
            tool = parsed.get("tool")
            tool_action = None
            if isinstance(tool, dict):
                tool_action = ToolAction(name=tool["name"], args=tool.get("args", {}))
            return AssistantReply(
                user_language=parsed.get("user_language", language),
                intent=parsed.get("intent", "chat"),
                gui_text=parsed["gui_text"],
                spoken_text=parsed["spoken_text"],
                tool=tool_action,
                raw_user_text=user_text,
            )
        except (KeyError, TypeError, json.JSONDecodeError):
            return None

    def _fallback_reply(self, user_text: str, language: str) -> AssistantReply:
        lowered = user_text.lower().strip()

        def make(gui: str, spoken: str, intent: str = "chat", tool: ToolAction | None = None) -> AssistantReply:
            return AssistantReply(language, intent, gui, spoken, tool=tool, raw_user_text=user_text)

        def lang_text(he_text: str, en_text: str) -> str:
            return he_text if language == "he" else en_text

        app_map = {
            "chrome": ["chrome", "כרום"],
            "spotify": ["spotify", "ספוטיפיי", "ספוטיפי"],
            "notepad": ["notepad", "פנקס", "נוטפד"],
            "calculator": ["calculator", "calc", "מחשבון"],
            "explorer": ["explorer", "file explorer", "קבצים", "סייר הקבצים", "סייר"],
            "edge": ["edge", "microsoft edge", "אדג'", "אדג"],
            "discord": ["discord", "דיסקורד"],
            "vscode": ["vscode", "vs code", "visual studio code", "קוד", "ויז'ואל סטודיו קוד"],
            "instagram": ["instagram", "insta", "אינסטגרם"],
        }
        site_map = {
            "youtube": ["youtube", "יוטיוב"],
            "google": ["google", "גוגל"],
            "gmail": ["gmail", "ג'ימייל", "גימייל"],
            "github": ["github", "גיטהאב", "גיט האב"],
            "chatgpt": ["chatgpt", "צ'אט ג'יפיטי", "צאט גיפיטי"],
            "whatsapp": ["whatsapp", "ווטסאפ", "וואטסאפ"],
            "instagram": ["instagram", "insta", "אינסטגרם"],
        }
        folder_map = {
            "desktop": ["desktop", "שולחן העבודה"],
            "downloads": ["downloads", "download", "הורדות"],
            "documents": ["documents", "docs", "מסמכים"],
            "pictures": ["pictures", "photos", "תמונות"],
            "music": ["music", "מוזיקה"],
            "videos": ["videos", "סרטונים", "וידאו"],
        }

        open_tokens = ["open", "launch", "run", "bring up", "show", "פתח", "תפתח", "תפעיל", "תריץ", "תראה", "תציג"]
        close_tokens = ["close", "quit", "kill", "סגור", "תסגור", "תכבה"]

        explicit_open = any(token in lowered for token in open_tokens)

        for app_name, aliases in app_map.items():
            if any(alias in lowered for alias in aliases) and any(token in lowered for token in close_tokens):
                return make(
                    lang_text(f"סוגר את {app_name}.", f"Closing {app_name}."),
                    f"Closing {app_name}.",
                    intent="close_app",
                    tool=ToolAction("close_app", {"app": app_name}),
                )

        for app_name, aliases in app_map.items():
            if any(alias in lowered for alias in aliases) and explicit_open:
                return make(
                    lang_text(f"פותח את {app_name} עכשיו.", f"Opening {app_name} now."),
                    f"Opening {app_name} now.",
                    intent="open_app",
                    tool=ToolAction("open_app", {"app": app_name}),
                )

        for site_name, aliases in site_map.items():
            if any(alias in lowered for alias in aliases) and explicit_open:
                return make(
                    lang_text(f"פותח את {site_name}.", f"Opening {site_name}."),
                    f"Opening {site_name}.",
                    intent="open_website",
                    tool=ToolAction("open_website", {"site": site_name}),
                )

        for folder_name, aliases in folder_map.items():
            if any(alias in lowered for alias in aliases) and explicit_open:
                return make(
                    lang_text(f"פותח את תיקיית {folder_name}.", f"Opening the {folder_name} folder."),
                    f"Opening the {folder_name} folder.",
                    intent="open_folder",
                    tool=ToolAction("open_folder", {"folder": folder_name}),
                )

        if any(token in lowered for token in ["what is the date", "date today", "day is it", "what day", "תאריך", "איזה יום", "מה התאריך", "מה היום"]):
            return make(
                lang_text("בודק את התאריך.", "Checking the date."),
                "Checking the date.",
                intent="tell_date",
                tool=ToolAction("tell_date", {}),
            )

        if any(token in lowered for token in ["what time", "time is it", "current time", "שעה", "מה השעה"]):
            return make(
                lang_text("בודק את השעה עכשיו.", "Checking the time now."),
                "Checking the time now.",
                intent="tell_time",
                tool=ToolAction("tell_time", {}),
            )

        if any(token in lowered for token in ["system status", "pc status", "cpu", "ram", "memory usage", "status", "מצב המחשב", "שימוש בזיכרון", "שימוש במעבד", "מצב המערכת"]):
            return make(
                lang_text("בודק את מצב המחשב.", "Checking the PC status."),
                "Checking the PC status.",
                intent="system_status",
                tool=ToolAction("system_status", {}),
            )

        if any(token in lowered for token in ["lock computer", "lock pc", "lock the computer", "נעל את המחשב", "תנעל את המחשב"]):
            return make(
                lang_text("נועל את המחשב.", "Locking the computer."),
                "Locking the computer.",
                intent="lock_computer",
                tool=ToolAction("lock_computer", {}),
            )

        if any(token in lowered for token in ["calculate", "חשב", "כמה זה"]) or self._looks_like_math(user_text):
            expr = user_text
            match = re.search(r"(?:calculate|what is|חשב|כמה זה)\s+(.+)", user_text, re.IGNORECASE)
            if match:
                expr = match.group(1)
            expr = expr.replace("plus", "+").replace("minus", "-").replace("times", "*").replace("x", "*").replace("divided by", "/")
            expr = expr.replace("כפול", "*").replace("לחלק", "/").replace("פחות", "-").replace("ועוד", "+")
            expr = CALC_SANITIZE_RE.sub("", expr).strip()
            return make(
                lang_text("מחשב את הביטוי.", "Calculating that now."),
                "Calculating that now.",
                intent="calculate",
                tool=ToolAction("calculate", {"expression": expr}),
            )

        if any(token in lowered for token in ["note", "write note", "פתק", "הערה", "תרשום", "כתוב"]):
            content = user_text
            match = re.search(r"(?:note|write note|הערה|פתק|כתוב|תרשום)\s*[:\-]?\s*(.+)", user_text, re.IGNORECASE)
            if match:
                content = match.group(1).strip()
            return make(
                lang_text("יוצר קובץ הערה חדש.", "Creating a new note file."),
                "Creating a note now.",
                intent="create_note",
                tool=ToolAction("create_note", {"content": content}),
            )

        web_match = re.search(r"(?:search(?: google)? for|google|find online|חפש בגוגל|תחפש בגוגל|חפש באינטרנט|תחפש באינטרנט)\s+(.+)", user_text, re.IGNORECASE)
        if web_match:
            query = web_match.group(1).strip()
            return make(
                lang_text("פותח חיפוש אינטרנטי בדפדפן.", "Opening a web search in the browser."),
                "Opening a web search in the browser.",
                intent="search_web",
                tool=ToolAction("search_web", {"query": query}),
            )

        if self._looks_like_web_question(user_text, language):
            return make(
                lang_text("מחפש תשובה באינטרנט.", "Looking that up on the internet."),
                "Looking that up on the internet.",
                intent="answer_web_question",
                tool=ToolAction("answer_web_question", {"query": user_text}),
            )

        if any(token in lowered for token in ["find file", "search files", "search for file", "חפש קובץ", "תמצא קובץ", "מצא קובץ", "חפש קבצים"]):
            query = user_text
            match = re.search(r"(?:find file|search files|search for file|חפש קובץ|חפש קבצים|מצא קובץ)\s+(.+)", user_text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
            return make(
                lang_text("מחפש קבצים תואמים.", "Searching for matching files."),
                "Searching files now.",
                intent="search_files",
                tool=ToolAction("search_files", {"query": query}),
            )

        if any(token in lowered for token in ["shutdown", "turn off", "כבה", "תכבה", "כיבוי", "shutdown pc"]):
            return make(
                lang_text("כיבוי דורש אישור מפורש.", "Shutdown needs explicit confirmation."),
                "Shutdown requires confirmation.",
                intent="shutdown_request",
                tool=ToolAction("shutdown_request", {}),
            )

        if any(alias in lowered for alias in ["schedule", "calendar", "לוח זמנים", "יומן", "הלוז"]) and not explicit_open:
            return make(
                lang_text("אני עדיין לא יכול לגשת ללוח הזמנים האישי שלך.", "I can't access your personal schedule yet."),
                "I can't access your personal schedule yet.",
                intent="personal_unavailable",
            )

        help_he = (
            "אני יכול לפתוח או לסגור אפליקציות, לפתוח את YouTube או Gmail, לפתוח תיקיות כמו Downloads, "
            "להגיד שעה או תאריך, לבדוק מצב מחשב, לחשב תרגיל, לחפש קבצים, ליצור הערה, לנעול את המחשב, "
            "או לחפש תשובה באינטרנט לשאלות עובדתיות. אם תרצה שאפתח משהו קשור, בקש את זה במפורש."
        )
        help_en = (
            "I can open or close apps, open sites like YouTube or Gmail, open folders like Downloads, "
            "tell the time or date, check PC status, calculate expressions, search files, create a note, "
            "lock the computer, or look up factual questions on the internet. If you want me to bring something up, ask explicitly."
        )
        return make(help_he if language == "he" else help_en, "Give me a command.")

    def _looks_like_math(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        return bool(re.fullmatch(r"[0-9\s+\-*/().%^=]+", stripped))

    def _looks_like_web_question(self, text: str, language: str) -> bool:
        lowered = text.lower().strip()
        if any(token in lowered for token in ["open ", "close ", "bring up", "show ", "פתח", "סגור", "תציג", "search files", "חפש קובץ", "write note", "הערה", "calculate", "חשב", "כמה זה"]):
            return False
        if self._personal_domain_reply(text, language) is not None:
            return False
        if language == "he":
            return bool(HE_WEB_Q_RE.search(lowered) or HE_CURRENT_HINTS_RE.search(lowered) or lowered.endswith("?"))
        return bool(EN_WEB_Q_RE.search(lowered) or CURRENT_HINTS_RE.search(lowered) or lowered.endswith("?"))

    def _apply_personality(self, reply: AssistantReply) -> AssistantReply:
        if self.config.tone_mode != "Respectful":
            return reply
        address = (self.config.address_name or "sir").strip()
        if not address:
            return reply

        gui_text = reply.gui_text
        spoken_text = reply.spoken_text

        if reply.user_language == "he":
            if not gui_text.lower().startswith(address.lower()):
                gui_text = f"{address}, {gui_text}"
        else:
            if not gui_text.lower().startswith(address.lower()):
                gui_text = f"{address.capitalize()}, {gui_text}"

        if not spoken_text.lower().startswith(address.lower()):
            spoken_text = f"{address.capitalize()}, {spoken_text}"

        return AssistantReply(
            user_language=reply.user_language,
            intent=reply.intent,
            gui_text=gui_text,
            spoken_text=spoken_text,
            tool=reply.tool,
            raw_user_text=reply.raw_user_text,
        )
