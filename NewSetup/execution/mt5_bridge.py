"""MT5 live/demo bridge for NewSetup (playbook section 7.3).

Thin wrapper around the MetaTrader5 python package. The module imports
cleanly on machines without MT5 installed: every MetaTrader5 access is
guarded, and the bridge simply reports ``available=False`` until a real
terminal connection is established.
"""

from __future__ import annotations

from typing import Any, Optional

from newsetup.models import AccountState


class MT5NotAvailable(RuntimeError):
    """Raised when an operation needs MT5 but the terminal is unavailable."""


class MT5WrongAccount(RuntimeError):
    """Raised on order submission when the terminal is logged into an
    unexpected account (single shared API socket, playbook 7.3 safety)."""


class MT5Bridge:
    """Gateway to a running MetaTrader 5 terminal (Pepperstone Razor)."""

    def __init__(self, auto_connect: bool = True):
        self.mt5: Any = None           # MetaTrader5 module once connected
        self.available: bool = False
        self.connected_login: Optional[int] = None
        if auto_connect:
            self.connect()

    # ------------------------------------------------------------------
    @staticmethod
    def _mt5_settings() -> dict:
        """MT5 connection settings from config/settings.yaml (mt5 section).

        Tolerates a missing section so the module keeps importing and the
        tests keep passing on machines without the config.
        """
        try:
            from newsetup.config import load_settings
            cfg = (load_settings() or {}).get("mt5") or {}
            return cfg if isinstance(cfg, dict) else {}
        except Exception:                      # noqa: BLE001
            return {}

    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Try to import MetaTrader5 and initialize the terminal.

        Never raises: on a machine without MT5 (or without the python
        package) the bridge simply stays unavailable. When settings.yaml
        defines an ``mt5`` section the bridge targets that specific
        terminal (path/portable) and, after connecting, verifies the
        account login matches the configured one. This guard exists
        because only ONE terminal per machine can own the Python API
        socket: a mismatch here means we are attached to the wrong
        terminal and must refuse to trade on it.
        """
        self.mt5 = None
        self.available = False
        self.connected_login = None
        try:
            import MetaTrader5 as mt5  # type: ignore[import-not-found]
        except Exception:  # ImportError or DLL issues on non-Windows
            return False
        self.mt5 = mt5

        cfg = self._mt5_settings()
        kwargs: dict = {}
        if cfg.get("terminal_path"):
            kwargs["path"] = cfg["terminal_path"]
        if cfg.get("portable"):
            kwargs["portable"] = True
        expected_login = cfg.get("login")
        if expected_login:
            kwargs["login"] = int(expected_login)
            server = cfg.get("server")
            if server:
                kwargs["server"] = str(server)
            password = ""
            env_name = cfg.get("password_env") or "PEPPERSTONE_MT5_PASSWORD"
            import os
            password = os.environ.get(env_name, "")
            if password:
                kwargs["password"] = password
        if cfg.get("init_timeout_s"):
            kwargs["timeout"] = int(float(cfg["init_timeout_s"]) * 1000)

        initialize = getattr(mt5, "initialize", None)
        ok = False
        try:
            ok = bool(initialize(**kwargs)) if callable(initialize) else False
        except Exception:                        # noqa: BLE001
            ok = False
        if ok and expected_login:
            # account guard: refuse the connection if the terminal we
            # reached is logged into a different account than configured.
            info = getattr(mt5, "account_info", lambda: None)()
            actual = getattr(info, "login", None)
            if actual != int(expected_login):
                try:
                    mt5.shutdown()
                except Exception:                  # noqa: BLE001
                    pass
                self.mt5 = None
                return False
        self.available = ok
        if ok and hasattr(mt5, "account_info"):
            info = getattr(mt5, "account_info", lambda: None)()
            self.connected_login = getattr(info, "login", None)
        return self.available

    def _verify_account(self) -> None:
        """Raise MT5WrongAccount if the live account differs from config.

        Re-checked at order time because terminal ownership of the API
        socket can change while the process is running.
        """
        cfg = self._mt5_settings()
        expected = cfg.get("login")
        if not expected:
            return
        info = self.mt5.account_info() if hasattr(self.mt5, "account_info") else None
        actual = getattr(info, "login", None)
        if actual != int(expected):
            raise MT5WrongAccount(
                f"MT5 account guard: expected login {expected}, terminal "
                f"reports {actual}. Refusing to trade on the wrong account."
            )


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
    def symbol_available(self, symbol: str) -> bool:
        """True when the broker lists `symbol` (name is case/space-tolerant)."""
        self._require()
        if getattr(self, "_symbol_names", None) is None:
            self._symbol_names = {
                " ".join(str(getattr(s, "name", "")).upper().split())
                for s in (self.mt5.symbols_get() or [])
            }
        wanted = " ".join(str(symbol).upper().split())
        return wanted in self._symbol_names

    def get_bars(self, symbol: str, timeframe: str = "D1",
                 count: int = 500) -> list:
        """Fetch the last `count` bars for `symbol` as rate tuples.

        Returns the raw MetaTrader5 rate rows (time/open/high/low/close/...);
        empty list on any failure. Callers convert to PriceBar via
        data.bar_cache.BarCache, which shares the timestamp handling.
        """
        self._require()
        mt5 = self.mt5
        try:
            mt5.symbol_select(symbol, True)
        except Exception:                             # noqa: BLE001
            pass
        tf = getattr(mt5, f"TIMEFRAME_{timeframe.upper()}", mt5.TIMEFRAME_D1)
        try:
            bars = mt5.copy_rates_from_pos(symbol, tf, 0, int(count))
        except Exception:                             # noqa: BLE001
            return []
        return list(bars) if bars is not None else []

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
        self._verify_account()
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
        self._verify_account()
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
