from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from typing import Any

from core.config import AppConfig

try:
    import trafilatura
except Exception:  # pragma: no cover - optional dependency
    trafilatura = None


KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "whatsapp": "https://web.whatsapp.com",
}

USER_AGENT = "JarvisLocalAssistant/0.15"
MAX_SNIPPET_LEN = 280
MAX_FETCH_CHARS = 2200


@dataclass(slots=True)
class WebAnswer:
    answer: str
    spoken_text: str
    source_lines: list[str]
    provider: str
    query: str

    def to_gui_text(self) -> str:
        if self.source_lines:
            return f"{self.answer}\n\nSources:\n" + "\n".join(self.source_lines)
        return self.answer


def open_website(site: str) -> str:
    key = site.lower().strip()
    url = KNOWN_SITES.get(key)
    if not url:
        return f"I do not know the website '{site}' yet."
    webbrowser.open(url)
    return f"Opened {key}."


def search_web(query: str) -> str:
    cleaned = query.strip()
    if not cleaned:
        return "No web search query was provided."
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(cleaned)}"
    webbrowser.open(url)
    return f"Opened a web search for '{cleaned}'."


def answer_web_question(query: str, config: AppConfig) -> WebAnswer:
    cleaned = _normalize_query(query)
    if not cleaned:
        return WebAnswer(
            answer="I need a real web question first.",
            spoken_text="I need a real web question first.",
            source_lines=[],
            provider="none",
            query=query,
        )

    if config.searxng_base_url.strip():
        answer = _answer_with_searxng(cleaned, config)
        if answer is not None:
            return answer

    if config.tavily_api_key.strip():
        answer = _answer_with_tavily(cleaned, config)
        if answer is not None:
            return answer

    answer = _answer_with_wikipedia(cleaned, config)
    if answer is not None:
        return answer

    return WebAnswer(
        answer=(
            "Web lookup could not get a reliable result. Set a working SearXNG instance URL in Settings, "
            "or fall back to Wikipedia questions only."
        ),
        spoken_text="I could not get a reliable web result.",
        source_lines=[],
        provider="none",
        query=cleaned,
    )


def _answer_with_searxng(query: str, config: AppConfig) -> WebAnswer | None:
    base = config.searxng_base_url.strip().rstrip("/")
    if not base:
        return None

    params = {
        "q": query,
        "format": "json",
        "categories": "general",
        "language": "he" if _looks_hebrew(query) else "en",
        "safesearch": "1",
    }
    url = f"{base}/search?{urllib.parse.urlencode(params)}"
    try:
        data = _get_json(url, timeout=config.web_timeout_seconds)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    results = data.get("results") or []
    if not isinstance(results, list) or not results:
        return None

    narrowed_results = []
    for item in results:
        if isinstance(item, dict) and item.get("url"):
            narrowed_results.append(item)
        if len(narrowed_results) >= max(2, min(8, int(config.web_max_results))):
            break
    if not narrowed_results:
        return None

    answer = _synthesize_from_pages(narrowed_results, timeout=config.web_timeout_seconds)
    if not answer:
        answer = _synthesize_from_results(narrowed_results)
    if not answer:
        return None

    source_lines = _format_sources(narrowed_results)
    spoken = _short_spoken_answer(answer)
    return WebAnswer(answer=answer, spoken_text=spoken, source_lines=source_lines, provider="searxng", query=query)


def _answer_with_tavily(query: str, config: AppConfig) -> WebAnswer | None:
    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max(2, min(8, int(config.web_max_results))),
        "include_answer": True,
        "include_raw_content": False,
        "topic": "general",
    }
    data = _post_json(
        "https://api.tavily.com/search",
        payload,
        headers={"Authorization": f"Bearer {config.tavily_api_key.strip()}"},
        timeout=config.web_timeout_seconds,
    )
    if not data:
        return None

    results = data.get("results") or []
    answer = str(data.get("answer") or "").strip()
    if not answer:
        answer = _synthesize_from_results(results)
    if not answer:
        return None

    source_lines = _format_sources(results)
    spoken = _short_spoken_answer(answer)
    return WebAnswer(answer=answer, spoken_text=spoken, source_lines=source_lines, provider="tavily", query=query)


