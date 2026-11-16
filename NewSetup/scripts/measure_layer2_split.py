"""Re-measure the layer-1/layer-2 agreement split (UGT-17/19 item 4).

UGT-14 measured the OLD one-size gate (RSI reversal extreme + trend
continuation) at raw-signal time: both-agree 11.0%, neither 39.0% of
7,149 signals. This script measures the same split under the reworked
THESIS-AWARE gate (signals/layer2_confirmation.py):

  reversion    : RSI extreme matching direction + pullback trend context
  continuation : RSI momentum (midline side) + trend carrying the move
  event        : RSI headroom + fresh-trigger component

It replays every layer-1 raw signal the rebuilt stack generates on the
cached D1 history (PRICE triggers, all symbols) plus the EVENT triggers
in the five playbook windows, computes both components at signal time,
and reports the both-agree / single / neither split per thesis and
overall, plus the analogous OLD-definition split for comparison.

Usage (from NewSetup/, C:/Python314/python.exe):

    python -m scripts.measure_layer2_split
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.event_backtests import PLAYBOOK_WINDOWS, _symbol_owner, replay_price_signals  # noqa: E402
from data.bar_cache import BarCache, CACHE_DIR                               # noqa: E402
from data.historical_events import load_all_events, replay_event_signals     # noqa: E402
from newsetup.config import ROOT, load_inefficiencies, load_settings         # noqa: E402
from newsetup.indicators import rsi as rsi_calc, sma as sma_calc             # noqa: E402
from newsetup.models import PriceBar                                        # noqa: E402

log = logging.getLogger("newsetup.layer2_split")

RESULTS_JSON = os.path.join(ROOT, "backtest", "results", "layer2_split.json")
RSI_MIDLINE = 50.0


def components(raw, bars_by_symbol, cfg):
    """(new_rsi_ok, new_second_ok, old_rsi_ok, old_sma_ok) at signal time."""
    bars = bars_by_symbol.get(raw.instrument)
    if not bars:
        return None
    idx = None
    for i, b in enumerate(bars):
        if b.ts >= raw.ts:
            idx = i
            break
    if idx is None or idx < cfg["sma_slow"]:
        return None
    window = [b.close for b in bars[:idx + 1]]
    r = rsi_calc(window, cfg["rsi_period"])
    fast = sma_calc(window, cfg["sma_fast"])
    slow = sma_calc(window, cfg["sma_slow"])
    if r is None or fast is None or slow is None:
        return None
    buy, sell = raw.direction == "BUY", raw.direction == "SELL"
    thesis = raw.thesis or "continuation"

    # reworked gate
    if thesis == "reversion":
        new_rsi = (buy and r <= cfg["rsi_oversold"]) or (sell and r >= cfg["rsi_overbought"])
        new_second = (buy and fast < slow) or (sell and fast > slow)
    elif thesis == "event":
        new_rsi = (buy and r < cfg["rsi_overbought"]) or (sell and r > cfg["rsi_oversold"])
        new_second = True
    else:  # continuation
        new_rsi = (buy and r >= RSI_MIDLINE) or (sell and r <= RSI_MIDLINE)
        new_second = (buy and fast > slow) or (sell and fast < slow)

    # old one-size gate (UGT-14 definition, for comparison)
    old_rsi = (buy and r <= cfg["rsi_oversold"]) or (sell and r >= cfg["rsi_overbought"])
    old_sma = (buy and fast > slow) or (sell and fast < slow)
    return new_rsi, new_second, old_rsi, old_sma


def classify(rsi_ok, second_ok):
    if rsi_ok and second_ok:
        return "both_agree"
    if rsi_ok or second_ok:
        return "rsi_only" if rsi_ok else "sma_only"
    return "neither"


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    cfg = settings["layer2"]
    ineffs = load_inefficiencies()
    cache = BarCache(CACHE_DIR, connect=False)

    price_data: dict[str, list[PriceBar]] = {}
    signals = []
    pseudo = 1000
    for symbol in cache.cached_symbols():
        bars = cache.load(symbol)
        if not bars or len(bars) < 300:
            continue
        owner = _symbol_owner(ineffs, symbol)
        if owner is not None:
            iid, iname = owner.id, owner.name
        else:
            pseudo += 1
            iid, iname = pseudo, symbol
        price_data[symbol] = bars
        signals.extend(replay_price_signals(bars, iid, iname, symbol))
    signals.sort(key=lambda s: s.ts)
    log.info("price replay: %d raw signals", len(signals))

    events = load_all_events()
    event_sigs = []
    for wname, (s, e, _d) in PLAYBOOK_WINDOWS.items():
        start = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(e, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        wevents = [ev for ev in events if start <= ev.ts <= end]
        event_sigs.extend(replay_event_signals(
            wevents, ineffs, available_symbols=set(price_data)))
    log.info("event replay: %d raw signals in playbook windows", len(event_sigs))

    new_counts: dict[str, dict] = {}
    old_counts: dict[str, dict] = {}
    totals = {"price": 0, "event": 0, "unpriced": 0}

    for raw in signals + event_sigs:
        comp = components(raw, price_data, cfg)
        if comp is None:
            totals["unpriced"] += 1
            continue
        thesis = raw.thesis or "continuation"
        totals["price" if raw.trigger_type == "PRICE" else "event"] += 1
        key = classify(comp[0], comp[1])
        new_counts.setdefault(thesis, {}).setdefault(key, 0)
        new_counts[thesis][key] = new_counts[thesis][key] + 1
        old_key = classify(comp[2], comp[3])
        old_counts.setdefault(thesis, {}).setdefault(old_key, 0)
        old_counts[thesis][old_key] = old_counts[thesis][old_key] + 1

    def pct_table(counts):
        out = {}
        grand = {}
        for thesis, c in counts.items():
            total = sum(c.values())
            out[thesis] = {k: {"count": v, "pct": round(100 * v / total, 1)}
                           for k, v in c.items()} | {"n": total}
            for k, v in c.items():
                grand[k] = grand.get(k, 0) + v
        gt = sum(grand.values())
        out["overall"] = {k: {"count": v, "pct": round(100 * v / gt, 1)}
                          for k, v in grand.items()} | {"n": gt}
        return out

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": totals,
        "new_gate_split": pct_table(new_counts),
        "old_gate_split_same_signals": pct_table(old_counts),
        "ugt14_baseline": {"both_agree_pct": 11.0, "neither_pct": 39.0,
                           "n": 7149},
    }
    os.makedirs(os.path.dirname(RESULTS_JSON), exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({"new_gate_split": report["new_gate_split"],
                      "old_gate_split_same_signals":
                          report["old_gate_split_same_signals"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
