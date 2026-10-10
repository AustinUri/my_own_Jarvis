from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import urllib.parse
import urllib.request


ABSTRACT_ENDPOINT = "https://phonevalidation.abstractapi.com/v1/"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _default_db_path() -> Path:
    override = os.getenv("JARVIS_CALLER_CACHE_DB", "").strip()
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return root / "Jarvis" / "caller_intelligence.sqlite3"

    return Path.home() / ".local" / "share" / "jarvis" / "caller_intelligence.sqlite3"


def normalize_phone_number(
    number: str,
    *,
    default_country_dial: str | None = None,
) -> str:
    raw = str(number or "").strip()
    if not raw:
        return ""

    lowered = raw.lower()
    if lowered in {"unknown", "private", "hidden", "anonymous", "restricted", "null"}:
        return ""

    compact = re.sub(r"[^\d+]", "", raw)

    if compact.startswith("00"):
        compact = "+" + compact[2:]

    if compact.startswith("+"):
        digits = re.sub(r"\D", "", compact[1:])
        return f"+{digits}" if 7 <= len(digits) <= 15 else ""

    digits = re.sub(r"\D", "", compact)
    if not digits:
        return ""

    country = re.sub(
        r"\D",
        "",
        str(default_country_dial or os.getenv("JARVIS_DEFAULT_COUNTRY_DIAL", "972")),
    )

    if country and digits.startswith(country):
        e164_digits = digits
    elif country and digits.startswith("0"):
        e164_digits = country + digits[1:]
    elif country and len(digits) <= 10:
        e164_digits = country + digits
    else:
        e164_digits = digits

    return f"+{e164_digits}" if 7 <= len(e164_digits) <= 15 else ""


def _nested(data: dict, *path: str):
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _first_text(data: dict, candidates: tuple[tuple[str, ...], ...]) -> str:
    for path in candidates:
        value = _nested(data, *path)
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() not in {"none", "null", "unknown", "n/a"}:
            return text
    return ""


def _first_bool(data: dict, candidates: tuple[tuple[str, ...], ...]) -> bool:
    for path in candidates:
        value = _nested(data, *path)
        if isinstance(value, bool):
            if value:
                return True
        elif isinstance(value, (int, float)):
            if value != 0:
                return True
        elif isinstance(value, str) and value.strip().lower() in {
            "true", "1", "yes", "y", "fraud", "scam", "spam", "abuse"
        }:
            return True
    return False


def _risk_score(data: dict) -> float | None:
    candidates = (
        ("risk_score",),
        ("risk", "score"),
        ("phone_risk", "score"),
        ("fraud", "score"),
    )
    for path in candidates:
        value = _nested(data, *path)
        if value is None:
            continue
        try:
            score = float(value)
        except (TypeError, ValueError):
            continue

        if score > 1.0 and score <= 100.0:
            score /= 100.0
        if 0.0 <= score <= 1.0:
            return score
    return None


@dataclass(frozen=True)
class CallerIntelResult:
    phone: str
    name: str = ""
    category: str = "unknown"
    confidence: float = 0.0
    fraud: bool = False
    spam: bool = False
    suspicious: bool = False
    risk_score: float | None = None
    carrier: str = ""
    line_type: str = ""
    location: str = ""
    provider: str = ""
    source: str = ""
    recommendation: str = "inform"

    def to_dict(self) -> dict:
        return asdict(self)


