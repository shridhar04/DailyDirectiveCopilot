from __future__ import annotations

from typing import TypedDict

from agentic_updates.models import Signal, SummaryOutput, UnifiedTask

class WorkflowState(TypedDict):
    signals: list[Signal]
    tasks: list[UnifiedTask]
    summary: SummaryOutput