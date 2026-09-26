from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.user_paths import jarvis_data_dir


_ALLOWED_SUFFIXES = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.kt', '.kts', '.json', '.md', '.txt',
    '.html', '.css', '.scss', '.xml', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.ps1', '.cmd',
    '.bat', '.sh', '.properties', '.gradle', '.sql', '.csv', '.c', '.cc', '.cpp', '.h', '.hpp'
}
_SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.gradle', 'build', 'dist', 'models', 'downloads'}


@dataclass
class CodingStatus:
    ready: bool
    workspace: str
    branch: str = ''
    dirty: bool = False
    changed_files: int = 0
    source: str = ''
    mode: str = 'assisted'
    message: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'ready': self.ready,
            'workspace': self.workspace,
            'branch': self.branch,
            'dirty': self.dirty,
            'changed_files': self.changed_files,
            'source': self.source,
            'mode': self.mode,
            'message': self.message,
        }


class CodingJarvisService:
    """Safe local-first software-engineering workspace for JARVIS.

    Coding JARVIS never edits the currently-running JARVIS installation. It works
    inside a separate Git clone under the user's JARVIS data directory. The model
    gets narrow read/search/patch/test/commit tools instead of unrestricted shell.
    """

    def __init__(self, repo_url: str = 'https://github.com/AustinUri/my_own_Jarvis.git', mode: str = 'assisted') -> None:
        self.repo_url = repo_url
        self.mode = mode if mode in {'review', 'assisted'} else 'assisted'
        self.root = jarvis_data_dir() / 'coding' / 'my_own_Jarvis-dev'
        self.root.parent.mkdir(parents=True, exist_ok=True)

    def _run(self, args: list[str], *, timeout: float = 45.0, input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=self.root if self.root.exists() else self.root.parent,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            shell=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )

    def _git(self, *args: str, timeout: float = 45.0, input_text: str | None = None) -> subprocess.CompletedProcess:
        return self._run(['git', *args], timeout=timeout, input_text=input_text)

    def ensure_workspace(self, refresh: bool = False) -> dict[str, Any]:
        try:
            if not (self.root / '.git').exists():
                if self.root.exists():
                    shutil.rmtree(self.root, ignore_errors=True)
                cp = subprocess.run(
                    ['git', 'clone', self.repo_url, str(self.root)],
                    cwd=self.root.parent,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    shell=False,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
                if cp.returncode != 0:
                    return {'ok': False, 'error': (cp.stderr or cp.stdout or 'Git clone failed.')[-1600:]}
            if refresh:
                self._git('fetch', '--all', '--prune', timeout=90)
                # Do not reset local edits. Update only when clean.
                st = self._git('status', '--porcelain')
                if st.returncode == 0 and not st.stdout.strip():
                    self._git('pull', '--ff-only', timeout=90)
            # Always keep coding work off main.
            branch = self._git('branch', '--show-current')
            current = branch.stdout.strip() if branch.returncode == 0 else ''
            if current in {'', 'main', 'master'}:
                existing = self._git('branch', '--list', 'jarvis-v29-dev')
                if 'jarvis-v29-dev' in existing.stdout:
                    self._git('switch', 'jarvis-v29-dev')
                else:
                    self._git('switch', '-c', 'jarvis-v29-dev')
            out = self.status()
            out['ok'] = bool(out.get('ready'))
            return out
        except FileNotFoundError:
            return {'ok': False, 'error': 'Git is not installed or not available on PATH.'}
        except subprocess.TimeoutExpired:
            return {'ok': False, 'error': 'Git operation timed out.'}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def status(self) -> dict[str, Any]:
        if not (self.root / '.git').exists():
            return CodingStatus(False, str(self.root), source=self.repo_url, mode=self.mode,
                                message='Coding workspace has not been prepared yet.').to_dict()
        branch = self._git('branch', '--show-current')
        st = self._git('status', '--porcelain')
        rows = [x for x in (st.stdout or '').splitlines() if x.strip()]
        return CodingStatus(
            True,
            str(self.root),
            branch=(branch.stdout or '').strip(),
            dirty=bool(rows),
            changed_files=len(rows),
            source=self.repo_url,
            mode=self.mode,
            message='Coding JARVIS works only in this development clone; the running stable build is untouched.',
        ).to_dict()

    def _safe_path(self, relative: str) -> Path:
        rel = str(relative or '').replace('\\', '/').lstrip('/')
        if not rel or '..' in Path(rel).parts:
            raise ValueError('Unsafe or empty repository path.')
        target = (self.root / rel).resolve()
        base = self.root.resolve()
        try:
            target.relative_to(base)
        except ValueError as exc:
            raise ValueError('Path escapes the Coding JARVIS workspace.') from exc
        return target

    def search(self, query: str, limit: int = 40) -> dict[str, Any]:
        query = (query or '').strip()
        if not query:
            return {'ok': False, 'error': 'Search query is empty.'}
        ready = self.ensure_workspace(False)
        if not ready.get('ok'):
            return ready

        # v29.2: search is still local/deterministic, but it is no longer one
        # exact phrase only. Natural requests such as "Surface browser
        # implementation" fan out to meaningful code tokens/symbols.
        raw_terms = [query.lower()]
        words = [w for w in re.findall(r'[a-z0-9_.-]{3,}', query.lower()) if w not in {
            'implementation','code','find','search','where','show','file','files','the','for','and','with'
        }]
        raw_terms.extend(words)
        ql = query.lower()
        if 'surface' in ql or 'browser' in ql or 'webview' in ql:
            raw_terms.extend(['native_surface','integrated_shell','qwebengineview','surface_view','surface_controller'])
        if 'phone' in ql or 'android' in ql:
            raw_terms.extend(['phonebridge','phoneapiclient','jarvisforegroundservice','contactsbridge'])
        terms = list(dict.fromkeys(t for t in raw_terms if t))

        scored: list[tuple[int, dict[str, Any]]] = []
        cap = max(1, min(100, int(limit)))
        for path in self.root.rglob('*'):
            if not path.is_file() or any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in _ALLOWED_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 1_500_000:
                    continue
                text = path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            lower = text.lower()
            rel = str(path.relative_to(self.root)).replace('\\', '/')
            rel_lower = rel.lower()
            best_idx = -1
            score = 0
            matched: list[str] = []
            for term in terms:
                idx = lower.find(term)
                in_path = term in rel_lower
                if idx >= 0 or in_path:
                    matched.append(term)
                    score += 5 if term == ql else 1
                    if in_path: score += 2
                    if best_idx < 0 and idx >= 0: best_idx = idx
            if not matched:
                continue
            line_no = lower[:max(0, best_idx)].count('\n') + 1 if best_idx >= 0 else 1
            start = max(0, best_idx - 180) if best_idx >= 0 else 0
            snippet = text[start:start + 520].replace('\x00', '')
            scored.append((score, {'path': rel, 'line': line_no, 'snippet': snippet, 'matched': matched[:8]}))
        scored.sort(key=lambda item: (-item[0], item[1]['path']))
        hits = [row for _score, row in scored[:cap]]
        return {'ok': True, 'query': query, 'terms': terms, 'hits': hits, 'count': len(hits)}

    def read_file(self, path: str, start_line: int = 1, max_lines: int = 220) -> dict[str, Any]:
        ready = self.ensure_workspace(False)
        if not ready.get('ok'):
            return ready
        try:
            target = self._safe_path(path)
            if not target.exists() or not target.is_file():
                return {'ok': False, 'error': f'File not found: {path}'}
            if target.stat().st_size > 2_000_000:
                return {'ok': False, 'error': 'File is too large for Coding JARVIS read mode.'}
            lines = target.read_text(encoding='utf-8', errors='replace').splitlines()
            start = max(1, int(start_line))
            amount = max(1, min(500, int(max_lines)))
            selected = lines[start - 1:start - 1 + amount]
            numbered = '\n'.join(f'{i}: {line}' for i, line in enumerate(selected, start=start))
            return {'ok': True, 'path': path, 'start_line': start, 'end_line': start + len(selected) - 1, 'content': numbered}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def apply_patch(self, patch: str) -> dict[str, Any]:
        if self.mode == 'review':
            return {'ok': False, 'error': 'Coding JARVIS is in review-only mode.'}
        ready = self.ensure_workspace(False)
        if not ready.get('ok'):
            return ready
        raw = patch or ''
        if len(raw) > 120_000:
            return {'ok': False, 'error': 'Patch is too large for one assisted change.'}
        if '../' in raw.replace('\\', '/') or re.search(r'^\+\+\+\s+/', raw, re.MULTILINE):
            return {'ok': False, 'error': 'Patch contains an unsafe path.'}
        if not ('--- ' in raw and '+++ ' in raw):
            return {'ok': False, 'error': 'Expected a unified diff patch.'}
        cp = self._git('apply', '--whitespace=fix', '-', timeout=40, input_text=raw)
        if cp.returncode != 0:
            return {'ok': False, 'error': (cp.stderr or cp.stdout or 'git apply failed.')[-2400:]}
        return {'ok': True, 'message': 'Patch applied in the isolated dev workspace.', 'status': self.status(), 'diff': self.diff(10000)}

    def diff(self, max_chars: int = 16000) -> dict[str, Any]:
        ready = self.ensure_workspace(False)
        if not ready.get('ok'):
            return ready
        stat = self._git('diff', '--stat')
        diff = self._git('diff', '--no-ext-diff', '--unified=3')
        text = diff.stdout or ''
        limit = max(1000, min(50000, int(max_chars)))
        return {'ok': True, 'stat': (stat.stdout or '').strip(), 'diff': text[:limit], 'truncated': len(text) > limit}

    def run_checks(self) -> dict[str, Any]:
        ready = self.ensure_workspace(False)
        if not ready.get('ok'):
            return ready
        checks: list[dict[str, Any]] = []

        def record(name: str, args: list[str], timeout: float = 90.0) -> None:
            try:
                cp = self._run(args, timeout=timeout)
                checks.append({'name': name, 'ok': cp.returncode == 0, 'output': ((cp.stdout or '') + (cp.stderr or ''))[-5000:]})
            except Exception as exc:
                checks.append({'name': name, 'ok': False, 'output': str(exc)})

        # Compile without installing anything new.
        py_files = [str(p) for p in self.root.rglob('*.py') if not any(part in _SKIP_DIRS for part in p.parts)]
        if py_files:
            record('python-syntax', ['python', '-m', 'compileall', '-q', str(self.root)], 120)
        js = self.root / 'workspace_ui' / 'dist' / 'workspace.js'
        if js.exists() and shutil.which('node'):
            record('workspace-js', ['node', '--check', str(js)], 30)
        record('git-diff-check', ['git', 'diff', '--check'], 30)
        return {'ok': all(c['ok'] for c in checks), 'checks': checks, 'status': self.status()}

    def commit(self, message: str) -> dict[str, Any]:
        if self.mode == 'review':
            return {'ok': False, 'error': 'Coding JARVIS is in review-only mode.'}
        ready = self.ensure_workspace(False)
        if not ready.get('ok'):
            return ready
        msg = ' '.join((message or '').split())[:180]
        if not msg:
            return {'ok': False, 'error': 'Commit message is empty.'}
        self._git('add', '-A')
        cp = self._git('commit', '-m', msg, timeout=60)
        if cp.returncode != 0:
            return {'ok': False, 'error': (cp.stderr or cp.stdout or 'Git commit failed.')[-2200:]}
        head = self._git('rev-parse', '--short', 'HEAD')
        return {'ok': True, 'commit': (head.stdout or '').strip(), 'message': msg, 'status': self.status()}
