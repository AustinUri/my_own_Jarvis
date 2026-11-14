from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .device_bus import device_manager


PHONE_DEVICE_ID = os.getenv("JARVIS_PHONE_DEVICE_ID", "uri-s25")
LOCAL_TZ_NAME = os.getenv("JARVIS_LOCAL_TIMEZONE", "Asia/Jerusalem")

_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")


def _clean(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _classify_history_intent(text: str) -> str | None:
    q = _clean(text)
    if not q:
        return None

    # Explicit missed-call requests must win before generic incoming/history.
    if _contains_any(
        q,
        (
            "missed calls",
            "missed call",
            "calls i missed",
            "שיחות שלא נענו",
            "שיחות שלא עניתי",
            "שיחות שלא עניתי להן",
        ),
    ):
        return "missed"

    if _contains_any(
        q,
        (
            "who called me",
            "who has called me",
            "who tried to call me",
            "calls to me",
            "incoming calls",
            "מי התקשר אליי",
            "מי התקשר אלי",
            "מי חייג אליי",
            "מי חייג אלי",
            "שיחות נכנסות",
        ),
    ):
        return "incoming"

    if _contains_any(
        q,
        (
            "who did i call",
            "who have i called",
            "outgoing calls",
            "calls i made",
            "למי התקשרתי",
            "למי חייגתי",
            "שיחות יוצאות",
        ),
    ):
        return "outgoing"

    if _contains_any(
        q,
        (
            "call history",
            "recent calls",
            "latest calls",
            "last calls",
            "my calls",
            "היסטוריית שיחות",
            "היסטורית שיחות",
            "שיחות אחרונות",
            "השיחות האחרונות",
            "יומן שיחות",
        ),
    ):
        return "recent"

    return None


def _extract_calls(result: dict[str, Any]) -> list[dict[str, Any]]:
    calls = result.get("calls")
    if isinstance(calls, list):
        return [row for row in calls if isinstance(row, dict)]

    nested = result.get("result")
    if isinstance(nested, dict):
        calls = nested.get("calls")
        if isinstance(calls, list):
            return [row for row in calls if isinstance(row, dict)]

    return []


def _matches(kind: str, call_type: str) -> bool:
    t = (call_type or "").strip().lower()
    if kind == "recent":
        return True
    if kind == "missed":
        return t == "missed"
    if kind == "incoming":
        return t in {"incoming", "missed", "rejected", "blocked", "voicemail"}
    if kind == "outgoing":
        return t == "outgoing"
    return False


def _format_when(date_ms: Any, hebrew: bool) -> str:
    try:
        stamp = int(date_ms)
        tz = ZoneInfo(LOCAL_TZ_NAME)
        dt = datetime.fromtimestamp(stamp / 1000.0, tz=tz)
        if hebrew:
            return dt.strftime("%d/%m %H:%M")
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return ""


def _format_duration(seconds: Any, hebrew: bool) -> str:
    try:
        total = max(0, int(seconds or 0))
    except Exception:
        total = 0

    if total <= 0:
        return ""

    minutes, secs = divmod(total, 60)
    if hebrew:
        if minutes:
            return f"{minutes}:{secs:02d} דק׳"
        return f"{secs} שנ׳"
    if minutes:
        return f"{minutes}:{secs:02d} min"
    return f"{secs} sec"


def _type_label(call_type: str, hebrew: bool) -> str:
    t = (call_type or "other").strip().lower()
    if hebrew:
        return {
            "incoming": "נכנסת",
            "outgoing": "יוצאת",
            "missed": "לא נענתה",
            "rejected": "נדחתה",
            "blocked": "חסומה",
            "voicemail": "תא קולי",
        }.get(t, "אחרת")
    return {
        "incoming": "incoming",
        "outgoing": "outgoing",
        "missed": "missed",
        "rejected": "rejected",
        "blocked": "blocked",
        "voicemail": "voicemail",
    }.get(t, "other")


def _display_identity(row: dict[str, Any], hebrew: bool) -> str:
    name = str(row.get("name") or "").strip()
    number = str(row.get("number") or row.get("canonical_number") or "").strip()

    if name and name.lower() != "unknown":
        if number:
            return f"{name} ({number})"
        return name

    if number:
        return number

    return "לא ידוע" if hebrew else "Unknown"


def _title(kind: str, hebrew: bool) -> str:
    if hebrew:
        return {
            "recent": "השיחות האחרונות שלך:",
            "missed": "השיחות שלא נענו:",
            "incoming": "מי התקשר אליך לאחרונה:",
            "outgoing": "למי התקשרת לאחרונה:",
        }[kind]
    return {
        "recent": "Your recent calls:",
        "missed": "Your missed calls:",
        "incoming": "Recent calls to you:",
        "outgoing": "Your recent outgoing calls:",
    }[kind]


def _empty_text(kind: str, hebrew: bool) -> str:
    if hebrew:
        return {
            "recent": "לא מצאתי שיחות אחרונות ביומן השיחות של הטלפון.",
            "missed": "לא מצאתי שיחות שלא נענו ביומן השיחות של הטלפון.",
            "incoming": "לא מצאתי שיחות נכנסות אחרונות ביומן השיחות של הטלפון.",
            "outgoing": "לא מצאתי שיחות יוצאות אחרונות ביומן השיחות של הטלפון.",
        }[kind]
    return {
        "recent": "I couldn't find recent calls in the phone call log.",
        "missed": "I couldn't find missed calls in the phone call log.",
        "incoming": "I couldn't find recent incoming calls in the phone call log.",
        "outgoing": "I couldn't find recent outgoing calls in the phone call log.",
    }[kind]


async def try_handle_call_history(
    text: str,
    source_device: str,
) -> dict[str, Any] | None:
    kind = _classify_history_intent(text)
    if kind is None:
        return None

    hebrew = bool(_HEBREW_RE.search(text or ""))
    source = (source_device or "").strip()
    target_device = source if source.startswith("uri-s25") else PHONE_DEVICE_ID

    if not device_manager.is_connected(target_device):
        msg = (
            "הטלפון לא מחובר כרגע ל-JARVIS, ולכן אני לא יכול לקרוא את יומן השיחות."
            if hebrew
            else "The phone is not connected to JARVIS, so I can't read the call log right now."
        )
        return {
            "ok": False,
            "text": msg,
            "route": "phone-call-history",
            "source_device": source_device,
            "target_device": target_device,
        }

    try:
        result = await device_manager.request(
            device_id=target_device,
            job_type="phone.call_history",
            payload={"limit": 40},
            timeout=15.0,
        )
    except Exception as exc:
        msg = (
            f"לא הצלחתי לקרוא את יומן השיחות מהטלפון: {exc}"
            if hebrew
            else f"I couldn't read the phone call log: {exc}"
        )
        return {
            "ok": False,
            "text": msg,
            "route": "phone-call-history",
            "source_device": source_device,
            "target_device": target_device,
        }

    if not isinstance(result, dict):
        result = {}

    if result.get("ok") is False:
        error = str(result.get("error") or "").strip()
        msg = (
            f"הטלפון לא הצליח לקרוא את יומן השיחות{': ' + error if error else ''}."
            if hebrew
            else f"The phone couldn't read the call log{': ' + error if error else ''}."
        )
        return {
            "ok": False,
            "text": msg,
            "route": "phone-call-history",
            "source_device": source_device,
            "target_device": target_device,
        }

    calls = [row for row in _extract_calls(result) if _matches(kind, str(row.get("type") or ""))]
    calls = calls[:10]

    if not calls:
        return {
            "ok": True,
            "text": _empty_text(kind, hebrew),
            "route": "phone-call-history",
            "source_device": source_device,
            "target_device": target_device,
            "query_kind": kind,
            "calls": [],
        }

    lines = [_title(kind, hebrew)]
    for idx, row in enumerate(calls, 1):
        identity = _display_identity(row, hebrew)
        label = _type_label(str(row.get("type") or ""), hebrew)
        when = _format_when(row.get("date_ms"), hebrew)
        duration = _format_duration(row.get("duration_seconds"), hebrew)

        details = [label]
        if when:
            details.append(when)
        if duration:
            details.append(duration)

        lines.append(f"{idx}. {identity} — " + " · ".join(details))

    return {
        "ok": True,
        "text": "\n".join(lines),
        "route": "phone-call-history",
        "provider": "android-call-log",
        "source_device": source_device,
        "target_device": target_device,
        "query_kind": kind,
        "calls": calls,
    }
