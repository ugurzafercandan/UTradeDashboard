"""Execution package for NewSetup (playbook sections 7.2 / 7.3).

Brokers (paper + MT5), order management and pre-trade risk enforcement
(playbook Appendix D circuit breakers and exposure caps).
"""

from __future__ import annotations

from .mt5_bridge import MT5Bridge, MT5NotAvailable
from .order_manager import OrderManager
from .paper_broker import PaperBroker
from .risk_enforcer import RiskEnforcer

__all__ = [
    "MT5Bridge",
    "MT5NotAvailable",
    "OrderManager",
    "PaperBroker",
    "RiskEnforcer",
]
