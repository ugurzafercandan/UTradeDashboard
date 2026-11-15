"""Order manager for NewSetup (playbook sections 7.2 / 7.3).

Routes sized signals to the active broker, applying pre-trade risk checks
when a RiskEnforcer is attached. Rejections are recorded with the reason
so the monitoring layer can report them (playbook 7.4).
"""

from __future__ import annotations

from typing import Optional

from newsetup.models import SizedSignal, Trade


class OrderManager:
    """Places sized signals through a broker (paper or MT5)."""

    def __init__(self, broker):
        """``broker`` is anything with submit / on_bar / account_state
        / open_trades (PaperBroker or an MT5-backed equivalent)."""
        self.broker = broker
        self.rejections: list[tuple] = []  # (SizedSignal, reason)

    # ------------------------------------------------------------------
    def place(
        self,
        sized: SizedSignal,
        risk_enforcer=None,
    ) -> Optional[Trade]:
        """Submit a sized signal, optionally gated by a RiskEnforcer.

        Returns the opened Trade, or None when the enforcer rejected the
        signal (the (signal, reason) pair is recorded in ``rejections``).
        """
        if risk_enforcer is not None:
            allowed, reason = risk_enforcer.check(
                sized, self.broker.account_state, self.broker.open_trades
            )
            if not allowed:
                self.rejections.append((sized, reason))
                return None
        return self.broker.submit(sized)

    # ------------------------------------------------------------------
    def sync(self) -> None:
        """Reconcile local state with the broker (playbook 7.3).

        No-op placeholder: the MT5 path will diff local trades against
        mt5.positions_get() here once live execution is wired up.
        """
        return None
