from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from .models import ParsedChat, Message

# These categories are deliberately concrete. They describe what is present in the
# conversation, not why a person behaved a certain way.
TOPICS = {
    "military": {
        "he": "צבא ושירות", "en": "Military / service",
        "terms": ["צבא", "צה\"ל", "צהל", "פרופיל", "פטור", "פטורים", "דח\"ש", "דחש", "מדים", "נשק", "קורס", "בסיס"],
    },
    "health": {
        "he": "בריאות", "en": "Health",
        "terms": ["אפילפס", "נוירולוג", "רופא", "רופאה", "מרפאה", "בדיקה", "תרופה", "התקף", "דיכאון", "כאב", "חולה"],
    },
    "sport": {
        "he": "טיפוס, אופניים וספורט", "en": "Climbing, cycling and sport",
        "terms": ["טיפוס", "לטפס", "טיפס", "מטפס", "קיר טיפוס", "אופניים", "רכיבה", "לרכב", "מסלול אופניים"],
    },
    "transport": {
        "he": "נסיעות ולוגיסטיקה", "en": "Travel and logistics",
        "terms": ["שאטל", "שאטלים", "מוביט", "אוטובוס", "רכבת", "תחנה", "סבידור", "חניון", "הגעה"],
    },
    "food": {
        "he": "אוכל ומתכונים", "en": "Food and recipes",
        "terms": ["בראוניז", "גלוטן", "מתכון", "פסטה", "אוכל", "לאכול", "מסעדה", "קפה"],
    },
    "family": {
        "he": "משפחה", "en": "Family",
        "terms": ["אמא", "אבא", "אחות", "אח שלי", "אחי", "בני דודים", "בת דודה", "בן דוד", "משפחה"],
    },
    "study_work": {
        "he": "לימודים, עבודה ומסגרות", "en": "Study, work and frameworks",
        "terms": ["מכינה", "עבודה", "לימודים", "בית ספר", "מבחן", "קורס", "תפקיד", "משמרת"],
    },
}

RELATIONSHIP_TERMS_HE = [
    "זוגיות", "פרידה", "להיפרד", "לסיים פה", "לא רואה את העתיד", "לא רוצה להחזיק",
    "מפריע לי", "מפריע", "השקעה", "פינוי זמן", "לא כתבת", "שתכתוב יותר", "לא מספיק",
    "אני לא רוצה יותר", "הגעתי למסקנה", "שיחת הנזיפה", "חוסר השיתוף", "שיחות עמוקות",
    "יחס ודאגה", "רמת היחס", "לא רואה פואנטה", "להישאר חברים", "צריך מרחב", "צריכה מרחב",
    "מרגישה שזה לא", "מרגיש שזה לא", "סיבות", "מבחינת היחס שלנו"
]
RELATIONSHIP_TERMS_EN = [
    "relationship", "break up", "breakup", "end the relationship", "don't see a future",
    "bothering me", "effort", "time together", "you didn't text", "not enough", "i don't want anymore",
    "i came to the conclusion", "lack of sharing", "deep conversations", "care and attention", "stay friends", "need space"
]

PERSON_STOP = {
    "אני","אתה","את","הוא","היא","זה","זאת","אותו","אותה","מישהו","מישהי","כולם",
    "הבית","בית","העבודה","עבודה","הצבא","צבא","שם","פה","מחר","היום","אמא","אבא",
    "ראשונה","ראשון","שנייה","שני","שלישית","הזמן","זמן","יום","לילה","בוקר","ערב","דרך","מקום","המפקדת","מפקדת","המפקד","מפקד","הרופא","רופא","הנוירולוג","נוירולוג",
    "you","me","him","her","home","work","there","here","today","tomorrow",
}

