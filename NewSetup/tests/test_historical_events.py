"""Tests for the historical event data layer (UGT-17/19 item 1)."""

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.historical_events import (HistoricalEventProvider, keywords_for,
                                    load_curated_events, match_inefficiencies,
                                    replay_event_signals, SHOCK_WORDS)
from newsetup.config import load_inefficiencies
from newsetup.models import Event


def _ev(headline, goldstein=-8.0, score=0.9, ts="2021-03-23T07:40:00Z"):
    return Event(headline=headline, themes=[], goldstein_score=goldstein,
                 score=score, source="test",
                 ts=datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
                     tzinfo=timezone.utc))


def test_curated_events_load_and_are_dated():
    events = load_curated_events()
    assert len(events) >= 30
    for ev in events:
        assert ev.headline
        assert ev.ts.year >= 2020
        assert ev.source.startswith("http")


def test_curated_events_cover_all_five_playbook_windows():
    from backtest.event_backtests import PLAYBOOK_WINDOWS
    events = load_curated_events()
    for name, (start, end, _d) in PLAYBOOK_WINDOWS.items():
        lo = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        hi = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        assert any(lo <= e.ts <= hi for e in events), name


def test_suez_headline_matches_red_sea_inefficiency():
    ineffs = load_inefficiencies()
    matched = match_inefficiencies(_ev("Container ship Ever Given runs aground "
                                       "and blocks the Suez Canal"), ineffs)
    names = {i.name for i in matched}
    assert "Red Sea / Suez" in names


def test_shock_word_headlines_match_broadly():
    ineffs = load_inefficiencies()
    matched = match_inefficiencies(_ev("Russia launches war on Ukraine"), ineffs)
    assert len(matched) >= 20          # 'war' is a shared shock word


def test_low_score_events_are_gated():
    ineffs = load_inefficiencies()
    ev = _ev("Container ship Ever Given blocks the Suez Canal",
             goldstein=-1.0, score=0.2)
    assert match_inefficiencies(ev, ineffs) == []


def test_deescalation_event_directions_sell():
    ineffs = load_inefficiencies()
    signals = replay_event_signals(
        [_ev("Ever Given refloated; Suez Canal traffic resumes",
             goldstein=4.0, score=0.85)],
        ineffs, available_symbols=None)
    assert signals
    assert all(s.direction == "SELL" for s in signals)


def test_replay_respects_cooldown_and_symbol_availability():
    ineffs = load_inefficiencies()
    ev1 = _ev("Houthi attack on cargo ship in the Red Sea",
              ts="2023-11-19T12:00:00Z")
    ev2 = _ev("Houthi attack on another cargo ship in the Red Sea",
              ts="2023-11-19T18:00:00Z")
    signals = replay_event_signals([ev1, ev2], ineffs,
                                   available_symbols={"QQQ.US"})
    # cooldown: same inefficiency fires once; instruments limited to cache
    keys = {(s.inefficiency_id, s.instrument) for s in signals}
    assert len(signals) == len(keys)
    assert all(s.instrument == "QQQ.US" for s in signals)


def test_event_provider_serves_recent_window():
    ev1 = _ev("one", ts="2020-03-10T13:00:00Z")
    ev2 = _ev("two", ts="2020-03-12T13:00:00Z")
    provider = HistoricalEventProvider(events=[ev1, ev2])
    recent = provider.get_events(since_hours=24)
    assert recent == [ev2]
