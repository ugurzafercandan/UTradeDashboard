"""UGT-14 evaluation stage: A/B adoption test + final acceptance runs.

Reads the walk-forward tuning output (backtest/results/wf_tuning.json),
then:

1. A/B baseline-vs-tuned on the UNTOUCHED holdout (2025-01-01..cache end)
   via backtest/ab_testing.py, adopting strictly per its own rules.
2. Re-runs the 5 playbook event windows with the tuned candidate and the
   UGT-7 inefficiency mapping active (PRICE-trigger replay; GDELT has no
   historical coverage - stated limitation).
3. Runs the holdout acceptance with baseline vs tuned parameters.
4. Structural diagnostics for the report: layer-1 signal density per
   window, layer-2 confirmation tension (RSI vs SMA), layer-1 threshold
   sensitivity, and a trigger-direction (momentum vs reversion) probe.

Usage (from NewSetup/, C:/Python314/python.exe):

    python -m backtest.wf_evaluate
"""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from newsetup.config import ROOT, load_settings
from newsetup.indicators import rsi as rsi_calc
from newsetup.indicators import sma as sma_calc
from newsetup.models import PriceBar, RawSignal

from data.bar_cache import BarCache, CACHE_DIR
from .ab_testing import ABTestFramework, ABVariant
from .event_backtests import PLAYBOOK_WINDOWS, run_event_backtest
from .runner import BacktestRunner
from .tune_walk_forward import (HOLDOUT_START, TUNING_JSON, build_universe,
                                overrides_from_combo, slice_run,
                                default_folds, param_grid)

log = logging.getLogger("newsetup.wf_evaluate")

RESULTS_DIR = os.path.join(ROOT, "backtest", "results")
EVAL_JSON = os.path.join(RESULTS_DIR, "wf_evaluation.json")
EVAL_MD = os.path.join(RESULTS_DIR, "wf_evaluation.md")

HOLDOUT_END = "2026-11-13"      # cache end (Pepperstone D1)


# ------------------------------------------------------------------ replay
def replay_momentum_signals(bars: list[PriceBar],
                            inefficiency_id: int,
                            inefficiency_name: str,
                            symbol: str,
                            settings: Optional[dict] = None,
                            cooldown: int = 5) -> list[RawSignal]:
    """Layer-1 PRICE replay with CONTINUATION direction (diagnostic only).

    Opposite of event_backtests.replay_price_signals: a -spike move emits
    SELL (follow the breakdown), +spike emits BUY, 30d continuation in
    the move direction. Not an adopted variant - diagnostic evidence for
    the structural report.
    """
    settings = settings or load_settings()
    cfg = settings["layer1"]
    spike_24h = float(cfg["price_spike_pct_24h"])
    spike_30d = float(cfg["price_spike_pct_30d"])
    signals: list[RawSignal] = []
    last_idx = -10 ** 9
    closes = [b.close for b in bars]
    for i in range(1, len(bars)):
        bar = bars[i]
        window = closes[:i + 1]
        chg_24h = _pct(window, 1)
        chg_30d = _pct(window, min(30, i))
        direction = None
        chg = None
        if chg_24h is not None and chg_24h <= -spike_24h:
            direction, chg = "SELL", chg_24h
        elif chg_24h is not None and chg_24h >= spike_24h:
            direction, chg = "BUY", chg_24h
        elif chg_30d is not None and abs(chg_30d) >= spike_30d:
            direction = "BUY" if chg_30d > 0 else "SELL"
            chg = chg_30d
        if direction is None or i - last_idx < cooldown:
            continue
        signals.append(RawSignal(
            inefficiency_id=inefficiency_id,
            inefficiency_name=inefficiency_name,
            instrument=symbol,
            direction=direction,
            trigger_type="PRICE_MOMENTUM",
            trigger_description=f"{symbol} momentum move {chg:+.2f}%",
            confidence=0.6,
            ts=bar.ts,
        ))
        last_idx = i
    return signals


def _pct(closes: list[float], lookback: int) -> Optional[float]:
    if len(closes) < lookback + 1 or closes[-lookback - 1] == 0:
        return None
    return (closes[-1] / closes[-lookback - 1] - 1.0) * 100.0


# ------------------------------------------------------------------ stages
def load_tuning() -> dict:
    with open(TUNING_JSON, encoding="utf-8") as f:
        return json.load(f)


