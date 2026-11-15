"""Playbook 5.2 event-window backtests on real cached data.

Runs the standard BacktestRunner over the historical event windows named
in the playbook's validation plan (COVID-19 2020, Suez/China power 2021,
Russia sanctions 2022, Red Sea 2023-24) using D1 bars downloaded from
the MT5 terminal into data/caches/ (see data/bar_cache.py).

Layer-1 EVENT triggers need live GDELT coverage which only extends a few
months back, so historical windows are replayed with the scanner's PRICE
trigger logic: at each bar the 1-day and 30-day moves are compared to
the settings.layer1 spike thresholds and a raw signal is emitted with a
per-symbol cooldown, mirroring Layer1Scanner._eval_price exactly.

Reports are written to backtest/results/<window>.json plus a combined
markdown summary (realdata_event_backtests.md).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from newsetup.config import ROOT, load_inefficiencies, load_settings
from newsetup.models import PriceBar, RawSignal

from data.bar_cache import BarCache
from .runner import BacktestRunner

log = logging.getLogger("newsetup.event_backtests")

RESULTS_DIR = ROOT + "/backtest/results"

# Playbook 5.2 validation windows: (start, end, description)
PLAYBOOK_WINDOWS: dict[str, tuple[str, str, str]] = {
    "covid_2020": ("2020-02-15", "2020-06-30",
                   "COVID-19 global supply shock"),
    "suez_2021": ("2021-03-10", "2021-04-20",
                  "Suez Canal Ever Given blockage"),
    "china_power_2021": ("2021-09-01", "2021-11-15",
                         "China energy crisis / power rationing"),
    "russia_sanctions_2022": ("2022-02-15", "2022-04-30",
                              "Russia sanctions / commodity squeeze"),
    "red_sea_2023_24": ("2023-11-01", "2024-03-31",
                        "Red Sea shipping attacks"),
}


def _pct(closes: list[float], lookback: int) -> Optional[float]:
    """Same helper as Layer1Scanner._pct (daily == 1-day move)."""
    if len(closes) < lookback + 1 or closes[-lookback - 1] == 0:
        return None
    return (closes[-1] / closes[-lookback - 1] - 1.0) * 100.0


def replay_price_signals(bars: list[PriceBar],
                         inefficiency_id: int,
                         inefficiency_name: str,
                         symbol: str,
                         settings: Optional[dict] = None,
                         cooldown: int = 5,
                         start: Optional[datetime] = None,
                         end: Optional[datetime] = None) -> list[RawSignal]:
    """Replay Layer1Scanner._eval_price over one symbol's history.

    Emits at most one signal per `cooldown` bars once the 1d/30d move
    crosses the layer1 spike thresholds (settings.layer1), with the same
    direction logic as the live scanner.
    """
    settings = settings or load_settings()
    cfg = settings["layer1"]
    spike_24h = float(cfg["price_spike_pct_24h"])
    spike_30d = float(cfg["price_spike_pct_30d"])
    signals: list[RawSignal] = []
    last_idx = -10 ** 9
    closes = [b.close for b in bars]
    for i in range(1, len(bars)):
        bar = bars[i]
        if start and bar.ts < start:
            continue
        if end and bar.ts > end:
            break
        chg_24h = _pct(closes[:i + 1], 1)
        chg_30d = _pct(closes[:i + 1], min(30, i))
        direction = None
        chg = None
        if chg_24h is not None and chg_24h <= -spike_24h:
            direction, chg = "BUY", chg_24h        # supply-shock spike up -> BUY proxy
        elif chg_24h is not None and chg_24h >= spike_24h:
            direction, chg = "SELL", chg_24h
        elif chg_30d is not None and abs(chg_30d) >= spike_30d:
            direction = "SELL" if chg_30d > 0 else "BUY"
            chg = chg_30d
        if direction is None or i - last_idx < cooldown:
            continue
        signals.append(RawSignal(
            inefficiency_id=inefficiency_id,
            inefficiency_name=inefficiency_name,
            instrument=symbol,
            direction=direction,
            trigger_type="PRICE",
            trigger_description=f"{symbol} move {chg:+.2f}% "
                                f"(threshold {spike_24h}%)",
            confidence=0.6,
            ts=bar.ts,
        ))
        last_idx = i
    return signals


def _symbol_owner(inefficiencies, symbol: str):
    """First inefficiency whose tradeable instruments include `symbol`."""
    for ineff in inefficiencies:
        if symbol in ineff.tradeable_symbols():
            return ineff
    return None


def run_event_backtest(window: str,
                       cache: BarCache,
                       symbols: Optional[list[str]] = None,
                       starting_balance: float = 10000.0,
                       warmup_bars: int = 260,
                       settings_overrides: Optional[dict] = None) -> dict:
    """Backtest one playbook window on real cached bars; returns a report."""
    if window not in PLAYBOOK_WINDOWS:
        raise KeyError(f"unknown window {window!r}; known: {list(PLAYBOOK_WINDOWS)}")
    start_s, end_s, description = PLAYBOOK_WINDOWS[window]
    start = datetime.strptime(start_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    inefficiencies = load_inefficiencies()
    symbols = symbols if symbols is not None else cache.cached_symbols()
    price_data: dict[str, list[PriceBar]] = {}
    raw_signals: list[RawSignal] = []
    skipped: dict[str, str] = {}
    pseudo_id = 1000  # synthetic inefficiency ids for unmapped symbols

    for symbol in symbols:
        bars = cache.load(symbol)
        if not bars:
            skipped[symbol] = "no cached bars"
            continue
        in_window = [b for b in bars if start <= b.ts <= end]
        pre_window = [b for b in bars if b.ts < start]
        if len(pre_window) < warmup_bars:
            skipped[symbol] = f"insufficient warmup ({len(pre_window)} bars)"
            continue
        if not in_window:
            skipped[symbol] = "no bars inside window"
            continue
        owner = _symbol_owner(inefficiencies, symbol)
        if owner is not None:
            ineff_id, ineff_name = owner.id, owner.name
        else:                       # unique pseudo-id keeps layer-3 per-
            pseudo_id += 1          # inefficiency caps from colliding
            ineff_id, ineff_name = pseudo_id, symbol
        price_data[symbol] = pre_window[-warmup_bars:] + in_window
        raw_signals.extend(replay_price_signals(
            price_data[symbol], ineff_id, ineff_name, symbol,
            start=start, end=end))

    runner = BacktestRunner(settings=settings_overrides)
    result = runner.run(price_data, raw_signals,
                        starting_balance=starting_balance)
    report = {
        "window": window,
        "description": description,
        "start": start_s,
        "end": end_s,
        "symbols_used": sorted(price_data),
        "symbols_skipped": skipped,
        "raw_signals": len(raw_signals),
        "metrics": result.metrics,
        "acceptance_passed": result.acceptance_passed,
        "acceptance_failures": result.acceptance_failures,
        "final_equity": result.final_equity,
        "starting_balance": starting_balance,
    }
    return report


def run_all_windows(cache: BarCache,
                    windows: Optional[list[str]] = None,
                    results_dir: str = RESULTS_DIR,
                    **kwargs) -> list[dict]:
    """Run the selected (default: all) playbook windows; save JSON+MD."""
    import os
    windows = windows if windows is not None else list(PLAYBOOK_WINDOWS)
    reports: list[dict] = []
    for window in windows:
        log.info("backtesting window %s", window)
        report = run_event_backtest(window, cache, **kwargs)
        reports.append(report)
        os.makedirs(results_dir, exist_ok=True)
        with open(os.path.join(results_dir, f"realdata_{window}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
    _write_markdown_summary(reports, results_dir)
    return reports


def _write_markdown_summary(reports: list[dict], results_dir: str) -> str:
    import os
    lines = ["# Real-data event-window backtests (playbook 5.2)", "",
             "Data: MT5 terminal D1 bars (data/caches/). Signals: layer-1",
             "PRICE trigger replay (GDELT DOC 2.0 only covers recent months",
             "so EVENT triggers cannot fire on 2020-2024 history).", ""]
    for r in reports:
        m = r["metrics"]
        lines += [
            f"## {r['window']} — {r['description']}",
            "",
            f"Window: {r['start']} .. {r['end']}"
            f" | symbols: {len(r['symbols_used'])}"
            f" (skipped {len(r['symbols_skipped'])})"
            f" | raw signals: {r['raw_signals']}",
            "",
            f"- Trades: {m.get('total_trades', 0)}",
            f"- Win rate: {m.get('win_rate_pct', 0):.1f}%",
            f"- Profit factor: {m.get('profit_factor', 0):.2f}",
            f"- Sharpe: {m.get('sharpe', 0):.2f}"
            f" | Sortino: {m.get('sortino', 0):.2f}",
            f"- Max drawdown: {m.get('max_drawdown_pct', 0):.2f}%",
            f"- Total return: {m.get('total_return_pct', 0):.2f}%",
            f"- Final equity: {r['final_equity']:.2f}"
            f" (start {r['starting_balance']:.0f})",
            f"- Acceptance: {'PASS' if r['acceptance_passed'] else 'FAIL'}"
            + (f" — {', '.join(r['acceptance_failures'])}"
               if r["acceptance_failures"] else ""),
            "",
        ]
    path = os.path.join(results_dir, "realdata_event_backtests.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
