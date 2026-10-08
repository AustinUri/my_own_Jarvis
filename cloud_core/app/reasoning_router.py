from __future__ import annotations

import os

from .device_bus import device_manager
from .reasoning import (
    DEFAULT_SYSTEM_PROMPT,
    cloud_reasoning_chat,
)


WINDOWS_DEVICE_ID = os.getenv(
    "JARVIS_WINDOWS_DEVICE_ID",
    "uri-windows",
)


class ReasoningRouteError(RuntimeError):
    pass


async def route_reasoning(
    text: str,
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 500,
    deep: bool = False,
    route: str = "auto",
) -> dict:
    route = (route or "auto").strip().lower()

    if route not in {"auto", "oracle", "windows"}:
        raise ReasoningRouteError(
            f"Unsupported reasoning route: {route}"
        )

    windows_error: str | None = None

    # Normal lightweight work stays on the always-on Oracle brain.
    # Deep work prefers Windows Qwen when Windows is available.
    should_try_windows = (
        route == "windows"
        or (
            route == "auto"
            and deep
            and device_manager.is_connected(WINDOWS_DEVICE_ID)
        )
    )

    if should_try_windows:
        if not device_manager.is_connected(WINDOWS_DEVICE_ID):
            windows_error = "Windows reasoning worker is offline"
        else:
            try:
                result = await device_manager.request(
                    WINDOWS_DEVICE_ID,
                    "reasoning",
                    {
                        "text": text,
                        "system": system_prompt or DEFAULT_SYSTEM_PROMPT,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    timeout=240.0,
                )

                if result.get("ok") and str(result.get("text") or "").strip():
                    return {
                        "ok": True,
                        "provider": "windows-qwen",
                        "model": result.get("model"),
                        "text": str(result["text"]).strip(),
                        "route": "windows",
                        "job_id": result.get("job_id"),
                    }

                windows_error = str(
                    result.get("error")
                    or "Windows reasoning worker returned no answer"
                )

            except Exception as exc:
                windows_error = str(exc)

        if route == "windows":
            raise ReasoningRouteError(
                windows_error or "Windows reasoning failed"
            )

    result = await cloud_reasoning_chat(
        text=text,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        deep=deep,
    )

    result["route"] = "oracle"

    if windows_error:
        result["fallback_reason"] = windows_error

    return result
