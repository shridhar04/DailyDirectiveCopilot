from __future__ import annotations

from agentic_updates.connectors.base import BaseConnector
from agentic_updates.models import SignalSource


class MeetingNotesConnector(BaseConnector):
    source = SignalSource.MEETING_NOTES
    file_name = "meeting_notes.json"