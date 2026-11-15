"""FinBERT sentiment scoring (playbook 2.3).

Uses the transformers FinBERT pipeline when available; otherwise a
lexicon-based fallback scorer so the system runs anywhere. Scores are
in [-1, 1] (negative = supply-threat / risk-off tone).
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

log = logging.getLogger("newsetup.sentiment")

_POSITIVE = ("eased", "reopened", "resolved", "surplus", "overcapacity", "boost",
             "expand", "record output", "agreement", "recovery")
_NEGATIVE = ("ban", "shortage", "crisis", "disruption", "halt", "strike", "coup",
             "war", "attack", "sanction", "restriction", "closure", "collapse",
             "flood", "earthquake", "export controls", "supply crunch")


class FinBERTSentiment:
    """Layer-1/2 SENTIMENT data source."""

    def __init__(self, model_name: str = "ProsusAI/finbert", use_transformers: bool | None = None):
        self.model_name = model_name
        if use_transformers is None:
            use_transformers = os.environ.get("NEWSETUP_DISABLE_TRANSFORMERS", "") != "1"
        self.pipeline = None
        if use_transformers:
            try:
                from transformers import pipeline            # optional heavy dep
                self.pipeline = pipeline("sentiment-analysis", model=model_name)
                log.info("FinBERT pipeline loaded: %s", model_name)
            except Exception as exc:                          # noqa: BLE001
                log.info("transformers unavailable (%s); using lexicon fallback", exc)
        self._theme_cache: dict[str, float] = {}

    # ------------------------------------------------------------------
    def score(self, text: str) -> float:
        """Sentiment score in [-1, 1]. Negative = supply-threat tone."""
        if self.pipeline is not None:
            try:
                out = self.pipeline(text[:512])[0]
                label = out["label"].lower()
                mag = float(out.get("score", 0.5))
                # negative FinBERT label = bearish/threat tone -> negative score
                return -mag if "negative" in label else mag
            except Exception as exc:                          # noqa: BLE001
                log.warning("FinBERT inference failed (%s); lexicon fallback", exc)
        return self._lexicon_score(text)

    @staticmethod
    def _lexicon_score(text: str) -> float:
        t = text.lower()
        pos = sum(1 for w in _POSITIVE if w in t)
        neg = sum(1 for w in _NEGATIVE if w in t)
        if pos == neg == 0:
            return 0.0
        total = pos + neg
        return round((pos - neg) / total, 3)

    # ------------------------------------------------------------------
    def latest_for_theme(self, theme: str) -> float | None:
        """Latest sentiment for a theme (e.g. an inefficiency name).

        In the full system this reads scored headlines from the DB; here it
        serves the deterministic offline path from a small theme map.
        """
        if theme in self._theme_cache:
            return self._theme_cache[theme]
        return None

    def ingest_headlines(self, headlines: list[str]) -> None:
        """Score headlines and store per-keyword theme averages."""
        buckets: dict[str, list[float]] = {}
        for h in headlines:
            s = self.score(h)
            for word in re.findall(r"[a-z]+", h.lower()):
                buckets.setdefault(word, []).append(s)
        self._theme_cache = {
            k: round(sum(v) / len(v), 3)
            for k, v in buckets.items()
            if len(v) >= 2 or abs(v[0]) > 0.3
        }
