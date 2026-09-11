from __future__ import annotations

import argparse
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path

import uvicorn
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication

from core.config import AppConfig
from core.orchestrator import Orchestrator
from workspace.bridge import WorkspaceBridge
from workspace.server import WorkspaceServer
from workspace.tray import WorkspaceTray


class CommandRouter(QObject):
    incoming = Signal(dict)

    def __init__(self, bridge: WorkspaceBridge):
        super().__init__()
        self.bridge = bridge
        self.incoming.connect(self._dispatch)

    @Slot(dict)
    def _dispatch(self, message: dict) -> None:
        action = str(message.get("action") or "").strip()
        payload = message.get("payload") or {}
        if action == "submit_text":
            self.bridge.submit_text.emit(str(payload.get("text") or ""))
        elif action == "push_to_talk":
            self.bridge.push_to_talk.emit()
        elif action == "test_microphone":
            self.bridge.test_microphone.emit()
        elif action == "test_voice":
            self.bridge.test_voice.emit()
        elif action == "set_assistant_enabled":
            self.bridge.set_assistant_enabled.emit(bool(payload.get("enabled", True)))
        elif action == "toggle_voice":
            self.bridge.toggle_voice.emit()
        elif action == "toggle_wake_word":
            self.bridge.toggle_wake_word.emit()
        elif action == "clear_memory":
            self.bridge.clear_memory.emit()
        elif action == "config_patch":
            self.bridge.apply_config_patch(dict(payload))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    app.setOrganizationName("AustinUri")
    app.setQuitOnLastWindowClosed(False)

    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "config.json"
    config = AppConfig.load(config_path)
    orchestrator = Orchestrator(base_dir=base_dir, config=config)

    state = {
        "assistantState": "Idle" if orchestrator.enabled else "Disabled",
        "transcript": "",
        "response": "",
        "responseLanguage": "en",
        "spoken": "",
        "logs": [],
        "error": "",
    }

    server: WorkspaceServer | None = None

    def snapshot() -> dict:
        return {
            "version": 23,
            "runtime": dict(state),
            "config": asdict(config),
            "aiStatus": state.get("aiStatus", "Checking AI provider…"),
            "capabilities": [d["function"]["name"] for d in orchestrator.tools.definitions()],
        }

    def publish(event_type: str, payload) -> None:
        if server is not None:
            server.publish(event_type, payload)

    bridge = WorkspaceBridge(orchestrator, config, config_path, publish)
    router = CommandRouter(bridge)

    server = WorkspaceServer(
        base_dir=base_dir,
        config=config,
        command_handler=lambda message: router.incoming.emit(message),
        snapshot_provider=snapshot,
    )

    orchestrator.tools.set_ui_event_sink(lambda action, payload: publish("ui_command", {"action": action, "payload": payload}))

    def add_log(message: str) -> None:
        state["logs"].append(message)
        state["logs"] = state["logs"][-300:]
        publish("log", message)

    orchestrator.state_changed.connect(lambda value: (state.__setitem__("assistantState", value), publish("state", value)))
    orchestrator.transcript_ready.connect(lambda text, lang: (state.__setitem__("transcript", text), publish("transcript", {"text": text, "language": lang})))
    orchestrator.response_ready.connect(lambda text, lang: (state.__setitem__("response", text), state.__setitem__("responseLanguage", lang), publish("response", {"text": text, "language": lang})))
    orchestrator.spoken_text_ready.connect(lambda text: (state.__setitem__("spoken", text), publish("spoken", text)))
    orchestrator.log_ready.connect(add_log)
    orchestrator.error_raised.connect(lambda text: (state.__setitem__("error", text), publish("error", text)))

    host = "127.0.0.1"
    url = f"http://{host}:{args.port}"
    uvicorn_config = uvicorn.Config(server.app, host=host, port=args.port, log_level="warning")
    uvicorn_server = uvicorn.Server(uvicorn_config)
    server_thread = threading.Thread(target=uvicorn_server.run, name="jarvis-workspace-server", daemon=True)
    server_thread.start()

    def quit_all() -> None:
        orchestrator.shutdown()
        config.save(config_path)
        uvicorn_server.should_exit = True
        app.quit()

    app.aboutToQuit.connect(orchestrator.shutdown)
    tray = WorkspaceTray(app, orchestrator, url, quit_all)

    def check_ai_status() -> None:
        status = orchestrator.ai_provider_status()
        state["aiStatus"] = status
        publish("ai_status", status)

    threading.Thread(target=check_ai_status, name="jarvis-ai-status", daemon=True).start()

    if not args.background and not args.no_open:
        QTimer.singleShot(900, tray.open_workspace)

    exit_code = app.exec()
    config.save(config_path)
    uvicorn_server.should_exit = True
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
