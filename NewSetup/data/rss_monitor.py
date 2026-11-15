"""RSS news monitor (playbook 8.4 supply chain news workflow).

Pulls the priority RSS feeds with stdlib only (urllib + xml.etree) and
converts items into Event objects. Feed list comes from the playbook's
source-priority table.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

from newsetup.models import Event, utcnow

log = logging.getLogger("newsetup.rss")

PRIORITY_FEEDS = [
    "https://www.reuters.com/arc/outboundfeeds/v3/all/rss",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.ft.com/rss/home",
    "https://oilprice.com/rss/main",
    "https://www.mining.com/feed/",
    "https://agriculture.ec.europa.eu/news_en/rss.xml",
]

_USER_AGENT = "Mozilla/5.0 (compatible; NewSetupRSS/0.1)"


class RssMonitor:
    def __init__(self, feeds: list[str] | None = None, timeout: int = 10, offline_events: list[Event] | None = None):
        self.feeds = feeds or PRIORITY_FEEDS
        self.timeout = timeout
        self._offline_events = offline_events or []

    def get_events(self, since_hours: int = 24, keywords: list[str] | None = None) -> list[Event]:
        """Fetch and filter feed items matching keywords."""
        items = self._fetch_all()
        if keywords:
            pat = re.compile("|".join(re.escape(k.lower()) for k in keywords))
            items = [e for e in items if pat.search(e.headline.lower())]
        return items

    def _fetch_all(self) -> list[Event]:
        events: list[Event] = []
        for url in self.feeds:
            try:
                events.extend(self._fetch_one(url))
            except Exception as exc:                          # noqa: BLE001
                log.debug("feed %s failed: %s", url, exc)
        if not events:
            return list(self._offline_events)
        return events

    def _fetch_one(self, url: str) -> list[Event]:
        req = Request(url, headers={"User-Agent": _USER_AGENT})
        with urlopen(req, timeout=self.timeout) as resp:
            root = ET.fromstring(resp.read())
        events = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            events.append(Event(
                headline=title,
                themes=[],
                goldstein_score=0.0,
                score=0.5,
                source="rss",
            ))
        return events
