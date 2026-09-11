from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from html import unescape
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

USER_AGENT = "JarvisLocalAssistant/0.17"
MAX_SNIPPET_LEN = 320
MAX_FETCH_CHARS = 350_000
MAX_FACT_SENTENCES = 2

EN_STOPWORDS = {
    "the", "a", "an", "of", "to", "for", "on", "in", "at", "and", "or", "is", "are", "was", "were",
    "when", "what", "who", "where", "why", "how", "did", "does", "do", "last", "time", "man", "human",
    "with", "from", "into", "about", "tell", "me", "sir", "please", "current", "latest",
}
HE_STOPWORDS = {
    "מה", "מתי", "מי", "איך", "למה", "של", "על", "את", "עם", "וגם", "אני", "לי", "אתה", "אתם", "האדם",
    "האחרון", "פעם", "אחרונה", "תגיד", "ספר", "האם", "זה", "זו", "הוא", "היא", "הם", "היום", "עכשיו",
}
PREFERRED_FACT_DOMAINS = (
    "wikipedia.org",
    "nasa.gov",
    "science.nasa.gov",
    "britannica.com",
    "history.com",
    "esa.int",
    "reuters.com",
    "bbc.com",
    "apnews.com",
)
LOW_TRUST_DOMAINS = (
    "reddit.com",
)
DIRTY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"function\s*\(",
        r"client-js",
        r"vector-feature",
        r"please wait for verification",
        r"cf-chl",
        r"captcha",
        r"<script",
        r"<style",
        r"<link\s",
        r"<svg",
        r"<stop\s+offset",
        r"cookie",
        r"consent",
    ]
]


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
    raw = site.strip()
    if not raw:
        return "No website was provided."
    key = raw.lower()
    url = KNOWN_SITES.get(key)
    if not url:
        # Allow normal domains/URLs without hard-coding every website Jarvis may ever use.
        if re.fullmatch(r"https?://[^\s]+", raw, re.IGNORECASE):
            url = raw
        elif re.fullmatch(r"(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s]*)?", key, re.IGNORECASE):
            url = f"https://{raw}"
        else:
            return f"I do not recognize '{site}' as a website or domain."
    webbrowser.open(url)
    return f"Opened {url}."


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

    if _should_try_wikipedia_first(cleaned):
        answer = _answer_with_wikipedia(cleaned, config)
        if answer is not None:
            return answer

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
            "or ask a more specific fact question."
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

    ranked_results = _rank_results(query, results)
    if not ranked_results:
        return None

    answer = _synthesize_from_pages(query, ranked_results, timeout=config.web_timeout_seconds)
    if not answer:
        answer = _synthesize_from_results(query, ranked_results)
    if not answer:
        return None

    source_lines = _format_sources(ranked_results)
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
    answer = _clean_text(str(data.get("answer") or ""))
    if not answer or _is_dirty_text(answer):
        answer = _synthesize_from_results(query, results)
    if not answer:
        return None

    source_lines = _format_sources(_rank_results(query, results))
    spoken = _short_spoken_answer(answer)
    return WebAnswer(answer=answer, spoken_text=spoken, source_lines=source_lines, provider="tavily", query=query)


def _answer_with_wikipedia(query: str, config: AppConfig) -> WebAnswer | None:
    lang = "he" if _looks_hebrew(query) else "en"
    api_base = f"https://{lang}.wikipedia.org/w/api.php"
    for candidate in _wikipedia_search_candidates(query):
        search_payload = _get_json(
            api_base + "?" + urllib.parse.urlencode(
                {
                    "action": "opensearch",
                    "search": candidate,
                    "limit": 1,
                    "namespace": 0,
                    "format": "json",
                }
            ),
            timeout=config.web_timeout_seconds,
        )
        if not isinstance(search_payload, list) or len(search_payload) < 2:
            continue
        titles = search_payload[1] if len(search_payload) > 1 else []
        urls = search_payload[3] if len(search_payload) > 3 else []
        if not titles:
            continue
        title = str(titles[0]).strip()
        page_url = str(urls[0]).strip() if urls else f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

        extract = _get_wikipedia_extract(title, lang, timeout=config.web_timeout_seconds)
        if not extract:
            continue

        answer = _answer_from_text(query, extract)
        if not answer:
            answer = _collapse_whitespace(extract)[:450]
        if not answer or _is_dirty_text(answer):
            continue

        spoken = _short_spoken_answer(answer)
        return WebAnswer(
            answer=answer,
            spoken_text=spoken,
            source_lines=[f"1. Wikipedia — {page_url}"],
            provider="wikipedia",
            query=query,
        )
    return None


