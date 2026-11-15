"""Per-inefficiency signal quality tracking (playbook 9.2).

Records the full pipeline funnel (fired -> confirmed -> traded -> won)
into the SQLite store and aggregates the monthly signal_quality rows:
signals fired / confirmed, trades taken, wins and gross PnL per
inefficiency per calendar month.

Aggregation rules (stated, not implied):
- a signal belongs to the month of its layer-1 timestamp;
- a trade belongs to the month in which it CLOSED (open trades are
  counted once they close, so months never double-count);
- gross_pnl is the signed sum of closed-trade pnl (no costs removed —
  the paper broker's spread cost is already inside entry fills).
"""

from __future__ import annotations

from typing import Iterable, Optional

from db.store import NewSetupDB
from newsetup.models import (ConfirmedSignal, RawSignal, SizedSignal, Trade)


class SignalQualityTracker:
    """Persists the signal funnel and publishes monthly quality stats."""

    def __init__(self, db: NewSetupDB):
        self.db = db

    # ----------------------------------------------------------- recording
    def record_cycle(self,
                    raw_signals: Iterable[RawSignal],
                    confirmed: Iterable[ConfirmedSignal],
                    sized: Iterable[SizedSignal],
                    closed_trades: Iterable[Trade] = (),
                    ) -> None:
        """Record one pipeline cycle (live, paper or backtest replay).

        ``confirmed`` / ``sized`` are matched back to their raw signal by
        object identity, so the funnel stays truthful even when layer 2
        or layer 3 drop signals.
        """
        confirmed_by_raw = {id(cs.raw): cs for cs in confirmed}
        sized_by_raw = {id(s.signal.raw): s for s in sized}
        for raw in raw_signals:
            cs = confirmed_by_raw.get(id(raw))
            sz = sized_by_raw.get(id(raw))
            if cs is not None and not cs.confirmed:
                status = "rejected"          # layer 2 dropped it
            elif cs is not None and sz is None:
                status = "expired"           # layer 3 caps dropped it
            else:
                status = "emitted"
            self.db.insert_signal(raw, confirmed=cs, sized=sz, status=status)
        for trade in closed_trades:
            self.db.insert_trade(trade)

    def record_backtest(self, raw_signals: Iterable[RawSignal],
                        confirmed: Iterable[ConfirmedSignal],
                        trades: Iterable[Trade]) -> None:
        """Record a finished backtest run (all trades are closed)."""
        self.record_cycle(raw_signals, confirmed, sized=[], closed_trades=trades)

    # ------------------------------------------------------------ reporting
    def refresh(self, month: Optional[str] = None) -> int:
        """Rebuild signal_quality rows; returns rows written."""
        return self.db.refresh_signal_quality(month)

    def monthly_quality(self, month: Optional[str] = None,
                        inefficiency_id: Optional[int] = None) -> list[dict]:
        return self.db.quality_rows(month, inefficiency_id)

    def monthly_report(self, month: Optional[str] = None) -> str:
        """Markdown table of the monthly funnel (playbook 9.2 format)."""
        rows = self.monthly_quality(month)
        if not rows:
            month = month or "current"
            return f"No signal-quality rows for {month}."
        lines = [
            "| month | ineff | fired | confirmed | trades | wins | gross_pnl |",
            "|-------|-------|-------|-----------|--------|------|-----------|",
        ]
        for r in rows:
            lines.append(
                f"| {r['month']} | #{r['inefficiency_id']} "
                f"| {r['signals_fired']} | {r['signals_confirmed']} "
                f"| {r['trades_taken']} | {r['wins']} "
                f"| {r['gross_pnl']:.2f} |")
        return "\n".join(lines)
