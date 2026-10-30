from __future__ import annotations
from math import exp
from .models import ConversationMetrics, PatternFinding

LENS_WEIGHTS = {
    "dating": {
        "initiative_asymmetry": 1.0, "curiosity_balance": 0.9, "warmth_reciprocity": 1.0,
        "repair_balance": 0.9, "planning_balance": 0.9, "boundary_signals": 0.8,
        "reply_rhythm": 0.7, "change_over_time": 1.0,
    },
    "ex": {
        "initiative_asymmetry": 0.9, "curiosity_balance": 0.6, "warmth_reciprocity": 0.7,
        "repair_balance": 1.0, "planning_balance": 0.5, "boundary_signals": 1.0,
        "reply_rhythm": 0.8, "change_over_time": 1.0,
    },
    "friends": {
        "initiative_asymmetry": 0.8, "curiosity_balance": 0.8, "warmth_reciprocity": 0.7,
        "repair_balance": 0.7, "planning_balance": 0.8, "boundary_signals": 0.5,
        "reply_rhythm": 0.5, "change_over_time": 0.7,
    },
    "family": {
        "initiative_asymmetry": 0.6, "curiosity_balance": 0.6, "warmth_reciprocity": 0.8,
        "repair_balance": 0.9, "planning_balance": 0.7, "boundary_signals": 0.8,
        "reply_rhythm": 0.4, "change_over_time": 0.8,
    },
    "work": {
        "initiative_asymmetry": 0.7, "curiosity_balance": 0.5, "warmth_reciprocity": 0.3,
        "repair_balance": 0.6, "planning_balance": 1.0, "boundary_signals": 0.8,
        "reply_rhythm": 0.8, "change_over_time": 0.7,
    },
    "other": {
        "initiative_asymmetry": 0.8, "curiosity_balance": 0.8, "warmth_reciprocity": 0.8,
        "repair_balance": 0.8, "planning_balance": 0.8, "boundary_signals": 0.8,
        "reply_rhythm": 0.6, "change_over_time": 0.8,
    },
}

def _conf(strength: float, n: int) -> str:
    if n < 40:
        return "low"
    if strength >= 0.55 and n >= 200:
        return "high"
    return "medium"

def _balance(a: int, b: int) -> float:
    if a + b == 0:
        return 0.0
    return abs(a - b) / (a + b)

