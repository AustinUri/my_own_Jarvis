from __future__ import annotations

from datetime import datetime
from pathlib import Path


def create_note(notes_dir: Path, content: str) -> str:
    notes_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = notes_dir / f"note_{timestamp}.txt"
    body = content.strip() or "Empty note"
    path.write_text(body, encoding="utf-8")
    return f"Created note: {path.name}"
