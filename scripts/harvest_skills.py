from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path.cwd()
FABRIC = ROOT / ".jarvis" / "skill-fabric"
PACKS = FABRIC / "packs"
TMP = FABRIC / ".harvest-tmp"
BACKUPS = ROOT / ".jarvis" / "backups"

MAX_FILE = 2 * 1024 * 1024          # 2 MiB per file
MAX_SOURCE = 40 * 1024 * 1024       # 40 MiB per source

TEXT_EXTENSIONS = {
    ".md", ".mdx", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".jsx", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".csv", ".tsv", ".html", ".css", ".scss",
    ".sh", ".bash", ".ps1", ".cmd", ".bat", ".svg", ".xml",
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav",
    ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".wasm",
    ".ttf", ".otf", ".woff", ".woff2",
}

SOURCES = [
    # ---------- Complete lightweight/self-contained skill packs ----------
    {
        "id": "impeccable",
        "repo": "pbakaus/impeccable",
        "mode": "prefix",
        "prefixes": ["plugin/skills/impeccable/"],
        "class": "ready-skill",
    },
    {
        "id": "ui-ux-pro-max",
        "repo": "nextlevelbuilder/ui-ux-pro-max-skill",
        "mode": "prefix",
        "prefixes": [".claude/skills/"],
        "class": "ready-skill",
    },
    {
        "id": "ponytail",
        "repo": "DietrichGebert/ponytail",
        "mode": "prefix",
        "prefixes": ["skills/ponytail/"],
        "class": "ready-skill",
    },
    {
        "id": "humanizer",
        "repo": "blader/humanizer",
        "mode": "exact",
        "files": ["SKILL.md"],
        "class": "ready-skill",
    },
    {
        "id": "grill-me",
        "repo": "RobMitt/grill-me-skill",
        "mode": "exact",
        "files": ["SKILL.md"],
        "class": "ready-skill",
    },
    {
        "id": "anti-slop",
        "repo": "miqdadbadjuber/anti-slop",
        "mode": "prefix",
        "prefixes": ["skills/"],
        "class": "ready-skill",
    },
    {
        "id": "diagram-design",
        "repo": "cathrynlavery/diagram-design",
        "mode": "prefix",
        "prefixes": ["skills/diagram-design/"],
        "class": "ready-skill",
    },
    {
        "id": "caveman-skills",
        "repo": "JuliusBrussee/caveman",
        "mode": "prefix",
        "prefixes": ["skills/"],
        "class": "ready-skill",
    },

    # Superpowers skills now live here, not in the lightweight shim repo.
    {
        "id": "superpowers",
        "repo": "obra/superpowers-skills",
        "mode": "prefix",
        "prefixes": ["skills/"],
        "class": "ready-skill",
    },

    # ---------- Research skills with their bundled scripts ----------
    {
        "id": "last30days",
        "repo": "mvanhorn/last30days-skill",
        "mode": "prefix",
        "prefixes": ["skills/last30days/"],
        "class": "ready-skill",
    },
    {
        "id": "video-lens",
        "repo": "kar2phi/video-lens",
        "mode": "prefix",
        "prefixes": ["skills/video-lens/"],
        "class": "ready-skill",
    },

    # ---------- Marketing / Revenue ----------
    # User wants the useful MarketingSkills library available.
    {
        "id": "marketing-skills",
        "repo": "coreyhaines31/marketingskills",
        "mode": "prefix",
        "prefixes": ["skills/"],
        "class": "ready-skill-library",
    },
    {
        "id": "pricing-strategy",
        "repo": "mohitagw15856/pm-claude-skills",
        "mode": "prefix",
        "prefixes": ["skills/pricing-strategy/"],
        "class": "ready-skill",
    },

    # ---------- Vercel ----------
    {
        "id": "vercel-agent-skills",
        "repo": "vercel-labs/agent-skills",
        "mode": "prefix",
        "prefixes": ["skills/"],
        "class": "ready-skill-library",
    },
    {
        "id": "find-skills",
        "repo": "vercel-labs/skills",
        "mode": "prefix",
        "prefixes": ["skills/find-skills/"],
        "class": "ready-skill",
    },

    # ---------- Anthropic ----------
    # Catalog only for now: definitions, not all heavy document assets.
    {
        "id": "anthropic-skills",
        "repo": "anthropics/skills",
        "mode": "skill-heads",
        "class": "catalog-only",
    },

    # ---------- Tools that should remain external runtimes ----------
    {
        "id": "agent-browser",
        "repo": "vercel-labs/agent-browser",
        "mode": "exact",
        "files": ["README.md", "package.json"],
        "class": "external-runtime",
    },
    {
        "id": "claude-mem",
        "repo": "thedotmack/claude-mem",
        "mode": "exact",
        "files": [
            "README.md",
            "docs/public/introduction.mdx",
            "docs/public/installation.mdx",
            "docs/public/usage/openai-compatible-provider.mdx",
        ],
        "class": "external-runtime",
    },

    # SEOmator: skill instructions + integration doc.
    # CLI runtime will be installed separately only when activated.
    {
        "id": "seo-audit",
        "repo": "seo-skills/seo-audit-skill",
        "mode": "mixed",
        "prefixes": ["skill/"],
        "files": ["docs/ai-agent-integration.md"],
        "class": "external-runtime-plus-skill",
    },

    # Architecture donor only. Do not embed its whole FastAPI/Groq app.
    {
        "id": "scrapling-rag-reference",
        "repo": "Tharanika-R-Git/Website-rag-using-scrapling",
        "mode": "exact",
        "files": [
            "README.md",
            "requirements.txt",
            "pyproject.toml",
        ],
        "class": "architecture-reference",
    },
]

