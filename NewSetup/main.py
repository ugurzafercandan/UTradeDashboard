"""NewSetup main orchestrator (playbook 4.5).

Runs the full pipeline: Layer 1 scan -> Layer 2 confirm -> Layer 3 size ->
emit to signal bus -> (paper mode) execute on the paper broker with hard
risk enforcement.

Usage:
    python main.py --once            # one pipeline cycle (paper mode)
    python main.py --loop            # scheduled loop (15 min scans)
    python main.py --report          # print daily report
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from newsetup.config import load_settings
from newsetup.models import AccountState
from signals.layer1_scanner import Layer1Scanner
from signals.layer2_confirmation import Layer2Confirmation
from signals.layer3_portfolio import Layer3PortfolioManager
from signals.signal_bus import SignalBus
from data.gdelt_monitor import GDELTMonitor
from data.sentiment import FinBERTSentiment
from data.price_provider import default_price_provider
from execution.paper_broker import PaperBroker
from execution.order_manager import OrderManager
from execution.risk_enforcer import RiskEnforcer
from db.store import NewSetupDB
from monitoring.alerter import Alerter
from monitoring.daily_report import daily_report
from monitoring.degradation import DegradationDetector
from monitoring.quality_tracker import SignalQualityTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "logs", "signals.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger("newsetup.main")


def build_pipeline(settings: dict | None = None,
                    offline: bool | None = None) -> dict:
    settings = settings or load_settings()
    prices = default_price_provider(offline=offline)
    events = GDELTMonitor(offline=offline if offline is not None else prices.__class__.__name__ == "SyntheticPriceProvider")
    sentiment = FinBERTSentiment(use_transformers=False)
    scanner = Layer1Scanner(events, prices, sentiment, settings=settings)
    confirmation = Layer2Confirmation(prices, sentiment, settings=settings)
    portfolio = Layer3PortfolioManager(settings=settings)
    bus = SignalBus(settings=settings)
    broker = PaperBroker(starting_balance=settings["paper_trading"]["starting_balance"],
                         spread_pct=settings["paper_trading"]["spread_pct"])
    risk = RiskEnforcer(settings=settings)
    manager = OrderManager(broker)
    alerter = Alerter()
    # Persistence + quality tracking (playbook 9.2) + degradation ladder
    # (9.4), attached when a db_file is configured. No db -> no tracking
    # (paper cycle still runs, just unrecorded).
    db_path = settings.get("paths", {}).get("db_file")
    if db_path:
        root = os.path.dirname(os.path.abspath(__file__))
        db = NewSetupDB(os.path.join(root, db_path))
    else:
        db = None
    tracker = SignalQualityTracker(db) if db is not None else None
    degradation = DegradationDetector(db=db, settings=settings) if db is not None else None
    return dict(scanner=scanner, confirmation=confirmation, portfolio=portfolio,
                bus=bus, broker=broker, risk=risk, manager=manager, prices=prices,
                alerter=alerter, settings=settings, db=db, tracker=tracker,
                degradation=degradation, trades_recorded=0)


def _apply_degradation_responses(p: dict, confirmed: list) -> list:
    """Filter paused/retired inefficiencies out and apply size reductions.

    Playbook 9.4 automated responses: 'reduce_size' scales the layer-3
    lot by the state multiplier; 'paused'/'retired' drop the signal.
    Returns the list of sized signals AFTER the responses are applied.
    """
    degradation = p.get("degradation")
    sized = p.get("_last_sized", [])
    if degradation is None or not sized:
        return sized
    sizing = p["settings"].get("sizing", {})
    min_lot = float(sizing.get("min_lot", 0.01))
    lot_step = float(sizing.get("lot_step", 0.01))
    out = []
    for s in sized:
        iid = s.signal.raw.inefficiency_id
        if not degradation.is_tradable(iid):
            log.info("degradation: dropping signal for inefficiency %d "
                     "(paused/retired)", iid)
            continue
        mult = degradation.lot_multiplier(iid)
        if mult != 1.0:
            s.lot_size = max(min_lot, round(s.lot_size * mult / lot_step) * lot_step)
        out.append(s)
    return out


def run_signal_pipeline(p: dict) -> list[dict]:
    """One full cycle: scan -> confirm -> size -> emit -> execute (paper)."""
    raw = p["scanner"].scan_all()
    log.info("Layer 1: %d raw signals", len(raw))
    confirmed = []
    for s in raw:
        cs = p["confirmation"].confirm(s)
        if cs.confirmed:
            confirmed.append(cs)
    log.info("Layer 2: %d confirmed signals", len(confirmed))
    sized = p["portfolio"].size_positions(confirmed, p["broker"].account_state,
                                          p["broker"].open_trades, p["prices"])
    p["_last_sized"] = sized
    sized = _apply_degradation_responses(p, confirmed)
    log.info("Layer 3: %d sized positions", len(sized))
    emitted = p["bus"].emit(sized)
    for s in sized:
        p["manager"].place(s, risk_enforcer=p["risk"])
    # feed recent bars through the paper broker to progress open trades
    for s in sized:
        bars = p["prices"].get_series(s.signal.raw.instrument, lookback_days=5)
        for b in bars[-5:]:
            p["broker"].on_bar(s.signal.raw.instrument, b)
    for level, msg in p["broker"].pop_alerts() if hasattr(p["broker"], "pop_alerts") else []:
        p["alerter"].alert(level, msg)
    # Persist the funnel + closed trades (playbook 9.2), then run the
    # rolling degradation checks with automated responses (playbook 9.4).
    if p.get("tracker") is not None:
        already = p.get("trades_recorded", 0)
        closed = list(p["broker"].closed_trades)[already:]
        p["tracker"].record_cycle(raw, confirmed, sized, closed)
        p["trades_recorded"] = already + len(closed)
        p["tracker"].refresh()
    if p.get("degradation") is not None:
        escalations = p["degradation"].check_and_respond(
            list(p["broker"].closed_trades))
        for a in escalations:
            p["alerter"].alert(
                "critical",
                f"DEGRADATION #{a.inefficiency_id} {a.from_level} -> "
                f"{a.to_level}: {'; '.join(a.reasons)}")
    # Persist the paper book so the next daily cycle continues the same
    # 4-week account instead of restarting from the starting balance
    # (UGT-15 Phase 4; PaperBroker is in-memory by design).
    save = getattr(p["broker"], "save_state", None)
    if callable(save):
        saved = save()
        if saved:
            log.info("paper book persisted to %s", saved)
    return emitted


def main() -> int:
    ap = argparse.ArgumentParser(description="NewSetup SCI trading environment")
    ap.add_argument("--once", action="store_true", help="run one pipeline cycle")
    ap.add_argument("--loop", action="store_true", help="run scheduled loop")
    ap.add_argument("--report", action="store_true", help="print daily report")
    ap.add_argument("--validate", action="store_true",
                    help="run synthetic harness validation and write the"
                         " validation report (backtest/results/validation_report.md)")
    ap.add_argument("--offline", action="store_true", help="force offline providers")
    args = ap.parse_args()

    if args.validate:
        from backtest.validation import write_validation_report
        path = write_validation_report()
        print(f"validation report written to {path}")
        return 0

    offline = args.offline or None
    p = build_pipeline(offline=offline)

    if args.report:
        print(daily_report(p["broker"], p["bus"].load()))
        return 0
    if args.loop:
        interval = p["settings"]["layer1"]["scan_interval_minutes"] * 60
        log.info("starting loop: scan every %ds", interval)
        while True:
            run_signal_pipeline(p)
            time.sleep(interval)
    run_signal_pipeline(p)
    print(daily_report(p["broker"], p["bus"].load()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
