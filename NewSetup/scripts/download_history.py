"""Download real D1 history from the MT5 terminal into data/caches/.

Usage (from the repo root, with the MT5 terminal running):

    C:/Python314/python.exe NewSetup/scripts/download_history.py
    C:/Python314/python.exe NewSetup/scripts/download_history.py --years 5

Downloads every playbook symbol that has a verified broker mapping
(config/broker_map.yaml) and stores CSVs under NewSetup/data/caches/.
Symbols the broker does not list are reported and skipped.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from newsetup.config import load_broker_map            # noqa: E402
from data.bar_cache import BarCache                     # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=float, default=4.0,
                        help="years of D1 bars to fetch (default 4)")
    parser.add_argument("--symbols", nargs="*", default=None,
                        help="subset of playbook symbols (default: all mapped)")
    args = parser.parse_args()

    broker_map = load_broker_map()
    symbols = args.symbols if args.symbols else sorted(broker_map)
    cache = BarCache()
    if not cache.available:
        print("ERROR: MT5 terminal not available; cannot download.")
        return 1

    print(f"downloading {len(symbols)} symbols, {args.years}y of D1 bars")
    results = cache.download_all(symbols, years=args.years)
    failed = {s: n for s, n in results.items() if n == 0}
    total = sum(results.values())
    print(f"done: {len(results) - len(failed)}/{len(results)} symbols, "
          f"{total} bars total")
    for symbol, count in sorted(results.items()):
        print(f"  {symbol:12s} {count:5d} bars")
    if failed:
        print("no data:", ", ".join(sorted(failed)))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
