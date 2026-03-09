from __future__ import annotations

import email
import imaplib
import os
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header

from agentic_updates.connectors.base import BaseConnector
from agentic_updates.models import Signal, SignalSource


class EmailConnector(BaseConnector):
    source = SignalSource.EMAIL
    file_name = "email_updates.json"

    def fetch_updates(self) -> list[Signal]:
        host = os.getenv("EMAIL_IMAP_HOST", "").strip()
        username = os.getenv("EMAIL_IMAP_USERNAME", "").strip()
        password = os.getenv("EMAIL_IMAP_PASSWORD", "").strip()
        folder = os.getenv("EMAIL_IMAP_FOLDER", "INBOX").strip()

        if not host or not username or not password:
            return self._fallback_file_signals()

        lookback_days = int(os.getenv("EMAIL_LOOKBACK_DAYS", "2"))
        max_messages = int(os.getenv("EMAIL_MAX_MESSAGES", "30"))
        since_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%d-%b-%Y")

        try:
            client = imaplib.IMAP4_SSL(host)
            client.login(username, password)
            client.select(folder)
            status, data = client.search(None, "SINCE", since_date)
            if status != "OK":
                client.logout()
                return self._fallback_file_signals()

            message_ids = data[0].split()[-max_messages:]
            signals: list[Signal] = []
            for raw_id in reversed(message_ids):
                status, msg_data = client.fetch(raw_id, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                subject = self._decode_header_value(msg.get("Subject", ""))
                sender = self._decode_header_value(msg.get("From", ""))
                date_value = msg.get("Date")
                body = self._extract_body(msg)
                task_key = self._extract_task_key(subject + " " + body)

                ts = self._parse_email_date(date_value)
                row = {
                    "id": f"email-{raw_id.decode(errors='ignore')}",
                    "title": subject or "Email update",
                    "body": body,
                    "owner": sender,
                    "timestamp": ts.isoformat(),
                    "tags": ["notification"],
                    "urgency_hint": "high" if any(k in (subject + " " + body).lower() for k in ["urgent", "action required", "asap"]) else None,
                    "task_key": task_key,
                    "raw": {"from": sender, "date": date_value},
                }
                signals.append(self._to_signal(row))

            client.close()
            client.logout()
            return signals or self._fallback_file_signals()
        except Exception:
            return self._fallback_file_signals()

    def _decode_header_value(self, value: str) -> str:
        chunks = decode_header(value)
        parts: list[str] = []
        for part, enc in chunks:
            if isinstance(part, bytes):
                parts.append(part.decode(enc or "utf-8", errors="ignore"))
            else:
                parts.append(part)
        return "".join(parts).strip()

    def _extract_body(self, msg: email.message.Message) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition", ""))
                if ctype == "text/plain" and "attachment" not in disp.lower():
                    payload = part.get_payload(decode=True) or b""
                    return payload.decode(part.get_content_charset() or "utf-8", errors="ignore").strip()[:2000]
        else:
            payload = msg.get_payload(decode=True) or b""
            return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore").strip()[:2000]
        return ""

    def _parse_email_date(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            dt = email.utils.parsedate_to_datetime(value)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)

    def _extract_task_key(self, text: str) -> str | None:
        match = re.search(r"\b[A-Z]{2,10}-\d{1,6}\b", text)
        return match.group(0) if match else None