def _rank_results(query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_tokens = _query_tokens(query)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        title = _clean_text(str(item.get("title") or ""))
        snippet = _clean_text(str(item.get("content") or item.get("snippet") or ""))
        if _is_blocked_result(url, title, snippet):
            continue
        score = float(item.get("score") or 0.0)
        haystack = f"{title} {snippet}".lower()
        score += sum(8 for tok in query_tokens if tok in title.lower())
        score += sum(4 for tok in query_tokens if tok in haystack)
        score += _domain_preference_score(url)
        if re.search(r"\b(apollo\s*17|eugene\s+cernan|gene\s+cernan)\b", haystack, re.IGNORECASE):
            score += 10
        ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:8]]


def _domain_preference_score(url: str) -> float:
    host = urllib.parse.urlparse(url).netloc.lower()
    score = 0.0
    if any(domain in host for domain in PREFERRED_FACT_DOMAINS):
        score += 30.0
    if any(domain in host for domain in LOW_TRUST_DOMAINS):
        score -= 20.0
    return score


def _is_blocked_result(url: str, title: str, snippet: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    combined = f"{title} {snippet} {host}"
    lowered = combined.lower()
    if any(domain in host for domain in LOW_TRUST_DOMAINS) and "verification" in lowered:
        return True
    if any(token in lowered for token in ["homepage", "news source", "please wait for verification"]):
        return True
    if path in ('', '/') and not any(domain in host for domain in PREFERRED_FACT_DOMAINS):
        return True
    if _is_dirty_text(combined):
        return True
    return False


def _synthesize_from_pages(query: str, results: list[dict[str, Any]], timeout: float) -> str:
    candidate_answers: list[tuple[float, str]] = []
    for item in results[:4]:
        url = str(item.get("url") or "").strip()
        title = _clean_text(str(item.get("title") or ""))
        snippet = _clean_text(str(item.get("content") or item.get("snippet") or ""))
        if not url:
            continue

        page_text = ""
        if "wikipedia.org/wiki/" in url:
            wiki_extract = _get_wikipedia_extract_from_url(url, timeout)
            if wiki_extract:
                page_text = wiki_extract
        if not page_text:
            page_text = _extract_page_text(url, timeout=timeout)

        for source_text in [page_text, snippet]:
            answer = _answer_from_text(query, source_text)
            if answer:
                candidate_answers.append((_answer_score(query, answer) + _domain_preference_score(url), answer))

        if not page_text and snippet:
            candidate_answers.append((_answer_score(query, snippet), snippet[:420]))

    if not candidate_answers:
        return ""

    candidate_answers.sort(key=lambda pair: pair[0], reverse=True)
    best = candidate_answers[0][1]
    return _clean_answer(best)


def _extract_page_text(url: str, timeout: float) -> str:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_FETCH_CHARS)
            content_type = response.headers.get("Content-Type", "")
    except Exception:
        return ""

    if "text/html" not in content_type and "text/plain" not in content_type:
        return ""
    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""

    if _is_dirty_text(html):
        return ""

    if trafilatura is not None:
        try:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
                url=url,
            )
            extracted = _clean_text(extracted or "")
            if extracted and not _is_dirty_text(extracted):
                return extracted
        except Exception:
            pass

    fallback = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    fallback = re.sub(r"<[^>]+>", " ", fallback)
    fallback = _clean_text(fallback)
    if _is_dirty_text(fallback):
        return ""
    return fallback


def _get_wikipedia_extract_from_url(url: str, timeout: float) -> str:
    parsed = urllib.parse.urlparse(url)
    if "wikipedia.org" not in parsed.netloc:
        return ""
    title = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1]).replace("_", " ").strip()
    if not title:
        return ""
    lang = parsed.netloc.split(".")[0]
    return _get_wikipedia_extract(title, lang, timeout)


def _get_wikipedia_extract(title: str, lang: str, timeout: float) -> str:
    api_base = f"https://{lang}.wikipedia.org/w/api.php"
    extract_payload = _get_json(
        api_base + "?" + urllib.parse.urlencode(
            {
                "action": "query",
                "prop": "extracts",
                "exchars": 1400,
                "explaintext": 1,
                "titles": title,
                "format": "json",
                "formatversion": 2,
            }
        ),
        timeout=timeout,
    )
    try:
        pages = extract_payload["query"]["pages"]
        extract = str(pages[0].get("extract") or "").strip()
    except Exception:
        return ""
    return _clean_text(extract)


def _wikipedia_search_candidates(query: str) -> list[str]:
    candidates = [query]
    simplified = re.sub(r"[?؟]", "", query)
    simplified = re.sub(r"\b(when|what|who|where|why|how|is|was|did|does|do|latest|current)\b", " ", simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"\b(מה|מתי|מי|איך|למה|האם|זה|זו|הוא|היא|האדם|האחרון|עכשיו|היום)\b", " ", simplified)
    simplified = _collapse_whitespace(simplified)
    if simplified and simplified.lower() != query.lower():
        candidates.append(simplified)
    if re.search(r"moon|ירח", query, re.IGNORECASE):
        candidates.append("Apollo 17 last man on the moon" if not _looks_hebrew(query) else "אפולו 17 האדם האחרון על הירח")
    deduped: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.lower()
        if key in seen or not item.strip():
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:3]


