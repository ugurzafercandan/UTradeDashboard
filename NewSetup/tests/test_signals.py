"""Tests for the layer 1-3 signal pipeline (playbook sections 4.1-4.3)."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from newsetup.config import load_settings
from newsetup.models import (AccountState, Event, PriceBar, RawSignal)
from signals.layer1_scanner import Layer1Scanner
from signals.layer2_confirmation import Layer2Confirmation
from signals.layer3_portfolio import Layer3PortfolioManager
from signals.signal_bus import SignalBus
from data.gdelt_monitor import GDELTMonitor
from data.sentiment import FinBERTSentiment
from data.price_provider import SyntheticPriceProvider


# ---------------------------------------------------------------- helpers
class FakePrices:
    """Declining then spiking series for deterministic scanner checks."""

    def __init__(self, closes):
        now = datetime.now(timezone.utc)
        self.bars = [
            PriceBar(ts=now - timedelta(days=len(closes) - i),
                    open=c, high=c * 1.01, low=c * 0.99, close=c)
            for i, c in enumerate(closes)
        ]

    def get_series(self, symbol, lookback_days=250):
        return self.bars


def make_settings():
    s = load_settings()
    return s


# ---------------------------------------------------------------- layer 1
class TestLayer1Scanner:
    def test_all_40_inefficiencies_loaded(self):
        scanner = Layer1Scanner(GDELTMonitor(offline=True), FakePrices([100] * 30))
        assert len(scanner.inefficiencies) == 40
        assert all(len(i.triggers) >= 1 for i in scanner.inefficiencies)

    def test_supply_shock_event_emits_buy_signal(self):
        events = GDELTMonitor(offline=True)
        scanner = Layer1Scanner(events, FakePrices([100] * 30))
        # fixture contains a rare earth export ban event
        sigs = scanner.scan_all()
        re_sigs = [s for s in sigs if s.inefficiency_id == 8]
        assert re_sigs, "rare earth export ban fixture should fire inefficiency #8"
        assert re_sigs[0].direction == "BUY"
        assert re_sigs[0].trigger_type == "EVENT"

    def test_price_spike_emits_signal(self):
        class NoEvents:
            def get_events(self, since_hours=24):
                return []
        # 3%+ single-bar drop -> BUY dip-trigger for Helium's primary symbol
        prices = FakePrices([100.0, 99.0, 100.0, 101.0, 100.5, 97.0, 95.0, 100.0])
        scanner = Layer1Scanner(NoEvents(), prices)
        sigs = scanner.scan_inefficiency(scanner.inefficiencies[0])  # Helium -> LIN.US
        assert sigs and sigs[0].trigger_type == "PRICE"

    def test_illiquid_inefficiencies_skipped(self):
        scanner = Layer1Scanner(GDELTMonitor(offline=True), FakePrices([100] * 30))
        vanilla = next(i for i in scanner.inefficiencies if i.name == "Vanilla")
        assert vanilla.trade_type.startswith("No trade")
        assert scanner.scan_inefficiency(vanilla) == []


# ---------------------------------------------------------------- layer 2
class TestLayer2Confirmation:
    def _raw(self, direction="BUY"):
        return RawSignal(inefficiency_id=38, inefficiency_name="Copper",
                        instrument="COPPER", direction=direction,
                        trigger_type="EVENT", trigger_description="mine strike",
                        confidence=0.8)

    def test_confirms_event_with_headroom(self):
        # event BUY needs RSI headroom (< overbought); uptrend keeps RSI
        # moderate, so the event thesis confirms by design
        closes = [200.0 + i * 0.5 for i in range(210)]      # rising trend
        closes += [320.0 - 8.0 * i for i in range(1, 8)]   # sharp pullback
        prices = FakePrices(closes)
        conf = Layer2Confirmation(prices, None, settings=make_settings())
        result = conf.confirm(self._raw("BUY"))
        assert result.confirmed
        assert result.score >= conf.min_score
        assert any("RSI" in r for r in result.reasons)
        assert any("event" in r for r in result.reasons)

    def test_confirms_continuation_buy_with_trend_and_momentum(self):
        closes = [100.0 + i * 0.8 for i in range(260)]     # steady uptrend
        prices = FakePrices(closes)
        conf = Layer2Confirmation(prices, None, settings=make_settings())
        raw = self._raw("BUY")
        raw.thesis = "continuation"
        result = conf.confirm(raw)
        assert result.confirmed                     # RSI>50 + fast>slow
        assert any("momentum" in r for r in result.reasons)

    def test_confirms_reversion_buy_in_pullback_context(self):
        closes = [400.0 - i * 1.2 for i in range(240)]    # long downtrend
        closes += [closes[-1] - 9.0 * i for i in range(1, 5)]  # crash
        prices = FakePrices(closes)
        conf = Layer2Confirmation(prices, None, settings=make_settings())
        raw = self._raw("BUY")
        raw.thesis = "reversion"
        result = conf.confirm(raw)
        assert result.confirmed                     # oversold RSI + fast<slow
        assert any("reversion" in r for r in result.reasons)

    def test_continuation_buy_rejected_in_downtrend(self):
        closes = [400.0 - i * 1.0 for i in range(240)]     # downtrend
        prices = FakePrices(closes)
        conf = Layer2Confirmation(prices, None, settings=make_settings())
        raw = self._raw("BUY")
        raw.thesis = "continuation"
        result = conf.confirm(raw)
        assert not result.confirmed                 # trend+momentum against

    def test_rejects_insufficient_history(self):
        conf = Layer2Confirmation(FakePrices([100.0] * 10), None, settings=make_settings())
        result = conf.confirm(self._raw())
        assert not result.confirmed
        assert "insufficient history" in result.reasons[0]

    def test_score_below_min_not_confirmed(self):
        flat = FakePrices([100.0] * 260)
        conf = Layer2Confirmation(flat, None, settings=make_settings())
        result = conf.confirm(RawSignal(1, "Helium", "LIN.US", "SELL", "PRICE", "x", 0.1))
        assert not result.confirmed


# ---------------------------------------------------------------- layer 3
class TestLayer3Portfolio:
    def _confirmed(self, iid=38, direction="BUY"):
        raw = RawSignal(iid, "Copper", "COPPER", direction, "EVENT", "strike", 0.8)
        from newsetup.models import ConfirmedSignal
        return ConfirmedSignal(raw=raw, confirmed=True, score=0.75)

    def test_sizes_with_atr_stop_and_r_multiple(self):
        prices = SyntheticPriceProvider()
        pm = Layer3PortfolioManager(settings=make_settings())
        account = AccountState(balance=10000, equity=10000)
        sized = pm.size_positions([self._confirmed()], account, [], prices)
        assert len(sized) == 1
        s = sized[0]
        assert s.stop_loss < s.entry_price < s.take_profit
        rr = (s.take_profit - s.entry_price) / (s.entry_price - s.stop_loss)
        assert abs(rr - pm.reward_risk) < 1e-4  # entry/sl/tp rounded to 5dp
        assert s.lot_size >= pm.min_lot

    def test_max_open_positions_cap(self):
        prices = SyntheticPriceProvider()
        pm = Layer3PortfolioManager(settings=make_settings())
        account = AccountState(balance=100000, equity=100000)
        confirmed = [self._confirmed(iid=i) for i in (1, 2, 3, 4, 5, 6, 7, 8, 9)]
        sized = pm.size_positions(confirmed, account, [], prices)
        assert len(sized) <= pm.max_open

    def test_one_position_per_inefficiency(self):
        prices = SyntheticPriceProvider()
        pm = Layer3PortfolioManager(settings=make_settings())
        account = AccountState(balance=100000, equity=100000)
        sized = pm.size_positions([self._confirmed(iid=38), self._confirmed(iid=38)],
                                  account, [], prices)
        assert len(sized) == 1


# ---------------------------------------------------------------- signal bus
class TestSignalBus:
    def test_emit_writes_mql5_format(self, tmp_path):
        from newsetup.models import ConfirmedSignal
        raw = RawSignal(38, "Copper", "COPPER", "BUY", "EVENT", "strike", 0.8)
        confirmed = ConfirmedSignal(raw=raw, confirmed=True, score=0.75)
        bus = SignalBus(signals_path=str(tmp_path / "active_signals.json"))
        sized = Layer3PortfolioManager(settings=make_settings()).size_positions(
            [confirmed], AccountState(10000, 10000), [], SyntheticPriceProvider())
        assert sized, "need at least one sized signal for the bus test"
        emitted = bus.emit(sized)
        assert emitted and emitted[0]["instrument"] == "COPPER"
        data = bus.load()
        assert data["last_updated"]
        assert set(data["signals"][0]) >= {"inefficiency_id", "instrument", "direction",
                                           "lot_size", "entry_price", "stop_loss",
                                           "take_profit", "confidence", "sector",
                                           "timestamp", "trigger"}

    _ = None  # silence linter for borrowed method name
