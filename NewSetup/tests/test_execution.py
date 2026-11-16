"""Tests for the NewSetup execution layer (playbook 7.2).

PaperBroker spread fills, SL/TP resolution, account equity, and the
OrderManager placement / rejection path.
"""

from __future__ import annotations

import pytest

from newsetup.models import PriceBar, utcnow
from execution.order_manager import OrderManager
from execution.paper_broker import PaperBroker

from _risk_helpers import make_sized


# ---------------------------------------------------------------- PaperBroker
def test_submit_fills_with_spread():
    broker = PaperBroker(starting_balance=10000.0, spread_pct=0.02)

    buy = broker.submit(make_sized(direction="BUY", entry=100.0))
    assert buy.direction == "BUY"
    # BUY fills above mid at entry * (1 + spread/100)
    assert buy.entry_price == pytest.approx(100.0 * (1 + 0.02 / 100.0))
    assert buy in broker.open_trades
    assert buy.opened_at is not None
    assert buy.closed_at is None

    sell = broker.submit(make_sized(direction="SELL", entry=100.0))
    # SELL fills below mid at entry * (1 - spread/100)
    assert sell.entry_price == pytest.approx(100.0 * (1 - 0.02 / 100.0))
    assert len(broker.open_trades) == 2


def test_stop_loss_closes_buy_with_negative_pnl():
    broker = PaperBroker(spread_pct=0.02)
    trade = broker.submit(make_sized(direction="BUY", entry=100.0,
                                     sl=99.0, tp=102.0, lot=1.0))
    fill = trade.entry_price  # 100.02

    ts = utcnow()
    bar = PriceBar(ts=ts, open=100.0, high=100.5, low=98.0, close=98.5)
    closed = broker.on_bar("XAUUSD", bar)

    assert len(closed) == 1
    assert closed[0] is trade
    assert trade.exit_reason == "sl"
    assert trade.exit_price == pytest.approx(99.0)
    assert trade.closed_at == ts
    # (99 - 100.02) * 1 lot * 10 < 0
    assert trade.pnl == pytest.approx((99.0 - fill) * 1.0 * 10.0)
    assert trade.pnl < 0
    assert broker.open_trades == []
    assert trade in broker.closed_trades
    assert broker.balance == pytest.approx(10000.0 + trade.pnl)


def test_take_profit_closes_buy_with_positive_pnl():
    broker = PaperBroker(spread_pct=0.02)
    trade = broker.submit(make_sized(direction="BUY", entry=100.0,
                                     sl=99.0, tp=102.0, lot=1.0))
    fill = trade.entry_price

    bar = PriceBar(ts=utcnow(), open=100.0, high=103.0, low=100.5, close=102.5)
    closed = broker.on_bar("XAUUSD", bar)

    assert len(closed) == 1
    assert trade.exit_reason == "tp"
    assert trade.exit_price == pytest.approx(102.0)
    assert trade.pnl == pytest.approx((102.0 - fill) * 1.0 * 10.0)
    assert trade.pnl > 0
    assert trade in broker.closed_trades


def test_account_state_equity_tracks_open_pnl():
    broker = PaperBroker(spread_pct=0.02)
    trade = broker.submit(make_sized(direction="BUY", entry=100.0,
                                     sl=99.0, tp=102.0, lot=1.0))
    fill = trade.entry_price

    state = broker.account_state
    assert state.open_positions == 1
    assert state.margin_used == 0.0
    # no price movement since fill -> equity == balance
    assert state.equity == pytest.approx(10000.0)

    bar = PriceBar(ts=utcnow(), open=100.0, high=101.5, low=100.0, close=101.0)
    broker.on_bar("XAUUSD", bar)
    state = broker.account_state
    assert state.balance == pytest.approx(10000.0)
    expected_equity = 10000.0 + (101.0 - fill) * 1.0 * 10.0
    assert state.equity == pytest.approx(expected_equity)
    assert state.equity > state.balance


