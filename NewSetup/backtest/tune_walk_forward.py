"""Real-data walk-forward parameter tuning (UGT-14, playbook 5.4-5.5).

Tunes the sanctioned settings.yaml search space (layer-2 min_score, RSI/SMA
windows, ATR SL/TP multiples, heat/sector caps) on REAL cached D1 bars using
calendar walk-forward folds:

    train 3 calendar years -> test the next calendar year, sliding by 1y
    (test years 2020..2024), 2025-01-01..cache-end kept as an UNTOUCHED
    out-of-sample holdout for the final acceptance evaluation.

Per fold the grid combo with the best train Sharpe (among combos reaching
the acceptance minimum trade count on train) is selected and evaluated on
the test year.  The candidate adopted for final evaluation is the pick of
the LAST (most recent) fold, so the holdout is never used for selection.

Signals are the layer-1 replay stack (event_backtests +
data/historical_events + data/mapped_events): PRICE triggers per symbol
(direction-model aware) PLUS EVENT triggers from the historical event
store (UGT-17/19) and the UGT-23 mapped dataset - so EVENT triggers now
fire across 2017-2026 including the holdout (GDELT DOC 2.0 itself still
has no history; the store backfills it).

Usage (from the repo root, C:/Python314/python.exe):

    python -m backtest.tune_walk_forward tune [--quick]
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from newsetup.config import ROOT, load_inefficiencies, load_settings
from newsetup.models import PriceBar, RawSignal

from data.bar_cache import BarCache, CACHE_DIR
from .event_backtests import PLAYBOOK_WINDOWS, _symbol_owner, replay_price_signals, run_event_backtest
from .runner import BacktestRunner

log = logging.getLogger("newsetup.tune_walk_forward")

RESULTS_DIR = os.path.join(ROOT, "backtest", "results")
TUNING_JSON = os.path.join(RESULTS_DIR, "wf_tuning.json")

# Tuning period: folds test years 2020..2024; holdout stays untouched.
HOLDOUT_START = "2025-01-01"


@dataclass(frozen=True)
class Fold:
    train_start: str
    train_end: str      # inclusive
    test_start: str
    test_end: str       # inclusive


def default_folds() -> list[Fold]:
    """3y train -> 1y test, sliding: test years 2020..2024."""
    folds = []
    for test_year in range(2020, 2025):
        folds.append(Fold(
            train_start=f"{test_year - 3}-01-01",
            train_end=f"{test_year - 1}-12-31",
            test_start=f"{test_year}-01-01",
            test_end=f"{test_year}-12-31",
        ))
    return folds


def param_grid(quick: bool = False) -> dict[str, list]:
    """Sanctioned search space (issue UGT-14)."""
    grid = {
        "layer2.min_score": [0.35, 0.5, 0.6],
        "layer2.rsi_period": [7, 14],
        "layer2.sma_fast": [20, 50],
        "layer2.sma_slow": [100, 200],
        "sizing.atr_mult_sl": [1.5, 2.0, 3.0],
        "sizing.reward_risk": [1.0, 1.5, 2.0, 3.0],
        "risk.max_portfolio_heat_pct": [3.0, 6.0],
        "risk.max_sector_exposure_pct": [20.0, 40.0],
    }
    if quick:
        grid["layer2.min_score"] = [0.6]
        grid["layer2.rsi_period"] = [14]
        grid["sizing.reward_risk"] = [2.0]
        grid["risk.max_portfolio_heat_pct"] = [3.0]
    return grid


def overrides_from_combo(combo: dict) -> dict:
    """Flat 'section.key' combo -> nested settings override dict."""
    nested: dict = {}
    for flat_key, value in combo.items():
        section, key = flat_key.split(".", 1)
        nested.setdefault(section, {})[key] = value
    return nested


# ------------------------------------------------------------------ data
def build_universe(cache: BarCache,
                   warmup_bars: int = 260) -> tuple[dict[str, list[PriceBar]], list[RawSignal]]:
    """All cached symbols' full history + layer-1 replay signals.

    PRICE triggers replay per symbol (direction-model aware). Since the
    UGT-17/23 structural rework, the universe ALSO carries layer-1 EVENT
    triggers so the walk-forward folds and the holdout run test the
    rebuilt stack instead of a price-trigger-only proxy (the UGT-14
    diagnosis): the UGT-17/19 event store (curated playbook landmarks +
    GDELT export extract, all five windows) plus the UGT-23 mapped
    dataset (2017-2019 walk-forward train years + 2025-2026 holdout;
    window groups excluded to avoid double-counting the store's window
    coverage).
    """
    from data.historical_events import load_all_events, replay_event_signals
    from data.mapped_events import load_mapped_signals

    inefficiencies = load_inefficiencies()
    price_data: dict[str, list[PriceBar]] = {}
    signals: list[RawSignal] = []
    pseudo_id = 1000
    for symbol in cache.cached_symbols():
        bars = cache.load(symbol)
        if not bars or len(bars) < warmup_bars + 30:
            continue
        owner = _symbol_owner(inefficiencies, symbol)
        if owner is not None:
            ineff_id, ineff_name = owner.id, owner.name
        else:
            pseudo_id += 1
            ineff_id, ineff_name = pseudo_id, symbol
        price_data[symbol] = bars
        signals.extend(replay_price_signals(bars, ineff_id, ineff_name, symbol))

    available = set(price_data)
    event_signals = replay_event_signals(
        load_all_events(), inefficiencies, available_symbols=available)
    mapped_signals = load_mapped_signals(
        inefficiencies, available_symbols=available)
    signals.extend(event_signals)
    signals.extend(mapped_signals)
    log.info("universe: %d symbols, %d PRICE + %d EVENT (store) "
             "+ %d EVENT (mapped) signals", len(price_data),
             len(signals) - len(event_signals) - len(mapped_signals),
             len(event_signals), len(mapped_signals))
    signals.sort(key=lambda s: s.ts)
    return price_data, signals


def _ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def slice_run(price_data: dict[str, list[PriceBar]],
              signals: list[RawSignal],
              start: str, end: str,
              warmup_days: int = 400,
              runner: Optional[BacktestRunner] = None,
              settings_overrides: Optional[dict] = None) -> dict:
    """Backtest [start, end] with warmup bars before `start` included."""
    lo, hi = _ts(start), _ts(end)
    warm_lo = lo - timedelta(days=warmup_days)
    data = {}
    for symbol, bars in price_data.items():
        selected = [b for b in bars if warm_lo <= b.ts <= hi]
        if selected:
            data[symbol] = selected
    window_signals = [s for s in signals if lo <= s.ts <= hi]
    runner = runner or BacktestRunner()
    result = runner.run(data, window_signals, settings_overrides=settings_overrides)
    return dict(result.metrics)


# ------------------------------------------------------------------ tune
def tune(cache: Optional[BarCache] = None,
         quick: bool = False,
         folds: Optional[list[Fold]] = None,
         min_train_trades: Optional[int] = None) -> dict:
    """Walk-forward grid search over the sanctioned parameter space."""
    cache = cache or BarCache(CACHE_DIR, connect=False)
    price_data, signals = build_universe(cache)
    settings = load_settings()
    if min_train_trades is None:
        min_train_trades = int(settings["backtest"]["acceptance"]["min_trades"])
    wfer_min = float(settings["backtest"]["walk_forward"]["wfer_min"])

    grid = param_grid(quick=quick)
    names = list(grid)
    combos = [dict(zip(names, values)) for values in itertools.product(*grid.values())]
    folds = folds or default_folds()
    log.info("tuning %d combos over %d folds", len(combos), len(folds))

    runner = BacktestRunner()
    fold_reports = []
    for fold in folds:
        best = None
        best_sharpe = float("-inf")
        eligible = 0
        for combo in combos:
            metrics = slice_run(price_data, signals, fold.train_start, fold.train_end,
                                runner=runner,
                                settings_overrides=overrides_from_combo(combo))
            if metrics.get("total_trades", 0) >= min_train_trades:
                eligible += 1
                if metrics.get("sharpe", 0.0) > best_sharpe:
                    best_sharpe = metrics.get("sharpe", 0.0)
                    best = combo
        if best is None:            # nothing reached the trade floor
            log.warning("fold %s: no combo reached %d train trades",
                        fold.test_start, min_train_trades)
            for combo in combos:
                metrics = slice_run(price_data, signals, fold.train_start, fold.train_end,
                                    runner=runner,
                                    settings_overrides=overrides_from_combo(combo))
                if metrics.get("sharpe", 0.0) > best_sharpe:
                    best_sharpe = metrics.get("sharpe", 0.0)
                    best = combo
        test_metrics = slice_run(price_data, signals, fold.test_start, fold.test_end,
                                 runner=runner,
                                 settings_overrides=overrides_from_combo(best or {}))
        fold_reports.append({
            "fold": asdict(fold),
            "eligible_combos": eligible,
            "best_params": best or {},
            "train_sharpe": best_sharpe,
            "test_metrics": test_metrics,
        })
        log.info("fold %s: best=%s train_sharpe=%.2f test_sharpe=%.2f test_trades=%d",
                 fold.test_start, best, best_sharpe,
                 test_metrics.get("sharpe", 0.0), test_metrics.get("total_trades", 0))

    mean_train = (sum(f["train_sharpe"] for f in fold_reports) / len(fold_reports)
                  if fold_reports else 0.0)
    mean_test = (sum(f["test_metrics"].get("sharpe", 0.0) for f in fold_reports)
                 / len(fold_reports) if fold_reports else 0.0)
    # Scaffold WFER definition; only meaningful when mean train Sharpe > 0.
    wfer = mean_test / mean_train if mean_train != 0.0 else 0.0
    wfer_meaningful = mean_train > 0.0
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "grid": grid,
        "grid_size": len(combos),
        "min_train_trades": min_train_trades,
        "folds": fold_reports,
        "mean_train_sharpe": mean_train,
        "mean_test_sharpe": mean_test,
        "wfer": wfer,
        "wfer_meaningful": wfer_meaningful,
        "wfer_min": wfer_min,
        "wfer_gate_passed": bool(wfer_meaningful and wfer >= wfer_min),
        "final_candidate": fold_reports[-1]["best_params"] if fold_reports else {},
        "holdout_start": HOLDOUT_START,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(TUNING_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return report


# ------------------------------------------------------------------ main
def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "tune":
        quick = "--quick" in argv
        report = tune(quick=quick)
        print(json.dumps({k: report[k] for k in
                          ("grid_size", "mean_train_sharpe", "mean_test_sharpe",
                           "wfer", "wfer_gate_passed", "final_candidate")},
                         indent=2, default=str))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
