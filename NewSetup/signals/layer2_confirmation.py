"""Layer 2: Confirmation Engine (playbook 4.2).

Confirms raw layer-1 signals with technical indicators (RSI, SMA trend),
sentiment and a minimum history check. Produces a 0..1 confirmation score;
signals below settings.layer2.min_score are not confirmed.
"""

from __future__ import annotations

from newsetup.config import load_settings
from newsetup.indicators import rsi, sma
from newsetup.models import ConfirmedSignal, RawSignal


class Layer2Confirmation:
    def __init__(self, price_provider, sentiment_provider=None, settings: dict | None = None):
        self.prices = price_provider
        self.sentiment = sentiment_provider
        self.settings = settings or load_settings()
        cfg = self.settings["layer2"]
        self.min_score = cfg["min_score"]
        self.rsi_period = cfg["rsi_period"]
        self.rsi_oversold = cfg["rsi_oversold"]
        self.rsi_overbought = cfg["rsi_overbought"]
        self.sma_fast = cfg["sma_fast"]
        self.sma_slow = cfg["sma_slow"]
        self.min_bars = cfg["min_history_bars"]

    def confirm(self, raw: RawSignal) -> ConfirmedSignal:
        reasons: list[str] = []
        score = 0.0

        bars = self.prices.get_series(raw.instrument, lookback_days=self.min_bars + 10)
        if not bars or len(bars) < self.min_bars:
            return ConfirmedSignal(raw=raw, confirmed=False, score=0.0,
                                   reasons=[f"insufficient history ({len(bars) if bars else 0} bars)"])
        closes = [b.close for b in bars]
        last = closes[-1]

        # 1) RSI check (weight 0.35): oversold for BUY, overbought for SELL
        r = rsi(closes, self.rsi_period)
        if r is None:
            reasons.append("RSI unavailable")
        elif raw.direction == "BUY" and r <= self.rsi_oversold:
            score += 0.35
            reasons.append(f"RSI({self.rsi_period})={r:.1f} oversold (supports BUY)")
        elif raw.direction == "SELL" and r >= self.rsi_overbought:
            score += 0.35
            reasons.append(f"RSI({self.rsi_period})={r:.1f} overbought (supports SELL)")
        else:
            reasons.append(f"RSI({self.rsi_period})={r:.1f} neutral")

        # 2) Trend check (weight 0.35): fast SMA vs slow SMA aligned with direction
        fast, slow = sma(closes, self.sma_fast), sma(closes, self.sma_slow)
        if fast is None or slow is None:
            reasons.append("SMA unavailable")
        elif raw.direction == "BUY" and fast > slow:
            score += 0.35
            reasons.append(f"SMA{self.sma_fast} > SMA{self.sma_slow} (uptrend)")
        elif raw.direction == "SELL" and fast < slow:
            score += 0.35
            reasons.append(f"SMA{self.sma_fast} < SMA{self.sma_slow} (downtrend)")
        else:
            reasons.append(f"SMA{self.sma_fast} {'<' if (fast or 0) < (slow or 0) else '>='} SMA{self.sma_slow} against direction")

        # 3) Layer-1 confidence contribution (weight 0.20)
        score += 0.20 * raw.confidence
        reasons.append(f"layer1 confidence {raw.confidence:.2f}")

        # 4) Sentiment agreement (weight 0.10)
        if self.sentiment is not None:
            s = self.sentiment.latest_for_theme(raw.inefficiency_name.lower())
            if s is not None:
                agree = (raw.direction == "BUY" and s < 0) or (raw.direction == "SELL" and s > 0)
                if agree:
                    score += 0.10
                    reasons.append(f"sentiment {s:+.2f} agrees")
                else:
                    reasons.append(f"sentiment {s:+.2f} neutral/opposed")

        confirmed = score >= self.min_score
        return ConfirmedSignal(raw=raw, confirmed=confirmed, score=round(score, 3), reasons=reasons)
