"""Tests for the NewSetup backtest package (playbook sections 5.1-5.5).

Covers BacktestAnalyzer math on a hand-computed case, the acceptance
gates, an end-to-end BacktestRunner replay over synthetic XAUUSD bars
with a local FakeBroker, and a WalkForwardOptimizer smoke run.
"""

from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timedelta, timezone

# Make NewSetup/ importable (packages: newsetup, signals, backtest) no
# matter which directory pytest was invoked from.
_NEWSETUP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _NEWSETUP_DIR not in sys.path:
    sys.path.insert(0, _NEWSETUP_DIR)

from backtest import (BacktestAnalyzer, BacktestResult, BacktestRunner,
                      WalkForwardOptimizer)
from newsetup.indicators import rsi
from newsetup.models import AccountState, PriceBar, RawSignal, Trade

BASE_TS = datetime(2025, 1, 1, tzinfo=timezone.utc)


# ----------------------------------------------------------------------
class FakeBroker:
    """Minimal local broker implementing the execution interface."""

    def __init__(self, balance: float = 10000.0):
        self.balance = float(balance)
        self._open: list[Trade] = []
        self._closed: list[Trade] = []

    def submit(self, sig) -> Trade:
        raw = sig.signal.raw
        trade = Trade(instrument=raw.instrument, direction=raw.direction,
                      lot_size=sig.lot_size, entry_price=sig.entry_price,
                      exit_price=0.0, stop_loss=sig.stop_loss,
                      take_profit=sig.take_profit, opened_at=raw.ts,
                      inefficiency_id=raw.inefficiency_id, sector=sig.sector)
        self._open.append(trade)
        return trade

    def on_bar(self, symbol: str, bar: PriceBar) -> list[Trade]:
        done = []
        for t in self._open:
            if t.instrument != symbol:
                continue
            sl = bar.low <= t.stop_loss if t.direction == "BUY" else bar.high >= t.stop_loss
            tp = bar.high >= t.take_profit if t.direction == "BUY" else bar.low <= t.take_profit
            if sl or tp:
                self._settle(t, t.stop_loss if sl else t.take_profit, bar.ts)
                done.append(t)
        for t in done:
            self._open.remove(t)
        return done

    def _settle(self, t: Trade, price: float, ts: datetime) -> None:
        t.exit_price, t.closed_at, t.exit_reason = price, ts, "sl_tp"
        sign = 1.0 if t.direction == "BUY" else -1.0
        t.pnl = (price - t.entry_price) * t.lot_size * sign
        self.balance += t.pnl
        self._closed.append(t)

    def close_all(self) -> list[Trade]:
        for t in list(self._open):
            self._settle(t, t.entry_price, t.opened_at)
        self._open.clear()
        return list(self._closed)

    @property
    def open_trades(self) -> list[Trade]:
        return list(self._open)

    @property
    def closed_trades(self) -> list[Trade]:
        return list(self._closed)

    @property
    def account_state(self) -> AccountState:
        return AccountState(balance=self.balance, equity=self.balance,
                            open_positions=len(self._open))


def _make_trade(pnl: float, entry: float = 100.0, sl: float = 98.0,
                lot: float = 1.0) -> Trade:
    return Trade(instrument="XAUUSD", direction="BUY", lot_size=lot,
                 entry_price=entry, exit_price=entry + pnl / lot,
                 stop_loss=sl, take_profit=entry + 10.0, opened_at=BASE_TS,
                 closed_at=BASE_TS + timedelta(hours=1), pnl=pnl,
                 exit_reason="take_profit", inefficiency_id=1, sector="s")


def _synth_bars(n: int = 260) -> list[PriceBar]:
    """Deterministic XAUUSD bars: upward drift plus a sine oscillation."""
    bars = []
    for i in range(n):
        close = 1900.0 + 0.8 * i + 12.0 * math.sin(i / 7.0)
        bars.append(PriceBar(ts=BASE_TS + timedelta(hours=i),
                             open=close - 1.0, high=close + 2.0,
                             low=close - 2.0, close=close, volume=100.0))
    return bars


def _buy_signals(bars: list[PriceBar], count: int = 3,
                 lookback: int = 30) -> list[RawSignal]:
    """BUY signals at deterministic oversold (RSI(5) <= 25) troughs."""
    signals: list[RawSignal] = []
    last_idx = -100
    for i in range(lookback, len(bars)):
        window = [b.close for b in bars[max(0, i - lookback + 1):i + 1]]
        r = rsi(window, 5)
        if r is not None and r <= 25.0 and i - last_idx >= 10:
            signals.append(RawSignal(
                inefficiency_id=1 + len(signals),
                inefficiency_name=f"inefficiency {1 + len(signals)}",
                instrument="XAUUSD", direction="BUY", trigger_type="PRICE",
                trigger_description="oversold dip", confidence=0.9,
                ts=bars[i].ts))
            last_idx = i
        if len(signals) >= count:
            break
    return signals


