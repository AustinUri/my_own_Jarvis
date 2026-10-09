from __future__ import annotations

import os
import re
import threading
import time
from typing import Any

from .api import CloudApiClient, default_token_file


_MEMORY_MARKER = "JARVIS SHARED MEMORY (canonical Oracle cross-device context)"
_LOCK = threading.RLock()
_DISABLED_UNTIL = 0.0
_CACHE_QUERY = ""
_CACHE_PROMPT = ""
_CACHE_AT = 0.0
_CACHE_TTL_SECONDS = 8.0
_FAILURE_BACKOFF_SECONDS = 30.0


def _enabled() -> bool:
    raw = str(os.getenv("JARVIS_ORACLE_MEMORY_READ", "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(part.strip() for part in parts if part and part.strip()).strip()
    return ""


def last_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages or []):
        if str(message.get("role") or "").lower() != "user":
            continue
        text = _content_text(message.get("content"))
        if text:
            return text
    return ""


def inject_memory_prompt(
    messages: list[dict[str, Any]],
    memory_prompt: str,
) -> list[dict[str, Any]]:
    """Merge Oracle memory into the *first* system message.

    LM Studio/Qwen chat templates used by JARVIS reject a later system role.
    Therefore shared memory must never be injected as a second system message.
    If a system message exists, enrich that first message in-place.  If none
    exists, create exactly one system message at index 0.
    """
    prompt = str(memory_prompt or "").strip()
    copied = [dict(message) for message in (messages or [])]
    if not prompt:
        return copied

    block = (
        f"{_MEMORY_MARKER}:\n"
        f"{prompt}\n\n"
        "Use this memory only when relevant to the current user request. "
        "If it directly answers the current request, answer from this memory and do not browse the web or call tools. "
        "The user's current request and corrections override older memory. "
        "Do not expose internal memory metadata unless the user explicitly asks about memory."
    )

    # If already injected, do not duplicate it.
    for message in copied:
        if _MEMORY_MARKER in _content_text(message.get("content")):
            return copied

    if copied and str(copied[0].get("role") or "").lower() == "system":
        existing = _content_text(copied[0].get("content"))
        copied[0]["content"] = f"{existing}\n\n{block}" if existing else block
    else:
        copied.insert(0, {"role": "system", "content": block})

    # Defensive normalization: a few legacy paths can accidentally carry
    # additional system messages. Merge them into the first system prompt so
    # LM Studio sees exactly one system role and it is at index 0.
    first = copied[0]
    normalized = [first]
    extra_system_text: list[str] = []
    for message in copied[1:]:
        if str(message.get("role") or "").lower() == "system":
            text = _content_text(message.get("content"))
            if text:
                extra_system_text.append(text)
            continue
        normalized.append(message)

    if extra_system_text:
        base = _content_text(first.get("content"))
        first["content"] = "\n\n".join([base, *extra_system_text]).strip()

    return normalized



_RECALL_QUESTION_RE = re.compile(
    r"(?:\bwhat(?:'s|\s+is|\s+was)\s+my\b|"
    r"\bwhat\s+did\s+i\s+(?:tell|say)\s+(?:you|earlier)\b|"
    r"\bdo\s+you\s+remember\b|\bwhat\s+do\s+you\s+remember\b|"
    r"\bwhat\s+(?:is|was)\s+.+?\s+called\b|"
    r"\bwhat\s+(?:was|is)\s+the\s+name\s+of\s+my\b|"
    r"(?:מה|איך)\s+(?:קוראים|נקרא)\s+|"
    r"(?:מה|איזה)\s+.+?\s+שלי|"
    r"(?:אתה\s+)?זוכר(?:ת)?\b|מה\s+אמרתי\s+לך)",
    re.IGNORECASE,
)


def is_personal_recall_question(query: str) -> bool:
    """Return True only for clear personal/cross-device recall questions.

    This is intentionally conservative.  Tool suppression is only safe when
    Oracle already returned relevant memory and the user is plainly asking
    JARVIS to recall something personal rather than perform an external action.
    """
    clean = " ".join(str(query or "").split())
    return bool(clean and _RECALL_QUESTION_RE.search(clean))


def prepare_messages_with_oracle_memory(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    """Inject relevant Oracle memory and report a direct-memory recall hit.

    ``direct_memory_hit`` is true only when Oracle returned non-empty relevant
    context *and* the current request is a clear personal recall question.  The
    provider can then keep web/device tools out of that model round so the
    model cannot turn a private-memory question into a web search.
    """
    query = last_user_text(messages)
    if not query:
        return [dict(message) for message in (messages or [])], False

    prompt = _fetch_prompt(query)
    augmented = inject_memory_prompt(messages, prompt)
    return augmented, bool(prompt and is_personal_recall_question(query))

def _fetch_prompt(query: str) -> str:
    global _DISABLED_UNTIL, _CACHE_QUERY, _CACHE_PROMPT, _CACHE_AT

    clean = " ".join(str(query or "").split())
    if not clean or not _enabled():
        return ""

    token_path = default_token_file()
    if not token_path.exists():
        return ""

    now = time.monotonic()
    with _LOCK:
        if now < _DISABLED_UNTIL:
            return ""
        if clean == _CACHE_QUERY and (now - _CACHE_AT) <= _CACHE_TTL_SECONDS:
            return _CACHE_PROMPT

    try:
        api = CloudApiClient(timeout=3.0)
        context = api.memory_context(
            clean,
            memory_scope="primary",
            fact_limit=16,
            turn_limit=8,
        )
        prompt = str(context.get("prompt") or "").strip()
        if len(prompt) > 6000:
            prompt = prompt[:6000]
    except Exception:
        with _LOCK:
            _DISABLED_UNTIL = time.monotonic() + _FAILURE_BACKOFF_SECONDS
        return ""

    with _LOCK:
        _CACHE_QUERY = clean
        _CACHE_PROMPT = prompt
        _CACHE_AT = time.monotonic()
        _DISABLED_UNTIL = 0.0
    return prompt


def augment_messages_with_oracle_memory(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Backward-compatible fail-open cross-device memory injection."""
    augmented, _direct_memory_hit = prepare_messages_with_oracle_memory(messages)
    return augmented
