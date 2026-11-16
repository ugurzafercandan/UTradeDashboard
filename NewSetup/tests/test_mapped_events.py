"""Tests for data.mapped_events (UGT-23 event-dataset replay)."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mapped_events import (DEFAULT_GROUPS, load_mapped_entries,
                                load_mapped_signals,
                                replay_mapped_event_signals)
from newsetup.models import Inefficiency


def _ineff(iid, name, symbols, trade_type="Equity CFD"):
    return Inefficiency(id=iid, name=name, category="TECH_INFRA",
                        concentration="", instruments={"equity": symbols},
                        trade_type=trade_type)


def _entry(eid, date, ids, direction, group="supplement_2017_2019",
           goldstein=-6.0):
    return {"id": eid, "date": date, "group": group, "headline": f"news {eid}",
            "source": "https://example.com", "goldstein": goldstein,
            "themes": ["test"], "inefficiency_ids": ids,
            "direction": direction, "date_confidence": "high"}


class TestDataset:
    def test_committed_dataset_loads_and_has_unique_groups(self):
        entries = load_mapped_entries()
        assert len(entries) == 101
        groups = {e["group"] for e in entries}
        assert "supplement_2017_2019" in groups
        assert "holdout_2025_2026" in groups
        ids = [e["id"] for e in entries]
        assert len(set(ids)) == len(ids)

    def test_default_groups_exclude_playbook_windows(self):
        entries = load_mapped_entries(DEFAULT_GROUPS)
        assert entries, "default groups must be non-empty"
        assert all(e["group"] in DEFAULT_GROUPS for e in entries)

    def test_all_groups_option_includes_windows(self):
        entries = load_mapped_entries(None)
        assert any(e["group"] == "covid_2020" for e in entries)


class TestReplay:
    def test_curated_direction_and_card_mapping_respected(self):
        ineffs = [_ineff(17, "Container Imbalance", ["ZIM.US"]),
                  _ineff(29, "TSMC Concentration", ["SOXX.US"])]
        entries = [_entry("a", "2018-03-01", [17], "BUY"),
                   _entry("b", "2018-04-02", [29], "SELL")]
        signals = replay_mapped_event_signals(
            entries, ineffs, available_symbols={"ZIM.US", "SOXX.US"})
        assert len(signals) == 2
        by_card = {s.inefficiency_id: s for s in signals}
        assert by_card[17].direction == "BUY"
        assert by_card[29].direction == "SELL"
        assert by_card[17].trigger_type == "EVENT"
        assert by_card[17].thesis == "event"
        assert by_card[17].instrument == "ZIM.US"

    def test_per_card_cooldown_suppresses_same_day_second_event(self):
        ineffs = [_ineff(17, "Container Imbalance", ["ZIM.US"])]
        entries = [_entry("a", "2018-03-01", [17], "BUY"),
                   _entry("b", "2018-03-01", [17], "BUY")]
        signals = replay_mapped_event_signals(
            entries, ineffs, available_symbols={"ZIM.US"})
        assert len(signals) == 1

    def test_symbol_restricted_to_available(self):
        ineffs = [_ineff(17, "Container Imbalance", ["ZIM.US", "MATX.US"]),
                  _ineff(29, "TSMC Concentration", ["SOXX.US"])]
        entries = [_entry("a", "2018-03-01", [17, 29], "BUY")]
        signals = replay_mapped_event_signals(
            entries, ineffs, available_symbols={"MATX.US"})
        assert len(signals) == 1
        assert signals[0].instrument == "MATX.US"

    def test_no_trade_cards_and_invalid_entries_skipped(self):
        ineffs = [_ineff(36, "Skilled Labor", [], trade_type="No trade"),
                  _ineff(17, "Container Imbalance", ["ZIM.US"])]
        entries = [_entry("a", "2018-03-01", [36, 17], "BUY"),
                   _entry("bad1", "2018-03-02", [17], "HOLD"),
                   _entry("bad2", "2018-03-02", [], "BUY")]
        signals = replay_mapped_event_signals(
            entries, ineffs, available_symbols={"ZIM.US"})
        assert len(signals) == 1
        assert signals[0].inefficiency_id == 17

    def test_start_end_window_filter(self):
        ineffs = [_ineff(17, "Container Imbalance", ["ZIM.US"])]
        entries = [_entry("a", "2018-03-01", [17], "BUY"),
                   _entry("b", "2025-06-01", [17], "SELL")]
        signals = replay_mapped_event_signals(
            entries, ineffs, available_symbols={"ZIM.US"},
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end=datetime(2025, 12, 31, tzinfo=timezone.utc))
        assert len(signals) == 1
        assert signals[0].direction == "SELL"

    def test_signal_ts_is_entry_date_midnight_utc(self):
        ineffs = [_ineff(17, "Container Imbalance", ["ZIM.US"])]
        signals = replay_mapped_event_signals(
            [_entry("a", "2018-03-01", [17], "BUY")], ineffs,
            available_symbols={"ZIM.US"})
        assert signals[0].ts == datetime(2018, 3, 1, tzinfo=timezone.utc)


class TestConvenienceLoader:
    def test_load_mapped_signals_runs_on_real_dataset(self):
        from newsetup.config import load_inefficiencies
        ineffs = load_inefficiencies()
        symbols = {"EURUSD", "XAUUSD", "WHEAT", "SOXX.US", "USDCNH",
                   "XTIUSD", "AUDUSD", "USDJPY", "AA.US", "COPPER"}
        signals = load_mapped_signals(ineffs, available_symbols=symbols)
        assert signals, "mapped events must fire for cached symbols"
        assert all(s.trigger_type == "EVENT" for s in signals)
        # every signal's instrument must be priced in the available set
        assert all(s.instrument in symbols for s in signals)
        # coverage: both train supplement and holdout periods represented
        years = {s.ts.year for s in signals}
        assert any(y <= 2019 for y in years), "train-year coverage expected"
        assert any(y >= 2025 for y in years), "holdout coverage expected"
