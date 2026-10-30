from __future__ import annotations
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from statistics import median
from .models import ParsedChat, ParticipantStats, ConversationMetrics

LEX={
"gratitude":["thank you","thanks","תודה","תודה רבה","מעריך","מעריכה"],
"apologies":["sorry","my bad","סליחה","מצטער","מצטערת","מתנצל","מתנצלת"],
"affection":["love you","miss you","❤️","❤","💕","😘","🥰","אוהב אותך","אוהבת אותך","מתגעגע","מתגעגעת","חיים שלי","מלך שלי","מלכה שלי"],
"warmth":["good morning","good night","take care","how are you","בוקר טוב","לילה טוב","שמור על עצמך","שמרי על עצמך","מה שלומך","בהצלחה","תרגיש טוב","תרגישי טוב","❤️","❤","🥰","😘"],
"boundaries":["don't","stop","i need space","not okay","leave me alone","אל ת","תפסיק","תפסיקי","צריך מרחב","צריכה מרחב","לא מתאים לי","עזוב אותי","עזבי אותי"],
"planning":["tomorrow","tonight","meet","see you","when are you","let's","weekend","book","מחר","הערב","נפגש","ניפגש","מתי אתה","מתי את","בוא","בואי","סופ\"ש","להזמין","נקבע"]}

def _count(text,terms):
    t=text.lower()
    return sum(t.count(x.lower()) for x in terms)

def build_metrics(parsed: ParsedChat, relationship_type="other", aliases: dict[str,str] | None=None) -> ConversationMetrics:
    aliases=aliases or {}
    stats={p:ParticipantStats(raw_name=p,name=(aliases.get(p) or p).strip()) for p in parsed.participants}
    reply=defaultdict(list)
    dated=[]
    prev=None
    sessions=0
    by_day=Counter()
    by_day_sender=defaultdict(Counter)
    by_day_hour=defaultdict(Counter)
    by_day_first={}
    by_day_last={}
    hourly=[0]*24

    for m in parsed.messages:
        s=stats.setdefault(m.sender,ParticipantStats(raw_name=m.sender,name=(aliases.get(m.sender) or m.sender).strip()))
        s.messages+=1
        s.characters+=len(m.text)
        s.questions+=m.text.count("?")
        for key in ("gratitude","apologies","affection","warmth","boundaries","planning"):
            setattr(s,key,getattr(s,key)+_count(m.text,LEX[key]))

        if m.timestamp:
            dated.append(m)
            day_key=m.timestamp.date()
            by_day[day_key]+=1
            by_day_sender[day_key][m.sender]+=1
            by_day_hour[day_key][m.timestamp.hour]+=1
            by_day_first[day_key]=min(by_day_first.get(day_key,m.timestamp),m.timestamp)
            by_day_last[day_key]=max(by_day_last.get(day_key,m.timestamp),m.timestamp)
            hourly[m.timestamp.hour]+=1
            new_session=prev is None or not prev.timestamp or (m.timestamp-prev.timestamp)>timedelta(hours=6)
            if new_session:
                sessions+=1
                s.session_starts+=1
            if prev is not None and prev.timestamp and prev.sender!=m.sender and m.timestamp>=prev.timestamp:
                gap=(m.timestamp-prev.timestamp).total_seconds()
                if gap<=7*86400:
                    reply[m.sender].append(gap)
        prev=m

    for name,vals in reply.items():
        stats[name].median_reply_seconds=round(float(median(vals)),1) if vals else None

    first=min((m.timestamp for m in dated),default=None)
    last=max((m.timestamp for m in dated),default=None)
    days_since=max(0,(datetime.now()-last).days) if last else None

    peak_day=None
    peak_count=0
    peak_day_details={}
    if by_day:
        day,peak_count=max(by_day.items(),key=lambda x:x[1])
        peak_day=day.isoformat()
        peak_sender_counts=by_day_sender[day]
        peak_hour_counts=by_day_hour[day]
        peak_day_peak_hour=max(peak_hour_counts,key=peak_hour_counts.get) if peak_hour_counts else None
        peak_day_details={
            "date": peak_day,
            "messages": peak_count,
            "participants":[
                {"name":(aliases.get(raw) or raw).strip(),"messages":count}
                for raw,count in sorted(peak_sender_counts.items(),key=lambda x:x[1],reverse=True)
            ],
            "peak_hour": peak_day_peak_hour,
            "peak_hour_messages": peak_hour_counts.get(peak_day_peak_hour,0) if peak_day_peak_hour is not None else 0,
            "first_message_time": by_day_first[day].strftime("%H:%M") if day in by_day_first else None,
            "last_message_time": by_day_last[day].strftime("%H:%M") if day in by_day_last else None,
        }

    times=sorted(m.timestamp for m in dated if m.timestamp)
    longest_silence=None
    if len(times)>=2:
        longest_silence=max((b-a).total_seconds()/3600 for a,b in zip(times,times[1:]))

    active_days=sorted(by_day)
    streak=0
    best=0
    prevd=None
    for d in active_days:
        if prevd is not None and (d-prevd).days==1:
            streak+=1
        else:
            streak=1
        best=max(best,streak)
        prevd=d

    total_hour=sum(hourly)
    after22=sum(hourly[22:])
    peak_hour=max(range(24),key=lambda h:hourly[h]) if total_hour else None
    daily=[]
    if active_days:
        d=active_days[0]
        end=active_days[-1]
        while d<=end:
            daily.append({"date":d.isoformat(),"count":by_day.get(d,0)})
            d += timedelta(days=1)

    return ConversationMetrics(
        total_messages=len(parsed.messages),
        participants=list(stats.values()),
        dated_messages=len(dated),
        first_message_at=first,
        last_message_at=last,
        days_since_last_message=days_since,
        sessions=sessions,
        relationship_type=relationship_type,
        media_inventory=parsed.media_inventory,
        peak_day=peak_day,
        peak_day_messages=peak_count,
        longest_silence_hours=round(longest_silence,2) if longest_silence is not None else None,
        longest_active_streak_days=best,
        peak_hour=peak_hour,
        after_22_percent=round(after22/total_hour*100,1) if total_hour else 0.0,
        hourly_counts=hourly,
        daily_activity=daily,
        peak_day_details=peak_day_details,
    )

def build_numbers(metrics: ConversationMetrics) -> dict:
    total=max(1,metrics.total_messages)
    parts=sorted(metrics.participants,key=lambda p:p.messages,reverse=True)
    starts=sum(p.session_starts for p in parts) or 1
    return {
        "participants":[
            {
                "name":p.name,
                "messages":p.messages,
                "share":round(p.messages/total*100,1),
                "starts":p.session_starts,
                "start_share":round(p.session_starts/starts*100,1),
            } for p in parts
        ],
        "peak_day":metrics.peak_day,
        "peak_day_messages":metrics.peak_day_messages,
        "longest_silence_hours":metrics.longest_silence_hours,
        "longest_active_streak_days":metrics.longest_active_streak_days,
        "peak_hour":metrics.peak_hour,
        "after_22_percent":metrics.after_22_percent,
        "hourly_counts":metrics.hourly_counts,
        "daily_activity":metrics.daily_activity,
        "peak_day_details":metrics.peak_day_details,
        "first_message_at":metrics.first_message_at,
        "last_message_at":metrics.last_message_at,
    }
