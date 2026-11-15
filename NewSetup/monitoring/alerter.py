"""Alerting (playbook 8.1): log-based alerts with optional Telegram channel."""

from __future__ import annotations

import json
import logging
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger("newsetup.alerter")

LEVELS = ("info", "warning", "critical")


class Alerter:
    def __init__(self, telegram_token: str | None = None, telegram_chat_id: str | None = None,
                 settings: dict | None = None):
        self.telegram_token = telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.history: list[dict] = []

    def alert(self, level: str, message: str) -> None:
        if level not in LEVELS:
            level = "info"
        entry = {"level": level, "message": message}
        self.history.append(entry)
        (log.warning if level != "info" else log.info)("ALERT[%s]: %s", level, message)
        if level == "critical" and self.telegram_token and self.telegram_chat_id:
            self._send_telegram(message)

    def circuit_breaker(self, breaker: str, detail: str = "") -> None:
        self.alert("critical", f"CIRCUIT BREAKER {breaker}: {detail}")

    def _send_telegram(self, text: str) -> bool:
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = urlencode({"chat_id": self.telegram_chat_id, "text": text}).encode()
            with urlopen(Request(url, data=data), timeout=10) as resp:
                return resp.status == 200
        except Exception as exc:                              # noqa: BLE001
            log.warning("telegram alert failed: %s", exc)
            return False
