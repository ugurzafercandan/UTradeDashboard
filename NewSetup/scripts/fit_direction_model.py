"""Fit the per-inefficiency direction model (UGT-17/19 item 3).

Replaces the global mean-reversion mapping of price-spike triggers
(down-spike -> BUY, up-spike -> SELL) with a per-inefficiency decision
between REVERSION and CONTINUATION, decided from data:

For every cached symbol, replay the layer-1 PRICE trigger moments (same
thresholds/cooldown as the scanner). At each trigger, measure the forward
10-bar (trading-day) return. Under REVERSION the mapped position is
opposite the triggering move; under CONTINUATION it is with the move.
Per inefficiency, compute both mappings' expectancy and profit factor
across all trigger moments on all its symbols, then decide:

  n >= min_triggers and the winner's expectancy beats the loser by
  more than the tie margin -> winner; otherwise inherit the category
  aggregate; category falls back to the global aggregate.

To keep the untouched holdout (2025-01-01..) and the walk-forward test
years honest, the fit window ends at --end (default 2024-12-31):
in-sample trigger evidence only. The inefficiency/category/global
decision is frozen into config/direction_model.yaml and consumed by the
live scanner and the backtest replay (newsetup/direction.py).

Usage (from NewSetup/, C:/Python314/python.exe):

    python -m scripts.fit_direction_model [--end 2024-12-31]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.event_backtests import PLAYBOOK_WINDOWS  # unused; kept for CLI parity  # noqa: F401,E501
from data.bar_cache import BarCache, CACHE_DIR                                    # noqa: E402
from newsetup.config import ROOT, load_inefficiencies, load_settings              # noqa: E402

log = logging.getLogger("newsetup.fit_direction")

OUT_YAML = os.path.join(ROOT, "config", "direction_model.yaml")
FORWARD_BARS = 10          # playbook avg trade duration band 1-14 days
MIN_TRIGGERS = 30
TIE_MARGIN = 0.2           # % expectancy margin required to win (expectancy_pct is in %)
SIGNIF_Z = 1.645           # one-sided 95%: |expectancy| must beat z*se


def _pct(closes, lookback):
    if len(closes) < lookback + 1 or closes[-lookback - 1] == 0:
        return None
    return (closes[-1] / closes[-lookback - 1] - 1.0) * 100.0


def trigger_moments(bars, settings, cooldown=5):
    """(bar_index, move_direction) at layer-1 PRICE trigger moments."""
    cfg = settings["layer1"]
    spike_24h = float(cfg["price_spike_pct_24h"])
    spike_30d = float(cfg["price_spike_pct_30d"])
    closes = [b.close for b in bars]
    out = []
    last = -10 ** 9
    for i in range(1, len(bars)):
        chg_24h = _pct(closes[:i + 1], 1)
        chg_30d = _pct(closes[:i + 1], min(30, i))
        move = None
        if chg_24h is not None and abs(chg_24h) >= spike_24h:
            move = "UP" if chg_24h > 0 else "DOWN"
        elif chg_30d is not None and abs(chg_30d) >= spike_30d:
            move = "UP" if chg_30d > 0 else "DOWN"
        if move is None or i - last < cooldown:
            continue
        out.append((i, move))
        last = i
    return out


def pnl_stats(pnls):
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
    exp = sum(pnls) / len(pnls) if pnls else 0.0
    wins = sum(1 for p in pnls if p > 0)
    std = (sum((p - exp) ** 2 for p in pnls) / len(pnls)) ** 0.5 if pnls else 0.0
    se = std / (len(pnls) ** 0.5) if pnls else 0.0
    return {"n": len(pnls), "expectancy_pct": round(exp, 4),
            "se_pct": round(se, 4),
            "profit_factor": round(pf, 3),
            "win_rate_pct": round(100 * wins / len(pnls), 1) if pnls else 0.0}


def decide(pnls_cont, min_n=MIN_TRIGGERS):
    """Significance-gated direction decision.

    pnl_reversion is exactly -pnl_continuation for the same trigger set,
    so the decision reduces to the sign of the continuation expectancy.
    Requires both a practical margin (> TIE_MARGIN %) and statistical
    significance (|exp| > SIGNIF_Z * se); otherwise returns None (inherit
    category -> global), guarding against noise-fitting on small n.
    """
    stats = pnl_stats(pnls_cont)
    if stats["n"] < min_n:
        return None, stats
    exp, se = stats["expectancy_pct"], stats["se_pct"]
    if abs(exp) <= TIE_MARGIN or abs(exp) <= SIGNIF_Z * se:
        return None, stats
    return ("continuation" if exp > 0 else "reversion"), stats


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", default="2024-12-31",
                    help="fit window end (inclusive); holdout stays untouched")
    args = ap.parse_args(argv)
    end = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    settings = load_settings()
    ineffs = load_inefficiencies()
    cache = BarCache(CACHE_DIR, connect=False)
    symbols = cache.cached_symbols()
    end_idx = None

    # trigger evidence: ineff -> mapping -> [pnl %]
    per_ineff = defaultdict(lambda: defaultdict(list))
    symbol_owner = {}
    pseudo_id = 1000
    for symbol in symbols:
        bars = [b for b in cache.load(symbol) if b.ts <= end]
        if len(bars) < 320:
            continue
        for ineff in ineffs:
            if symbol in ineff.tradeable_symbols():
                symbol_owner[symbol] = ineff.id
                break
        else:
            pseudo_id += 1
            symbol_owner[symbol] = -pseudo_id     # unmapped: global pool only

    for symbol in symbols:
        bars = [b for b in cache.load(symbol) if b.ts <= end]
        if len(bars) < 320:
            continue
        closes = [b.close for b in bars]
        for i, move in trigger_moments(bars, settings):
            if i + FORWARD_BARS >= len(closes):
                continue
            fwd = (closes[i + FORWARD_BARS] / closes[i] - 1.0) * 100.0
            sign = 1.0 if move == "UP" else -1.0
            pnl_cont = sign * fwd           # continuation: with the move
            pnl_rev = -sign * fwd          # reversion: against the move
            owner = symbol_owner.get(symbol)
            per_ineff[owner]["continuation"].append(pnl_cont)
            per_ineff[owner]["reversion"].append(pnl_rev)

    # decide per inefficiency
    global_pnls = {"continuation": [], "reversion": []}
    for owner, mapping in per_ineff.items():
        if owner is None or owner < 0:
            continue
        for m, pnls in mapping.items():
            global_pnls[m].extend(pnls)
    global_stats = {m: pnl_stats(p) for m, p in global_pnls.items()}
    global_decision, _ = decide(global_pnls["continuation"])
    if global_decision is None:
        # documented default when data cannot distinguish the two mappings
        global_decision = "continuation"

    per_ineff_stats = {}
    decisions = {}
    for ineff in ineffs:
        pnls = per_ineff.get(ineff.id)
        stats = {m: pnl_stats(p) for m, p in pnls.items()} if pnls else {}
        per_ineff_stats[ineff.id] = stats
        d, _ = decide(pnls["continuation"]) if pnls else (None, None)
        decisions[ineff.id] = d      # None -> inherit category -> global

    # category aggregates for fallback
    cat_pnls = defaultdict(lambda: {"continuation": [], "reversion": []})
    for ineff in ineffs:
        for m in ("continuation", "reversion"):
            cat_pnls[ineff.category][m].extend(
                per_ineff.get(ineff.id, {}).get(m, []))
    cat_decision = {}
    for cat, mapping in cat_pnls.items():
        d, _ = decide(mapping["continuation"])
        cat_decision[cat] = d

    resolved = {}
    resolved_from = {}
    for ineff in ineffs:
        if decisions.get(ineff.id):
            resolved[ineff.id] = decisions[ineff.id]
            resolved_from[ineff.id] = "inefficiency"
        elif cat_decision.get(ineff.category):
            resolved[ineff.id] = cat_decision[ineff.category]
            resolved_from[ineff.id] = "category"
        else:
            resolved[ineff.id] = global_decision
            resolved_from[ineff.id] = "global"

    doc = {
        "_doc": ("Per-inefficiency price-trigger direction model (UGT-17/19 "
                 "item 3). Generated by scripts/fit_direction_model.py from "
                 f"D1 history through {args.end} (holdout untouched). "
                 "direction: reversion = fade the spike; continuation = go "
                 "with the move. Stats are % pnl over a 10-trading-day "
                 "forward horizon."),
        "default": global_decision,
        "fit_window_end": args.end,
        "forward_bars": FORWARD_BARS,
        "min_triggers": MIN_TRIGGERS,
        "global_stats": global_stats,
        "inefficiencies": {
            ineff.id: {
                "name": ineff.name,
                "category": ineff.category,
                "direction": resolved[ineff.id],
                "decided_from": resolved_from[ineff.id],
                "stats": per_ineff_stats.get(ineff.id) or {},
            } for ineff in ineffs
        },
    }
    with open(OUT_YAML, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False, default_flow_style=False)
    n_revert = sum(1 for v in resolved.values() if v == "reversion")
    n_cont = len(resolved) - n_revert
    n_global = global_stats["continuation"]["n"]
    log.info("direction model: %d continuation / %d reversion "
             "(global %s; %d trigger samples)", n_cont, n_revert,
             global_decision, n_global)
    print(yaml.safe_dump({"default": global_decision,
                          "continuation": n_cont, "reversion": n_revert,
                          "global_stats": global_stats}, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
