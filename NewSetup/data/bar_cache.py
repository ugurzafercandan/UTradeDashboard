"""D1 bar cache backed by the MT5 terminal (playbook 2.2).

Downloads real daily bars through the MetaTrader5 package into per-symbol
CSV files under ``data/caches/`` so the backtest runner and the live
pipeline share one on-disk history store. Downloads resolve the playbook
instrument name (config/instruments.yaml / inefficiencies.yaml) to the
connected broker's symbol name via config/broker_map.yaml; symbols with
no verified broker mapping are skipped with a warning.

The CSV cache is the offline->online bridge: once downloaded, everything
downstream (backtests, walk-forward, replay tests) runs without the
terminal, and the live pipeline simply refreshes the cache.
"""

from __future__ import annotations

import csv
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

from newsetup.config import ROOT, load_broker_map
from newsetup.models import PriceBar

log = logging.getLogger("newsetup.bar_cache")

CACHE_DIR = os.path.join(ROOT, "data", "caches")
CSV_FIELDS = ("ts", "open", "high", "low", "close", "volume")


def normalize_name(name: str) -> str:
    """Uppercase + collapse whitespace, for tolerant broker-name matching."""
    return " ".join(str(name).upper().split())


def cache_path(cache_dir: str, symbol: str) -> str:
    safe = symbol.replace("/", "_")
    return os.path.join(cache_dir, f"{safe}_D1.csv")


