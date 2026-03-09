from __future__ import annotations

from agentic_updates.connectors.base import BaseConnector
from agentic_updates.models import Signal


class BaseAgent:
    name: str

    def __init__(self,connector: BaseConnector) -> None:
        self.connector = connector

    def run(self) -> list[Signal]:
        return self.connector.fetch_updates()    