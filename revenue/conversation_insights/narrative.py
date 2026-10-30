from __future__ import annotations
import re


def contains_hebrew(s: str | None) -> bool:
    return bool(s and re.search(r"[\u0590-\u05FF]", s))


def choose_report_language(requested: str, aliases: dict[str, str], chat_guess: str) -> str:
    if requested in {"he", "en"}:
        return requested
    if chat_guess in {"he", "en"}:
        return chat_guess
    if any(contains_hebrew(v) for v in (aliases or {}).values()):
        return "he"
    return "en"
