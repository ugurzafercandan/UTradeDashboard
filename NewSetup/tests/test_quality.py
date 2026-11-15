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
