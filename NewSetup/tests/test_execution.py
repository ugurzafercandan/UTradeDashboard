"""Tests for the NewSetup execution layer (playbook 7.2).

PaperBroker spread fills, SL/TP resolution, account equity, and the
OrderManager placement / rejection path.
"""

from __future__ import annotations

import pytest

from datetime import timedelta

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


def test_on_bar_ignores_bars_at_or_before_open():
    """UGT-15 cycle-1 defect: the pre-open D1 replay must never close a
    fresh position on a bar stamped before the fill (phantom SL hit with
    closed_at < opened_at)."""
    broker = PaperBroker(spread_pct=0.02)
    trade = broker.submit(make_sized(direction="BUY", entry=100.0,
                                     sl=99.0, tp=102.0, lot=1.0))

    # historical bar stamped 5 days BEFORE the fill; low pierces the SL
    stale = PriceBar(ts=trade.opened_at - timedelta(days=5),
                     open=100.0, high=100.5, low=98.0, close=98.5)
    closed = broker.on_bar("XAUUSD", stale)
    assert closed == []
    assert trade in broker.open_trades
    assert broker.closed_trades == []
    assert trade.exit_reason == ""

    # a bar stamped after the open still resolves SL normally
    fresh = PriceBar(ts=trade.opened_at + timedelta(hours=1),
                     open=100.0, high=100.5, low=98.0, close=98.5)
    closed = broker.on_bar("XAUUSD", fresh)
    assert len(closed) == 1
    assert closed[0] is trade
    assert trade.exit_reason == "sl"
    assert trade.closed_at == fresh.ts


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


def test_anti_wipe_guard_on_save_state(tmp_path):
    """A fresh-reset book must never overwrite a populated state file
    (UGT-15 incident 2026-11-16: a validation run wiped the live book)."""
    import json
    state = tmp_path / "state.json"
    state.write_text(json.dumps({
        "version": 1, "starting_balance": 10000.0, "balance": 10000.0,
        "peak_equity": 10000.0,
        "open": [{"instrument": "USDCNH", "pnl": 0.0}], "closed": [],
        "last_prices": {}}))
    broker = PaperBroker(starting_balance=10000.0, spread_pct=0.02,
                         settings={"paper_trading": {"state_file": str(state)}})
    broker.reset()  # fresh default book: no open, no closed, balance == start
    with pytest.raises(RuntimeError, match="anti-wipe"):
        broker.save_state()
    # the populated file is untouched
    assert json.loads(state.read_text())["open"]


def test_save_state_persists_post_fill_high_water(tmp_path):
    """save_state() persists the post-fill equity high-water mark.

    UGT-15 cycle-4 audit: main.py last touches account_state BEFORE placing
    fills, so a new post-fill equity mark only entered the in-memory peak
    during the daily report -- after save_state. RiskEnforcer reads
    broker.peak_equity as its drawdown reference each cycle, so the
    persisted peak must include the post-fill mark (a stale low peak
    understates drawdown and delays the 5/8/12% breakers).
    """
    state = tmp_path / "paper_state.json"
    settings = {"paper_trading": {"starting_balance": 10000.0,
                                  "spread_pct": 0.02,
                                  "state_file": str(state)}}
    b1 = PaperBroker(settings=settings)
    trade = b1.submit(make_sized(direction="BUY", entry=100.0,
                                  sl=90.0, tp=120.0, lot=1.0))
    # price rallies past the fill AFTER the pre-fill account_state touches
    # (no further account_state call before the save); wide SL/TP so the
    # bar records the price WITHOUT resolving the position
    bar = PriceBar(ts=trade.opened_at + timedelta(hours=1),
                   open=100.0, high=103.0, low=100.0, close=102.5)
    assert b1.on_bar("XAUUSD", bar) == []   # no SL/TP hit, price recorded
    expected_equity = 10000.0 + (102.5 - trade.entry_price) * 1.0 * 10.0
    assert expected_equity > 10000.0
    # the in-memory peak has not seen the post-fill mark yet...
    assert b1.peak_equity == pytest.approx(10000.0)
    # ...but save_state must persist it, not the stale starting peak
    b1.save_state()
    b2 = PaperBroker(settings=settings)
    assert b2.peak_equity == pytest.approx(expected_equity)
    assert b2.account_state.equity == pytest.approx(expected_equity)
    # balance and book contents are untouched by the re-mark
    assert b2.balance == pytest.approx(10000.0)
    assert len(b2.open_trades) == 1
    assert b2.open_trades[0].instrument == trade.instrument
