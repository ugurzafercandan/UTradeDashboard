"""Tests for the live-data stack (playbook 2.2/2.3): broker map, bar
cache, MT5 bridge helpers, GDELT live parsing, and event-window
backtests. Everything here runs offline with fakes injected.
"""

from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backtest.event_backtests import (PLAYBOOK_WINDOWS,
                                      replay_price_signals,
                                      run_event_backtest)
from data.bar_cache import BarCache, cache_path, normalize_name
from data.gdelt_monitor import GDELTMonitor
from execution.mt5_bridge import MT5Bridge, MT5NotAvailable
from newsetup.config import load_broker_map
from newsetup.models import PriceBar

BASE_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


class FakeMT5:
    """Minimal MetaTrader5 stub: one symbol, deterministic bars."""

    TIMEFRAME_D1 = 24

    class _Sym:
        def __init__(self, name):
            self.name = name
            self.visible = True

    def __init__(self, names=("WTI", "XAUUSD")):
        self._names = names
        self.calls = []
        # 5 years of daily bars with a mild sawtooth
        self._bars = [
            {"time": (BASE_TS + timedelta(days=i)).timestamp(),
             "open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0 + (i % 2), "tick_volume": 1000, "spread": 1,
             "real_volume": 0}
            for i in range(1300)
        ]

    def symbols_get(self, *a, **k):
        return [self._Sym(n) for n in self._names]

    def symbol_select(self, symbol, enable):
        self.calls.append(("select", symbol, enable))
        return True

    def copy_rates_from_pos(self, symbol, tf, start, count):
        self.calls.append(("copy", symbol, start, count))
        return self._bars[:count]

    def last_error(self):
        return (0, "ok")


# ------------------------------------------------------------ broker map
class TestBrokerMap:
    def test_loads_and_contains_verified_symbols(self):
        bm = load_broker_map()
        assert isinstance(bm, dict) and len(bm) >= 40
        assert bm["XTIUSD"] == "SpotCrude"
        assert bm["XAUUSD"] == "XAUUSD"
        assert bm["MSFT.US"] == "MSFT.US"
        assert bm["COPPER"] == "Copper"
        assert bm["ALUMINIUM"] == "Aluminium"
        # ETF proxies are live on the Pepperstone terminal
        for etf in ("QQQ.US", "SOXX.US", "COPX.US"):
            assert etf in bm
        # symbols verified as unavailable must not be mapped
        for missing in ("VALE.US", "FRO.US", "ZIM.US", "REMX.US", "TAN.US", "BHP.US"):
            assert missing not in bm


# -------------------------------------------------------------- bar cache
class TestBarCache:
    def test_download_resolves_broker_symbol_and_saves_csv(self, tmp_path):
        mt5 = FakeMT5(names=("WTI",))
        cache = BarCache(cache_dir=str(tmp_path), mt5=mt5, connect=False,
                         broker_map={"XTIUSD": "WTI"})
        bars = cache.download("XTIUSD", years=3)
        assert len(bars) > 700
        assert all(("select", "WTI", True) == c[:3] for c in mt5.calls[:1])
        assert cache.has("XTIUSD")
        assert any(c[0] == "copy" and c[1] == "WTI" for c in mt5.calls)

    def test_load_roundtrips_saved_bars(self, tmp_path):
        mt5 = FakeMT5(names=("WTI",))
        cache = BarCache(cache_dir=str(tmp_path), mt5=mt5, connect=False,
                         broker_map={"XTIUSD": "WTI"})
        cache.download("XTIUSD", years=1)
        loaded = cache.load("XTIUSD")
        assert loaded and all(isinstance(b, PriceBar) for b in loaded)
        assert loaded == sorted(loaded, key=lambda b: b.ts)
        assert loaded[0].ts.tzinfo is not None

    def test_unmapped_symbol_skipped(self, tmp_path):
        mt5 = FakeMT5(names=("WTI",))
        cache = BarCache(cache_dir=str(tmp_path), mt5=mt5, connect=False,
                         broker_map={"XTIUSD": "WTI"})
        assert cache.download("ALUMINIUM") == []
        assert not cache.has("ALUMINIUM")

    def test_resolve_without_mt5_trusts_map(self, tmp_path):
        cache = BarCache(cache_dir=str(tmp_path), mt5=None, connect=False,
                         broker_map={"XTIUSD": "WTI", "XAUUSD": "XAUUSD"})
        assert cache.resolve("XTIUSD") == "WTI"
        assert cache.resolve("XAUUSD") == "XAUUSD"
        assert cache.resolve("ALUMINIUM") is None

    def test_resolve_normalizes_broker_names(self, tmp_path):
        mt5 = FakeMT5(names=("Eaton  PLC CFD",))
        cache = BarCache(cache_dir=str(tmp_path), mt5=mt5, connect=False,
                         broker_map={"ETN.US": "EATON PLC CFD"})
        # tolerant match, exact broker spelling returned
        assert cache.resolve("ETN.US") == "Eaton  PLC CFD"
        assert normalize_name(" eaton  plc cfd ") == "EATON PLC CFD"

    def test_cached_symbols_listing(self, tmp_path):
        mt5 = FakeMT5(names=("WTI", "XAUUSD"))
        cache = BarCache(cache_dir=str(tmp_path), mt5=mt5, connect=False,
                         broker_map={"XTIUSD": "WTI", "XAUUSD": "XAUUSD"})
        cache.download("XTIUSD", years=0.5)
        cache.download("XAUUSD", years=0.5)
        assert cache.cached_symbols() == ["XAUUSD", "XTIUSD"]
        assert os.path.basename(cache_path(str(tmp_path), "XAUUSD")) == "XAUUSD_D1.csv"

    def test_save_load_roundtrip_exact(self, tmp_path):
        cache = BarCache(cache_dir=str(tmp_path), mt5=None, connect=False,
                         broker_map={})
        bars = [PriceBar(ts=BASE_TS, open=1.0, high=2.0, low=0.5,
                         close=1.5, volume=10.0)]
        cache.save("TEST", bars)
        assert cache.load("TEST") == bars


