"""Tests for the A/B testing framework scaffold (playbook 9.5)."""

from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest import (ABTestFramework, ABTestResult, ABVariant,
                      BacktestRunner)
from backtest.ab_testing import _paired_ttest
from newsetup.indicators import rsi
from newsetup.models import PriceBar, RawSignal

BASE_TS = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _synth_bars(n: int = 600) -> list[PriceBar]:
    bars = []
    for i in range(n):
        close = 100.0 + 0.2 * i + 4.0 * math.sin(i / 6.0)
        bars.append(PriceBar(ts=BASE_TS + timedelta(hours=i), open=close - 0.5,
                             high=close + 1.0, low=close - 1.0, close=close,
                             volume=100.0))
    return bars


def _buy_signals(bars: list[PriceBar], count: int = 12) -> list[RawSignal]:
    signals: list[RawSignal] = []
    last_idx = -100
    for i in range(30, len(bars)):
        window = [b.close for b in bars[max(0, i - 30):i + 1]]
        r = rsi(window, 5)
        if r is not None and r <= 25.0 and i - last_idx >= 10:
            signals.append(RawSignal(
                inefficiency_id=1, inefficiency_name="ineff 1",
                instrument="XAUUSD", direction="BUY", trigger_type="PRICE",
                trigger_description="oversold dip", confidence=0.9,
                ts=bars[i].ts))
            last_idx = i
        if len(signals) >= count:
            break
    return signals


def _runner_and_settings(min_trades: int = 1):
    settings = {
        "layer2": {"min_score": 0.5, "min_history_bars": 20, "rsi_period": 5,
                   "sma_fast": 5, "sma_slow": 20},
        "backtest": {"acceptance": {"min_trades": min_trades}},
        "ab_testing": {"min_folds": 3, "p_value_threshold": 0.05},
    }
    runner = BacktestRunner(settings=settings)
    return runner, settings


def test_paired_ttest_math():
    # Identical diffs -> no evidence.
    t, p = _paired_ttest([0.0, 0.0, 0.0, 0.0])
    assert t == 0.0 and p == 1.0
    # Constant positive diff -> huge t, p ~ 0 (float variance ~1e-34).
    t, p = _paired_ttest([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    assert t > 1e3 and p < 1e-6
    # Alternating diffs -> mean 0, p 1.
    t, p = _paired_ttest([0.5, -0.5, 0.5, -0.5, 0.5, -0.5])
    assert abs(t) < 1e-9 and p > 0.9
    # Too few samples -> neutral.
    t, p = _paired_ttest([0.3])
    assert t == 0.0 and p == 1.0


def test_ab_compare_structure_and_decisions():
    bars = _synth_bars()
    signals = _buy_signals(bars)
    runner, settings = _runner_and_settings(min_trades=1)
    ab = ABTestFramework(runner, settings=settings)

    result = ab.compare(ABVariant("base", {}), ABVariant("base_twin", {}),
                        {"XAUUSD": bars}, signals, folds=4)
    assert isinstance(result, ABTestResult)
    assert result.folds == 4
    assert len(result.fold_sharpes) == 4
    assert result.mean_diff == 0.0        # identical variants
    assert result.decision == "keep_baseline"
    assert result.to_dict()["decision"] == "keep_baseline"

    # A variant that differs produces real per-fold numbers and a verdict
    # from the allowed vocabulary.
    result2 = ab.compare(ABVariant("base", {"rsi_oversold": 25.0}),
                         ABVariant("cand", {"rsi_oversold": 45.0}),
                         {"XAUUSD": bars}, signals, folds=4)
    assert result2.decision in ("adopt_candidate", "keep_baseline", "inconclusive")
    assert all({"baseline_sharpe", "candidate_sharpe"} <= set(f)
               for f in result2.fold_sharpes)
    assert isinstance(result2.t_stat, float) and isinstance(result2.p_value, float)


def test_ab_inconclusive_when_too_few_folds():
    bars = _synth_bars(200)
    signals = _buy_signals(bars)
    runner, settings = _runner_and_settings()
    ab = ABTestFramework(runner, settings=settings)
    result = ab.compare(ABVariant("a", {}), ABVariant("b", {"rsi_oversold": 35.0}),
                        {"XAUUSD": bars}, signals, folds=2)
    assert result.decision == "inconclusive"
    assert any("folds" in n for n in result.notes)


def test_ab_inconclusive_when_trades_below_minimum():
    bars = _synth_bars()
    signals = _buy_signals(bars)
    runner, settings = _runner_and_settings(min_trades=10_000)
    ab = ABTestFramework(runner, settings=settings)
    result = ab.compare(ABVariant("a", {}), ABVariant("b", {}),
                        {"XAUUSD": bars}, signals, folds=4)
    assert result.decision == "inconclusive"
    assert any("trade" in n for n in result.notes)
