from __future__ import annotations

import os
import re
from typing import Any

from .device_bus import device_manager

PHONE_DEVICE_ID = os.getenv(
    "JARVIS_PHONE_DEVICE_ID",
    "uri-s25",
)

_ENGLISH_CALL_RE = re.compile(
    r"^\s*(?:(?:hey\s+)?jarvis[\s,:-]+)?"
    r"(?:please\s+)?(?:call|phone|dial)\s+(.+?)\s*[.!?]*$",
    re.IGNORECASE,
)

_HEBREW_CALL_RE = re.compile(
    r"^\s*(?:ג[׳']?ר(?:וו|ו)יס[\s,:-]+)?"
    r"(?:בבקשה\s+)?(?:תתקשר|התקשר|חייג)"
    r"(?:\s+אל\s+|\s+ל|\s+)(.+?)\s*[.!?]*$",
)

_ALIAS_GROUPS = (
    ("mom", "mother", "mum", "mummy", "אמא", "אימא"),
    ("dad", "father", "daddy", "אבא"),
)


def _clean_target(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "").strip())

    if value.casefold().startswith("my "):
        value = value[3:].strip()

    if value.endswith(" שלי"):
        value = value[:-4].strip()

    return value.strip(" \t\r\n,;:!?.")


def _extract_call_target(text: str) -> tuple[str, str] | None:
    raw = str(text or "").strip()
    if not raw:
        return None

    match = _ENGLISH_CALL_RE.match(raw)
    if match:
        target = _clean_target(match.group(1))
        return (target, "en") if target else None

    match = _HEBREW_CALL_RE.match(raw)
    if match:
        target = _clean_target(match.group(1))
        return (target, "he") if target else None

    return None


def _candidate_queries(target: str) -> list[str]:
    target = _clean_target(target)
    if not target:
        return []

    out = [target]
    folded = target.casefold()

    for group in _ALIAS_GROUPS:
        if folded not in {x.casefold() for x in group}:
            continue

        for item in group:
            if item.casefold() != folded and item not in out:
                out.append(item)

        break

    return out


def _contacts_from_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []

    contacts = result.get("contacts")

    if not isinstance(contacts, list):
        nested = result.get("result")
        if isinstance(nested, dict):
            contacts = nested.get("contacts")

    if not isinstance(contacts, list):
        return []

    return [row for row in contacts if isinstance(row, dict)]


def _usable_number(contact: dict[str, Any]) -> str:
    for key in ("raw_number", "canonical_number", "number"):
        value = str(contact.get(key) or "").strip()
        if value:
            return value
    return ""


def _norm_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _select_contact(
    contacts: list[dict[str, Any]],
    target: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:

    usable = [row for row in contacts if _usable_number(row)]
    if not usable:
        return None, []

    exact = [
        row
        for row in usable
        if _norm_name(row.get("name", "")) == _norm_name(target)
    ]

    pool = exact if exact else usable

    unique: dict[str, dict[str, Any]] = {}

    for row in pool:
        number = _usable_number(row)
        key = re.sub(r"\D+", "", number) or number

        if key not in unique:
            unique[key] = row
            continue

        try:
            new_type = int(row.get("type", -1))
            old_type = int(unique[key].get("type", -1))
        except Exception:
            new_type = old_type = -1

        # Android TYPE_MOBILE == 2.
        if new_type == 2 and old_type != 2:
            unique[key] = row

    choices = list(unique.values())

    if len(choices) == 1:
        return choices[0], choices

    mobile = []
    for row in choices:
        try:
            if int(row.get("type", -1)) == 2:
                mobile.append(row)
        except Exception:
            pass

    if exact and len(mobile) == 1:
        return mobile[0], choices

    return None, choices


def _choice_text(row: dict[str, Any]) -> str:
    name = str(row.get("name") or "Unknown").strip()
    number = str(
        row.get("number")
        or row.get("raw_number")
        or row.get("canonical_number")
        or ""
    ).strip()

    return f"{name} ({number})" if number else name


def _reply(text: str, ok: bool, state: str, **data: Any) -> dict[str, Any]:
    return {
        "ok": ok,
        "provider": "jarvis-action-router",
        "model": None,
        "route": "phone-action",
        "text": text,
        "action": {
            "type": "phone.call",
            "state": state,
            **data,
        },
    }


def _say(language: str, english: str, hebrew: str) -> str:
    return hebrew if language == "he" else english


async def try_handle_phone_action(
    *,
    text: str,
    source_device: str,
) -> dict[str, Any] | None:

    parsed = _extract_call_target(text)
    if parsed is None:
        return None

    target, language = parsed

    target_device = (
        source_device
        if str(source_device or "").startswith("uri-s25")
        else PHONE_DEVICE_ID
    )

    if not device_manager.is_connected(target_device):
        return _reply(
            _say(
                language,
                "Your phone is offline, so I did not place the call.",
                "הטלפון לא מחובר כרגע, לכן לא ביצעתי את השיחה.",
            ),
            False,
            "phone-offline",
            target=target,
            device_id=target_device,
        )

    contacts: list[dict[str, Any]] = []
    search_error = ""

    for query in _candidate_queries(target):
        try:
            result = await device_manager.request(
                device_id=target_device,
                job_type="phone.contacts_search",
                payload={"query": query},
                timeout=15.0,
            )
        except Exception as exc:
            search_error = str(exc)
            continue

        if not result.get("ok", False):
            search_error = str(result.get("error") or "contact search failed")
            continue

        contacts = _contacts_from_result(result)

        if contacts:
            target = query
            break

    if not contacts:
        detail = f" ({search_error})" if search_error else ""

        return _reply(
            _say(
                language,
                f"I couldn't find a phone contact matching {target}.{detail}",
                f"לא מצאתי איש קשר בטלפון שמתאים ל־{target}.{detail}",
            ),
            False,
            "contact-not-found",
            target=target,
        )

    selected, choices = _select_contact(contacts, target)

    if selected is None:
        visible = ", ".join(_choice_text(row) for row in choices[:5])

        return _reply(
            _say(
                language,
                f"I found more than one possible match for {target}: {visible}. Say the exact contact name.",
                f"מצאתי יותר מהתאמה אחת עבור {target}: {visible}. אמור את שם איש הקשר המדויק.",
            ),
            False,
            "ambiguous-contact",
            target=target,
            choices=choices[:5],
        )

    name = str(selected.get("name") or target).strip()
    number = _usable_number(selected)

    try:
        call_result = await device_manager.request(
            device_id=target_device,
            job_type="phone.call",
            payload={
                "number": number,
                "name": name,
            },
            timeout=15.0,
        )
    except Exception as exc:
        return _reply(
            _say(
                language,
                f"I found {name}, but the phone failed to start the call: {exc}",
                f"מצאתי את {name}, אבל הטלפון לא הצליח להתחיל את השיחה: {exc}",
            ),
            False,
            "call-failed",
            target=target,
            name=name,
        )

    if not call_result.get("ok", False):
        error = str(
            call_result.get("error")
            or call_result.get("message")
            or "unknown phone error"
        )

        return _reply(
            _say(
                language,
                f"I found {name}, but the phone did not place the call: {error}",
                f"מצאתי את {name}, אבל הטלפון לא ביצע את השיחה: {error}",
            ),
            False,
            "call-failed",
            target=target,
            name=name,
        )

    # Never report success before Android says ok=true.
    return _reply(
        _say(
            language,
            f"Calling {name}.",
            f"מתקשר אל {name}.",
        ),
        True,
        "started",
        target=target,
        name=name,
        number=str(call_result.get("number") or number),
        device_id=target_device,
    )
