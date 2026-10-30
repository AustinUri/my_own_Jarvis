from __future__ import annotations
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from .config import MAX_CHAT_TEXT_BYTES, MAX_MESSAGES
from .models import Message, ParsedChat

BIDI = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
BIDI_RE = re.compile("[" + re.escape(BIDI) + "]")
LINE_RE = re.compile(
    r"^\[?(?P<date>\d{1,2}[./-]\d{1,2}[./-]\d{2,4}),?\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp]\.?[Mm]\.?)?)\]?\s*"
    r"(?:[-–—]\s*)?(?P<sender>[^:]{1,120}):\s?(?P<text>.*)$"
)
STAMP_RE = re.compile(
    r"^\[?\d{1,2}[./-]\d{1,2}[./-]\d{2,4},?\s+"
    r"\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp]\.?[Mm]\.?)?\]?\s*(?:[-–—]\s*)?"
)
MEDIA_PATTERNS = [
    ("image", re.compile(r"(image omitted|תמונה הושמטה|התמונה הושמטה|\.jpe?g\b|\.png\b)", re.I)),
    ("video", re.compile(r"(video omitted|וידאו הושמט|\.mp4\b|\.mov\b)", re.I)),
    ("audio", re.compile(r"(audio omitted|voice message omitted|אודיו הושמט|הודעה קולית|\.opus\b|\.ogg\b|\.m4a\b)", re.I)),
    ("document", re.compile(r"(document omitted|מסמך הושמט|\.pdf\b|\.docx?\b|\.xlsx?\b)", re.I)),
    ("sticker", re.compile(r"(sticker omitted|מדבקה הושמטה|\.webp\b)", re.I)),
]
EXT_KIND = {
    ".jpg":"image",".jpeg":"image",".png":"image",".gif":"image",".webp":"sticker",
    ".mp4":"video",".mov":"video",".avi":"video",".mkv":"video",
    ".opus":"audio",".ogg":"audio",".m4a":"audio",".mp3":"audio",".wav":"audio",
    ".pdf":"document",".doc":"document",".docx":"document",".xls":"document",".xlsx":"document",
    ".ppt":"document",".pptx":"document",".txt":"text",".md":"text"
}

def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig","utf-8","utf-16","cp1255","cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")

def _clean_line(line: str) -> str:
    return BIDI_RE.sub("", line).replace("\ufeff", "").rstrip("\r\n")

def _raw_parts(date_s: str):
    a,b,y = [int(x) for x in re.split(r"[./-]", date_s)]
    if y < 100:
        y += 2000 if y < 70 else 1900
    return a,b,y

def _make_date(a,b,y,order):
    day,month = (a,b) if order == "dmy" else (b,a)
    try:
        return datetime(y,month,day)
    except ValueError:
        return None

def _infer_date_order(lines: list[str]) -> str:
    raw=[]
    for line in lines:
        m=LINE_RE.match(_clean_line(line))
        if m:
            raw.append(_raw_parts(m.group("date")))
            if len(raw) >= 2000:
                break
    if not raw:
        return "dmy"

    dmy_votes=sum(1 for a,b,y in raw if a>12 and b<=12)
    mdy_votes=sum(1 for a,b,y in raw if b>12 and a<=12)
    if dmy_votes != mdy_votes:
        return "dmy" if dmy_votes > mdy_votes else "mdy"

    def score(order):
        seq=[]
        invalid=0
        for a,b,y in raw:
            d=_make_date(a,b,y,order)
            if d is None:
                invalid += 1
            else:
                seq.append(d)
        backwards=0
        continuity=0.0
        for x,y in zip(seq,seq[1:]):
            gap=(y-x).days
            if gap < 0:
                backwards += 1
                continuity += abs(gap)*20
            else:
                continuity += min(gap,120) ** 0.5
        return invalid*100000 + backwards*10000 + continuity

    return min(("dmy","mdy"), key=score)

def _parse_dt(date_s: str, time_s: str, order: str) -> datetime | None:
    a,b,y=_raw_parts(date_s)
    d=_make_date(a,b,y,order)
    if not d:
        return None
    t=time_s.strip().replace(".", "").upper()
    for fmt in ("%H:%M:%S","%H:%M","%I:%M:%S %p","%I:%M %p"):
        try:
            tt=datetime.strptime(t,fmt).time()
            return datetime(d.year,d.month,d.day,tt.hour,tt.minute,tt.second)
        except ValueError:
            pass
    return None