def ab_on_holdout(price_data, signals, tuned_overrides,
                  folds: int = 4) -> dict:
    """A/B baseline vs tuned strictly on the untouched holdout."""
    from .tune_walk_forward import _ts
    from datetime import timedelta
    lo, hi = _ts(HOLDOUT_START), _ts(HOLDOUT_END)
    warm_lo = lo - timedelta(days=400)
    data = {}
    for symbol, bars in price_data.items():
        selected = [b for b in bars if warm_lo <= b.ts <= hi]
        if selected:
            data[symbol] = selected
    holdout_signals = [s for s in signals if lo <= s.ts <= hi]
    framework = ABTestFramework(BacktestRunner())
    result = framework.compare(
        ABVariant(name="baseline", settings_overrides={}),
        ABVariant(name="tuned", settings_overrides=tuned_overrides),
        price_data=data,
        raw_signals=holdout_signals,
        folds=folds,
    )
    return result.to_dict()


def holdout_acceptance(price_data, signals, tuned_overrides) -> dict:
    """Baseline vs tuned full-run acceptance on the untouched holdout."""
    from .tune_walk_forward import _ts
    from datetime import timedelta
    lo, hi = _ts(HOLDOUT_START), _ts(HOLDOUT_END)
    warm_lo = lo - timedelta(days=400)
    data = {}
    for symbol, bars in price_data.items():
        selected = [b for b in bars if warm_lo <= b.ts <= hi]
        if selected:
            data[symbol] = selected
    holdout_signals = [s for s in signals if lo <= s.ts <= hi]
    out = {"window": f"{HOLDOUT_START}..{HOLDOUT_END}",
           "raw_signals": len(holdout_signals)}
    for name, overrides in (("baseline", {}), ("tuned", tuned_overrides)):
        result = BacktestRunner(settings=overrides).run(data, holdout_signals)
        out[name] = {"metrics": result.metrics,
                     "acceptance_passed": result.acceptance_passed,
                     "acceptance_failures": result.acceptance_failures}
    return out


