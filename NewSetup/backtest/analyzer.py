"""Backtest metrics and hard acceptance gates (playbook sections 5.1-5.3).

BacktestAnalyzer computes the acceptance-criterion statistics from a list
of closed trades plus an equity curve, and applies the Phase-5.3 hard
criteria configured under backtest.acceptance in config/settings.yaml.
"""

from __future__ import annotations

import math
from typing import Optional

from newsetup.config import load_settings
from newsetup.models import Trade

_ANNUALIZATION = math.sqrt(252.0)
_PF_NO_LOSERS = 999.0  # capped representation of infinite profit factor


class BacktestAnalyzer:
    """Metric computation and acceptance-gate checks (playbook 5.1-5.3)."""

    # ------------------------------------------------------------------
    def compute_metrics(self, trades: list[Trade],
                        equity_curve: list[float]) -> dict:
        """Derive all acceptance statistics for one backtest run.

        Sharpe/sortino are annualized (sqrt(252)) period returns of the
        equity curve; max drawdown is measured from the running peak.
        """
        trades = list(trades)
        curve = [float(v) for v in equity_curve]
        pnls = [float(t.pnl) for t in trades]
        wins = [p for p in pnls if p > 0.0]
        losses = [p for p in pnls if p < 0.0]
        total = len(trades)

        gross_win = sum(wins)
        gross_loss = -sum(losses)
        if total == 0:
            profit_factor = 0.0
        elif gross_loss == 0.0:
            profit_factor = _PF_NO_LOSERS
        else:
            profit_factor = gross_win / gross_loss

        risks = [abs(t.entry_price - t.stop_loss) * t.lot_size for t in trades]
        mean_risk = sum(risks) / len(risks) if risks else 0.0
        if total and mean_risk > 0.0:
            expectancy_r = (sum(pnls) / total) / mean_risk
        else:
            expectancy_r = 0.0

        returns = self._period_returns(curve)
        sharpe = self._sharpe(returns)
        sortino = self._sortino(returns)

        return {
            "total_trades": total,
            "win_rate_pct": 100.0 * len(wins) / total if total else 0.0,
            "profit_factor": profit_factor,
            "expectancy_r": expectancy_r,
            "sharpe": sharpe,
            "sortino": sortino,
            "max_drawdown_pct": self._max_drawdown_pct(curve),
            "total_return_pct": self._total_return_pct(curve),
            "avg_win": gross_win / len(wins) if wins else 0.0,
            "avg_loss": gross_loss / len(losses) if losses else 0.0,
        }

    # ------------------------------------------------------------------
    def acceptance(self, metrics: dict,
                   settings: Optional[dict] = None) -> tuple[bool, list[str]]:
        """Check metrics against backtest.acceptance (playbook 5.3).

        Returns (passed, failures) where each failure is a human-readable
        string such as 'max_drawdown_pct 14.2 > 12.0'.
        """
        settings = settings if settings is not None else load_settings()
        acc = (settings or {}).get("backtest", {}).get("acceptance", {}) or {}

        min_checks = (
            ("min_trades", "total_trades", acc.get("min_trades", 0)),
            ("min_win_rate_pct", "win_rate_pct", acc.get("min_win_rate_pct", 0.0)),
            ("min_profit_factor", "profit_factor", acc.get("min_profit_factor", 0.0)),
            ("min_sharpe", "sharpe", acc.get("min_sharpe", 0.0)),
        )
        failures: list[str] = []
        for criterion, metric, limit in min_checks:
            value = metrics.get(metric, 0.0)
            if value < limit:
                failures.append(
                    f"{criterion} not met: {metric} {round(value, 4)} < {round(limit, 4)}")
        max_dd = metrics.get("max_drawdown_pct", 0.0)
        dd_limit = acc.get("max_drawdown_pct", math.inf)
        if max_dd > dd_limit:
            failures.append(
                f"max_drawdown_pct {round(max_dd, 4)} > {round(dd_limit, 4)}")
        return (not failures, failures)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _period_returns(curve: list[float]) -> list[float]:
        returns: list[float] = []
        for prev, cur in zip(curve, curve[1:]):
            if prev == 0.0:
                returns.append(0.0)
            else:
                returns.append(cur / prev - 1.0)
        return returns

    @staticmethod
    def _sharpe(returns: list[float]) -> float:
        """Annualized mean/std of period returns; 0.0 when std is 0."""
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / len(returns)
        std = math.sqrt(var)
        if std == 0.0:
            return 0.0
        return mean / std * _ANNUALIZATION

    @staticmethod
    def _sortino(returns: list[float]) -> float:
        """Annualized mean/downside-deviation; 0.0 when downside is 0."""
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        downside = math.sqrt(
            sum(min(r, 0.0) ** 2 for r in returns) / len(returns))
        if downside == 0.0:
            return 0.0
        return mean / downside * _ANNUALIZATION

    @staticmethod
    def _max_drawdown_pct(curve: list[float]) -> float:
        if not curve:
            return 0.0
        peak = curve[0]
        max_dd = 0.0
        for value in curve:
            if value > peak:
                peak = value
            elif peak > 0.0:
                max_dd = max(max_dd, (peak - value) / peak * 100.0)
        return max_dd

    @staticmethod
    def _total_return_pct(curve: list[float]) -> float:
        if len(curve) < 2 or curve[0] == 0.0:
            return 0.0
        return (curve[-1] / curve[0] - 1.0) * 100.0
