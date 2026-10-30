from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    timestamp: datetime | None = None
    sender: str
    text: str
    media_kind: str | None = None

class ParsedChat(BaseModel):
    source_name: str
    messages: list[Message]
    participants: list[str]
    media_inventory: dict[str, int] = Field(default_factory=dict)
    text_member_name: str | None = None
    language_guess: str = "unknown"
    date_order: str = "unknown"

class ParticipantStats(BaseModel):
    raw_name: str
    name: str
    messages: int = 0
    characters: int = 0
    questions: int = 0
    gratitude: int = 0
    apologies: int = 0
    affection: int = 0
    warmth: int = 0
    boundaries: int = 0
    planning: int = 0
    session_starts: int = 0
    median_reply_seconds: float | None = None

class ConversationMetrics(BaseModel):
    total_messages: int
    participants: list[ParticipantStats]
    dated_messages: int = 0
    first_message_at: datetime | None = None
    last_message_at: datetime | None = None
    days_since_last_message: int | None = None
    sessions: int = 0
    relationship_type: str = "other"
    media_inventory: dict[str, int] = Field(default_factory=dict)
    peak_day: str | None = None
    peak_day_messages: int = 0
    longest_silence_hours: float | None = None
    longest_active_streak_days: int = 0
    peak_hour: int | None = None
    after_22_percent: float = 0.0
    hourly_counts: list[int] = Field(default_factory=lambda:[0]*24)
    daily_activity: list[dict[str, Any]] = Field(default_factory=list)
    peak_day_details: dict[str, Any] = Field(default_factory=dict)

class FirstReadReport(BaseModel):
    report_id: str
    language: str
    title: str
    subtitle: str
    paragraphs: list[str]
    highlights: list[str] = Field(default_factory=list)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    numbers: dict[str, Any]
    metrics: ConversationMetrics
    relationship_type: str
    relationship_description: str | None = None
    goal: str | None = None
    created_at: datetime
