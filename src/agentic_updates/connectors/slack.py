from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

from agentic_updates.connectors.base import BaseConnector
from agentic_updates.models import Signal, SignalSource


class SlackConnector(BaseConnector):
    source = SignalSource.SLACK
    file_name = "slack_updates.json"

    def fetch_updates(self) -> list[Signal]:
        token = os.getenv("SLACK_BOT_TOKEN", "").strip()
        channel_ids = [c.strip() for c in os.getenv("SLACK_CHANNEL_IDS", "").split(",") if c.strip()]
        if not token or not channel_ids:
            return self._fallback_file_signals()

        lookback_hours = int(os.getenv("SLACK_LOOKBACK_HOURS", "24"))
        limit = int(os.getenv("SLACK_MESSAGES_PER_CHANNEL", "50"))

        oldest_ts = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp()
        headers = {"Authorization": f"Bearer {token}"}

        signals: list[Signal] = []

        for channel in channel_ids:
            try:
                resp = requests.get(
                    "https://slack.com/api/conversations.history",
                    headers=headers,
                    params={"channel": channel, "oldest": oldest_ts, "limit": limit},
                    timeout=20,
                )
                resp.raise_for_status()
                payload = resp.json()
                if not payload.get("ok"):
                    continue
            except Exception:
                continue

            for msg in payload.get("messages", []):
                text = (msg.get("text") or "").strip()
                if not text:
                    continue

                ts_val = msg.get("ts")
                if not ts_val:
                    continue

                try:
                    msg_dt = datetime.fromtimestamp(float(ts_val), tz=timezone.utc)
                except ValueError:
                    continue

                title = text[:90]
                row = {
                    "id": f"slack-{channel}-{ts_val}",
                    "title": title,
                    "body": text,
                    "owner": msg.get("user") or msg.get("username"),
                    "timestamp": msg_dt.isoformat(),
                    "tags": ["channel:" + channel],
                    "urgency_hint": "high" if any(k in text.lower() for k in ["urgent", "blocker", "asap"]) else None,
                    "task_key": self._extract_task_key(text),
                    "raw": {"channel": channel, "thread_ts": msg.get("thread_ts")},
                }
                signals.append(self._to_signal(row))

        return signals or self._fallback_file_signals()

    def _extract_task_key(self, text: str) -> str | None:
        import re

        match = re.search(r"\b[A-Z]{2,10}-\d{1,6}\b", text)
        return match.group(0) if match else None
