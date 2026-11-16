"""Layer 1: Inefficiency Scanner (playbook 4.1).

Scans all 40 inefficiencies' trigger conditions against pluggable data
providers and emits raw signals. Providers are injected so the same
scanner serves live (GDELT/MT5), paper and backtest (fixtures/replay)
environments.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol

from newsetup.config import (load_gdelt_keywords, load_inefficiencies,
                             load_settings)
from newsetup.direction import map_direction, thesis_for
from newsetup.models import (Event, Inefficiency, PriceBar, RawSignal,
                             utcnow)


class EventProvider(Protocol):
    def get_events(self, since_hours: int = 24) -> list[Event]: ...


class PriceProvider(Protocol):
    def get_series(self, symbol: str, lookback_days: int = 250) -> list[PriceBar]: ...


class SentimentProvider(Protocol):
    def latest_for_theme(self, theme: str) -> float | None: ...


class Layer1Scanner:
    def __init__(
        self,
        event_provider: EventProvider,
        price_provider: PriceProvider,
        sentiment_provider: SentimentProvider | None = None,
        inefficiencies: list[Inefficiency] | None = None,
        settings: dict | None = None,
    ):
        self.events = event_provider
        self.prices = price_provider
        self.sentiment = sentiment_provider
        self.inefficiencies = inefficiencies or load_inefficiencies()
        self.settings = settings or load_settings()
        self.gdelt_keywords = load_gdelt_keywords()   # per-inefficiency theming
        cfg = self.settings["layer1"]
        self.event_score_threshold = cfg["event_score_threshold"]
        self.spike_24h = cfg["price_spike_pct_24h"]
        self.spike_30d = cfg["price_spike_pct_30d"]

    # ------------------------------------------------------------------
    def scan_all(self) -> list[RawSignal]:
        """Run every inefficiency's triggers. Returns raw signals."""
        signals: list[RawSignal] = []
        for ineff in self.inefficiencies:
            signals.extend(self.scan_inefficiency(ineff))
        return signals

    def scan_inefficiency(self, ineff: Inefficiency) -> list[RawSignal]:
        signals: list[RawSignal] = []
        symbol = ineff.primary_symbol()
        if not symbol or ineff.trade_type.startswith("No trade"):
            return signals
        for trigger in ineff.triggers:
            sig = self._evaluate(trigger, ineff, symbol)
            if sig is not None:
                signals.append(sig)
                break  # one signal per inefficiency per scan
        return signals

    # ------------------------------------------------------------------
    def _evaluate(self, trigger, ineff: Inefficiency, symbol: str) -> RawSignal | None:
        handler = {
            "EVENT": self._eval_event,
            "PRICE": self._eval_price,
            "SENTIMENT": self._eval_sentiment,
            "DATA": self._eval_data,
        }.get(trigger.trigger_type.upper())
        if handler is None:
            return None
        return handler(trigger, ineff, symbol)

    def _eval_event(self, trigger, ineff, symbol) -> RawSignal | None:
        events = self.events.get_events(since_hours=24)
        keywords = self._keywords(ineff)
        for ev in events:
            if ev.score < self.event_score_threshold and abs(ev.goldstein_score) < 5:
                continue
            text = ev.headline.lower()
            if any(k in text for k in keywords):
                # negative-goldstein / disruption news -> long the proxy
                direction = "BUY" if self._is_supply_shock(text, ev) else "SELL"
                return RawSignal(
                    inefficiency_id=ineff.id,
                    inefficiency_name=ineff.name,
                    instrument=symbol,
                    direction=direction,
                    trigger_type="EVENT",
                    trigger_description=f"{ev.headline} (score={ev.score:.2f})",
                    confidence=min(0.95, 0.5 + abs(ev.goldstein_score) / 20.0 + ev.score / 4.0),
                    thesis="event",
                )
        return None

    def _eval_price(self, trigger, ineff, symbol) -> RawSignal | None:
        bars = self.prices.get_series(symbol, lookback_days=250)
        if not bars or len(bars) < 2:
            return None
        closes = [b.close for b in bars]
        chg_24h = self._pct(closes, 1)
        chg_30d = self._pct(closes, min(30, len(closes) - 1))
        # Per-inefficiency direction thesis (UGT-17/19 item 3): the same
        # spike can be faded (reversion) or followed (continuation)
        # depending on the inefficiency's fitted model entry.
        thesis = thesis_for(ineff.id)
        move = None
        for chg in (chg_24h, chg_30d):
            if chg is None:
                continue
            if chg <= -self.spike_24h:
                move = "DOWN"
            elif chg >= self.spike_24h:
                move = "UP"
            if move:
                return self._price_signal(ineff, symbol,
                                           map_direction(thesis, move),
                                           chg, thesis)
        if chg_30d is not None and abs(chg_30d) >= self.spike_30d:
            move = "UP" if chg_30d > 0 else "DOWN"
            return self._price_signal(ineff, symbol,
                                      map_direction(thesis, move),
                                      chg_30d, thesis)
        return None

    def _price_signal(self, ineff, symbol, direction, chg,
                      thesis: str = "") -> RawSignal:
        return RawSignal(
            inefficiency_id=ineff.id,
            inefficiency_name=ineff.name,
            instrument=symbol,
            direction=direction,
            trigger_type="PRICE",
            trigger_description=f"{symbol} move {chg:+.2f}% (threshold {self.spike_24h}%)",
            confidence=0.6,
            thesis=thesis,
        )

    def _eval_sentiment(self, trigger, ineff, symbol) -> RawSignal | None:
        if self.sentiment is None:
            return None
        score = self.sentiment.latest_for_theme(ineff.name.lower())
        if score is None:
            return None
        if score <= self.settings["layer2"]["sentiment_threshold"]:
            return RawSignal(
                inefficiency_id=ineff.id,
                inefficiency_name=ineff.name,
                instrument=symbol,
                direction="BUY",   # negative supply sentiment -> long proxy/short consumer
                trigger_type="SENTIMENT",
                trigger_description=f"Sentiment {score:.2f} for {ineff.name}",
                confidence=0.55,
            )
        return None

    def _eval_data(self, trigger, ineff, symbol) -> RawSignal | None:
        # Structured-data triggers (USGS, MarineTraffic, inventories) are
        # scheduled jobs in the full system; the scanner surfaces them via
        # the event provider as synthetic events.
        return None

    # ------------------------------------------------------------------
    def _keywords(self, ineff: Inefficiency) -> list[str]:
        """GDELT match keywords for one inefficiency.

        Uses the per-inefficiency keyword theming derived from the playbook
        trade cards (config/gdelt_keywords.yaml) when available, falling back
        to the generic name + shock-word list.
        """
        themed = self.gdelt_keywords.get(ineff.id)
        # Shared disruption shock-words applied on top of the theme. This
        # list intentionally matches Layer1Scanner._is_supply_shock so any
        # headline that can flip direction can also fire the trigger
        # (UGT-17/19 consistency fix: war/attack/halt were previously
        # direction-only and could never trigger).
        extras = ["export ban", "restriction", "sanction", "disruption",
                  "shutdown", "mine strike", "coup", "closure",
                  "earthquake", "flood", "ban", "strike", "attack",
                  "war", "halt"]
        if themed:
            return list(themed) + extras
        base = [w.lower() for w in ineff.name.replace("/", " ").split()]
        return base + extras

    @staticmethod
    def _is_supply_shock(text: str, ev: Event) -> bool:
        shock_words = ("ban", "restriction", "strike", "shutdown", "coup",
                       "closure", "attack", "war", "sanction", "disruption",
                       "earthquake", "flood", "halt")
        return any(w in text for w in shock_words) or ev.goldstein_score < 0

    @staticmethod
    def _pct(closes: list[float], lookback: int) -> float | None:
        if len(closes) < lookback + 1 or closes[-lookback - 1] == 0:
            return None
        return (closes[-1] / closes[-lookback - 1] - 1.0) * 100.0
