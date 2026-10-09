from __future__ import annotations

from typing import Any, Callable

from cloud_client.api import (
    CloudApiClient,
    DEFAULT_CLOUD_BASE_URL,
    DEFAULT_PHONE_DEVICE_ID,
)


class CloudPhoneHub:
    """Windows-side phone adapter backed only by the Oracle Device Bus.

    It deliberately keeps the small ``request(...)`` surface used by the existing
    JARVIS tools so V29 phone capabilities can migrate without keeping the old
    legacy PC-local transport alive.
    """

    _ALIASES = {
        "calendar_upcoming": "phone.calendar_upcoming",
        "calendar_list": "phone.calendar_upcoming",
        "phone.calendar_upcoming": "phone.calendar_upcoming",
        "contacts_search": "phone.contacts_search",
        "contact_search": "phone.contacts_search",
        "contact_find": "phone.contacts_search",
        "phone.contacts_search": "phone.contacts_search",
        "call_log_list": "phone.call_history",
        "call_log": "phone.call_history",
        "call_history": "phone.call_history",
        "phone.call_history": "phone.call_history",
        "call": "phone.call",
        "call_contact": "phone.call",
        "dial_contact": "phone.call",
        "call_number": "phone.call",
        "phone.call": "phone.call",
        "whatsapp": "phone.whatsapp_compose",
        "whatsapp_compose": "phone.whatsapp_compose",
        "whatsapp_message": "phone.whatsapp_compose",
        "whatsapp_send": "phone.whatsapp_compose",
        "phone.whatsapp_compose": "phone.whatsapp_compose",
        "capabilities": "phone.capabilities",
        "phone.capabilities": "phone.capabilities",
    }

    def __init__(
        self,
        config,
        log: Callable[[str], None] | None = None,
        status_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.config = config
        self.log = log or (lambda _m: None)
        self.status_callback = status_callback or (lambda _s: None)
        self.device_id = str(
            getattr(config, "cloud_phone_device_id", DEFAULT_PHONE_DEVICE_ID)
            or DEFAULT_PHONE_DEVICE_ID
        )
        self.api = CloudApiClient(
            base_url=str(
                getattr(config, "cloud_base_url", DEFAULT_CLOUD_BASE_URL)
                or DEFAULT_CLOUD_BASE_URL
            ),
            timeout=float(getattr(config, "cloud_request_timeout_seconds", 10.0)),
        )

    def begin_pairing(self) -> dict[str, Any]:
        result = self.api.create_pairing_code()
        seconds = int(result.get("expires_in_seconds") or 600)
        payload = {
            "code": str(result.get("code") or ""),
            "minutes": max(1, round(seconds / 60)),
            "expires_in_seconds": seconds,
            "server_url": self.api.base_url,
            "transport": "Oracle Device Bus",
        }
        self.status_callback(self.status())
        return payload

    def diagnostics(self) -> dict[str, Any]:
        status = self.status()
        return {
            "cloud_ok": status.get("cloud_online", False),
            "device_connected": status.get("connected", False),
            "device_id": self.device_id,
            "server_url": self.api.base_url,
            "transport": "Oracle Device Bus (WSS)",
            "error": status.get("error", ""),
        }

    def request(
        self,
        command: str,
        args: dict[str, Any] | None = None,
        timeout: float | None = None,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        job_type = self._ALIASES.get(str(command or "").strip())
        if not job_type:
            raise RuntimeError(
                f"Phone command '{command}' is not available on the V30 Device Bus"
            )

        wait = float(
            timeout
            if timeout is not None
            else getattr(self.config, "phone_command_timeout_seconds", 30.0)
        )

        raw = self.api.run_device_job(
            device_id or self.device_id,
            job_type,
            args or {},
            timeout=wait,
        )

        if raw.get("ok") is False:
            raise RuntimeError(str(raw.get("error") or "Phone command failed"))

        result = raw.get("result")
        if isinstance(result, dict):
            return result

        return raw

    def status(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "enabled": True,
            "paired": False,
            "connected": False,
            "cloud_online": False,
            "devices": [],
            "server_url": self.api.base_url,
            "transport": "Oracle Device Bus (WSS)",
            "security": "TLS + per-device cloud token",
        }

        try:
            health = self.api.health()
            out["cloud_online"] = bool(health.get("ok"))
        except Exception as exc:
            out["error"] = str(exc)
            return out

        try:
            paired_raw = self.api.list_paired_devices()
            paired_rows = paired_raw.get("devices") or []
            paired = next(
                (
                    row
                    for row in paired_rows
                    if str(row.get("device_id") or "") == self.device_id
                ),
                None,
            )

            connected_raw = self.api.list_devices()
            connected_rows = connected_raw.get("devices") or []
            connected = next(
                (
                    row
                    for row in connected_rows
                    if str(row.get("device_id") or "") == self.device_id
                ),
                None,
            )

            out["paired"] = paired is not None
            out["connected"] = connected is not None

            if paired or connected:
                row = dict(paired or {})
                row.update(connected or {})
                row.setdefault("device_id", self.device_id)
                row.setdefault("name", row.get("device_name") or "Samsung S25+")
                row["connected"] = connected is not None
                out["devices"] = [row]

        except Exception as exc:
            out["error"] = str(exc)

        return out
