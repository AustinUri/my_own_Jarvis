from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from core.user_paths import credentials_dir

SCOPES = ['https://www.googleapis.com/auth/calendar']
_KEYRING_SERVICE = 'JARVIS.GoogleCalendar'
_KEYRING_USER = 'oauth-token-v1'


class GoogleCalendarService:
    """Optional Google Calendar backup.

    Authentication is one-time in normal operation. Refresh credentials are
    reused silently. On Windows, v26 prefers the OS credential vault via the
    Python keyring package; an existing v25 token JSON is migrated when
    possible. The native phone calendar remains the preferred source.
    """

    def __init__(self, config):
        self.config = config
        root = credentials_dir()
        configured = str(getattr(config, 'google_calendar_client_secret_path', '') or '').strip()
        self.client_secret = Path(configured) if configured else root / 'google_calendar_client.json'
        self.legacy_token_path = root / 'google_calendar_token.json'

    def _imports(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except Exception as exc:
            raise RuntimeError('Google Calendar dependencies are not installed. Run pip install -r requirements.txt.') from exc
        return Request, Credentials, InstalledAppFlow, build

    @staticmethod
    def _keyring():
        try:
            import keyring
            return keyring
        except Exception:
            return None

    def _load_token_json(self) -> str:
        keyring = self._keyring()
        if keyring is not None:
            try:
                value = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER)
                if value:
                    return value
            except Exception:
                pass
        if self.legacy_token_path.exists():
            try:
                value = self.legacy_token_path.read_text(encoding='utf-8')
            except Exception:
                return ''
            # Best-effort migration into Windows Credential Manager/keyring.
            if keyring is not None and value:
                try:
                    keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER, value)
                    self.legacy_token_path.unlink(missing_ok=True)
                except Exception:
                    pass
            return value
        return ''

    def _save_token_json(self, value: str) -> None:
        keyring = self._keyring()
        if keyring is not None:
            try:
                keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER, value)
                self.legacy_token_path.unlink(missing_ok=True)
                return
            except Exception:
                pass
        # Fallback for systems without a usable keyring backend. This remains
        # inside the current user's AppData credential directory, never source.
        self.legacy_token_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_token_path.write_text(value, encoding='utf-8')

    def status(self) -> dict[str, Any]:
        if not self.client_secret.exists():
            return {'connected': False, 'ready': False, 'source': 'google', 'message': f'Optional Google backup: add OAuth desktop credentials at {self.client_secret}'}
        if not self._load_token_json():
            return {'connected': False, 'ready': True, 'source': 'google', 'message': 'Google Calendar backup is ready to connect once.'}
        try:
            service = self._service(interactive=False)
            return {'connected': service is not None, 'ready': True, 'source': 'google', 'message': 'Google Calendar backup connected.' if service else 'Google Calendar backup needs reconnection.'}
        except Exception as exc:
            return {'connected': False, 'ready': True, 'source': 'google', 'message': str(exc)}

    def connect(self) -> str:
        if not self.client_secret.exists():
            return f'Google OAuth credentials are missing. Put the Desktop App JSON file at {self.client_secret}'
        service = self._service(interactive=True)
        return 'Google Calendar backup connected. Future token refresh is automatic.' if service else 'Google Calendar connection failed.'

    def _service(self, interactive: bool):
        Request, Credentials, InstalledAppFlow, build = self._imports()
        creds = None
        token_json = self._load_token_json()
        if token_json:
            try:
                creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
            except Exception:
                creds = None
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_token_json(creds.to_json())
        if (not creds or not creds.valid) and interactive:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secret), SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)
            self._save_token_json(creds.to_json())
        if not creds or not creds.valid:
            return None
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)

    def list_events(self, days: int = 2) -> list[dict[str, Any]]:
        service = self._service(interactive=False)
        if service is None:
            raise RuntimeError('Google Calendar backup is not connected.')
        now = dt.datetime.now().astimezone()
        end = now + dt.timedelta(days=max(1, min(30, int(days))))
        events = service.events().list(
            calendarId='primary', timeMin=now.isoformat(), timeMax=end.isoformat(),
            singleEvents=True, orderBy='startTime', maxResults=50,
        ).execute().get('items', [])
        out = []
        for event in events:
            start = (event.get('start') or {}).get('dateTime') or (event.get('start') or {}).get('date') or ''
            finish = (event.get('end') or {}).get('dateTime') or (event.get('end') or {}).get('date') or ''
            out.append({'id': event.get('id'), 'summary': event.get('summary') or '(No title)', 'start': start, 'end': finish, 'location': event.get('location') or '', 'htmlLink': event.get('htmlLink') or '', 'source': 'google'})
        return out

    def create_event(self, summary: str, start_iso: str, end_iso: str, location: str = '', description: str = '') -> dict[str, Any]:
        service = self._service(interactive=False)
        if service is None:
            raise RuntimeError('Google Calendar backup is not connected.')
        body = {
            'summary': summary,
            'start': {'dateTime': start_iso},
            'end': {'dateTime': end_iso},
        }
        if location:
            body['location'] = location
        if description:
            body['description'] = description
        event = service.events().insert(calendarId='primary', body=body).execute()
        return {'id': event.get('id'), 'summary': event.get('summary'), 'htmlLink': event.get('htmlLink'), 'start': (event.get('start') or {}).get('dateTime'), 'source': 'google'}
