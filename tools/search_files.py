from __future__ import annotations

from pathlib import Path


SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}


def search_files(base_dir: Path, query: str) -> str:
    q = query.lower().strip()
    if not q:
        return "No search query was provided."

    matches: list[str] = []
    for path in base_dir.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and q in path.name.lower():
            matches.append(str(path.relative_to(base_dir)))
            if len(matches) >= 5:
                break

    if not matches:
        return f"No files found for '{query}'."
    return "Found files: " + ", ".join(matches)
