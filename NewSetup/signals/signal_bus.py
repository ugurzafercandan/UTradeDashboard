"""Signal bus: routes sized signals to consumers and persists the
Python -> MQL5 signal file (active_signals.json, playbook section 4.4)."""

from __future__ import annotations

import json
import logging
import os

from newsetup.models import SizedSignal, iso, utcnow

log = logging.getLogger("newsetup.signal_bus")


class SignalBus:
    def __init__(self, signals_path: str | None = None, settings: dict | None = None):
        self.settings = settings or {}
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.signals_path = signals_path or os.path.join(
            root, self.settings.get("paths", {}).get("signals_file", "active_signals.json"))
        self.history: list[dict] = []

    def emit(self, sized: list[SizedSignal]) -> list[dict]:
        """Write the current signal set to active_signals.json and return it."""
        payload = {
            "last_updated": iso(utcnow()),
            "signals": [s.to_dict() for s in sized],
        }
        self.history.append(payload)
        with open(self.signals_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        log.info("SignalBus: emitted %d signals -> %s", len(sized), self.signals_path)
        return payload["signals"]

    def load(self) -> dict:
        """Read back the current signal file (what the MQL5 EA would read)."""
        if not os.path.exists(self.signals_path):
            return {"last_updated": None, "signals": []}
        with open(self.signals_path, "r", encoding="utf-8") as f:
            return json.load(f)
