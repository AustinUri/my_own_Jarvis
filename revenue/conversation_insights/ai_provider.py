from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request


class SemanticAnalysisUnavailable(RuntimeError):
    pass


class SemanticProvider:
    """OpenAI-compatible provider. Defaults to the existing local JARVIS LM Studio."""

    def __init__(self):
        self.base_url = os.getenv("CONV_AI_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")
        self.model = os.getenv("CONV_AI_MODEL", "jarvis-qwen").strip()
        self.api_key = os.getenv("CONV_AI_API_KEY", "lm-studio").strip()
        self.timeout = int(os.getenv("CONV_AI_TIMEOUT", "180"))
        self.auto_start = os.getenv("CONV_AI_AUTO_START", "1").strip().lower() not in {"0", "false", "no"}

    def _request(self, path: str, payload: dict | None = None, timeout: int | None = None):
        url = self.base_url + path
        headers = {"Content-Type": "application/json", "User-Agent": "JARVIS-Conversation-Insights/0.6.1"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def models(self):
        try:
            return self._request("/models", timeout=4)
        except Exception:
            return None

    def _model_ids(self, body) -> list[str]:
        ids = []
        if isinstance(body, dict):
            for row in body.get("data") or body.get("models") or []:
                if isinstance(row, dict):
                    ids.append(str(row.get("id") or row.get("model") or row.get("name") or ""))
        return [x for x in ids if x]

    def ensure_ready(self):
        body = self.models()
        if body is not None and self.model in self._model_ids(body):
            return
        if not self.auto_start:
            raise SemanticAnalysisUnavailable(f"Semantic model '{self.model}' is not available at {self.base_url}.")

        lms = shutil.which("lms")
        if not lms:
            raise SemanticAnalysisUnavailable("LM Studio CLI (lms) was not found.")

        if body is None:
            try:
                subprocess.run([lms, "server", "start"], check=False, capture_output=True, text=True, timeout=30)
            except Exception:
                pass
            for _ in range(16):
                time.sleep(0.5)
                body = self.models()
                if body is not None:
                    break
        if body is None:
            raise SemanticAnalysisUnavailable("LM Studio server could not be reached.")

        if self.model not in self._model_ids(body):
            model_key = os.getenv("CONV_AI_LOCAL_MODEL_KEY", "qwen/qwen3.5-9b")
            context = os.getenv("CONV_AI_CONTEXT", "16384")
            try:
                subprocess.run(
                    [lms, "load", model_key, "--identifier", self.model, "--context-length", context],
                    check=False, capture_output=True, text=True, timeout=180,
                )
            except Exception:
                pass
            body = self.models() or {}
            if self.model not in self._model_ids(body):
                raise SemanticAnalysisUnavailable(f"LM Studio is online, but model '{self.model}' is not loaded.")

    @staticmethod
    def _strip_reasoning_and_fences(text: str) -> str:
        text = (text or "").strip().lstrip("\ufeff")
        # Qwen-family models can emit thinking blocks even when the requested answer is JSON.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.I | re.S).strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text).strip()
        return text

    @staticmethod
    def _balanced_json_object(text: str) -> str | None:
        """Extract the first balanced JSON object, respecting quoted braces."""
        start = text.find("{")
        if start < 0:
            return None
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        return None

    @classmethod
    def _extract_json(cls, text: str) -> dict:
        text = cls._strip_reasoning_and_fences(text)
        if not text:
            raise ValueError("Model returned an empty response.")
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        candidate = cls._balanced_json_object(text)
        if candidate:
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
        raise ValueError("Model did not return valid JSON.")

    @staticmethod
    def _structured_format(schema: dict | None, schema_name: str) -> dict:
        if schema:
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            }
        return {"type": "json_object"}

    def _raw_completion(
        self,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
        schema: dict | None,
        schema_name: str,
    ) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "response_format": self._structured_format(schema, schema_name),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        body = self._request("/chat/completions", payload)
        msg = body["choices"][0]["message"]
        # Normal OpenAI-compatible location. Some engines additionally expose reasoning_content.
        content = msg.get("content")
        if isinstance(content, list):
            content = "".join(str(x.get("text") or "") if isinstance(x, dict) else str(x) for x in content)
        return str(content or "")

    def json_completion(
        self,
        system: str,
        user: str,
        max_tokens: int = 1800,
        temperature: float = 0.18,
        schema: dict | None = None,
        schema_name: str = "semantic_output",
    ) -> dict:
        self.ensure_ready()
        first_text = ""
        try:
            first_text = self._raw_completion(system, user, max_tokens, temperature, schema, schema_name)
            return self._extract_json(first_text)
        except urllib.error.HTTPError as e:
            # If a model/backend rejects json_schema, retry with generic JSON-object mode.
            if e.code not in {400, 422}:
                raise SemanticAnalysisUnavailable(f"Semantic model request failed: HTTP {e.code}") from e
            try:
                payload = {
                    "model": self.model,
                    "temperature": 0.05,
                    "max_tokens": max_tokens,
                    "stream": False,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system + "\nReturn exactly one valid JSON object and nothing else."},
                        {"role": "user", "content": user},
                    ],
                }
                body = self._request("/chat/completions", payload)
                first_text = str(body["choices"][0]["message"].get("content") or "")
                return self._extract_json(first_text)
            except Exception as inner:
                raise SemanticAnalysisUnavailable(f"Structured JSON request failed: {inner}") from inner
        except ValueError:
            # One bounded repair request. Do not persist the raw model output anywhere.
            repair_system = (
                "You repair malformed model output into strict JSON. "
                "Return exactly one JSON object matching the requested schema. "
                "Do not explain, do not use markdown, do not add new facts."
            )
            repair_user = (
                "Original task schema/name: " + schema_name + "\n"
                + "Malformed output:\n" + first_text[:12000]
            )
            try:
                repaired = self._raw_completion(
                    repair_system,
                    repair_user,
                    max_tokens=max_tokens,
                    temperature=0.0,
                    schema=schema,
                    schema_name=schema_name + "_repair",
                )
                return self._extract_json(repaired)
            except Exception as e:
                raise SemanticAnalysisUnavailable(
                    "Semantic model answered, but structured JSON could not be recovered after one repair attempt."
                ) from e
        except SemanticAnalysisUnavailable:
            raise
        except Exception as e:
            raise SemanticAnalysisUnavailable(f"Semantic model request failed: {e}") from e
