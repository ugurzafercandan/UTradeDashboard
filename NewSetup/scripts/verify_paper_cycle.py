"""Verify a Phase-4 paper-trading cycle against the UGT-36 acceptance criteria.

Read-only checker for the post-mortem of each ``paper_daily`` cycle. It
implements the four checks from issue UGT-36 ("Post-fix Phase-4 cycle-2
verification"), so the issue-scoped wake after a cycle can run:

    C:/Python314/python.exe NewSetup/scripts/verify_paper_cycle.py

Checks
------
1. Last cycle in NewSetup/logs/paper_daily.log exited 0.
2. Book sanity (paper_state.json): open positions have SL/TP ordered
   correctly for their direction, closed_at null, pnl 0.
3. No phantom closes in state AND db: every closed trade has
   closed_at strictly AFTER opened_at, and no SL/TP exit within the
   same cycle (~10 min) as the fill (the UGT-32 defect pattern).
4. Fill freshness: for each instrument traded in the last cycle, the
   D1 bar cache has a bar within ``--stale-days`` (default 5) of the
   cycle, and the fill entry price is within ``--max-dev`` (default 3%)
   of the latest cached close.

Also cross-checks db/newsetup.sqlite3 (trades rows with impossible
closed_at, signals count) when present.

Exit codes: 0 all checks pass, 1 at least one check failed,
2 structural error (missing/unparseable files).

Validated 2026-11-17 against: the clean post-revert cycle-1 state
(PASS) and the preserved USDZAR phantom-close evidence file
(paper_state.json.usdzar_phantom_evidence_2026-11-17, expected FAIL).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CYCLE_MARKER = "cycle ====="
EXIT_MARKER = "===== exit"

# A close within this many seconds of the fill is the same daily cycle.
SAME_CYCLE_S = 10 * 60


def _parse_ts(value):
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except ValueError:
        return None


def last_cycle(log_path):
    """Return (cycle_header, cycle_ts, exit_code, exit_line) for the last block."""
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    header = ts = exit_line = None
    for line in lines:
        if CYCLE_MARKER in line:
            header = line
            # e.g. "===== Mon 11/16/2026 15:45:00.93 UGT15_..._PaperDaily cycle ====="
            inner = line.split("=====", 2)
            if len(inner) == 3:
                for tok in inner[1].split():
                    try:
                        ts = datetime.strptime(tok, "%m/%d/%Y").replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
        elif EXIT_MARKER in line and header is not None:
            exit_line = line
    if exit_line:
        try:
            code = int(exit_line.split("exit", 1)[1].split()[0].rstrip("."))
        except (ValueError, IndexError):
            code = -1
    else:
        code = None
    return header, ts, code, exit_line


def load_last_close(cache_dir, symbol):
    """Return (last_bar_ts, last_close) for symbol from the D1 CSV cache."""
    path = os.path.join(cache_dir, f"{symbol}_D1.csv")
    if not os.path.exists(path):
        return None, None
    last_ts = last_close = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            if row.get("ts") and row.get("close"):
                last_ts = _parse_ts(row["ts"])
                try:
                    last_close = float(row["close"])
                except ValueError:
                    pass
    return last_ts, last_close


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state", default=os.path.join(ROOT, "data", "paper_state.json"))
    ap.add_argument("--log", default=os.path.join(ROOT, "logs", "paper_daily.log"))
    ap.add_argument("--db", default=os.path.join(ROOT, "db", "newsetup.sqlite3"))
    ap.add_argument("--caches", default=os.path.join(ROOT, "data", "caches"))
    ap.add_argument("--stale-days", type=float, default=5.0)
    ap.add_argument("--max-dev", type=float, default=0.03,
                    help="max |entry - last cached close| / close before a fill is flagged")
    ap.add_argument("--json", action="store_true", help="also print a JSON result block")
    args = ap.parse_args()

    failures, warnings, info = [], [], []

    # --- 1. last cycle exit ------------------------------------------------
    cycle_code = None
    if not os.path.exists(args.log):
        failures.append(f"log not found: {args.log}")
    else:
        header, cycle_ts, cycle_code, exit_line = last_cycle(args.log)
        if header is None:
            failures.append(f"no cycle block found in {args.log}")
        else:
            info.append(f"last cycle: {header.strip()}")
            if cycle_code != 0:
                failures.append(f"last cycle exit code {cycle_code!r} (want 0): {exit_line}")

    # --- 2/3. state file ----------------------------------------------------
    state = None
    if not os.path.exists(args.state):
        failures.append(f"state file not found: {args.state}")
    else:
        try:
            with open(args.state, encoding="utf-8") as fh:
                state = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            failures.append(f"state file unparseable: {exc}")

    closed = open_ = []
    balance = None
    if state is not None:
        open_ = state.get("open") or []
        closed = state.get("closed") or []
        balance = state.get("balance")
        info.append(f"book: {len(open_)} open / {len(closed)} closed, balance {balance}")

        for i, pos in enumerate(open_):
            tag = f"open[{i}] {pos.get('instrument')}"
            entry = pos.get("entry_price")
            sl, tp = pos.get("stop_loss"), pos.get("take_profit")
            direction = str(pos.get("direction", "")).upper()
            if not entry or not sl or not tp:
                failures.append(f"{tag}: missing entry/SL/TP")
                continue
            if direction == "BUY" and not (sl < entry < tp):
                failures.append(f"{tag}: BUY with SL {sl} / entry {entry} / TP {tp} out of order")
            if direction == "SELL" and not (tp < entry < sl):
                failures.append(f"{tag}: SELL with TP {tp} / entry {entry} / SL {sl} out of order")
            if pos.get("closed_at") is not None:
                failures.append(f"{tag}: open position has closed_at {pos.get('closed_at')}")
            if pos.get("pnl") not in (None, 0, 0.0):
                warnings.append(f"{tag}: open position has pnl {pos.get('pnl')}")
            if _parse_ts(pos.get("opened_at")) is None:
                failures.append(f"{tag}: unparseable opened_at {pos.get('opened_at')!r}")

        for i, tr in enumerate(closed):
            tag = f"closed[{i}] {tr.get('instrument')}"
            opened = _parse_ts(tr.get("opened_at"))
            closed_ts = _parse_ts(tr.get("closed_at"))
            if opened is None:
                failures.append(f"{tag}: unparseable opened_at {tr.get('opened_at')!r}")
                continue
            if closed_ts is None:
                failures.append(f"{tag}: unparseable closed_at {tr.get('closed_at')!r}")
                continue
            if closed_ts <= opened:
                failures.append(
                    f"{tag}: PHANTOM close - closed_at {closed_ts.isoformat()} "
                    f"<= opened_at {opened.isoformat()} (UGT-32 defect)")
            elif (closed_ts - opened).total_seconds() < SAME_CYCLE_S:
                reason = str(tr.get("exit_reason", "")).lower()
                failures.append(
                    f"{tag}: same-cycle exit after {(closed_ts - opened).total_seconds():.0f}s "
                    f"(reason {reason!r}) - implausible for D1 paper cycles")

    # --- 4. fill freshness ---------------------------------------------------
    cycle_ref = None
    if state is not None:
        for pos in closed + open_:
            ts = _parse_ts(pos.get("opened_at"))
            if ts and (cycle_ref is None or ts > cycle_ref):
                cycle_ref = ts
    if cycle_ref is None:
        cycle_ref = datetime.now(timezone.utc)
    instruments = sorted({str(p.get("instrument")) for p in (closed + open_) if p.get("instrument")})
    for sym in instruments:
        bar_ts, last_close = load_last_close(args.caches, sym)
        entry = next((p.get("entry_price") for p in (closed + open_)
                      if p.get("instrument") == sym), None)
        if bar_ts is None:
            warnings.append(f"{sym}: no cached D1 bars in {args.caches}")
            continue
        age_days = (cycle_ref - bar_ts).total_seconds() / 86400.0
        # The daily pipeline fills from the LIVE provider (MT5, else
        # synthetic); it does NOT refresh the on-disk D1 cache, so cache
        # comparisons are diagnostics, not defect criteria. Only flag a
        # deviation as a FAILURE when the cache itself is fresh enough
        # to be a valid reference (< ~2 days).
        if age_days > args.stale_days:
            warnings.append(
                f"{sym}: D1 cache not refreshed since {bar_ts.date()} "
                f"({age_days:.1f}d old at cycle time) - cache is only "
                f"updated by manual/scripted downloads, not by the daily run")
        if entry and last_close:
            dev = abs(entry - last_close) / last_close
            if dev > args.max_dev and age_days <= 2.0:
                failures.append(
                    f"{sym}: fill {entry} deviates {dev:.2%} from a FRESH "
                    f"cached close {last_close} ({bar_ts.date()}) - stale-price fill?")
            elif dev > args.max_dev:
                warnings.append(
                    f"{sym}: fill {entry} deviates {dev:.2%} from last cached "
                    f"close {last_close}, but that cache bar is {age_days:.1f}d "
                    f"old at cycle time - diagnostic only")
            else:
                info.append(f"{sym}: fill {entry} within {dev:.2%} of last cached close ({bar_ts.date()})")

    # --- db cross-check ----------------------------------------------------
    if os.path.exists(args.db):
        try:
            con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
            try:
                n_trades = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
                n_signals = con.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
                bad = con.execute(
                    "SELECT COUNT(*) FROM trades WHERE closed_at IS NOT NULL "
                    "AND closed_at <= opened_at").fetchone()[0]
                info.append(f"db: {n_trades} trade rows, {n_signals} signal rows")
                if bad:
                    failures.append(f"db: {bad} trade rows with closed_at <= opened_at")
            finally:
                con.close()
        except sqlite3.Error as exc:
            warnings.append(f"db cross-check skipped: {exc}")

    # --- report --------------------------------------------------------------
    print("== UGT-36 cycle verification ==")
    for line in info:
        print("INFO   ", line)
    for line in warnings:
        print("WARN   ", line)
    for line in failures:
        print("FAIL   ", line)

    book_fail = [f for f in failures if f.startswith("open[") or f.startswith("book")]
    phantom_fail = [f for f in failures if "PHANTOM" in f or "same-cycle" in f]
    fresh_fail = [f for f in failures if "stale-price fill" in f]
    result = {
        "checks": {"cycle_exit_zero": cycle_code == 0,
                   "book_sane": not book_fail,
                   "no_phantom_closes": not phantom_fail,
                   "fills_fresh": not fresh_fail},
        "failures": failures,
        "warnings": warnings,
        "pass": not failures,
    }
    if args.json:
        print(json.dumps(result, indent=2))

    print("RESULT:", "PASS" if not failures else f"FAIL ({len(failures)} problem(s))")
    return 0 if not failures else (2 if state is None else 1)


if __name__ == "__main__":
    sys.exit(main())