def detect_patterns(metrics: ConversationMetrics, relationship_type: str, lang: str = "en") -> list[PatternFinding]:
    parts = sorted(metrics.participants, key=lambda p: p.messages, reverse=True)
    if len(parts) < 2:
        return []
    a, b = parts[0], parts[1]
    n = metrics.total_messages
    weights = LENS_WEIGHTS.get(relationship_type, LENS_WEIGHTS["other"])
    out: list[PatternFinding] = []

    def add(key, raw_strength, obs_en, obs_he, int_en, int_he, evidence, alt_en, alt_he):
        strength = max(0.0, min(1.0, raw_strength * weights.get(key, 1.0)))
        if strength < 0.18:
            return
        titles = {
            "initiative_asymmetry": ("Who keeps restarting the conversation", "מי מחזיר את השיחה לחיים"),
            "curiosity_balance": ("Curiosity balance", "מאזן הסקרנות"),
            "warmth_reciprocity": ("Warmth is not distributed equally", "החום לא מתחלק שווה"),
            "repair_balance": ("Who repairs after friction", "מי מתקן אחרי חיכוך"),
            "planning_balance": ("Planning effort", "מאמץ בתכנון"),
            "boundary_signals": ("Boundary signals", "אותות של גבולות"),
            "reply_rhythm": ("Reply rhythm", "קצב התגובה"),
            "change_over_time": ("The week the rhythm shifted", "השבוע שבו הקצב השתנה"),
        }
        title = titles[key][1 if lang == "he" else 0]
        out.append(PatternFinding(
            key=key,
            title=title,
            strength=round(strength, 3),
            confidence=_conf(strength, n),
            observation=obs_he if lang == "he" else obs_en,
            interpretation=int_he if lang == "he" else int_en,
            evidence=evidence,
            alternative_explanation=alt_he if lang == "he" else alt_en,
        ))

    init_bal = _balance(a.session_starts, b.session_starts)
    starter = a if a.session_starts >= b.session_starts else b
    add(
        "initiative_asymmetry", init_bal,
        f"{starter.name} starts noticeably more conversation sessions.",
        f"{starter.name} מתחיל/ה יותר מקטעי שיחה באופן מורגש.",
        "That can indicate unequal maintenance effort, but it is not the same thing as unequal caring.",
        "זה יכול להעיד על מאמץ לא שווה בתחזוקת הקשר, אבל זה לא אותו דבר כמו אכפתיות לא שווה.",
        [f"{a.name}: {a.session_starts} starts", f"{b.name}: {b.session_starts} starts"],
        "Schedules, personality, or one person's habit of continuing old threads can distort this signal.",
        "לו״ז, אופי, או הרגל של אחד הצדדים להמשיך שיחות ישנות יכולים לעוות את האות הזה."
    )

    qbal = _balance(a.questions, b.questions)
    asker = a if a.questions >= b.questions else b
    add(
        "curiosity_balance", qbal,
        f"{asker.name} asks a larger share of the explicit questions.",
        f"{asker.name} שואל/ת חלק גדול יותר מהשאלות המפורשות.",
        "Repeated curiosity is one useful proxy for conversational investment, especially when it persists over time.",
        "סקרנות חוזרת היא אינדיקציה שימושית להשקעה בשיחה, במיוחד כשהיא נשמרת לאורך זמן.",
        [f"{a.name}: {a.questions} questions", f"{b.name}: {b.questions} questions"],
        "Some people show interest through statements, voice notes, actions or practical help rather than question marks.",
        "יש אנשים שמביעים עניין דרך אמירות, הודעות קוליות, מעשים או עזרה מעשית ולא דרך סימני שאלה."
    )

    wa, wb = a.warmth + a.affection + a.gratitude, b.warmth + b.affection + b.gratitude
    wbal = _balance(wa, wb)
    warm = a if wa >= wb else b
    add(
        "warmth_reciprocity", wbal,
        f"{warm.name} sends more explicit warmth signals in text.",
        f"{warm.name} שולח/ת יותר אותות חום מפורשים בטקסט.",
        "This is about expressed warmth in chat, not a diagnosis of who feels more.",
        "זה מתאר חום שמובע בצ'אט — לא אבחנה של מי מרגיש יותר.",
        [f"{a.name}: {wa} warmth signals", f"{b.name}: {wb} warmth signals"],
        "Affection may be expressed offline, through media, or in language this deterministic pass does not recognize yet.",
        "חיבה יכולה להתבטא מחוץ לצ'אט, דרך מדיה, או בניסוחים שהמעבר הדטרמיניסטי עדיין לא מזהה."
    )

    rbal = _balance(a.apologies, b.apologies)
    repairer = a if a.apologies >= b.apologies else b
    add(
        "repair_balance", rbal,
        f"{repairer.name} uses more explicit apology/repair language.",
        f"{repairer.name} משתמש/ת יותר בשפת התנצלות ותיקון מפורשת.",
        "If this repeats around conflict, it may show who is carrying more of the repair work.",
        "אם זה חוזר סביב קונפליקטים, ייתכן שזה מראה מי נושא יותר מעבודת התיקון.",
        [f"{a.name}: {a.apologies}", f"{b.name}: {b.apologies}"],
        "One person may repair through humor, action or a change of behavior rather than apology words.",
        "אחד הצדדים יכול לתקן דרך הומור, פעולה או שינוי התנהגות ולא דרך מילות התנצלות."
    )

    pbal = _balance(a.planning, b.planning)
    planner = a if a.planning >= b.planning else b
    add(
        "planning_balance", pbal,
        f"{planner.name} contributes more planning language.",
        f"{planner.name} מביא/ה יותר שפת תכנון וקביעת מפגשים.",
        "Planning is a stronger signal when it leads to follow-through; this preview only measures the planning side.",
        "תכנון הוא אות חזק יותר כשהוא מוביל לביצוע; התצוגה המקדימה מודדת כרגע רק את צד התכנון.",
        [f"{a.name}: {a.planning}", f"{b.name}: {b.planning}"],
        "The other person may plan outside WhatsApp or respond to plans rather than initiate them.",
        "הצד השני יכול לתכנן מחוץ ל-WhatsApp או להיענות לתכנונים במקום ליזום אותם."
    )

    if metrics.turning_point_week and (metrics.turning_point_score or 0) > 0.45:
        add(
            "change_over_time", min(1.0, (metrics.turning_point_score or 0)/2.0),
            f"The largest week-to-week shift in volume/warmth/participation appears around {metrics.turning_point_week}.",
            f"השינוי השבועי הגדול ביותר בנפח/חום/חלוקת ההשתתפות מופיע סביב {metrics.turning_point_week}.",
            "This is a candidate turning point for the AI pass to inspect against the actual surrounding messages.",
            "זו נקודת מפנה מועמדת שה-AI צריך לבדוק מול ההודעות שסביבה, ולא לקבוע אוטומטית כסיבה.",
            [f"shift score: {metrics.turning_point_score}"],
            "A holiday, trip, illness, exams, work pressure or a change in routine can create the same statistical shift.",
            "חג, נסיעה, מחלה, מבחנים, עומס בעבודה או שינוי שגרה יכולים ליצור אותו שינוי סטטיסטי."
        )

    out.sort(key=lambda x: x.strength, reverse=True)
    return out[:6]
