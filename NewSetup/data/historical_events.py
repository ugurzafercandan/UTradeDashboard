"""Historical event data for backtest EVENT-trigger replay (UGT-17/19, item 1).

GDELT DOC 2.0 (the live layer-1 feed) only covers recent months, which is
why event-conditioned triggers never fired in the historical backtests
(UGT-14 diagnosis). This module rebuilds a backfillable event history from
two sources:

1. config/event_history.yaml - hand-curated, dated landmark supply-chain
   disruption events for the five playbook 5.2 windows, each with a
   verifiable source URL.
2. data/caches/events/gdelt_export_events.csv - bulk extract of the GDELT
   2.0 export archive (data.gdeltproject.org, 15-minute event files) for
   the playbook windows, produced by scripts/fetch_gdelt_window_exports.py.

The replay matcher mirrors signals/layer1_scanner.Layer1Scanner._eval_event
keyword logic so backtest EVENT triggers behave like the live scanner.
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import yaml

from newsetup.config import ROOT, load_gdelt_keywords, load_inefficiencies, load_settings
from newsetup.models import Event, Inefficiency, RawSignal

log = logging.getLogger("newsetup.historical_events")

EVENTS_DIR = os.path.join(ROOT, "data", "caches", "events")
GDELT_CSV = os.path.join(EVENTS_DIR, "gdelt_export_events.csv")
HISTORY_YAML = os.path.join(ROOT, "config", "event_history.yaml")

# Shared disruption shock-words appended to every inefficiency's theme
# keywords (identical to Layer1Scanner._keywords extras / fallback list).
# UGT-17/19 fix: the committed scanner's extras list omitted war/attack/
# halt - the very words its own _is_supply_shock direction heuristic uses -
# so war/attack headlines never fired EVENT triggers. The matcher's shock
# vocabulary now equals the direction heuristic's vocabulary; both lists
# are kept identical in scanner and replay.
SHOCK_WORDS = ["export ban", "restriction", "sanction", "disruption",
               "shutdown", "mine strike", "coup", "closure",
               "earthquake", "flood", "ban", "strike", "attack",
               "war", "halt"]


# ------------------------------------------------------------------ load
def _parse_ts(value: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"unparsable timestamp {value!r}")


def load_curated_events() -> list[Event]:
    """Hand-curated landmark events from config/event_history.yaml."""
    if not os.path.exists(HISTORY_YAML):
        return []
    with open(HISTORY_YAML, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    events: list[Event] = []
    for row in doc.get("events", []):
        events.append(Event(
            headline=str(row.get("headline", "")),
            themes=list(row.get("themes", [])),
            goldstein_score=float(row.get("goldstein", 0.0)),
            score=float(row.get("score", 0.0)),
            source=str(row.get("source", "curated")),
            ts=_parse_ts(str(row["ts"])),
        ))
    events.sort(key=lambda e: e.ts)
    return events


def load_gdelt_events() -> list[Event]:
    """GDELT 2.0 export-archive extract (written by the fetch script)."""
    if not os.path.exists(GDELT_CSV):
        return []
    events: list[Event] = []
    with open(GDELT_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            events.append(Event(
                headline=row["headline"],
                themes=[t for t in row.get("themes", "").split("|") if t],
                goldstein_score=float(row.get("goldstein", 0.0)),
                score=float(row.get("score", 0.0)),
                source="gdelt_export",
                ts=_parse_ts(row["ts"]),
            ))
    events.sort(key=lambda e: e.ts)
    return events


def load_all_events() -> list[Event]:
    """Curated + GDELT events, time-sorted."""
    events = load_curated_events() + load_gdelt_events()
    events.sort(key=lambda e: e.ts)
    return events


# ------------------------------------------------------------------ match
def keywords_for(inefficiency: Inefficiency,
                 gdelt_keywords: Optional[dict] = None) -> list[str]:
    """Per-inefficiency keyword list, same construction as the scanner."""
    gdelt_keywords = gdelt_keywords if gdelt_keywords is not None \
        else load_gdelt_keywords()
    themed = gdelt_keywords.get(inefficiency.id) or gdelt_keywords.get(str(inefficiency.id))
    if themed:
        return list(themed) + SHOCK_WORDS
    base = [w.lower() for w in inefficiency.name.replace("/", " ").split()]
    return base + SHOCK_WORDS


def event_passes_threshold(ev: Event,
                           event_score_threshold: float) -> bool:
    """Same gate as Layer1Scanner._eval_event."""
    return ev.score >= event_score_threshold or abs(ev.goldstein_score) >= 5.0


def match_inefficiencies(ev: Event,
                         inefficiencies: list[Inefficiency],
                         gdelt_keywords: Optional[dict] = None,
                         event_score_threshold: float = 0.7) -> list[Inefficiency]:
    """Inefficiencies whose keywords match a passing event."""
    if not event_passes_threshold(ev, event_score_threshold):
        return []
    text = ev.headline.lower()
    out = []
    for ineff in inefficiencies:
        if ineff.trade_type.startswith("No trade"):
            continue
        if any(k in text for k in keywords_for(ineff, gdelt_keywords)):
            out.append(ineff)
    return out


# ------------------------------------------------------------------ replay
class HistoricalEventProvider:
    """EventProvider over the historical store (scanner-compatible)."""

    def __init__(self, events: Optional[list[Event]] = None,
                 since: Optional[datetime] = None,
                 until: Optional[datetime] = None):
        self.events = [e for e in (events if events is not None else load_all_events())
                       if (since is None or e.ts >= since)
                       and (until is None or e.ts <= until)]

    def get_events(self, since_hours: int = 24) -> list[Event]:
        now = self.events[-1].ts if self.events else datetime.now(timezone.utc)
        lo = now - timedelta(hours=since_hours)
        return [e for e in self.events if e.ts >= lo]


def replay_event_signals(events: list[Event],
                         inefficiencies: list[Inefficiency],
                         available_symbols: Optional[set] = None,
                         settings: Optional[dict] = None,
                         cooldown_hours: int = 24,
                         gdelt_keywords: Optional[dict] = None) -> list[RawSignal]:
    """Replay Layer1Scanner._eval_event logic over the event history.

    For each passing event and each keyword-matching inefficiency, emits a
    raw EVENT signal on the inefficiency's first tradeable instrument that
    has cached price data, with a per-inefficiency cooldown. Direction is
    the scanner's supply-shock heuristic (BUY on shock wording or negative
    goldstein, SELL otherwise - i.e. de-escalation short).
    """
    settings = settings or load_settings()
    threshold = float(settings["layer1"]["event_score_threshold"])
    gdelt_keywords = gdelt_keywords if gdelt_keywords is not None \
        else load_gdelt_keywords()
    signals: list[RawSignal] = []
    last_emit: dict[int, datetime] = {}
    for ev in sorted(events, key=lambda e: e.ts):
        for ineff in match_inefficiencies(ev, inefficiencies,
                                          gdelt_keywords, threshold):
            symbol = _symbol_with_data(ineff, available_symbols)
            if symbol is None:
                continue
            prev = last_emit.get(ineff.id)
            if prev is not None and ev.ts - prev < timedelta(hours=cooldown_hours):
                continue
            direction = "BUY" if _is_supply_shock(ev) else "SELL"
            signals.append(RawSignal(
                inefficiency_id=ineff.id,
                inefficiency_name=ineff.name,
                instrument=symbol,
                direction=direction,
                trigger_type="EVENT",
                trigger_description=f"{ev.headline} (score={ev.score:.2f})",
                confidence=min(0.95, 0.5 + abs(ev.goldstein_score) / 20.0
                                + ev.score / 4.0),
                ts=ev.ts,
                thesis="event",
            ))
            last_emit[ineff.id] = ev.ts
    return signals


def _symbol_with_data(inefficiency: Inefficiency,
                      available_symbols: Optional[set]) -> Optional[str]:
    """First tradeable instrument that actually has cached bars.

    Mirrors the scanner's primary_symbol() pick, restricted to symbols the
    backtest can actually price.
    """
    for symbol in inefficiency.tradeable_symbols():
        if available_symbols is None or symbol in available_symbols:
            return symbol
    return None


def _is_supply_shock(ev: Event) -> bool:
    """Same heuristic as Layer1Scanner._is_supply_shock."""
    text = ev.headline.lower()
    shock_words = ("ban", "restriction", "strike", "shutdown", "coup",
                   "closure", "attack", "war", "sanction", "disruption",
                   "earthquake", "flood", "halt")
    return any(w in text for w in shock_words) or ev.goldstein_score < 0
