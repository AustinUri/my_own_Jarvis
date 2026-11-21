"""Rank measured homepage observations; no browsing, client contact or personal memory."""
from __future__ import annotations

import json
import time
from urllib.parse import urlsplit

from agent.provider import OpenAICompatibleProvider
from core.gaming_mode import require_local_ai_available
from services import local_ai_runtime as runtime

# One small catalogue of evidence-backed, review-only service suggestions.
ACTIONS = {
    "mobile": "בדיקת גלישה אופקית ותיקון התאמת האתר למסכים קטנים.",
    "metadata": "כתיבת תיאור עמוד רלוונטי ובדיקת מטא-נתונים.",
    "heading": "בדיקת היררכיית הכותרות והוספת כותרת ראשית מתאימה.",
    "alt": "סקירת התמונות והוספת alt מתאים לפי תפקיד התמונה.",
    "phone": "בדיקת נראות פרטי הקשר והוספת קישור לחיוג אם מתאים.",
    "whatsapp": "לברר עם העסק אם קישור WhatsApp ללקוחות מתאים ואם כבר קיים.",
    "booking": "לברר עם העסק את צורכי התורים והמערכת הקיימת לפני הצעת פתרון.",
    "https": "בדיקת מעבר ל-HTTPS.",
}


# Conservative fallback: observed technical issues before unconfirmed sales opportunities.
RULE_PRIORITY = ("https", "mobile", "phone", "heading", "alt", "metadata", "whatsapp", "booking")


def findings(audit: dict) -> dict:
    """Translate actual observations into a small typed input, not raw page text."""
    if audit.get("status") != "read" or audit.get("same_host") is not True or audit.get("inspection_error"):
        return {}
    p = audit.get("page_checks")
    if not isinstance(p, dict) or not p:
        return {}
    out = {}
    width, document = p.get("viewport_width"), p.get("document_width")
    if type(width) is int and type(document) is int and 0 < width < document - 4:
        out["mobile"] = {"viewport_width": width, "document_width": document}
    if p.get("meta_description") is False:
        out["metadata"] = {"meta_description": False}
    if type(p.get("h1_count")) is int and p["h1_count"] == 0:
        out["heading"] = {"h1_count": 0}
    if type(p.get("images_missing_alt")) is int and p["images_missing_alt"] > 0:
        out["alt"] = {"images_missing_alt": p["images_missing_alt"]}
    if type(p.get("phone_links")) is int and p["phone_links"] == 0:
        out["phone"] = {"homepage_phone_links": 0}
    if audit.get("links_truncated") is False:
        for key in ("whatsapp", "booking"):
            if audit.get("digital_presence", {}).get(key, {}).get("status") == "not_found_in_checked_links":
                out[key] = {"homepage_link": "not_found_in_checked_links"}
    if audit.get("https") is False:
        out["https"] = {"https": False}
    return out


def rank_local(observations: dict, kind: str) -> list[str]:
    # Reuse the configured local runtime/provider, without starting servers,
    # loading models, calling Oracle, attaching tools or trying paid fallbacks.
    base = urlsplit(runtime.BASE_URL)
    if (base.scheme not in ("http", "https") or base.hostname not in ("localhost", "127.0.0.1", "::1")
            or base.username or base.password or base.query or base.fragment or base.path not in ("", "/v1")):
        raise ValueError("Opportunity analysis requires a local LM Studio endpoint")
    require_local_ai_available()
    model = runtime.MODEL_KEYS[kind]
    if model not in runtime.loaded_models():
        raise RuntimeError("Load the selected model in LM Studio before analysis")
    provider = OpenAICompatibleProvider(base_url=runtime.BASE_URL.removesuffix("/v1") + "/v1",
                                         model=model, timeout=30 if kind == "qwen" else 90)
    count = min(3, len(observations))
    instruction = ("Rank observed homepage improvement opportunities for a small business. "
                   "Choose only supplied IDs. Missing links mean verify with the owner, not absence. "
                   f'Return only JSON {{"priority_order":["id",...]}} containing exactly {count} distinct IDs in priority order.')
    data = json.dumps(observations, ensure_ascii=False)
    if kind == "qwen":
        # Native endpoint verified with reasoning disabled; validate its small answer below.
        message = provider.chat_without_reasoning(instruction + "\nObservations: " + data, max_tokens=256)
    else:
        response_format = {"type": "json_schema", "json_schema": {
            "name": "opportunity_priority",
            "schema": {"type": "object", "properties": {"priority_order": {
                "type": "array", "items": {"type": "string", "enum": list(observations)},
                "minItems": count, "maxItems": count}},
                "required": ["priority_order"], "additionalProperties": False},
        }}
        message = provider.chat([
            {"role": "system", "content": instruction},
            {"role": "user", "content": data},
        ], temperature=0.1, max_tokens=2048, use_oracle_memory=False, strict_model=True,
           response_format=response_format)
    text = message.get("content")
    if not isinstance(text, str) or len(text) > 4000:
        raise ValueError("Missing or oversized model answer")
    if not text.strip():
        reasoning = message.get("reasoning_content")
        raise ValueError("Empty model content; separate reasoning present: " + str(bool(reasoning)))
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid model JSON at character {exc.pos}; content length={len(text)}") from exc
    if not isinstance(parsed, dict) or set(parsed) != {"priority_order"}:
        raise ValueError("Unexpected model answer format")
    return parsed["priority_order"]


def analyze(audit: dict, *, model_kind: str = "qwen", ranker=rank_local) -> dict:
    observed = findings(audit)
    result = {"status": "no_measured_findings", "model_requested": model_kind,
              "requires_human_review": True, "lead_score": None,
              "measured_findings": observed, "recommended_actions": []}
    if not observed:
        if audit.get("status") != "read" or audit.get("same_host") is not True or not audit.get("page_checks") or audit.get("inspection_error"):
            result["status"] = "audit_incomplete"
        return result
    started = time.monotonic()
    try:
        order = ranker(observed, model_kind)
        if (not isinstance(order, list) or len(order) != min(3, len(observed))
                or any(not isinstance(key, str) or key not in observed for key in order)
                or len(set(order)) != len(order)):
            raise ValueError("Model returned invalid or unsupported finding IDs")
    except Exception as exc:
        # No retries, new model or paid fallback. Rules produce review-only suggestions.
        order = [key for key in RULE_PRIORITY if key in observed][:3]
        result.update(status="ranked_rules", analysis_source="rules", model_status="failed",
                      model_error=str(exc)[:240])
    else:
        result.update(status="ranked", analysis_source="local_model", model_status="ok")
    result.update(elapsed_seconds=round(time.monotonic() - started, 2),
                  recommended_actions=[{"id": key, "evidence": observed[key], "suggestion_he": ACTIONS[key]} for key in order])
    return result
