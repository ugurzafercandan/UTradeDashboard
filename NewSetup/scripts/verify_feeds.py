"""Verify the live data feeds required by playbook sections 2.2/2.3.

Checks, in order:
1. MT5 package + terminal connection and account info (execution/mt5_bridge.py)
2. Symbol availability for every mapped playbook instrument
   (config/instruments.yaml + config/broker_map.yaml)
3. GDELT DOC 2.0 live query with graceful fallback (data/gdelt_monitor.py)

Run from the repo root:  C:/Python314/python.exe NewSetup/scripts/verify_feeds.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from newsetup.config import load_broker_map, load_instruments  # noqa: E402
from data.gdelt_monitor import GDELTMonitor                   # noqa: E402
from execution.mt5_bridge import MT5Bridge                    # noqa: E402


def main() -> int:
    report: dict = {}

    # 1) MT5 terminal ------------------------------------------------------
    bridge = MT5Bridge()
    report["mt5_available"] = bridge.available
    if bridge.available:
        acct = bridge.get_account_info()
        report["account"] = {
            "balance": acct.balance, "equity": acct.equity,
            "margin_used": acct.margin_used, "open_positions": acct.open_positions,
            "currency": acct.currency,
        }
        print(f"MT5: connected; account equity {acct.equity:.2f} "
              f"{acct.currency}, {acct.open_positions} open positions")
    else:
        print("MT5: NOT AVAILABLE")

    # 2) mapped instrument availability ------------------------------------
    broker_map = load_broker_map()
    instruments = load_instruments()
    mapped = sorted({s for group in instruments.values()
                     if isinstance(group, list) for s in group}
                    | set(broker_map))
    availability: dict[str, str] = {}
    if bridge.available:
        for symbol in mapped:
            broker_symbol = broker_map.get(symbol, symbol)
            if bridge.symbol_available(broker_symbol):
                availability[symbol] = f"OK ({broker_symbol})"
            elif symbol in broker_map:
                availability[symbol] = f"MAPPED-NOT-LISTED ({broker_symbol})"
            else:
                availability[symbol] = "NOT AVAILABLE"
    report["symbols_checked"] = len(mapped)
    report["symbol_availability"] = availability
    ok = sum(1 for v in availability.values() if v.startswith("OK"))
    print(f"Symbols: {ok}/{len(availability)} available "
          f"({len(mapped)} playbook symbols checked)")
    missing = [s for s, v in availability.items() if not v.startswith("OK")]
    if missing:
        print("  unavailable:", ", ".join(missing))

    # 3) GDELT live ----------------------------------------------------------
    gdelt = GDELTMonitor(offline=False)
    events = gdelt.get_events(since_hours=24)
    live = [e for e in events if e.source == "gdelt"]
    report["gdelt_events_live"] = len(live)
    report["gdelt_events_total"] = len(events)
    report["gdelt_live_ok"] = bool(live)
    print(f"GDELT: {len(live)} live events (fallback fixtures used: "
          f"{len(events) - len(live)})")
    for ev in live[:3]:
        print(f"  - {ev.headline[:80]}")

    print(json.dumps(report, indent=2, default=str))
    return 0 if (bridge.available and report.get("gdelt_live_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