# ------------------------------------------------------------ MT5 bridge
class FakeBridgeMT5:
    TIMEFRAME_H1 = 4
    TIMEFRAME_D1 = 24

    class _Sym:
        def __init__(self, name):
            self.name = name

    def __init__(self):
        self.selected = []
        self.login = 61636260

    def account_info(self):
        class _Acct:
            login = 0
            balance = 0.0
            equity = 0.0
            margin = 0.0
            positions = 0
            currency = "USD"
        a = _Acct()
        a.login = self.login
        a.balance = 50000.0
        a.equity = 50000.0
        a.margin = 0.0
        a.positions = 0
        a.currency = "USD"
        return a

    def symbols_get(self, *a, **k):
        return [self._Sym(n) for n in ("XAUUSD", "MICROSOFT CFD")]

    def symbol_select(self, symbol, enable):
        self.selected.append(symbol)
        return True

    def copy_rates_from_pos(self, symbol, tf, start, count):
        return [{"time": BASE_TS.timestamp(), "open": 1.0, "high": 2.0,
                 "low": 0.5, "close": 1.5, "tick_volume": 3.0,
                 "spread": 0, "real_volume": 0}] * count


class TestMT5BridgeHelpers:
    def _bridge(self):
        b = MT5Bridge(auto_connect=False)
        b.mt5 = FakeBridgeMT5()
        b.available = True
        return b

    def test_symbol_available_normalized(self):
        b = self._bridge()
        assert b.symbol_available("XAUUSD")
        assert b.symbol_available("microsoft cfd")
        assert not b.symbol_available("NOSUCH")

    def test_get_bars_returns_rows(self):
        b = self._bridge()
        bars = b.get_bars("XAUUSD", timeframe="D1", count=10)
        assert len(bars) == 10
        assert bars[0]["close"] == 1.5

    def test_unavailable_bridge_raises(self):
        b = MT5Bridge(auto_connect=False)
        try:
            b.symbol_available("XAUUSD")
            raised = False
        except MT5NotAvailable:
            raised = True
        assert raised


class TestMT5AccountGuard:
    """The account guard refuses trading on the wrong MT5 account."""

    def _bridge(self, expected, actual):
        b = MT5Bridge(auto_connect=False)
        b.mt5 = FakeBridgeMT5()
        b.mt5.login = actual
        b.available = True
        b._mt5_settings = lambda: {"login": expected}
        return b

    def test_order_blocked_on_wrong_account(self):
        from execution.mt5_bridge import MT5WrongAccount
        b = self._bridge(expected=61636260, actual=52920535)
        try:
            b.market_order("XAUUSD", "BUY", 0.01, 1.0, 2.0)
            raised = False
        except MT5WrongAccount:
            raised = True
        assert raised

    def test_order_allowed_on_matching_account(self):
        b = self._bridge(expected=61636260, actual=61636260)
        # order_send is missing from the fake, so we get the "no result"
        # dict — but the guard must NOT raise.
        result = b.market_order("XAUUSD", "BUY", 0.01, 1.0, 2.0)
        assert result["retcode"] == -1

    def test_no_expected_login_configured_means_no_guard(self):
        b = self._bridge(expected=None, actual=12345678)
        result = b.market_order("XAUUSD", "BUY", 0.01, 1.0, 2.0)
        assert result["retcode"] == -1

    def test_close_position_also_guarded(self):
        from execution.mt5_bridge import MT5WrongAccount
        b = self._bridge(expected=61636260, actual=52920535)
        try:
            b.close_position(12345)
            raised = False
        except MT5WrongAccount:
            raised = True
        assert raised


