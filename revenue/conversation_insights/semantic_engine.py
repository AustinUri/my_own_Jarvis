from __future__ import annotations

from datetime import datetime
import json
import math
import re

from .ai_provider import SemanticProvider
from .metrics import build_numbers
from .models import ParsedChat, ConversationMetrics, FirstReadReport

RELATIONSHIP_LENSES = {
    "dating": "dating/romantic relationship: consistency, reciprocity, attraction, planning, vulnerability, repair, follow-through",
    "ex": "former romantic relationship: breakup trajectory, unresolved loops, re-contact, boundaries, what changed, what each side explicitly said",
    "friends": "friendship: reciprocity, support, inclusion, shared rituals, reliability, humor, who maintains contact",
    "family": "family relationship: care, obligation, hierarchy, roles, coordination, recurring friction, boundaries",
    "work": "work relationship: ownership, responsiveness, clarity, follow-through, escalation, boundaries, collaboration",
    "other": "custom relationship. The user's description is the primary lens.",
}
META_HE = ["הדוח חושב", "הדוח מצא", "הדוח לא המציא", "הבינה המלאכותית", "ה-ai", "לפי האלגוריתם", "המנוע", "המתודולוגיה"]
META_EN = ["the report thinks", "the report found", "the ai", "the algorithm", "the engine", "the methodology"]


def _alias(raw, aliases):
    return (aliases.get(raw) or raw).strip()


def _date(ts, lang):
    if not ts:
        return ""
    return ts.strftime("%d.%m.%Y") if lang == "he" else ts.strftime("%d %b %Y")


def _clean(text, limit=420):
    s = re.sub(r"\s+", " ", (text or "").strip())
    return s if len(s) <= limit else s[:limit].rstrip() + "…"


def _line(eid, m, aliases, lang):
    return f"[{eid}] {_date(m.timestamp, lang)} | {_alias(m.sender, aliases)}: {_clean(m.text, 500)}"


def _score_message(text):
    t = (text or "").strip()
    if not t:
        return 0.0
    low = t.lower()
    score = min(len(t), 1200) / 100.0
    strong = [
        "מפריע לי", "בעיני", "אני מרגיש", "אני מרגישה", "אני רוצה", "אני לא רוצה", "אני צריך", "אני צריכה",
        "נפגע", "סליחה", "מצטער", "אוהב אותך", "אוהבת אותך", "מתגעגע", "להיפרד", "זוגיות", "חברות",
        "i feel", "for me", "i want", "i don't want", "i need", "sorry", "love you", "miss you", "break up",
        "relationship", "friendship", "hurt",
    ]
    score += sum(5 for x in strong if x in low)
    score += min(t.count("?"), 3) * 0.8
    return score


def _segment_indices(n, count):
    if n <= 0:
        return []
    count = max(1, min(count, n))
    step = math.ceil(n / count)
    return [(i, min(n, i + step)) for i in range(0, n, step)]


