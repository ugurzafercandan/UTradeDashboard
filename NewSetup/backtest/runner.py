"""Event-driven backtest runner (playbook sections 5.1-5.2).

Replays historical bars chronologically through layer-2 confirmation and
layer-3 sizing against a broker. The broker is injectable (the production
PaperBroker implements the same interface) or defaults to _SimBroker, a
minimal local fill simulator: entries fill at the signal price plus a
0.02% spread and stops/targets resolve against subsequent bars' low/high.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Optional

from newsetup.config import load_settings
from newsetup.models import (AccountState, PriceBar, RawSignal, SizedSignal,
                             Trade)

from signals.layer2_confirmation import Layer2Confirmation
from signals.layer3_portfolio import Layer3PortfolioManager

from .analyzer import BacktestAnalyzer

# Sections searched when resolving flat override keys like 'rsi_oversold'.
_OVERRIDE_SECTIONS = ("layer2", "layer3", "risk", "sizing", "layer1", "backtest")


# ----------------------------------------------------------------------
def _deep_merge(base: dict, override: Optional[dict]) -> dict:
    """Deep-merge `override` onto a copy of `base` (never mutates base)."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _nest_overrides(settings: dict, overrides: Optional[dict]) -> dict:
    """Map flat param names onto their settings section.

    A walk-forward grid may use flat names ('rsi_oversold'); this locates
    the owning section (layer2/layer3/risk/sizing/...) so runner.run()'s
    settings_overrides reach the layer that consumes them.
    """
    if not overrides:
        return {}
    nested: dict[str, Any] = {}
    for key, value in overrides.items():
        if isinstance(settings.get(key), dict):
            nested[key] = copy.deepcopy(value)
            continue
        for section in _OVERRIDE_SECTIONS:
            if isinstance(settings.get(section), dict) and key in settings[section]:
                nested.setdefault(section, {})[key] = copy.deepcopy(value)
                break
        else:
            # Unknown flat param: assume it is a layer-2 confirmation knob.
            nested.setdefault("layer2", {})[key] = copy.deepcopy(value)
    return nested


# ----------------------------------------------------------------------
@dataclass
class BacktestResult:
    """Output of one backtest run (playbook 5.1-5.3)."""

    equity_curve: list[float]
    trades: list
    metrics: dict
    acceptance_passed: bool
    acceptance_failures: list[str] = field(default_factory=list)
    final_equity: float = 0.0


class InMemoryPrices:
    """Price provider over in-memory bars with a replay cursor (5.1).

    get_series(symbol, lookback_days) returns the tail of the symbol's
    series up to the current replay index; the runner advances the cursor
    as it walks the merged chronological stream.

    UGT-17/19 item 2 (intraday execution): `bars_per_day` marks symbols
    whose execution stream is intraday (H1=24, M15=96). For those,
    get_series returns DAILY aggregates of the visible execution bars so
    layer-2 (RSI/SMA) and layer-3 (ATR) keep playbook daily-bar semantics,
    while get_spot returns the latest execution bar (entry pricing and
    broker SL/TP resolution happen on the intraday stream).
    """

    def __init__(self, price_data: dict[str, list[PriceBar]],
                 bars_per_day: Optional[dict[str, int]] = None):
        self.series: dict[str, list[PriceBar]] = {
            symbol: sorted(bars, key=lambda b: b.ts)
            for symbol, bars in price_data.items()
        }
        self.bars_per_day: dict[str, int] = {
            symbol: (bars_per_day or {}).get(symbol, 1)
            for symbol in self.series
        }
        self._cursor: dict[str, int] = {symbol: 0 for symbol in self.series}

    def advance(self, symbol: str, index: int) -> None:
        """Make bars[:index] visible to the signal layers."""
        self._cursor[symbol] = max(self._cursor.get(symbol, 0), index)

    def get_spot(self, symbol: str) -> Optional[PriceBar]:
        """Latest visible execution bar (entry pricing on the H1 stream)."""
        bars = self.series.get(symbol, [])
        cursor = self._cursor.get(symbol, 0)
        if cursor <= 0:
            return None
        return bars[cursor - 1]

    def get_execution_bars(self, symbol: str, count: int = 30) -> list[PriceBar]:
        """Tail of the raw execution stream (intraday when present).

        Layer-3 uses these for ATR-based stop sizing so that on an H1
        execution stream stops/targets are sized to intraday volatility
        and exits resolve within the event response instead of spanning
        months of daily-ATR distance.
        """
        bars = self.series.get(symbol, [])
        cursor = self._cursor.get(symbol, 0)
        return bars[max(0, cursor - count):cursor]

    def _daily_aggregates(self, bars: list[PriceBar]) -> list[PriceBar]:
        """Aggregate an execution-bar window into daily OHLCV bars."""
        by_day: dict = {}
        for b in bars:
            key = b.ts.date()
            cur = by_day.get(key)
            if cur is None:
                by_day[key] = PriceBar(ts=b.ts, open=b.open, high=b.high,
                                       low=b.low, close=b.close,
                                       volume=b.volume)
            else:
                cur.high = max(cur.high, b.high)
                cur.low = min(cur.low, b.low)
                cur.close = b.close
                cur.volume = cur.volume + b.volume
        return [by_day[d] for d in sorted(by_day)]

    def get_series(self, symbol: str, lookback_days: int = 250) -> list[PriceBar]:
        bars = self.series.get(symbol, [])
        cursor = self._cursor.get(symbol, 0)
        if cursor <= 0:
            return []
        bpd = self.bars_per_day.get(symbol, 1)
        if bpd <= 1:
            return bars[max(0, cursor - lookback_days):cursor]
        window = bars[max(0, cursor - (lookback_days + 10) * bpd):cursor]
        daily = self._daily_aggregates(window)
        return daily[-lookback_days:]


