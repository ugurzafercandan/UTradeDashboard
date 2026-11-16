"""Fetch intraday H1/M15 bars around the playbook event windows (UGT-17/19 item 2).

Attaches to the Pepperstone portable terminal by explicit path (the
machine's python-API socket default may be owned by another terminal;
never run two python APIs at once) and downloads, per cached symbol and
per playbook window:

  - H1 bars from window_start - 240 calendar days (daily-indicator warmup
    for layer-2's 210-bar minimum daily history) to window_end, for ALL
    five windows where broker history depth allows;
  - M15 bars for the red_sea_2023_24 window (Pepperstone M15 depth starts
    2022-08, so it is the only window with M15 coverage).

Bars are merged per symbol and written to data/caches/intraday/ as
{SYMBOL}_H1.csv / {SYMBOL}_M15.csv (same CSV format as the D1 cache), plus
a coverage report (coverage.json) stating, per symbol/window/timeframe,
how many daily bars precede the window start and whether the window is
usable for intraday backtests (needs >= 210 pre-window daily bars).

Usage (from NewSetup/, C:/Python314/python.exe):

    python -m scripts.fetch_intraday
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.event_backtests import PLAYBOOK_WINDOWS                      # noqa: E402
from data.bar_cache import BarCache, CACHE_DIR, CSV_FIELDS, normalize_name  # noqa: E402
from newsetup.config import ROOT, load_settings                            # noqa: E402

log = logging.getLogger("newsetup.fetch_intraday")

INTRADAY_DIR = os.path.join(ROOT, "data", "caches", "intraday")
COVERAGE_JSON = os.path.join(INTRADAY_DIR, "coverage.json")
WARMUP_DAYS = 240
MIN_PRE_WINDOW_DAILY = 210


def _fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def save_bars(symbol: str, timeframe: str, bars: list) -> str:
    os.makedirs(INTRADAY_DIR, exist_ok=True)
    path = os.path.join(INTRADAY_DIR, f"{symbol.replace('/', '_')}_{timeframe}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_FIELDS)
        for b in bars:
            writer.writerow((_fmt_ts(b.ts), repr(b.open), repr(b.high),
                              repr(b.low), repr(b.close), repr(b.volume)))
    return path


def load_bars(symbol: str, timeframe: str) -> list:
    from newsetup.models import PriceBar
    path = os.path.join(INTRADAY_DIR, f"{symbol.replace('/', '_')}_{timeframe}.csv")
    if not os.path.exists(path):
        return []
    bars = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bars.append(PriceBar(ts=_parse_ts(row["ts"]), open=float(row["open"]),
                                 high=float(row["high"]), low=float(row["low"]),
                                 close=float(row["close"]), volume=float(row["volume"])))
    return bars


def fetch_rates(mt5, broker_symbol: str, timeframe, start: datetime,
                end: datetime, retries: int = 4, delay: float = 3.0):
    """copy_rates_range with retries; returns list[dict] or []."""
    for attempt in range(retries):
        try:
            rates = mt5.copy_rates_range(broker_symbol, timeframe, start, end)
            if rates is not None and len(rates) > 0:
                return list(rates)
        except Exception as exc:                      # noqa: BLE001
            log.warning("copy_rates_range(%s) raised: %s", broker_symbol, exc)
        log.warning("copy_rates_range(%s) attempt %d failed: %s",
                    broker_symbol, attempt, mt5.last_error())
        time.sleep(delay)
    return []


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    argv = argv if argv is not None else sys.argv[1:]

    import MetaTrader5 as mt5                       # type: ignore[import-not-found]

    settings = load_settings()
    mt5_cfg = settings.get("mt5") or {}
    init_kwargs = {"path": mt5_cfg.get("terminal_path")}
    if mt5_cfg.get("portable"):
        init_kwargs["portable"] = True
    if mt5_cfg.get("init_timeout_s"):
        init_kwargs["timeout"] = int(float(mt5_cfg["init_timeout_s"]) * 1000)
    if not mt5.initialize(**init_kwargs):
        log.error("MT5 initialize failed: %s", mt5.last_error())
        return 1
    acc = mt5.account_info()
    log.info("attached to terminal, account %s (%s)",
             acc.login if acc else "?", acc.server if acc else "?")

    try:
        cache = BarCache(CACHE_DIR, mt5=mt5, connect=False)
        symbols = cache.cached_symbols()
        log.info("fetching intraday bars for %d cached symbols", len(symbols))

        h1_by_symbol: dict[str, dict[str, tuple]] = {}
        m15_by_symbol: dict[str, dict[str, tuple]] = {}
        coverage = {}

        timeframes = [("H1", mt5.TIMEFRAME_H1, h1_by_symbol)]
        for symbol in symbols:
            broker_symbol = cache.resolve(symbol)
            if broker_symbol is None:
                log.warning("no broker symbol for %s; skipped", symbol)
                continue
            try:
                mt5.symbol_select(broker_symbol, True)
            except Exception as exc:                # noqa: BLE001
                log.warning("symbol_select(%s) failed: %s", broker_symbol, exc)
                continue

            for window, (start_s, end_s, _desc) in PLAYBOOK_WINDOWS.items():
                start = datetime.strptime(start_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                end = datetime.strptime(end_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                lo = start - timedelta(days=WARMUP_DAYS)

                rates = fetch_rates(mt5, broker_symbol, mt5.TIMEFRAME_H1, lo, end)
                for r in rates:
                    ts = datetime.fromtimestamp(float(r["time"]), tz=timezone.utc)
                    row = (float(r["open"]), float(r["high"]),
                           float(r["low"]), float(r["close"]), float(r["tick_volume"]))
                    h1_by_symbol.setdefault(symbol, {})[ts] = row

                # M15 only where broker depth plausibly covers it
                if window == "red_sea_2023_24":
                    m15 = fetch_rates(mt5, broker_symbol, mt5.TIMEFRAME_M15, lo, end)
                    for r in m15:
                        ts = datetime.fromtimestamp(float(r["time"]), tz=timezone.utc)
                        row = (float(r["open"]), float(r["high"]),
                               float(r["low"]), float(r["close"]), float(r["tick_volume"]))
                        m15_by_symbol.setdefault(symbol, {})[ts] = row

                pre_days = len({ts.date() for ts in h1_by_symbol.get(symbol, {})
                                if ts.date() < start.date()})
                in_bars = sum(1 for ts in h1_by_symbol.get(symbol, {})
                              if start <= ts <= end)
                coverage[f"{symbol}|{window}|H1"] = {
                    "pre_window_daily_bars": pre_days,
                    "in_window_bars": in_bars,
                    "usable": pre_days >= MIN_PRE_WINDOW_DAILY and in_bars > 0,
                }
            log.info("fetched %s (H1 bars: %d)", symbol,
                     len(h1_by_symbol.get(symbol, {})))

        # save merged, sorted bars
        from newsetup.models import PriceBar
        saved = {}
        for symbol, rows in h1_by_symbol.items():
            bars = [PriceBar(ts=t, open=row[0], high=row[1], low=row[2],
                             close=row[3], volume=row[4])
                    for t, row in sorted(rows.items())]
            save_bars(symbol, "H1", bars)
            saved[f"{symbol}_H1"] = len(bars)
        for symbol, rows in m15_by_symbol.items():
            bars = [PriceBar(ts=t, open=row[0], high=row[1], low=row[2],
                             close=row[3], volume=row[4])
                    for t, row in sorted(rows.items())]
            save_bars(symbol, "M15", bars)
            saved[f"{symbol}_M15"] = len(bars)

        os.makedirs(INTRADAY_DIR, exist_ok=True)
        with open(COVERAGE_JSON, "w", encoding="utf-8") as f:
            json.dump({"warmup_days": WARMUP_DAYS,
                       "min_pre_window_daily": MIN_PRE_WINDOW_DAILY,
                       "saved": saved, "windows": coverage}, f, indent=2)
        usable = sum(1 for v in coverage.values() if v["usable"])
        log.info("saved %d intraday files; %d/%d symbol-window H1 combos usable",
                 len(saved), usable, len(coverage))
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
