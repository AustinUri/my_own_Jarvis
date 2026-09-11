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

    def set_ui_event_sink(self, sink: Callable[[str, dict[str, Any]], None] | None) -> None:
        self._ui_event_sink = sink

    def definitions(self) -> list[dict[str, Any]]:
        return [
            self._tool("open_app", "Open an installed desktop application. Use only when the user explicitly asks to open/run/launch an app.", {"app": self._string("Application name such as chrome, spotify, notepad, calculator, explorer, edge, discord, vscode.")}, ["app"]),
            self._tool("close_app", "Close a desktop application. Use only when explicitly requested.", {"app": self._string("Application name to close.")}, ["app"]),
            self._tool("open_website", "Open a website in the default browser. The site may be a known name, a domain such as chess.com, or an http/https URL. Use only when explicitly asked to open/show/navigate to it.", {"site": self._string("Website name, domain, or URL.")}, ["site"]),
            self._tool("search_web", "Open a browser search page for a query. This changes the user's UI, so use only when the user explicitly asks to search/open search results.", {"query": self._string("Search query.")}, ["query"]),
            self._tool("answer_web_question", "Research a public factual/current question using Jarvis's local SearXNG/Wikipedia web pipeline. Use this for facts that may require the internet. Never use it for the user's private schedule, inbox, files, reminders, or personal data.", {"query": self._string("The factual question to research.")}, ["query"]),
            self._tool("open_folder", "Open a common local folder when explicitly requested.", {"folder": self._string("One of desktop, downloads, documents, pictures, music, videos.")}, ["folder"]),
            self._tool("tell_time", "Get the current local time from the PC.", {}, []),
            self._tool("tell_date", "Get the current local date from the PC.", {}, []),
            self._tool("system_status", "Read basic PC status such as CPU/RAM/battery.", {}, []),
            self._tool("calculate", "Safely calculate a mathematical expression.", {"expression": self._string("Arithmetic expression.")}, ["expression"]),
            self._tool("create_note", "Create a local text note when the user asks Jarvis to write/save a note.", {"content": self._string("Note text.")}, ["content"]),
            self._tool("search_files", "Search Jarvis's project/local search scope for matching files.", {"query": self._string("Filename or search phrase.")}, ["query"]),
            self._tool("lock_computer", "Lock the Windows computer. Use only on an explicit request.", {}, []),
            self._tool("shutdown_request", "Request a PC shutdown. This tool does not shut down immediately; it returns that confirmation is required.", {}, []),
            self._tool("ui_show_panel", "Show a JARVIS workspace panel when the user explicitly asks to see it. Valid panel IDs: orb, conversation, activity, sources, system, context, camera, settings.", {"panel": self._string("Workspace panel ID.")}, ["panel"]),
            self._tool("ui_hide_panel", "Hide a JARVIS workspace panel when the user explicitly asks to hide/close that panel.", {"panel": self._string("Workspace panel ID.")}, ["panel"]),
            self._tool("ui_switch_workspace", "Switch the JARVIS workspace layout when the user explicitly asks. Valid names: Normal, Research, Developer, Vision, Minimal.", {"workspace": self._string("Workspace name.")}, ["workspace"]),
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
        if action.name in {"ui_show_panel", "ui_hide_panel", "ui_switch_workspace"}:
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
