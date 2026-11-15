"""Pre-trade risk enforcement for NewSetup (playbook 7.2 and Appendix D).

Enforces, in order: margin cap, max open positions, per-sector exposure
cap, portfolio heat cap, drawdown circuit breakers (pause / week halt /
full halt) and the daily loss halt. All thresholds come from
``settings['risk']``.
"""

from __future__ import annotations

from typing import Optional

from newsetup.config import load_settings
from newsetup.models import AccountState, SizedSignal, Trade


class RiskEnforcer:
    """Gatekeeper applied before every order placement (Appendix D)."""

    def __init__(self, settings: Optional[dict] = None):
        self.settings = settings or load_settings()
        risk = self.settings["risk"]
        self.max_margin_pct: float = risk["max_margin_used_pct"]
        self.max_open_positions: int = risk["max_open_positions"]
        self.max_sector_pct: float = risk["max_sector_exposure_pct"]
        self.max_heat_pct: float = risk["max_portfolio_heat_pct"]
        self.max_daily_loss_pct: float = risk["max_daily_loss_pct"]
        breakers = risk.get("drawdown_breakers", {})
        self.pause_pct: float = breakers.get("pause_pct", 5.0)
        self.halt_week_pct: float = breakers.get("halt_week_pct", 8.0)
        self.full_halt_pct: float = breakers.get("full_halt_pct", 12.0)
        # mutable state
        self._drawdown_pct: float = 0.0
        self._day_pnl: float = 0.0
        self._day_equity: float = 0.0

    # ------------------------------------------------------------------
    def update_drawdown(self, equity: float, peak_equity: float) -> float:
        """Record the current drawdown percentage from equity peaks."""
        if peak_equity > 0:
            self._drawdown_pct = max(0.0, (peak_equity - equity) / peak_equity * 100.0)
        else:
            self._drawdown_pct = 0.0
        return self._drawdown_pct

    def current_breaker(self) -> str:
        """Active drawdown circuit breaker (Appendix D thresholds)."""
        if self._drawdown_pct >= self.full_halt_pct:
            return "full_halt"
        if self._drawdown_pct >= self.halt_week_pct:
            return "week_halt"
        if self._drawdown_pct >= self.pause_pct:
            return "pause"
        return "none"

    def set_day_pnl(self, pnl: float, equity: float) -> None:
        """Feed today's realized+open P&L and the reference equity."""
        self._day_pnl = pnl
        self._day_equity = equity

    # ------------------------------------------------------------------
    def check(
        self,
        sized: SizedSignal,
        account: AccountState,
        open_trades: list,
    ) -> tuple[bool, str]:
        """Return (allowed, reason) for placing ``sized`` now.

        Reasons: 'ok' | 'margin' | 'max_positions' | 'sector_exposure'
        | 'heat' | 'dd_pause' | 'dd_week_halt' | 'dd_full_halt'
        | 'daily_loss' (playbook 7.2 risk table, Appendix D breakers).
        """
        open_trades = open_trades or []
        equity = account.equity

        # (a) margin cap
        if account.margin_used_pct > self.max_margin_pct:
            return False, "margin"

        # (b) max open positions
        if len(open_trades) >= self.max_open_positions:
            return False, "max_positions"

        if equity > 0:
            # (c) sector exposure (same correlation sector as the signal)
            sector_exposure = sum(
                t.entry_price * t.lot_size
                for t in open_trades
                if t.sector == sized.sector
            )
            sector_exposure += sized.entry_price * sized.lot_size
            if sector_exposure / equity * 100.0 > self.max_sector_pct:
                return False, "sector_exposure"

            # (d) portfolio heat: total open risk incl. the new trade
            heat = sum(
                abs(t.entry_price - t.stop_loss) * t.lot_size
                for t in open_trades
            )
            heat += abs(sized.entry_price - sized.stop_loss) * sized.lot_size
            if heat / equity * 100.0 > self.max_heat_pct:
                return False, "heat"

        # (e) drawdown circuit breakers (highest severity first)
        breaker = self.current_breaker()
        if breaker == "full_halt":
            return False, "dd_full_halt"
        if breaker == "week_halt":
            return False, "dd_week_halt"
        if breaker == "pause":
            return False, "dd_pause"

        # (f) daily loss halt
        if (
            self._day_equity > 0
            and self._day_pnl <= -self._day_equity * self.max_daily_loss_pct / 100.0
        ):
            return False, "daily_loss"

        return True, "ok"

    # ------------------------------------------------------------------
    def allowed(
        self,
        sized: SizedSignal,
        account: AccountState,
        open_trades: list,
    ) -> bool:
        """Boolean convenience wrapper around check()."""
        return self.check(sized, account, open_trades)[0]