# ---------------------------------------------------------------- GDELT
def _export_zip_bytes() -> bytes:
    """One valid GDELT 2.0 export-archive slot containing one keep-event
    row (tab-separated, 61 columns) zipped as the monitor expects."""
    f = [""] * 61
    f[6] = "RUSSIA"                       # Actor1Name
    f[26] = "194"                         # EventCode
    f[28] = "19"                          # EventRootCode (military fight)
    f[30] = "-8.0"                        # GoldsteinScale
    f[33] = "15"                          # NumArticles
    f[34] = "-5.0"                        # AvgTone
    f[52] = "Suez, Egypt"                 # ActionGeo_FullName
    f[53] = "EG"                          # ActionGeo_CountryCode
    row = "\t".join(f) + "\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("20261116120000.export.CSV", row)
    return buf.getvalue()


class TestGDELTExportArchive:
    """UGT-15 Phase 4: DOC-API failures must fall back to the fresh GDELT
    2.0 export archive (same feed as the UGT-14 walk-forward), not stale
    fixtures."""

    def test_parse_export_line_maps_row_to_event(self):
        from data.gdelt_monitor import parse_export_line
        f = [""] * 61
        f[6], f[21] = "RUSSIA", "UKRAINE"
        f[26], f[28] = "194", "19"
        f[30], f[33], f[34] = "-8.0", "15", "-5.0"
        f[52], f[53] = "Suez, Egypt", "EG"
        ev = parse_export_line("\t".join(f), ts=BASE_TS)
        assert ev is not None
        assert ev.source == "gdelt_export"
        assert "conventional military fight" in ev.headline
        assert "Suez, Egypt" in ev.headline
        assert "RUSSIA" in ev.headline and "UKRAINE" in ev.headline
        assert ev.goldstein_score == -8.0
        assert 0 < ev.score <= 1.0

    def test_parse_export_line_drops_noise(self):
        from data.gdelt_monitor import parse_export_line
        f = [""] * 61
        f[26], f[28] = "010", "10"        # 'make statement', cooperation
        f[30], f[33], f[34] = "1.0", "50", "0.0"
        f[52], f[53] = "Italy", "IT"
        assert parse_export_line("\t".join(f), ts=BASE_TS) is None
        assert parse_export_line("short\trow", ts=BASE_TS) is None

    def test_doc_failure_falls_back_to_export_archive(self, monkeypatch):
        zipped = _export_zip_bytes()

        class FakeResp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return None

        def fake_urlopen(url, timeout=None):
            if "data.gdeltproject.org/gdeltv2" in url:
                return FakeResp(zipped)
            raise OSError("HTTP Error 429: Too Many Requests")

        monkeypatch.setattr("data.gdelt_monitor.urlopen", fake_urlopen)
        monitor = GDELTMonitor(offline=False)
        monitor.EXPORT_SLOTS = 2          # keep the test light
        events = monitor.get_events()
        assert events
        assert all(e.source == "gdelt_export" for e in events)
        assert all("Suez, Egypt" in e.headline for e in events)
        # export results are cached like DOC results
        assert monitor.get_events() is not None


class TestGDELTLive:
    def test_live_query_parses_doc20_payload(self, monkeypatch):
        payload = {"articles": [
            {"title": "Copper mine strike halts Chilean output",
             "goldstein": -5.5, "url": "https://x/1", "seendate": "20261115T120000Z"},
            {"title": "Port congestion eases after canal reopens",
             "goldstein": 3.0, "url": "https://x/2", "seendate": "20261115T130000Z"},
        ]}
        captured = {}

        class FakeResp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return None

        def fake_urlopen(url, timeout=None):
            captured["url"] = url
            return FakeResp(json.dumps(payload).encode())

        monkeypatch.setattr("data.gdelt_monitor.urlopen", fake_urlopen)
        events = GDELTMonitor(offline=False).get_events(keywords=["copper"])
        assert "api.gdeltproject.org" in captured["url"]
        assert len(events) == 2
        assert events[0].source == "gdelt"
        assert events[0].headline.startswith("Copper mine strike")
        assert events[0].goldstein_score == -5.5
        assert 0 <= events[0].score <= 1

    def test_live_results_cached_within_ttl(self, monkeypatch):
        calls = []

        class FakeResp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return None

        payload = json.dumps({"articles": [
            {"title": "copper strike", "goldstein": -4.0}]})

        def fake_urlopen(url, timeout=None):
            calls.append(url)
            return FakeResp(payload.encode())

        monkeypatch.setattr("data.gdelt_monitor.urlopen", fake_urlopen)
        monitor = GDELTMonitor(offline=False)
        first = monitor.get_events()
        second = monitor.get_events()
        assert len(calls) == 1          # second call served from cache
        assert [e.headline for e in second] == [e.headline for e in first]

    def test_live_failure_falls_back_to_fixtures(self, monkeypatch):
        def boom(url, timeout=None):
            raise OSError("no network")

        monkeypatch.setattr("data.gdelt_monitor.urlopen", boom)
        events = GDELTMonitor(offline=False).get_events()
        assert events
        assert all(e.source == "fixture" for e in events)


