"""GDELT event monitor (playbook 2.3).

Queries the GDELT DOC 2.0 API when network is available and falls back to
the GDELT 2.0 export archive (the same 15-minute ``export.CSV.zip`` feed
the UGT-14 walk-forward used), then to bundled fixture events offline, so
the pipeline is testable without network access. Events are mapped to
the shared Event model with a relevance score (0..1).
"""

from __future__ import annotations

import io
import json
import logging
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen

from newsetup.models import Event, utcnow

log = logging.getLogger("newsetup.gdelt")

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_EXPORT_URL = "http://data.gdeltproject.org/gdeltv2/{slot}.export.CSV.zip"
FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "fixtures", "sample_events.json")

# CAMEO root codes -> description fragment for the synthesized headline
# (mirrors scripts/fetch_gdelt_window_exports.py, the UGT-14 backtest feed).
CAMEO_ROOT = {
    "13": "threaten", "14": "protest", "15": "exhibit military force posture",
    "16": "reduce relations", "17": "coerce", "18": "assault",
    "19": "conventional military fight", "20": "use unconventional mass violence",
    "07": "provide security cooperation", "08": "yield, concede",
    "10": "make statement", "11": "decline comment", "12": "cooperate",
}


def keep_event(goldstein: float, root: str, articles: int) -> bool:
    """Disruptive-event filter (mirrors the UGT-14 backtest ingestion).

    Severe conflict (Goldstein <= -5) with real coverage (>= 5 articles),
    or material conflict / mass protest root codes with >= 10 articles.
    Cooperation-only noise is dropped.
    """
    if goldstein <= -5.0 and articles >= 5:
        return True
    if root in ("18", "19", "20") and articles >= 10:
        return True
    if root == "14" and goldstein <= -4.0 and articles >= 50:
        return True
    return False


def parse_export_line(line: str, ts: datetime) -> Event | None:
    """Parse one GDELT 2.0 export-archive row into a scanner Event.

    GDELT 2.0 export schema (tab-separated, no header, 61 columns;
    indices verified against a live slot, 2026-11-16):
        6 Actor1Name, 21 Actor2Name, 26 EventCode, 28 EventRootCode,
        30 GoldsteinScale, 33 NumArticles, 34 AvgTone,
        52 ActionGeo_FullName, 53 ActionGeo_CountryCode
    """
    f = line.split("\t")
    if len(f) < 54:
        return None
    try:
        root = f[28]
        goldstein = float(f[30])
        articles = int(f[33])
        avg_tone = float(f[34])
    except (ValueError, IndexError):
        return None
    if not keep_event(goldstein, root, articles):
        return None
    geo = f[52] or ""
    country = f[53] or ""
    desc = CAMEO_ROOT.get(root, f"event {f[26]}")
    actors = ", ".join(a for a in (f[6], f[21]) if a)
    where = geo or country
    headline = (f"{desc}: {actors} in {where}" if actors
               else f"{desc} in {where}").strip()
    if not headline or headline == f"event {f[26]}":
        return None
    score = max(0.0, min(1.0, (5.0 - goldstein) / 10.0 + max(0.0, -avg_tone) / 40.0))
    return Event(
        headline=headline,
        themes=[f"cameo{root}", country.lower()],
        goldstein_score=goldstein,
        score=round(score, 3),
        source="gdelt_export",
        ts=ts,
    )


class GDELTMonitor:
    """Layer-1 EVENT data source."""

    # GDELT DOC 2.0 asks for at most one request every 5 seconds; the
    # scanner evaluates up to 40 inefficiencies per cycle, so live query
    # results are cached briefly and shared across those evaluations.
    LIVE_CACHE_TTL = 300  # seconds
    # Export-archive fallback (UGT-15 Phase 4): the DOC 2.0 API rate-limits
    # to one request / 5 s and 429s persistently on this host, which used
    # to push the live pipeline onto stale fixtures. The 15-minute export
    # archive is the same feed the UGT-14 walk-forward ingested, so it is
    # preferred over fixtures whenever the DOC API is unavailable.
    EXPORT_SLOTS: int = 96   # last 24 hours of published 15-minute slots
                             # (matches the DOC API's since_hours=24 window)
    EXPORT_LAG_MIN: int = 45  # newest slot that is certainly published

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
        events: list[Event] | None = None
        try:
            events = self._query_gdelt(keywords or [], since_hours)
        except Exception as exc:                     # noqa: BLE001 - degrade gracefully
            # GDELT DOC 2.0 rate-limits to one request per 5 seconds and
            # answers with a plain-text notice; retry once after a pause.
            log.warning("GDELT DOC query failed (%s); retrying once in 6s", exc)
            import time
            time.sleep(6)
            try:
                events = self._query_gdelt(keywords or [], since_hours)
            except Exception as exc2:                # noqa: BLE001
                log.warning("GDELT DOC retry failed (%s)", exc2)
                events = None
        if not events:
            # DOC API unavailable -> 15-minute export archive (fresh, real
            # events; the same feed the UGT-14 walk-forward ingested).
            events = self._query_export(since_hours)
        if not events:
            log.warning("DOC API and export archive both empty; "
                        "falling back to fixtures (STALE events)")
            events = self._fixture_events()
        # Cache whatever we settled on (including fixtures) so one failing
        # cycle does not re-attempt the network for every inefficiency.
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

    # ------------------------------------------------------------------
    def _query_export(self, since_hours: int) -> list[Event]:
        """Fetch recent GDELT 2.0 export-archive slots (fresh real events).

        Pulls the last ``EXPORT_SLOTS`` published 15-minute ``export.CSV.zip``
        files (bounded, ~100KB each), filters to disruptive events and maps
        them to scanner Events with synthesized CAMEO headlines - the same
        parsing the UGT-14 walk-forward ingestion used.
        """
        end = datetime.now(timezone.utc) - timedelta(minutes=self.EXPORT_LAG_MIN)
        end = end.replace(minute=end.minute - end.minute % 15, second=0,
                          microsecond=0)
        slots = [(end - timedelta(minutes=15 * i)).strftime("%Y%m%d%H%M%S")
                 for i in range(self.EXPORT_SLOTS)]
        events: list[Event] = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            for evs in pool.map(self._fetch_export_slot, slots):
                events.extend(evs)
        if events:
            log.info("GDELT export archive: %d events from %d slots "
                     "(doc-api unavailable)", len(events), len(slots))
        return events

    def _fetch_export_slot(self, slot: str) -> list[Event]:
        url = GDELT_EXPORT_URL.format(slot=slot)
        try:
            data = urlopen(url, timeout=30).read()
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                raw = zf.read(zf.namelist()[0]).decode("utf-8", errors="replace")
        except Exception as exc:                      # noqa: BLE001 - slot simply absent
            log.debug("export slot %s unavailable: %s", slot, exc)
            return []
        ts = datetime.strptime(slot, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        out = []
        for line in raw.splitlines():
            ev = parse_export_line(line, ts=ts)
            if ev is not None:
                out.append(ev)
        return out

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
