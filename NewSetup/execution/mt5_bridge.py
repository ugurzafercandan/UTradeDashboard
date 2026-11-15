"""MT5 live/demo bridge for NewSetup (playbook section 7.3).

Thin wrapper around the MetaTrader5 python package. The module imports
cleanly on machines without MT5 installed: every MetaTrader5 access is
guarded, and the bridge simply reports ``available=False`` until a real
terminal connection is established.
"""

from __future__ import annotations

from typing import Optional

from newsetup.models import AccountState


class MT5NotAvailable(RuntimeError):
    """Raised when an operation needs MT5 but the terminal is unavailable."""


class MT5Bridge:
    """Gateway to a running MetaTrader 5 terminal (Pepperstone Razor)."""

    def __init__(self, auto_connect: bool = True):
        self.mt5 = None                # MetaTrader5 module once connected
        self.available: bool = False
        if auto_connect:
            self.connect()

    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Try to import MetaTrader5 and initialize the terminal.

        Never raises: on a machine without MT5 (or without the python
        package) the bridge simply stays unavailable.
        """
        self.mt5 = None
        self.available = False
        try:
            import MetaTrader5 as mt5  # type: ignore[import-not-found]
        except Exception:  # ImportError or DLL issues on non-Windows
            return False
        self.mt5 = mt5
        initialize = getattr(mt5, "initialize", None)
        ok = False
        try:
            ok = bool(initialize()) if callable(initialize) else False
        except Exception:
            ok = False
        self.available = ok
        return self.available

    def disconnect(self) -> None:
        """Shut down the MT5 terminal connection if it was open."""
        if self.mt5 is not None and hasattr(self.mt5, "shutdown"):
            try:
                self.mt5.shutdown()
            except Exception:
                pass
        self.mt5 = None
        self.available = False

    def _require(self) -> None:
        if not self.available or self.mt5 is None:
            raise MT5NotAvailable(
                "MetaTrader5 terminal is not available (module missing, "
                "not installed, or terminal not running)"
            )

    # ------------------------------------------------------------------
    def get_account_info(self) -> AccountState:
        """Snapshot the MT5 account as an AccountState (playbook 7.3)."""
        self._require()
        mt5 = self.mt5
        info = mt5.account_info() if hasattr(mt5, "account_info") else None
        if info is None:
            raise MT5NotAvailable("mt5.account_info() returned no data")
        return AccountState(
            balance=float(getattr(info, "balance", 0.0)),
            equity=float(getattr(info, "equity", 0.0)),
            margin_used=float(getattr(info, "margin", 0.0)),
            open_positions=int(getattr(info, "positions", 0) or 0),
            currency=str(getattr(info, "currency", "USD") or "USD"),
        )

    # ------------------------------------------------------------------
    def market_order(
        self,
        symbol: str,
        direction: str,
        lot: float,
        stop_loss: float,
        take_profit: float,
    ) -> dict:
        """Send a market order with attached SL/TP; return the result dict.

        ``direction`` is ``"BUY"`` or ``"SELL"``. The result mirrors the
        MQL5 trade server response (retcode/order/volume/price/...).
        """
        self._require()
        mt5 = self.mt5

        buy_type = getattr(mt5, "ORDER_TYPE_BUY", 0)
        sell_type = getattr(mt5, "ORDER_TYPE_SELL", 1)
        order_type = buy_type if str(direction).upper() == "BUY" else sell_type

        request = {
            "action": getattr(mt5, "TRADE_ACTION_DEAL", 1),
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": 0.0,  # market order: server fills at current price
            "sl": float(stop_loss),
            "tp": float(take_profit),
            "deviation": 10,
            "magic": 20261115,
            "comment": "NewSetup playbook 7.3 market order",
            "type_time": getattr(mt5, "ORDER_TIME_GTC", 0),
            "type_filling": getattr(mt5, "ORDER_FILLING_IOC", 0),
        }

        order_send = getattr(mt5, "order_send", None)
        result = order_send(request) if callable(order_send) else None
        if result is None:
            return {"retcode": -1, "comment": "order_send returned no result",
                    "request": request}

        out: dict = {"request": request}
        for attr in ("retcode", "deal", "order", "volume", "price",
                     "bid", "ask", "comment", "retcode_external"):
            out[attr] = getattr(result, attr, None)
        return out

    # ------------------------------------------------------------------
    def close_position(self, ticket: int) -> Optional[dict]:
        """Close an open position by ticket (optional helper)."""
        self._require()
        mt5 = self.mt5

        positions_get = getattr(mt5, "positions_get", None)
        positions = positions_get(ticket=ticket) if callable(positions_get) else None
        if not positions:
            return None
        pos = positions[0]

        is_buy = bool(getattr(pos, "type", 0) == getattr(mt5, "POSITION_TYPE_BUY", 0))
        order_type = getattr(mt5, "ORDER_TYPE_SELL", 1) if is_buy else getattr(mt5, "ORDER_TYPE_BUY", 0)
        tick_get = getattr(mt5, "symbol_info_tick", None)
        tick = tick_get(pos.symbol) if callable(tick_get) else None
        price = getattr(tick, "bid", None) if is_buy else getattr(tick, "ask", None)

        request = {
            "action": getattr(mt5, "TRADE_ACTION_DEAL", 1),
            "position": int(ticket),
            "symbol": pos.symbol,
            "volume": float(pos.volume),
            "type": order_type,
            "price": float(price or 0.0),
            "deviation": 10,
            "magic": 20261115,
            "comment": "NewSetup close_position",
            "type_time": getattr(mt5, "ORDER_TIME_GTC", 0),
            "type_filling": getattr(mt5, "ORDER_FILLING_IOC", 0),
        }
        order_send = getattr(mt5, "order_send", None)
        result = order_send(request) if callable(order_send) else None
        if result is None:
            return {"retcode": -1, "comment": "order_send returned no result",
                    "request": request}
        return {"retcode": getattr(result, "retcode", None),
                "order": getattr(result, "order", None),
                "request": request}