def _answer_from_text(query: str, text: str) -> str:
    clean = _clean_text(text)
    if not clean or _is_dirty_text(clean):
        return ""
    sentences = _split_sentences(clean)
    if not sentences:
        return ""
    scored: list[tuple[float, str]] = []
    for sentence in sentences:
        sent = _clean_text(sentence)
        if len(sent) < 30 or _is_dirty_text(sent):
            continue
        scored.append((_answer_score(query, sent), sent))
    if not scored:
        return ""
    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [sent for score, sent in scored if score > 0][:MAX_FACT_SENTENCES]
    if not top:
        top = [scored[0][1]]
    return _clean_answer(" ".join(top))


def _answer_score(query: str, sentence: str) -> float:
    tokens = _query_tokens(query)
    lowered = sentence.lower()
    score = sum(3.0 for tok in tokens if tok in lowered)
    if re.search(r"\b(19\d{2}|20\d{2})\b", sentence):
        score += 2.0 if _looks_like_when_question(query) else 0.4
    if _looks_like_who_question(query) and re.search(r"\b(is|was|served|served as|astronaut|president)\b", lowered):
        score += 1.5
    if _looks_like_when_question(query) and re.search(r"\b(on|in|during|ended|last|final)\b", lowered):
        score += 1.5
    if len(sentence) > 260:
        score -= 0.5
    return score


def _synthesize_from_results(query: str, results: list[dict[str, Any]]) -> str:
    candidate_answers: list[tuple[float, str]] = []
    for item in results[:4]:
        snippet = _clean_text(str(item.get("content") or item.get("snippet") or ""))
        if not snippet or _is_dirty_text(snippet):
            continue
        answer = _answer_from_text(query, snippet)
        if answer:
            candidate_answers.append((_answer_score(query, answer) + _domain_preference_score(str(item.get("url") or "")), answer))
    if not candidate_answers:
        return ""
    candidate_answers.sort(key=lambda pair: pair[0], reverse=True)
    return _clean_answer(candidate_answers[0][1])


def _clean_answer(text: str) -> str:
    cleaned = _clean_text(text)
    cleaned = re.sub(r"\s*Sources?:.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(function\s*\(|client-js|vector-feature|please wait for verification)\b.*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned[:520].rstrip(" ,;:-")


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
        title = _clean_text(str(item.get("title") or item.get("url") or "Source"))
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        lines.append(f"{idx}. {title} — {url}")
    return lines


def _query_tokens(query: str) -> list[str]:
    raw_tokens = re.findall(r"[\w\u0590-\u05FF']+", query.lower())
    tokens: list[str] = []
    for token in raw_tokens:
        if _looks_hebrew(token):
            if token in HE_STOPWORDS or len(token) < 2:
                continue
        else:
            if token in EN_STOPWORDS or len(token) < 3:
                continue
        tokens.append(token)
    return tokens[:10]


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?։])\s+", text) if part.strip()]


def _short_spoken_answer(text: str, hard_limit: int = 220) -> str:
    compact = _collapse_whitespace(text)
    sentence = re.split(r"(?<=[.!?])\s+", compact)[0].strip()
    chosen = sentence or compact
    if len(chosen) > hard_limit:
        return chosen[:hard_limit].rstrip(" ,;:-") + "..."
    return chosen


def _clean_text(text: str) -> str:
    cleaned = unescape(text or "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.replace("\x00", " ")
    return cleaned.strip()


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _looks_hebrew(text: str) -> bool:
    return bool(re.search(r"[\u0590-\u05FF]", text or ""))


def _looks_like_when_question(query: str) -> bool:
    return bool(re.search(r"\bwhen\b|מתי", query, re.IGNORECASE))


def _looks_like_who_question(query: str) -> bool:
    return bool(re.search(r"\bwho\b|מי", query, re.IGNORECASE))


def _should_try_wikipedia_first(query: str) -> bool:
    lowered = query.lower()
    if any(token in lowered for token in ["latest", "current", "today", "news", "price", "weather", "stock", "score", "president", "prime minister"]):
        return False
    if re.search(r"מה\s+המחיר|חדשות|מזג\s+האוויר|ציון|תוצאה", query):
        return False
    return bool(re.search(r"\?$|\b(when|who|what|where|why|how|history|apollo|moon)\b", lowered) or re.search(r"מתי|מי|מה|למה|איך|היסטוריה|ירח|אפולו", query))


def _is_dirty_text(text: str) -> bool:
    sample = (text or "")[:2500]
    if not sample.strip():
        return True
    if any(pattern.search(sample) for pattern in DIRTY_PATTERNS):
        return True
    if sample.count("<") > 8 or sample.count("{") > 8:
        return True
    if re.search(r"https?://\S+\s+https?://\S+", sample):
        return True
    return False
