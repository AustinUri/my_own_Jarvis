from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = (
    Path(os.environ.get("LOCALAPPDATA", Path.home()))
    / "Jarvis"
    / "claude_project_memory.sqlite3"
)

class ClaudeProjectMemory:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or DEFAULT_DB).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    def _ensure(self):
        with closing(self._connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    query TEXT NOT NULL,
                    result TEXT NOT NULL,
                    files_json TEXT NOT NULL DEFAULT '[]'
                )
            """)
            try:
                db.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
                    USING fts5(query, result, content='observations', content_rowid='id')
                """)
                db.executescript("""
                    CREATE TRIGGER IF NOT EXISTS obs_ai AFTER INSERT ON observations BEGIN
                      INSERT INTO observations_fts(rowid, query, result)
                      VALUES (new.id, new.query, new.result);
                    END;
                    CREATE TRIGGER IF NOT EXISTS obs_ad AFTER DELETE ON observations BEGIN
                      INSERT INTO observations_fts(observations_fts, rowid, query, result)
                      VALUES('delete', old.id, old.query, old.result);
                    END;
                    CREATE TRIGGER IF NOT EXISTS obs_au AFTER UPDATE ON observations BEGIN
                      INSERT INTO observations_fts(observations_fts, rowid, query, result)
                      VALUES('delete', old.id, old.query, old.result);
                      INSERT INTO observations_fts(rowid, query, result)
                      VALUES (new.id, new.query, new.result);
                    END;
                """)
            except sqlite3.OperationalError:
                pass

    def remember(self, mode: str, query: str, result: str, files: list[str] | None = None):
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO observations(created_at,mode,query,result,files_json) VALUES(?,?,?,?,?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    mode[:40],
                    query[:12000],
                    result[:30000],
                    json.dumps(files or [], ensure_ascii=False),
                ),
            )

    def search(self, query: str, limit: int = 5) -> list[dict]:
        clean = (query or "").strip()
        if not clean:
            return []
        limit = max(1, min(int(limit), 10))
        with closing(self._connect()) as db:
            try:
                rows = db.execute(
                    """
                    SELECT o.id,o.created_at,o.mode,o.query,o.result,o.files_json
                    FROM observations_fts f
                    JOIN observations o ON o.id=f.rowid
                    WHERE observations_fts MATCH ?
                    ORDER BY bm25(observations_fts)
                    LIMIT ?
                    """,
                    (clean.replace('"', ' '), limit),
                ).fetchall()
            except sqlite3.OperationalError:
                like = f"%{clean[:120]}%"
                rows = db.execute(
                    """
                    SELECT id,created_at,mode,query,result,files_json
                    FROM observations
                    WHERE query LIKE ? OR result LIKE ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (like, like, limit),
                ).fetchall()
        return [dict(r) for r in rows]

    def context(self, query: str, limit: int = 4) -> str:
        hits = self.search(query, limit=limit)
        if not hits:
            return ""
        chunks = ["Relevant prior JARVIS project observations:"]
        for h in hits:
            chunks.append(
                f"- [{h['mode']}] {h['query'][:220]}\n  Result: {h['result'][:700]}"
            )
        return "\n".join(chunks)

memory = ClaudeProjectMemory()
