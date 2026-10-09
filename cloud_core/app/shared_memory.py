from __future__ import annotations

import hashlib
from contextlib import contextmanager
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator


DEFAULT_SCOPE = "primary"
DEFAULT_TURN_RETENTION_DAYS = 30


def _utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now() -> str:
    return _utc_now_dt().isoformat()


def default_memory_db_path() -> Path:
    configured = str(os.getenv("JARVIS_MEMORY_DB") or "").strip()
    if configured:
        return Path(configured).expanduser()

    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA") or Path.home())
        return root / "Jarvis" / "cloud_memory.sqlite3"

    return Path.home() / ".local" / "share" / "jarvis" / "cloud_memory.sqlite3"


class SharedMemoryStore:
    """Canonical cross-device memory owned by Oracle Cloud Core.

    V30.1 adds a conservative Memory Gate in front of durable facts:
    * explicit remember/forget/correct/show commands are deterministic;
    * only high-confidence stable statements are auto-saved;
    * credentials/secrets are never written as durable facts;
    * sensitive information is never auto-saved (explicit remember is required);
    * recent conversation is retained for a bounded period and is not a fact store.
    """

    _REMEMBER_PATTERNS = (
        re.compile(r"^\s*remember(?:\s+that)?\s+(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*please\s+remember(?:\s+that)?\s+(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*תזכור(?:\s+ש)?\s*(.+?)\s*$"),
        re.compile(r"^\s*זכור(?:\s+ש)?\s*(.+?)\s*$"),
    )

    _SHOW_PATTERNS = (
        re.compile(r"^\s*(?:show|tell)\s+me\s+what\s+you\s+remember(?:\s+about\s+me)?[?.!]*\s*$", re.IGNORECASE),
        re.compile(r"^\s*what\s+do\s+you\s+remember(?:\s+about\s+me)?[?.!]*\s*$", re.IGNORECASE),
        re.compile(r"^\s*(?:show|list)\s+(?:my\s+)?memor(?:y|ies)[?.!]*\s*$", re.IGNORECASE),
        re.compile(r"^\s*מה\s+אתה\s+זוכר(?:\s+עלי)?[?.!]*\s*$"),
        re.compile(r"^\s*תראה\s+לי\s+מה\s+אתה\s+זוכר[?.!]*\s*$"),
    )

    _FORGET_ALL_PATTERNS = (
        re.compile(r"^\s*forget\s+(?:everything|all)(?:\s+you\s+remember)?[?.!]*\s*$", re.IGNORECASE),
        re.compile(r"^\s*(?:clear|delete)\s+(?:all\s+)?(?:my\s+)?memor(?:y|ies)[?.!]*\s*$", re.IGNORECASE),
        re.compile(r"^\s*תשכח\s+(?:הכל|את\s+הכל)[?.!]*\s*$"),
        re.compile(r"^\s*מחק\s+(?:את\s+)?כל\s+הזיכרון[?.!]*\s*$"),
    )

    _FORGET_PATTERNS = (
        re.compile(r"^\s*forget(?:\s+that)?\s+(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*delete\s+(?:the\s+)?memory\s+(?:that\s+)?(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*תשכח(?:\s+ש|\s+את)?\s*(.+?)\s*$"),
        re.compile(r"^\s*מחק\s+מהזיכרון\s+(.+?)\s*$"),
    )

    _CORRECT_PATTERNS = (
        re.compile(r"^\s*(?:correct|change)\s+(.+?)\s+(?:to|into)\s+(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*correction\s*[:,-]\s*(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*actually\s*[,:-]?\s*(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*תקן(?:\s+את)?\s+(.+?)\s+ל(?:-|־)?\s*(.+?)\s*$"),
        re.compile(r"^\s*בעצם\s*[,:-]?\s*(.+?)\s*$"),
    )

    # Things that should never be placed in durable memory, even on an explicit
    # "remember" command. The conversation turn can still exist briefly, but the
    # durable fact gate refuses it.
    _HARD_SECRET_PATTERNS = (
        re.compile(r"\bpassword\b", re.IGNORECASE),
        re.compile(r"\bpasscode\b", re.IGNORECASE),
        re.compile(r"\bpin\b", re.IGNORECASE),
        re.compile(r"\botp\b", re.IGNORECASE),
        re.compile(r"\b2fa\b", re.IGNORECASE),
        re.compile(r"\bone[- ]time\s+(?:password|code)\b", re.IGNORECASE),
        re.compile(r"\bapi[- ]?key\b", re.IGNORECASE),
        re.compile(r"\bprivate[- ]?key\b", re.IGNORECASE),
        re.compile(r"\bsecret[- ]?key\b", re.IGNORECASE),
        re.compile(r"\bauth(?:entication)?[- ]?token\b", re.IGNORECASE),
        re.compile(r"\bbearer\s+token\b", re.IGNORECASE),
        re.compile(r"\bcvv\b", re.IGNORECASE),
        re.compile(r"\bcredit\s*card\s*(?:number)?\b", re.IGNORECASE),
        re.compile(r"\bseed\s+phrase\b", re.IGNORECASE),
        re.compile(r"\brecovery\s+phrase\b", re.IGNORECASE),
        re.compile(r"סיסמ[אה]"),
        re.compile(r"קוד\s+אימות"),
        re.compile(r"קוד\s+חד[- ]פעמי"),
        re.compile(r"מפתח\s+(?:api|פרטי)", re.IGNORECASE),
        re.compile(r"כרטיס\s+אשראי"),
    )

    # These are not blocked when the user explicitly asks JARVIS to remember
    # them, but they are never auto-saved from casual conversation.
    _SECRET_DISCLOSURE_PATTERNS = (
        re.compile(r"\b(?:my\s+)?(?:password|passcode|pin|otp|api[- ]?key|auth(?:entication)?[- ]?token|cvv)\s*(?:is|=|:)\s*\S+", re.IGNORECASE),
        re.compile(r"(?:הסיסמ[אה]|הפין|קוד\s+האימות|מפתח\s+ה-api)\s+שלי\s+(?:הוא|היא|זה|:)\s*\S+", re.IGNORECASE),
    )

    _SENSITIVE_AUTO_BLOCK_PATTERNS = (
        re.compile(r"\b(?:diagnosis|diagnosed|medical|medication|medicine|prescription)\b", re.IGNORECASE),
        re.compile(r"\b(?:bank\s+account|iban|routing\s+number|passport|social\s+security|national\s+id)\b", re.IGNORECASE),
        re.compile(r"\b(?:home\s+address|street\s+address)\b", re.IGNORECASE),
        re.compile(r"(?:אבחנה|תרופ|מרשם|חשבון\s+בנק|דרכון|תעודת\s+זהות|כתובת\s+בית)"),
    )

    _AUTO_STABLE_PATTERNS = (
        ("preference", re.compile(r"^\s*i\s+(?:strongly\s+)?prefer\s+(.+?)\s*$", re.IGNORECASE)),
        ("preference", re.compile(r"^\s*from\s+now\s+on\s+(.+?)\s*$", re.IGNORECASE)),
        ("profile", re.compile(r"^\s*my\s+(.+?)\s+is\s+called\s+(.+?)\s*$", re.IGNORECASE)),
        ("profile", re.compile(r"^\s*my\s+(.+?)\s+is\s+(.+?)\s*$", re.IGNORECASE)),
        ("project", re.compile(r"^\s*we\s+(?:decided|agreed)\s+(?:that\s+)?(.+?)\s*$", re.IGNORECASE)),
        ("preference", re.compile(r"^\s*אני\s+מעדיף\s+(.+?)\s*$")),
        ("project", re.compile(r"^\s*החלטנו\s+ש(.+?)\s*$")),
    )

    _EPHEMERAL_HINTS = re.compile(
        r"\b(?:today|tonight|tomorrow|yesterday|right\s+now|for\s+now|this\s+time|currently\s+looking)\b|(?:היום|הלילה|מחר|אתמול|כרגע|בינתיים)",
        re.IGNORECASE,
    )

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or default_memory_db_path())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    @property
    def turn_retention_days(self) -> int:
        raw = str(os.getenv("JARVIS_MEMORY_TURN_DAYS") or DEFAULT_TURN_RETENTION_DAYS).strip()
        try:
            return max(1, min(365, int(raw)))
        except ValueError:
            return DEFAULT_TURN_RETENTION_DAYS

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            str(self.db_path),
            timeout=15.0,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self._lock, self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    source_device TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'fact',
                    source_kind TEXT NOT NULL DEFAULT 'explicit',
                    UNIQUE(scope, memory_key)
                );

                CREATE INDEX IF NOT EXISTS idx_memory_facts_scope_updated
                ON memory_facts(scope, updated_at DESC);

                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL,
                    source_device TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conversation_turns_scope_id
                ON conversation_turns(scope, id DESC);
                """
            )

            # Migrate databases created by the first V30 shared-memory patch.
            columns = {
                str(row["name"])
                for row in db.execute("PRAGMA table_info(memory_facts)").fetchall()
            }
            if "category" not in columns:
                db.execute("ALTER TABLE memory_facts ADD COLUMN category TEXT NOT NULL DEFAULT 'fact'")
            if "source_kind" not in columns:
                db.execute("ALTER TABLE memory_facts ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'explicit'")

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _slug(value: str) -> str:
        clean = re.sub(r"[^\w\u0590-\u05FF]+", "_", str(value or "").casefold(), flags=re.UNICODE)
        return clean.strip("_")[:80]

    @staticmethod
    def _stable_key(value: str) -> str:
        digest = hashlib.sha256(value.casefold().encode("utf-8")).hexdigest()[:16]
        return f"note:{digest}"

    def _semantic_key(self, value: str, category: str = "fact") -> str | None:
        clean = self._normalize(value)
        patterns = (
            re.compile(r"^my\s+(.+?)\s+is\s+called\s+.+$", re.IGNORECASE),
            re.compile(r"^my\s+(.+?)\s+is\s+.+$", re.IGNORECASE),
            re.compile(r"^the\s+(.+?)\s+is\s+.+$", re.IGNORECASE),
        )
        for pattern in patterns:
            match = pattern.match(clean)
            if match:
                subject = self._slug(match.group(1))
                if subject:
                    return f"{category}:{subject}"

        hebrew = re.match(r"^(.+?)\s+שלי\s+(?:הוא|היא|זה)\s+.+$", clean)
        if hebrew:
            subject = self._slug(hebrew.group(1))
            if subject:
                return f"{category}:{subject}"
        return None

    def _contains_hard_secret(self, text: str) -> bool:
        clean = self._normalize(text)
        if any(pattern.search(clean) for pattern in self._HARD_SECRET_PATTERNS):
            return True

        # Common credential-like literals. Deliberately conservative: long
        # bearer/JWT/private-token shapes should not become durable facts.
        if re.search(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", clean):
            return True
        if re.search(r"\b(?:sk|pk|ghp|github_pat)_[A-Za-z0-9_-]{16,}\b", clean, flags=re.IGNORECASE):
            return True
        return False

    def _contains_sensitive_auto_block(self, text: str) -> bool:
        clean = self._normalize(text)
        return any(pattern.search(clean) for pattern in self._SENSITIVE_AUTO_BLOCK_PATTERNS)

    def _contains_secret_disclosure(self, text: str) -> bool:
        clean = self._normalize(text)
        if any(pattern.search(clean) for pattern in self._SECRET_DISCLOSURE_PATTERNS):
            return True
        if re.search(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", clean):
            return True
        if re.search(r"\b(?:sk|pk|ghp|github_pat)_[A-Za-z0-9_-]{16,}\b", clean, flags=re.IGNORECASE):
            return True
        return False

    def remember(
        self,
        value: str,
        *,
        source_device: str,
        scope: str = DEFAULT_SCOPE,
        key: str | None = None,
        category: str = "fact",
        source_kind: str = "explicit",
    ) -> dict:
        clean_value = self._normalize(value)
        if not clean_value:
            raise ValueError("Memory value cannot be empty")
        if self._contains_hard_secret(clean_value):
            raise ValueError("Secrets and credentials cannot be stored in durable memory")

        clean_scope = self._normalize(scope) or DEFAULT_SCOPE
        clean_source = self._normalize(source_device) or "unknown"
        clean_category = self._slug(category) or "fact"
        clean_kind = self._slug(source_kind) or "explicit"
        memory_key = self._normalize(key or "") or self._semantic_key(clean_value, clean_category) or self._stable_key(clean_value)
        now = _utc_now()

        with self._lock, self._connect() as db:
            db.execute(
                """
                INSERT INTO memory_facts(
                    scope, memory_key, value, source_device, created_at, updated_at,
                    category, source_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scope, memory_key) DO UPDATE SET
                    value=excluded.value,
                    source_device=excluded.source_device,
                    updated_at=excluded.updated_at,
                    category=excluded.category,
                    source_kind=excluded.source_kind
                """,
                (
                    clean_scope,
                    memory_key,
                    clean_value,
                    clean_source,
                    now,
                    now,
                    clean_category,
                    clean_kind,
                ),
            )

        return {
            "scope": clean_scope,
            "key": memory_key,
            "value": clean_value,
            "source_device": clean_source,
            "category": clean_category,
            "source_kind": clean_kind,
            "updated_at": now,
        }

    def remember_from_text(
        self,
        text: str,
        *,
        source_device: str,
        scope: str = DEFAULT_SCOPE,
    ) -> dict | None:
        """Backward-compatible explicit remember parser."""
        decision = self.process_user_text(
            text,
            source_device=source_device,
            scope=scope,
            allow_auto=False,
        )
        if decision.get("action") == "remember":
            return decision.get("memory")
        return None

    def _auto_memory_candidate(self, text: str) -> tuple[str, str] | None:
        clean = self._normalize(text)
        if not clean or len(clean) < 8 or len(clean) > 600:
            return None
        if self._EPHEMERAL_HINTS.search(clean):
            return None
        if self._contains_hard_secret(clean) or self._contains_sensitive_auto_block(clean):
            return None

        for category, pattern in self._AUTO_STABLE_PATTERNS:
            if pattern.match(clean):
                return category, clean
        return None

    def _find_matching_fact(self, target: str, *, scope: str) -> dict | None:
        clean_target = self._normalize(target).casefold()
        if not clean_target:
            return None
        target_tokens = self._tokens(clean_target)
        best: tuple[float, dict] | None = None

        for fact in self.list_facts(scope=scope, limit=500):
            value = self._normalize(str(fact.get("value") or ""))
            folded = value.casefold()
            if clean_target == folded:
                score = 1.0
            elif clean_target in folded or folded in clean_target:
                score = 0.95
            else:
                value_tokens = self._tokens(value)
                union = target_tokens | value_tokens
                score = (len(target_tokens & value_tokens) / len(union)) if union else 0.0

            if best is None or score > best[0]:
                best = (score, fact)

        if best is None or best[0] < 0.55:
            return None
        return best[1]

    def forget_matching(self, target: str, *, scope: str = DEFAULT_SCOPE) -> dict | None:
        clean_scope = self._normalize(scope) or DEFAULT_SCOPE
        match = self._find_matching_fact(target, scope=clean_scope)
        if not match:
            return None

        with self._lock, self._connect() as db:
            db.execute(
                "DELETE FROM memory_facts WHERE scope = ? AND memory_key = ?",
                (clean_scope, match["key"]),
            )
        return match

    def clear_facts(self, *, scope: str = DEFAULT_SCOPE) -> int:
        clean_scope = self._normalize(scope) or DEFAULT_SCOPE
        with self._lock, self._connect() as db:
            cursor = db.execute("DELETE FROM memory_facts WHERE scope = ?", (clean_scope,))
            return int(cursor.rowcount or 0)

    def correct_matching(
        self,
        old: str | None,
        new: str,
        *,
        source_device: str,
        scope: str = DEFAULT_SCOPE,
    ) -> dict:
        clean_scope = self._normalize(scope) or DEFAULT_SCOPE
        clean_new = self._normalize(new)
        if not clean_new:
            raise ValueError("Corrected memory cannot be empty")
        if self._contains_hard_secret(clean_new):
            raise ValueError("Secrets and credentials cannot be stored in durable memory")

        existing = self._find_matching_fact(old or clean_new, scope=clean_scope) if (old or clean_new) else None
        if existing:
            return self.remember(
                clean_new,
                source_device=source_device,
                scope=clean_scope,
                key=str(existing["key"]),
                category=str(existing.get("category") or "fact"),
                source_kind="correction",
            )

        return self.remember(
            clean_new,
            source_device=source_device,
            scope=clean_scope,
            category="fact",
            source_kind="correction",
        )

    def format_memory_summary(self, *, scope: str = DEFAULT_SCOPE, limit: int = 20) -> str:
        facts = self.list_facts(scope=scope, limit=limit)
        if not facts:
            return "I do not have any durable facts stored in shared memory yet."
        lines = ["Here is what I currently remember:"]
        for fact in facts:
            category = str(fact.get("category") or "fact")
            lines.append(f"- [{category}] {fact['value']}")
        return "\n".join(lines)

    def process_user_text(
        self,
        text: str,
        *,
        source_device: str,
        scope: str = DEFAULT_SCOPE,
        allow_auto: bool = True,
    ) -> dict:
        """Run the deterministic Memory Gate for a user utterance.

        The returned dict is intentionally API-friendly. `direct_response` means
        the cloud assistant can answer without spending an LLM call.
        """
        clean = self._normalize(text)
        clean_scope = self._normalize(scope) or DEFAULT_SCOPE
        clean_source = self._normalize(source_device) or "unknown"
        if not clean:
            return {"action": "none", "reason": "empty"}

        for pattern in self._SHOW_PATTERNS:
            if pattern.match(clean):
                return {
                    "action": "show",
                    "reason": "explicit_show",
                    "direct_response": self.format_memory_summary(scope=clean_scope),
                }

        for pattern in self._FORGET_ALL_PATTERNS:
            if pattern.match(clean):
                deleted = self.clear_facts(scope=clean_scope)
                return {
                    "action": "forget_all",
                    "reason": "explicit_forget_all",
                    "deleted": deleted,
                    "direct_response": f"Done. I removed {deleted} durable memor{'y' if deleted == 1 else 'ies'} from shared memory.",
                }

        for pattern in self._FORGET_PATTERNS:
            match = pattern.match(clean)
            if match:
                target = self._normalize(match.group(1))
                forgotten = self.forget_matching(target, scope=clean_scope)
                if forgotten:
                    return {
                        "action": "forget",
                        "reason": "explicit_forget",
                        "forgotten": forgotten,
                        "direct_response": f"Forgotten: {forgotten['value']}",
                    }
                return {
                    "action": "forget",
                    "reason": "no_match",
                    "forgotten": None,
                    "direct_response": "I could not find a durable memory matching that request.",
                }

        for pattern in self._CORRECT_PATTERNS:
            match = pattern.match(clean)
            if not match:
                continue
            groups = [self._normalize(item) for item in match.groups() if item is not None]
            old = groups[0] if len(groups) >= 2 else None
            new = groups[-1] if groups else ""
            if self._contains_hard_secret(new):
                return {
                    "action": "blocked",
                    "reason": "secret",
                    "direct_response": "I will not store passwords, PINs, OTPs, API keys, tokens, payment security codes, or similar secrets in long-term memory.",
                }
            corrected = self.correct_matching(
                old,
                new,
                source_device=clean_source,
                scope=clean_scope,
            )
            return {
                "action": "correct",
                "reason": "explicit_correction",
                "memory": corrected,
                "direct_response": f"Corrected. I now remember: {corrected['value']}",
            }

        for pattern in self._REMEMBER_PATTERNS:
            match = pattern.match(clean)
            if match:
                fact = self._normalize(match.group(1))
                if not fact:
                    break
                if self._contains_hard_secret(fact):
                    return {
                        "action": "blocked",
                        "reason": "secret",
                        "store_turn": False,
                        "direct_response": "I will not store passwords, PINs, OTPs, API keys, tokens, payment security codes, or similar secrets in long-term memory.",
                    }
                saved = self.remember(
                    fact,
                    source_device=clean_source,
                    scope=clean_scope,
                    category="fact",
                    source_kind="explicit",
                )
                return {
                    "action": "remember",
                    "reason": "explicit_remember",
                    "memory": saved,
                    "direct_response": f"Remembered: {saved['value']}",
                }

        # A secret disclosed in ordinary conversation may still need an answer,
        # but it must not be copied into cross-device history or durable facts.
        if self._contains_secret_disclosure(clean):
            return {
                "action": "no_store",
                "reason": "secret_disclosure",
                "store_turn": False,
                "direct_response": None,
            }

        if allow_auto:
            candidate = self._auto_memory_candidate(clean)
            if candidate:
                category, value = candidate
                saved = self.remember(
                    value,
                    source_device=clean_source,
                    scope=clean_scope,
                    category=category,
                    source_kind="auto",
                )
                return {
                    "action": "remember_auto",
                    "reason": "high_confidence_stable",
                    "memory": saved,
                    "direct_response": None,
                }

        return {"action": "none", "reason": "not_memory_worthy"}

    def _prune_turns_locked(self, db: sqlite3.Connection, *, scope: str) -> None:
        cutoff = (_utc_now_dt() - timedelta(days=self.turn_retention_days)).isoformat()
        db.execute(
            "DELETE FROM conversation_turns WHERE scope = ? AND created_at < ?",
            (scope, cutoff),
        )
        db.execute(
            """
            DELETE FROM conversation_turns
            WHERE scope = ? AND id NOT IN (
                SELECT id FROM conversation_turns
                WHERE scope = ?
                ORDER BY id DESC
                LIMIT 1000
            )
            """,
            (scope, scope),
        )

    def record_turn(
        self,
        role: str,
        content: str,
        *,
        source_device: str,
        scope: str = DEFAULT_SCOPE,
    ) -> dict:
        clean_role = self._normalize(role).lower()
        if clean_role not in {"user", "assistant", "system"}:
            raise ValueError(f"Unsupported conversation role: {role}")

        clean_content = self._normalize(content)
        if not clean_content:
            raise ValueError("Conversation content cannot be empty")

        clean_scope = self._normalize(scope) or DEFAULT_SCOPE
        clean_source = self._normalize(source_device) or "unknown"
        created_at = _utc_now()

        with self._lock, self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO conversation_turns(
                    scope, source_device, role, content, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    clean_scope,
                    clean_source,
                    clean_role,
                    clean_content,
                    created_at,
                ),
            )
            turn_id = int(cursor.lastrowid)
            self._prune_turns_locked(db, scope=clean_scope)

        return {
            "id": turn_id,
            "scope": clean_scope,
            "source_device": clean_source,
            "role": clean_role,
            "content": clean_content,
            "created_at": created_at,
        }

    def list_facts(
        self,
        *,
        scope: str = DEFAULT_SCOPE,
        limit: int = 100,
    ) -> list[dict]:
        safe_limit = max(1, min(500, int(limit)))
        clean_scope = self._normalize(scope) or DEFAULT_SCOPE

        with self._lock, self._connect() as db:
            rows = db.execute(
                """
                SELECT memory_key, value, source_device, created_at, updated_at,
                       category, source_kind
                FROM memory_facts
                WHERE scope = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (clean_scope, safe_limit),
            ).fetchall()

        return [
            {
                "key": row["memory_key"],
                "value": row["value"],
                "source_device": row["source_device"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "category": row["category"],
                "source_kind": row["source_kind"],
            }
            for row in rows
        ]

    def recent_turns(
        self,
        *,
        scope: str = DEFAULT_SCOPE,
        limit: int = 12,
    ) -> list[dict]:
        safe_limit = max(1, min(100, int(limit)))
        clean_scope = self._normalize(scope) or DEFAULT_SCOPE

        with self._lock, self._connect() as db:
            self._prune_turns_locked(db, scope=clean_scope)
            rows = db.execute(
                """
                SELECT id, source_device, role, content, created_at
                FROM conversation_turns
                WHERE scope = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (clean_scope, safe_limit),
            ).fetchall()

        rows = list(reversed(rows))
        return [
            {
                "id": int(row["id"]),
                "source_device": row["source_device"],
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    _CONTEXT_STOP_WORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "my", "your", "our", "i", "me", "you", "we", "it", "this", "that",
        "what", "which", "who", "how", "do", "does", "did", "to", "of", "in",
        "on", "for", "and", "or", "with", "about", "from", "called", "name",
        "please", "can", "could", "would", "should",
        "של", "שלי", "שלך", "מה", "מי", "איך", "את", "אתה", "אני", "הוא",
        "היא", "זה", "זאת", "עם", "על", "אל", "לי", "לך", "לנו", "קוראים",
    }

    _CONTEXT_META_RE = re.compile(
        r"\b(?:remember|memory|memories|earlier|previous|before|last\s+time|continue|we\s+discussed|i\s+told\s+you|what\s+did\s+i\s+say|what\s+do\s+you\s+know)\b"
        r"|(?:זוכר|זיכרון|זכרונות|קודם|לפני|המשך|דיברנו|אמרתי\s+לך)",
        re.IGNORECASE,
    )

    _CONTINUATION_RE = re.compile(
        r"^\s*(?:and|also|then|so|okay|ok|what\s+about|ומה|וגם|אז|אוקיי)\b",
        re.IGNORECASE,
    )

    @classmethod
    def _tokens(cls, text: str) -> set[str]:
        return {
            token.casefold()
            for token in re.findall(r"[\w\u0590-\u05FF]+", text or "", flags=re.UNICODE)
            if len(token) >= 2 and token.casefold() not in cls._CONTEXT_STOP_WORDS
        }

    @classmethod
    def _wants_broad_context(cls, query: str) -> bool:
        return bool(cls._CONTEXT_META_RE.search(query or ""))

    def _rank_facts(self, query: str, facts: Iterable[dict], limit: int) -> list[dict]:
        rows = list(facts)
        safe_limit = max(1, limit)
        if self._wants_broad_context(query):
            return rows[:safe_limit]

        query_tokens = self._tokens(query)
        if not query_tokens:
            return []

        scored: list[tuple[int, int, dict]] = []
        for index, fact in enumerate(rows):
            value = str(fact.get("value") or "")
            overlap = len(query_tokens & self._tokens(value))
            if overlap <= 0:
                continue
            scored.append((overlap, -index, fact))

        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [row[2] for row in scored[:safe_limit]]

    def _rank_turns(self, query: str, turns: Iterable[dict], limit: int) -> list[dict]:
        rows = list(turns)
        safe_limit = max(1, limit)
        if self._wants_broad_context(query) or self._CONTINUATION_RE.search(query or ""):
            return rows[-safe_limit:]

        query_tokens = self._tokens(query)
        if not query_tokens:
            return []

        scored: list[tuple[int, int, dict]] = []
        for index, turn in enumerate(rows):
            content = str(turn.get("content") or "")
            overlap = len(query_tokens & self._tokens(content))
            if overlap <= 0:
                continue
            scored.append((overlap, index, turn))

        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        selected = [row[2] for row in scored[:safe_limit]]
        selected.sort(key=lambda row: int(row.get("id") or 0))
        return selected

    def context_for(
        self,
        query: str,
        *,
        scope: str = DEFAULT_SCOPE,
        fact_limit: int = 24,
        turn_limit: int = 12,
    ) -> dict:
        all_facts = self.list_facts(scope=scope, limit=100)
        facts = self._rank_facts(query, all_facts, max(1, min(50, fact_limit)))
        recent = self.recent_turns(scope=scope, limit=40)
        turns = self._rank_turns(query, recent, max(1, min(20, turn_limit)))

        lines: list[str] = []
        if facts:
            lines.append("Shared facts:")
            for fact in facts:
                lines.append(f"- [{fact.get('category') or 'fact'}] {fact['value']}")

        if turns:
            lines.append("Recent cross-device conversation:")
            for turn in turns:
                source = turn.get("source_device") or "unknown"
                role = turn.get("role") or "user"
                lines.append(f"- [{source} | {role}] {turn.get('content') or ''}")

        prompt = "\n".join(lines).strip()
        return {
            "prompt": prompt,
            "facts": facts,
            "turns": turns,
        }

    def snapshot(
        self,
        *,
        scope: str = DEFAULT_SCOPE,
        fact_limit: int = 100,
        turn_limit: int = 30,
    ) -> dict:
        return {
            "scope": scope,
            "db_path": str(self.db_path),
            "facts": self.list_facts(scope=scope, limit=fact_limit),
            "turns": self.recent_turns(scope=scope, limit=turn_limit),
            "policy": {
                "turn_retention_days": self.turn_retention_days,
                "auto_memory": "conservative-high-confidence",
                "secrets": "never-durable",
            },
        }

    def health(self) -> dict:
        with self._lock, self._connect() as db:
            facts = int(db.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0])
            turns = int(db.execute("SELECT COUNT(*) FROM conversation_turns").fetchone()[0])

        return {
            "ok": True,
            "backend": "sqlite",
            "db_path": str(self.db_path),
            "facts": facts,
            "turns": turns,
            "turn_retention_days": self.turn_retention_days,
            "memory_gate": "enabled",
        }


memory_store = SharedMemoryStore()
