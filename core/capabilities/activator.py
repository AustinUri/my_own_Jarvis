from __future__ import annotations

import argparse
import json
import hashlib
import re
import shutil
from pathlib import Path

from core.capabilities.registry import get_capability
from core.capabilities.status import capability_state


ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / ".jarvis" / "skill-fabric" / "packs"
INDEX = PACKS / "_skill-index.json"
SKILLS_DIR = ROOT / ".claude" / "skills"
ACTIVE_MANIFEST = ROOT / ".jarvis" / "skill-fabric" / "active.json"

MANAGED_PREFIX = "jarvis-"


class ActivationError(RuntimeError):
    pass


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "skill"


def _load_index() -> list[dict]:
    if not INDEX.exists():
        raise ActivationError(f"Skill index not found: {INDEX}")

    data = json.loads(INDEX.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ActivationError("Skill index has invalid format")

    return data


def _load_manifest() -> dict:
    if not ACTIVE_MANIFEST.exists():
        return {"active": []}

    try:
        data = json.loads(ACTIVE_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return {"active": []}

    if not isinstance(data, dict):
        return {"active": []}

    data.setdefault("active", [])
    return data


def _save_manifest(data: dict) -> None:
    ACTIVE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_MANIFEST.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _pack_id(capability_name: str) -> str:
    capability = get_capability(capability_name)

    if capability is None:
        raise ActivationError(
            f"Unknown capability: {capability_name}"
        )

    if capability.local_path is None:
        raise ActivationError(
            f"{capability_name} has no local skill pack"
        )

    return capability.local_path.name


def _project_source(capability_name: str) -> Path | None:
    capability = get_capability(capability_name)
    if capability is None or getattr(capability, "source", None) != "jarvis-project":
        return None
    if not capability.enabled or capability.local_path is None:
        raise ActivationError(f"Project skill disabled or has no path: {capability_name}")
    path = capability.local_path.resolve()
    try:
        path.relative_to((ROOT / "skills").resolve())
    except ValueError as exc:
        raise ActivationError("Project skill escapes repository skills directory") from exc
    if not (path / "SKILL.md").is_file():
        raise ActivationError(f"Project SKILL.md missing: {path}")
    return path


def _hash_files(path: Path, *, marker: str = ".jarvis-project-skill.json") -> dict[str, str]:
    files = {}
    for file in sorted(path.rglob("*")):
        if file.is_symlink():
            raise ActivationError("Project skill contains a symbolic link")
        if file.is_file() and file.name != marker:
            files[file.relative_to(path).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    return files


def skills_for(capability_name: str) -> list[dict]:
    local = _project_source(capability_name)
    if local is not None:
        return [{"name": capability_name, "source": "jarvis-project",
                 "path": str((local / "SKILL.md").relative_to(ROOT).as_posix())}]
    pack_id = _pack_id(capability_name)

    return [
        item
        for item in _load_index()
        if item.get("source") == pack_id
        and item.get("path", "").endswith("SKILL.md")
    ]


def _resolve_skill(
    capability_name: str,
    requested_skill: str | None,
) -> dict:
    candidates = skills_for(capability_name)

    if not candidates:
        raise ActivationError(
            f"No SKILL.md definitions found for {capability_name}"
        )

    if requested_skill is None:
        if len(candidates) == 1:
            return candidates[0]

        names = sorted(
            str(item.get("name", "unknown"))
            for item in candidates
        )

        raise ActivationError(
            f"{capability_name} contains {len(candidates)} skills. "
            f"Choose one explicitly:\n  "
            + "\n  ".join(names)
        )

    needle = requested_skill.strip().lower()

    exact = [
        item
        for item in candidates
        if str(item.get("name", "")).strip().lower() == needle
    ]

    if len(exact) == 1:
        return exact[0]

    slug_matches = [
        item
        for item in candidates
        if _slug(str(item.get("name", ""))) == _slug(needle)
    ]

    if len(slug_matches) == 1:
        return slug_matches[0]

    partial = [
        item
        for item in candidates
        if needle in str(item.get("name", "")).lower()
    ]

    if len(partial) == 1:
        return partial[0]

    if len(partial) > 1:
        raise ActivationError(
            "Skill name is ambiguous:\n  "
            + "\n  ".join(
                sorted(str(item.get("name")) for item in partial)
            )
        )

    raise ActivationError(
        f"No skill matching '{requested_skill}' "
        f"inside {capability_name}"
    )


def activate(
    capability_name: str,
    requested_skill: str | None = None,
) -> Path:
    local = _project_source(capability_name)
    if local is None:
        state = capability_state(capability_name)
        if state != "ready":
            raise ActivationError(
                f"{capability_name} is not ready: state={state}"
            )

    entry = _resolve_skill(
        capability_name,
        requested_skill,
    )

    relative_skill_file = Path(entry["path"])
    if local is not None:
        source_dir = local
    else:
        source_dir = PACKS / relative_skill_file.parent
        resolved_source = source_dir.resolve()
        resolved_packs = PACKS.resolve()
        try:
            resolved_source.relative_to(resolved_packs)
        except ValueError as exc:
            raise ActivationError(
                "Skill path escapes harvested pack directory"
            ) from exc

    if not source_dir.exists():
        raise ActivationError(
            f"Skill source directory missing: {source_dir}"
        )

    if not (source_dir / "SKILL.md").exists():
        raise ActivationError(
            f"SKILL.md missing from: {source_dir}"
        )

    skill_name = str(entry.get("name") or source_dir.name)

    destination_name = (
        f"{MANAGED_PREFIX}"
        f"{_slug(capability_name)}-"
        f"{_slug(skill_name)}"
    )

    destination = SKILLS_DIR / destination_name

    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    if local is not None:
        # First-party skills have a dedicated name and refuse to clobber edits.
        destination_name = "jarvis-project-" + _slug(capability_name)
        destination = SKILLS_DIR / destination_name
        marker = ".jarvis-project-skill.json"
        source_hashes = _hash_files(source_dir)
        if destination.exists():
            recorded_path = destination / marker
            if not recorded_path.is_file():
                raise ActivationError(f"Existing project skill is not managed: {destination}")
            recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
            if recorded.get("source") != capability_name or recorded.get("hashes") != _hash_files(destination):
                raise ActivationError(f"Project skill was locally edited; refusing overwrite: {destination}")
        # Copy to staging and then replace to avoid incomplete skill activation.
        staging = SKILLS_DIR / (destination_name + ".installing")
        if staging.exists():
            raise ActivationError(f"Stale activation staging directory: {staging}")
        shutil.copytree(source_dir, staging)
        (staging / marker).write_text(
            json.dumps({"source": capability_name, "hashes": source_hashes}, indent=2),
            encoding="utf-8",
        )
        if destination.exists():
            backup = SKILLS_DIR / (destination_name + ".previous")
            if backup.exists():
                shutil.rmtree(staging)
                raise ActivationError(f"Previous activation backup exists: {backup}")
            destination.rename(backup)
            try:
                staging.rename(destination)
            except Exception:
                backup.rename(destination)
                raise
            shutil.rmtree(backup)
        else:
            staging.rename(destination)
    else:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source_dir, destination)

    manifest = _load_manifest()

    manifest["active"] = [
        item
        for item in manifest["active"]
        if item.get("destination") != destination_name
    ]

    manifest["active"].append(
        {
            "capability": capability_name,
            "skill": skill_name,
            "source": str(relative_skill_file),
            "destination": destination_name,
        }
    )

    _save_manifest(manifest)

    return destination


def deactivate_all() -> int:
    manifest = _load_manifest()
    removed = 0

    for item in manifest.get("active", []):
        destination_name = item.get("destination")

        if not destination_name:
            continue

        if not destination_name.startswith(MANAGED_PREFIX):
            continue

        destination = SKILLS_DIR / destination_name

        if destination.exists():
            shutil.rmtree(destination)
            removed += 1

    _save_manifest({"active": []})

    return removed


def status() -> list[dict]:
    manifest = _load_manifest()
    result = []

    for item in manifest.get("active", []):
        destination_name = item.get("destination", "")
        destination = SKILLS_DIR / destination_name

        row = dict(item)
        row["present"] = (
            destination.exists()
            and (destination / "SKILL.md").exists()
        )

        result.append(row)

    return result


def catalog(capability_name: str) -> list[dict]:
    return skills_for(capability_name)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="jarvis-skills",
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    catalog_parser = sub.add_parser("catalog")
    catalog_parser.add_argument("capability")

    activate_parser = sub.add_parser("activate")
    activate_parser.add_argument("capability")
    activate_parser.add_argument(
        "skill",
        nargs="?",
    )

    sub.add_parser("status")
    sub.add_parser("deactivate-all")

    args = parser.parse_args()

    try:
        if args.command == "catalog":
            items = catalog(args.capability)

            print(
                f"{args.capability}: "
                f"{len(items)} skill(s)"
            )

            for item in items:
                print(
                    f"- {item.get('name')} "
                    f"[{item.get('path')}]"
                )

            return 0

        if args.command == "activate":
            destination = activate(
                args.capability,
                args.skill,
            )

            print(f"Activated: {destination}")
            return 0

        if args.command == "deactivate-all":
            count = deactivate_all()
            print(f"Deactivated: {count}")
            return 0

        if args.command == "status":
            items = status()

            if not items:
                print("No JARVIS-managed skills active.")
                return 0

            for item in items:
                state = "OK" if item["present"] else "MISSING"

                print(
                    f"{state}  "
                    f"{item['capability']} -> "
                    f"{item['skill']} "
                    f"({item['destination']})"
                )

            return 0

    except ActivationError as exc:
        print(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