def _sample_segment(messages, start, end, cap=70):
    rows = list(range(start, end))
    if len(rows) <= cap:
        return rows
    selected = set()
    stride = max(1, len(rows) // 24)
    selected.update(rows[::stride][:24])
    selected.update(sorted(rows, key=lambda i: _score_message(messages[i].text), reverse=True)[:34])
    selected.update(rows[:6])
    selected.update(rows[-6:])
    return sorted(selected)[:cap]


def build_evidence_segments(parsed, aliases, lang):
    messages = parsed.messages
    seg_count = 3 if len(messages) < 700 else 4 if len(messages) < 2500 else 5
    evidence_map, segments = {}, []
    for si, (start, end) in enumerate(_segment_indices(len(messages), seg_count), 1):
        lines = []
        for i in _sample_segment(messages, start, end):
            m = messages[i]
            eid = f"E{i+1:06d}"
            evidence_map[eid] = {"sender": _alias(m.sender, aliases), "date": _date(m.timestamp, lang), "text": _clean(m.text, 520), "index": i}
            lines.append(_line(eid, m, aliases, lang))
        segments.append({"segment": si, "start_index": start, "end_index": end, "text": "\n".join(lines)})
    return segments, evidence_map


SEGMENT_SYSTEM = """You are the evidence analyst for a conversation-intelligence product.
You are NOT writing the final report.
Read only the supplied WhatsApp evidence lines and extract what is actually distinctive in this part of the conversation.

Rules:
- Every factual claim must cite one or more supplied evidence IDs.
- Never invent an evidence ID.
- Separate explicit statements from interpretation.
- Notice concrete life details: people, places, work/study, family, health, hobbies, logistics, routines, shared jokes, plans, conflicts, affection, apologies, disappointments, requests and changes.
- Pay special attention to repeated patterns and moments where a participant explicitly explains what they need or what changed.
- Do not diagnose attachment styles, mental illness, lying, cheating or motives unless explicitly stated.
- Do not write generic relationship advice.
- Output JSON only.

Schema:
{
  "segment_summary":"2-5 sentences",
  "distinctive_facts":[{"claim":"...","evidence_ids":["E000001"],"confidence":"high|medium"}],
  "explicit_needs_or_boundaries":[{"claim":"...","evidence_ids":["..."]}],
  "events_or_turning_points":[{"claim":"...","evidence_ids":["..."]}],
  "recurring_people_places_or_rituals":[{"claim":"...","evidence_ids":["..."]}],
  "relationship_dynamics":[{"claim":"...","evidence_ids":["..."],"confidence":"high|medium"}]
}
"""

FINAL_SYSTEM = """You are the senior writer for a relationship-conversation analysis product.
Write a UNIQUE first report for THIS conversation. Never reuse a fixed story from another relationship.

The user has already seen the numeric dashboard, so do not merely restate counts.
Your job is to synthesize the actual life, events, language, needs, conflicts, warmth, routines and changes in this specific chat.

Hard rules:
1. Build one clear thesis that could only plausibly belong to this conversation.
2. Be direct when evidence is strong. You may name behavior bluntly if the supplied summaries support it.
3. Do not diagnose a personality disorder, attachment style, mental illness, lying or cheating unless explicitly stated.
4. Distinguish behavior from motive. Name what someone did; do not pretend to know hidden intent.
5. Use evidence_ids. Never invent them.
6. The UI will render the original WhatsApp text for those IDs. Do not fabricate quote text.
7. Do not mention AI, algorithms, methodology, evidence engines, or talk about "the report" inside the prose.
8. Do not use sterile disclaimers. If evidence is weak, omit the claim.
9. Section titles must be specific to this story, not generic labels.
10. Use 4-7 sections. Vary section kind and emoji naturally.
11. Include at least one uncomfortable but useful conclusion when evidence supports one.
12. End with 2-4 concrete lessons that follow from THIS chat, not generic advice.
13. Write in the requested language.

Output JSON only:
{
 "title":"specific editorial title with 1-2 emojis",
 "intro":["direct paragraph","direct paragraph"],
 "sections":[{
   "kind":"verdict|mirror|timeline|texture|context|lesson",
   "title":"specific title with emoji",
   "punchline":"one strong sentence",
   "paragraphs":["1-3 concrete paragraphs"],
   "evidence_ids":["E000001","E000002"]
 }],
 "lessons":["specific lesson","specific lesson"]
}
"""



SEGMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "segment_summary": {"type": "string"},
        "distinctive_facts": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "claim": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["high", "medium"]}
                },
                "required": ["claim", "evidence_ids", "confidence"]
            }
        },
        "explicit_needs_or_boundaries": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"claim": {"type": "string"}, "evidence_ids": {"type": "array", "items": {"type": "string"}}},
                "required": ["claim", "evidence_ids"]
            }
        },
        "events_or_turning_points": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"claim": {"type": "string"}, "evidence_ids": {"type": "array", "items": {"type": "string"}}},
                "required": ["claim", "evidence_ids"]
            }
        },
        "recurring_people_places_or_rituals": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"claim": {"type": "string"}, "evidence_ids": {"type": "array", "items": {"type": "string"}}},
                "required": ["claim", "evidence_ids"]
            }
        },
        "relationship_dynamics": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "claim": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["high", "medium"]}
                },
                "required": ["claim", "evidence_ids", "confidence"]
            }
        }
    },
    "required": [
        "segment_summary", "distinctive_facts", "explicit_needs_or_boundaries",
        "events_or_turning_points", "recurring_people_places_or_rituals", "relationship_dynamics"
    ]
}

FINAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "intro": {"type": "array", "items": {"type": "string"}},
        "sections": {
            "type": "array",
            "minItems": 3,
            "maxItems": 7,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "kind": {"type": "string", "enum": ["verdict", "mirror", "timeline", "texture", "context", "lesson"]},
                    "title": {"type": "string"},
                    "punchline": {"type": "string"},
                    "paragraphs": {"type": "array", "items": {"type": "string"}},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["kind", "title", "punchline", "paragraphs", "evidence_ids"]
            }
        },
        "lessons": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["title", "intro", "sections", "lessons"]
}

def _segment_prompt(seg, relationship_type, relationship_description, goal, aliases, lang):
    lens = RELATIONSHIP_LENSES.get(relationship_type, RELATIONSHIP_LENSES["other"])
    return f"""Language: {lang}
Relationship type: {relationship_type}
Relationship lens: {lens}
Custom relationship description: {relationship_description or '(none)'}
User question/goal: {goal or '(none)'}
Participant display names: {json.dumps(aliases, ensure_ascii=False)}

Evidence from chronological segment {seg['segment']}:
{seg['text']}
"""


def _final_prompt(summaries, metrics, relationship_type, relationship_description, goal, aliases, lang):
    lens = RELATIONSHIP_LENSES.get(relationship_type, RELATIONSHIP_LENSES["other"])
    participants = [
        {"name": p.name, "messages": p.messages, "session_starts": p.session_starts, "questions": p.questions, "affection": p.affection, "apologies": p.apologies, "planning": p.planning}
        for p in metrics.participants
    ]
    numeric = {
        "total_messages": metrics.total_messages,
        "first_message": str(metrics.first_message_at or ""),
        "last_message": str(metrics.last_message_at or ""),
        "participants": participants,
        "peak_day": metrics.peak_day,
        "longest_silence_hours": metrics.longest_silence_hours,
        "longest_active_streak_days": metrics.longest_active_streak_days,
    }
    return f"""Requested language: {lang}
Relationship type: {relationship_type}
Relationship lens: {lens}
Custom relationship description: {relationship_description or '(none)'}
User question/goal: {goal or '(none)'}
Participant names: {json.dumps(aliases, ensure_ascii=False)}

Numeric context (background only; do not turn the report into a stats recap):
{json.dumps(numeric, ensure_ascii=False, indent=2)}

Chronological semantic segment summaries:
{json.dumps(summaries, ensure_ascii=False, indent=2)}
"""


def _valid_ids(values, evidence_map):
    out = []
    for x in values or []:
        if x in evidence_map and x not in out:
            out.append(x)
    return out[:4]


def _sanitize_output(data, evidence_map, lang):
    title = str(data.get("title") or "").strip()
    intro = [str(x).strip() for x in data.get("intro") or [] if str(x).strip()][:3]
    sections = []
    for raw in data.get("sections") or []:
        if not isinstance(raw, dict):
            continue
        sections.append(
            {
                "kind": str(raw.get("kind") or "context"),
                "title": str(raw.get("title") or "").strip(),
                "punchline": str(raw.get("punchline") or "").strip(),
                "paragraphs": [str(x).strip() for x in raw.get("paragraphs") or [] if str(x).strip()][:3],
                "evidence_ids": _valid_ids(raw.get("evidence_ids"), evidence_map),
            }
        )
        if len(sections) >= 7:
            break
    joined = " ".join([title, *intro] + [s["title"] + " " + s["punchline"] + " " + " ".join(s["paragraphs"]) for s in sections]).lower()
    forbidden = META_HE if lang == "he" else META_EN
    if any(x.lower() in joined for x in forbidden):
        raise ValueError("Semantic writer returned forbidden meta-talk.")
    if not title or len(sections) < 3:
        raise ValueError("Semantic writer returned an incomplete report.")
    return {"title": title, "intro": intro, "sections": sections, "lessons": data.get("lessons") or []}


