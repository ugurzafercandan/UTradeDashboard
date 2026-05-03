"""
update_frontend.py — USO-332
Pulls live paper trading results from paper_trades_v2.db and writes
results/live_paper_trades.json for the AlgoSignal Lab dashboard.

DB schema (actual columns):
    id, signal_id, open_time, close_time, symbol, portfolio_signal,
    direction, entry_price, exit_price, sl_price, tp_price,
    pnl, pnl_pct, bars_held, close_reason, status

Usage:
    python update_frontend.py [--db PATH] [--config PATH] [--out PATH]

Typical cron (every 30 min on gpu-server2):
    */30 * * * * cd /workspace/fx_ml && python update_frontend.py >> /tmp/update_frontend.log 2>&1
"""

import sqlite3
import json
import os
import math
import argparse
from datetime import datetime, timezone

DB_PATH_DEFAULT     = "/workspace/fx_ml/paper_trades_v2.db"
CFG_PATH_DEFAULT    = "/workspace/fx_ml/paper_trader_config.json"
OUT_PATH_DEFAULT    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "live_paper_trades.json")

RECENT_TRADES_LIMIT = 50
DEFAULT_NOTIONAL_FRAC = 0.1
DEFAULT_INITIAL_CAPITAL = 100_000


def load_notional_config(cfg_path):
    """Returns (default_frac, overrides_dict, initial_capital) from paper_trader_config.json."""
    if not os.path.exists(cfg_path):
        return DEFAULT_NOTIONAL_FRAC, {}, DEFAULT_INITIAL_CAPITAL
    with open(cfg_path) as f:
        cfg = json.load(f)
    default_frac = cfg.get("notional_frac", DEFAULT_NOTIONAL_FRAC)
    initial_capital = cfg.get("initial_capital", DEFAULT_INITIAL_CAPITAL)
    overrides = cfg.get("notional_overrides", {})
    return default_frac, overrides, initial_capital


def get_notional_frac(portfolio_signal, default_frac, overrides):
    """Look up notional fraction for a portfolio_signal label.

    The overrides keys use a longer name (e.g. 'P35_EURCHF_r067') while
    portfolio_signal in the DB is a shorter prefix (e.g. 'P35_EURCHF').
    Match by prefix.
    """
    if portfolio_signal in overrides:
        return overrides[portfolio_signal]
    # Try prefix match
    for key, val in overrides.items():
        if key.startswith(portfolio_signal):
            return val
    return default_frac


def sharpe_ratio(returns):
    """Annualised Sharpe from per-trade P&L % values. Assumes ~6 trades/day across portfolio."""
    if len(returns) < 2:
        return None
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    std = math.sqrt(variance)
    if std == 0:
        return None
    trades_per_year = 252 * 6
    return (mean / std) * math.sqrt(trades_per_year)


def query_all_signals(db_path, cfg_path):
    default_frac, overrides, initial_capital = load_notional_config(cfg_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT portfolio_signal, symbol
        FROM trades
        WHERE status = 'closed' AND portfolio_signal IS NOT NULL
        ORDER BY portfolio_signal
    """)
    signal_rows = cur.fetchall()

    signals_out = []
    for sig_row in signal_rows:
        portfolio_signal = sig_row["portfolio_signal"]
        symbol = sig_row["symbol"]
        notional_frac = get_notional_frac(portfolio_signal, default_frac, overrides)
        notional_usd = round(notional_frac * initial_capital)

        cur.execute("""
            SELECT open_time, close_time, symbol, direction,
                   entry_price, exit_price, pnl, pnl_pct, bars_held, close_reason
            FROM trades
            WHERE portfolio_signal = ? AND status = 'closed'
            ORDER BY close_time ASC
        """, (portfolio_signal,))
        rows = cur.fetchall()

        trades = []
        for r in rows:
            trades.append({
                "open_time":   r["open_time"] or "",
                "close_time":  r["close_time"] or "",
                "symbol":      r["symbol"] or symbol,
                "direction":   r["direction"] or "",
                "open_price":  r["entry_price"],
                "close_price": r["exit_price"],
                "pnl":         float(r["pnl"]) if r["pnl"] is not None else None,
                "pnl_pct":     float(r["pnl_pct"]) if r["pnl_pct"] is not None else None,
                "close_reason": r["close_reason"] or "",
            })

        pnl_values = [t["pnl_pct"] for t in trades if t["pnl_pct"] is not None]
        total = len(trades)
        wins = sum(1 for v in pnl_values if v > 0)
        win_rate = wins / total if total > 0 else None
        cum_pnl = sum(pnl_values)
        pnl_usd = sum(t["pnl"] for t in trades if t["pnl"] is not None)

        equity_curve = []
        running = 0.0
        for v in pnl_values:
            running += v
            equity_curve.append(round(running, 4))

        sharpe = sharpe_ratio(pnl_values)

        signals_out.append({
            "signal_id":         portfolio_signal,
            "symbol":            symbol,
            "notional_frac":     notional_frac,
            "notional_usd":      notional_usd,
            "total_trades":      total,
            "win_rate":          round(win_rate, 4) if win_rate is not None else None,
            "cumulative_pnl_pct": round(cum_pnl, 4),
            "cumulative_pnl_usd": round(pnl_usd, 2),
            "sharpe":            round(sharpe, 4) if sharpe is not None else None,
            "equity_curve":      equity_curve,
            "recent_trades":     trades[-RECENT_TRADES_LIMIT:],
        })
        print(f"[update_frontend] {portfolio_signal} {symbol}: {total} trades, "
              f"win_rate={win_rate:.1%} cum_pnl={cum_pnl:.4f}% "
              f"notional={notional_frac*100:.1f}% (${notional_usd:,})")

    conn.close()
    return signals_out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db",     default=DB_PATH_DEFAULT)
    parser.add_argument("--config", default=CFG_PATH_DEFAULT)
    parser.add_argument("--out",    default=OUT_PATH_DEFAULT)
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[update_frontend] DB not found: {args.db}")
        return

    signals_out = query_all_signals(args.db, args.config)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "signals": signals_out,
    }

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[update_frontend] Written {len(signals_out)} signals to {args.out}")


if __name__ == "__main__":
    main()
