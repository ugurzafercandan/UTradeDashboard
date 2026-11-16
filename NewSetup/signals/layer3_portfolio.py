"""Layer 3: Portfolio Manager (playbook 4.3).

Sizes confirmed signals using the fixed-fractional method (Appendix D
Formula 1), sets ATR-based stops and R-multiple targets, and enforces
portfolio-level caps (max positions, one position per inefficiency,
portfolio heat, sector exposure).
"""

from __future__ import annotations

from newsetup.config import load_settings, sector_for
from newsetup.indicators import atr
from newsetup.models import (AccountState, ConfirmedSignal, SizedSignal,
                             Trade)


class Layer3PortfolioManager:
    def __init__(self, settings: dict | None = None):
        self.settings = settings or load_settings()
        risk = self.settings["risk"]
        sizing = self.settings["sizing"]
        self.risk_per_trade_pct = risk["risk_per_trade_pct"]
        self.max_open = risk["max_open_positions"]
        self.max_sector_pct = risk["max_sector_exposure_pct"]
        self.max_heat_pct = risk["max_portfolio_heat_pct"]
        self.atr_mult_sl = sizing["atr_mult_sl"]
        self.reward_risk = sizing["reward_risk"]
        self.min_lot = sizing["min_lot"]
        self.lot_step = sizing["lot_step"]
        self.max_per_inefficiency = self.settings["layer3"]["max_positions_per_inefficiency"]

    # ------------------------------------------------------------------
    def size_positions(
        self,
        confirmed: list[ConfirmedSignal],
        account: AccountState,
        open_trades: list[Trade] | None = None,
        price_provider=None,
    ) -> list[SizedSignal]:
        """Convert confirmed signals into sized, executable signals.

        Drops signals that would violate portfolio caps. `open_trades` is the
        currently open book (used for cap checks).
        """
        open_trades = open_trades or []
        if account.equity <= 0:
            return []
        sized: list[SizedSignal] = []
        open_by_ineff = {t.inefficiency_id for t in open_trades}
        sector_exposure: dict[str, float] = {}
        for t in open_trades:
            sector_exposure[t.sector] = sector_exposure.get(t.sector, 0.0) + t.entry_price * t.lot_size
        current_heat = sum(abs(t.entry_price - t.stop_loss) * t.lot_size for t in open_trades)

        for cs in confirmed:
            if not cs.confirmed:
                continue
            if len(open_trades) + len(sized) >= self.max_open:
                break
            raw = cs.raw
            if raw.inefficiency_id in open_by_ineff:
                continue  # one position per inefficiency

            # Entry prices come from the execution stream (intraday spot
            # when present - UGT-17/19 item 2); ATR/stop sizing uses the
            # EXECUTION bars so exits resolve on the intraday stream when
            # one is present (falls back to the daily context series).
            spot = (getattr(price_provider, "get_spot", None)
                    and price_provider.get_spot(raw.instrument)) or None
            exec_bars = None
            if price_provider is not None and hasattr(price_provider, "get_execution_bars"):
                exec_bars = price_provider.get_execution_bars(raw.instrument, count=30)
            bars = exec_bars or (price_provider.get_series(raw.instrument, lookback_days=30) if price_provider else [])
            if spot is not None:
                entry = spot.close
            elif not bars or not bars[-1]:
                continue
            else:
                entry = bars[-1].close
            a = atr(bars, 14) or (entry * 0.02)
            stop_dist = a * self.atr_mult_sl
            if stop_dist <= 0:
                continue

            if raw.direction == "BUY":
                sl, tp = entry - stop_dist, entry + stop_dist * self.reward_risk
            else:
                sl, tp = entry + stop_dist, entry - stop_dist * self.reward_risk

            # Fixed fractional: risk amount / stop distance -> lot size.
            # 1 lot moves 1 price unit per pip-equivalent; for CFD/FX proxies
            # we normalize stop distance as a fraction of price.
            risk_amount = account.equity * self.risk_per_trade_pct / 100.0
            lot = round(max(self.min_lot,
                           risk_amount / (stop_dist * 10.0)), 2)
            lot = max(self.min_lot, lot - (lot % self.lot_step))

            sector = sector_for(_ineff(cs))
            exposure = sector_exposure.get(sector, 0.0) + entry * lot
            if exposure / account.equity * 100.0 > self.max_sector_pct:
                continue
            new_heat = (current_heat + stop_dist * lot)
            if account.equity and new_heat / account.equity * 100.0 > self.max_heat_pct:
                continue

            sector_exposure[sector] = exposure
            current_heat = new_heat
            sized.append(
                SizedSignal(
                    signal=cs,
                    lot_size=lot,
                    entry_price=round(entry, 5),
                    stop_loss=round(sl, 5),
                    take_profit=round(tp, 5),
                    sector=sector,
                    confidence=cs.score,
                )
            )
            open_by_ineff.add(raw.inefficiency_id)
        return sized


def _ineff(cs: ConfirmedSignal):
    from newsetup.models import Inefficiency
    return Inefficiency(id=cs.raw.inefficiency_id, name=cs.raw.inefficiency_name,
                        category="", concentration="")
