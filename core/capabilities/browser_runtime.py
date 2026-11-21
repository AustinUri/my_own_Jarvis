"""Explicit, isolated browser reads. No LLM, shell, or automatic outreach."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import uuid
from urllib.parse import urlsplit


MAX_SNAPSHOT_CHARS = 8000
MAX_TEXT_CHARS = 16000

# Fixed observation only; never execute code taken from a web page or model.
SITE_CHECKS = r"""JSON.stringify({
  title: document.title.slice(0, 200),
  language: document.documentElement.lang.slice(0, 30),
  meta_description: !!document.querySelector('meta[name="description"][content]:not([content=""])'),
  viewport_meta: !!document.querySelector('meta[name="viewport"]'),
  h1_count: document.querySelectorAll('h1').length,
  images_missing_alt: document.querySelectorAll('img:not([alt])').length,
  phone_links: document.querySelectorAll('a[href^="tel:"]').length,
  viewport_width: window.innerWidth,
  document_width: document.documentElement.scrollWidth
})"""


def parse_inspection(raw: str) -> dict:
    data = json.loads(raw)
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        raise ValueError("Unexpected inspection format")
    result = {}
    for field in ("title", "language"):
        if isinstance(data.get(field), str):
            result[field] = data[field][:200]
    for field in ("meta_description", "viewport_meta"):
        if type(data.get(field)) is bool:
            result[field] = data[field]
    for field in ("h1_count", "images_missing_alt", "phone_links", "viewport_width", "document_width"):
        if type(data.get(field)) is int and 0 <= data[field] <= 1000000:
            result[field] = data[field]
    if not result:
        raise ValueError("No recognized inspection fields")
    if result.get("viewport_width") and "document_width" in result:
        result["horizontal_overflow_hint"] = result["document_width"] > result["viewport_width"] + 4
    return result


def possible_block(url: str, snapshot: str) -> bool:
    lower = (url + "\n" + snapshot).lower()
    return any(marker in lower for marker in (
        "recaptcha", "captcha", "unusual traffic", "verify you are human", "/sorry/index"))


def resolve_browser() -> str:
    if os.name != "nt":
        executable = shutil.which("agent-browser")
        if executable:
            return executable
    else:
        executable = shutil.which("agent-browser.exe")
        if executable:
            return executable
        # npm global installs on Windows use a .cmd shim. Prefer the native
        # binary so URL arguments never go through cmd.exe interpretation.
        shim = shutil.which("agent-browser.cmd")
        if shim:
            modules = Path(shim).parent / "node_modules"
            package = Path("@agent-browser/cli-win32-x64-msvc/bin/agent-browser.exe")
            for path in (modules / "agent-browser/node_modules" / package,
                         modules / package):
                if path.is_file():
                    return str(path)
    raise RuntimeError("Agent Browser executable not found. Check the existing installation and PATH.")


def _validate_url(url: str) -> None:
    if any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError("URL must not contain whitespace or control characters")
    parsed = urlsplit(url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        raise ValueError("Only explicit HTTP(S) URLs are accepted")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials in URLs are not allowed")


def extract_links(snapshot: str) -> tuple[list[dict], bool]:
    """Extract complete link lines before the text snapshot is clipped."""
    links = []
    limited = False
    pattern = re.compile(r'^\s*- link "(.*)" \[ref=[^,\]]+, url=(.*?)\]', re.M)
    for label, url in pattern.findall(snapshot):
        if not url.startswith(("http://", "https://")):
            continue
        if len(links) >= 150 or len(url) > 12000:
            limited = True
            continue
        links.append({"label": label[:500], "url": url})
    return links, limited


def read_page(url: str, *, headed: bool = False, include_links: bool = False, inspect_site: bool = False, include_text: bool = False) -> dict:
    """Read a user-selected URL once. Output is untrusted page content.

    Not a network sandbox: do not expose this to untrusted URL selection.
    """
    _validate_url(url)
    executable = resolve_browser()
    session = "jarvis-read-" + uuid.uuid4().hex[:12]
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("AGENT_BROWSER_")}
    base = [executable, "--session", session]

    def run(*args: str) -> str:
        result = subprocess.run(base + list(args), env=env, shell=False,
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=45, check=False)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or "Browser command failed")[:1000])
        return result.stdout

    cleanup_error = None
    inspection = None
    inspection_error = None
    try:
        run(*(["--headed"] if headed else []), "open", url)
        final_url = run("get", "url").strip()[:2000]
        snapshot = run("snapshot", "-i", "--urls") if include_links else run("snapshot", "-c")
        text_snapshot = run("snapshot", "-c") if include_text and include_links else snapshot
        if inspect_site and not possible_block(final_url, snapshot):
            try:
                run("set", "viewport", "390", "844")
                inspection = parse_inspection(run("eval", SITE_CHECKS))
            except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
                inspection_error = str(exc)[:300]
    finally:
        try:
            run("close")
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            cleanup_error = str(exc)[:1000]
    blocked = possible_block(final_url, snapshot) or (include_text and possible_block(final_url, text_snapshot))
    result = {"requested_url": url, "final_url": final_url,
            "status": "possible_block" if blocked else "read",
            "untrusted_snapshot": snapshot[:MAX_SNAPSHOT_CHARS],
            "truncated": len(snapshot) > MAX_SNAPSHOT_CHARS,
            "cleanup_error": cleanup_error}
    if include_links:
        result["links"], result["links_truncated"] = extract_links(snapshot)
    if include_text:
        result["untrusted_text"] = text_snapshot[:MAX_TEXT_CHARS]
        result["text_truncated"] = len(text_snapshot) > MAX_TEXT_CHARS
    if inspect_site:
        result["inspection"] = inspection
        result["inspection_error"] = inspection_error
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    try:
        result = read_page(args.url, headed=args.headed)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "error": str(exc)[:1000]}, ensure_ascii=True))
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] == "read" and not result["cleanup_error"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