class BarCache:
    """Download/load D1 bars per playbook symbol (mt5 injectable for tests)."""

    def __init__(self, cache_dir: str = CACHE_DIR,
                 broker_map: Optional[dict] = None,
                 mt5: Any = None,
                 connect: bool = True):
        self.cache_dir = cache_dir
        self.broker_map = broker_map if broker_map is not None else load_broker_map()
        self.mt5 = mt5
        if mt5 is None and connect:
            self._connect()

    # ------------------------------------------------------------------ MT5
    @staticmethod
    def _mt5_connect_kwargs() -> dict:
        """MT5 initialize() kwargs from config/settings.yaml (mt5 section).

        Mirrors execution/mt5_bridge.py so the cache and the bridge
        always target the same configured terminal (path/portable and
        optional login credentials). Tolerates a missing section.
        """
        kwargs: dict = {}
        try:
            from newsetup.config import load_settings
            cfg = (load_settings() or {}).get("mt5") or {}
            if not isinstance(cfg, dict):
                return {}
            if cfg.get("terminal_path"):
                kwargs["path"] = cfg["terminal_path"]
            if cfg.get("portable"):
                kwargs["portable"] = True
            if cfg.get("login"):
                kwargs["login"] = int(cfg["login"])
                if cfg.get("server"):
                    kwargs["server"] = str(cfg["server"])
                env_name = cfg.get("password_env") or "PEPPERSTONE_MT5_PASSWORD"
                password = os.environ.get(env_name, "")
                if password:
                    kwargs["password"] = password
            if cfg.get("init_timeout_s"):
                kwargs["timeout"] = int(float(cfg["init_timeout_s"]) * 1000)
        except Exception:                              # noqa: BLE001
            return {}
        return kwargs

    def _connect(self) -> None:
        """Import MetaTrader5 and initialize the terminal (never raises)."""
        try:
            import MetaTrader5 as mt5  # type: ignore[import-not-found]
        except Exception as exc:                       # noqa: BLE001
            log.warning("MetaTrader5 unavailable: %s", exc)
            return
        kwargs = self._mt5_connect_kwargs()
        try:
            if mt5.initialize(**kwargs):
                self.mt5 = mt5
            else:
                log.warning("MT5 initialize(%s) failed: %s",
                            kwargs.get("path", "default terminal"),
                            mt5.last_error())
        except Exception as exc:                       # noqa: BLE001
            log.warning("MT5 initialize raised: %s", exc)

    @property
    def available(self) -> bool:
        return self.mt5 is not None

    def _require_mt5(self):
        if self.mt5 is None:
            raise RuntimeError("MT5 terminal not available for download")
        return self.mt5

    def _broker_exact_names(self) -> dict[str, str]:
        """{normalized name: exact broker name} for the connected terminal."""
        cached = getattr(self, "_broker_exact", None)
        if cached is None:
            mt5 = self._require_mt5()
            syms = mt5.symbols_get() or []
            cached = {normalize_name(s.name): str(s.name) for s in syms}
            self._broker_exact = cached
        return cached

    # -------------------------------------------------------------- resolve
    def resolve(self, symbol: str) -> Optional[str]:
        """Playbook symbol -> exact broker symbol (None when unmapped).

        Matching is whitespace/case-tolerant, but the returned name is
        the broker's exact spelling (e.g. "EATON  PLC CFD"), because
        symbol_select/copy_rates require the exact name.
        """
        if symbol in self.broker_map:
            mapped = self.broker_map[symbol]
            if not self.available:
                return mapped                    # trust the verified map
            exact = self._broker_exact_names().get(normalize_name(mapped))
            if exact is not None:
                return exact
            log.warning("mapped symbol %s -> %s not listed by broker",
                        symbol, mapped)
            return None
        if not self.available:
            return None
        exact = self._broker_exact_names().get(normalize_name(symbol))
        return exact if exact is not None else None

    # ------------------------------------------------------------- download
    def download(self, symbol: str, years: float = 4.0,
                 retries: int = 4, retry_delay: float = 3.0) -> list[PriceBar]:
        """Fetch `years` of D1 bars for `symbol` and write the cache CSV.

        Returns the downloaded bars (empty list when the broker offers no
        data for the symbol). The terminal rate-limits rapid history
        requests; failures are retried with a delay.
        """
        mt5 = self._require_mt5()
        broker_symbol = self.resolve(symbol)
        if broker_symbol is None:
            log.warning("no broker symbol for %s; skipping download", symbol)
            return []
        try:
            mt5.symbol_select(broker_symbol, True)
        except Exception as exc:                 # noqa: BLE001
            log.warning("symbol_select(%s) failed: %s", broker_symbol, exc)

        count = max(1, int(years * 260) + 10)
        bars = None
        for attempt in range(retries):
            try:
                bars = mt5.copy_rates_from_pos(
                    broker_symbol, mt5.TIMEFRAME_D1, 0, count)
            except Exception as exc:              # noqa: BLE001
                log.warning("copy_rates(%s) attempt %d raised: %s",
                            broker_symbol, attempt, exc)
                bars = None
            if bars is not None and len(bars) > 0:
                break
            log.warning("copy_rates(%s) attempt %d failed: %s",
                        broker_symbol, attempt, getattr(mt5, "last_error", lambda: None)())
            time.sleep(retry_delay)
        if bars is None or len(bars) == 0:
            log.warning("no D1 history for %s (broker symbol %s)",
                        symbol, broker_symbol)
            return []

        out: list[PriceBar] = []
        for b in bars:
            try:
                ts = datetime.fromtimestamp(float(b["time"]), tz=timezone.utc)
                out.append(PriceBar(
                    ts=ts,
                    open=float(b["open"]), high=float(b["high"]),
                    low=float(b["low"]), close=float(b["close"]),
                    volume=float(b["tick_volume"]),
                ))
            except Exception:                     # noqa: BLE001 - bad row
                continue
        out.sort(key=lambda x: x.ts)
        self.save(symbol, out)
        return out

    def download_all(self, symbols: list[str], years: float = 4.0) -> dict:
        """Download a set of symbols; returns {symbol: bar_count}."""
        results: dict[str, int] = {}
        for symbol in symbols:
            bars = self.download(symbol, years=years)
            results[symbol] = len(bars)
        return results

    # ------------------------------------------------------------- storage
    def save(self, symbol: str, bars: list[PriceBar]) -> str:
        os.makedirs(self.cache_dir, exist_ok=True)
        path = cache_path(self.cache_dir, symbol)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_FIELDS)
            for b in bars:
                writer.writerow((
                    b.ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    repr(b.open), repr(b.high), repr(b.low), repr(b.close),
                    repr(b.volume),
                ))
        return path

    def load(self, symbol: str) -> list[PriceBar]:
        path = cache_path(self.cache_dir, symbol)
        if not os.path.exists(path):
            return []
        bars: list[PriceBar] = []
        with open(path, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                bars.append(PriceBar(
                    ts=datetime.strptime(row["ts"], "%Y-%m-%dT%H:%M:%SZ")
                                       .replace(tzinfo=timezone.utc),
                    open=float(row["open"]), high=float(row["high"]),
                    low=float(row["low"]), close=float(row["close"]),
                    volume=float(row["volume"]),
                ))
        bars.sort(key=lambda x: x.ts)
        return bars

    def has(self, symbol: str) -> bool:
        return os.path.exists(cache_path(self.cache_dir, symbol))

    def cached_symbols(self) -> list[str]:
        if not os.path.isdir(self.cache_dir):
            return []
        return sorted(f[:-7] for f in os.listdir(self.cache_dir)
                      if f.endswith("_D1.csv"))
