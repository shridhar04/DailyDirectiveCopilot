from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

from agentic_updates.connectors.base import BaseConnector
from agentic_updates.models import Signal, SignalSource


class JiraConnector(BaseConnector):
    source = SignalSource.JIRA
    file_name = "jira_updates.json"

    def fetch_updates(self) -> list[Signal]:
        base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
        user_email = os.getenv("JIRA_USER_EMAIL", "").strip()
        api_token = os.getenv("JIRA_API_TOKEN", "").strip()

        if not base_url or not user_email or not api_token:
            return self._fallback_file_signals()

        lookback_days = int(os.getenv("JIRA_LOOKBACK_DAYS", "3"))
        max_results = int(os.getenv("JIRA_MAX_RESULTS", "50"))
        jql = os.getenv(
            "JIRA_JQL",
            f"updated >= -{lookback_days}d ORDER BY priority DESC, updated DESC",
        )

        url = f"{base_url}/rest/api/3/search"
        headers = {"Accept": "application/json"}
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,description,assignee,priority,updated,labels,status",
        }

        try:
            resp = requests.get(
                url,
                headers=headers,
                params=params,
                auth=(user_email, api_token),
                timeout=20,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            return self._fallback_file_signals()

        issues = payload.get("issues", [])
        now = datetime.now(timezone.utc)
        min_ts = now - timedelta(days=lookback_days)

        signals: list[Signal] = []
        for item in issues:
            fields = item.get("fields", {})
            updated = fields.get("updated")
            if not updated:
                continue
            updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if updated_dt < min_ts:
                continue

            desc = fields.get("description")
            desc_text = self._flatten_jira_description(desc)
            assignee = fields.get("assignee") or {}
            priority = (fields.get("priority") or {}).get("name", "")

            row = {
                "id": item.get("id") or item.get("key"),
                "title": fields.get("summary", ""),
                "body": desc_text,
                "owner": assignee.get("displayName"),
                "timestamp": updated_dt.isoformat(),
                "tags": fields.get("labels", []),
                "urgency_hint": priority.lower() if priority else None,
                "task_key": item.get("key"),
                "raw": {
                    "status": (fields.get("status") or {}).get("name"),
                    "priority": priority,
                },
            }
            signals.append(self._to_signal(row))

        return signals or self._fallback_file_signals()

    def _flatten_jira_description(self, desc: object) -> str:
        if isinstance(desc, str):
            return desc
        if not isinstance(desc, dict):
            return ""

        parts: list[str] = []

        def walk(node: object) -> None:
            if isinstance(node, dict):
                text = node.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
                for child in node.get("content", []) or []:
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)

        walk(desc)
        return " ".join(parts)
