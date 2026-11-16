"""Supplementary intraday fetch for the covid_2020 window (UGT-17/19 item 2).

Pepperstone H1 history reaches back to mid-2018, deeper than the 240-day
warmup window the main fetch used, so the covid window (2020-02-15) was
left without the >= 210 pre-window daily bars layer-2 needs. This script
fetches H1 bars from 2018-06-01 to 2020-06-30 for every mapped symbol,
merges them into data/caches/intraday/{SYMBOL}_H1.csv (dedupe by ts) and
recomputes the covid coverage entries in coverage.json.

Usage: python -m scripts.fetch_intraday_covid_deep
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.event_backtests import PLAYBOOK_WINDOWS                          # noqa: E402
from scripts.fetch_intraday import (COVERAGE_JSON, INTRADAY_DIR, WARMUP_DAYS,
                                    MIN_PRE_WINDOW_DAILY, load_bars, save_bars)  # noqa: E402
from data.bar_cache import BarCache, CACHE_DIR, CSV_FIELDS                    # noqa: E402
from newsetup.models import PriceBar                                          # noqa: E402

log = logging.getLogger("newsetup.fetch_covid_deep")

START = datetime(2018, 6, 1, tzinfo=timezone.utc)
END = datetime(2020, 6, 30, tzinfo=timezone.utc)


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    import MetaTrader5 as mt5
    if not mt5.initialize(path="C:/Program Files/MT5-Pepperstone/terminal64.exe",
                          portable=True, timeout=90000):
        log.error("MT5 init failed: %s", mt5.last_error())
        return 1
    try:
        cache = BarCache(CACHE_DIR, mt5=mt5, connect=False)
        window = PLAYBOOK_WINDOWS["covid_2020"]
        wstart = datetime.strptime(window[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        wend = datetime.strptime(window[1], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        with open(COVERAGE_JSON, encoding="utf-8") as f:
            cov = json.load(f)
        for symbol in cache.cached_symbols():
            broker = cache.resolve(symbol)
            if broker is None:
                continue
            mt5.symbol_select(broker, True)
            rates = mt5.copy_rates_range(broker, mt5.TIMEFRAME_H1, START, END)
            if rates is None or len(rates) == 0:
                log.warning("%s: no deep H1 history", symbol)
                continue
            existing = {(b.ts.year, b.ts.month, b.ts.day, b.ts.hour): b
                        for b in load_bars(symbol, "H1")}
            merged = dict(existing)
            for r in rates:
                ts = datetime.fromtimestamp(float(r["time"]), tz=timezone.utc)
                merged[(ts.year, ts.month, ts.day, ts.hour)] = PriceBar(
                    ts=ts, open=float(r["open"]), high=float(r["high"]),
                    low=float(r["low"]), close=float(r["close"]),
                    volume=float(r["tick_volume"]))
            bars = sorted(merged.values(), key=lambda b: b.ts)
            save_bars(symbol, "H1", bars)
            pre_days = len({b.ts.date() for b in bars if b.ts.date() < wstart.date()})
            in_bars = sum(1 for b in bars if wstart <= b.ts <= wend)
            key = f"{symbol}|covid_2020|H1"
            cov["windows"][key] = {
                "pre_window_daily_bars": pre_days,
                "in_window_bars": in_bars,
                "usable": pre_days >= MIN_PRE_WINDOW_DAILY and in_bars > 0,
            }
            cov["saved"][f"{symbol}_H1"] = len(bars)
            log.info("%s: %d H1 bars (%d pre-window daily), usable=%s",
                     symbol, len(bars), pre_days, cov["windows"][key]["usable"])
        with open(COVERAGE_JSON, "w", encoding="utf-8") as f:
            json.dump(cov, f, indent=2)
        finally_usable = sum(1 for k, v in cov["windows"].items()
                             if "covid" in k and v["usable"])
        log.info("covid window intraday usable symbols: %d", finally_usable)
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
