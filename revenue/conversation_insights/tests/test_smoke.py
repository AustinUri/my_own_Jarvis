from __future__ import annotations
import io, zipfile, re
from revenue.conversation_insights.parser_whatsapp import parse_upload
from revenue.conversation_insights.metrics import build_metrics
from revenue.conversation_insights.semantic_engine import generate_semantic_report
from revenue.conversation_insights.ai_provider import SemanticProvider


class FakeProvider:
    def json_completion(self, system, user, max_tokens=1000, temperature=0.1, schema=None, schema_name="semantic_output"):
        if "segment_summary" in system:
            ids = re.findall(r"\[(E\d+)\]", user)
            first = ids[0] if ids else "E000001"
            if "כדורגל" in user or "football" in user.lower():
                return {
                    "segment_summary": "The chat is organized around football plans and cousin banter.",
                    "distinctive_facts": [{"claim": "They coordinate football and family plans.", "evidence_ids": [first], "confidence": "high"}],
                    "explicit_needs_or_boundaries": [],
                    "events_or_turning_points": [],
                    "recurring_people_places_or_rituals": [{"claim": "Football is a shared ritual.", "evidence_ids": [first]}],
                    "relationship_dynamics": [],
                }
            return {
                "segment_summary": "The chat contains a romantic breakup discussion about time and sharing.",
                "distinctive_facts": [{"claim": "A breakup focuses on time and sharing.", "evidence_ids": [first], "confidence": "high"}],
                "explicit_needs_or_boundaries": [{"claim": "One side asks for more time and sharing.", "evidence_ids": [first]}],
                "events_or_turning_points": [{"claim": "The relationship ends.", "evidence_ids": [first]}],
                "recurring_people_places_or_rituals": [],
                "relationship_dynamics": [],
            }

        ids = re.findall(r"E\d{6}", user)
        eid = ids[0] if ids else "E000001"
        if "football" in user.lower():
            return {
                "title": "⚽ משפחה, כדורגל והקשר שמחזיק דרך שגרה",
                "intro": ["זה קשר משפחתי שחי דרך תיאומים, צחוקים ותוכניות משותפות."],
                "sections": [
                    {"kind": "texture", "title": "⚽ הטקס הקבוע שלכם", "punchline": "כדורגל הוא לא פרט שולי כאן.", "paragraphs": ["הוא חוזר כדרך להיפגש ולהחזיק קשר."], "evidence_ids": [eid]},
                    {"kind": "context", "title": "👨‍👩‍👦 משפחה לפני דרמה", "punchline": "השיחה בנויה יותר על שגרה משותפת מאשר על עימות.", "paragraphs": ["זה קשר שמתקיים דרך היום־יום."], "evidence_ids": [eid]},
                    {"kind": "lesson", "title": "🎯 מה עובד כאן", "punchline": "העקביות היא הכוח של הקשר.", "paragraphs": ["המשיכו ליצור סיבות להיפגש."], "evidence_ids": [eid]},
                ],
                "lessons": ["שמרו על הטקסים המשותפים."],
            }
        return {
            "title": "💔 זמן, שיתוף והנקודה שבה זה נשבר",
            "intro": ["הקשר נשחק סביב צורך שלא קיבל מענה בזמן."],
            "sections": [
                {"kind": "verdict", "title": "⏱️ הזמן הפך לבעיה", "punchline": "הפער לא היה רק בכמות ההודעות.", "paragraphs": ["הוא היה בציפייה ליוזמה והשקעה."], "evidence_ids": [eid]},
                {"kind": "mirror", "title": "🧱 השיתוף נתקע", "punchline": "אחד ביקש יותר פתיחות.", "paragraphs": ["השיתוף הפך לנקודת חיכוך."], "evidence_ids": [eid]},
                {"kind": "lesson", "title": "🎯 הלקח", "punchline": "שינוי שמגיע מאוחר מדי לא תמיד מציל קשר.", "paragraphs": ["צריך לפעול לפני שהאמון נשחק."], "evidence_ids": [eid]},
            ],
            "lessons": ["אל תחכה לשיחת פרידה כדי להתחיל להשתנות."],
        }


def make(txt):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("chat.txt", txt.encode("utf-8"))
    b.seek(0)
    return b


def report(txt, rel):
    p = parse_upload(make(txt), "chat.zip")
    aliases = {x: x for x in p.participants}
    m = build_metrics(p, rel, aliases)
    return generate_semantic_report(p, m, rel, None, None, p.participants[0], p.participants[1] if len(p.participants) > 1 else None, aliases, "he", FakeProvider())


def main():
    ex = """[25/7/26, 03:24] אורי: אני מבין ששינוי לוקח זמן
[25/7/26, 03:25] פולינה: אני רוצה להיפרד כי חסר לי זמן ושיתוף
[25/7/26, 03:26] אורי: אני אוהב אותך אבל מבין
"""
    cousin = """[1/8/26, 10:00] אורי: בא לכדורגל היום?
[1/8/26, 10:05] דני: ברור בן דוד, נפגשים במגרש
[8/8/26, 10:00] אורי: כדורגל גם השבוע?
[8/8/26, 10:05] דני: כן, ואחרי זה ארוחה אצל סבתא
"""
    a = report(ex, "ex")
    b = report(cousin, "family")
    assert a.title != b.title
    assert "כדורגל" in b.title or any("כדורגל" in s.get("title", "") for s in b.sections)
    assert "שיתוף" in a.title or any("שיתוף" in s.get("title", "") for s in a.sections)
    print("MVP 0.6.1 structured semantic regression test: PASS")
    print("ex title:", a.title)
    print("family title:", b.title)


if __name__ == "__main__":
    main()
