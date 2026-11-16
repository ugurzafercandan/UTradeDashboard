"""Fetch GDELT 2.0 export-archive events for the playbook windows (UGT-17/19 item 1).

Downloads the 15-minute ``export.CSV.zip`` event files from
http://data.gdeltproject.org/gdeltv2/ for every playbook 5.2 window (six
slots per day, i.e. one every four hours), filters to disruptive events
(severe Goldstein score or material-conflict/protest CAMEO root codes with
real coverage), converts each to the scanner Event model with a
synthesized headline (CAMEO root description + action geography), and
writes data/caches/events/gdelt_export_events.csv.

GDELT 2.0 export schema (tab-separated, no header), columns used here:
    26 EventCode, 28 EventRootCode, 30 GoldsteinScale, 31 NumMentions,
    32 NumSources, 33 NumArticles, 34 AvgTone, 51 ActionGeo_FullName,
    52 ActionGeo_CountryCode, 58 DATEADDED, 59 SOURCEURL

Usage (from NewSetup/, any Python with requests/stdlib):

    python -m scripts.fetch_gdelt_window_exports [--workers 8]
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import os
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.event_backtests import PLAYBOOK_WINDOWS          # noqa: E402
from data.historical_events import EVENTS_DIR, GDELT_CSV       # noqa: E402

log = logging.getLogger("newsetup.fetch_gdelt")

BASE_URL = "http://data.gdeltproject.org/gdeltv2/{slot}.export.CSV.zip"
SLOTS_PER_DAY = 6           # every 4 hours starting 00:45 UTC
SLOT_HOURS = 24 // SLOTS_PER_DAY

# CAMEO root codes -> description fragment for the synthesized headline.
CAMEO_ROOT = {
    "13": "threaten", "14": "protest", "15": "exhibit military force posture",
    "16": "reduce relations", "17": "coerce", "18": "assault",
    "19": "conventional military fight", "20": "use unconventional mass violence",
    "07": "provide security cooperation", "08": "yield, concede",
    "10": "make statement", "11": "decline comment", "12": "cooperate",
}

# Keep events that are disruptive: severe conflict (Goldstein <= -5) with
# real coverage (>= 5 articles), or material conflict / mass protest root
# codes with >= 10 articles. Cooperation-only noise is dropped.
def keep_event(goldstein: float, root: str, articles: int) -> bool:
    if goldstein <= -5.0 and articles >= 5:
        return True
    if root in ("18", "19", "20") and articles >= 10:
        return True
    if root == "14" and goldstein <= -4.0 and articles >= 50:
        return True
    return False


def window_days(start_s: str, end_s: str):
    start = datetime.strptime(start_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days


def slot_stamps(day: datetime) -> list[str]:
    stamps = []
    for h in range(SLOT_HOURS // 2, 24, SLOT_HOURS):
        stamps.append(day.strftime("%Y%m%d") + f"{h:02d}4500")
    return stamps


def fetch_slot(slot: str, retries: int = 3) -> list[dict]:
    url = BASE_URL.format(slot=slot)
    data = None
    for _ in range(retries):
        try:
            data = urllib.request.urlopen(url, timeout=60).read()
            break
        except Exception:
            continue
    if data is None:
        log.warning("failed to fetch %s", slot)
        return []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        name = zf.namelist()[0]
        raw = zf.read(name).decode("utf-8", errors="replace")
    out = []
    ts = datetime.strptime(slot, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    for line in raw.splitlines():
        f = line.split("\t")
        if len(f) < 60:
            continue
        try:
            root = f[28]
            goldstein = float(f[30])
            articles = int(f[33])
            avg_tone = float(f[34])
        except (ValueError, IndexError):
            continue
        if not keep_event(goldstein, root, articles):
            continue
        geo = f[51] or ""
        country = f[52] or ""
        desc = CAMEO_ROOT.get(root, f"event {f[26]}")
        headline = f"{desc} in {geo or country}".strip()
        if not headline or headline == f"event {f[26]}":
            continue
        score = max(0.0, min(1.0, (5.0 - goldstein) / 10.0 + max(0.0, -avg_tone) / 40.0))
        out.append({
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "headline": headline,
            "goldstein": goldstein,
            "score": round(score, 3),
            "themes": f"cameo{root}|{country.lower()}",
            "source_url": f[59][:200] if len(f) > 59 else "",
        })
    return out


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(argv)

    slots = []
    for window, (start, end, _desc) in PLAYBOOK_WINDOWS.items():
        for day in window_days(start, end):
            slots.extend((window, s) for s in slot_stamps(day))
    log.info("fetching %d GDELT export slots across %d windows",
             len(slots), len(PLAYBOOK_WINDOWS))

    rows: list[dict] = []
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(fetch_slot, s): (w, s) for w, s in slots}
        for fut in as_completed(futs):
            done += 1
            if done % 200 == 0:
                log.info("slots %d/%d, events so far %d", done, len(slots), len(rows))
            rows.extend(fut.result())

    rows.sort(key=lambda r: r["ts"])
    os.makedirs(EVENTS_DIR, exist_ok=True)
    with open(GDELT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ts", "headline", "goldstein",
                                               "score", "themes", "source_url"])
        writer.writeheader()
        writer.writerows(rows)
    log.info("wrote %d GDELT events to %s", len(rows), GDELT_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
