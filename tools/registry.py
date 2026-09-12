from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from core.config import AppConfig
from core.events import ToolAction
from tools.clock import tell_time
from tools.date_tools import tell_date
from tools.folders import open_folder
from tools.math_tools import calculate_expression
from tools.notes import create_note
from tools.open_app import open_app
from tools.search_files import search_files
from tools.system_tools import close_app, get_system_status, lock_computer
from tools.web_tools import WebAnswer, answer_web_question, open_website, search_web
from services.weather import WeatherService
from services.google_calendar import GoogleCalendarService
from services.f1_learning import F1LearningService
from services.daily_briefing import DailyBriefingService


class ToolRegistry:
    """The controlled capability boundary between the AI and the computer.

    The model never receives shell access. It can only request one of the
    explicitly described functions below, and policy code can still deny a
    request before execution.
    """

    def __init__(self, base_dir: Path, config: AppConfig):
        self.base_dir = base_dir
        self.config = config
        self._ui_event_sink: Callable[[str, dict[str, Any]], None] | None = None
        self._camera_frame_supplier: Callable[[], Any] | None = None
        self._vision_analyzer: Callable[[str, str], str] | None = None
        self._phone_hub: Any | None = None
        self.weather_service = WeatherService(config)
        self.google_calendar_service = GoogleCalendarService(config)
        self.calendar_service = self.google_calendar_service  # backward-compatible alias for UI code
        self.f1_learning_service = F1LearningService()
        self.daily_briefing_service = DailyBriefingService(config)
        self.daily_briefing_service.set_calendar_provider(self.calendar_status_data, self.list_calendar_events)

    def set_ui_event_sink(self, sink: Callable[[str, dict[str, Any]], None] | None) -> None:
        self._ui_event_sink = sink

    def set_camera_vision(
        self,
        frame_supplier: Callable[[], Any] | None,
        analyzer: Callable[[str, str], str] | None,
    ) -> None:
        self._camera_frame_supplier = frame_supplier
        self._vision_analyzer = analyzer

    def set_phone_hub(self, hub: Any | None) -> None:
        self._phone_hub = hub

    def phone_status_data(self) -> dict[str, Any]:
        if self._phone_hub is None:
            return {"enabled": False, "paired": False, "connected": False, "devices": [], "message": "Phone bridge is not running."}
        status = dict(self._phone_hub.status())
        status["message"] = "Native phone calendar available." if status.get("connected") else "Phone companion is not connected."
        return status

    def calendar_status_data(self) -> dict[str, Any]:
        phone = self.phone_status_data()
        google = self.google_calendar_service.status() if getattr(self.config, "google_calendar_fallback_enabled", True) else {"connected": False, "ready": False, "message": "Google fallback disabled."}
        if getattr(self.config, "prefer_phone_calendar", True) and phone.get("connected"):
            return {"connected": True, "source": "phone", "message": "Using native phone calendar.", "phone": phone, "google": google}
        if google.get("connected"):
            return {"connected": True, "source": "google", "message": "Using Google Calendar fallback.", "phone": phone, "google": google}
        return {"connected": False, "source": "none", "message": "Connect the phone companion or Google Calendar backup.", "phone": phone, "google": google}

    def list_calendar_events(self, days: int = 2) -> list[dict[str, Any]]:
        days = max(1, min(30, int(days)))
        phone = self.phone_status_data()
        if getattr(self.config, "prefer_phone_calendar", True) and phone.get("connected") and self._phone_hub is not None:
            payload = self._phone_hub.request("calendar_list", {"days": days})
            events = payload.get("events") or payload.get("result") or []
            if isinstance(events, list):
                out = []
                for item in events:
                    if not isinstance(item, dict):
                        continue
                    row = dict(item)
                    row.setdefault("source", "phone")
                    out.append(row)
                return out
        if getattr(self.config, "google_calendar_fallback_enabled", True):
            return self.google_calendar_service.list_events(days=days)
        raise RuntimeError("No calendar source is connected.")

    def definitions(self) -> list[dict[str, Any]]:
        return [
            self._tool("open_app", "Open an installed desktop application. Use only when the user explicitly asks to open/run/launch an app.", {"app": self._string("Application name such as chrome, spotify, notepad, calculator, explorer, edge, discord, vscode.")}, ["app"]),
            self._tool("close_app", "Close a desktop application. Use only when explicitly requested.", {"app": self._string("Application name to close.")}, ["app"]),
            self._tool("open_website", "Open a website in the default browser. The site may be a known name, a domain such as chess.com, or an http/https URL. Use only when explicitly asked to open/show/navigate to it.", {"site": self._string("Website name, domain, or URL.")}, ["site"]),
            self._tool("search_web", "Open a browser search page for a query. This changes the user's UI, so use only when the user explicitly asks to search/open search results.", {"query": self._string("Search query.")}, ["query"]),
            self._tool("answer_web_question", "Research a public factual/current question using Jarvis's local SearXNG/Wikipedia web pipeline. It supports deep multi-source list/history/range research (for example all finals since a given year), not just single facts. Use this for facts that may require the internet. Never use it for the user's private schedule, inbox, files, reminders, or personal data.", {"query": self._string("The complete factual/research question, preserving requested years, ranges, and qualifiers.")}, ["query"]),
            self._tool("get_weather", "Get current weather and a short forecast for the user's configured location or another named location. Prefer this over generic web search for weather.", {"location": self._string("Optional city/location name. Leave empty to use the configured home weather location.")}, []),
            self._tool("calendar_status", "Check the preferred calendar source. JARVIS uses the native phone calendar when the trusted phone companion is connected, with Google Calendar as an optional backup.", {}, []),
            self._tool("calendar_connect", "Connect the optional Google Calendar backup. Native phone calendar does not require Google OAuth. Use only when the user explicitly asks to connect Google Calendar.", {}, []),
            self._tool("calendar_list_events", "Read upcoming events from the preferred personal calendar source: native phone calendar first, Google Calendar backup second. Never substitute a public web search for private calendar data.", {"days": {"type":"integer","description":"Number of days ahead to read, normally 1-7."}}, []),
            self._tool("calendar_create_event", "Create an event using Google Calendar backup for now. Native phone-calendar writing is intentionally deferred until the user explicitly grants write permission. Only use on an explicit request to create/add/schedule an event.", {"summary": self._string("Event title."), "start_iso": self._string("Start date/time as ISO 8601 with timezone when possible."), "end_iso": self._string("End date/time as ISO 8601 with timezone when possible."), "location": self._string("Optional event location."), "description": self._string("Optional description.")}, ["summary","start_iso","end_iso"]),
            self._tool("get_daily_briefing", "Return Jarvis's cached daily briefing, including selected news, sports, F1 learning, weather and calendar. Refresh it when requested.", {"refresh": {"type":"boolean","description":"Set true only when the user asks for a refresh/latest briefing."}}, []),
            self._tool("phone_status", "Check whether the trusted JARVIS phone companion is paired and currently connected. This does not access phone content.", {}, []),
            self._tool("f1_next_lesson", "Get the next Formula 1 learning topic from the user's persistent learning progression. Use when the user asks Jarvis to teach them something new about F1.", {}, []),
            self._tool("analyze_camera", "Inspect the latest frame from the explicitly enabled JARVIS Camera widget. Use only when the user asks what you can see, asks whether you can see them/an object, or asks you to inspect the camera.", {"prompt": self._string("What to inspect or describe in the camera frame.")}, ["prompt"]),
            self._tool("open_folder", "Open a common local folder when explicitly requested.", {"folder": self._string("One of desktop, downloads, documents, pictures, music, videos.")}, ["folder"]),
            self._tool("tell_time", "Get the current local time from the PC.", {}, []),
            self._tool("tell_date", "Get the current local date from the PC.", {}, []),
            self._tool("system_status", "Read basic PC status such as CPU/RAM/battery.", {}, []),
            self._tool("calculate", "Safely calculate a mathematical expression.", {"expression": self._string("Arithmetic expression.")}, ["expression"]),
            self._tool("create_note", "Create a local text note when the user asks Jarvis to write/save a note.", {"content": self._string("Note text.")}, ["content"]),
            self._tool("search_files", "Search Jarvis's project/local search scope for matching files.", {"query": self._string("Filename or search phrase.")}, ["query"]),
            self._tool("lock_computer", "Lock the Windows computer. Use only on an explicit request.", {}, []),
            self._tool("shutdown_request", "Request a PC shutdown. This tool does not shut down immediately; it returns that confirmation is required.", {}, []),
            self._tool("ui_show_panel", "Show a JARVIS workspace panel when the user explicitly asks to see it. Valid panel IDs include orb, conversation, briefing, weather, calendar, sports, learning, services, phone, activity, sources, system, context, camera, settings.", {"panel": self._string("Workspace panel ID.")}, ["panel"]),
            self._tool("ui_hide_panel", "Hide a JARVIS workspace panel when the user explicitly asks to hide/close that panel.", {"panel": self._string("Workspace panel ID.")}, ["panel"]),
            self._tool("ui_switch_workspace", "Switch the JARVIS workspace layout when the user explicitly asks. Use the exact workspace/mode name requested by the user; custom saved modes are allowed.", {"workspace": self._string("Workspace name.")}, ["workspace"]),
            self._tool("ui_create_workspace", "Create a persistent custom JARVIS mode/workspace by cloning the current layout. Use only when the user explicitly asks to create/save a new mode.", {"workspace": self._string("Name for the new mode/workspace.")}, ["workspace"]),
        ]

    @staticmethod
    def _string(description: str) -> dict[str, Any]:
        return {"type": "string", "description": description}

    @staticmethod
    def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        }

    def run(self, action: ToolAction) -> Any:
        if action.name == "open_app":
            return open_app(action.args.get("app", ""))
        if action.name == "close_app":
            return close_app(action.args.get("app", ""))
        if action.name == "open_website":
            return open_website(action.args.get("site", ""))
        if action.name == "search_web":
            return search_web(action.args.get("query", ""))
        if action.name == "answer_web_question":
            return answer_web_question(action.args.get("query", ""), self.config)
        if action.name == "get_weather":
            return self.weather_service.get(action.args.get("location") or None).to_dict()
        if action.name == "calendar_status":
            return self.calendar_status_data()
        if action.name == "calendar_connect":
            return self.google_calendar_service.connect()
        if action.name == "calendar_list_events":
            return self.list_calendar_events(days=int(action.args.get("days") or 2))
        if action.name == "calendar_create_event":
            return self.google_calendar_service.create_event(
                summary=str(action.args.get("summary") or ""),
                start_iso=str(action.args.get("start_iso") or ""),
                end_iso=str(action.args.get("end_iso") or ""),
                location=str(action.args.get("location") or ""),
                description=str(action.args.get("description") or ""),
            )
        if action.name == "get_daily_briefing":
            return self.daily_briefing_service.generate(force=bool(action.args.get("refresh", False)))
        if action.name == "phone_status":
            return self.phone_status_data()
        if action.name == "f1_next_lesson":
            return self.f1_learning_service.next_lesson()
        if action.name == "analyze_camera":
            if self._camera_frame_supplier is None or self._vision_analyzer is None:
                return "Camera vision is not connected to the JARVIS runtime."
            snapshot = self._camera_frame_supplier()
            if snapshot is None:
                return "The camera is not enabled or no recent camera frame is available. Enable the Camera widget first."
            try:
                return self._vision_analyzer(snapshot.data_url, action.args.get("prompt", "Describe what is visible in the camera."))
            except Exception as exc:
                return f"Camera analysis failed: {exc}"
        if action.name == "open_folder":
            return open_folder(action.args.get("folder", ""))
        if action.name == "tell_time":
            return tell_time()
        if action.name == "tell_date":
            return tell_date()
        if action.name == "system_status":
            return get_system_status()
        if action.name == "calculate":
            return calculate_expression(action.args.get("expression", ""))
        if action.name == "create_note":
            notes_dir = self.base_dir / self.config.notes_dir
            return create_note(notes_dir, action.args.get("content", ""))
        if action.name == "search_files":
            return search_files(self.base_dir, action.args.get("query", ""))
        if action.name == "lock_computer":
            return lock_computer()
        if action.name == "shutdown_request":
            return "Confirmation required. No shutdown was executed."
        if action.name in {"ui_show_panel", "ui_hide_panel", "ui_switch_workspace", "ui_create_workspace"}:
            if self._ui_event_sink is None:
                return "Workspace UI is not connected."
            payload = dict(action.args)
            self._ui_event_sink(action.name, payload)
            return "Workspace updated."
        return f"Tool '{action.name}' is not implemented."

    @staticmethod
    def result_for_model(result: Any) -> str:
        if isinstance(result, WebAnswer):
            payload = {
                "answer": result.answer,
                "sources": result.source_lines,
                "provider": result.provider,
                "query": result.query,
            }
            return json.dumps(payload, ensure_ascii=False)
        if isinstance(result, (dict, list, tuple)):
            return json.dumps(result, ensure_ascii=False, default=str)
        return str(result)
