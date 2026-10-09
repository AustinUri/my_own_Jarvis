from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_CLOUD_BASE_URL = "https://uri-jarvis.duckdns.org"
DEFAULT_WINDOWS_DEVICE_ID = "uri-windows"
DEFAULT_PHONE_DEVICE_ID = "uri-s25"


def default_token_file() -> Path:
    return (
        Path(os.environ.get("LOCALAPPDATA", Path.home()))
        / "Jarvis"
        / "cloud.token"
    )


def load_cloud_token(path: Path | None = None) -> str:
    token_path = path or default_token_file()

    if not token_path.exists():
        raise RuntimeError(f"Cloud token not found: {token_path}")

    token = token_path.read_text(encoding="utf-8").strip()

    if not token:
        raise RuntimeError("Cloud token file is empty")

    return token


class CloudApiClient:
    def __init__(
        self,
        base_url: str = DEFAULT_CLOUD_BASE_URL,
        token_file: Path | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = str(base_url or DEFAULT_CLOUD_BASE_URL).rstrip("/")
        self.token_file = token_file or default_token_file()
        self.timeout = max(1.0, float(timeout))

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        auth: bool = False,
        timeout: float | None = None,
    ) -> dict:
        data = None
        headers = {
            "Accept": "application/json",
            "User-Agent": "JarvisV30Windows/30",
        }

        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if auth:
            headers["Authorization"] = f"Bearer {load_cloud_token(self.token_file)}"

        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method.upper(),
        )

        try:
            with urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:1200]
            except Exception:
                detail = ""
            raise RuntimeError(
                f"JARVIS Cloud returned HTTP {exc.code}: {detail or exc.reason}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"JARVIS Cloud request failed: {exc}") from exc

        if not raw.strip():
            return {}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("JARVIS Cloud returned invalid JSON") from exc

        if not isinstance(parsed, dict):
            raise RuntimeError("JARVIS Cloud returned an unexpected response")

        return parsed

    def health(self) -> dict:
        return self._request("GET", "/api/v1/health")

    def list_devices(self) -> dict:
        return self._request("GET", "/api/v1/devices", auth=True)

    def list_paired_devices(self) -> dict:
        return self._request("GET", "/api/v1/pairing/devices", auth=True)

    def create_pairing_code(self) -> dict:
        return self._request("POST", "/api/v1/pairing/create", {}, auth=True)

    def run_device_job(
        self,
        device_id: str,
        job_type: str,
        payload: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        wait = max(1.0, min(120.0, float(timeout)))
        return self._request(
            "POST",
            f"/api/v1/devices/{device_id}/jobs",
            {
                "job_type": job_type,
                "payload": payload or {},
                "timeout_seconds": wait,
            },
            auth=True,
            timeout=wait + 5.0,
        )
