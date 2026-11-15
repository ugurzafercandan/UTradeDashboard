"""Strategy degradation detection (playbook 9.4).

Rolling checks over the last N days (default 30) of closed trades, per
inefficiency:

- win rate below the floor (default 40%, i.e. clearly under the 48%
  acceptance bar), and/or
- annualized Sharpe of daily PnL returns below the floor (default 0.0),

each escalate the automated-response ladder ONE step per evaluation:

    ok -> reduce_size -> paused -> retired

reduce_size applies a lot multiplier (default 0.5x) that layer-3 sizing
must honor; paused and retired block new entries for the inefficiency.
State persists in the degradation_state table, so responses survive
restarts. Evaluations with fewer than min_trades closed trades in the
window are explicitly ignored (insufficient sample) — the detector never
escalates on noise.

Sharpe convention (stated): daily net PnL of closed trades divided by a
baseline equity (paper_trading.starting_balance by default), annualized
with sqrt(252). This is a monitoring statistic, not the acceptance-gate
Sharpe; it is intentionally crude but robust.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from db.store import (DEGRADATION_LEVELS, DEFAULT_LOT_MULTIPLIERS,
                      NewSetupDB)
from newsetup.config import load_settings
from newsetup.models import Trade, utcnow


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class DegradationAction:
    """One escalation decision for one inefficiency."""

    inefficiency_id: int
    from_level: str
    to_level: str
    lot_multiplier: float
    trades_in_window: int
    win_rate_pct: float
    sharpe: float
    reasons: list[str] = field(default_factory=list)

    @property
    def escalated(self) -> bool:
        return DEGRADATION_LEVELS.index(self.to_level) > DEGRADATION_LEVELS.index(self.from_level)


class DegradationDetector:
    """Rolling 30-day health check with an automated response ladder."""

    def __init__(self, db: Optional[NewSetupDB] = None,
                 settings: Optional[dict] = None):
        self.settings = settings or load_settings()
        cfg = self.settings.get("monitoring", {}).get("degradation", {}) or {}
        self.window_days = int(cfg.get("window_days", 30))
        self.min_trades = int(cfg.get("min_trades", 20))
        self.win_rate_floor_pct = float(cfg.get("win_rate_floor_pct", 40.0))
        self.sharpe_floor = float(cfg.get("sharpe_floor", 0.0))
        self.reduce_lot_mult = float(cfg.get("reduce_size_lot_mult", 0.5))
        self.baseline_equity = float(
            self.settings.get("paper_trading", {}).get("starting_balance", 10000.0))
        self.db = db
        # In-memory ladder state, used when no db is attached and kept
        # in sync with it when one is (db is the durable source).
        self._memory_state: dict[int, tuple[str, float]] = {}

    # ------------------------------------------------------------ state
    def _current_level(self, inefficiency_id: int) -> tuple[str, float]:
        if self.db is not None:
            state = self.db.get_degradation_state(inefficiency_id)
            if state:
                return state["level"], float(state["lot_multiplier"])
        elif inefficiency_id in self._memory_state:
            return self._memory_state[inefficiency_id]
        return "ok", 1.0

    def lot_multiplier(self, inefficiency_id: int) -> float:
        """Multiplier layer-3 sizing must apply for this inefficiency."""
        return self._current_level(inefficiency_id)[1]

    def is_tradable(self, inefficiency_id: int) -> bool:
        """False once the inefficiency is paused or retired."""
        return self._current_level(inefficiency_id)[0] in ("ok", "reduce_size")

    # ----------------------------------------------------------- metrics
    def _window_trades(self, trades: list[Trade], as_of: datetime,
                       inefficiency_id: int) -> list[Trade]:
        cutoff = as_of - timedelta(days=self.window_days)
        out = []
        for t in trades:
            if t.inefficiency_id != inefficiency_id or not t.closed_at:
                continue
            if cutoff <= _as_utc(t.closed_at) <= as_of:  # closed_at checked
                out.append(t)
        return out

    def _win_rate_pct(self, trades: list[Trade]) -> float:
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.pnl > 0.0)
        return 100.0 * wins / len(trades)

    def _sharpe(self, trades: list[Trade]) -> float:
        """Annualized Sharpe of daily closed-PnL returns (see module doc)."""
        if not trades:
            return 0.0
        daily: dict[str, float] = {}
        for t in trades:
            if not t.closed_at:
                continue
            key = _as_utc(t.closed_at).strftime("%Y-%m-%d")
            daily[key] = daily.get(key, 0.0) + float(t.pnl)
        if len(daily) < 2:
            return 0.0
        returns = [p / self.baseline_equity for p in daily.values()]
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / len(returns)
        std = math.sqrt(var)
        if std == 0.0:
            return 0.0
        return mean / std * math.sqrt(252.0)

    # ------------------------------------------------------- main entry
    def evaluate(self, trades: list[Trade],
                 as_of: Optional[datetime] = None) -> list[DegradationAction]:
        """Check every inefficiency present in the window; escalate at most
        one step per call. Returns only inefficiencies that were evaluated
        (>= min_trades closed in the window), whether or not they escalated.
        """
        as_of = _as_utc(as_of) if as_of is not None else utcnow()
        ids = sorted({t.inefficiency_id for t in trades if t.closed_at})
        actions: list[DegradationAction] = []
        for iid in ids:
            window = self._window_trades(trades, as_of, iid)
            if len(window) < self.min_trades:
                continue  # insufficient sample: never act on noise
            win_rate = self._win_rate_pct(window)
            sharpe = self._sharpe(window)
            reasons: list[str] = []
            if win_rate < self.win_rate_floor_pct:
                reasons.append(
                    f"win rate {win_rate:.1f}% < {self.win_rate_floor_pct:.1f}% "
                    f"over {len(window)} trades / {self.window_days}d")
            if sharpe < self.sharpe_floor:
                reasons.append(
                    f"rolling Sharpe {sharpe:.2f} < {self.sharpe_floor:.2f}")
            from_level, _ = self._current_level(iid)
            if not reasons:
                actions.append(DegradationAction(
                    inefficiency_id=iid, from_level=from_level,
                    to_level=from_level,
                    lot_multiplier=DEFAULT_LOT_MULTIPLIERS[from_level],
                    trades_in_window=len(window), win_rate_pct=win_rate,
                    sharpe=sharpe, reasons=["healthy"]))
                continue
            idx = DEGRADATION_LEVELS.index(from_level)
            to_level = DEGRADATION_LEVELS[min(idx + 1, len(DEGRADATION_LEVELS) - 1)]
            mult = (self.reduce_lot_mult if to_level == "reduce_size"
                    else DEFAULT_LOT_MULTIPLIERS[to_level])
            actions.append(DegradationAction(
                inefficiency_id=iid, from_level=from_level, to_level=to_level,
                lot_multiplier=mult, trades_in_window=len(window),
                win_rate_pct=win_rate, sharpe=sharpe, reasons=reasons))
        return actions

    def apply(self, actions: list[DegradationAction],
              as_of: Optional[datetime] = None) -> list[DegradationAction]:
        """Persist escalations (db attached) and return the escalated ones."""
        as_of = _as_utc(as_of) if as_of is not None else utcnow()
        escalated = [a for a in actions if a.escalated]
        for a in escalated:
            self._memory_state[a.inefficiency_id] = (a.to_level,
                                                     a.lot_multiplier)
            if self.db is not None:
                self.db.set_degradation_state(
                    a.inefficiency_id, a.to_level, a.lot_multiplier,
                    "; ".join(a.reasons), as_of)
        return escalated

    def check_and_respond(self, trades: list[Trade],
                          as_of: Optional[datetime] = None
                          ) -> list[DegradationAction]:
        """Convenience: evaluate + apply, returning escalations only."""
        return self.apply(self.evaluate(trades, as_of=as_of), as_of=as_of)
