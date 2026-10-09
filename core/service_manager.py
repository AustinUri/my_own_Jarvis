from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

from core.user_paths import jarvis_data_dir
from cloud_client.api import CloudApiClient


CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


class ServiceManager:
    """Keeps Jarvis's local dependencies alive without making the user babysit terminals."""

    def __init__(self, config, log: Callable[[str], None] | None = None, status_callback: Callable[[dict], None] | None = None):
        self.config = config
        self.log = log or (lambda _m: None)
        self.status_callback = status_callback or (lambda _s: None)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.status = {
            'lm_studio': 'unknown',
            'model': 'unknown',
            'docker': 'unknown',
            'searxng': 'unknown',
            'cloud_core': 'unknown',
            'windows_device': 'unknown',
            'samsung_device': 'unknown',
        }
        self.cloud = CloudApiClient(
            base_url=str(getattr(config, 'cloud_base_url', 'https://uri-jarvis.duckdns.org')),
            timeout=float(getattr(config, 'cloud_request_timeout_seconds', 10.0)),
        )

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='jarvis-service-manager', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _set(self, key: str, value: str) -> None:
        if self.status.get(key) == value:
            return
        self.status[key] = value
        self.status_callback(dict(self.status))

    def _loop(self) -> None:
        # First boot is eager, then health-check periodically.
        try:
            self.ensure_all()
        except Exception as exc:
            self.log(f'Service manager startup warning: {exc}')
        while not self._stop.wait(max(20.0, float(getattr(self.config, 'service_health_interval_seconds', 45.0)))):
            try:
                self._refresh_status()
                if getattr(self.config, 'auto_manage_services', True):
                    if self.status['lm_studio'] != 'online' or self.status['model'] != 'loaded':
                        self._ensure_lm_studio()
                    if self.status['searxng'] != 'online':
                        self._ensure_searxng()
            except Exception as exc:
                self.log(f'Service manager health warning: {exc}')

    def ensure_all(self) -> None:
        if not getattr(self.config, 'auto_manage_services', True):
            self._refresh_status()
            return
        if getattr(self.config, 'auto_start_lm_studio', True):
            self._ensure_lm_studio()
        if getattr(self.config, 'auto_start_searxng', True):
            self._ensure_searxng()
        self._refresh_status()

    def _refresh_status(self) -> None:
        models = self._lm_models()
        self._set('lm_studio', 'online' if models is not None else 'offline')
        wanted = str(getattr(self.config, 'ai_model_name', 'jarvis-qwen'))
        loaded = False
        if isinstance(models, dict):
            for item in models.get('data') or []:
                if str(item.get('id') or '') == wanted:
                    loaded = True
                    break
        self._set('model', 'loaded' if loaded else 'not-loaded')
        docker_ok = self._docker_ready()
        self._set('docker', 'online' if docker_ok else 'offline')
        self._set('searxng', 'online' if self._searxng_ready() else 'offline')
        self._refresh_cloud_status()

    def _refresh_cloud_status(self) -> None:
        try:
            health = self.cloud.health()
            cloud_online = bool(health.get('ok'))
        except Exception:
            cloud_online = False

        self._set('cloud_core', 'online' if cloud_online else 'offline')

        if not cloud_online:
            self._set('windows_device', 'offline')
            self._set('samsung_device', 'offline')
            return

        try:
            payload = self.cloud.list_devices()
            rows = payload.get('devices') or []
            connected = {str(row.get('device_id') or '') for row in rows if isinstance(row, dict)}
        except Exception:
            self._set('windows_device', 'auth-error')
            self._set('samsung_device', 'auth-error')
            return

        windows_id = str(getattr(self.config, 'cloud_windows_device_id', 'uri-windows'))
        phone_id = str(getattr(self.config, 'cloud_phone_device_id', 'uri-s25'))
        self._set('windows_device', 'online' if windows_id in connected else 'offline')
        self._set('samsung_device', 'online' if phone_id in connected else 'offline')

    def _http_json(self, url: str, timeout: float = 3.0):
        req = urllib.request.Request(url, headers={'User-Agent': 'JarvisLocalAssistant/27'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', errors='replace'))

    def _lm_models(self):
        try:
            base = str(getattr(self.config, 'ai_base_url', 'http://127.0.0.1:1234/v1')).rstrip('/')
            return self._http_json(base + '/models', timeout=2.5)
        except Exception:
            return None

    def _ensure_lm_studio(self) -> None:
        models = self._lm_models()
        if models is None:
            lms = shutil.which('lms')
            if not lms:
                self._set('lm_studio', 'missing')
                self.log('LM Studio CLI (lms) is not on PATH. Jarvis will keep running in degraded mode.')
                return
            self.log('Starting LM Studio local server…')
            self._run_hidden([lms, 'server', 'start'], timeout=20)
            for _ in range(20):
                time.sleep(0.75)
                models = self._lm_models()
                if models is not None:
                    break
        self._set('lm_studio', 'online' if models is not None else 'offline')
        if models is None:
            return

        wanted = str(getattr(self.config, 'ai_model_name', 'jarvis-qwen'))
        if any(str(x.get('id') or '') == wanted for x in (models.get('data') or [])):
            self._set('model', 'loaded')
            return
        if not getattr(self.config, 'auto_load_ai_model', True):
            self._set('model', 'not-loaded')
            return
        lms = shutil.which('lms')
        if not lms:
            return
        model_key = str(getattr(self.config, 'ai_local_model_key', 'qwen/qwen3.5-9b'))
        context = str(int(getattr(self.config, 'ai_context_length', 16384)))
        self.log(f'Loading {model_key} as {wanted}…')
        self._run_hidden([lms, 'load', model_key, '--identifier', wanted, '--context-length', context], timeout=120)
        refreshed = self._lm_models() or {}
        loaded = any(str(x.get('id') or '') == wanted for x in (refreshed.get('data') or []))
        self._set('model', 'loaded' if loaded else 'not-loaded')

    def _docker_ready(self) -> bool:
        docker = shutil.which('docker')
        if not docker:
            return False
        try:
            result = subprocess.run([docker, 'version', '--format', '{{.Server.Version}}'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=6, creationflags=CREATE_NO_WINDOW)
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False

    def _start_docker_desktop(self) -> None:
        # V30: Docker Desktop must never be started implicitly.
        # Local SearXNG is optional; users may start Docker manually when wanted.
        if str(os.environ.get("JARVIS_ALLOW_DOCKER_AUTOSTART", "")).strip().lower() not in {"1", "true", "yes", "on"}:
            self.log("Docker Desktop auto-start is disabled in V30; local SearXNG remains optional.")
            return
        candidates = [
            Path(r'C:\Program Files\Docker\Docker\Docker Desktop.exe'),
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Docker' / 'Docker Desktop.exe',
        ]
        for exe in candidates:
            if exe.exists():
                try:
                    subprocess.Popen([str(exe)], close_fds=True, creationflags=CREATE_NO_WINDOW)
                    self.log('Starting Docker Desktop for Jarvis web search…')
                    return
                except OSError:
                    pass

    def _searxng_ready(self) -> bool:
        try:
            base = str(getattr(self.config, 'searxng_base_url', 'http://localhost:8888')).rstrip('/')
            url = base + '/search?' + urllib.parse.urlencode({'q': 'jarvis health', 'format': 'json'})
            data = self._http_json(url, timeout=3.0)
            return isinstance(data, dict) and 'results' in data
        except Exception:
            return False

    def _ensure_searxng(self) -> None:
        if self._searxng_ready():
            self._set('searxng', 'online')
            return
        docker = shutil.which('docker')
        if not docker:
            self._set('docker', 'missing')
            self._set('searxng', 'offline')
            self.log('Docker CLI is not installed; SearXNG cannot be auto-managed.')
            return
        if not self._docker_ready():
            if getattr(self.config, 'auto_start_docker_desktop', True):
                self._start_docker_desktop()
            for _ in range(45):
                if self._stop.wait(1.0):
                    return
                if self._docker_ready():
                    break
        if not self._docker_ready():
            self._set('docker', 'offline')
            return
        self._set('docker', 'online')

        inspect = subprocess.run([docker, 'inspect', 'searxng'], capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=CREATE_NO_WINDOW)
        if inspect.returncode != 0:
            self._create_managed_searxng(docker)
        else:
            self._run_hidden([docker, 'start', 'searxng'], timeout=25)
        for _ in range(20):
            time.sleep(0.5)
            if self._searxng_ready():
                self._set('searxng', 'online')
                self.log('SearXNG is online.')
                return
        self._set('searxng', 'offline')

    def _create_managed_searxng(self, docker: str) -> None:
        cfg_dir = jarvis_data_dir() / 'searxng'
        cfg_dir.mkdir(parents=True, exist_ok=True)
        settings = cfg_dir / 'settings.yml'
        if not settings.exists():
            settings.write_text(
                'use_default_settings: true\n'
                'search:\n'
                '  formats:\n'
                '    - html\n'
                '    - json\n'
                'server:\n'
                f'  secret_key: "{secrets.token_hex(32)}"\n'
                '  limiter: false\n',
                encoding='utf-8',
            )
        self.log('Creating a managed local SearXNG container…')
        mount = f'{cfg_dir}:/etc/searxng'
        self._run_hidden([
            docker, 'run', '--name', 'searxng', '-d', '-p', '8888:8080',
            '-v', mount, 'docker.io/searxng/searxng:latest'
        ], timeout=120)

    @staticmethod
    def _run_hidden(args: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=CREATE_NO_WINDOW)
