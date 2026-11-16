"""Supplementary diagnostic: playbook-window Sharpe on DAILY equity (UGT-23).

backtest/analyzer.py annualizes Sharpe with sqrt(252) over per-equity-POINT
returns, which is correct for the D1 walk-forward/holdout runs but deflates
intraday-window Sharpe by ~sqrt(bars_per_day): an H1 window posts ~24 equity
points per day, each annualized as if it were a daily point. This script
re-runs the five TUNED playbook windows, aggregates each run's equity curve
to one point per UTC day (last value of the day), and reports the committed
per-point Sharpe next to the daily-aggregated Sharpe so the report can state
the measurement artifact explicitly. Diagnostic only - NOT an adopted gate.

Usage (from NewSetup/, C:/Python314/python.exe):

    python -m scripts.window_sharpe_daily
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.bar_cache import BarCache, CACHE_DIR                              # noqa: E402
from backtest.event_backtests import PLAYBOOK_WINDOWS, run_event_backtest    # noqa: E402
from backtest.runner import BacktestRunner                                  # noqa: E402
from backtest.tune_walk_forward import overrides_from_combo                  # noqa: E402

log = logging.getLogger("newsetup.window_sharpe_daily")
RESULTS_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "backtest", "results", "window_sharpe_daily.json")


def sharpe(returns: list[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return mean / std * math.sqrt(252.0)


def daily_returns(equity_curve: list[float],
                  timestamps: list) -> list[float]:
    """One return per UTC day (last equity point of each day)."""
    by_day: dict = {}
    for ts, eq in zip(timestamps, equity_curve):
        by_day[ts.date()] = eq
    values = [by_day[d] for d in sorted(by_day)]
    return [cur / prev - 1.0
            for prev, cur in zip(values, values[1:]) if prev > 0]


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "backtest", "results", "wf_tuning.json"),
              encoding="utf-8") as f:
        tuning = json.load(f)
    tuned_overrides = overrides_from_combo(tuning["final_candidate"])

    cache = BarCache(CACHE_DIR, connect=False)
    captured: dict = {}
    original_run = BacktestRunner.run

    def patched_run(self, price_data, raw_signals, *args, **kwargs):
        result = original_run(self, price_data, raw_signals, *args, **kwargs)
        events = []
        for symbol, bars in price_data.items():
            for bar in bars:
                events.append((bar.ts, symbol))
        events.sort(key=lambda e: (e[0], e[1]))
        captured["timestamps"] = [e[0] for e in events[:len(result.equity_curve)]]
        captured["result"] = result
        return result

    BacktestRunner.run = patched_run
    rows = []
    try:
        for window in PLAYBOOK_WINDOWS:
            report = run_event_backtest(window, cache,
                                        settings_overrides=tuned_overrides)
            result = captured.get("result")
            ts = captured.get("timestamps") or []
            agg = daily_returns(result.equity_curve, ts) if result else []
            row = {
                "window": window,
                "start": report["start"], "end": report["end"],
                "trades": report["metrics"]["total_trades"],
                "win_rate_pct": round(report["metrics"]["win_rate_pct"], 1),
                "profit_factor": round(report["metrics"]["profit_factor"], 2),
                "sharpe_per_point": round(report["metrics"]["sharpe"], 3),
                "sharpe_daily_agg": round(sharpe(agg), 3),
                "equity_points": len(result.equity_curve) if result else 0,
                "acceptance_passed_per_point": report["acceptance_passed"],
            }
            rows.append(row)
            log.info("%s: trades=%d win=%.1f%% PF=%.2f per-point Sharpe=%.3f"
                     " daily-agg Sharpe=%.3f (%d equity points)",
                     window, row["trades"], row["win_rate_pct"],
                     row["profit_factor"], row["sharpe_per_point"],
                     row["sharpe_daily_agg"], row["equity_points"])
    finally:
        BacktestRunner.run = original_run

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"tuned_candidate": tuning["final_candidate"],
                   "windows": rows}, f, indent=2, default=str)
    print(f"summary -> {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