# ----------------------------------------------------------------------
class _SimBroker:
    """Minimal internal broker (playbook 5.2 simulated execution).

    Same interface as the execution package's paper broker: fills at the
    sized signal's entry with a 0.02% spread cost, then resolves SL/TP on
    subsequent bars' low/high and marks open trades to the last close.
    """

    def __init__(self, starting_balance: float, settings: dict):
        self.balance = float(starting_balance)
        self.settings = settings
        self.spread_pct = float(
            settings.get("paper_trading", {}).get("spread_pct", 0.02))
        self._open: list[Trade] = []
        self._closed: list[Trade] = []
        self._last_close: dict[str, float] = {}
        self._last_ts: dict[str, Any] = {}

    # -- interface ----------------------------------------------------
    def submit(self, signal: SizedSignal) -> Trade:
        raw = signal.signal.raw
        spread = signal.entry_price * self.spread_pct / 100.0
        fill = (signal.entry_price + spread if raw.direction == "BUY"
                else signal.entry_price - spread)
        trade = Trade(
            instrument=raw.instrument,
            direction=raw.direction,
            lot_size=signal.lot_size,
            entry_price=fill,
            exit_price=0.0,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            opened_at=raw.ts,
            inefficiency_id=raw.inefficiency_id,
            sector=signal.sector,
        )
        self._open.append(trade)
        return trade

    def on_bar(self, symbol: str, bar: PriceBar) -> list[Trade]:
        self._last_close[symbol] = bar.close
        self._last_ts[symbol] = bar.ts
        closed: list[Trade] = []
        for trade in list(self._open):
            if trade.instrument != symbol:
                continue
            exit_price = self._exit_price(trade, bar)
            if exit_price is not None:
                self._settle(trade, exit_price, bar.ts, "sl_tp")
                closed.append(trade)
        return closed

    def close_all(self) -> list[Trade]:
        """Force-close remaining positions at each symbol's last close."""
        for trade in list(self._open):
            self._settle(
                trade,
                self._last_close.get(trade.instrument, trade.entry_price),
                self._last_ts.get(trade.instrument, trade.opened_at),
                "end_of_data",
            )
        return list(self._closed)

    @property
    def open_trades(self) -> list[Trade]:
        return list(self._open)

    @property
    def closed_trades(self) -> list[Trade]:
        return list(self._closed)

    @property
    def account_state(self) -> AccountState:
        return AccountState(balance=self.balance,
                            equity=self.balance + self._unrealized(),
                            open_positions=len(self._open))

    # -- internals ----------------------------------------------------
    @staticmethod
    def _exit_price(trade: Trade, bar: PriceBar) -> Optional[float]:
        if trade.direction == "BUY":
            if bar.low <= trade.stop_loss:
                return trade.stop_loss
            if bar.high >= trade.take_profit:
                return trade.take_profit
        else:
            if bar.high >= trade.stop_loss:
                return trade.stop_loss
            if bar.low <= trade.take_profit:
                return trade.take_profit
        return None

    def _settle(self, trade: Trade, price: float, ts: Any, reason: str) -> None:
        trade.exit_price = price
        trade.closed_at = ts
        trade.exit_reason = reason
        sign = 1.0 if trade.direction == "BUY" else -1.0
        trade.pnl = (price - trade.entry_price) * trade.lot_size * sign
        self.balance += trade.pnl
        if trade in self._open:
            self._open.remove(trade)
        self._closed.append(trade)

    def _unrealized(self) -> float:
        total = 0.0
        for trade in self._open:
            last = self._last_close.get(trade.instrument, trade.entry_price)
            sign = 1.0 if trade.direction == "BUY" else -1.0
            total += (last - trade.entry_price) * trade.lot_size * sign
        return total