def _media_kind(text: str) -> str | None:
    low=text.lower()
    if "<media omitted>" in low or "מדיה הושמטה" in text:
        return "media"
    for kind,rx in MEDIA_PATTERNS:
        if rx.search(text):
            return kind
    return None

def _guess_language(messages: list[Message]) -> str:
    sample=" ".join(m.text for m in messages[:3000])
    he=len(re.findall(r"[\u0590-\u05FF]", sample))
    latin=len(re.findall(r"[A-Za-z]", sample))
    if he > max(40, latin*0.20):
        return "he"
    if latin > 40:
        return "en"
    return "unknown"

def parse_text(text: str, source_name="chat.txt", media_inventory=None) -> ParsedChat:
    lines=text.splitlines()
    date_order=_infer_date_order(lines)
    messages=[]
    current=None

    for raw in lines:
        line=_clean_line(raw)
        m=LINE_RE.match(line)
        if m:
            if len(messages)>=MAX_MESSAGES:
                raise ValueError(f"Chat exceeds {MAX_MESSAGES:,} messages.")
            current=Message(
                timestamp=_parse_dt(m.group("date"),m.group("time"),date_order),
                sender=m.group("sender").strip(),
                text=m.group("text").strip(),
                media_kind=_media_kind(m.group("text")),
            )
            messages.append(current)
            continue
        if STAMP_RE.match(line):
            current=None
            continue
        if current is not None and line:
            current.text += "\n" + line
            if current.media_kind is None:
                current.media_kind=_media_kind(current.text)

    if not messages:
        raise ValueError("No WhatsApp messages could be parsed. Upload the original WhatsApp ZIP or TXT export.")

    participants=[]
    seen=set()
    for m in messages:
        if m.sender not in seen:
            seen.add(m.sender)
            participants.append(m.sender)

    refs=Counter(m.media_kind for m in messages if m.media_kind)
    inv=dict(media_inventory or {})
    for k,v in refs.items():
        inv[k]=max(inv.get(k,0),v)

    return ParsedChat(
        source_name=source_name,
        messages=messages,
        participants=participants,
        media_inventory=inv,
        text_member_name=source_name,
        language_guess=_guess_language(messages),
        date_order=date_order,
    )

def _read_limited(zf, info):
    if info.file_size>MAX_CHAT_TEXT_BYTES:
        raise ValueError("Chat text inside ZIP is too large.")
    with zf.open(info,"r") as f:
        data=f.read(MAX_CHAT_TEXT_BYTES+1)
    if len(data)>MAX_CHAT_TEXT_BYTES:
        raise ValueError("Chat text exceeded safety limit.")
    return data

def _zip_inventory(zf):
    counts=Counter()
    for info in zf.infolist():
        if info.is_dir():
            continue
        kind=EXT_KIND.get(Path(info.filename).suffix.lower(),"other")
        if kind not in {"text","other"}:
            counts[kind]+=1
    return dict(counts)

def parse_upload(fileobj: BinaryIO, filename: str) -> ParsedChat:
    lower=(filename or "").lower()
    if lower.endswith(".txt"):
        data=fileobj.read(MAX_CHAT_TEXT_BYTES+1)
        if len(data)>MAX_CHAT_TEXT_BYTES:
            raise ValueError("Chat text file is too large.")
        return parse_text(_decode(data),filename)

    if not lower.endswith(".zip"):
        raise ValueError("Please upload a WhatsApp ZIP or TXT export.")

    fileobj.seek(0)
    try:
        with zipfile.ZipFile(fileobj,"r") as zf:
            infos=[i for i in zf.infolist() if not i.is_dir()]
            txts=[i for i in infos if i.filename.lower().endswith(".txt")]
            if not txts:
                raise ValueError("The ZIP contains no TXT chat export.")

            def score(i):
                n=Path(i.filename).name.lower()
                canonical=int(
                    n in {"_chat.txt","chat.txt"} or
                    "whatsapp" in n or
                    "chat" in n or
                    "צ'אט" in n
                )
                return (canonical,i.file_size)

            chosen=sorted(txts,key=score,reverse=True)[0]
            parsed=parse_text(_decode(_read_limited(zf,chosen)),filename,_zip_inventory(zf))
            parsed.text_member_name=chosen.filename
            return parsed
    except zipfile.BadZipFile as e:
        raise ValueError("The uploaded ZIP is damaged or invalid.") from e
