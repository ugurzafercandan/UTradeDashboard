"""Portfolio manager — orchestrates all 27 ML signals with risk controls.

Manages simultaneous signal execution with:
- Tier-based position sizing (A=100%, B=75%, C=50%)
- Per-currency exposure caps (max 40%)
- Cross-signal deduplication (same pair, different signals)
- Portfolio-level risk limits
- Audit trail logging
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from ml_signal_server.signal_config import (
    ALL_SIGNALS,
    MAX_CURRENCY_EXPOSURE_PCT,
    TIER_SIZING,
    SignalConfig,
)


@dataclass
class PortfolioPosition:
    signal_id: str
    symbol: str
    direction: str
    confidence: float
    tier: str
    tier_weight: float
    notional_eur: float
    magic_number: int
    entry_time: str
    atr: float


@dataclass
class PortfolioState:
    positions: dict[str, PortfolioPosition] = field(default_factory=dict)
    total_equity: float = 10000.0
    max_positions: int = 15
    max_risk_per_trade_pct: float = 2.0
    max_portfolio_risk_pct: float = 15.0
    daily_pnl_pct: float = 0.0
    daily_loss_limit_pct: float = 5.0

    @property
    def position_count(self) -> int:
        return len(self.positions)

    def currency_exposure(self) -> dict[str, float]:
        exposure: dict[str, float] = defaultdict(float)
        for pos in self.positions.values():
            base = pos.symbol[:3]
            quote = pos.symbol[3:]
            exposure[base] += pos.notional_eur
            exposure[quote] += pos.notional_eur
        total = self.total_equity if self.total_equity > 0 else 1.0
        return {k: (v / total) * 100.0 for k, v in exposure.items()}


@dataclass
class SignalDecision:
    signal_id: str
    symbol: str
    action: str
    reason: str
    direction: str = "HOLD"
    confidence: float = 0.0
    tier_weight: float = 1.0
    notional_eur: float = 0.0


class PortfolioManager:
    def __init__(
        self,
        base_notional_eur: float = 1000.0,
        state: PortfolioState | None = None,
        audit_log_dir: str = "logs/portfolio",
    ):
        self.base_notional_eur = base_notional_eur
        self.state = state or PortfolioState()
        self.audit_log_dir = audit_log_dir
        Path(audit_log_dir).mkdir(parents=True, exist_ok=True)

    def process_signals(self, signals: list[dict[str, Any]]) -> list[SignalDecision]:
        decisions = []
        candidates = self._rank_and_filter(signals)

        for sig in candidates:
            decision = self._evaluate_signal(sig)
            decisions.append(decision)

            if decision.action == "ENTER":
                self._record_position(decision, sig)

        self._log_audit(decisions, signals)
        return decisions

    def _rank_and_filter(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        actionable = []
        for sig in signals:
            if sig.get("direction", "HOLD") == "HOLD":
                continue
            if not sig.get("spread_ok", True):
                continue
            config = ALL_SIGNALS.get(sig.get("signal_id", ""))
            if not config:
                continue
            if sig.get("confidence", 0) < config.entry_threshold:
                continue
            actionable.append(sig)

        def sort_key(s):
            config = ALL_SIGNALS[s["signal_id"]]
            tier_order = {"A": 0, "B": 1, "C": 2}
            return (tier_order.get(config.tier, 3), -s.get("confidence", 0))

        actionable.sort(key=sort_key)
        return actionable

    def _evaluate_signal(self, sig: dict[str, Any]) -> SignalDecision:
        signal_id = sig["signal_id"]
        config = ALL_SIGNALS[signal_id]
        tier_weight = TIER_SIZING.get(config.tier, 0.5)
        notional = self.base_notional_eur * tier_weight

        if signal_id in self.state.positions:
            return SignalDecision(
                signal_id=signal_id,
                symbol=config.symbol,
                action="SKIP",
                reason="Already has open position",
                direction=sig["direction"],
                confidence=sig["confidence"],
                tier_weight=tier_weight,
            )

        if self._has_duplicate_pair(config.symbol, sig["direction"]):
            return SignalDecision(
                signal_id=signal_id,
                symbol=config.symbol,
                action="SKIP",
                reason=f"Duplicate pair {config.symbol} already in portfolio",
                direction=sig["direction"],
                confidence=sig["confidence"],
                tier_weight=tier_weight,
            )

        if self.state.position_count >= self.state.max_positions:
            return SignalDecision(
                signal_id=signal_id,
                symbol=config.symbol,
                action="SKIP",
                reason=f"Max positions reached ({self.state.max_positions})",
                direction=sig["direction"],
                confidence=sig["confidence"],
                tier_weight=tier_weight,
            )

        currency_block = self._check_currency_exposure(config.symbol, notional)
        if currency_block:
            return SignalDecision(
                signal_id=signal_id,
                symbol=config.symbol,
                action="SKIP",
                reason=currency_block,
                direction=sig["direction"],
                confidence=sig["confidence"],
                tier_weight=tier_weight,
            )

        if self.state.daily_pnl_pct <= -self.state.daily_loss_limit_pct:
            return SignalDecision(
                signal_id=signal_id,
                symbol=config.symbol,
                action="SKIP",
                reason="Daily loss limit hit",
                direction=sig["direction"],
                confidence=sig["confidence"],
                tier_weight=tier_weight,
            )

        return SignalDecision(
            signal_id=signal_id,
            symbol=config.symbol,
            action="ENTER",
            reason="All checks passed",
            direction=sig["direction"],
            confidence=sig["confidence"],
            tier_weight=tier_weight,
            notional_eur=notional,
        )

    def _has_duplicate_pair(self, symbol: str, direction: str) -> bool:
        # B2 fix: block by symbol alone, not (symbol, direction).
        # Allowing opposing directions on the same symbol creates net-zero exposure
        # while paying spread twice — identical to the P36 stacking bug.
        # P15 (CADJPY Tier B) and P29 (CADJPY Tier C) are the only duplicate-symbol pair.
        for pos in self.state.positions.values():
            if pos.symbol == symbol:
                return True
        return False

    def _check_currency_exposure(self, symbol: str, additional_notional: float) -> str | None:
        base = symbol[:3]
        quote = symbol[3:]
        current = self.state.currency_exposure()
        total = self.state.total_equity if self.state.total_equity > 0 else 1.0
        add_pct = (additional_notional / total) * 100.0

        for ccy in [base, quote]:
            projected = current.get(ccy, 0.0) + add_pct
            if projected > MAX_CURRENCY_EXPOSURE_PCT:
                return f"{ccy} exposure would reach {projected:.1f}% (max {MAX_CURRENCY_EXPOSURE_PCT}%)"

        return None

    def _record_position(self, decision: SignalDecision, sig: dict[str, Any]) -> None:
        config = ALL_SIGNALS[decision.signal_id]
        self.state.positions[decision.signal_id] = PortfolioPosition(
            signal_id=decision.signal_id,
            symbol=config.symbol,
            direction=decision.direction,
            confidence=decision.confidence,
            tier=config.tier,
            tier_weight=decision.tier_weight,
            notional_eur=decision.notional_eur,
            magic_number=config.magic_number,
            entry_time=sig.get("timestamp", datetime.now(timezone.utc).isoformat()),
            atr=sig.get("atr", 0.0),
        )
        logger.info(
            "ENTER {} {} {} conf={:.3f} tier={} notional={:.0f}EUR",
            decision.signal_id, decision.direction, config.symbol,
            decision.confidence, config.tier, decision.notional_eur,
        )

    def close_position(self, signal_id: str, pnl_pct: float = 0.0) -> None:
        if signal_id in self.state.positions:
            pos = self.state.positions.pop(signal_id)
            self.state.daily_pnl_pct += pnl_pct
            logger.info(
                "CLOSE {} {} {} pnl={:.2f}%",
                signal_id, pos.direction, pos.symbol, pnl_pct,
            )

    def get_portfolio_summary(self) -> dict[str, Any]:
        by_tier: dict[str, int] = defaultdict(int)
        by_currency: dict[str, int] = defaultdict(int)
        for pos in self.state.positions.values():
            by_tier[pos.tier] += 1
            by_currency[pos.symbol[:3]] += 1
            by_currency[pos.symbol[3:]] += 1

        return {
            "total_positions": self.state.position_count,
            "by_tier": dict(by_tier),
            "currency_exposure_pct": self.state.currency_exposure(),
            "daily_pnl_pct": self.state.daily_pnl_pct,
            "positions": [
                {
                    "signal_id": p.signal_id,
                    "symbol": p.symbol,
                    "direction": p.direction,
                    "tier": p.tier,
                    "confidence": p.confidence,
                    "notional_eur": p.notional_eur,
                }
                for p in self.state.positions.values()
            ],
        }

    def _log_audit(self, decisions: list[SignalDecision], raw_signals: list[dict]) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        audit = {
            "timestamp": ts,
            "portfolio_summary": self.get_portfolio_summary(),
            "decisions": [
                {
                    "signal_id": d.signal_id,
                    "symbol": d.symbol,
                    "action": d.action,
                    "reason": d.reason,
                    "direction": d.direction,
                    "confidence": d.confidence,
                    "tier_weight": d.tier_weight,
                    "notional_eur": d.notional_eur,
                }
                for d in decisions
            ],
            "raw_signal_count": len(raw_signals),
        }

        filepath = os.path.join(self.audit_log_dir, f"audit_{ts}.json")
        try:
            with open(filepath, "w") as f:
                json.dump(audit, f, indent=2)
        except Exception as e:
            logger.error("Failed to write audit log: {}", e)
