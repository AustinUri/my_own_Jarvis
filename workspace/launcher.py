from __future__ import annotations

import argparse
import sys
import threading
from dataclasses import asdict
from pathlib import Path

import uvicorn
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication

from core.config import AppConfig
from core.orchestrator import Orchestrator
from core.service_manager import ServiceManager
from workspace.bridge import WorkspaceBridge
from workspace.profiles import WorkspaceProfileStore
from workspace.server import WorkspaceServer
from workspace.tray import WorkspaceTray
from workspace.activity import ActivityTimeline
from vision.camera_state import CameraState
from vision.hololab import run_visual_tests
from phone.cloud_hub import CloudPhoneHub
from core.agent_mesh import AgentMesh
from core.resource_governor import ResourceGovernor
from workspace.native_surface import NativeSurfaceController


class CommandRouter(QObject):
    incoming = Signal(dict)

    def __init__(self, bridge: WorkspaceBridge, camera_state: CameraState, publish, orchestrator: Orchestrator, phone_hub: CloudPhoneHub, agent_mesh: AgentMesh, resource_governor: ResourceGovernor, surface_controller: NativeSurfaceController):
        super().__init__()
        self.bridge = bridge
        self.camera_state = camera_state
        self.publish = publish
        self.orchestrator = orchestrator
        self.phone_hub = phone_hub
        self.agent_mesh = agent_mesh
        self.resource_governor = resource_governor
        self.surface_controller = surface_controller
        self.incoming.connect(self._dispatch)

    def _thread(self, target, name: str) -> None:
        threading.Thread(target=target, name=name, daemon=True).start()

    def shutdown_surface(self) -> None:
        # The V29 Surface renderer is an isolated QWebEngine sibling owned by the
        # Control Center shell. There is no screenshot/CDP worker to tear down.
        try:
            self.surface_controller.close()
        except Exception:
            pass

    @Slot(dict)
    def _dispatch(self, message: dict) -> None:
        action = str(message.get('action') or '').strip()
        payload = message.get('payload') or {}
        if action == 'submit_text':
            text = str(payload.get('text') or '')
            self.bridge.submit_text.emit(text)
        elif action == 'push_to_talk':
            self.bridge.push_to_talk.emit()
        elif action == 'test_microphone':
            self.bridge.test_microphone.emit()
        elif action == 'test_voice':
            self.bridge.test_voice.emit()
        elif action == 'set_assistant_enabled':
            self.bridge.set_assistant_enabled.emit(bool(payload.get('enabled', True)))
        elif action == 'toggle_voice':
            self.bridge.toggle_voice.emit()
        elif action == 'toggle_wake_word':
            self.bridge.toggle_wake_word.emit()
        elif action == 'clear_memory':
            self.bridge.clear_memory.emit()
        elif action == 'config_patch':
            self.bridge.apply_config_patch(dict(payload))
        elif action == 'camera_enabled':
            self.camera_state.set_enabled(True)
            self.publish('camera_status', self.camera_state.status())
        elif action == 'camera_disabled':
            self.camera_state.set_enabled(False)
            self.publish('camera_status', self.camera_state.status())
        elif action == 'camera_frame':
            accepted = self.camera_state.update(
                str(payload.get('data_url') or ''),
                int(payload.get('width') or 0),
                int(payload.get('height') or 0),
            )
            if accepted:
                self.publish('camera_status', self.camera_state.status())
        elif action == 'hololab_test':
            self.publish('hololab_result', run_visual_tests(dict(payload)))
        elif action in {'surface_open_native', 'surface_open_integrated'}:
            url = str(payload.get('url') or '')
            title = str(payload.get('title') or '')
            self.surface_controller.open(url, title)
        elif action == 'surface_close':
            self.surface_controller.close()
        elif action == 'surface_back':
            self.surface_controller.back()
        elif action == 'surface_forward':
            self.surface_controller.forward()
        elif action == 'surface_reload':
            self.surface_controller.reload()
        elif action in {'surface_pause','surface_resume','surface_viewport','surface_pointer','surface_text','surface_key'}:
            # Legacy V28 streamed-surface events are intentionally ignored in V29.
            pass
        elif action == 'refresh_briefing':
            def run_briefing():
                self.publish('briefing_status', {'status': 'working'})
                data = self.orchestrator.tools.daily_briefing_service.generate(force=True)
                self.publish('daily_briefing', data)
            self._thread(run_briefing, 'jarvis-briefing-refresh')
        elif action == 'refresh_weather':
            def run_weather():
                try:
                    data = self.orchestrator.tools.weather_service.get(str(payload.get('location') or '') or None).to_dict()
                    self.publish('weather', data)
                except Exception as exc:
                    self.publish('weather', {'error': str(exc)})
            self._thread(run_weather, 'jarvis-weather-refresh')
        elif action == 'refresh_calendar':
            def run_calendar():
                try:
                    tools = self.orchestrator.tools
                    self.publish('calendar_status', tools.calendar_status_data())
                    self.publish('calendar_events', tools.list_calendar_events(days=int(payload.get('days') or 3)))
                except Exception as exc:
                    self.publish('calendar_status', {'connected': False, 'source': 'none', 'message': str(exc)})
                    self.publish('calendar_events', [])
            self._thread(run_calendar, 'jarvis-calendar-refresh')
        elif action == 'calendar_connect':
            def connect_calendar():
                service = self.orchestrator.tools.google_calendar_service
                try:
                    message = service.connect()
                    self.publish('log', message)
                    self.publish('calendar_status', self.orchestrator.tools.calendar_status_data())
                    try:
                        self.publish('calendar_events', self.orchestrator.tools.list_calendar_events(days=3))
                    except Exception:
                        pass
                except Exception as exc:
                    self.publish('calendar_status', {'connected': False, 'source': 'none', 'message': str(exc)})
            self._thread(connect_calendar, 'jarvis-calendar-connect')
        elif action == 'phone_pair':
            def pair_phone():
                try:
                    pairing = self.phone_hub.begin_pairing()
                    self.publish('phone_pairing', pairing)
                    self.publish('phone_status', self.phone_hub.status())
                except Exception as exc:
                    self.publish('phone_pairing', {"error": str(exc)})
            self._thread(pair_phone, 'jarvis-cloud-phone-pair')
        elif action == 'phone_status':
            def phone_status():
                self.publish('phone_status', self.phone_hub.status())
            self._thread(phone_status, 'jarvis-cloud-phone-status')
        elif action == 'phone_call_history':
            def phone_call_history():
                try:
                    result = self.phone_hub.request("call_log_list", {"limit": int(payload.get("limit") or 30)})
                    calls = (result.get("calls") or []) if isinstance(result, dict) else []
                    self.publish('phone_call_history', {
                        "ok": True,
                        "calls": calls,
                        "count": len(calls),
                        "full_history": bool(result.get("full_history")) if isinstance(result, dict) else False,
                        "history_source": str(result.get("history_source") or "unknown") if isinstance(result, dict) else "unknown",
                    })
                except Exception as exc:
                    self.publish('phone_call_history', {"ok": False, "calls": [], "error": str(exc)})
            self._thread(phone_call_history, 'jarvis-cloud-phone-call-history')
        elif action == 'coding_status':
            self.publish('coding_status', self.orchestrator.tools.coding_service.status())
        elif action == 'coding_prepare':
            def prepare_coding():
                self.publish('coding_status', self.orchestrator.tools.coding_service.ensure_workspace(refresh=bool(payload.get('refresh', False))))
            self._thread(prepare_coding, 'jarvis-coding-prepare')
        elif action == 'coding_checks':
            def coding_checks():
                self.publish('coding_status', self.orchestrator.tools.coding_service.run_checks())
            self._thread(coding_checks, 'jarvis-coding-checks')
        elif action == 'coding_diff':
            def coding_diff():
                result = self.orchestrator.tools.coding_service.diff(12000)
                status = self.orchestrator.tools.coding_service.status()
                status['diff_preview'] = result.get('diff', '') if isinstance(result, dict) else ''
                status['diff_stat'] = result.get('stat', '') if isinstance(result, dict) else ''
                self.publish('coding_status', status)
            self._thread(coding_diff, 'jarvis-coding-diff')
        elif action == 'next_f1_lesson':
            self.publish('f1_lesson', self.orchestrator.tools.f1_learning_service.next_lesson())
        elif action == 'engineering_status':
            self.publish('engineering_status', self.orchestrator.tools.engineering_learning_service.status())
        elif action == 'engineering_sync':
            def sync_engineering():
                result = self.orchestrator.tools.engineering_learning_service.sync()
                self.publish('engineering_status', result)
            self._thread(sync_engineering, 'jarvis-engineering-sync')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)

    app = QApplication(sys.argv)
    app.setApplicationName('JARVIS')
    app.setOrganizationName('AustinUri')
    app.setQuitOnLastWindowClosed(False)

    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / 'config.json'
    config = AppConfig.load(config_path)
    orchestrator = Orchestrator(base_dir=base_dir, config=config)
    activity = ActivityTimeline(max_events=400)

    state = {
        'assistantState': 'Idle' if orchestrator.enabled else 'Disabled',
        'transcript': '', 'response': '', 'responseLanguage': 'en', 'spoken': '',
        'logs': [], 'activity': [], 'error': '', 'dailyBriefing': orchestrator.tools.daily_briefing_service.cached(),
        'weather': {}, 'calendarStatus': orchestrator.tools.calendar_status_data(), 'calendarEvents': [],
        'f1Lesson': {}, 'engineeringStatus': orchestrator.tools.engineering_learning_service.status(), 'codingStatus': orchestrator.tools.coding_service.status(), 'serviceStatus': {}, 'phoneStatus': {}, 'phonePairing': {}, 'phoneCallHistory': {'ok': False, 'calls': []}, 'agentMesh': {}, 'hololabResult': {}, 'surfaceStatus': {},
    }

    server: WorkspaceServer | None = None

    def snapshot() -> dict:
        return {
            'version': 30, 'build': '30.0-cloud',
            'runtime': dict(state),
            'config': asdict(config),
            'aiStatus': state.get('aiStatus', 'Checking AI provider…'),
            'capabilities': [d['function']['name'] for d in orchestrator.tools.definitions()],
            'dailyBriefing': state.get('dailyBriefing') or {},
            'weather': state.get('weather') or {},
            'calendarStatus': state.get('calendarStatus') or {},
            'calendarEvents': state.get('calendarEvents') or [],
            'f1Lesson': state.get('f1Lesson') or {},
            'engineeringStatus': state.get('engineeringStatus') or {},
            'codingStatus': state.get('codingStatus') or {},
            'serviceStatus': state.get('serviceStatus') or {},
            'phoneStatus': state.get('phoneStatus') or {},
            'phonePairing': state.get('phonePairing') or {},
            'phoneCallHistory': state.get('phoneCallHistory') or {'ok': False, 'calls': []},
            'agentMesh': state.get('agentMesh') or {},
            'hololabResult': state.get('hololabResult') or {},
            'surfaceStatus': state.get('surfaceStatus') or {},
            'activity': state.get('activity') or [],
        }

    def publish(event_type: str, payload) -> None:
        if event_type == 'daily_briefing': state['dailyBriefing'] = payload
        elif event_type == 'weather': state['weather'] = payload
        elif event_type == 'calendar_status': state['calendarStatus'] = payload
        elif event_type == 'calendar_events': state['calendarEvents'] = payload
        elif event_type == 'f1_lesson': state['f1Lesson'] = payload
        elif event_type == 'engineering_status': state['engineeringStatus'] = payload
        elif event_type == 'coding_status': state['codingStatus'] = payload
        elif event_type == 'service_status': state['serviceStatus'] = payload
        elif event_type == 'phone_status': state['phoneStatus'] = payload
        elif event_type == 'phone_pairing': state['phonePairing'] = payload
        elif event_type == 'phone_call_history': state['phoneCallHistory'] = payload
        elif event_type == 'agent_mesh': state['agentMesh'] = payload
        elif event_type == 'hololab_result': state['hololabResult'] = payload
        elif event_type == 'surface_status': state['surfaceStatus'] = payload
        elif event_type == 'activity': state['activity'] = activity.snapshot()
        if server is not None:
            server.publish(event_type, payload)

    camera_state = CameraState()
    orchestrator.tools.set_camera_vision(lambda: camera_state.latest(), orchestrator.agent.analyze_camera_frame)

    phone_hub = CloudPhoneHub(config, log=lambda m: publish('log', m), status_callback=lambda data: publish('phone_status', data))
    orchestrator.tools.set_phone_hub(phone_hub)
    state['phoneStatus'] = phone_hub.status()
    state['calendarStatus'] = orchestrator.tools.calendar_status_data()

    resource_governor = ResourceGovernor(config)
    agent_mesh = AgentMesh(config)
    state['agentMesh'] = agent_mesh.snapshot(resource=resource_governor.snapshot().to_dict())

    bridge = WorkspaceBridge(orchestrator, config, config_path, publish)
    surface_controller = NativeSurfaceController(publish=publish)
    state['surfaceStatus'] = surface_controller.status()
    router = CommandRouter(bridge, camera_state, publish, orchestrator, phone_hub, agent_mesh, resource_governor, surface_controller)
    profile_store = WorkspaceProfileStore()

    briefing_started = threading.Event()
    def prepare_arrival_briefing() -> None:
        if briefing_started.is_set() or not config.briefing_enabled or not config.briefing_on_workspace_open:
            return
        briefing_started.set()
        def worker():
            try:
                # Give the managed web service a short chance to come online after login.
                import time
                for _ in range(24):
                    if state.get('serviceStatus', {}).get('searxng') == 'online':
                        break
                    time.sleep(0.75)
                data = orchestrator.tools.daily_briefing_service.generate(force=False)
                publish('daily_briefing', data)
                # Lightweight side data keeps widgets useful even if briefing sections are disabled.
                if isinstance(data.get('weather'), dict): publish('weather', data.get('weather'))
                if isinstance(data.get('calendar'), dict):
                    publish('calendar_status', orchestrator.tools.calendar_status_data())
                    publish('calendar_events', data['calendar'].get('events') or [])
                if isinstance(data.get('f1_learning'), dict): publish('f1_lesson', data.get('f1_learning'))
                if config.briefing_announce_voice and config.voice_enabled:
                    try:
                        orchestrator.speaker.speak('Good day, sir. Your daily briefing is ready. Which section would you like first?')
                    except Exception:
                        pass
            except Exception as exc:
                publish('log', f'Daily briefing warning: {exc}')
        threading.Thread(target=worker, name='jarvis-arrival-briefing', daemon=True).start()

    state['activity'] = activity.snapshot()

    server = WorkspaceServer(
        base_dir=base_dir, config=config,
        command_handler=lambda message: router.incoming.emit(message),
        snapshot_provider=snapshot,
        profile_store=profile_store,
        on_client_connected=prepare_arrival_briefing,
    )
    orchestrator.tools.set_ui_event_sink(lambda action, payload: publish('ui_command', {'action': action, 'payload': payload}))

    def push_activity(event: dict | None) -> None:
        if not event:
            return
        state['activity'] = activity.snapshot()
        if server is not None:
            server.publish('activity', event)

    def add_log(message: str) -> None:
        state['logs'].append(message)
        state['logs'] = state['logs'][-300:]
        push_activity(activity.from_log(message))
        publish('log', message)

    def on_state(value: str) -> None:
        state['assistantState'] = value
        publish('state', value)
        push_activity(activity.state(value))

    def on_transcript(text: str, lang: str) -> None:
        state['transcript'] = text
        publish('transcript', {'text': text, 'language': lang})
        if (text or '').strip() and text != '[nothing heard]' and getattr(config, 'agent_mesh_enabled', True):
            try:
                resources = resource_governor.snapshot().to_dict()
                publish('agent_mesh', agent_mesh.route(text, resource=resources))
            except Exception as exc:
                add_log(f'Agent Mesh routing warning: {exc}')
        push_activity(activity.input(text, source='voice-or-text'))

    def on_response(text: str, lang: str) -> None:
        state['response'] = text
        state['responseLanguage'] = lang
        publish('response', {'text': text, 'language': lang})
        if getattr(config, 'agent_mesh_enabled', True):
            publish('agent_mesh', agent_mesh.complete(resource=resource_governor.snapshot().to_dict()))
        push_activity(activity.output(text))

    def on_error(text: str) -> None:
        state['error'] = text
        publish('error', text)
        push_activity(activity.add('error', 'JARVIS error', text, status='error', source='runtime'))

    orchestrator.state_changed.connect(on_state)
    orchestrator.transcript_ready.connect(on_transcript)
    orchestrator.response_ready.connect(on_response)
    orchestrator.spoken_text_ready.connect(lambda text: (state.__setitem__('spoken', text), publish('spoken', text)))
    orchestrator.log_ready.connect(add_log)
    orchestrator.error_raised.connect(on_error)
    phone_hub.log = add_log
    orchestrator.tools.daily_briefing_service.log = add_log
    push_activity(activity.add('system', 'JARVIS Core started', 'Background runtime and Control Center bridge initialized.', status='success', source='runtime'))

    host = '127.0.0.1'
    url = f'http://{host}:{args.port}'
    uvicorn_config = uvicorn.Config(server.app, host=host, port=args.port, log_level='warning')
    uvicorn_server = uvicorn.Server(uvicorn_config)
    server_thread = threading.Thread(target=uvicorn_server.run, name='jarvis-workspace-server', daemon=True)
    server_thread.start()

    service_manager = ServiceManager(config, log=add_log, status_callback=lambda data: publish('service_status', data))
    service_manager.start()

    def quit_all() -> None:
        router.shutdown_surface()
        service_manager.stop()
        orchestrator.shutdown()
        config.save(config_path)
        uvicorn_server.should_exit = True
        app.quit()

    app.aboutToQuit.connect(orchestrator.shutdown)
    tray = WorkspaceTray(app, orchestrator, url, quit_all, service_manager=service_manager, surface_controller=surface_controller)

    def check_ai_status() -> None:
        status = orchestrator.ai_provider_status()
        state['aiStatus'] = status
        publish('ai_status', status)
    threading.Thread(target=check_ai_status, name='jarvis-ai-status', daemon=True).start()

    if not args.background and not args.no_open:
        QTimer.singleShot(900, tray.open_workspace)

    exit_code = app.exec()
    router.shutdown_surface()
    service_manager.stop()
    config.save(config_path)
    uvicorn_server.should_exit = True
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
