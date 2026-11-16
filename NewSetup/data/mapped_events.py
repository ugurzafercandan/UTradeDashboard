"""UGT-23 mapped historical events: explicit per-card event replay.

The UGT-17/19 event store (data/historical_events.py) maps news to
inefficiency cards by keyword matching and derives direction from the
scanner's supply-shock heuristic - a faithful mirror of the live layer-1
scanner, used for the five playbook windows.

This module adds the UGT-23 curated dataset (config/historical_events.yaml,
101 dated events, committed e0872cc) as a second event stream whose card
mapping (inefficiency_ids) and trade direction (BUY = long proxy on
disruption/squeeze, SELL = short on glut/demand destruction) are curated
PER EVENT explicitly instead of derived from headline wording. Its unique
coverage vs. the UGT-19 store:

  - supplement_2017_2019 (20 events): walk-forward TRAIN years
  - holdout_2025_2026    (25 events): the untouched holdout evaluation

so event-conditioned triggers exist across the whole walk-forward period
(2017-01 .. cache end), not only inside the five playbook windows.

Signal shape mirrors data.historical_events.replay_event_signals
(EVENT trigger, thesis='event', same confidence formula) so layers 2-3
treat both streams identically.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

import yaml

from newsetup.config import ROOT
from newsetup.models import Inefficiency, RawSignal

log = logging.getLogger("newsetup.mapped_events")

MAPPED_YAML = os.path.join(ROOT, "config", "historical_events.yaml")

# The three window groups duplicate the UGT-19 store's window coverage
# (38 curated + GDELT extract) - including them here would double-count
# the same real-world news as two signals. Only the groups the other
# store does NOT cover replay by default.
DEFAULT_GROUPS = ("supplement_2017_2019", "holdout_2025_2026")


def load_mapped_entries(groups: Optional[Iterable[str]] = None) -> list[dict]:
    """Raw UGT-23 dataset entries, optionally filtered by group."""
    if not os.path.exists(MAPPED_YAML):
        return []
    with open(MAPPED_YAML, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    entries = list(doc.get("events") or [])
    if groups is not None:
        allowed = set(groups)
        entries = [e for e in entries if e.get("group") in allowed]
    entries.sort(key=lambda e: str(e.get("date", "")))
    return entries


def _entry_ts(entry: dict) -> datetime:
    """Dataset dates are first-report UTC dates; the replay timestamp is
    that day's 00:00 UTC so signals resolve at the day's first bar."""
    return datetime.strptime(str(entry["date"]), "%Y-%m-%d") \
        .replace(tzinfo=timezone.utc)


def _entry_score(entry: dict) -> float:
    """Scanner relevance score; curated >= 0.85 mirrors the UGT-19 store's
    curated-event convention and clears the 0.7 layer-1 threshold."""
    return max(0.85, min(1.0, abs(float(entry.get("goldstein", 0.0))) / 10.0))


def _symbol_with_data(inefficiency: Inefficiency,
                      available_symbols: Optional[set]) -> Optional[str]:
    """First tradeable instrument that has cached bars (scanner's
    primary_symbol() pick restricted to priced symbols)."""
    for symbol in inefficiency.tradeable_symbols():
        if available_symbols is None or symbol in available_symbols:
            return symbol
    return None


def replay_mapped_event_signals(entries: list[dict],
                                inefficiencies: list[Inefficiency],
                                available_symbols: Optional[set] = None,
                                cooldown_hours: int = 24,
                                start: Optional[datetime] = None,
                                end: Optional[datetime] = None) -> list[RawSignal]:
    """Replay the UGT-23 curated dataset as EVENT signals.

    For each entry (date-sorted) and each explicitly mapped inefficiency
    that has priced data, emits one raw EVENT signal on the card's first
    cached tradeable symbol at the event's first-report date, with the
    entry's curated direction and a per-card cooldown. Entries with no
    direction/inefficiency_ids are skipped (schema-invalid).
    """
    by_id = {ineff.id: ineff for ineff in inefficiencies}
    signals: list[RawSignal] = []
    last_emit: dict[int, datetime] = {}
    for entry in entries:
        ids = entry.get("inefficiency_ids") or []
        direction = entry.get("direction")
        if direction not in ("BUY", "SELL") or not ids:
            continue
        ts = _entry_ts(entry)
        if start is not None and ts < start:
            continue
        if end is not None and ts > end:
            continue
        headline = str(entry.get("headline", ""))[:120]
        goldstein = float(entry.get("goldstein", 0.0))
        score = _entry_score(entry)
        for ineff_id in ids:
            ineff = by_id.get(int(ineff_id))
            if ineff is None or ineff.trade_type.startswith("No trade"):
                continue
            symbol = _symbol_with_data(ineff, available_symbols)
            if symbol is None:
                continue
            prev = last_emit.get(ineff.id)
            if prev is not None and ts - prev < timedelta(hours=cooldown_hours):
                continue
            signals.append(RawSignal(
                inefficiency_id=ineff.id,
                inefficiency_name=ineff.name,
                instrument=symbol,
                direction=direction,
                trigger_type="EVENT",
                trigger_description=f"{headline} (mapped card {ineff.id}, "
                                    f"score={score:.2f})",
                confidence=min(0.95, 0.5 + abs(goldstein) / 20.0 + score / 4.0),
                ts=ts,
                thesis="event",
            ))
            last_emit[ineff.id] = ts
    return signals


def load_mapped_signals(inefficiencies: list[Inefficiency],
                        available_symbols: Optional[set] = None,
                        groups: Optional[Iterable[str]] = None,
                        cooldown_hours: int = 24) -> list[RawSignal]:
    """Convenience: load the dataset and replay it (default groups)."""
    entries = load_mapped_entries(groups)
    return replay_mapped_event_signals(entries, inefficiencies,
                                       available_symbols=available_symbols,
                                       cooldown_hours=cooldown_hours)