ALWAYS_ROOT = {
    "README.md",
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "SECURITY.md",
}


def headers():
    h = {
        "User-Agent": "jarvis-skill-harvester/1.0",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def get_json(url: str):
    req = urllib.request.Request(url, headers=headers())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def get_bytes(url: str):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "jarvis-skill-harvester/1.0"},
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(1 + attempt)
    raise last


def git_head(repo: str):
    url = f"https://github.com/{repo}.git"
    p = subprocess.run(
        ["git", "ls-remote", "--symref", url, "HEAD"],
        text=True,
        capture_output=True,
        timeout=45,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "git ls-remote failed")

    branch = None
    sha = None

    for line in p.stdout.splitlines():
        if line.startswith("ref:") and line.endswith("\tHEAD"):
            ref = line.split()[1]
            if ref.startswith("refs/heads/"):
                branch = ref[len("refs/heads/"):]
        elif line.endswith("\tHEAD") and not line.startswith("ref:"):
            sha = line.split()[0]

    if not branch or not sha:
        raise RuntimeError(f"Could not resolve HEAD for {repo}")

    return branch, sha


def get_tree(repo: str, branch: str):
    qbranch = urllib.parse.quote(branch, safe="")
    url = (
        f"https://api.github.com/repos/{repo}/git/trees/"
        f"{qbranch}?recursive=1"
    )
    data = get_json(url)
    if data.get("truncated"):
        raise RuntimeError(
            f"GitHub returned a truncated tree for {repo}; refusing partial harvest"
        )
    return data.get("tree", [])


def should_skip(path: str, size: int):
    suffix = Path(path).suffix.lower()

    if size and size > MAX_FILE:
        return f"file>{MAX_FILE}"

    if suffix in SKIP_EXTENSIONS:
        return "binary/media"

    # Files with no extension are allowed (LICENSE, shell launchers, etc.)
    if suffix and suffix not in TEXT_EXTENSIONS:
        return "non-text-extension"

    return None


def chosen(path: str, spec: dict):
    # Always retain small source/license metadata when present.
    if path in ALWAYS_ROOT:
        return True

    mode = spec["mode"]

    if mode == "prefix":
        return any(path.startswith(p) for p in spec.get("prefixes", []))

    if mode == "exact":
        return path in spec.get("files", [])

    if mode == "mixed":
        return (
            path in spec.get("files", [])
            or any(path.startswith(p) for p in spec.get("prefixes", []))
        )

    if mode == "skill-heads":
        return path.startswith("skills/") and path.endswith("/SKILL.md")

    return False


def extract_skill_name(text: str, fallback: str):
    # Enough for standard Agent Skill YAML frontmatter without adding PyYAML.
    head = text[:6000]
    m = re.search(r"(?m)^name:\s*[\"']?([^\"'\n]+)", head)
    if m:
        return m.group(1).strip()
    return fallback


