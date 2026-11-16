"""Layer 2: Confirmation Engine (playbook 4.2, UGT-17/19 item 4 rework).

Confirms raw layer-1 signals with technical indicators (RSI, SMA trend),
sentiment and a minimum history check. Produces a 0..1 confirmation score;
signals below settings.layer2.min_score are not confirmed.

UGT-17/19 consistency rework: the old gate applied one fixed check set to
every signal - RSI reversal extremes plus trend CONTINUATION - so for the
stack's (default) reversion triggers the two checks contradicted each
other by construction (the UGT-14 measured split: both-agree 11.0%,
neither 39.0% of 7,149 signals). The gate is now thesis-aware and agrees
with the layer-1 trigger BY DESIGN:

  reversion (fade the spike):
    RSI   - BUY needs oversold, SELL needs overbought (the stretched
            extreme that makes fading plausible)
    SMA   - BUY needs fast < slow, SELL needs fast > slow (the pullback
            context the bounce happens in)

  continuation (go with the move):
    RSI   - BUY needs RSI >= midline, SELL needs RSI <= midline (fresh
            momentum on the breakout side)
    SMA   - BUY needs fast > slow, SELL needs fast < slow (trend carries
            the move)

  event (semantic news direction: disruption long / de-escalation short):
    RSI   - BUY needs RSI < overbought, SELL needs RSI > oversold
            (headroom: the repricing still has room to run)
    event - fresh-trigger check: the raw signal IS the event response, so
            this component always supports an event trigger by design
            (weight replaces the SMA check)

Weights are unchanged (RSI 0.35, second check 0.35, layer-1 confidence
0.20, sentiment 0.10), so min_score keeps its tuning meaning.
"""

from __future__ import annotations

from newsetup.config import load_settings
from newsetup.direction import CONTINUATION, EVENT, REVERSION
from newsetup.indicators import rsi, sma
from newsetup.models import ConfirmedSignal, RawSignal

RSI_MIDLINE = 50.0


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
        thesis = raw.thesis or self._default_thesis(raw)

        bars = self.prices.get_series(raw.instrument, lookback_days=self.min_bars + 10)
        if not bars or len(bars) < self.min_bars:
            return ConfirmedSignal(raw=raw, confirmed=False, score=0.0,
                                   reasons=[f"insufficient history ({len(bars) if bars else 0} bars)"])
        closes = [b.close for b in bars]

        # 1) RSI check (weight 0.35), thesis-aware
        r = rsi(closes, self.rsi_period)
        rsi_ok = False
        if r is None:
            reasons.append("RSI unavailable")
        elif thesis == REVERSION:
            rsi_ok = ((raw.direction == "BUY" and r <= self.rsi_oversold)
                      or (raw.direction == "SELL" and r >= self.rsi_overbought))
            reasons.append(
                f"RSI({self.rsi_period})={r:.1f} "
                + (f"{'oversold' if raw.direction == 'BUY' else 'overbought'} (supports {raw.direction})"
                   if rsi_ok else f"no stretch extreme for reversion {raw.direction}"))
        elif thesis == EVENT:
            rsi_ok = ((raw.direction == "BUY" and r < self.rsi_overbought)
                      or (raw.direction == "SELL" and r > self.rsi_oversold))
            reasons.append(
                f"RSI({self.rsi_period})={r:.1f} "
                + (f"headroom for event {raw.direction}" if rsi_ok
                   else f"at RSI extreme, no headroom for event {raw.direction}"))
        else:  # continuation
            rsi_ok = ((raw.direction == "BUY" and r >= RSI_MIDLINE)
                      or (raw.direction == "SELL" and r <= RSI_MIDLINE))
            reasons.append(
                f"RSI({self.rsi_period})={r:.1f} "
                + (f"momentum supports continuation {raw.direction}" if rsi_ok
                   else f"no momentum for continuation {raw.direction}"))
        if rsi_ok:
            score += 0.35

        # 2) Second check (weight 0.35), thesis-aware
        if thesis == EVENT:
            # the raw signal is the event response; a fresh event trigger
            # supports itself by design (weight in place of the SMA check)
            score += 0.35
            reasons.append("event trigger is its own confirmation (fresh news reprice)")
        else:
            fast, slow = sma(closes, self.sma_fast), sma(closes, self.sma_slow)
            second_ok = False
            if fast is None or slow is None:
                reasons.append("SMA unavailable")
            elif thesis == REVERSION:
                second_ok = ((raw.direction == "BUY" and fast < slow)
                              or (raw.direction == "SELL" and fast > slow))
                reasons.append(
                    f"SMA{self.sma_fast} {'<' if (fast or 0) < (slow or 0) else '>'} SMA{self.sma_slow} "
                    + ("pullback context (supports reversion)" if second_ok
                       else "no pullback context for reversion"))
            else:  # continuation
                second_ok = ((raw.direction == "BUY" and fast > slow)
                              or (raw.direction == "SELL" and fast < slow))
                reasons.append(
                    f"SMA{self.sma_fast} {'<' if (fast or 0) < (slow or 0) else '>'} SMA{self.sma_slow} "
                    + ("trend carries the move (supports continuation)" if second_ok
                       else "trend against continuation direction"))
            if second_ok:
                score += 0.35

        # 3) Layer-1 confidence contribution (weight 0.20)
        score += 0.20 * raw.confidence
        reasons.append(f"layer1 confidence {raw.confidence:.2f} (thesis={thesis})")

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

    def _default_thesis(self, raw: RawSignal | None = None) -> str:
        """Thesis for legacy signals with no thesis tag: EVENT triggers
        use the event thesis; everything else falls back to the direction
        model's global default."""
        from newsetup.direction import thesis_for
        if raw is not None and raw.trigger_type.upper() == "EVENT":
            return EVENT
        return thesis_for(None)
