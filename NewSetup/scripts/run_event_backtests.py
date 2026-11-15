"""Run the playbook 5.2 event-window backtests on real cached bars.

Usage (from the repo root; requires data/caches/ populated, see
scripts/download_history.py):

    C:/Python314/python.exe NewSetup/scripts/run_event_backtests.py
    C:/Python314/python.exe NewSetup/scripts/run_event_backtests.py \
        --windows covid_2020 russia_sanctions_2022
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.bar_cache import BarCache                     # noqa: E402
from backtest.event_backtests import PLAYBOOK_WINDOWS    # noqa: E402
from backtest.event_backtests import run_all_windows    # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", nargs="*", default=None,
                        choices=list(PLAYBOOK_WINDOWS),
                        help="subset of playbook windows (default: all)")
    parser.add_argument("--balance", type=float, default=10000.0)
    args = parser.parse_args()

    cache = BarCache(connect=False)          # read from the CSV cache
    cached = cache.cached_symbols()
    if not cached:
        print("ERROR: data/caches/ is empty; run scripts/download_history.py first.")
        return 1
    print(f"running windows {args.windows or 'ALL'} on {len(cached)} cached symbols")

    reports = run_all_windows(cache, windows=args.windows,
                              starting_balance=args.balance)
    for r in reports:
        m = r["metrics"]
        print(f"{r['window']}: trades={m.get('total_trades', 0)} "
              f"win%={m.get('win_rate_pct', 0):.1f} "
              f"PF={m.get('profit_factor', 0):.2f} "
              f"sharpe={m.get('sharpe', 0):.2f} "
              f"DD%={m.get('max_drawdown_pct', 0):.2f} "
              f"ret%={m.get('total_return_pct', 0):.2f} "
              f"accept={'PASS' if r['acceptance_passed'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
