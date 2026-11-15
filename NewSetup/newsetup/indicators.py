"""Technical indicators used across layers (pure functions, no deps)."""

from __future__ import annotations

from .models import PriceBar


def sma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(len(closes) - period, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def atr(bars: list[PriceBar], period: int = 14) -> float | None:
    if len(bars) < period + 1:
        return None
    trs = []
    for i in range(len(bars) - period, len(bars)):
        cur, prev = bars[i], bars[i - 1]
        trs.append(max(
            cur.high - cur.low,
            abs(cur.high - prev.close),
            abs(cur.low - prev.close),
        ))
    return sum(trs) / period


def pct_change(closes: list[float], lookback: int) -> float | None:
    """Percent change of the last close vs `lookback` bars ago."""
    if len(closes) < lookback + 1 or closes[-lookback - 1] == 0:
        return None
    return (closes[-1] / closes[-lookback - 1] - 1.0) * 100.0