def _answer_with_wikipedia(query: str, config: AppConfig) -> WebAnswer | None:
    lang = "he" if _looks_hebrew(query) else "en"
    api_base = f"https://{lang}.wikipedia.org/w/api.php"
    search_payload = _get_json(
        api_base + "?" + urllib.parse.urlencode(
            {
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "namespace": 0,
                "format": "json",
            }
        ),
        timeout=config.web_timeout_seconds,
    )
    if not isinstance(search_payload, list) or len(search_payload) < 2:
        return None
    titles = search_payload[1] if len(search_payload) > 1 else []
    urls = search_payload[3] if len(search_payload) > 3 else []
    if not titles:
        return None
    title = str(titles[0]).strip()
    page_url = str(urls[0]).strip() if urls else f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

    extract_payload = _get_json(
        api_base + "?" + urllib.parse.urlencode(
            {
                "action": "query",
                "prop": "extracts",
                "exchars": 900,
                "explaintext": 1,
                "titles": title,
                "format": "json",
                "formatversion": 2,
            }
        ),
        timeout=config.web_timeout_seconds,
    )
    try:
        pages = extract_payload["query"]["pages"]
        extract = str(pages[0].get("extract") or "").strip()
    except Exception:
        return None
    if not extract:
        return None
    answer = _collapse_whitespace(extract)
    spoken = _short_spoken_answer(answer)
    return WebAnswer(
        answer=answer,
        spoken_text=spoken,
        source_lines=[f"1. Wikipedia — {page_url}"],
        provider="wikipedia",
        query=query,
    )


def _synthesize_from_pages(results: list[dict[str, Any]], timeout: float) -> str:
    chunks: list[str] = []
    for item in results[:3]:
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        extracted = _extract_page_text(url, timeout=timeout)
        if extracted:
            chunks.append(extracted[:700])
    if not chunks:
        return ""
    joined = " ".join(chunks)
    compact = _collapse_whitespace(joined)
    sentence = re.split(r"(?<=[.!?])\s+", compact)[0].strip()
    return sentence or compact[:420]


def _extract_page_text(url: str, timeout: float) -> str:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_FETCH_CHARS * 2)
            content_type = response.headers.get("Content-Type", "")
    except Exception:
        return ""

    if "text/html" not in content_type and not url.startswith("http"):
        return ""
    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""

    if trafilatura is not None:
        try:
            extracted = trafilatura.extract(html, include_comments=False, include_tables=False, favor_precision=True)
            if extracted:
                return _collapse_whitespace(extracted)
        except Exception:
            pass

    fallback = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    fallback = re.sub(r"<[^>]+>", " ", fallback)
    return _collapse_whitespace(fallback)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: float = 12.0) -> dict[str, Any] | None:
    req_headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=req_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _get_json(url: str, timeout: float = 12.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize_query(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^search(?: the web)? for\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(?:חפש(?:\s+באינטרנט|\s+ברשת)?|תחפש(?:\s+באינטרנט|\s+ברשת)?)\s+", "", cleaned)
    return _collapse_whitespace(cleaned)


def _format_sources(results: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for idx, item in enumerate(results[:3], start=1):
        title = _collapse_whitespace(str(item.get("title") or item.get("url") or "Source"))
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        lines.append(f"{idx}. {title} — {url}")
    return lines


def _synthesize_from_results(results: list[dict[str, Any]]) -> str:
    snippets: list[str] = []
    for item in results[:3]:
        content = _collapse_whitespace(str(item.get("content") or item.get("snippet") or ""))
        if content:
            snippets.append(content[:MAX_SNIPPET_LEN])
    if not snippets:
        return ""
    joined = " ".join(snippets)
    return _short_spoken_answer(joined, hard_limit=420)


def _short_spoken_answer(text: str, hard_limit: int = 220) -> str:
    compact = _collapse_whitespace(text)
    sentence = re.split(r"(?<=[.!?])\s+", compact)[0].strip()
    chosen = sentence or compact
    if len(chosen) > hard_limit:
        return chosen[:hard_limit].rstrip(" ,;:-") + "..."
    return chosen


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _looks_hebrew(text: str) -> bool:
    return bool(re.search(r"[\u0590-\u05FF]", text or ""))