ADDRESS_STOP = {
    "היי","בוקר","לילה","טוב","טובב","סורי","רגע","אגב","אוקיי","וואי","פאק","כן","לא",
    "אני","אתה","את","הוא","היא","אנחנו","איך","מה","למה","מתי","איפה","אז","אבל","פשוט","באמת","הכל","בסדר","הבנתי","רוצה","רוצהה","וואי","אגב","סבבה","תודה","יופי","אהה","אההה",
    "hey","good","sorry","okay","ok","well","how","what","why","when","where","really","just",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _contains_term(text: str, term: str) -> bool:
    return term.lower() in text.lower()


def _topic_hits(text: str) -> list[str]:
    out = []
    for key, spec in TOPICS.items():
        if any(_contains_term(text, term) for term in spec["terms"]):
            out.append(key)
    return out


def _display_sender(sender: str, aliases: dict[str, str]) -> str:
    return (aliases.get(sender) or sender).strip()


def _date_label(ts: datetime | None, lang: str) -> str:
    if not ts:
        return ""
    return ts.strftime("%d.%m.%Y") if lang == "he" else ts.strftime("%d %b %Y")


def _clean_snippet(text: str, max_chars: int = 230) -> str:
    s = _norm(text)
    s = re.sub(r"<[^>]+ omitted>", "", s, flags=re.I)
    s = re.sub(r"\[Forwarded\]\s*", "", s, flags=re.I)
    if len(s) <= max_chars:
        return s
    # Prefer a natural sentence boundary near the limit.
    cut = max(s.rfind(". ", 0, max_chars), s.rfind("? ", 0, max_chars), s.rfind("! ", 0, max_chars))
    if cut < max_chars * 0.55:
        cut = max_chars
    return s[:cut].rstrip(" .") + "…"


def _relationship_points(text: str, max_points: int = 4, max_chars: int = 270) -> list[str]:
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    # WhatsApp breakup/feedback messages often use bullets. Split BEFORE whitespace normalization.
    raw_parts = re.split(r"\n\s*[*•-]\s+|(?<=[.!?])\s+|\n+", raw)
    clean = _norm(raw)
    terms = RELATIONSHIP_TERMS_HE + RELATIONSHIP_TERMS_EN
    ranked = []
    for order, p in enumerate(raw_parts):
        p = p.strip(" -*•\t")
        if len(p) < 24:
            continue
        hits = sum(1 for t in terms if _contains_term(p, t))
        topic_hits = len(_topic_hits(p))
        explicit = sum(p.lower().count(x) for x in ["בעיני", "מפריע לי", "הגעתי למסקנה", "אני לא רוצה", "בשבילי", "for me", "i don't want", "i came to the conclusion"])
        if hits or explicit:
            score = hits * 5 + explicit * 6 + topic_hits * 1.5 + min(len(p), 900) / 160.0
            ranked.append((score, -order, p))
    ranked.sort(reverse=True)
    out=[]
    seen=set()
    for _,__,p in ranked:
        sn=_clean_snippet(p,max_chars)
        key=sn[:80].lower()
        if key in seen:
            continue
        seen.add(key); out.append(sn)
        if len(out)>=max_points:
            break
    if not out and clean:
        out=[_clean_snippet(clean,max_chars)]
    return out

def _relationship_score(msg: Message) -> float:
    text = _norm(msg.text)
    if len(text) < 45:
        return 0.0
    terms = RELATIONSHIP_TERMS_HE + RELATIONSHIP_TERMS_EN
    hits = sum(1 for t in terms if _contains_term(text, t))
    if hits == 0:
        return 0.0
    # Explicit first-person framing is more useful than generic mentions of a relationship.
    explicit = sum(text.lower().count(x) for x in ["אני מרגיש", "אני מרגישה", "בעיני", "מפריע לי", "i feel", "for me", "i don't want"])
    return hits * 3 + explicit * 4 + min(len(text), 1400) / 180.0


def _extract_people(messages: list[Message], aliases: dict[str, str]) -> list[dict[str, Any]]:
    discovered = Counter()
    examples: dict[str, str] = {}
    # Strong constructions only. Plain "with X" in Hebrew is too noisy ("with time", "with the first...").
    patterns = [
        re.compile(r"(?:אצל|לדבר עם|דיברתי עם|נפגש עם|נפגשתי עם|להיפגש עם|לקרוא ל|לחכות ל)\s*([א-ת][א-ת'׳\-]{1,16})"),
        re.compile(r"(?:at|talk(?:ing)? to|spoke with|meet(?:ing)? with|wait for)\s+([A-Z][a-z]{1,20})", re.I),
    ]
    participant_names = {k.lower() for k in aliases} | {v.lower() for v in aliases.values() if v}
    all_text = "\n".join(_norm(m.text) for m in messages)
    for m in messages:
        text = _norm(m.text)
        for rx in patterns:
            for name in rx.findall(text):
                n = name.strip(".,!?׳'\"")
                if not n or n.lower() in participant_names or n.lower() in PERSON_STOP:
                    continue
                discovered[n] += 1
                examples.setdefault(n, _clean_snippet(text, 150))
    rows=[]
    for n,_ in discovered.most_common(12):
        if re.search(r"[א-ת]",n):
            total=len(re.findall(rf"(?<![א-ת]){re.escape(n)}(?![א-ת])",all_text))
        else:
            total=len(re.findall(rf"\b{re.escape(n)}\b",all_text,re.I))
        if total>=2:
            rows.append({"name":n,"mentions":total,"example":examples.get(n,"")})
    rows.sort(key=lambda x:x["mentions"],reverse=True)
    return rows[:6]

def _extract_address_language(messages: list[Message], aliases: dict[str, str]) -> list[dict[str, Any]]:
    counts = Counter()
    senders = defaultdict(Counter)
    alias_prefixes=set()
    alias_full=set()
    for value in aliases.values():
        v=(value or "").strip().lower()
        if v:
            alias_full.add(v)
        if len(v)>=4:
            alias_prefixes.add(v[:3])
            alias_prefixes.add(v[:4])
    affectionate = {"אהובי","אהובה","אהוב","מותק","חיים","נסיך","נסיכה","מלכה","מלך","בייבי","baby","babe"}
    for m in messages:
        text = _norm(m.text)
        first = re.match(r"^([א-תA-Za-z][א-תA-Za-z'׳\-]{2,18})([,!]?)(?:\s|$)", text)
        if not first:
            continue
        token=first.group(1).strip(); delim=first.group(2)
        low=token.lower()
        if low in ADDRESS_STOP or low in alias_full or low == m.sender.lower() or re.fullmatch(r"ח+|ה+|א+", token):
            continue
        nickname_shape = token.endswith(("ילה","וש","ושקה","צ׳יק")) or low in affectionate or low in alias_prefixes
        if not delim and not nickname_shape:
            continue
        counts[token]+=1
        senders[token][_display_sender(m.sender, aliases)] += 1
    rows=[]
    for token,count in counts.most_common(20):
        if count<4:
            continue
        rows.append({"term":token,"count":count,"used_by":senders[token].most_common(2)})
    return rows[:5]

def analyze_content(
    parsed: ParsedChat,
    aliases: dict[str, str],
    user_raw: str,
    other_raw: str | None,
    relationship_type: str,
    lang: str,
) -> dict[str, Any]:
    messages = parsed.messages

    topic_stats = {}
    for key, spec in TOPICS.items():
        matched = []
        days = set()
        by_sender = Counter()
        samples = []
        for m in messages:
            if any(_contains_term(m.text, t) for t in spec["terms"]):
                matched.append(m)
                if m.timestamp:
                    days.add(m.timestamp.date().isoformat())
                by_sender[_display_sender(m.sender, aliases)] += 1
                if len(samples) < 3 and len(_norm(m.text)) >= 12:
                    samples.append({
                        "date": _date_label(m.timestamp, lang),
                        "sender": _display_sender(m.sender, aliases),
                        "text": _clean_snippet(m.text, 170),
                    })
        if matched:
            topic_stats[key] = {
                "key": key,
                "label": spec[lang if lang in {"he","en"} else "en"],
                "messages": len(matched),
                "days": len(days),
                "by_sender": dict(by_sender),
                "samples": samples,
            }

    # Score explicit relationship messages. This is the strongest content source because
    # it reflects what a participant actually said, rather than model inference.
    scored = []
    for idx, m in enumerate(messages):
        score = _relationship_score(m)
        if score > 0:
            scored.append((score, idx, m))
    scored.sort(reverse=True, key=lambda x: x[0])

    explicit = []
    used_days = set()
    for score, idx, m in scored:
        day = m.timestamp.date().isoformat() if m.timestamp else f"i{idx}"
        # avoid returning five pieces from one giant breakup message/date
        if day in used_days and len(explicit) >= 1:
            continue
        used_days.add(day)
        topics_here = _topic_hits(m.text)
        points = _relationship_points(m.text)
        explicit.append({
            "date": _date_label(m.timestamp, lang),
            "sender": _display_sender(m.sender, aliases),
            "snippet": points[0] if points else _clean_snippet(m.text),
            "points": points,
            "topics": [TOPICS[k][lang if lang in {"he","en"} else "en"] for k in topics_here],
            "score": round(score, 2),
        })
        if len(explicit) >= 3:
            break

    topic_weight={"military":1.2,"health":1.25,"sport":1.25,"transport":0.9,"food":0.9,"family":0.8,"study_work":1.0}
    for row in topic_stats.values():
        row["salience"] = round((row["days"] * 1.8 + row["messages"] * 0.12) * topic_weight.get(row["key"],1.0), 2)
    top_topics = sorted(topic_stats.values(), key=lambda x: x["salience"], reverse=True)[:5]
    people = _extract_people(messages, aliases)
    private_language = _extract_address_language(messages, aliases)

    # Concrete intersections: explicit relationship messages that themselves mention a life domain.
    intersections = []
    for row in explicit:
        if row["topics"]:
            topic_point = row["snippet"]
            for pt in row.get("points", []):
                if _topic_hits(pt):
                    topic_point = pt
                    break
            intersections.append({
                "sender": row["sender"],
                "date": row["date"],
                "topics": row["topics"],
                "snippet": topic_point,
            })

    return {
        "top_topics": top_topics,
        "people": people,
        "private_language": private_language,
        "explicit_relationship_messages": explicit,
        "life_relationship_intersections": intersections,
    }
