"""Shared helpers for NewSetup execution tests: dummy signal builders."""

from __future__ import annotations

from newsetup.models import (ConfirmedSignal, RawSignal, SizedSignal, Trade,
                             utcnow)


def make_sized(
    direction: str = "BUY",
    entry: float = 100.0,
    sl: float = 99.0,
    tp: float = 102.0,
    lot: float = 1.0,
    sector: str = "ENERGY_MINING:Test Inefficiency",
    instrument: str = "XAUUSD",
) -> SizedSignal:
    """Build a SizedSignal (ConfirmedSignal wrapping a RawSignal) inline."""
    raw = RawSignal(
        inefficiency_id=1,
        inefficiency_name="Test Inefficiency",
        instrument=instrument,
        direction=direction,
        trigger_type="PRICE",
        trigger_description="test trigger",
        confidence=0.8,
    )
    confirmed = ConfirmedSignal(raw=raw, confirmed=True, score=0.8,
                                reasons=["test"])
    return SizedSignal(
        signal=confirmed,
        lot_size=lot,
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        sector=sector,
        confidence=0.8,
    )


def make_trade(
    entry: float = 100.0,
    stop: float = 99.0,
    lot: float = 1.0,
    sector: str = "ENERGY_MINING:Test Inefficiency",
    direction: str = "BUY",
    instrument: str = "XAUUSD",
) -> Trade:
    """Build an open Trade with dummy values."""
    return Trade(
        instrument=instrument,
        direction=direction,
        lot_size=lot,
        entry_price=entry,
        exit_price=0.0,
        stop_loss=stop,
        take_profit=entry + (entry - stop) * 2.0,
        opened_at=utcnow(),
        sector=sector,
    )
