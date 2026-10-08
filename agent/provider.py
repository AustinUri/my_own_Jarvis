from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class ProviderError(RuntimeError):
    pass


# Hard process-wide ceiling for expensive local generations. Even when future
# specialist agents fan out, v27 never allows more than two LM Studio chat
# requests to generate at the same time.
_LOCAL_LLM_SLOTS = threading.BoundedSemaphore(2)


@dataclass(slots=True)
class OpenAICompatibleProvider:
    base_url: str
    model: str
    api_key: str = "lm-studio"
    timeout: float = 60.0

    @property
    def label(self) -> str:
        return "LM Studio / OpenAI-compatible"

    def _endpoint(self, path: str) -> str:
        return self.base_url.rstrip("/") + "/" + path.lstrip("/")

    def list_models(self) -> list[str]:
        req = urllib.request.Request(self._endpoint("models"), headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=min(self.timeout, 8.0)) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ProviderError(f"AI server is not reachable at {self.base_url}: {exc}") from exc
        items = payload.get("data", []) if isinstance(payload, dict) else []
        return [str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")]

    def resolve_model(self) -> str:
        configured = (self.model or "").strip()
        models = self.list_models()
        if configured and configured.lower() != "auto":
            if configured in models or not models:
                return configured
            # A custom identifier can be loaded after Jarvis has already started.
            # Prefer an exact configured ID, but if it is absent and only one model is
            # served, use that one instead of failing pointlessly.
            if len(models) == 1:
                return models[0]
            raise ProviderError(
                f"Configured model '{configured}' is not loaded in LM Studio. Loaded models: {', '.join(models) or 'none'}."
            )
        if not models:
            raise ProviderError("LM Studio is reachable, but no model is loaded.")
        return models[0]

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.35,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        model = self.resolve_model()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": float(temperature),
            "stream": False,
        }

        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        req = urllib.request.Request(
            self._endpoint("chat/completions"),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        acquired = _LOCAL_LLM_SLOTS.acquire(timeout=max(5.0, min(float(self.timeout), 60.0)))
        if not acquired:
            raise ProviderError("Local AI concurrency guard is busy; try again in a moment.")
        try:
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    raw = json.loads(response.read().decode("utf-8"))
            finally:
                _LOCAL_LLM_SLOTS.release()
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:800]
            except Exception:
                pass
            raise ProviderError(f"AI server returned HTTP {exc.code}. {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise ProviderError(f"AI request failed: {exc}") from exc

        try:
            message = raw["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"AI server returned an unexpected response: {raw!r}") from exc
        if not isinstance(message, dict):
            raise ProviderError("AI server returned an invalid assistant message.")
        return message

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
