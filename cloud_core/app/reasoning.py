from __future__ import annotations

import asyncio
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REASONING_BASE_URL = os.getenv(
    "JARVIS_REASONING_URL",
    "http://127.0.0.1:8770",
).rstrip("/")

REASONING_MODEL = os.getenv(
    "JARVIS_REASONING_MODEL",
    "Qwen/Qwen3-8B-GGUF:Q4_K_M",
)

DEFAULT_SYSTEM_PROMPT = """
You are JARVIS, an always-on autonomous assistant and business reasoning system.

Your job is to:
- reason carefully before making recommendations
- distinguish facts from assumptions
- protect profit and reduce unnecessary risk
- consider opportunity cost and uncertainty
- recommend escalation when a decision exceeds your authority
- never claim an external action was completed unless a tool actually completed it
- give a clear practical answer

When numbers matter, use values supplied by verified tools or deterministic
business calculations rather than inventing figures.
""".strip()


class ReasoningError(RuntimeError):
    pass


def _request_json(
    path: str,
    payload: dict | None = None,
    timeout: float = 300.0,
) -> dict:
    url = f"{REASONING_BASE_URL}{path}"

    data = None
    method = "GET"

    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
        headers["Content-Type"] = "application/json"

    req = Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")

    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
        except Exception:
            detail = ""

        raise ReasoningError(
            f"Reasoning engine returned HTTP {exc.code}: {detail}"
        ) from exc

    except (URLError, TimeoutError, OSError) as exc:
        raise ReasoningError(
            f"Reasoning engine is unavailable: {exc}"
        ) from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReasoningError(
            "Reasoning engine returned invalid JSON"
        ) from exc

    if not isinstance(result, dict):
        raise ReasoningError(
            "Reasoning engine returned an unexpected response"
        )

    return result


async def cloud_reasoning_health() -> dict:
    result = await asyncio.to_thread(
        _request_json,
        "/health",
        None,
        10.0,
    )

    if result.get("status") != "ok":
        raise ReasoningError(
            f"Unexpected reasoning health response: {result}"
        )

    return result


async def cloud_reasoning_chat(
    text: str,
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 500,
    deep: bool = False,
) -> dict:
    user_text = text.strip()

    if not user_text:
        raise ReasoningError("No reasoning request was supplied")

    # Normal Oracle jobs should produce a concise final answer instead of
    # spending the entire token budget exposing the model's internal thinking.
    # Deep reasoning can be enabled selectively by the future router.
    if not deep and "/no_think" not in user_text.lower():
        user_text = f"{user_text}\n/no_think"

    payload = {
        "model": REASONING_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt or DEFAULT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    result = await asyncio.to_thread(
        _request_json,
        "/v1/chat/completions",
        payload,
        420.0,
    )

    choices = result.get("choices")

    if not isinstance(choices, list) or not choices:
        raise ReasoningError(
            "Reasoning engine returned no choices"
        )

    choice = choices[0]
    message = choice.get("message") or {}
    answer = str(message.get("content") or "").strip()

    if not answer:
        raise ReasoningError(
            "Reasoning engine completed without a final answer"
        )

    return {
        "ok": True,
        "provider": "oracle-qwen",
        "model": result.get("model", REASONING_MODEL),
        "text": answer,
        "finish_reason": choice.get("finish_reason"),
        "usage": result.get("usage", {}),
    }
