"""Shared domain models for NewSetup.

Everything is a plain dataclass so the layers (scanner, confirmation,
portfolio, execution, backtest) share one vocabulary. Playbook reference:
sections 4.1-4.5 (signal engine) and the Python -> MQL5 signal format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class Trigger:
    """A single layer-1 trigger condition for one inefficiency."""
    id: int
    inefficiency_id: int
    trigger_type: str          # EVENT | PRICE | SENTIMENT | DATA
    condition: str
    threshold: str = ""
    data_source: str = ""
    scan_freq: str = ""


@dataclass
class Inefficiency:
    """One of the 40 supply chain inefficiencies with its tradeable instruments."""
    id: int
    name: str
    category: str              # ENERGY_MINING | FOOD_SHIPPING | TECH_INFRA
    concentration: str
    instruments: dict = field(default_factory=dict)
    trade_type: str = ""
    triggers: list = field(default_factory=list)

    def tradeable_symbols(self) -> list[str]:
        """All Pepperstone-available symbols for this inefficiency."""
        out: list[str] = []
        for kind in ("direct_cfd", "forex", "etf", "equity"):
            for sym in self.instruments.get(kind, []):
                if sym not in out:
                    out.append(sym)
        return out

    def primary_symbol(self) -> Optional[str]:
        syms = self.tradeable_symbols()
        return syms[0] if syms else None


@dataclass
class Event:
    """A detected news/geopolitical event (GDELT or RSS sourced)."""
    headline: str
    themes: list = field(default_factory=list)      # e.g. ["China export ban", "mining"]
    goldstein_score: float = 0.0                      # -10..10 conflict/cooperation scale
    score: float = 0.0                               # scanner relevance score 0..1
    source: str = "gdelt"
    ts: datetime = field(default_factory=utcnow)


@dataclass
class PriceBar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class RawSignal:
    """Layer-1 output: an inefficiency trigger fired for an instrument."""
    inefficiency_id: int
    inefficiency_name: str
    instrument: str
    direction: str            # BUY | SELL
    trigger_type: str         # EVENT | PRICE | SENTIMENT | DATA
    trigger_description: str
    confidence: float         # 0..1
    ts: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "inefficiency_id": self.inefficiency_id,
            "inefficiency_name": self.inefficiency_name,
            "instrument": self.instrument,
            "direction": self.direction,
            "trigger_type": self.trigger_type,
            "trigger": self.trigger_description,
            "confidence": round(self.confidence, 3),
            "timestamp": iso(self.ts),
        }


@dataclass
class ConfirmedSignal:
    """Layer-2 output: a raw signal that passed technical/sentiment checks."""
    raw: RawSignal
    confirmed: bool
    score: float = 0.0
    reasons: list = field(default_factory=list)   # human-readable check results


@dataclass
class SizedSignal:
    """Layer-3 output: risk-sized, executable trade instruction.

    Field names mirror the Python -> MQL5 active_signals.json format
    (playbook section 4.4) so the same object feeds paper, backtest and
    live execution paths.
    """
    signal: ConfirmedSignal
    lot_size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    sector: str
    confidence: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = iso(self.signal.raw.ts)

    def to_dict(self) -> dict:
        r = self.signal.raw
        return {
            "inefficiency_id": r.inefficiency_id,
            "instrument": r.instrument,
            "direction": r.direction,
            "lot_size": round(self.lot_size, 2),
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confidence": round(self.confidence, 3),
            "sector": self.sector,
            "timestamp": self.timestamp,
            "trigger": r.trigger_description,
        }


@dataclass
class AccountState:
    balance: float
    equity: float
    margin_used: float = 0.0
    open_positions: int = 0
    currency: str = "USD"

    @property
    def margin_used_pct(self) -> float:
        return (self.margin_used / self.equity * 100.0) if self.equity else 0.0


@dataclass
class Trade:
    """A closed (or open) trade produced by a broker/paper broker."""
    instrument: str
    direction: str
    lot_size: float
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    opened_at: datetime
    closed_at: Optional[datetime] = None
    pnl: float = 0.0
    exit_reason: str = ""
    inefficiency_id: int = 0
    sector: str = ""
