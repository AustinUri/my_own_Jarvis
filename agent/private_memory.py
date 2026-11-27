"""Desktop-only, OS-user-scoped memory. Nothing in this module contacts a network."""
from __future__ import annotations

import ctypes
import hashlib
import hmac
import json
import os
import re
import sqlite3
import uuid
import zipfile
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from cloud_core.app.memory_text import memory_tokens


_SHARD = re.compile(r"conversations(?:[-_]\d+)?\.json\Z")
_MAX_SHARD = 128 * 1024 * 1024
_MAX_TOTAL = 512 * 1024 * 1024
_LOCAL_PREFIX = "jarvis-turn:"


@dataclass(frozen=True, repr=False)
class ConversationInfo:
    id: str
    title: str
    project_id: str | None


@dataclass(frozen=True, repr=False)
class ExportPreview:
    path: Path
    conversations: tuple[ConversationInfo, ...]
    project_ids: tuple[str, ...]
    fingerprint: bytes = field(repr=False)


def _valid_id(value):
    return isinstance(value, str) and 0 < len(value) <= 256 and value.strip() == value and value.isprintable()


def _collection(value: str) -> str:
    if not isinstance(value, str) or (value != "" and not _valid_id(value)):
        raise ValueError("Choose a valid local collection.")
    return value


def _read_member(stream, size, total):
    if size > _MAX_SHARD or total + size > _MAX_TOTAL:
        raise ValueError("The conversations export exceeds the local preview size limit.")
    data = stream.read(size + 1)
    if len(data) != size:
        raise ValueError("The conversations export changed. Preview it again.")
    return data


def _export_members(path: Path):
    total = 0
    if path.is_symlink():
        raise ValueError("Select the original local export.")
    if path.is_dir():
        files = sorted(p for p in path.iterdir() if _SHARD.fullmatch(p.name))
    elif path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = sorted((m for m in archive.infolist() if _SHARD.fullmatch(m.filename)),
                             key=lambda m: m.filename)
            if not members or len(members) > 1024 or len({m.filename for m in members}) != len(members):
                raise ValueError("Expected unique conversations JSON files at the root of the export.")
            for member in members:
                with archive.open(member) as stream:
                    data = _read_member(stream, member.file_size, total)
                total += len(data)
                yield member.filename, data
        return
    elif path.suffix.lower() == ".json":
        files = [path]
    else:
        files = []
    if not files or len(files) > 1024:
        raise ValueError("Choose conversations JSON, its export folder, or the original ZIP.")
    for member in files:
        if member.is_symlink() or not member.is_file():
            raise ValueError("The export contains an unsupported conversation file.")
        with member.open("rb") as stream:
            data = _read_member(stream, os.fstat(stream.fileno()).st_size, total)
        total += len(data)
        yield member.name, data


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError("The export contains ambiguous JSON fields.")
        fields[key] = value
    return fields


def _visible_messages(record):
    nodes = record.get("mapping")
    current = record.get("current_node")
    if not isinstance(nodes, dict) or not _valid_id(current):
        raise ValueError("A selected conversation has no identifiable active branch.")
    seen = set()
    messages = []
    while current is not None:
        if not _valid_id(current) or current in seen or not isinstance(nodes.get(current), dict):
            raise ValueError("A selected conversation has an ambiguous message branch.")
        seen.add(current)
        node = nodes[current]
        if node.get("id", current) != current or "parent" not in node:
            raise ValueError("A selected conversation has incomplete branch metadata.")
        current = node["parent"]
        msg = node.get("message")
        if not isinstance(msg, dict):
            continue
        author, content, metadata = msg.get("author"), msg.get("content"), msg.get("metadata", {})
        if not all(isinstance(v, dict) for v in (author, content, metadata)):
            continue
        role = author.get("role")
        if (role not in ("user", "assistant") or msg.get("recipient", "all") != "all"
                or metadata.get("is_visually_hidden_from_conversation") or metadata.get("attachments")
                or msg.get("channel") not in (None, "final") or content.get("content_type") != "text"):
            continue
        parts = content.get("parts")
        if isinstance(parts, list) and all(isinstance(part, str) for part in parts):
            body = "\n".join(parts).strip()
            if body:
                messages.append({"role": role, "content": body})
    if not messages:
        raise ValueError("A selected conversation contains no supported visible text.")
    return list(reversed(messages))


