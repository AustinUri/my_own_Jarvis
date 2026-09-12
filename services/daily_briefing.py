from __future__ import annotations

import datetime as dt
import json
import re
import threading
from typing import Any, Callable

from agent.provider import OpenAICompatibleProvider
from core.user_paths import cache_dir
from services.weather import WeatherService
from services.google_calendar import GoogleCalendarService
from services.f1_learning import F1LearningService
from tools.web_tools import search_web_evidence


class DailyBriefingService:
    """Free, local-first daily briefing editor.

    SearXNG discovers current sources.  Local Qwen selects and summarizes the
    important items.  Interest flags are ranking hints, not mandatory headings:
    categories with nothing useful simply disappear rather than displaying an
    internal search error to the user.
    """

    def __init__(self, config, log: Callable[[str], None] | None = None):
        self.config = config
        self.log = log or (lambda _m: None)
        self.cache_path = cache_dir() / "daily_briefing.json"
        self.weather = WeatherService(config)
        self.google_calendar = GoogleCalendarService(config)
        self.f1 = F1LearningService()
        self._lock = threading.Lock()
        self._calendar_status: Callable[[], dict[str, Any]] | None = None
        self._calendar_list: Callable[[int], list[dict[str, Any]]] | None = None

    def set_calendar_provider(
        self,
        status_provider: Callable[[], dict[str, Any]] | None,
        list_provider: Callable[[int], list[dict[str, Any]]] | None,
    ) -> None:
        self._calendar_status = status_provider
        self._calendar_list = list_provider

    def cached(self) -> dict[str, Any]:
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return {"generated_at": None, "sections": [], "status": "not-generated"}

    def is_fresh_today(self) -> bool:
        cached = self.cached()
        stamp = cached.get("generated_at")
        if not stamp:
            return False
        try:
            return dt.datetime.fromisoformat(stamp).astimezone().date() == dt.datetime.now().astimezone().date()
        except Exception:
            return False

    def generate(self, force: bool = False) -> dict[str, Any]:
        with self._lock:
            if not force and self.is_fresh_today():
                return self.cached()
            now = dt.datetime.now().astimezone()
            candidates = self._discover(now)
            sections = self._edit_with_local_ai(candidates, now)
            if not sections:
                sections = self._deterministic_fallback(candidates)

            weather = None
            if getattr(self.config, "briefing_include_weather", True):
                try:
                    weather = self.weather.get().to_dict()
                except Exception:
                    weather = None

            calendar = None
            if getattr(self.config, "briefing_include_calendar", True):
                try:
                    status = self._calendar_status() if self._calendar_status else self.google_calendar.status()
                    events = self._calendar_list(2) if self._calendar_list else self.google_calendar.list_events(days=2)
                    calendar = {"connected": bool(status.get("connected")), "source": status.get("source", "google"), "events": events}
                except Exception:
                    calendar = {"connected": False, "source": "none", "events": []}

            learning = self.f1.current_lesson() if getattr(self.config, "briefing_include_f1_learning", True) else None
            payload = {
                "generated_at": now.isoformat(),
                "date": now.date().isoformat(),
                "sections": sections,
                "weather": weather,
                "calendar": calendar,
                "f1_learning": learning,
                "status": "ready" if sections else "limited",
                "discovered_sources": len(candidates),
            }
            self.cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return payload

    def _queries(self, now: dt.datetime) -> list[tuple[str, str]]:
        date = now.strftime("%Y-%m-%d")
        queries: list[tuple[str, str]] = []
        if getattr(self.config, "briefing_include_world", True):
            queries.append(("world", f"major world news developments today {date} Reuters AP BBC"))
        if getattr(self.config, "briefing_include_israel", True):
            queries.append(("israel", f"Israel major news developments today {date} Reuters Times of Israel Jerusalem Post"))
        if getattr(self.config, "briefing_include_idf", True):
            queries.append(("security", f"Israel IDF security verified developments today {date} IDF Reuters"))
        if getattr(self.config, "briefing_include_football", True):
            queries.append(("football", f"major football soccer results news today {date} UEFA BBC Sport ESPN"))
        if getattr(self.config, "briefing_include_champions_league", True):
            queries.append(("champions", f"UEFA Champions League matches results highlights today yesterday {date} site:uefa.com"))
        if getattr(self.config, "briefing_include_f1", True):
            queries.append(("f1", f"Formula 1 latest important news today {date} Formula1 FIA Reuters"))
        if getattr(self.config, "briefing_include_ai", True):
            queries.append(("technology", f"major AI technology news today {date} Reuters AP BBC technology"))
        return queries

    def _discover(self, now: dt.datetime) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for category, query in self._queries(now):
            self.log(f"Daily briefing: discovering {category}…")
            try:
                rows = search_web_evidence(query, self.config, limit=7)
            except Exception:
                rows = []
            for row in rows:
                url = str(row.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                item = dict(row)
                item["category"] = category
                item["source_id"] = len(collected) + 1
                collected.append(item)
                if len(collected) >= 36:
                    return collected
        return collected

    def _edit_with_local_ai(self, candidates: list[dict[str, Any]], now: dt.datetime) -> list[dict[str, Any]]:
        if not candidates:
            return []
        provider = OpenAICompatibleProvider(
            base_url=str(self.config.ai_base_url),
            model=str(self.config.ai_model_name),
            api_key=str(self.config.ai_api_key),
            timeout=min(90.0, float(getattr(self.config, "ai_timeout_seconds", 60.0)) + 20.0),
        )
        evidence = []
        for item in candidates[:30]:
            evidence.append({
                "id": item["source_id"],
                "category": item.get("category"),
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "url": item.get("url"),
                "published": item.get("published"),
            })
        system = (
            "You are the editor of a private JARVIS daily briefing. Use ONLY the supplied search evidence. "
            "Select 5 to 8 genuinely important, distinct developments. Interest categories are preferences, not required sections. "
            "Do not invent facts, scores, dates, quotes, or links. If two snippets conflict, omit or cautiously qualify the item. "
            "Keep each summary to 1-2 sentences. For football/Champions League, include verified score information when present and "
            "prefer official UEFA/club highlight URLs when the evidence supplies them. Return STRICT JSON only: "
            '{"items":[{"title":"...","summary":"...","category":"world|israel|security|football|champions|f1|technology","source_ids":[1,2]}]}.'
        )
        user = f"Local date: {now:%Y-%m-%d}. Evidence:\n" + json.dumps(evidence, ensure_ascii=False)
        try:
            message = provider.chat([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ], temperature=0.18)
            content = str(message.get("content") or "")
            data = self._extract_json(content)
        except Exception as exc:
            self.log(f"Daily briefing local editor fallback: {exc}")
            return []
        rows = data.get("items") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return []
        source_map = {int(x["source_id"]): x for x in candidates if x.get("source_id")}
        sections: list[dict[str, Any]] = []
        used_titles: set[str] = set()
        for idx, item in enumerate(rows[:8], start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "Update").strip()[:120]
            summary = str(item.get("summary") or "").strip()[:900]
            if not summary:
                continue
            key = re.sub(r"\W+", " ", title.lower()).strip()
            if key in used_titles:
                continue
            used_titles.add(key)
            ids = item.get("source_ids") or []
            sources = []
            for sid in ids[:3]:
                try:
                    src = source_map.get(int(sid))
                except Exception:
                    src = None
                if not src:
                    continue
                sources.append(f"{len(sources)+1}. {src.get('title')} — {src.get('url')}")
            if not sources:
                continue
            sections.append({
                "id": f"story-{idx}",
                "title": title,
                "summary": summary,
                "category": str(item.get("category") or "world"),
                "sources": sources,
                "provider": "searxng+local-qwen",
            })
        return sections

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start:end + 1]
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}

    def _deterministic_fallback(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Still give the user something useful if Qwen is temporarily unavailable."""
        out: list[dict[str, Any]] = []
        per_category: dict[str, int] = {}
        for item in candidates:
            category = str(item.get("category") or "world")
            if per_category.get(category, 0) >= 2:
                continue
            title = str(item.get("title") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url or not snippet:
                continue
            per_category[category] = per_category.get(category, 0) + 1
            out.append({
                "id": f"fallback-{len(out)+1}",
                "title": title[:120],
                "summary": snippet[:650],
                "category": category,
                "sources": [f"1. {title} — {url}"],
                "provider": "searxng-snippet",
            })
            if len(out) >= 6:
                break
        return out
