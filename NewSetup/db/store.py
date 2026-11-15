"""SQLite persistence for NewSetup (playbook sections 2.4, 9.2, 9.4).

Applies db/schema.sql on open and provides typed accessors for the
signals / trades / signal_quality tables plus the degradation-state
table used by monitoring.degradation. All timestamps are stored as
ISO-8601 UTC strings (newsetup.models.iso) so SQLite can compare and
sort them lexically.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from newsetup.models import (ConfirmedSignal, RawSignal, SizedSignal, Trade,
                             iso)

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "schema.sql")

# Degradation response ladder (playbook 9.4): ok -> reduce_size -> paused ->
# retired. The lot multiplier is applied to layer-3 sizing; paused/retired
# block new entries for the inefficiency.
DEGRADATION_LEVELS = ("ok", "reduce_size", "paused", "retired")
DEFAULT_LOT_MULTIPLIERS = {"ok": 1.0, "reduce_size": 0.5, "paused": 0.0,
                           "retired": 0.0}


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class NewSetupDB:
    """SQLite store for signals, trades and per-inefficiency quality."""

    def __init__(self, path: Optional[str] = None):
        """``path`` defaults to an in-memory database (tests / analysis).

        Pass a file path (typically from settings paths.db_file, resolved
        against the NewSetup root) for durable paper/live tracking.
        """
        self.path = path or ":memory:"
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    # ------------------------------------------------------------ lifecycle
    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "NewSetupDB":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -------------------------------------------------------------- signals
    def insert_signal(self,
                      raw: RawSignal,
                      confirmed: Optional[ConfirmedSignal] = None,
                      sized: Optional[SizedSignal] = None,
                      status: str = "emitted") -> int:
        """Persist one layer-1 signal with its confirmation/sizing state.

        ``confirmed`` carries the layer-2 verdict; ``sized`` the layer-3
        sizing (None when layer 2 or 3 dropped the signal). ``status``
        follows the schema vocabulary: emitted | filled | rejected | expired.
        """
        cs = confirmed
        cur = self.conn.execute(
            """INSERT INTO signals
               (ts, inefficiency_id, instrument, direction, trigger_type,
                trigger_description, layer1_confidence, confirmed,
                layer2_score, lot_size, entry_price, stop_loss,
                take_profit, sector, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (iso(_as_utc(raw.ts)), raw.inefficiency_id, raw.instrument,
             raw.direction, raw.trigger_type, raw.trigger_description,
             float(raw.confidence),
             1 if (cs is not None and cs.confirmed) else 0,
             float(cs.score) if cs is not None else None,
             float(sized.lot_size) if sized is not None else None,
             float(sized.entry_price) if sized is not None else None,
             float(sized.stop_loss) if sized is not None else None,
             float(sized.take_profit) if sized is not None else None,
             sized.sector if sized is not None else None,
             status),
        )
        self.conn.commit()
        assert cur.lastrowid is not None
        return int(cur.lastrowid)

    # --------------------------------------------------------------- trades
    def insert_trade(self, trade: Trade) -> int:
        """Persist a closed trade (open trades have closed_at/pnl unset)."""
        cur = self.conn.execute(
            """INSERT INTO trades
               (opened_at, closed_at, instrument, direction, lot_size,
                entry_price, exit_price, stop_loss, take_profit, pnl,
                exit_reason, inefficiency_id, sector)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (iso(_as_utc(trade.opened_at)),
             iso(_as_utc(trade.closed_at)) if trade.closed_at else None,
             trade.instrument, trade.direction, float(trade.lot_size),
             float(trade.entry_price),
             float(trade.exit_price) if trade.exit_price else None,
             float(trade.stop_loss) if trade.stop_loss else None,
             float(trade.take_profit) if trade.take_profit else None,
             float(trade.pnl),
             trade.exit_reason,
             int(trade.inefficiency_id) if trade.inefficiency_id else None,
             trade.sector or None),
        )
        self.conn.commit()
        assert cur.lastrowid is not None
        return int(cur.lastrowid)

    def closed_trades_since(self, cutoff: datetime) -> list[dict]:
        """Closed trades with closed_at >= cutoff, oldest first."""
        rows = self.conn.execute(
            """SELECT * FROM trades
               WHERE closed_at IS NOT NULL AND closed_at >= ?
               ORDER BY closed_at""", (iso(_as_utc(cutoff)),)).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------- signal quality (9.2)
    def refresh_signal_quality(self, month: Optional[str] = None) -> int:
        """Rebuild signal_quality rows from signals + trades.

        Aggregation rules (documented honestly):
        - signals_fired / signals_confirmed come from the signals table,
          bucketed by the month of the layer-1 timestamp;
        - trades_taken / wins / gross_pnl come from closed trades only,
          bucketed by the month the trade CLOSED (a trade contributes to
          exactly one month; open trades count when they close).
        Returns the number of (month, inefficiency) rows written.
        """
        fired: dict[tuple[str, int], int] = {}
        confirmed: dict[tuple[str, int], int] = {}
        for row in self.conn.execute(
                "SELECT ts, inefficiency_id, confirmed FROM signals"):
            key = (str(row["ts"])[:7], int(row["inefficiency_id"]))
            fired[key] = fired.get(key, 0) + 1
            if row["confirmed"]:
                confirmed[key] = confirmed.get(key, 0) + 1
        taken: dict[tuple[str, int], dict] = {}
        for row in self.conn.execute(
                """SELECT closed_at, inefficiency_id, pnl FROM trades
                   WHERE closed_at IS NOT NULL AND inefficiency_id IS NOT NULL"""):
            key = (str(row["closed_at"])[:7], int(row["inefficiency_id"]))
            agg = taken.setdefault(key, {"n": 0, "wins": 0, "pnl": 0.0})
            agg["n"] += 1
            if row["pnl"] is not None and float(row["pnl"]) > 0.0:
                agg["wins"] += 1
            agg["pnl"] += float(row["pnl"] or 0.0)

        keys = sorted(set(fired) | set(confirmed) | set(taken))
        written = 0
        for key in keys:
            if month is not None and key[0] != month:
                continue
            agg = taken.get(key, {"n": 0, "wins": 0, "pnl": 0.0})
            self.conn.execute(
                """INSERT INTO signal_quality
                   (month, inefficiency_id, signals_fired, signals_confirmed,
                    trades_taken, wins, gross_pnl)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(month, inefficiency_id) DO UPDATE SET
                     signals_fired=excluded.signals_fired,
                     signals_confirmed=excluded.signals_confirmed,
                     trades_taken=excluded.trades_taken,
                     wins=excluded.wins,
                     gross_pnl=excluded.gross_pnl""",
                (key[0], key[1], fired.get(key, 0), confirmed.get(key, 0),
                 agg["n"], agg["wins"], agg["pnl"]))
            written += 1
        self.conn.commit()
        return written

    def quality_rows(self, month: Optional[str] = None,
                     inefficiency_id: Optional[int] = None) -> list[dict]:
        """Persisted per-inefficiency monthly quality rows (playbook 9.2)."""
        sql = "SELECT * FROM signal_quality WHERE 1=1"
        params: list[Any] = []
        if month is not None:
            sql += " AND month = ?"
            params.append(month)
        if inefficiency_id is not None:
            sql += " AND inefficiency_id = ?"
            params.append(inefficiency_id)
        sql += " ORDER BY month, inefficiency_id"
        return [dict(r) for r in
                self.conn.execute(sql, params).fetchall()]

    # ------------------------------------------- degradation state (9.4)
    def get_degradation_state(self, inefficiency_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM degradation_state WHERE inefficiency_id = ?",
            (inefficiency_id,)).fetchone()
        return dict(row) if row else None

    def set_degradation_state(self, inefficiency_id: int, level: str,
                              lot_multiplier: float, reason: str,
                              as_of: datetime) -> None:
        self.conn.execute(
            """INSERT INTO degradation_state
               (inefficiency_id, level, lot_multiplier, updated_at, reason)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(inefficiency_id) DO UPDATE SET
                 level=excluded.level,
                 lot_multiplier=excluded.lot_multiplier,
                 updated_at=excluded.updated_at,
                 reason=excluded.reason""",
            (inefficiency_id, level, float(lot_multiplier),
             iso(_as_utc(as_of)), reason))
        self.conn.commit()

    def degradation_states(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM degradation_state ORDER BY inefficiency_id"
        ).fetchall()
        return [dict(r) for r in rows]