def classify_abstract_payload(phone: str, payload: dict) -> CallerIntelResult:
    if not isinstance(payload, dict):
        payload = {}

    name = _first_text(
        payload,
        (
            ("phone_registration", "name"),
            ("registration", "name"),
            ("registered_owner",),
            ("owner_name",),
            ("name",),
        ),
    )

    carrier = _first_text(
        payload,
        (
            ("carrier", "name"),
            ("carrier",),
        ),
    )
    line_type = _first_text(
        payload,
        (
            ("line_type",),
            ("type",),
            ("phone_type",),
        ),
    )
    location = _first_text(
        payload,
        (
            ("registered_location",),
            ("location",),
            ("country", "name"),
            ("country_name",),
        ),
    )

    explicit_fraud = _first_bool(
        payload,
        (
            ("is_fraud",),
            ("fraud",),
            ("is_scam",),
            ("scam",),
            ("risk", "is_fraud"),
            ("risk", "is_scam"),
        ),
    )
    explicit_spam = _first_bool(
        payload,
        (
            ("is_spam",),
            ("spam",),
            ("is_telemarketing",),
            ("telemarketing",),
            ("risk", "is_spam"),
        ),
    )
    abuse = _first_bool(
        payload,
        (
            ("is_abuse_detected",),
            ("abuse",),
            ("risk", "is_abuse_detected"),
            ("phone_risk", "is_abuse_detected"),
        ),
    )
    score = _risk_score(payload)
    high_risk = score is not None and score >= 0.85

    fraud = explicit_fraud
    spam = explicit_spam
    suspicious = bool(abuse or high_risk) and not fraud

    if fraud:
        category = "fraud"
        recommendation = "warn_strong"
        confidence = 0.95
    elif spam:
        category = "spam"
        recommendation = "inform"
        confidence = 0.90
    elif suspicious:
        category = "suspicious"
        recommendation = "warn"
        confidence = 0.80 if high_risk else 0.70
    elif name:
        category = "identified"
        recommendation = "normal"
        confidence = 0.75
    else:
        category = "unknown"
        recommendation = "inform"
        confidence = 0.25 if payload.get("valid") else 0.0

    return CallerIntelResult(
        phone=phone,
        name=name,
        category=category,
        confidence=confidence,
        fraud=fraud,
        spam=spam,
        suspicious=suspicious,
        risk_score=score,
        carrier=carrier,
        line_type=line_type,
        location=location,
        provider="abstract",
        source="provider",
        recommendation=recommendation,
    )


class CallerCache:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or _default_db_path()).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    def _ensure_schema(self) -> None:
        with closing(self._connect()) as db, db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS caller_lookup_cache (
                    phone TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_caller_lookup_expiry "
                "ON caller_lookup_cache(expires_at)"
            )

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS learned_callers (
                    phone TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL DEFAULT '',
                    label TEXT NOT NULL DEFAULT 'known',
                    notes TEXT NOT NULL DEFAULT '',
                    times_seen INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_seen_at TEXT
                )
                """
            )

    def get(self, phone: str) -> CallerIntelResult | None:
        now = _iso(_utcnow())
        with closing(self._connect()) as db, db:
            row = db.execute(
                """
                SELECT result_json
                FROM caller_lookup_cache
                WHERE phone = ? AND expires_at > ?
                """,
                (phone, now),
            ).fetchone()

        if row is None:
            return None

        try:
            data = json.loads(row["result_json"])
            data["source"] = "cache"
            return CallerIntelResult(**data)
        except Exception:
            return None

    def put(self, result: CallerIntelResult, *, ttl_days: int) -> None:
        now = _utcnow()
        expires = now + timedelta(days=max(1, int(ttl_days)))
        payload = result.to_dict()

        with closing(self._connect()) as db, db:
            db.execute(
                """
                INSERT INTO caller_lookup_cache(
                    phone, result_json, provider, updated_at, expires_at
                )
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(phone) DO UPDATE SET
                    result_json = excluded.result_json,
                    provider = excluded.provider,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at
                """,
                (
                    result.phone,
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    result.provider or "unknown",
                    _iso(now),
                    _iso(expires),
                ),
            )


    def remember_caller(
        self,
        number: str,
        *,
        name: str = "",
        label: str = "known",
        notes: str = "",
    ) -> CallerIntelResult:
        phone = normalize_phone_number(number)
        if not phone:
            raise ValueError("A valid phone number is required")

        safe_label = str(label or "known").strip().lower()
        if safe_label not in {
            "known",
            "trusted",
            "spam",
            "fraud",
            "suspicious",
            "unknown",
        }:
            raise ValueError(
                "label must be one of: known, trusted, spam, fraud, suspicious, unknown"
            )

        now = _iso(_utcnow())
        display_name = str(name or "").strip()
        safe_notes = str(notes or "").strip()

        with closing(self._connect()) as db, db:
            existing = db.execute(
                "SELECT created_at, times_seen FROM learned_callers WHERE phone = ?",
                (phone,),
            ).fetchone()

            created_at = existing["created_at"] if existing else now
            times_seen = int(existing["times_seen"]) if existing else 0

            db.execute(
                """
                INSERT INTO learned_callers(
                    phone, display_name, label, notes,
                    times_seen, created_at, updated_at, last_seen_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(phone) DO UPDATE SET
                    display_name = excluded.display_name,
                    label = excluded.label,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    phone,
                    display_name,
                    safe_label,
                    safe_notes,
                    times_seen,
                    created_at,
                    now,
                ),
            )

        result = self.get_learned(phone)
        if result is None:
            raise RuntimeError("Learned caller could not be read back")
        return result

    def get_learned(self, number: str) -> CallerIntelResult | None:
        phone = normalize_phone_number(number)
        if not phone:
            return None

        with closing(self._connect()) as db, db:
            row = db.execute(
                """
                SELECT phone, display_name, label
                FROM learned_callers
                WHERE phone = ?
                """,
                (phone,),
            ).fetchone()

        if row is None:
            return None

        label = str(row["label"] or "known").strip().lower()
        name = str(row["display_name"] or "").strip()

        fraud = label == "fraud"
        spam = label == "spam"
        suspicious = label == "suspicious"

        if fraud:
            category = "fraud"
            recommendation = "warn_strong"
        elif spam:
            category = "spam"
            recommendation = "inform"
        elif suspicious:
            category = "suspicious"
            recommendation = "warn"
        elif label in {"known", "trusted"}:
            category = "identified" if name else "known"
            recommendation = "normal"
        else:
            category = "unknown"
            recommendation = "inform"

        return CallerIntelResult(
            phone=phone,
            name=name,
            category=category,
            confidence=1.0,
            fraud=fraud,
            spam=spam,
            suspicious=suspicious,
            provider="jarvis_local",
            source="user_confirmed",
            recommendation=recommendation,
        )

    def forget_caller(self, number: str) -> bool:
        phone = normalize_phone_number(number)
        if not phone:
            return False

        with closing(self._connect()) as db, db:
            cursor = db.execute(
                "DELETE FROM learned_callers WHERE phone = ?",
                (phone,),
            )

        return bool(cursor.rowcount)

    def record_seen(self, number: str) -> None:
        phone = normalize_phone_number(number)
        if not phone:
            return

        now = _iso(_utcnow())
        with closing(self._connect()) as db, db:
            db.execute(
                """
                UPDATE learned_callers
                SET times_seen = times_seen + 1,
                    last_seen_at = ?,
                    updated_at = ?
                WHERE phone = ?
                """,
                (now, now, phone),
            )



