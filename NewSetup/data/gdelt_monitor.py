"""GDELT event monitor (playbook 2.3).

Queries the GDELT DOC 2.0 API when network is available and falls back to
bundled fixture events offline, so the pipeline is testable without
network access. Events are mapped to the shared Event model with a
relevance score (0..1).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import urlopen

from newsetup.models import Event, utcnow

log = logging.getLogger("newsetup.gdelt")

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "fixtures", "sample_events.json")


class GDELTMonitor:
    """Layer-1 EVENT data source."""

    # GDELT DOC 2.0 asks for at most one request every 5 seconds; the
    # scanner evaluates up to 40 inefficiencies per cycle, so live query
    # results are cached briefly and shared across those evaluations.
    LIVE_CACHE_TTL = 300  # seconds

    def __init__(self, offline: bool = False, timeout: int = 15):
        self.offline = offline
        self.timeout = timeout
        self._cache: list[Event] | None = None
        self._cache_at = None
        self._live_cache: list[Event] | None = None
        self._live_cache_at = None

    def get_events(self, since_hours: int = 24, keywords: list[str] | None = None) -> list[Event]:
        if self.offline:
            return self._fixture_events()
        now = utcnow()
        if (self._live_cache is not None and self._live_cache_at is not None
                and now - self._live_cache_at
                < timedelta(seconds=self.LIVE_CACHE_TTL)):
            return self._live_cache
        try:
            events = self._query_gdelt(keywords or [], since_hours)
        except Exception as exc:                     # noqa: BLE001 - degrade gracefully
            # GDELT DOC 2.0 rate-limits to one request per 5 seconds and
            # answers with a plain-text notice; retry once after a pause.
            log.warning("GDELT query failed (%s); retrying once in 6s", exc)
            import time
            time.sleep(6)
            try:
                events = self._query_gdelt(keywords or [], since_hours)
            except Exception as exc2:                # noqa: BLE001
                log.warning("GDELT retry failed (%s); falling back to fixtures", exc2)
                return self._fixture_events()
        self._live_cache, self._live_cache_at = events, now
        return events

    # ------------------------------------------------------------------
    def _query_gdelt(self, keywords: list[str], since_hours: int) -> list[Event]:
        query = " ".join(keywords) or "supply chain disruption"
        params = urlencode({
            "query": query,
            "mode": "ArtList",
            "maxrecords": 50,
            "sort": "DateDesc",
            "format": "json",
        })
        with urlopen(f"{GDELT_DOC_URL}?{params}", timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        events: list[Event] = []
        for art in data.get("articles", []):
            title = art.get("title", "")
            goldstein = art.get("goldstein", 0.0) or 0.0
            events.append(Event(
                headline=title,
                themes=[query],
                goldstein_score=float(goldstein),
                score=min(1.0, abs(float(goldstein)) / 10.0),
                source="gdelt",
            ))
        return events

    def _fixture_events(self) -> list[Event]:
        if self._cache is not None and utcnow() - self._cache_at < timedelta(hours=1):
            return self._cache
        if os.path.exists(FIXTURE_PATH):
            with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            events = [Event(**e) for e in raw]
        else:
            events = [
                Event(headline="China announces export ban on rare earth processing technology",
                      themes=["export ban", "rare earth"], goldstein_score=-7.0,
                      score=0.8, source="fixture"),
                Event(headline="Major copper mine strike in Chile enters second week",
                      themes=["mine strike", "copper"], goldstein_score=-5.5,
                      score=0.7, source="fixture"),
                Event(headline="Panama Canal transit restrictions eased after rainfall",
                      themes=["canal", "shipping"], goldstein_score=4.0,
                      score=0.6, source="fixture"),
            ]
        self._cache, self._cache_at = events, utcnow()
        return events