def human_bytes(n: int):
    units = ["B", "KiB", "MiB", "GiB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024


def main():
    if not (ROOT / ".git").exists():
        print("ERROR: run this from ~/Desktop/my_own_Jarvis", file=sys.stderr)
        sys.exit(2)

    FABRIC.mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)

    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)

    lock = {
        "format": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sources": [],
    }

    grand_total = 0

    print()
    print("JARVIS LIGHTWEIGHT SKILL HARVEST")
    print("Nothing downloaded here will be executed.")
    print("=" * 68)

    for i, spec in enumerate(SOURCES, 1):
        source_id = spec["id"]
        repo = spec["repo"]

        print(f"\n[{i:02d}/{len(SOURCES):02d}] {source_id}")
        print(f"     source: {repo}")
        print(f"     class : {spec['class']}")

        entry = {
            "id": source_id,
            "repo": repo,
            "class": spec["class"],
            "files": 0,
            "bytes": 0,
            "skipped": [],
        }

        try:
            branch, sha = git_head(repo)
            tree = get_tree(repo, branch)

            entry["branch"] = branch
            entry["commit"] = sha

            candidates = []
            for item in tree:
                if item.get("type") != "blob":
                    continue

                path = item["path"]
                size = int(item.get("size") or 0)

                if not chosen(path, spec):
                    continue

                reason = should_skip(path, size)
                if reason:
                    entry["skipped"].append(
                        {"path": path, "reason": reason, "size": size}
                    )
                    continue

                candidates.append((path, size))

            selected_bytes = sum(size for _, size in candidates)

            if selected_bytes > MAX_SOURCE:
                # Prefer SKILL definitions/reference docs/scripts over ancillary data.
                priority = []
                rest = []

                for item in candidates:
                    path, size = item
                    name = Path(path).name.lower()

                    if (
                        name == "skill.md"
                        or "/references/" in path
                        or "/scripts/" in path
                        or path.endswith(".py")
                        or path.endswith(".sh")
                        or path.endswith(".ps1")
                        or path.endswith(".cmd")
                    ):
                        priority.append(item)
                    else:
                        rest.append(item)

                candidates = priority
                used = sum(size for _, size in candidates)

                for item in rest:
                    if used + item[1] <= MAX_SOURCE:
                        candidates.append(item)
                        used += item[1]
                    else:
                        entry["skipped"].append({
                            "path": item[0],
                            "reason": "source-size-cap",
                            "size": item[1],
                        })

            dest_root = TMP / source_id
            dest_root.mkdir(parents=True, exist_ok=True)

            for path, expected_size in candidates:
                raw = (
                    f"https://raw.githubusercontent.com/"
                    f"{repo}/{sha}/{urllib.parse.quote(path)}"
                )

                data = get_bytes(raw)

                dest = dest_root / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)

                entry["files"] += 1
                entry["bytes"] += len(data)

            grand_total += entry["bytes"]

            print(
                f"     commit: {sha[:12]}  "
                f"files: {entry['files']}  "
                f"size: {human_bytes(entry['bytes'])}"
            )

            if entry["skipped"]:
                print(f"     skipped safely: {len(entry['skipped'])} files")

        except Exception as e:
            entry["error"] = str(e)
            print(f"     ERROR: {e}")

        lock["sources"].append(entry)

    # Build a lightweight skill index.
    skill_index = []

    for skillfile in TMP.rglob("SKILL.md"):
        rel = skillfile.relative_to(TMP)
        source_id = rel.parts[0]
        try:
            text = skillfile.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        fallback = skillfile.parent.name
        name = extract_skill_name(text, fallback)

        skill_index.append({
            "name": name,
            "source": source_id,
            "path": str(rel).replace("\\", "/"),
            "bytes": skillfile.stat().st_size,
        })

    skill_index.sort(key=lambda x: (x["source"], x["name"]))

    (TMP / "_skill-index.json").write_text(
        json.dumps(skill_index, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (TMP / "_sources.lock.json").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Human-readable inventory.
    with (TMP / "_inventory.tsv").open("w", encoding="utf-8") as f:
        f.write("SOURCE\tCLASS\tCOMMIT\tFILES\tSIZE_BYTES\tERROR\n")
        for e in lock["sources"]:
            f.write(
                f"{e['id']}\t"
                f"{e['class']}\t"
                f"{e.get('commit','')[:12]}\t"
                f"{e['files']}\t"
                f"{e['bytes']}\t"
                f"{e.get('error','')}\n"
            )

    # Atomic-ish replacement, keeping an old pack backup if one exists.
    if PACKS.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        old = BACKUPS / f"skill-packs-{stamp}"
        shutil.move(str(PACKS), str(old))
        print(f"\nPrevious pack backed up to: {old}")

    shutil.move(str(TMP), str(PACKS))

    # Keep harvested third-party source out of normal git commits for now.
    exclude = ROOT / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)

    existing = exclude.read_text(
        encoding="utf-8", errors="ignore"
    ) if exclude.exists() else ""

    pattern = ".jarvis/skill-fabric/packs/"
    if pattern not in existing:
        with exclude.open("a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n# JARVIS harvested third-party skill cache\n")
            f.write(pattern + "\n")

    ok = [e for e in lock["sources"] if "error" not in e]
    failed = [e for e in lock["sources"] if "error" in e]

    print()
    print("=" * 68)
    print("JARVIS SKILL HARVEST COMPLETE")
    print("=" * 68)
    print(f"Sources OK : {len(ok)}/{len(SOURCES)}")
    print(f"Skills found: {len(skill_index)}")
    print(f"Total size : {human_bytes(grand_total)}")
    print(f"Location   : {PACKS}")

    if failed:
        print()
        print("FAILED SOURCES:")
        for e in failed:
            print(f"  - {e['id']}: {e['error']}")

    print()
    print("Nothing has been activated in .claude/skills.")
    print("Nothing downloaded was executed.")
    print()
    print("Top-level pack sizes:")

    for p in sorted(PACKS.iterdir()):
        if not p.is_dir():
            continue
        size = sum(x.stat().st_size for x in p.rglob("*") if x.is_file())
        print(f"  {p.name:28} {human_bytes(size):>10}")


if __name__ == "__main__":
    main()
