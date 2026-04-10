from __future__ import annotations

from pathlib import Path
from typing import Any

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
from tools.web_tools import answer_web_question, open_website, search_web


class ToolRegistry:
    def __init__(self, base_dir: Path, config: AppConfig):
        self.base_dir = base_dir
        self.config = config

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
        return f"Tool '{action.name}' is not implemented yet."
