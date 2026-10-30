from __future__ import annotations
import json, sqlite3
from pathlib import Path
from .config import DB_PATH
from .models import FirstReadReport

class ReportStore:
    def __init__(self,path=DB_PATH):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self._init()

    def _connect(self):
        return sqlite3.connect(str(self.path),timeout=20)

    def _init(self):
        con=self._connect()
        try:
            con.execute(
                "CREATE TABLE IF NOT EXISTS reports("
                "report_id TEXT PRIMARY KEY,"
                "created_at TEXT NOT NULL,"
                "language TEXT NOT NULL,"
                "relationship_type TEXT NOT NULL,"
                "report_json TEXT NOT NULL)"
            )
            con.commit()
        finally:
            con.close()

    def save(self,r: FirstReadReport):
        con=self._connect()
        try:
            con.execute(
                "INSERT OR REPLACE INTO reports VALUES(?,?,?,?,?)",
                (r.report_id,r.created_at.isoformat(),r.language,r.relationship_type,r.model_dump_json()),
            )
            con.commit()
        finally:
            con.close()

    def get(self,rid):
        con=self._connect()
        try:
            row=con.execute("SELECT report_json FROM reports WHERE report_id=?",(rid,)).fetchone()
            return json.loads(row[0]) if row else None
        finally:
            con.close()

    def delete(self,rid):
        con=self._connect()
        try:
            cur=con.execute("DELETE FROM reports WHERE report_id=?",(rid,))
            con.commit()
            return cur.rowcount>0
        finally:
            con.close()