def _scan(path, selected=()):
    digest = hashlib.sha256()
    info, messages = {}, {}
    for name, data in _export_members(path):
        digest.update(name.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
        try:
            records = json.loads(data, object_pairs_hook=_unique_fields)
        except (UnicodeError, json.JSONDecodeError, RecursionError):
            raise ValueError("The conversations JSON cannot be read.") from None
        if not isinstance(records, list):
            raise ValueError("Expected a ChatGPT conversations JSON array.")
        for record in records:
            if not isinstance(record, dict):
                continue
            key = record.get("conversation_id", record.get("id"))
            if not _valid_id(key) or key.startswith(_LOCAL_PREFIX):
                continue
            if record.get("id", key) != key or key in info:
                raise ValueError("Conflicting conversation identities. Use one unambiguous export.")
            project = record.get("project_id")
            if not _valid_id(project):
                project = None
            nested = record.get("project")
            if isinstance(nested, dict) and nested.get("id", project) != project:
                project = None
            title = record.get("title")
            title = " ".join(title.split())[:300] if isinstance(title, str) else ""
            info[key] = ConversationInfo(key, title or "Untitled conversation", project)
            if key in selected:
                updated = record.get("update_time")
                if type(updated) not in (int, float) or not 0 < updated < 1e12:
                    updated = None
                messages[key] = (_visible_messages(record), updated)
    return digest.digest(), info, messages


def preview_export(path) -> ExportPreview:
    path = Path(path).absolute()
    digest, info, _ = _scan(path)
    projects = tuple(sorted({c.project_id for c in info.values() if c.project_id}))
    return ExportPreview(path, tuple(info.values()), projects, digest)


def _os_principal() -> str:
    if os.name != "nt":
        return f"uid:{os.geteuid()}"
    # The Windows SID stays bound to the account across renames and display-name reuse.
    security = ctypes.windll.advapi32
    effective_token = ctypes.c_void_p(-6)  # GetCurrentThreadEffectiveToken() pseudo-handle.
    token_user = 1
    size = ctypes.c_ulong()
    security.GetTokenInformation(effective_token, token_user, None, 0, ctypes.byref(size))
    if not size.value:
        raise PermissionError("Windows could not identify the signed-in user.")
    user = ctypes.create_string_buffer(size.value)
    if not security.GetTokenInformation(effective_token, token_user, user, size, ctypes.byref(size)):
        raise PermissionError("Windows could not identify the signed-in user.")
    sid = ctypes.c_void_p.from_buffer(user)
    return "sid:" + ctypes.string_at(sid, security.GetLengthSid(sid)).hex()


def _default_db():
    base = Path.home() / ("AppData/Local" if os.name == "nt" else ".local/share")
    return base / "Jarvis" / "private-ai" / "memory.sqlite3"


class PrivateMemory:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else _default_db()
        self._owner = _os_principal()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise PermissionError("The private memory file cannot be a symbolic link.")
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            if os.name != "nt":
                metadata = os.fstat(fd)
                if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
                    raise PermissionError("The private memory file must be accessible only to its owner.")
        finally:
            os.close(fd)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS conversations (
                owner TEXT NOT NULL, project TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL,
                messages TEXT NOT NULL, source_updated REAL, PRIMARY KEY(owner, project, id))""")

    @contextmanager
    def _db(self):
        if self._owner != _os_principal():
            raise PermissionError("The active operating-system user changed.")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA secure_delete = ON")
            yield db

    def import_selected(self, preview, *, conversation_ids=(), project_ids=(), destination, owner_confirmed):
        project = _collection(destination)
        if owner_confirmed is not True:
            raise PermissionError("Confirm ownership of every selected conversation before importing.")
        ids, projects = set(conversation_ids), set(project_ids)
        known = {c.id: c for c in preview.conversations}
        if not ids.issubset(known) or not projects.issubset(preview.project_ids):
            raise ValueError("Choose conversations and projects shown in this preview.")
        if projects:
            if len(projects) != 1 or not project or any(known[key].project_id not in projects for key in ids):
                raise ValueError("Import one whole project into a named collection at a time.")
            ids.update(c.id for c in known.values() if c.project_id in projects)
        if not ids:
            raise ValueError("Select at least one conversation or project.")
        digest, current, messages = _scan(preview.path, ids)
        if not hmac.compare_digest(preview.fingerprint, digest) or not ids.issubset(messages):
            raise ValueError("The export changed after preview. Review it again.")
        # Repeat the project membership check against the reopened source.
        if projects and any(current[key].project_id not in projects for key in ids):
            raise ValueError("Project membership changed. Review the export again.")
        with self._db() as db:
            before = db.total_changes
            for key in sorted(ids):
                visible, updated = messages[key]
                db.execute("""INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(owner, project, id) DO UPDATE SET title=excluded.title, messages=excluded.messages,
                        source_updated=excluded.source_updated
                    WHERE (source_updated IS NULL OR excluded.source_updated >= source_updated)
                        AND (title != excluded.title OR messages != excluded.messages
                             OR source_updated IS NOT excluded.source_updated)""",
                           (self._owner, project, key, current[key].title,
                            json.dumps(visible, ensure_ascii=False), updated))
            return db.total_changes - before

    def collections(self):
        with self._db() as db:
            names = db.execute("SELECT DISTINCT project FROM conversations WHERE owner=? ORDER BY project",
                               (self._owner,))
            return ["", *(row[0] for row in names if row[0])]

    def list_conversations(self, project):
        with self._db() as db:
            return [ConversationInfo(key, title, project or None) for key, title in db.execute(
                "SELECT id, title FROM conversations WHERE owner=? AND project=? ORDER BY title, id",
                (self._owner, _collection(project)))]

    def read_conversation(self, project, id):
        with self._db() as db:
            row = db.execute("SELECT messages FROM conversations WHERE owner=? AND project=? AND id=?",
                             (self._owner, _collection(project), id)).fetchone()
        if row is None:
            raise KeyError("Conversation not found in this collection.")
        return json.loads(row[0])

    def delete_conversation(self, project, id):
        with self._db() as db:
            return bool(db.execute("DELETE FROM conversations WHERE owner=? AND project=? AND id=?",
                                   (self._owner, _collection(project), id)).rowcount)

    def save_turn(self, project, question, answer, *, enabled):
        if enabled is not True:
            return
        messages = [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
        with self._db() as db:
            db.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?, NULL)",
                       (self._owner, _collection(project), _LOCAL_PREFIX + str(uuid.uuid4()),
                        question[:100], json.dumps(messages, ensure_ascii=False)))

    def context(self, project, question):
        project = _collection(project)
        best = []
        with self._db() as db:
            terms = memory_tokens(question)
            if not terms:
                return ""
            rows = db.execute("SELECT messages FROM conversations WHERE owner=? AND project=? ORDER BY rowid DESC",
                              (self._owner, project))
            for (raw,) in rows:
                for msg in json.loads(raw):
                    content = msg["content"]
                    # Score bounded excerpts so a long message cannot disclose its unrelated tail.
                    for offset in range(0, len(content), 420):
                        excerpt = content[offset:offset + 420]
                        score = len(terms & memory_tokens(excerpt))
                        if score and all(excerpt != entry[1] for entry in best):
                            best.append((score, excerpt))
                            best.sort(key=lambda entry: entry[0], reverse=True)
                            del best[3:]
        return "\n".join(text for _, text in best)

    def export_user(self, path):
        target = Path(path).resolve()
        if any((parent / ".git").exists() for parent in target.parents):
            raise PermissionError("Choose a private export location outside a Git repository.")
        with self._db() as db:
            rows = db.execute("SELECT project, id, title, messages FROM conversations WHERE owner=? ORDER BY project,id",
                              (self._owner,))
            result = [{"project": project, "id": key, "title": title, "messages": json.loads(raw)}
                      for project, key, title, raw in rows]
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)

    def delete_user(self):
        with self._db() as db:
            db.execute("DELETE FROM conversations WHERE owner=?", (self._owner,))