# ---------------------------------------------------------------- analyzer
def test_analyzer_metrics_hand_computed():
    """Playbook 5.1: hand-computed tiny case (1 winner of 3 trades)."""
    analyzer = BacktestAnalyzer()
    trades = [_make_trade(150.0), _make_trade(-50.0), _make_trade(-50.0)]
    curve = [10000.0, 10100.0, 9900.0, 10200.0]
    m = analyzer.compute_metrics(trades, curve)

    assert m["total_trades"] == 3
    assert abs(m["win_rate_pct"] - 100.0 / 3.0) < 0.01          # ~33.33
    # Drawdown measured from the running peak 10100 -> 9900 = 1.98%.
    assert abs(m["max_drawdown_pct"] - 200.0 / 10100.0 * 100.0) < 0.05
    assert isinstance(m["sharpe"], float)
    assert isinstance(m["sortino"], float)
    assert abs(m["profit_factor"] - 1.5) < 0.01
    assert abs(m["total_return_pct"] - 2.0) < 0.01
    assert m["avg_win"] == 150.0
    assert m["avg_loss"] == 50.0
    assert isinstance(m["expectancy_r"], float)


def test_acceptance_gates():
    """Playbook 5.3: min_trades failure and an all-passing metrics set."""
    analyzer = BacktestAnalyzer()

    failing = {"total_trades": 5, "win_rate_pct": 60.0, "profit_factor": 2.0,
               "sharpe": 2.0, "max_drawdown_pct": 5.0}
    ok, failures = analyzer.acceptance(failing)
    assert ok is False
    assert any("min_trades" in f for f in failures)

    passing = {"total_trades": 50, "win_rate_pct": 55.0, "profit_factor": 1.5,
               "sharpe": 1.5, "max_drawdown_pct": 6.0}
    ok, failures = analyzer.acceptance(passing)
    assert ok is True and failures == []

    # Explicit settings override the loaded defaults.
    strict = {"backtest": {"acceptance": {
        "min_trades": 100, "max_drawdown_pct": 12.0, "min_sharpe": 1.0,
        "min_win_rate_pct": 48.0, "min_profit_factor": 1.3}}}
    ok, failures = analyzer.acceptance(passing, settings=strict)
    assert ok is False
    assert any("min_trades" in f for f in failures)


# ------------------------------------------------------------------ runner
def test_runner_end_to_end_synthetic():
    """Playbook 5.1-5.2: full replay with a local FakeBroker."""
    bars = _synth_bars(260)
    signals = _buy_signals(bars, count=3)
    assert len(signals) == 3

    runner = BacktestRunner(
        settings={"layer2": {"min_score": 0.5, "min_history_bars": 20,
                            "rsi_period": 5, "sma_fast": 5, "sma_slow": 20}},
        broker=FakeBroker(10000.0),
    )
    result = runner.run({"XAUUSD": bars}, signals, starting_balance=10000.0)

    assert isinstance(result, BacktestResult)
    assert len(result.equity_curve) > 0
    assert "total_trades" in result.metrics
    assert result.metrics["total_trades"] >= 1
    assert (result.final_equity != 10000.0
            or result.metrics["total_trades"] > 0)
    assert isinstance(result.acceptance_passed, bool)


def test_runner_internal_sim_broker():
    """Playbook 5.2: default path uses the built-in _SimBroker."""
    bars = _synth_bars(260)
    signals = _buy_signals(bars, count=2)
    runner = BacktestRunner(
        settings={"layer2": {"min_score": 0.5, "min_history_bars": 20,
                            "rsi_period": 5, "sma_fast": 5, "sma_slow": 20}},
    )
    result = runner.run({"XAUUSD": bars}, signals)
    assert isinstance(result, BacktestResult)
    assert result.final_equity > 0
    assert result.metrics["total_trades"] >= 0


# ------------------------------------------------------------ walk-forward
def test_walk_forward_smoke():
    """Playbook 5.4-5.5: optimizer returns windows and a WFER float."""
    bars = _synth_bars(260)
    signals = _buy_signals(bars, count=3)
    runner = BacktestRunner(
        settings={"layer2": {"min_score": 0.5, "min_history_bars": 15,
                            "rsi_period": 5, "sma_fast": 5, "sma_slow": 10}},
    )
    optimizer = WalkForwardOptimizer(runner, {"rsi_oversold": [25, 30]})
    result = optimizer.run({"XAUUSD": bars}, signals,
                           train_bars=40, test_bars=20)

    assert "windows" in result
    assert isinstance(result["wfer"], float)
    assert isinstance(result["windows"], list)
    if result["windows"]:
        first = result["windows"][0]
        assert {"train_sharpe", "test_sharpe", "best_params"} <= set(first)
