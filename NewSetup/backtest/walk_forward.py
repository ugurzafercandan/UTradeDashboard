"""Walk-forward optimization scaffold (playbook sections 5.4-5.5).

Slides train/test windows across the merged timeline, tunes layer-2/3
parameters from a grid on each in-sample (train) segment, then scores
the best pick out-of-sample. Reports the walk-forward efficiency ratio
(WFER = mean out-of-sample sharpe / mean in-sample sharpe) against the
configured backtest.walk_forward.wfer_min gate.
"""

from __future__ import annotations

import itertools
from typing import Any, Optional

from .runner import BacktestRunner


def _merged_timeline(price_data: dict) -> list[tuple[Any, str, Any]]:
    """All bars of all symbols as one time-ordered (ts, symbol, bar) stream."""
    events: list[tuple[Any, str, Any]] = []
    for symbol, bars in price_data.items():
        for bar in sorted(bars, key=lambda b: b.ts):
            events.append((bar.ts, symbol, bar))
    events.sort(key=lambda e: (e[0], e[1]))
    return events


def _slice_window(price_data: dict, events: list, raw_signals: list) -> tuple:
    """Restrict bars and signals to one window's timestamp range."""
    if not events:
        return {}, []
    lo, hi = events[0][0], events[-1][0]
    data = {}
    for symbol, bars in price_data.items():
        selected = [b for b in sorted(bars, key=lambda b: b.ts) if lo <= b.ts <= hi]
        if selected:
            data[symbol] = selected
    signals = [s for s in raw_signals if lo <= s.ts <= hi]
    return data, signals


class WalkForwardOptimizer:
    """Scaffold walk-forward parameter tuner (playbook 5.4-5.5).

    The runner should be constructed with broker=None so every segment
    replay starts from a fresh internal simulator.
    """

    def __init__(self, runner: BacktestRunner, param_grid: dict):
        self.runner = runner
        self.param_grid = dict(param_grid)

    def run(self,
            price_data: dict,
            raw_signals: list,
            train_bars: int = 500,
            test_bars: int = 125) -> dict:
        """Slide train/test windows, tune per window, score out-of-sample."""
        walk_forward = self.runner.settings.get("backtest", {}).get(
            "walk_forward", {}) or {}
        train_bars = train_bars or walk_forward.get("train_bars", 500)
        test_bars = test_bars or walk_forward.get("test_bars", 125)
        wfer_min = walk_forward.get("wfer_min", 0.5)

        events = _merged_timeline(price_data)
        names = list(self.param_grid)
        combos = [dict(zip(names, values))
                  for values in itertools.product(*self.param_grid.values())]
        if not combos:
            combos = [{}]

        windows: list[dict] = []
        start = 0
        while start + train_bars + test_bars <= len(events):
            train_events = events[start:start + train_bars]
            test_events = events[start + train_bars:
                                  start + train_bars + test_bars]
            train_data, train_signals = _slice_window(
                price_data, train_events, raw_signals)
            test_data, test_signals = _slice_window(
                price_data, test_events, raw_signals)

            # Tune on the train segment, pick by sharpe (playbook 5.4).
            best_params: Optional[dict] = None
            best_sharpe = float("-inf")
            for params in combos:
                result = self.runner.run(
                    train_data, train_signals, settings_overrides=params)
                sharpe = result.metrics.get("sharpe", 0.0)
                if sharpe > best_sharpe:
                    best_sharpe, best_params = sharpe, params

            # Evaluate the pick out-of-sample (playbook 5.5).
            test_result = self.runner.run(
                test_data, test_signals, settings_overrides=best_params or {})
            windows.append({
                "train_sharpe": best_sharpe if best_params is not None else 0.0,
                "test_sharpe": test_result.metrics.get("sharpe", 0.0),
                "best_params": best_params or {},
            })
            start += test_bars  # slide one test segment forward

        mean_train = (sum(w["train_sharpe"] for w in windows) / len(windows)
                      if windows else 0.0)
        mean_test = (sum(w["test_sharpe"] for w in windows) / len(windows)
                     if windows else 0.0)
        wfer = mean_test / mean_train if mean_train != 0.0 else 0.0
        return {
            "windows": windows,
            "wfer": wfer,
            "passed": wfer >= wfer_min,
        }
