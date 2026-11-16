"""Price data providers.

MT5PriceProvider pulls real bars from the MetaTrader 5 terminal when
available; SyntheticPriceProvider generates deterministic random-walk
series so the paper pipeline can run offline (and tests are stable).
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timedelta, timezone

from newsetup.models import PriceBar


def _mt5_settings() -> dict:
    """MT5 connection settings from config/settings.yaml (``mt5`` section).

    Tolerates a missing section so the module keeps importing (and tests
    keep passing) on machines without the config.
    """
    try:
        from newsetup.config import load_settings

        cfg = (load_settings() or {}).get("mt5") or {}
        return cfg if isinstance(cfg, dict) else {}
    except Exception:                           # noqa: BLE001
        return {}


class MT5PriceProvider:
    """Real price history via the MetaTrader5 python API (optional dep).

    Attaches to the configured NewSetup terminal by EXPLICIT path
    (config/settings.yaml ``mt5`` section) - never via bare
    ``mt5.initialize()``: a bare call attaches to whichever terminal owns
    python API port 22346, and per the server autostart policy that port is
    owned by the Alpari trades terminal, not the Pepperstone NewSetup
    terminal. After connecting, the account guard refuses any terminal
    whose login differs from the configured one (mirrors
    execution/mt5_bridge.py): a mismatch means we are attached to the wrong
    terminal and must not read prices from it.
    """

    def __init__(self, offline: bool = False):
        self.offline = offline
        self.mt5 = None
        self.connected_login: int | None = None
        if not offline:
            try:
                import MetaTrader5 as mt5       # optional heavy dep
                cfg = _mt5_settings()
                kwargs: dict = {}
                if cfg.get("terminal_path"):
                    kwargs["path"] = str(cfg["terminal_path"])
                if cfg.get("portable"):
                    kwargs["portable"] = True
                if cfg.get("init_timeout_s"):
                    kwargs["timeout"] = int(float(cfg["init_timeout_s"]) * 1000)
                if mt5.initialize(**kwargs):
                    info = mt5.account_info()
                    login = int(getattr(info, "login", 0) or 0) if info is not None else 0
                    expected = cfg.get("login")
                    if expected is not None and int(expected) != login:
                        mt5.shutdown()          # wrong terminal: refuse it
                    else:
                        self.mt5 = mt5
                        self.connected_login = login
            except Exception:                   # noqa: BLE001
                self.mt5 = None

    @property
    def available(self) -> bool:
        return self.mt5 is not None

    def _broker_symbol(self, symbol: str) -> str:
        """Playbook symbol -> broker symbol (config/broker_map.yaml)."""
        try:
            from newsetup.config import load_broker_map
            return load_broker_map().get(symbol, symbol)
        except Exception:                       # noqa: BLE001
            return symbol

    def get_series(self, symbol: str, lookback_days: int = 250) -> list[PriceBar]:
        if self.mt5 is None:
            return []
        name = self._broker_symbol(symbol)
        # symbol_select is required before copy_rates on a live terminal
        if not self.mt5.symbol_select(name, True):
            return []
        bars = self.mt5.copy_rates_from_pos(name, self.mt5.TIMEFRAME_D1, 0, lookback_days)
        if bars is None:
            return []
        return [
            PriceBar(
                ts=datetime.fromtimestamp(b["time"], tz=timezone.utc),
                open=float(b["open"]), high=float(b["high"]),
                low=float(b["low"]), close=float(b["close"]),
                volume=float(b["tick_volume"]),
            )
            for b in bars
        ]


class SyntheticPriceProvider:
    """Deterministic pseudo-random walk (seeded per symbol)."""

    BASE_PRICES = {
        "COPPER": 4.85, "XAUUSD": 2650.0, "XTIUSD": 72.0, "COCOA": 9500.0,
        "WHEAT": 580.0, "ALUMINIUM": 2600.0, "USDCNH": 7.25, "AUDUSD": 0.66,
        "USDZAR": 18.2, "USDTRY": 34.5, "USDCAD": 1.38, "EURUSD": 1.08,
        "USDJPY": 152.0, "REMX.US": 45.0, "SOXX.US": 230.0, "URA.US": 28.0,
    }

    def __init__(self, days: int = 300, volatility: float = 0.012):
        self.days = days
        self.volatility = volatility
        self._cache: dict[str, list[PriceBar]] = {}

    def get_series(self, symbol: str, lookback_days: int = 250) -> list[PriceBar]:
        series = self._series_for(symbol)
        if len(series) <= lookback_days:
            return series
        return series[-lookback_days:]

    def _series_for(self, symbol: str) -> list[PriceBar]:
        if symbol in self._cache:
            return self._cache[symbol]
        seed = sum(ord(c) * (i + 1) for i, c in enumerate(symbol))
        base = self.BASE_PRICES.get(symbol, 100.0)
        bars: list[PriceBar] = []
        price = base
        now = datetime.now(timezone.utc)
        for i in range(self.days):
            # deterministic lcg step
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            u = (seed / 2 ** 31) * 2 - 1                       # -1..1
            drift = 0.0002 * math.sin(i / 21.0)                # gentle cycle
            ret = drift + self.volatility * u
            open_ = price
            price = max(price * (1 + ret), base * 0.2)
            high = max(open_, price) * (1 + abs(u) * self.volatility * 0.5)
            low = min(open_, price) * (1 - abs(u) * self.volatility * 0.5)
            bars.append(PriceBar(
                ts=now - timedelta(days=self.days - i),
                open=round(open_, 5), high=round(high, 5),
                low=round(low, 5), close=round(price, 5),
                volume=1000.0 + (seed % 500),
            ))
        self._cache[symbol] = bars
        return bars


def default_price_provider(offline: bool | None = None):
    """MT5 prices when the terminal is reachable, synthetic otherwise."""
    if offline is None:
        offline = os.environ.get("NEWSETUP_OFFLINE", "") == "1"
    mt5p = MT5PriceProvider(offline=offline)
    if mt5p.available:
        return mt5p
    return SyntheticPriceProvider()
