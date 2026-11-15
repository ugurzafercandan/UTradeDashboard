"""Daily report generator (playbook 8.2 daily dashboard metrics)."""

from __future__ import annotations

from datetime import datetime, timezone


def daily_report(broker, signal_file: dict | None = None) -> str:
    """Markdown daily P&L / status report from a broker-like object."""
    acct = broker.account_state
    closed = broker.closed_trades
    open_ = broker.open_trades
    day_pnl = getattr(broker, "day_pnl", lambda: sum(t.pnl for t in closed))()
    wins = [t for t in closed if t.pnl > 0]
    losses = [t for t in closed if t.pnl <= 0]
    win_rate = (len(wins) / len(closed) * 100.0) if closed else 0.0
    total_pnl = sum(t.pnl for t in closed)
    active = (signal_file or {}).get("signals", [])

    lines = [
        f"# Daily Report — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        "",
        "## Portfolio",
        f"- Balance: {acct.balance:,.2f} USD",
        f"- Equity: {acct.equity:,.2f} USD",
        f"- Open positions: {len(open_)}",
        f"- Closed trades (all time): {len(closed)}",
        f"- Total closed P&L: {total_pnl:,.2f} USD",
        f"- Today P&L: {day_pnl:,.2f} USD",
        f"- Win rate: {win_rate:.1f}%",
        "",
        "## Open positions",
    ]
    if open_:
        for t in open_:
            lines.append(f"- {t.direction} {t.instrument} {t.lot_size} @ {t.entry_price} "
                         f"(SL {t.stop_loss} / TP {t.take_profit})")
    else:
        lines.append("- none")
    lines += ["", "## Active signals"]
    if active:
        for s in active:
            lines.append(f"- #{s.get('inefficiency_id')} {s.get('instrument')} "
                         f"{s.get('direction')} conf={s.get('confidence')}")
    else:
        lines.append("- none")
    return "\n".join(lines)
