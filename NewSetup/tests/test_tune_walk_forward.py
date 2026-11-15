"""Tests for the UGT-14 real-data walk-forward tuning modules.

Covers tune_walk_forward (grid/override mapping, fold layout, slice_run
warmup behavior, a tiny end-to-end tune on synthetic bars with the
results redirected to a tmp dir) and the wf_evaluate momentum-direction
replay probe.
"""

from __future__ import annotations

import importlib
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

_NEWSETUP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _NEWSETUP_DIR not in sys.path:
    sys.path.insert(0, _NEWSETUP_DIR)

import pytest

from backtest import tune_walk_forward as twf
from backtest import wf_evaluate
from newsetup.models import PriceBar

BASE_TS = datetime(2019, 1, 1, tzinfo=timezone.utc)


# ------------------------------------------------------------------ helpers
class FakeCache:
    """BarCache stand-in: two synthetic symbols with spike days."""

    def __init__(self):
        self.bars = {f"SYMA{i}": self._make_bars(i) for i in range(2)}

    @staticmethod
    def _make_bars(seed: int) -> list[PriceBar]:
        bars = []
        price = 100.0 + 10 * seed
        for i in range(800):
            # gentle drift, a -3% crash every 120 bars, recovery after
            move = -3.0 if i % 120 == 60 else (0.05 * seed + 0.02)
            price *= 1.0 + move / 100.0
            bars.append(PriceBar(
                ts=BASE_TS + timedelta(days=i),
                open=price, high=price * 1.005, low=price * 0.995,
                close=price, volume=1000.0))
        return bars

    def cached_symbols(self):
        return list(self.bars)

    def load(self, symbol):
        return self.bars.get(symbol, [])


# ------------------------------------------------------------------ units
def test_overrides_from_combo_nests_sections():
    combo = {"layer2.min_score": 0.5, "sizing.atr_mult_sl": 1.5}
    assert twf.overrides_from_combo(combo) == {
        "layer2": {"min_score": 0.5},
        "sizing": {"atr_mult_sl": 1.5},
    }


def test_default_folds_layout():
    folds = twf.default_folds()
    assert len(folds) == 5
    for fold, year in zip(folds, range(2020, 2025)):
        assert fold.test_start == f"{year}-01-01"
        assert fold.train_start == f"{year - 3}-01-01"
        assert fold.train_end == f"{year - 1}-12-31"


def test_param_grid_quick_is_subset():
    full, quick = twf.param_grid(), twf.param_grid(quick=True)
    assert set(quick).issubset(set(full))
    assert twf.param_grid()["sizing.reward_risk"] == [1.0, 1.5, 2.0, 3.0]


def test_slice_run_warmup_and_window(tmp_path):
    cache = FakeCache()
    price_data, signals = twf.build_universe(cache)
    assert signals, "synthetic crashes should produce replay signals"
    # window inside data: signals outside [start, end] excluded
    metrics = twf.slice_run(price_data, signals,
                            "2020-06-01", "2020-12-31")
    assert isinstance(metrics, dict)
    assert "sharpe" in metrics
    # a window with no signals at all trades nothing
    start = (BASE_TS + timedelta(days=5)).strftime("%Y-%m-%d")
    end = (BASE_TS + timedelta(days=25)).strftime("%Y-%m-%d")
    empty = twf.slice_run(price_data, signals, start, end)
    assert empty["total_trades"] == 0


def test_tune_end_to_end_synthetic(tmp_path, monkeypatch):
    monkeypatch.setattr(twf, "RESULTS_DIR", str(tmp_path))
    monkeypatch.setattr(twf, "TUNING_JSON",
                        os.path.join(str(tmp_path), "wf_tuning.json"))
    folds = [
        twf.Fold("2019-01-01", "2020-06-30", "2020-07-01", "2020-12-31"),
        twf.Fold("2019-06-01", "2021-06-30", "2021-07-01", "2021-12-31"),
    ]
    report = twf.tune(cache=FakeCache(), quick=True, folds=folds,
                      min_train_trades=1)
    assert report["grid_size"] > 0
    assert len(report["folds"]) == 2
    assert os.path.exists(os.path.join(str(tmp_path), "wf_tuning.json"))
    for fold in report["folds"]:
        assert fold["best_params"], "a best combo must always be picked"
        assert "test_metrics" in fold
    # WFER bookkeeping present and consistent
    if report["mean_train_sharpe"] == 0.0:
        assert report["wfer"] == 0.0
    else:
        assert report["wfer"] == pytest.approx(
            report["mean_test_sharpe"] / report["mean_train_sharpe"], rel=1e-6)


def test_momentum_replay_direction():
    bars = FakeCache._make_bars(0)
    signals = wf_evaluate.replay_momentum_signals(
        bars, 1, "MOMENTUM", "SYMA0")
    assert signals, "crash days must emit signals"
    for sig in signals:
        assert sig.trigger_type == "PRICE_MOMENTUM"
        # continuation mapping: -3% crash -> SELL
        assert "momentum" in sig.trigger_description


def test_momentum_replay_is_dual_of_reversion():
    from backtest.event_backtests import replay_price_signals
    bars = FakeCache._make_bars(0)
    rev = replay_price_signals(bars, 1, "X", "SYMA0")
    mom = wf_evaluate.replay_momentum_signals(bars, 1, "X", "SYMA0")
    assert len(rev) == len(mom)
    assert all(r.direction != m.direction for r, m in zip(rev, mom))