# ----------------------------------------------------------------------
class BacktestRunner:
    """Chronological replay through layers 2-3 against a broker (5.1-5.2).

    Per bar timestamp: advance the price cursors, feed the broker, then
    confirm any raw signal due on/before that timestamp and submit what
    layer-3 sizes. An injected broker is reused across run() calls, so
    pass broker=None (fresh internal simulator per run) when running many
    segments, e.g. from the walk-forward optimizer.
    """

    def __init__(self, settings: Optional[dict] = None, broker: Any = None):
        self.settings = _deep_merge(load_settings(), settings)
        self.broker = broker
        self.analyzer = BacktestAnalyzer()

    def run(self,
            price_data: dict[str, list[PriceBar]],
            raw_signals: list[RawSignal],
            starting_balance: float = 10000.0,
            settings_overrides: Optional[dict] = None,
            bars_per_day: Optional[dict[str, int]] = None) -> BacktestResult:
        """Replay the merged timeline and return metrics + acceptance."""
        settings = _deep_merge(
            self.settings, _nest_overrides(self.settings, settings_overrides))
        provider = InMemoryPrices(price_data, bars_per_day=bars_per_day)
        broker = self.broker if self.broker is not None else _SimBroker(
            starting_balance, settings)
        layer2 = Layer2Confirmation(provider, settings=settings)
        layer3 = Layer3PortfolioManager(settings=settings)

        # One time-ordered stream across all symbols.
        events: list[tuple[Any, str, int, PriceBar]] = []
        for symbol, bars in provider.series.items():
            for index, bar in enumerate(bars):
                events.append((bar.ts, symbol, index, bar))
        events.sort(key=lambda e: (e[0], e[1]))

        pending = sorted(raw_signals, key=lambda s: s.ts)
        next_signal = 0
        equity_curve: list[float] = []

        for ts, symbol, index, bar in events:
            provider.advance(symbol, index + 1)
            broker.on_bar(symbol, bar)
            # Signals due on/before this timestamp (playbook 5.1 ordering).
            while next_signal < len(pending) and pending[next_signal].ts <= ts:
                raw = pending[next_signal]
                next_signal += 1
                confirmed = layer2.confirm(raw)
                if not confirmed.confirmed:
                    continue
                sized = layer3.size_positions(
                    [confirmed], broker.account_state,
                    broker.open_trades, provider)
                for signal in sized:
                    broker.submit(signal)
            equity_curve.append(float(broker.account_state.equity))

        # Close any survivors at the last known closes (playbook 5.2).
        if hasattr(broker, "close_all"):
            broker.close_all()

        trades = list(broker.closed_trades)
        metrics = self.analyzer.compute_metrics(trades, equity_curve)
        passed, failures = self.analyzer.acceptance(metrics, settings)
        final_equity = float(broker.account_state.equity)
        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            acceptance_passed=passed,
            acceptance_failures=failures,
            final_equity=final_equity,
        )
