"""Tests for strategy degradation detection and the automated response
ladder (playbook 9.4)."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.store import NewSetupDB
from monitoring.degradation import DegradationDetector
from newsetup.models import Trade

NOW = datetime(2025, 3, 1, tzinfo=timezone.utc)


def _settings(**over):
    base = {
        "paper_trading": {"starting_balance": 10000.0},
        "monitoring": {"degradation": {
            "window_days": 30, "min_trades": 20,
            "win_rate_floor_pct": 40.0, "sharpe_floor": 0.0,
            "reduce_size_lot_mult": 0.5}},
    }
    base["monitoring"]["degradation"].update(over)
    return base


def _trade(pnl: float, closed: datetime, iid: int = 1) -> Trade:
    return Trade(instrument="XAUUSD", direction="BUY", lot_size=1.0,
                 entry_price=100.0, exit_price=100.0 + pnl, stop_loss=98.0,
                 take_profit=110.0, opened_at=closed - timedelta(days=1),
                 closed_at=closed, pnl=pnl, exit_reason="tp",
                 inefficiency_id=iid, sector="s")


def _sequence(n_win: int, n_loss: int, iid: int = 1,
              start: datetime = NOW - timedelta(days=20)) -> list[Trade]:
    """n_win + n_loss trades spread over the 30-day window."""
    trades = []
    total = n_win + n_loss
    for i in range(total):
        ts = start + timedelta(days=20 * i / max(total, 1))
        pnl = 40.0 if i < n_win else -60.0
        trades.append(_trade(pnl, ts, iid))
    return trades


def test_healthy_window_no_escalation():
    det = DegradationDetector(settings=_settings())
    trades = _sequence(12, 8)                    # 60% win rate, positive pnl
    actions = det.evaluate(trades, as_of=NOW)
    assert len(actions) == 1
    a = actions[0]
    assert a.to_level == "ok" and not a.escalated
    assert det.is_tradable(1) is True
    assert det.lot_multiplier(1) == 1.0


def test_degraded_window_escalates_one_step():
    det = DegradationDetector(settings=_settings())
    trades = _sequence(5, 15)                    # 25% win rate
    actions = det.evaluate(trades, as_of=NOW)
    assert len(actions) == 1
    a = actions[0]
    assert a.from_level == "ok" and a.to_level == "reduce_size"
    assert a.lot_multiplier == 0.5
    assert any("win rate" in r for r in a.reasons)


def test_ladder_progression_to_retired():
    det = DegradationDetector(settings=_settings())
    bad = _sequence(5, 15)
    levels = []
    for _ in range(4):
        escalated = det.apply(det.evaluate(bad, as_of=NOW), as_of=NOW)
        levels.append(escalated[0].to_level if escalated else None)
    assert levels == ["reduce_size", "paused", "retired", None]
    assert det.is_tradable(1) is False
    assert det.lot_multiplier(1) == 0.0


def test_min_trades_guard_no_action_on_noise():
    det = DegradationDetector(settings=_settings())
    trades = _sequence(0, 10)                   # all losers but only 10 trades
    assert det.evaluate(trades, as_of=NOW) == []


def test_out_of_window_trades_ignored():
    det = DegradationDetector(settings=_settings())
    fresh = _sequence(5, 15)
    stale = [_trade(-60.0, NOW - timedelta(days=90), iid=2)] * 30
    actions = det.evaluate(fresh + stale, as_of=NOW)
    assert [a.inefficiency_id for a in actions] == [1]   # only iid 1 in window


def test_sharpe_floor_triggers():
    # Win rate above the floor (52%) but the daily-return Sharpe is
    # negative: the Sharpe check alone must escalate.
    trades = []
    for i in range(25):
        ts = NOW - timedelta(days=25 - i)
        trades.append(_trade(5.0 if i % 2 == 0 else -50.0, ts))
    det = DegradationDetector(settings=_settings(win_rate_floor_pct=0.0))
    actions = det.evaluate(trades, as_of=NOW)
    assert actions, "expected a sharpe-driven evaluation"
    assert all("Sharpe" in r for a in actions for r in a.reasons)


def test_state_persists_in_db_across_detectors():
    with NewSetupDB() as db:
        det = DegradationDetector(db=db, settings=_settings())
        det.check_and_respond(_sequence(5, 15), as_of=NOW)
        # A brand-new detector on the same db must read the persisted level.
        det2 = DegradationDetector(db=db, settings=_settings())
        assert det2.lot_multiplier(1) == 0.5
        assert det2.is_tradable(1) is True
        det2.check_and_respond(_sequence(5, 15), as_of=NOW)
        det3 = DegradationDetector(db=db, settings=_settings())
        assert det3.is_tradable(1) is False      # paused now
        state = db.get_degradation_state(1)
        assert state is not None and state["level"] == "paused"


def test_rolling_sharpe_positive_for_consistent_wins():
    det = DegradationDetector(settings=_settings())
    trades = []
    for i in range(30):
        # positive daily pnl with real variance -> sharpe > 0
        trades.append(_trade(40.0 + (i % 3) * 10.0, NOW - timedelta(days=30 - i)))
    assert det._sharpe(trades) > 0.0
