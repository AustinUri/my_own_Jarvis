from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.user_paths import profiles_dir


class WorkspaceProfileStore:
    def __init__(self):
        self.root = profiles_dir()

    @staticmethod
    def _safe(name: str) -> str:
        cleaned = re.sub(r'[^A-Za-z0-9 _.-]+', '', name).strip().strip('.')
        return cleaned[:80] or 'Workspace'

    def list(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for path in sorted(self.root.glob('*.json')):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                name = str(data.get('name') or path.stem)
                out[name] = data
            except Exception:
                continue
        return out

    def save(self, name: str, data: dict[str, Any]) -> dict[str, Any]:
        safe = self._safe(name)
        payload = dict(data)
        payload['name'] = safe
        path = self.root / f'{safe}.json'
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return payload

    def delete(self, name: str) -> bool:
        path = self.root / f'{self._safe(name)}.json'
        if path.exists():
            path.unlink()
            return True
        return False
