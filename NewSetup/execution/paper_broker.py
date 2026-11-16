"""Paper trading broker for NewSetup (playbook section 7.2).

Simulates Pepperstone Razor fills with a spread cost, SL/TP resolution
on each bar, and a simple cash account. PnL convention matches Layer 3
sizing: 1 lot == 10 units of quote currency per price unit of movement
(``pnl = (exit - entry) * lot * 10`` for a BUY, inverted for a SELL).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from newsetup.config import load_settings
from newsetup.models import AccountState, PriceBar, SizedSignal, Trade, utcnow


def _as_utc(dt: datetime) -> datetime:
    """Treat naive timestamps as UTC so comparisons never explode."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class PaperBroker:
    """In-memory paper broker with spread-adjusted fills."""

    def __init__(
        self,
        starting_balance: Optional[float] = None,
        spread_pct: Optional[float] = None,
        settings: Optional[dict] = None,
    ):
        """Defaults come from ``settings['paper_trading']`` when provided,
        otherwise the playbook paper defaults (10000 / 0.02%)."""
        settings = settings or load_settings()
        pt = settings.get("paper_trading", {}) if settings else {}
        self.starting_balance = float(
            starting_balance if starting_balance is not None
            else pt.get("starting_balance", 10000.0)
        )
        self.spread_pct = float(
            spread_pct if spread_pct is not None
            else pt.get("spread_pct", 0.02)
        )
        self.balance: float = self.starting_balance
        self._open: list[Trade] = []
        self._closed: list[Trade] = []
        self._last_prices: dict[str, float] = {}
        # Durable paper-book state (UGT-15 Phase 4): the broker is otherwise
        # in-memory, so a fresh process would restart the 4-week book from
        # the starting balance every day. Restore from disk when present so
        # daily cycles accumulate one continuous paper account.
        self._state_path: Optional[str] = None
        state_file = (pt or {}).get("state_file") or (
            (settings or {}).get("paper_trading", {}) or {}).get("state_file")
        if state_file:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self._state_path = os.path.join(root, str(state_file))
        self._load_state()

    # ------------------------------------------------------------------
    def _fill_price(self, entry: float, direction: str) -> float:
        """BUY fills above mid (ask), SELL below mid (bid) — half-spread."""
        if direction == "BUY":
            return entry * (1.0 + self.spread_pct / 100.0)
        return entry * (1.0 - self.spread_pct / 100.0)

    @staticmethod
    def _pnl(trade: Trade, exit_price: float) -> float:
        if trade.direction == "BUY":
            return (exit_price - trade.entry_price) * trade.lot_size * 10.0
        return (trade.entry_price - exit_price) * trade.lot_size * 10.0

    # ------------------------------------------------------------------
    @staticmethod
    def _trade_to_dict(t: Trade) -> dict:
        return {
            "instrument": t.instrument, "direction": t.direction,
            "lot_size": t.lot_size, "entry_price": t.entry_price,
            "exit_price": t.exit_price, "stop_loss": t.stop_loss,
            "take_profit": t.take_profit,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            "pnl": t.pnl, "exit_reason": t.exit_reason,
            "inefficiency_id": t.inefficiency_id, "sector": t.sector,
        }

    @staticmethod
    def _trade_from_dict(d: dict) -> Trade:
        return Trade(
            instrument=d["instrument"], direction=d["direction"],
            lot_size=float(d["lot_size"]), entry_price=float(d["entry_price"]),
            exit_price=float(d.get("exit_price", 0.0)),
            stop_loss=float(d["stop_loss"]), take_profit=float(d["take_profit"]),
            opened_at=datetime.fromisoformat(d["opened_at"]) if d.get("opened_at") else utcnow(),
            closed_at=datetime.fromisoformat(d["closed_at"]) if d.get("closed_at") else None,
            pnl=float(d.get("pnl", 0.0)), exit_reason=str(d.get("exit_reason", "")),
            inefficiency_id=int(d.get("inefficiency_id", 0)),
            sector=str(d.get("sector", "")),
        )

    def _load_state(self) -> None:
        """Restore balance/open/closed/last prices from ``state_file``.

        Tolerant of a missing or corrupt file: warn and start fresh (the
        paper pipeline must never crash on its own state file).
        """
        if not self._state_path or not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.balance = float(data["balance"])
            self.starting_balance = float(data.get("starting_balance", self.starting_balance))
            self._open = [self._trade_from_dict(d) for d in data.get("open", [])]
            self._closed = [self._trade_from_dict(d) for d in data.get("closed", [])]
            self._last_prices = {str(k): float(v) for k, v in data.get("last_prices", {}).items()}
        except Exception:                         # noqa: BLE001
            import logging
            logging.getLogger("newsetup.paper_broker").warning(
                "paper state file %s unreadable; starting a fresh book", self._state_path)

    def save_state(self) -> Optional[str]:
        """Atomically persist the paper book for the next daily cycle."""
        if not self._state_path:
            return None
        data = {
            "version": 1,
            "starting_balance": self.starting_balance,
            "balance": self.balance,
            "open": [self._trade_to_dict(t) for t in self._open],
            "closed": [self._trade_to_dict(t) for t in self._closed],
            "last_prices": dict(self._last_prices),
        }
        os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
        tmp = self._state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, self._state_path)
        return self._state_path

    # ------------------------------------------------------------------
    def _close(self, trade: Trade, exit_price: float, reason: str,
               closed_at: datetime) -> Trade:
        trade.exit_price = exit_price
        trade.pnl = self._pnl(trade, exit_price)
        trade.exit_reason = reason
        trade.closed_at = closed_at
        self._open.remove(trade)
        self._closed.append(trade)
        self.balance += trade.pnl
        return trade

    # ------------------------------------------------------------------
    def submit(self, sized: SizedSignal) -> Trade:
        """Open a paper position at the spread-adjusted fill price."""
        raw = sized.signal.raw
        fill = self._fill_price(sized.entry_price, raw.direction)
        trade = Trade(
            instrument=raw.instrument,
            direction=raw.direction,
            lot_size=sized.lot_size,
            entry_price=fill,
            exit_price=0.0,
            stop_loss=sized.stop_loss,
            take_profit=sized.take_profit,
            opened_at=utcnow(),
            inefficiency_id=raw.inefficiency_id,
            sector=sized.sector,
        )
        self._open.append(trade)
        self._last_prices.setdefault(raw.instrument, fill)
        return trade

    # ------------------------------------------------------------------
    def on_bar(self, symbol: str, bar: PriceBar) -> list[Trade]:
        """Resolve SL/TP for open trades on ``symbol`` against this bar.

        Returns the trades closed by this bar (possibly empty).
        """
        self._last_prices[symbol] = bar.close
        closed: list[Trade] = []
        for trade in list(self._open):
            if trade.instrument != symbol:
                continue
            hit = None
            if trade.direction == "BUY":
                if bar.low <= trade.stop_loss:
                    hit = (trade.stop_loss, "sl")
                elif bar.high >= trade.take_profit:
                    hit = (trade.take_profit, "tp")
            else:  # SELL
                if bar.high >= trade.stop_loss:
                    hit = (trade.stop_loss, "sl")
                elif bar.low <= trade.take_profit:
                    hit = (trade.take_profit, "tp")
            if hit is not None:
                closed.append(
                    self._close(trade, hit[0], hit[1], _as_utc(bar.ts))
                )
        return closed

    # ------------------------------------------------------------------
    def close_all(self, price_map: Optional[dict] = None) -> list[Trade]:
        """Force-close every open trade at the given prices (or last known).

        ``price_map`` maps instrument -> price. Instruments with no known
        price are closed flat at their entry fill (pnl 0).
        """
        price_map = price_map or {}
        closed: list[Trade] = []
        for trade in list(self._open):
            price = price_map.get(trade.instrument)
            if price is None:
                price = self._last_prices.get(trade.instrument)
            if price is None:
                price = trade.entry_price
            closed.append(self._close(trade, float(price), "manual", utcnow()))
        return closed

    # ------------------------------------------------------------------
    def _open_pnl(self) -> float:
        total = 0.0
        for trade in self._open:
            price = self._last_prices.get(trade.instrument, trade.entry_price)
            total += self._pnl(trade, price)
        return total

    @property
    def open_trades(self) -> list[Trade]:
        return list(self._open)

    @property
    def closed_trades(self) -> list[Trade]:
        return list(self._closed)

    @property
    def account_state(self) -> AccountState:
        """Balance/equity snapshot; paper account uses no margin."""
        equity = self.balance + self._open_pnl()
        return AccountState(
            balance=round(self.balance, 2),
            equity=round(equity, 2),
            margin_used=0.0,
            open_positions=len(self._open),
        )

    # ------------------------------------------------------------------
    def day_pnl(self) -> float:
        """Closed pnl since the latest midnight seen in closed trades,
        plus current open pnl (playbook 7.2 daily P&L tracking)."""
        cutoffs = [_as_utc(t.closed_at) for t in self._closed if t.closed_at]
        if cutoffs:
            ref = max(cutoffs)
            cutoff = ref.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            ref = utcnow()
            cutoff = ref.replace(hour=0, minute=0, second=0, microsecond=0)
        total = sum(
            t.pnl for t in self._closed
            if t.closed_at and _as_utc(t.closed_at) >= cutoff
        )
        return total + self._open_pnl()

    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Reset the account to its starting state (for tests)."""
        self.balance = self.starting_balance
        self._open.clear()
        self._closed.clear()
        self._last_prices.clear()
