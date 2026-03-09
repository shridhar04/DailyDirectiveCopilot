from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SignalSource(str, Enum):
    JIRA = "jira"
    SLACK = "slack"
    EMAIL = "email"
    MEETING_NOTES = "meeting_notes"


class Signal(BaseModel):
    id: str
    source: SignalSource
    title: str
    body: str
    owner: str | None = None
    timestamp: datetime
    tags: list[str] = Field(default_factory=list)
    urgency_hint: str | None = None
    task_key: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class UnifiedTask(BaseModel):
    id: str
    title: str
    description: str
    owners: list[str] = Field(default_factory=list)
    sources: list[SignalSource] = Field(default_factory=list)
    linked_signal_ids: list[str] = Field(default_factory=list)
    urgency_score: float = 0.0
    urgency_reason: str = ""


class SummaryOutput(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    bullets: list[str] = Field(default_factory=list)
    tasks: list[UnifiedTask] = Field(default_factory=list)