def generate_semantic_report(parsed: ParsedChat, metrics: ConversationMetrics, relationship_type: str, relationship_description: str | None, goal: str | None, user_raw: str, other_raw: str | None, aliases: dict[str, str], lang: str, provider: SemanticProvider | None = None) -> FirstReadReport:
    provider = provider or SemanticProvider()
    segments, evidence_map = build_evidence_segments(parsed, aliases, lang)
    summaries = []
    for seg in segments:
        out = provider.json_completion(SEGMENT_SYSTEM, _segment_prompt(seg, relationship_type, relationship_description, goal, aliases, lang), max_tokens=1800, temperature=0.05, schema=SEGMENT_SCHEMA, schema_name="segment_analysis")
        for key in ("distinctive_facts", "explicit_needs_or_boundaries", "events_or_turning_points", "recurring_people_places_or_rituals", "relationship_dynamics"):
            rows = []
            for row in out.get(key) or []:
                if not isinstance(row, dict):
                    continue
                ids = _valid_ids(row.get("evidence_ids"), evidence_map)
                if ids:
                    rows.append({**row, "evidence_ids": ids})
            out[key] = rows[:10]
        summaries.append(out)

    final = provider.json_completion(FINAL_SYSTEM, _final_prompt(summaries, metrics, relationship_type, relationship_description, goal, aliases, lang), max_tokens=3200, temperature=0.16, schema=FINAL_SCHEMA, schema_name="report_one")
    final = _sanitize_output(final, evidence_map, lang)

    sections = []
    for s in final["sections"]:
        ids = s.pop("evidence_ids", [])
        quotes = []
        for eid in ids:
            ev = evidence_map[eid]
            quotes.append({"sender": ev["sender"], "date": ev["date"], "text": ev["text"], "evidence_id": eid})
        s["quotes"] = quotes
        s["evidence"] = []
        sections.append(s)

    if final.get("lessons"):
        sections.append(
            {
                "kind": "lesson",
                "title": "🎯 מה לקחת מכאן" if lang == "he" else "🎯 What to carry forward",
                "punchline": str(final["lessons"][0]),
                "paragraphs": [str(x) for x in final["lessons"][1:4]],
                "quotes": [],
                "evidence": [],
            }
        )

    if metrics.first_message_at and metrics.last_message_at:
        subtitle = (
            f"דוח 1 · חינם · {metrics.total_messages:,} הודעות · {metrics.first_message_at:%d.%m.%Y}–{metrics.last_message_at:%d.%m.%Y}"
            if lang == "he"
            else f"Report 1 · Free · {metrics.total_messages:,} messages · {metrics.first_message_at:%d %b %Y}–{metrics.last_message_at:%d %b %Y}"
        )
    else:
        subtitle = f"דוח 1 · חינם · {metrics.total_messages:,} הודעות" if lang == "he" else f"Report 1 · Free · {metrics.total_messages:,} messages"

    import uuid
    return FirstReadReport(
        report_id=uuid.uuid4().hex,
        language=lang,
        title=final["title"],
        subtitle=subtitle,
        paragraphs=final["intro"],
        highlights=[],
        sections=sections,
        numbers=build_numbers(metrics),
        metrics=metrics,
        relationship_type=relationship_type,
        relationship_description=relationship_description,
        goal=goal,
        created_at=datetime.utcnow(),
    )
