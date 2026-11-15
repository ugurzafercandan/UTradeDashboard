"""Tests for data providers (GDELT, sentiment, prices) and monitoring."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.gdelt_monitor import GDELTMonitor
from data.sentiment import FinBERTSentiment
from data.price_provider import SyntheticPriceProvider, MT5PriceProvider
from monitoring.alerter import Alerter
from monitoring.daily_report import daily_report


class TestGDELT:
    def test_offline_fixtures_available(self):
        events = GDELTMonitor(offline=True).get_events()
        assert len(events) >= 3
        assert any("export ban" in e.headline for e in events)
        assert all(-10 <= e.goldstein_score <= 10 for e in events)

    def test_events_have_scores(self):
        events = GDELTMonitor(offline=True).get_events()
        assert all(0 <= e.score <= 1 for e in events)


class TestSentiment:
    def test_lexicon_negative(self):
        s = FinBERTSentiment(use_transformers=False)
        assert s.score("China export ban causes supply shortage crisis") < 0

    def test_lexicon_positive(self):
        s = FinBERTSentiment(use_transformers=False)
        assert s.score("Canal reopened; congestion resolved") > 0

    def test_neutral(self):
        s = FinBERTSentiment(use_transformers=False)
        assert s.score("Company reports quarterly revenue") == 0.0

    def test_theme_cache(self):
        s = FinBERTSentiment(use_transformers=False)
        assert s.latest_for_theme("anything") is None
        s.ingest_headlines(["copper mine strike halted", "copper mine strike continues"])
        assert s.latest_for_theme("copper") is not None


class TestPriceProviders:
    def test_synthetic_deterministic(self):
        a = SyntheticPriceProvider().get_series("COPPER", 250)
        b = SyntheticPriceProvider().get_series("COPPER", 250)
        assert len(a) == len(b) == 250
        assert [x.close for x in a] == [x.close for x in b]
        assert all(x.low <= x.close <= x.high for x in a)

    def test_synthetic_respects_lookback(self):
        short = SyntheticPriceProvider().get_series("XAUUSD", 10)
        assert len(short) == 10


class TestMonitoring:
    def test_alerter_records_and_levels(self):
        a = Alerter()
        a.alert("warning", "test")
        a.circuit_breaker("dd_pause", "5% drawdown")
        assert a.history[0]["level"] == "warning"
        assert a.history[1]["level"] == "critical"

    def test_daily_report_renders(self):
        class FakeBroker:
            account_state = type("A", (), {"balance": 10000.0, "equity": 10000.0,
                                          "margin_used": 0.0, "open_positions": 0})()
            open_trades = []
            closed_trades = []
            def day_pnl(self):
                return 0.0
        report = daily_report(FakeBroker(), {"signals": []})
        assert "Daily Report" in report
        assert "Equity" in report