# ------------------------------------------------------ event backtests
def _trending_bars(days: int, base: float = 100.0) -> list[PriceBar]:
    """Sawtooth with 3% daily jumps every 10th day to trip the 2% trigger."""
    bars = []
    price = base
    for i in range(days):
        if i % 10 == 5:
            ret = 0.03
        elif i % 10 == 6:
            ret = -0.03
        else:
            ret = 0.0
        open_ = price
        price = price * (1 + ret)
        bars.append(PriceBar(ts=BASE_TS + timedelta(days=i),
                             open=open_, high=max(open_, price) * 1.001,
                             low=min(open_, price) * 0.999, close=price,
                             volume=100.0))
    return bars


class TestReplayPriceSignals:
    def test_spikes_emit_signals_with_cooldown(self):
        bars = _trending_bars(40)
        sigs = replay_price_signals(bars, 7, "Test", "XAUUSD", cooldown=5)
        assert sigs, "expected at least one signal from 3% daily jumps"
        assert all(s.trigger_type == "PRICE" for s in sigs)
        assert all(s.instrument == "XAUUSD" for s in sigs)
        # 3% drop day -> BUY (supply shock), 3% rise day -> SELL
        dirs = [s.direction for s in sigs]
        assert "BUY" in dirs or "SELL" in dirs
        # cooldown: no two signals within 5 bars
        idx = [i for i, b in enumerate(bars)
               if any(s.ts == b.ts for s in sigs)]
        assert all(j - i >= 5 for i, j in zip(idx, idx[1:]))

    def test_window_bounds_respected(self):
        bars = _trending_bars(40)
        start = bars[10].ts
        end = bars[20].ts
        sigs = replay_price_signals(bars, 7, "Test", "XAUUSD",
                                   start=start, end=end)
        assert all(start <= s.ts <= end for s in sigs)


class TestEventBacktestRunner:
    def test_end_to_end_on_cached_fixture(self, tmp_path):
        # Build a fake cache with one symbol: 300 warmup bars + window bars.
        mt5 = FakeMT5()
        cache = BarCache(cache_dir=str(tmp_path), mt5=mt5, connect=False,
                         broker_map={"XAUUSD": "XAUUSD"})
        bars = _trending_bars(300, base=100.0)
        # timestamp so the covid_2020 window (2020-02-15..06-30) is covered
        for i, b in enumerate(bars):
            b.ts = (datetime(2019, 6, 1, tzinfo=timezone.utc)
                    + timedelta(days=i))
        cache.save("XAUUSD", bars)

        report = run_event_backtest(
            "covid_2020", cache,
            settings_overrides={"layer2": {"min_history_bars": 20,
                                           "sma_fast": 5, "sma_slow": 20,
                                           "min_score": 0.4}},
            warmup_bars=200, starting_balance=10000.0)
        assert report["window"] == "covid_2020"
        assert report["symbols_used"] == ["XAUUSD"]
        assert report["metrics"]["total_trades"] >= 0
        assert isinstance(report["acceptance_passed"], bool)
        assert "final_equity" in report

    def test_unknown_window_raises(self, tmp_path):
        cache = BarCache(cache_dir=str(tmp_path), mt5=None, connect=False,
                         broker_map={})
        try:
            run_event_backtest("nope", cache)
            raised = False
        except KeyError:
            raised = True
        assert raised

    def test_windows_defined_for_playbook_periods(self):
        assert "covid_2020" in PLAYBOOK_WINDOWS
        assert "russia_sanctions_2022" in PLAYBOOK_WINDOWS
        assert "red_sea_2023_24" in PLAYBOOK_WINDOWS
        for name, (start, end, _d) in PLAYBOOK_WINDOWS.items():
            datetime.strptime(start, "%Y-%m-%d")
            datetime.strptime(end, "%Y-%m-%d")