def run_tuned_windows(cache: BarCache, tuned_overrides) -> list[dict]:
    """5 playbook windows re-run with the tuned candidate overrides."""
    reports = []
    for window in PLAYBOOK_WINDOWS:
        report = run_event_backtest(window, cache,
                                    settings_overrides=tuned_overrides)
        reports.append(report)
        path = os.path.join(RESULTS_DIR, f"realdata_tuned_{window}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
    return reports


# ------------------------------------------------------------------ diagnose
def confirmation_tension(signals: list[RawSignal],
                         price_data,
                         settings: Optional[dict] = None) -> dict:
    """RSI-vs-SMA agreement split at raw-signal time (layer-2 tension)."""
    settings = settings or load_settings()
    cfg = settings["layer2"]
    counts = {"both_agree": 0, "rsi_only": 0, "sma_only": 0, "neither": 0}
    sorted_bars = {s: sorted(bars, key=lambda b: b.ts)
                   for s, bars in price_data.items()}
    series = {s: [b.close for b in bars] for s, bars in sorted_bars.items()}
    for sig in signals:
        bars = sorted_bars.get(sig.instrument)
        if not bars:
            continue
        idx = _index_at(sig.ts, bars)
        if idx is None or idx < cfg["sma_slow"]:
            continue
        window = series[sig.instrument][:idx + 1]
        r = rsi_calc(window, cfg["rsi_period"])
        fast = sma_calc(window, cfg["sma_fast"])
        slow = sma_calc(window, cfg["sma_slow"])
        if r is None or fast is None or slow is None:
            continue
        rsi_ok = (sig.direction == "BUY" and r <= cfg["rsi_oversold"]) or \
                 (sig.direction == "SELL" and r >= cfg["rsi_overbought"])
        sma_ok = (sig.direction == "BUY" and fast > slow) or \
                 (sig.direction == "SELL" and fast < slow)
        key = ("both_agree" if rsi_ok and sma_ok else
               "rsi_only" if rsi_ok else
               "sma_only" if sma_ok else "neither")
        counts[key] += 1
    total = sum(counts.values())
    return {k: {"count": v, "pct": round(100.0 * v / total, 1) if total else 0.0}
            for k, v in counts.items()} | {"evaluated_signals": total}


def _index_at(ts, bars) -> Optional[int]:
    for i, bar in enumerate(bars):
        if bar.ts >= ts:
            return i
    return None


def signal_density(cache: BarCache) -> list[dict]:
    """Raw replay signals per playbook window (density vs min_trades gate)."""
    rows = []
    for window, (start, end, desc) in PLAYBOOK_WINDOWS.items():
        report = json.load(open(
            os.path.join(RESULTS_DIR, f"realdata_{window}.json"),
            encoding="utf-8")) if os.path.exists(
            os.path.join(RESULTS_DIR, f"realdata_{window}.json")) else None
        rows.append({
            "window": window,
            "start": start,
            "end": end,
            "raw_signals": report["raw_signals"] if report else None,
            "traded": report["metrics"]["total_trades"] if report else None,
        })
    return rows


def layer1_threshold_sensitivity(price_data, tuned_overrides) -> list[dict]:
    """Diagnostic: lower layer-1 spike thresholds -> signal/trade counts.

    NOT part of the sanctioned search space (issue UGT-14 lists layer-2
    min_score, RSI/SMA windows, ATR SL/TP, heat/sector caps); reported as
    evidence for what would have to change, never adopted.
    """
    rows = []
    for spike_24h, spike_30d in ((2.0, 15.0), (1.0, 10.0), (0.75, 8.0)):
        # load_settings() is lru_cache'd: deep-copy before mutating.
        settings = copy.deepcopy(load_settings())
        settings["layer1"]["price_spike_pct_24h"] = spike_24h
        settings["layer1"]["price_spike_pct_30d"] = spike_30d
        from .event_backtests import replay_price_signals
        signals = []
        for symbol_id, (symbol, bars) in enumerate(price_data.items()):
            signals.extend(replay_price_signals(
                bars, symbol_id + 1, symbol, symbol, settings=settings))
        metrics = slice_run(price_data, signals, "2017-01-01", HOLDOUT_END,
                            settings_overrides=tuned_overrides)
        rows.append({
            "price_spike_pct_24h": spike_24h,
            "price_spike_pct_30d": spike_30d,
            "raw_signals_2017_2026": len(signals),
            "full_period_metrics": metrics,
        })
    return rows


def direction_probe(price_data, tuned_overrides) -> dict:
    """Diagnostic: continuation (momentum) trigger direction vs adopted
    mean-reversion mapping, same layer-2/3 stack, at the DEFAULT layer-1
    thresholds and at the 0.75%/8.0% low-threshold variant."""
    out = {}
    for label, (s24, s30) in (("default", (2.0, 15.0)),
                              ("low_threshold", (0.75, 8.0))):
        settings = copy.deepcopy(load_settings())
        settings["layer1"]["price_spike_pct_24h"] = s24
        settings["layer1"]["price_spike_pct_30d"] = s30
        signals = []
        for symbol_id, (symbol, bars) in enumerate(price_data.items()):
            signals.extend(replay_momentum_signals(
                bars, symbol_id + 1, symbol, symbol, settings=settings))
        metrics = slice_run(price_data, signals, "2017-01-01", HOLDOUT_END,
                            settings_overrides=tuned_overrides)
        out[label] = {"raw_signals": len(signals),
                      "full_period_metrics": metrics}
    return out


# ------------------------------------------------------------------ report
def evaluate(cache: Optional[BarCache] = None) -> dict:
    logging.basicConfig(level=logging.INFO)
    cache = cache or BarCache(CACHE_DIR, connect=False)
    tuning = load_tuning()
    candidate = tuning["final_candidate"]
    tuned_overrides = overrides_from_combo(candidate)
    price_data, signals = build_universe(cache)

    log.info("A/B on holdout %s..%s", HOLDOUT_START, HOLDOUT_END)
    ab = ab_on_holdout(price_data, signals, tuned_overrides)
    log.info("A/B decision: %s", ab["decision"])

    log.info("tuned playbook window re-runs")
    windows = run_tuned_windows(cache, tuned_overrides)

    log.info("holdout acceptance runs")
    holdout = holdout_acceptance(price_data, signals, tuned_overrides)

    log.info("structural diagnostics")
    tension = confirmation_tension(signals, price_data)
    density = signal_density(cache)
    thresholds = layer1_threshold_sensitivity(price_data, tuned_overrides)
    direction = direction_probe(price_data, tuned_overrides)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tuned_candidate": candidate,
        "tuned_overrides": tuned_overrides,
        "tuning_summary": {k: tuning[k] for k in
                           ("mean_train_sharpe", "mean_test_sharpe",
                            "wfer", "wfer_meaningful", "wfer_gate_passed",
                            "grid_size", "holdout_start")},
        "ab_holdout": ab,
        "tuned_windows": windows,
        "holdout": holdout,
        "diagnostics": {
            "confirmation_tension": tension,
            "signal_density": density,
            "layer1_threshold_sensitivity": thresholds,
            "direction_probe": direction,
        },
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(EVAL_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    write_markdown(report)
    return report


def write_markdown(report: dict) -> str:
    lines = ["# UGT-14 walk-forward tuning evaluation (real data)", ""]
    t = report["tuning_summary"]
    c = report["tuned_candidate"]
    lines += [
        "## Walk-forward summary (3y train -> 1y test, test years 2020-2024)",
        "",
        f"- Grid: {t['grid_size']} combos over the sanctioned space "
        "(layer-2 min_score, RSI/SMA windows, ATR SL/TP, heat/sector caps)",
        f"- Mean train Sharpe: {t['mean_train_sharpe']:.2f} | "
        f"mean test Sharpe: {t['mean_test_sharpe']:.2f}",
        f"- WFER: {t['wfer']:.2f} (meaningful: {t['wfer_meaningful']}; "
        f"gate >= {t['wfer_min'] if 'wfer_min' in t else 0.5}: "
        f"{'PASS' if t['wfer_gate_passed'] else 'FAIL'})",
        f"- Final candidate (last fold pick): `{json.dumps(c)}`",
        "",
        "## A/B on untouched holdout "
        f"({t['holdout_start']}..{HOLDOUT_END})",
        "",
        f"- Decision: **{report['ab_holdout']['decision']}** "
        f"(p={report['ab_holdout']['p_value']:.3f}, "
        f"mean diff={report['ab_holdout']['mean_diff']:.2f}, "
        f"folds={report['ab_holdout']['folds']})",
        "",
        "## Tuned playbook windows (acceptance table)",
        "",
        "| window | trades | win% | PF | Sharpe | DD% | pass |",
        "|---|---|---|---|---|---|---|",
    ]
    for w in report["tuned_windows"]:
        m = w["metrics"]
        lines.append(
            f"| {w['window']} | {m.get('total_trades', 0)} "
            f"| {m.get('win_rate_pct', 0):.1f} | {m.get('profit_factor', 0):.2f} "
            f"| {m.get('sharpe', 0):.2f} | {m.get('max_drawdown_pct', 0):.2f} "
            f"| {'PASS' if w['acceptance_passed'] else 'FAIL'} |")
    lines += ["", "## Holdout acceptance "
              f"({HOLDOUT_START}..{HOLDOUT_END}, untouched OOS)", ""]
    for variant in ("baseline", "tuned"):
        h = report["holdout"][variant]
        m = h["metrics"]
        lines.append(
            f"- {variant}: trades={m.get('total_trades', 0)} "
            f"win={m.get('win_rate_pct', 0):.1f}% PF={m.get('profit_factor', 0):.2f} "
            f"Sharpe={m.get('sharpe', 0):.2f} DD={m.get('max_drawdown_pct', 0):.2f}% "
            f"-> {'PASS' if h['acceptance_passed'] else 'FAIL'}")
    d = report["diagnostics"]
    lines += ["", "## Structural diagnostics", "",
              "Layer-2 confirmation tension at raw-signal time "
              "(RSI vs SMA support of trigger direction):", ""]
    for k, v in d["confirmation_tension"].items():
        lines.append(f"- {k}: {v['count']} ({v['pct']}%)" if isinstance(v, dict)
                     else f"- {k}: {v}")
    lines += ["", "Layer-1 trigger sensitivity (diagnostic only, NOT adopted):", ""]
    for row in d["layer1_threshold_sensitivity"]:
        m = row["full_period_metrics"]
        lines.append(
            f"- spike {row['price_spike_pct_24h']}%/day, "
            f"{row['price_spike_pct_30d']}%/30d: "
            f"{row['raw_signals_2017_2026']} raw signals, "
            f"trades={m.get('total_trades', 0)} win={m.get('win_rate_pct', 0):.1f}% "
            f"PF={m.get('profit_factor', 0):.2f} Sharpe={m.get('sharpe', 0):.2f}")
    dp = d["direction_probe"]
    lines += ["", "Trigger direction probe (continuation/momentum, diagnostic only):", ""]
    for label, row in dp.items():
        m = row["full_period_metrics"]
        lines.append(
            f"- {label} thresholds: {row['raw_signals']} raw signals; "
            f"trades={m.get('total_trades', 0)} win={m.get('win_rate_pct', 0):.1f}% "
            f"PF={m.get('profit_factor', 0):.2f} Sharpe={m.get('sharpe', 0):.2f} "
            f"DD={m.get('max_drawdown_pct', 0):.2f}%")
    lines += ["",
              "See wf_evaluation.json for full numbers; tuning detail in wf_tuning.json.",
              ""]
    with open(EVAL_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return EVAL_MD


def main(argv: Optional[list[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "run":
        report = evaluate()
        print(json.dumps({k: report[k] for k in
                          ("ab_holdout", "holdout")}, indent=2, default=str)[:2000])
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