def test_close_all_and_reset():
    broker = PaperBroker(spread_pct=0.02)
    broker.submit(make_sized(direction="BUY", entry=100.0))
    broker.submit(make_sized(direction="SELL", entry=200.0,
                            instrument="WTIUSD"))
    closed = broker.close_all(price_map={"XAUUSD": 101.0, "WTIUSD": 200.0})
    assert len(closed) == 2
    assert all(t.exit_reason == "manual" for t in closed)
    assert broker.open_trades == []
    assert len(broker.closed_trades) == 2

    broker.reset()
    assert broker.balance == 10000.0
    assert broker.open_trades == []
    assert broker.closed_trades == []


# -------------------------------------------------------------- OrderManager
class _RejectingEnforcer:
    """Stub enforcer that always rejects with 'max_positions'."""

    def __init__(self):
        self.calls = []

    def check(self, sized, account, open_trades):
        self.calls.append((sized, account, open_trades))
        return (False, "max_positions")


def test_order_manager_places_without_enforcer():
    broker = PaperBroker(spread_pct=0.02)
    om = OrderManager(broker)
    sized = make_sized(direction="BUY", entry=100.0)
    trade = om.place(sized)
    assert trade is not None
    assert trade in broker.open_trades
    assert om.rejections == []
    om.sync()  # no-op placeholder must not raise


def test_order_manager_respects_rejecting_enforcer():
    broker = PaperBroker(spread_pct=0.02)
    om = OrderManager(broker)
    enforcer = _RejectingEnforcer()
    sized = make_sized(direction="BUY", entry=100.0)

    result = om.place(sized, risk_enforcer=enforcer)
    assert result is None
    assert broker.open_trades == []
    assert len(om.rejections) == 1
    rejected_signal, reason = om.rejections[0]
    assert rejected_signal is sized
    assert reason == "max_positions"
    # the enforcer was consulted with the broker's live state
    assert enforcer.calls[0][1].open_positions == 0


# --------------------------------------------- UGT-15 Phase-4 persistence
def test_paper_book_persists_across_processes(tmp_path):
    """save_state() -> new PaperBroker() restores the same open book.

    The daily Phase-4 cycle runs one process per day; without persistence
    each day would restart the 4-week paper account from the starting
    balance (the broker is otherwise in-memory by design).
    """
    import json
    state = tmp_path / "paper_state.json"
    settings = {"paper_trading": {"starting_balance": 10000.0,
                                  "spread_pct": 0.02,
                                  "state_file": str(state)}}
    b1 = PaperBroker(settings=settings)
    trade = b1.submit(make_sized(direction="BUY", entry=100.0,
                                  sl=99.0, tp=102.0, lot=1.0))
    bar = PriceBar(ts=utcnow(), open=100.0, high=103.0, low=100.0, close=102.5)
    closed = b1.on_bar("XAUUSD", bar)
    assert closed, "expected the tp hit to close the trade"
    b2_trade = b1.submit(make_sized(direction="SELL", entry=50.0,
                                    sl=51.0, tp=48.0, lot=2.0))
    saved = b1.save_state()
    assert saved == str(state) and state.exists()

    # fresh process restores balance, closed history and the open trade
    b2 = PaperBroker(settings=settings)
    assert b2.balance == pytest.approx(b1.balance)
    assert len(b2.closed_trades) == 1
    assert b2.closed_trades[0].exit_reason == "tp"
    assert len(b2.open_trades) == 1
    assert b2.open_trades[0].instrument == b2_trade.instrument
    assert b2.open_trades[0].lot_size == pytest.approx(2.0)
    assert b2._last_prices.get("XAUUSD") == pytest.approx(102.5)


def test_paper_book_state_tolerates_corrupt_file(tmp_path):
    state = tmp_path / "paper_state.json"
    state.write_text("{ not json", encoding="utf-8")
    settings = {"paper_trading": {"starting_balance": 10000.0,
                                  "spread_pct": 0.02,
                                  "state_file": str(state)}}
    b = PaperBroker(settings=settings)
    assert b.balance == pytest.approx(10000.0)   # fresh book, no crash
    assert b.open_trades == [] and b.closed_trades == []
