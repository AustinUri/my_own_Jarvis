from __future__ import annotations

import json
import re
import urllib.parse
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
from tools.web_tools import WebAnswer, answer_web_question, open_website, search_web, KNOWN_SITES
from services.weather import WeatherService
from services.google_calendar import GoogleCalendarService
from services.f1_learning import F1LearningService
from services.mech_learning import MechanicalEngineeringLearningService
from services.daily_briefing import DailyBriefingService
from services.coding_jarvis import CodingJarvisService


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
        self.engineering_learning_service = MechanicalEngineeringLearningService()
        self.daily_briefing_service = DailyBriefingService(config)
        self.coding_service = CodingJarvisService(
            repo_url=str(getattr(config, "coding_repo_url", "https://github.com/AustinUri/my_own_Jarvis.git")),
            mode=str(getattr(config, "coding_mode", "assisted")),
        )
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
            self._tool("open_website", "Open a website inside the JARVIS Surface Dock by default. The site may be a known name, a domain such as chess.com, or an http/https URL. Use only when explicitly asked to open/show/navigate to it. Do not open a separate external browser unless the user explicitly asks for an external/default browser.", {"site": self._string("Website name, domain, or URL.")}, ["site"]),
            self._tool("search_web", "Open a Google search inside the JARVIS Surface Dock. Use only when the user explicitly asks to search/open search results.", {"query": self._string("Search query.")}, ["query"]),
            self._tool("answer_web_question", "Research a public factual/current question using Jarvis's local SearXNG/Wikipedia web pipeline. It supports deep multi-source list/history/range research (for example all finals since a given year), not just single facts. Use this for facts that may require the internet. Never use it for the user's private schedule, inbox, files, reminders, or personal data.", {"query": self._string("The complete factual/research question, preserving requested years, ranges, and qualifiers.")}, ["query"]),
            self._tool("get_weather", "Get current weather and a short forecast for the user's configured location or another named location. Prefer this over generic web search for weather.", {"location": self._string("Optional city/location name. Leave empty to use the configured home weather location.")}, []),
            self._tool("calendar_status", "Check the preferred calendar source. JARVIS uses the native phone calendar when the trusted phone companion is connected, with Google Calendar as an optional backup.", {}, []),
            self._tool("calendar_connect", "Connect the optional Google Calendar backup. Native phone calendar does not require Google OAuth. Use only when the user explicitly asks to connect Google Calendar.", {}, []),
            self._tool("calendar_list_events", "Read upcoming events from the preferred personal calendar source: native phone calendar first, Google Calendar backup second. Never substitute a public web search for private calendar data.", {"days": {"type":"integer","description":"Number of days ahead to read, normally 1-7."}}, []),
            self._tool("calendar_create_event", "Create an event using Google Calendar backup for now. Native phone-calendar writing is intentionally deferred until the user explicitly grants write permission. Only use on an explicit request to create/add/schedule an event.", {"summary": self._string("Event title."), "start_iso": self._string("Start date/time as ISO 8601 with timezone when possible."), "end_iso": self._string("End date/time as ISO 8601 with timezone when possible."), "location": self._string("Optional event location."), "description": self._string("Optional description.")}, ["summary","start_iso","end_iso"]),
            self._tool("get_daily_briefing", "Return Jarvis's cached daily briefing, including selected news, sports, F1 learning, weather and calendar. Refresh it when requested.", {"refresh": {"type":"boolean","description":"Set true only when the user asks for a refresh/latest briefing."}}, []),
            self._tool("phone_status", "Check whether the trusted JARVIS phone companion is paired and currently connected. This does not access phone content.", {}, []),
            self._tool("phone_device_info", "Read basic non-sensitive device information from the paired phone, such as manufacturer, model and Android version.", {}, []),
            self._tool("phone_battery_status", "Read the paired phone battery percentage and whether it is charging.", {}, []),
            self._tool("phone_call_history", "Read recent cellular call-history metadata from the paired Android phone when Android grants call-log access. Returns contact/name, normalized number, direction, time and duration; it does not imply that call audio was recorded.", {"limit": {"type":"integer","description":"Number of recent calls, normally 10-50."}}, []),
            self._tool("phone_find_contact", "Search the paired Android phone contacts by name. Duplicate raw-contact rows and equivalent Israeli +972/05 numbers are normalized before results are returned. Requires contacts permission on the phone.", {"query": self._string("Contact name to search for.")}, ["query"]),
            self._tool("phone_call_contact", "Place a normal cellular call from the paired Android phone to a named contact. The tool performs contact lookup and duplicate-number cleanup itself; use it directly for explicit requests such as 'call Mum'. If several genuinely different numbers remain it returns them for clarification. This is dial/handoff mode; JARVIS starts the call but does not inject AI audio into the SIM call.", {"query": self._string("Contact name to call.")}, ["query"]),
            self._tool("phone_call_number", "Place a normal cellular call from the paired Android phone to an explicit phone number. Use only when the user explicitly asks to call/dial that number. Emergency numbers are blocked.", {"number": self._string("Phone number to call.")}, ["number"]),
            self._tool("phone_whatsapp_contact", "Open WhatsApp on the paired Android phone for a named contact with a message pre-filled. Contact lookup uses the same duplicate-safe +972/05 normalization as calling. V29.2 deliberately stops at compose/review: the user taps Send in WhatsApp, so JARVIS never falsely claims a message was sent.", {"query": self._string("Contact name for the WhatsApp message."), "message": self._string("Message text to prepare in WhatsApp.")}, ["query","message"]),
            self._tool("call_agent_prepare", "Prepare a transparent JARVIS call-agent handoff plan for a named person and message. This does not pretend to inject AI speech into a SIM call; it returns the disclosure/message and the next dial step.", {"recipient": self._string("Person/contact to call."), "message": self._string("What JARVIS should communicate or remind the user to say.")}, ["recipient","message"]),
            self._tool("coding_status", "Check Coding JARVIS development workspace status. Coding JARVIS uses a separate Git clone and never edits the running stable JARVIS copy.", {}, []),
            self._tool("coding_prepare_workspace", "Prepare or refresh the isolated Coding JARVIS Git development workspace. This may clone/pull the user's JARVIS repository but never edits the running stable copy.", {"refresh": {"type":"boolean","description":"Fetch/pull updates when the dev workspace is clean."}}, []),
            self._tool("coding_search", "Search the isolated JARVIS development codebase for a symbol, error text, file, or phrase.", {"query": self._string("Code/file/symbol/error search phrase.")}, ["query"]),
            self._tool("coding_read_file", "Read a text/source file from the isolated Coding JARVIS development workspace.", {"path": self._string("Repository-relative file path."), "start_line": {"type":"integer"}, "max_lines": {"type":"integer"}}, ["path"]),
            self._tool("coding_apply_patch", "Apply a unified-diff patch only inside the isolated Coding JARVIS development branch. Use only when the user explicitly asks Coding JARVIS to fix/change code.", {"patch": self._string("Unified diff patch to apply in the dev workspace.")}, ["patch"]),
            self._tool("coding_diff", "Show the current uncommitted diff from the isolated Coding JARVIS development branch.", {}, []),
            self._tool("coding_run_checks", "Run safe local syntax/diff checks against the isolated Coding JARVIS development workspace.", {}, []),
            self._tool("coding_commit", "Commit tested Coding JARVIS development-branch changes locally. This never pushes or promotes them to the stable running build.", {"message": self._string("Git commit message.")}, ["message"]),
            self._tool("f1_next_lesson", "Get the next Formula 1 learning topic from the user's persistent learning progression. Use when the user asks Jarvis to teach them something new about F1.", {}, []),
            self._tool("engineering_course_status", "Check whether the user's home-mech-engin mechanical-engineering course repository is available locally and report learning progress. This is local/keyless.", {}, []),
            self._tool("engineering_course_sync", "Clone or update the user's public home-mech-engin course repository with Git. No AI API key is required. Use when the user asks to sync/update the engineering course or when the course is not available.", {}, []),
            self._tool("engineering_lesson", "Teach or quiz the user from their home-mech-engin mechanical-engineering course. The tool returns source context from the local repository for the local JARVIS model to explain. Modes: teach, next, quiz, review.", {"topic": self._string("Optional engineering topic; leave blank for the next lesson."), "mode": self._string("teach, next, quiz, or review")}, []),
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
            self._tool("ui_show_panel", "Show a JARVIS workspace panel when the user explicitly asks to see it. Valid panel IDs include orb, conversation, briefing, weather, calendar, sports, learning, services, phone, calls, activity, sources, system, context, camera, agentmesh, engineering, coding, settings. Surface is a native pane controlled through ui_open_surface, not a widget.", {"panel": self._string("Workspace panel ID.")}, ["panel"]),
            self._tool("ui_hide_panel", "Hide a JARVIS workspace panel when the user explicitly asks to hide/close that panel.", {"panel": self._string("Workspace panel ID.")}, ["panel"]),
            self._tool("ui_switch_workspace", "Switch the JARVIS workspace layout when the user explicitly asks. Use the exact workspace/mode name requested by the user; custom saved modes are allowed.", {"workspace": self._string("Workspace name.")}, ["workspace"]),
            self._tool("ui_create_workspace", "Create a persistent custom JARVIS mode/workspace by cloning the current layout. Use only when the user explicitly asks to create/save a new mode.", {"workspace": self._string("Name for the new mode/workspace.")}, ["workspace"]),
            self._tool("ui_hololab_config", "Configure the HoloLab visual prototype when the user explicitly asks to change the holographic object.", {"enabled": {"type":"boolean","description":"Whether HoloLab should be active."}, "shape": self._string("cube, sphere, ring, cylinder, or gauntlet."), "material": self._string("aluminium, titanium, steel, ABS, PLA, or polycarbonate."), "width_mm": {"type":"number"}, "height_mm": {"type":"number"}, "depth_mm": {"type":"number"}}, []),
            self._tool("ui_open_surface", "Bring an explicitly requested normal website/domain into the JARVIS Surface Dock. Use this when the user asks to show a web surface inside the JARVIS layout. Games, DRM/UAC-sensitive software, and normal desktop applications should remain external instead of being force-embedded.", {"target": self._string("HTTPS URL or domain to show inside JARVIS."), "title": self._string("Optional short title for the surface.")}, ["target"]),
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
            site = str(action.args.get("site", "") or "").strip()
            key = site.lower()
            target = KNOWN_SITES.get(key, site)
            if self._ui_event_sink is not None:
                self._ui_event_sink("ui_open_surface", {"target": target, "title": key.title() if key in KNOWN_SITES else ""})
                return f"Opened {target} inside the JARVIS Surface."
            return open_website(site)
        if action.name == "search_web":
            query = str(action.args.get("query", "") or "").strip()
            if self._ui_event_sink is not None and query:
                target = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
                self._ui_event_sink("ui_open_surface", {"target": target, "title": "Search"})
                return f"Opened a web search for '{query}' inside the JARVIS Surface."
            return search_web(query)
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
        if action.name == "phone_device_info":
            if self._phone_hub is None:
                return {"ok": False, "error": "Phone bridge is not running."}
            return self._phone_hub.request("device_info", {})
        if action.name == "phone_battery_status":
            if self._phone_hub is None:
                return {"ok": False, "error": "Phone bridge is not running."}
            return self._phone_hub.request("battery_status", {})
        if action.name == "phone_call_history":
            if self._phone_hub is None:
                return {"ok": False, "error": "Phone bridge is not running."}
            limit = max(1, min(100, int(action.args.get("limit") or 30)))
            return self._phone_hub.request("call_log_list", {"limit": limit})
        if action.name == "phone_find_contact":
            if self._phone_hub is None:
                return {"ok": False, "error": "Phone bridge is not running."}
            return self._phone_hub.request("contact_search", {"query": str(action.args.get("query") or "")})
        if action.name == "phone_call_contact":
            if self._phone_hub is None:
                return {"ok": False, "error": "Phone bridge is not running."}
            query = str(action.args.get("query") or "").strip()
            query = re.sub(r"^(?:my|the)\s+", "", query, flags=re.IGNORECASE).strip()
            found = self._phone_hub.request("contact_search", {"query": query})
            contacts = (found.get("contacts") or []) if isinstance(found, dict) else []
            if not contacts:
                return {"ok": False, "error": f"No phone contact matched '{query}'.", "contacts": []}
            if len(contacts) > 1:
                # Android may legitimately expose several different numbers for one
                # person. Prefer a single mobile row; otherwise ask instead of guessing.
                mobiles = [c for c in contacts if int(c.get("type") or -1) == 2]
                if len(mobiles) == 1:
                    contacts = mobiles
            if len(contacts) != 1:
                return {"ok": False, "error": "That name still resolves to more than one distinct phone number. Please choose which one to call.", "contacts": contacts}
            row = contacts[0]
            return self._phone_hub.request("call_number", {"number": str(row.get("number") or ""), "name": str(row.get("name") or query)})
        if action.name == "phone_call_number":
            if self._phone_hub is None:
                return {"ok": False, "error": "Phone bridge is not running."}
            return self._phone_hub.request("call_number", {"number": str(action.args.get("number") or "")})
        if action.name == "phone_whatsapp_contact":
            if self._phone_hub is None:
                return {"ok": False, "error": "Phone bridge is not running."}
            query = str(action.args.get("query") or "").strip()
            query = re.sub(r"^(?:my|the)\s+", "", query, flags=re.IGNORECASE).strip()
            message = str(action.args.get("message") or "").strip()
            if not message:
                return {"ok": False, "error": "WhatsApp message text is empty."}
            found = self._phone_hub.request("contact_search", {"query": query})
            contacts = (found.get("contacts") or []) if isinstance(found, dict) else []
            if not contacts:
                return {"ok": False, "error": f"No phone contact matched '{query}'.", "contacts": []}
            if len(contacts) > 1:
                mobiles = [c for c in contacts if int(c.get("type") or -1) == 2]
                if len(mobiles) == 1:
                    contacts = mobiles
            if len(contacts) != 1:
                return {"ok": False, "error": "That name resolves to more than one distinct phone number. Please choose which one to message.", "contacts": contacts}
            row = contacts[0]
            return self._phone_hub.request("whatsapp_message", {
                "number": str(row.get("number") or ""),
                "name": str(row.get("name") or query),
                "message": message,
            })
        if action.name == "call_agent_prepare":
            recipient = str(action.args.get("recipient") or "").strip()
            message = str(action.args.get("message") or "").strip()
            return {
                "ok": True,
                "mode": "cellular-handoff",
                "recipient": recipient,
                "disclosure": f"Hello, this is JARVIS calling on behalf of my user.",
                "message": message,
                "next_step": f"Use phone_call_contact for {recipient} after the user has explicitly asked to place the call.",
                "limitation": "V29.2 does not inject synthesized JARVIS audio into ordinary SIM-call uplink/downlink audio.",
            }
        if action.name == "coding_status":
            return self.coding_service.status()
        if action.name == "coding_prepare_workspace":
            return self.coding_service.ensure_workspace(refresh=bool(action.args.get("refresh", False)))
        if action.name == "coding_search":
            return self.coding_service.search(str(action.args.get("query") or ""))
        if action.name == "coding_read_file":
            return self.coding_service.read_file(
                str(action.args.get("path") or ""),
                start_line=int(action.args.get("start_line") or 1),
                max_lines=int(action.args.get("max_lines") or 220),
            )
        if action.name == "coding_apply_patch":
            return self.coding_service.apply_patch(str(action.args.get("patch") or ""))
        if action.name == "coding_diff":
            return self.coding_service.diff()
        if action.name == "coding_run_checks":
            return self.coding_service.run_checks()
        if action.name == "coding_commit":
            return self.coding_service.commit(str(action.args.get("message") or ""))
        if action.name == "f1_next_lesson":
            return self.f1_learning_service.next_lesson()
        if action.name == "engineering_course_status":
            return self.engineering_learning_service.status()
        if action.name == "engineering_course_sync":
            return self.engineering_learning_service.sync()
        if action.name == "engineering_lesson":
            return self.engineering_learning_service.lesson(
                topic=str(action.args.get("topic") or ""),
                mode=str(action.args.get("mode") or "teach"),
            )
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
        if action.name in {"ui_show_panel", "ui_hide_panel", "ui_switch_workspace", "ui_create_workspace", "ui_open_surface", "ui_hololab_config"}:
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
