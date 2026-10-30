from __future__ import annotations
import time, uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import (
    MAX_UPLOAD_BYTES, MAX_UPLOAD_MB, REPORT_LANGUAGES,
    SESSION_TTL_MINUTES, SUPPORTED_RELATIONSHIPS
)
from .metrics import build_metrics
from .narrative import choose_report_language
from .semantic_engine import generate_semantic_report
from .ai_provider import SemanticAnalysisUnavailable, SemanticProvider
from .parser_whatsapp import parse_upload
from .storage import ReportStore

PACKAGE_DIR=Path(__file__).resolve().parent
STATIC_DIR=PACKAGE_DIR/"static"

app=FastAPI(title="JARVIS Conversation Insights",version="0.6.1")
app.mount("/static",StaticFiles(directory=str(STATIC_DIR)),name="static")
store=ReportStore()

@dataclass
class Session:
    created_at: float
    parsed: Any

_sessions={}

def _clean():
    cutoff=time.time()-SESSION_TTL_MINUTES*60
    for sid in [k for k,v in _sessions.items() if v.created_at<cutoff]:
        _sessions.pop(sid,None)

class AnalyzeRequest(BaseModel):
    session_id:str
    user_participant:str
    other_participant:str|None=None
    aliases:dict[str,str]=Field(default_factory=dict)
    relationship_type:str
    relationship_description:str|None=Field(default=None,max_length=500)
    goal:str|None=Field(default=None,max_length=1000)
    language:str="auto"

@app.get("/")
def home():
    return FileResponse(STATIC_DIR/"index.html")

@app.get("/api/health")
def health():
    return {"ok":True,"version":"0.6.1","max_upload_mb":MAX_UPLOAD_MB}

@app.get("/api/semantic-health")
def semantic_health():
    p=SemanticProvider()
    body=p.models()
    ids=p._model_ids(body) if body is not None else []
    return {"server_online":body is not None,"model":p.model,"model_loaded":p.model in ids,"base_url":p.base_url}

@app.get("/api/config")
def config():
    return {
        "max_upload_mb":MAX_UPLOAD_MB,
        "relationship_types":SUPPORTED_RELATIONSHIPS,
        "languages":REPORT_LANGUAGES,
        "privacy":{
            "raw_chat_persisted":False,
            "reports_persisted":True,
            "session_ttl_minutes":SESSION_TTL_MINUTES,
        }
    }

@app.post("/api/upload")
async def upload(file:UploadFile=File(...)):
    _clean()
    total=0
    while True:
        chunk=await file.read(1024*1024)
        if not chunk:
            break
        total+=len(chunk)
        if total>MAX_UPLOAD_BYTES:
            raise HTTPException(413,f"Upload exceeds {MAX_UPLOAD_MB} MB.")
    await file.seek(0)

    try:
        parsed=parse_upload(file.file,file.filename or "chat.zip")
    except ValueError as e:
        raise HTTPException(400,str(e)) from e

    sid=uuid.uuid4().hex
    _sessions[sid]=Session(time.time(),parsed)
    first=next((m.timestamp for m in parsed.messages if m.timestamp),None)
    last=next((m.timestamp for m in reversed(parsed.messages) if m.timestamp),None)
    return {
        "session_id":sid,
        "source_name":parsed.source_name,
        "text_member_name":parsed.text_member_name,
        "participants":parsed.participants,
        "message_count":len(parsed.messages),
        "first_message_at":first,
        "last_message_at":last,
        "language_guess":parsed.language_guess,
        "date_order":parsed.date_order,
        "media_inventory":parsed.media_inventory,
        "raw_chat_saved":False,
    }

@app.post("/api/analyze")
def analyze(req:AnalyzeRequest):
    _clean()
    session=_sessions.get(req.session_id)
    if not session:
        raise HTTPException(410,"Upload session expired. Upload the chat again.")

    allowed={x["id"] for x in SUPPORTED_RELATIONSHIPS}
    if req.relationship_type not in allowed:
        raise HTTPException(400,"Invalid relationship type.")
    if req.relationship_type=="other" and not (req.relationship_description or "").strip():
        raise HTTPException(400,"Describe the relationship when Other is selected.")
    if req.user_participant not in session.parsed.participants:
        raise HTTPException(400,"Choose yourself from the detected participants.")

    aliases={k:(v.strip() if isinstance(v,str) else "") for k,v in req.aliases.items()}
    lang=choose_report_language(req.language,aliases,session.parsed.language_guess)

    for p in session.parsed.participants:
        if aliases.get(p):
            continue
        if p.lower()=="you":
            aliases[p]="אני" if lang=="he" else "Me"
        else:
            aliases[p]=p

    metrics=build_metrics(session.parsed,req.relationship_type,aliases)
    try:
        report=generate_semantic_report(
            session.parsed, metrics, req.relationship_type,
            (req.relationship_description or "").strip() or None,
            (req.goal or "").strip() or None,
            req.user_participant, req.other_participant, aliases, lang,
        )
    except SemanticAnalysisUnavailable as e:
        raise HTTPException(503, "Semantic Report 1 is unavailable. Start the local JARVIS/LM Studio model and try again. " + str(e)) from e
    except ValueError as e:
        raise HTTPException(422, "The semantic writer could not produce a grounded report: " + str(e)) from e
    store.save(report)
    return report.model_dump(mode="json")

@app.get("/api/reports/{report_id}")
def get_report(report_id:str):
    r=store.get(report_id)
    if not r:
        raise HTTPException(404,"Report not found.")
    return r

@app.delete("/api/reports/{report_id}")
def delete_report(report_id:str):
    return {"deleted":store.delete(report_id)}
