"""Tests for SQLite persistence and per-inefficiency signal quality
tracking (playbook 9.2)."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.store import NewSetupDB
from monitoring.quality_tracker import SignalQualityTracker
from newsetup.models import ConfirmedSignal, RawSignal, SizedSignal, Trade

BASE_TS = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)


def _raw(iid: int = 1, ts=BASE_TS, instrument: str = "XAUUSD") -> RawSignal:
    return RawSignal(inefficiency_id=iid, inefficiency_name=f"ineff {iid}",
                     instrument=instrument, direction="BUY",
                     trigger_type="PRICE", trigger_description="test spike",
                     confidence=0.9, ts=ts)


def _confirmed(raw: RawSignal, score: float = 0.8) -> ConfirmedSignal:
    return ConfirmedSignal(raw=raw, confirmed=True, score=score, reasons=[])


def _trade(iid: int, pnl: float, closed: datetime, entry: float = 100.0,
           lot: float = 1.0, sl: float = 98.0) -> Trade:
    return Trade(instrument="XAUUSD", direction="BUY", lot_size=lot,
                 entry_price=entry, exit_price=entry + pnl, stop_loss=sl,
                 take_profit=entry + 10.0, opened_at=closed - timedelta(days=2),
                 closed_at=closed, pnl=pnl, exit_reason="tp",
                 inefficiency_id=iid, sector="s")


# ------------------------------------------------------------------- store
def test_db_applies_schema_and_roundtrips():
    with NewSetupDB() as db:
        raw = _raw()
        sid = db.insert_signal(raw, confirmed=_confirmed(raw))
        assert sid >= 1
        tid = db.insert_trade(_trade(1, 50.0, BASE_TS + timedelta(days=1)))
        assert tid >= 1
        rows = db.conn.execute("SELECT * FROM signals").fetchall()
        assert len(rows) == 1
        assert rows[0]["confirmed"] == 1
        assert rows[0]["inefficiency_id"] == 1
        trades = db.conn.execute("SELECT * FROM trades").fetchall()
        assert len(trades) == 1
        assert abs(trades[0]["pnl"] - 50.0) < 1e-9


def test_quality_aggregation_hand_computed():
    """Two fired (one confirmed), one Jan win, one Feb loss."""
    with NewSetupDB() as db:
        tracker = SignalQualityTracker(db)
        r1, r2 = _raw(1), _raw(1, ts=BASE_TS + timedelta(hours=1))
        tracker.record_cycle([r1, r2], [_confirmed(r1)], [], [])
        tracker.record_cycle([], [], [],
                             [_trade(1, 50.0, datetime(2025, 1, 20, tzinfo=timezone.utc)),
                              _trade(1, -30.0, datetime(2025, 2, 5, tzinfo=timezone.utc))])
        assert tracker.refresh() == 2          # months 2025-01 and 2025-02

        jan = db.quality_rows(month="2025-01", inefficiency_id=1)
        assert len(jan) == 1
        assert jan[0]["signals_fired"] == 2
        assert jan[0]["signals_confirmed"] == 1
        assert jan[0]["trades_taken"] == 1
        assert jan[0]["wins"] == 1
        assert abs(jan[0]["gross_pnl"] - 50.0) < 1e-9

        feb = db.quality_rows(month="2025-02", inefficiency_id=1)
        assert feb[0]["signals_fired"] == 0
        assert feb[0]["trades_taken"] == 1
        assert feb[0]["wins"] == 0
        assert abs(feb[0]["gross_pnl"] - (-30.0)) < 1e-9


def test_quality_upsert_is_idempotent():
    with NewSetupDB() as db:
        tracker = SignalQualityTracker(db)
        raw = _raw(3)
        tracker.record_cycle([raw], [_confirmed(raw)], [],
                             [_trade(3, 20.0, BASE_TS + timedelta(days=1))])
        tracker.refresh()
        tracker.refresh()                      # must not duplicate rows
        rows = db.quality_rows(inefficiency_id=3)
        assert len(rows) == 1
        assert rows[0]["signals_fired"] == 1


def test_funnel_status_vocabulary():
    """Unconfirmed -> rejected; confirmed but unsized -> expired."""
    with NewSetupDB() as db:
        tracker = SignalQualityTracker(db)
        r_ok, r_drop, r_cap = _raw(1), _raw(2), _raw(3)
        cs_drop = ConfirmedSignal(raw=r_drop, confirmed=False, score=0.3,
                                  reasons=["low score"])
        sized = SizedSignal(signal=_confirmed(r_ok), lot_size=0.5,
                            entry_price=100.0, stop_loss=98.0,
                            take_profit=104.0, sector="s", confidence=0.8)
        tracker.record_cycle([r_ok, r_drop, r_cap],
                             [_confirmed(r_ok), cs_drop, _confirmed(r_cap)],
                             [sized])
        statuses = {row["inefficiency_id"]: row["status"]
                    for row in db.conn.execute("SELECT * FROM signals")}
        assert statuses == {1: "emitted", 2: "rejected", 3: "expired"}


def test_monthly_report_markdown():
    with NewSetupDB() as db:
        tracker = SignalQualityTracker(db)
        raw = _raw(7)
        tracker.record_cycle([raw], [_confirmed(raw)], [],
                             [_trade(7, 25.0, BASE_TS + timedelta(days=1))])
        tracker.refresh()
        report = tracker.monthly_report("2025-01")
        assert "ineff" in report or "#7" in report
        assert "gross_pnl" in report
def test_closed_trade_persistence_idempotent_across_restarts(tmp_path):
    """Replaying closed_trades across independent restarts must not duplicate
    rows or inflate signal_quality, while new closes alongside history still
    persist."""
    from execution.paper_broker import PaperBroker

    db_file = str(tmp_path / "test.sqlite3")
    state_file = str(tmp_path / "paper_state.json")
    settings = {"paper_trading": {"starting_balance": 10000.0, "spread_pct": 0.02, "state_file": state_file}}

    t1 = _trade(1, -48.66, datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc))
    t2 = _trade(7, -49.82, datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc))

    # Cycle 1: first close persisted
    b1 = PaperBroker(settings=settings)
    b1._closed.append(t1)
    b1.balance += t1.pnl
    b1.save_state()
    with NewSetupDB(db_file) as db:
        tracker = SignalQualityTracker(db)
        tracker.record_cycle([], [], [], b1.closed_trades)
        tracker.refresh()

    # Cycle 2: independent restart replays b2.closed_trades from disk
    b2 = PaperBroker(settings=settings)
    with NewSetupDB(db_file) as db:
        tracker = SignalQualityTracker(db)
        tracker.record_cycle([], [], [], b2.closed_trades)
        tracker.refresh()
        rows = db.conn.execute("SELECT * FROM trades").fetchall()
        assert len(rows) == 1
        q = db.quality_rows(month="2026-11", inefficiency_id=1)
        assert len(q) == 1
        assert q[0]["trades_taken"] == 1
        assert abs(q[0]["gross_pnl"] - (-48.66)) < 1e-9

    # Cycle 3: new close alongside existing history
    b3 = PaperBroker(settings=settings)
    b3._closed.append(t2)
    b3.balance += t2.pnl
    b3.save_state()
    with NewSetupDB(db_file) as db:
        tracker = SignalQualityTracker(db)
        tracker.record_cycle([], [], [], b3.closed_trades)
        tracker.refresh()
        rows = db.conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
        assert len(rows) == 2
        q1 = db.quality_rows(month="2026-11", inefficiency_id=1)
        q7 = db.quality_rows(month="2026-11", inefficiency_id=7)
        assert q1[0]["trades_taken"] == 1
        assert q7[0]["trades_taken"] == 1
        total_pnl = sum(r["gross_pnl"] for r in db.quality_rows(month="2026-11"))
        assert abs(total_pnl - (-98.48)) < 1e-9
def test_distinct_trade_instances_not_merged():
    """Two distinct closes on the same instrument/inefficiency at different
    timestamps must both be persisted and aggregated."""
    t1 = _trade(1, -48.66, datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc))
    t2 = _trade(1, 75.00, datetime(2026, 11, 25, 0, 0, tzinfo=timezone.utc))
    with NewSetupDB() as db:
        id1 = db.insert_trade(t1)
        id2 = db.insert_trade(t2)
        id1_replay = db.insert_trade(t1)
        assert id1 != id2
        assert id1_replay == id1
        rows = db.conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
        assert len(rows) == 2
        db.refresh_signal_quality()
        q = db.quality_rows(month="2026-11", inefficiency_id=1)
        assert len(q) == 1
        assert q[0]["trades_taken"] == 2
        assert q[0]["wins"] == 1
        assert abs(q[0]["gross_pnl"] - 26.34) < 1e-9