class CallerIntelligence:
    def __init__(
        self,
        *,
        cache: CallerCache | None = None,
        timeout_seconds: float = 1.25,
    ):
        self.cache = cache or CallerCache()
        self.timeout_seconds = max(0.5, float(timeout_seconds))

    def lookup(
        self,
        number: str,
        *,
        force_refresh: bool = False,
    ) -> CallerIntelResult:
        phone = normalize_phone_number(number)
        if not phone:
            return CallerIntelResult(
                phone="",
                category="unknown",
                source="local",
                recommendation="inform",
            )

        learned = self.cache.get_learned(phone)
        if learned is not None:
            self.cache.record_seen(phone)
            return learned

        if not force_refresh:
            cached = self.cache.get(phone)
            if cached is not None:
                return cached

        external_enabled = os.getenv(
            "JARVIS_CALLER_EXTERNAL_LOOKUP",
            "",
        ).strip().lower() in {"1", "true", "yes", "on"}

        if not external_enabled:
            return CallerIntelResult(
                phone=phone,
                category="unknown",
                source="local_only",
                recommendation="inform",
            )

        api_key = os.getenv("ABSTRACT_PHONE_API_KEY", "").strip()
        if not api_key:
            return CallerIntelResult(
                phone=phone,
                category="unknown",
                source="provider_unconfigured",
                recommendation="inform",
            )

        query = urllib.parse.urlencode({
            "api_key": api_key,
            "phone": phone,
        })
        request = urllib.request.Request(
            f"{ABSTRACT_ENDPOINT}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "JARVIS-Caller-Intelligence/1.0",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except Exception:
            return CallerIntelResult(
                phone=phone,
                category="unknown",
                source="provider_error",
                provider="abstract",
                recommendation="inform",
            )

        result = classify_abstract_payload(phone, payload)

        ttl_days = 30 if (
            result.name
            or result.fraud
            or result.spam
            or result.suspicious
        ) else 7
        self.cache.put(result, ttl_days=ttl_days)
        return result
